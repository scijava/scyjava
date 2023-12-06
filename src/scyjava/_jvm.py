"""
Utility functions for working with the Java Virtual Machine.
"""

import atexit
import logging
import os
import re
import subprocess
import sys
from functools import lru_cache
from importlib import import_module
from pathlib import Path

import jpype
import jpype.config
from jgo import jgo

import scyjava.config
from scyjava.config import Mode, mode

_logger = logging.getLogger(__name__)

_startup_callbacks = []
_shutdown_callbacks = []


def jvm_version() -> str:
    """
    Gets the version of the JVM as a tuple, with each dot-separated digit
    as one element. Characters in the version string beyond only numbers
    and dots are ignored, in line with the java.version system property.

    Examples:
    * OpenJDK 17.0.1 -> [17, 0, 1]
    * OpenJDK 11.0.9.1-internal -> [11, 0, 9, 1]
    * OpenJDK 1.8.0_312 -> [1, 8, 0]

    If the JVM is already started, this function returns the equivalent of:
       jimport('java.lang.System')
         .getProperty('java.version')
         .split('.')

    In case the JVM is not started yet, a best effort is made to deduce
    the version from the environment without actually starting up the
    JVM in-process. If the version cannot be deduced, a RuntimeError
    with the cause is raised.
    """
    if mode == Mode.JEP:
        System = jimport("java.lang.System")
        version = str(System.getProperty("java.version"))
        # Get everything up to the hyphen
        version = version.split("-")[0]
        return tuple(map(int, version.split(".")))

    assert mode == Mode.JPYPE

    jvm_version = jpype.getJVMVersion()
    if jvm_version and jvm_version[0]:
        # JPype already knew the version.
        # JVM is probably already started.
        # Or JPype got smarter since 1.3.0.
        return jvm_version

    # JPype was clueless, which means the JVM has probably not started yet.
    # Let's look for a java executable, and ask via 'java -version'.

    default_jvm_path = jpype.getDefaultJVMPath()
    if not default_jvm_path:
        raise RuntimeError("Cannot glean the default JVM path")

    p = Path(default_jvm_path)
    if not p.exists():
        raise RuntimeError(f"Invalid default JVM path: {p}")

    java = None
    for _ in range(3):  # The bin folder is always <=3 levels up from libjvm.
        p = p.parent
        if p.name == "lib":
            java = p.parent / "bin" / "java"
        elif p.name == "bin":
            java = p / "java"

        if java is not None:
            if os.name == "nt":
                # Good ol' Windows! Nothing beats Windows.
                java = java.with_suffix(".exe")
            if not java.is_file():
                raise RuntimeError(f"No ../bin/java found at: {p}")
            break
    if java is None:
        raise RuntimeError(f"No java executable found inside: {p}")

    try:
        output = subprocess.check_output(
            [str(java), "-version"], stderr=subprocess.STDOUT
        ).decode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("System call to java failed") from e

    m = re.match('.*version "(([0-9]+\\.)+[0-9]+)', output)
    if not m:
        raise RuntimeError(f"Inscrutable java command output:\n{output}")

    return tuple(map(int, m.group(1).split(".")))


