import enum
import logging
import os
import pathlib

import jpype
from jgo import maven_scijava_repository

_logger = logging.getLogger(__name__)

endpoints = []
_repositories = {"scijava.public": maven_scijava_repository()}
_verbose = 0
_manage_deps = True
_cache_dir = pathlib.Path.home() / ".jgo"
_m2_repo = pathlib.Path.home() / ".m2" / "repository"
_options = []
_shortcuts = {}


class Mode(enum.Enum):
    JEP = "jep"
    JPYPE = "jpype"


try:
    import jep  # noqa: F401

    mode = Mode.JEP
except ImportError:
    mode = Mode.JPYPE


def add_endpoints(*new_endpoints):
    """
    DEPRECATED since v1.2.1
    Please modify the endpoints field directly instead.
    """
    _logger.warning(
        "Deprecated method call: scyjava.config.add_endpoints(). "
        "Please modify scyjava.config.endpoints directly instead."
    )
    global endpoints
    _logger.debug("Adding endpoints %s to %s", new_endpoints, endpoints)
    endpoints.extend(new_endpoints)


def get_endpoints():
    """
    DEPRECATED since v1.2.1
    Please access the endpoints field directly instead.
    """
    _logger.warning(
        "Deprecated method call: scyjava.config.get_endpoints(). "
        "Please access scyjava.config.endpoints directly instead."
    )
    global endpoints
    return endpoints


def add_repositories(*args, **kwargs):
    global _repositories
    for arg in args:
        _logger.debug("Adding repositories %s to %s", arg, _repositories)
        _repositories.update(arg)
    _logger.debug("Adding repositories %s to %s", kwargs, _repositories)
    _repositories.update(kwargs)


def get_repositories():
    global _repositories
    return _repositories


def set_verbose(level):
    global _verbose
    _logger.debug("Setting verbose level to %d (was %d)", level, _verbose)
    _verbose = level


def get_verbose():
    global _verbose
    _logger.debug("Getting verbose level: %d", _verbose)
    return _verbose


def set_manage_deps(manage):
    global _manage_deps
    _logger.debug("Setting manage deps to %d (was %d)", manage, _manage_deps)
    _manage_deps = manage


def get_manage_deps():
    global _manage_deps
    return _manage_deps


def set_cache_dir(dir):
    global _cache_dir
    _logger.debug("Setting cache dir to %s (was %s)", dir, _cache_dir)
    _cache_dir = dir


def get_cache_dir():
    global _cache_dir
    return _cache_dir


def set_m2_repo(dir):
    global _m2_repo
    _logger.debug("Setting m2 repo dir to %s (was %s)", dir, _m2_repo)
    _m2_repo = dir


def get_m2_repo():
    global _m2_repo
    return _m2_repo


def add_classpath(*path):
    """
    Add elements to the Java class path.

    See also find_jars, which can be combined with add_classpath to
    add all the JARs beneath a given directory to the class path, a la:

        add_classpath(*find_jars('/path/to/folder-of-jars'))

    :param path:
        One or more file paths to add to the Java class path.

        A valid Java class path element is typically either a .jar file or a
        directory. When a class needs to be loaded, the Java runtime looks
        beneath each class path element for the .class file, nested in a folder
        structure matching the class's package name. For example, when loading
        a class foo.bar.Fubar, if a directory /home/jdoe/classes is included as
        a class path element, the class file at
        /home/jdoe/classes/foo/bar/Fubar.class will be used. It works the same
        for JAR files, except that the class files are loaded from the
        directory structure inside the JAR; in this example, a JAR file
        /home/jdoe/jars/fubar.jar on the class path containing file
        foo/bar/Fubar.class inside would be another way to provide the class
        foo.bar.Fubar.
    """
    for p in path:
        jpype.addClassPath(p)


def find_jars(directory):
    """
    Find .jar files beneath a given directory.

    :param directory: the folder to be searched
    :return: a list of JAR files
    """
    jars = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".jar"):
                path = os.path.join(root, f)
                jars.append(path)
    return jars


def get_classpath():
    return jpype.getClassPath()


def set_heap_min(mb: int = None, gb: int = None):
    """
    Set the initial amount of memory to allocate to the Java heap.

    Either mb or gb, but not both, must be given.

    Shortcut for passing -Xms###m or -Xms###g to Java.

    :param mb:
        The ### of megabytes of memory Java should start with.
    :param gb:
        The ### of gigabytes of memory Java should start with.
    :raise ValueError: If exactly one of mb or gb is not given.
    """
    add_option(f"-Xms{_mem_value(mb, gb)}")


def set_heap_max(mb: int = None, gb: int = None):
    """
    Shortcut for passing -Xmx###m or -Xmx###g to Java.

    Either mb or gb, but not both, must be given.

    :param mb:
        The maximum ### of megabytes of memory Java is allowed to use.
    :param gb:
        The maximum ### of gigabytes of memory Java is allowed to use.
    :raise ValueError: If exactly one of mb or gb is not given.
    """
    add_option(f"-Xmx{_mem_value(mb, gb)}")


def _mem_value(mb: int = None, gb: int = None) -> str:
    # fmt: off
    if mb is not None and gb is None: return f"{mb}m"  # noqa: E701
    if gb is not None and mb is None: return f"{gb}g"  # noqa: E701
    # fmt: on
    raise ValueError("Exactly one of mb or gb must be given.")


def enable_headless_mode():
    """
    Enable headless mode, for running Java without a display.
    This mode prevents any graphical elements from popping up.
    Shortcut for passing -Djava.awt.headless=true to Java.
    """
    add_option("-Djava.awt.headless=true")


def enable_remote_debugging(port: int = 8000, suspend: bool = False):
    """
    Enable the JDWP debugger, listening on the given port of localhost.
    Shortcut for -agentlib:jdwp=transport=dt_socket,address=localhost:<port>.

    :param port:
        The port to listen on for client debuggers (e.g. IDEs).
    :param suspend:
        If True, pause when starting up the JVM until a client debugger connects.
    """
    jdwp_args = {
        "transport": "dt_socket",
        "server": "y",
        "suspend": "y" if suspend else "n",
        "address": f"localhost:{port}",
    }
    arg_string = ",".join(f"{k}={v}" for k, v in jdwp_args.items())
    add_option(f"-agentlib:jdwp={arg_string}")


def add_option(option):
    global _options
    _options.append(option)


def add_options(options):
    global _options
    if isinstance(options, str):
        _options.append(options)
    else:
        _options.extend(options)


def get_options():
    global _options
    return _options


def add_shortcut(k, v):
    global _shortcuts
    _shortcuts[k] = v


def get_shortcuts():
    global _shortcuts
    return _shortcuts
