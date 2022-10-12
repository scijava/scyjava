"""
Utility functions for working with the Java and JVM.
"""
import atexit
import logging
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Callable

import jpype
import jpype.config
from jgo import jgo

import scyjava.config

_logger = logging.getLogger(__name__)

_startup_callbacks = []
_shutdown_callbacks = []


class JavaClasses:
    """
    Utility class used to make importing frequently-used Java classes
    significantly easier and more readable.

    Benefits:
    * Minimal boilerplate
    * Lazy evaluation
    * Usable within type hints

    Example:

        from scyjava import JavaClasses

        class MyJavaClasses(JavaClasses):
            @JavaClasses.java_class
            def String(self): return "java.lang.String"
            @JavaClasses.java_class
            def Integer(self): return "java.lang.Integer"
            # ... and many more ...

        jc = MyJavaClasses()

        def parse_number_with_java(s: "jc.String") -> "jc.Integer":
            return jc.Integer.parseInt(s)
    """

    def java_import(func: Callable[[], str]) -> Callable[[], jpype.JClass]:
        """
        A decorator used to lazily evaluate a java import.
        func is a function of a Python class that takes no arguments and
        returns a string identifying a Java class by name.

        Using that function, this decorator creates a property
        that when called, imports the class identified by the function.
        """

        @property
        def inner(self):
            if not jvm_started():
                raise Exception()
            try:
                return jimport(func(self))
            except TypeError:
                return None

        return inner


# -- JVM functions --


def jvm_version():
    """
    Gets the version of the JVM as a tuple,
    with each dot-separated digit as one element.
    Characters in the version string beyond only
    numbers and dots are ignored, in line
    with the java.version system property.

    Examples:
    * OpenJDK 17.0.1 -> [17, 0, 1]
    * OpenJDK 11.0.9.1-internal -> [11, 0, 9, 1]
    * OpenJDK 1.8.0_312 -> [1, 8, 0]

    If the JVM is already started,
    this function should return the equivalent of:
       jimport('java.lang.System')
         .getProperty('java.version')
         .split('.')

    In case the JVM is not started yet,a best effort is made to deduce
    the version from the environment without actually starting up the
    JVM in-process. If the version cannot be deduced, a RuntimeError
    with the cause is raised.
    """
    jvm_version = jpype.getJVMVersion()
    if jvm_version and jvm_version[0]:
        # JPype already knew the version.
        # JVM is probably already started.
        # Or JPype got smarter since 1.3.0.
        return jvm_version

    # JPype was clueless, which means the JVM has probably not started yet.
    # Let's look for a java executable, and ask it directly with 'java
    # -version'.

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

    version = subprocess.check_output(
        [str(java), "-version"], stderr=subprocess.STDOUT
    ).decode()
    m = re.match('.*version "(([0-9]+\\.)+[0-9]+)', version)
    if not m:
        raise RuntimeError(f"Inscrutable java command output:\n{version}")

    return tuple(map(int, m.group(1).split(".")))


def start_jvm(options=None):
    """
    Explicitly connect to the Java virtual machine (JVM). Only one JVM can
    be active; does nothing if the JVM has already been started. Calling
    this function directly is typically not necessary, because the first
    time a scyjava function needing a JVM is invoked, one is started on the
    fly with the configuration specified via the scijava.config mechanism.

    :param options: List of options to pass to the JVM. For example:
                    ['-Djava.awt.headless=true', '-Xmx4g']
    """
    # if JVM is already running -- break
    if jvm_started():
        _logger.debug("The JVM is already running.")
        return

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


def shutdown_jvm():
    """Shutdown the JVM.

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
    """
    if not jvm_started():
        return

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


def jvm_started():
    """Return true iff a Java virtual machine (JVM) has been started."""
    return jpype.isJVMStarted()


def is_jvm_headless():
    """
    Return true iff Java is running in headless mode.

    :raises RuntimeError: If the JVM has not started yet.
    """
    if not jvm_started():
        raise RuntimeError("JVM has not started yet!")

    GraphicsEnvironment = scyjava.jimport("java.awt.GraphicsEnvironment")
    return GraphicsEnvironment.isHeadless()


def is_awt_initialized():
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


def when_jvm_starts(f):
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


def when_jvm_stops(f):
    """
    Registers a function to be called just before the JVM shuts down.
    This is useful to perform cleanup of Java-dependent data structures.

    Note that if the JVM is not already running when shutdown_jvm is
    called, then these registered callback functions will be skipped!

    :param f: Function to invoke when scyjava.shutdown_jvm() is called.
    """
    global _shutdown_callbacks
    _shutdown_callbacks.append(f)


# -- Java functions --


def isjava(data):
    """Return whether the given data object is a Java object."""
    return isinstance(data, jpype.JClass) or isinstance(data, jpype.JObject)


@lru_cache(maxsize=None)
def jimport(class_name):
    """
    Import a class from Java to Python.

    :param class_name: Name of the class to import.
    :returns: A pointer to the class, which can be used to
              e.g. instantiate objects of that class.
    """
    start_jvm()
    return jpype.JClass(class_name)


def jclass(data):
    """
    Obtain a Java class object.

    :param data: The object from which to glean the class.
    Supported types include:
    A. Name of a class to look up, analogous to
    Class.forName("java.lang.String");
    B. A jpype.JClass object analogous to String.class;
    C. A jpype.JObject instance analogous to o.getClass().
    :returns: A java.lang.Class object, suitable for use with reflection.
    :raises TypeError: if the argument is not one of the aforementioned types.
    """
    if isinstance(data, jpype.JClass):
        return data.class_
    if isinstance(data, jpype.JObject):
        return data.getClass()
    if isinstance(data, str):
        return jclass(jimport(data))
    raise TypeError("Cannot glean class from data of type: " + str(type(data)))


def jstacktrace(exc):
    """
    Extract the Java-side stack trace from a Java exception.

    Example of usage:

        from scyjava import jimport, jstacktrace
        try:
            Integer = jimport('java.lang.Integer')
            nan = Integer.parseInt('not a number')
        except Exception as exc:
            print(jstacktrace(exc))

    :param exc: The Java Throwable from which to extract the stack trace.
    :returns: A multi-line string containing the stack trace, or empty string
    if no stack trace could be extracted.
    """
    try:
        StringWriter = jimport("java.io.StringWriter")
        PrintWriter = jimport("java.io.PrintWriter")
        sw = StringWriter()
        exc.printStackTrace(PrintWriter(sw, True))
        return sw.toString()
    except BaseException:
        return ""