def start_jvm(options=None) -> None:
    """
    Explicitly connect to the Java virtual machine (JVM). Only one JVM can
    be active; does nothing if the JVM has already been started. Calling
    this function directly is typically not necessary, because the first
    time a scyjava function needing a JVM is invoked, one is started on the
    fly with the configuration specified via the scijava.config mechanism.

    :param options:
        List of options to pass to the JVM.
        For example: ['-Dfoo=bar', '-XX:+UnlockExperimentalVMOptions']
    """
    # if JVM is already running -- break
    if jvm_started():
        _logger.debug("The JVM is already running.")
        return

    assert mode == Mode.JPYPE

    # retrieve endpoint and repositories from scyjava config
    endpoints = scyjava.config.endpoints
    repositories = scyjava.config.get_repositories()

    # use the logger to notify user that endpoints are being added
    _logger.debug("Adding jars from endpoints {0}".format(endpoints))

    # get endpoints and add to JPype class path
    if len(endpoints) > 0:
        endpoints = endpoints[:1] + sorted(endpoints[1:])
        _logger.debug("Using endpoints %s", endpoints)
        _, workspace = jgo.resolve_dependencies(
            "+".join(endpoints),
            m2_repo=scyjava.config.get_m2_repo(),
            cache_dir=scyjava.config.get_cache_dir(),
            manage_dependencies=scyjava.config.get_manage_deps(),
            repositories=repositories,
            verbose=scyjava.config.get_verbose(),
            shortcuts=scyjava.config.get_shortcuts(),
        )
        jpype.addClassPath(os.path.join(workspace, "*"))

    # HACK: Try to set JAVA_HOME if it isn't already.
    if (
        "JAVA_HOME" not in os.environ
        or not os.environ["JAVA_HOME"]
        or not os.path.isdir(os.environ["JAVA_HOME"])
    ):
        _logger.debug("JAVA_HOME not set. Will try to infer it from sys.path.")

        libjvm_win = Path("Library") / "jre" / "bin" / "server" / "jvm.dll"
        libjvm_macos = Path("lib") / "server" / "libjvm.dylib"
        libjvm_linux = Path("lib") / "server" / "libjvm.so"
        libjvm_paths = {
            libjvm_win: Path("Library"),
            libjvm_macos: Path(),
            libjvm_linux: Path(),
        }
        for p in sys.path:
            if not p.endswith("site-packages"):
                continue
            # e.g. $CONDA_PREFIX/lib/python3.10/site-packages -> $CONDA_PREFIX
            # But we want it to work outside of Conda as well, theoretically.
            base = Path(p).parent.parent.parent
            for libjvm_path, java_home_path in libjvm_paths.items():
                if (base / libjvm_path).exists():
                    java_home = str((base / java_home_path).resolve())
                    _logger.debug(f"Detected JAVA_HOME: {java_home}")
                    os.environ["JAVA_HOME"] = java_home
                    break

    # initialize JPype JVM
    _logger.debug("Starting JVM")
    if options is None:
        options = scyjava.config.get_options()
    jpype.startJVM(*options, interrupt=True)

    # replace JPype/JVM shutdown handling with our own
    jpype.config.onexit = False
    jpype.config.free_resources = False
    atexit.register(shutdown_jvm)

    # invoke registered callback functions
    for callback in _startup_callbacks:
        callback()


def shutdown_jvm() -> None:
    """Shut down the JVM.

    This function makes a best effort to clean up Java resources first.
    In particular, shutdown hooks registered with scyjava.when_jvm_stops
    are sequentially invoked.

    Then, if the AWT subsystem has started, all AWT windows (as identified
    by the java.awt.Window.getWindows() method) are disposed to reduce the
    risk of GUI resources delaying JVM shutdown.

    Finally, the jpype.shutdownJVM() function is called. Note that you can
    set the jpype.config.destroy_jvm flag to request JPype to destroy the
    JVM explicitly, although setting this flag can lead to delayed shutdown
    times while the JVM is waiting for threads to finish.

    Note that if the JVM is not already running, then this function does
    nothing! In particular, shutdown hooks are skipped in this situation.

    :raise RuntimeError: if this method is called while in Jep mode.
    """
    if not jvm_started():
        return

    if mode == Mode.JEP:
        raise RuntimeError("Cannot shut down the JVM in Jep mode.")

    assert mode == Mode.JPYPE

    # invoke registered shutdown callback functions
    for callback in _shutdown_callbacks:
        try:
            callback()
        except Exception as e:
            print(f"Exception during shutdown callback: {e}")

    # dispose AWT resources if applicable
    if is_awt_initialized():
        Window = jimport("java.awt.Window")
        for w in Window.getWindows():
            w.dispose()

    # okay to shutdown JVM
    try:
        jpype.shutdownJVM()
    except Exception as e:
        print(f"Exception during JVM shutdown: {e}")


def jvm_started() -> bool:
    """Return true iff a Java virtual machine (JVM) has been started."""
    if mode == Mode.JEP:
        return True

    assert mode == Mode.JPYPE

    return jpype.isJVMStarted()


def gc() -> None:
    """
    Do a round of Java garbage collection.

    This function is a shortcut for Java's System.gc().

    :raise RuntimeError: If the JVM has not started yet.
    """
    _assert_jvm_started()
    System = jimport("java.lang.System")
    System.gc()


def memory_total() -> int:
    """
    Get the total amount of memory currently reserved by the JVM.

    This number will always be less than or equal to memory_max().

    In case the JVM was configured with -Xms flag upon startup (e.g. using
    the scyjava.config.set_heap_min function), the initial value will typically
    correspond approximately, but not exactly, to the configured value,
    although it is likely to grow over time as more Java objects are allocated.

    This function is a shortcut for Java's Runtime.getRuntime().totalMemory().

    :return: The total memory in bytes.
    :raise RuntimeError: if the JVM has not yet been started.
    """
    return int(_runtime().totalMemory())


def memory_max() -> int:
    """
    Get the maximum amount of memory that the JVM will attempt to use.

    This number will always be greater than or equal to memory_total().

    In case the JVM was configured with -Xmx flag upon startup (e.g. using
    the scyjava.config.set_heap_max function), the value will typically
    correspond approximately, but not exactly, to the configured value.

    This function is a shortcut for Java's Runtime.getRuntime().maxMemory().

    :return: The maximum memory in bytes.
    :raise RuntimeError: if the JVM has not yet been started.
    """
    return int(_runtime().maxMemory())


def memory_used() -> int:
    """
    Get the amount of memory currently in use by the JVM.

    This function is a shortcut for
    Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory().

    :return: The used memory in bytes.
    :raise RuntimeError: if the JVM has not yet been started.
    """
    return memory_total() - int(_runtime().freeMemory())


def available_processors() -> int:
    """
    Get the number of processors available to the JVM.

    This function is a shortcut for Java's
    Runtime.getRuntime().availableProcessors().

    :return: The number of available processors.
    :raise RuntimeError: if the JVM has not yet been started.
    """
    return int(_runtime().availableProcessors())


def is_jvm_headless() -> bool:
    """
    Return true iff Java is running in headless mode.

    :raise RuntimeError: If the JVM has not started yet.
    """
    if not jvm_started():
        raise RuntimeError("JVM has not started yet!")

    GraphicsEnvironment = scyjava.jimport("java.awt.GraphicsEnvironment")
    return bool(GraphicsEnvironment.isHeadless())


def is_awt_initialized() -> bool:
    """
    Return true iff the AWT subsystem has been initialized.

    Java starts up its AWT subsystem automatically and implicitly, as
    soon as an action is performed requiring it -- for example, if you
    jimport a java.awt or javax.swing class. This can lead to deadlocks
    on macOS if you are not running in headless mode and did not invoke
    those actions via the jpype.setupGuiEnvironment wrapper function;
    see the Troubleshooting section of the scyjava README for details.
    """
    if not jvm_started():
        return False
    Thread = scyjava.jimport("java.lang.Thread")
    threads = Thread.getAllStackTraces().keySet()
    return any(t.getName().startsWith("AWT-") for t in threads)


def when_jvm_starts(f) -> None:
    """
    Registers a function to be called when the JVM starts (or immediately).
    This is useful to defer construction of Java-dependent data structures
    until the JVM is known to be available. If the JVM has already been
    started, the function executes immediately.

    :param f: Function to invoke when scyjava.start_jvm() is called.
    """
    if jvm_started():
        # JVM was already started; invoke callback function immediately.
        f()
    else:
        # Add function to the list of callbacks to invoke upon start_jvm().
        global _startup_callbacks
        _startup_callbacks.append(f)


def when_jvm_stops(f) -> None:
    """
    Registers a function to be called just before the JVM shuts down.
    This is useful to perform cleanup of Java-dependent data structures.

    Note that if the JVM is not already running when shutdown_jvm is
    called, then these registered callback functions will be skipped!

    :param f: Function to invoke when scyjava.shutdown_jvm() is called.
    """
    global _shutdown_callbacks
    _shutdown_callbacks.append(f)


@lru_cache(maxsize=None)
def jimport(class_name: str):
    """
    Import a class from Java to Python.

    :param class_name: Name of the class to import.
    :return:
        A pointer to the class, which can be used to
        e.g. instantiate objects of that class.
    """
    if mode == Mode.JEP:
        module_path = class_name.rsplit(".", 1)
        module = import_module(module_path[0], module_path[1])
        return getattr(module, module_path[1])

    assert mode == Mode.JPYPE
    start_jvm()
    return jpype.JClass(class_name)


def _assert_jvm_started():
    if not jvm_started():
        raise RuntimeError("JVM has not started yet!")


def _runtime():
    _assert_jvm_started()
    Runtime = jimport("java.lang.Runtime")
    return Runtime.getRuntime()
