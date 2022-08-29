import atexit
import collections.abc
import logging
import os
import re
import subprocess
import sys
import typing
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, NamedTuple

import jgo
import jpype
import jpype.config
from _jpype import _JObject
from jpype.types import (
    JArray,
    JBoolean,
    JByte,
    JChar,
    JDouble,
    JFloat,
    JInt,
    JLong,
    JShort,
)

import scyjava.config

_logger = logging.getLogger(__name__)

# Set of module properties
_CONSTANTS: Dict[str, Callable] = {}


def constant(func: Callable[[], Any], cache=True) -> Callable[[], Any]:
    """
    Turns a function into a property of this module
    Functions decorated with this property must have a
    leading underscore!
    :param func: The function to turn into a property
    """
    if func.__name__[0] != "_":
        raise ValueError(
            f"""Function {func.__name__} must have
            a leading underscore in its name
            to become a module property!"""
        )
    name = func.__name__[1:]
    if cache:
        func = (lru_cache(maxsize=None))(func)
    _CONSTANTS[name] = func
    return func


def __getattr__(name):
    """
    Runs as a fallback when this module does not have an
    attribute.
    :param name: The name of the attribute being searched for.
    """
    if name in _CONSTANTS:
        return _CONSTANTS[name]()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


@constant
def ___version__():
    # First pass: use the version output by setuptools_scm
    try:
        import scyjava.version

        return scyjava.version.version
    except ImportError:
        pass
    # Second pass: use importlib.metadata
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("scyjava")
    except ImportError or PackageNotFoundError:
        pass
    # Third pass: use pkg_resources
    try:
        from pkg_resources import get_distribution

        return get_distribution("scyjava").version
    except ImportError:
        pass
    # Fourth pass: Give up
    return "Cannot determine version! Ensure pkg_resources is installed!"


# -- JVM setup --

_startup_callbacks = []
_shutdown_callbacks = []


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


_config_options = scyjava.config.get_options()


def start_jvm(options=_config_options):
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
    jpype.startJVM(*options, interrupt=True)

    # replace JPype/JVM shutdown handling with our own
    jpype.config.onexit = False
    jpype.config.free_resources = False
    atexit.register(shutdown_jvm)

    _import_java_classes()

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


# -- Utility functions --


def get_version(java_class):
    """
    Return the version of a Java class.
    Requires org.scijava:scijava-common on the classpath.

    The version string is extracted from the given class's associated JAR
    artifact (if any), either the embedded Maven POM if the project was built
    with Maven, or the JAR manifest's Specification-Version value if it exists.

    See org.scijava.VersionUtils.getVersion(Class) for further details.
    """
    VersionUtils = jimport("org.scijava.util.VersionUtils")
    version = VersionUtils.getVersion(java_class)
    return version


def is_version_at_least(actual_version, minimum_version):
    """
    Return a boolean on a version comparison.
    Requires org.scijava:scijava-common on the classpath.

    Returns True if the given actual version is greater than or
    equal to the specified minimum version, or False otherwise.

    See org.scijava.VersionUtils.compare(String, String) for further details.
    """
    VersionUtils = jimport("org.scijava.util.VersionUtils")
    return VersionUtils.compare(actual_version, minimum_version) >= 0


def compare_version(version, java_class_version):
    """
    This function is deprecated. Use is_version_at_least instead.
    """
    _logger.warning(
        "The compare_version function is deprecated. Use is_version_at_least instead."
    )
    return version != java_class_version and is_version_at_least(
        java_class_version, version
    )


# -- Type Conversion Utilities --

# NB: We cannot use org.scijava.priority.Priority or other Java-side class
# here because we don't want to impose Java-side dependencies, and we don't
# want to require Java to be started before reasoning about priorities.
class Priority:
    FIRST = 1e300
    EXTREMELY_HIGH = 1e6
    VERY_HIGH = 1e4
    HIGH = 1e2
    NORMAL = 0
    LOW = -1e2
    VERY_LOW = -1e4
    EXTREMELY_LOW = -1e6
    LAST = -1e300


class Converter(NamedTuple):
    predicate: Callable[[Any], bool]
    converter: Callable[[Any], Any]
    priority: float = Priority.NORMAL


def _convert(obj: Any, converters: typing.List[Converter]) -> Any:
    suitable_converters = filter(lambda c: c.predicate(obj), converters)
    prioritized = max(suitable_converters, key=lambda c: c.priority)
    return prioritized.converter(obj)


def _add_converter(converter: Converter, converters: typing.List[Converter]):
    converters.append(converter)


# -- Python to Java --

# Adapted from code posted by vslotman on GitHub:
# https://github.com/kivy/pyjnius/issues/217#issue-145981070


def isjava(data):
    """Return whether the given data object is a Java object."""
    return isinstance(data, jpype.JClass) or isinstance(data, _JObject)


def jclass(data):
    """
    Obtain a Java class object.

    :param data: The object from which to glean the class.
    Supported types include:
    A. Name of a class to look up, analogous to
    Class.forName("java.lang.String");
    B. A jpype.JClass object analogous to String.class;
    C. A _jpype._JObject instance analogous to o.getClass().
    :returns: A java.lang.Class object, suitable for use with reflection.
    :raises TypeError: if the argument is not one of the aforementioned types.
    """
    if isinstance(data, jpype.JClass):
        return data.class_
    if isinstance(data, _JObject):
        return data.getClass()
    if isinstance(data, str):
        return jclass(jimport(data))
    raise TypeError("Cannot glean class from data of type: " + str(type(data)))


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


def _raise_type_exception(obj: Any):
    raise TypeError("Unsupported type: " + str(type(obj)))


def _convertMap(obj: collections.abc.Mapping):
    jmap = LinkedHashMap()
    for k, v in obj.items():
        jk = to_java(k)
        jv = to_java(v)
        jmap.put(jk, jv)
    return jmap


def _convertSet(obj: collections.abc.Set):
    jset = LinkedHashSet()
    for item in obj:
        jitem = to_java(item)
        jset.add(jitem)
    return jset


def _convertIterable(obj: collections.abc.Iterable):
    jlist = ArrayList()
    for item in obj:
        jitem = to_java(item)
        jlist.add(jitem)
    return jlist


java_converters: typing.List[Converter] = []


def add_java_converter(converter: Converter):
    """
    Adds a converter to the list used by to_java
    :param converter: A Converter going from python to java
    """
    _add_converter(converter, java_converters)


def to_java(obj: Any) -> Any:
    """
    Recursively convert a Python object to a Java object.
    :param data: The Python object to convert.
    Supported types include:
    * str -> String
    * bool -> Boolean
    * int -> Integer, Long or BigInteger as appropriate
    * float -> Float, Double or BigDecimal as appropriate
    * dict -> LinkedHashMap
    * set -> LinkedHashSet
    * list -> ArrayList
    :returns: A corresponding Java object with the same contents.
    :raises TypeError: if the argument is not one of the aforementioned types.
    """
    start_jvm()
    return _convert(obj, java_converters)


def _stock_java_converters() -> typing.List[Converter]:
    """
    Returns all python-to-java converters supported out of the box!
    This should only be called after the JVM has been started!
    :returns: A list of Converters
    """
    return [
        # Other (Exceptional) converter
        Converter(
            predicate=lambda obj: True,
            converter=_raise_type_exception,
            priority=Priority.EXTREMELY_LOW - 1,
        ),
        # NoneType converter
        Converter(
            predicate=lambda obj: obj is None,
            converter=lambda obj: None,
            priority=Priority.EXTREMELY_HIGH + 1,
        ),
        # Java identity converter
        Converter(
            predicate=isjava,
            converter=lambda obj: obj,
            priority=Priority.EXTREMELY_HIGH,
        ),
        # String converter
        Converter(
            predicate=lambda obj: isinstance(obj, str),
            converter=lambda obj: String(obj.encode("utf-8"), "utf-8"),
        ),
        # Boolean converter
        Converter(
            predicate=lambda obj: isinstance(obj, bool),
            converter=Boolean,
        ),
        # Integer converter
        Converter(
            predicate=lambda obj: isinstance(obj, int)
            and Integer.MIN_VALUE <= obj <= Integer.MAX_VALUE,
            converter=Integer,
        ),
        # Long converter
        Converter(
            predicate=lambda obj: isinstance(obj, int)
            and Long.MIN_VALUE <= obj <= Long.MAX_VALUE,
            converter=Long,
            priority=Priority.NORMAL - 1,
        ),
        # BigInteger converter
        Converter(
            predicate=lambda obj: isinstance(obj, int),
            converter=lambda obj: BigInteger(str(obj)),
            priority=Priority.NORMAL - 2,
        ),
        # Float converter
        Converter(
            predicate=lambda obj: isinstance(obj, float)
            and Float.MIN_VALUE <= obj <= Float.MAX_VALUE,
            converter=Float,
        ),
        # Double converter
        Converter(
            predicate=lambda obj: isinstance(obj, float)
            and Double.MAX_VALUE <= obj <= Double.MAX_VALUE,
            converter=Double,
            priority=Priority.NORMAL - 1,
        ),
        # BigDecimal converter
        Converter(
            predicate=lambda obj: isinstance(obj, float),
            converter=lambda obj: BigDecimal(str(obj)),
            priority=Priority.NORMAL - 2,
        ),
        # Pandas table converter
        Converter(
            predicate=lambda obj: type(obj).__name__ == "DataFrame",
            converter=_pandas_to_table,
            priority=Priority.NORMAL + 1,
        ),
        # Mapping converter
        Converter(
            predicate=lambda obj: isinstance(obj, collections.abc.Mapping),
            converter=_convertMap,
        ),
        # Set converter
        Converter(
            predicate=lambda obj: isinstance(obj, collections.abc.Set),
            converter=_convertSet,
        ),
        # Iterable converter
        Converter(
            predicate=lambda obj: isinstance(obj, collections.abc.Iterable),
            converter=_convertIterable,
            priority=Priority.NORMAL - 1,
        ),
    ]


# -- Java to Python --


def _jstr(data):
    if isinstance(data, JavaObject):
        return str(data)
    # NB: We want Python strings to render in single quotes.
    return "{!r}".format(data)


class JavaObject:
    def __init__(self, jobj, intended_class=None):
        if intended_class is None:
            intended_class = Object
        if not isinstance(jobj, intended_class):
            raise TypeError(
                f"Not a {intended_class.getName()}: {jclass(jobj).getName()}"
            )
        self.jobj = jobj

    def __str__(self):
        return _jstr(self.jobj)


class JavaIterable(JavaObject, collections.abc.Iterable):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Iterable)

    def __iter__(self):
        return to_python(self.jobj.iterator())

    def __str__(self):
        return "[" + ", ".join(_jstr(v) for v in self) + "]"


class JavaCollection(JavaIterable, collections.abc.Collection):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Collection)

    def __contains__(self, item):
        # NB: Collection.contains returns boolean, so no need for gentleness.
        return to_python(self.jobj.contains(to_java(item)))

    def __len__(self):
        return to_python(self.jobj.size())

    def __eq__(self, other):
        try:
            if len(self) != len(other):
                return False
            for e1, e2 in zip(self, other):
                if e1 != e2:
                    return False
            return True
        except TypeError:
            return False


class JavaIterator(JavaObject, collections.abc.Iterator):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Iterator)

    def __next__(self):
        if self.jobj.hasNext():
            # NB: Even if an element cannot be converted,
            # we still want to support Pythonic iteration.
            return to_python(self.jobj.next(), gentle=True)
        raise StopIteration


class JavaList(JavaCollection, collections.abc.MutableSequence):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, List)

    def __getitem__(self, key):
        # NB: Even if an element cannot be converted,
        # we still want Pythonic access to elements.
        return to_python(self.jobj.get(key), gentle=True)

    def __setitem__(self, key, value):
        # NB: List.set(int, Object) returns inserted element, so be gentle
        # here.
        return to_python(self.jobj.set(key, to_java(value)), gentle=True)

    def __delitem__(self, key):
        # NB: List.remove(Object) returns boolean, so no need for gentleness.
        return to_python(self.jobj.remove(to_java(key)))

    def insert(self, index, object):
        # NB: List.set(int, Object) returns inserted element, so be gentle
        # here.
        return to_python(self.jobj.set(index, to_java(object)), gentle=True)


class JavaMap(JavaObject, collections.abc.MutableMapping):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Map)

    def __getitem__(self, key):
        # NB: Even if an element cannot be converted,
        # we still want Pythonic access to elements.
        return to_python(self.jobj.get(to_java(key)), gentle=True)

    def __setitem__(self, key, value):
        # NB: Map.put(Object, Object) returns inserted value, so be gentle
        # here.
        put_return: bool = self.jobj.put(to_java(key), to_java(value))
        return to_python(put_return, gentle=True)

    def __delitem__(self, key):
        # NB: Map.remove(Object) returns the removed key, so be gentle here.
        return to_python(self.jobj.remove(to_java(key)), gentle=True)

    def keys(self):
        return to_python(self.jobj.keySet())

    def __iter__(self):
        return self.keys().__iter__()

    def __len__(self):
        return to_python(self.jobj.size())

    def __eq__(self, other):
        try:
            if len(self) != len(other):
                return False
            for k in self:
                if k not in other or self[k] != other[k]:
                    return False
            return True
        except TypeError:
            return False

    def __str__(self):
        def item_str(k, v):
            return _jstr(k) + ": " + _jstr(v)

        return "{" + ", ".join(item_str(k, v) for k, v in self.items()) + "}"


class JavaSet(JavaCollection, collections.abc.MutableSet):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Set)

    def add(self, item):
        # NB: Set.add returns boolean, so no need for gentleness.
        return to_python(self.jobj.add(to_java(item)))

    def discard(self, item):
        # NB: Set.remove returns boolean, so no need for gentleness.
        return to_python(self.jobj.remove(to_java(item)))

    def __iter__(self):
        return to_python(self.jobj.iterator())

    def __eq__(self, other):
        try:
            if len(self) != len(other):
                return False
            for k in self:
                if k not in other:
                    return False
            return True
        except TypeError:
            return False

    def __str__(self):
        return "{" + ", ".join(_jstr(v) for v in self) + "}"


py_converters: typing.List[Converter] = []


def add_py_converter(converter: Converter):
    """
    Adds a converter to the list used by to_python
    :param converter: A Converter from java to python
    """
    _add_converter(converter, py_converters)


def to_python(data: Any, gentle: bool = False) -> Any:
    """
    Recursively convert a Java object to a Python object.
    :param data: The Java object to convert.
    :param gentle: If set, and the type cannot be converted, leaves
                   the data alone rather than raising a TypeError.
    Supported types include:
    * String, Character -> str
    * Boolean -> bool
    * Byte, Short, Integer, Long, BigInteger -> int
    * Float, Double, BigDecimal -> float
    * Map -> collections.abc.MutableMapping (dict-like)
    * Set -> collections.abc.MutableSet (set-like)
    * List -> collections.abc.MutableSequence (list-like)
    * Collection -> collections.abc.Collection
    * Iterable -> collections.abc.Iterable
    * Iterator -> collections.abc.Iterator
    :returns: A corresponding Python object with the same contents.
    :raises TypeError: if the argument is not one of the aforementioned types,
                       and the gentle flag is not set.
    """
    start_jvm()
    try:
        return _convert(data, py_converters)
    except TypeError as exc:
        if gentle:
            return data
        raise exc


def _stock_py_converters() -> typing.List:
    """
    Returns all java-to-python converters supported out of the box!
    This should only be called after the JVM has been started!
    :returns: A list of Converters
    """
    return [
        # Other (Exceptional) converter
        Converter(
            predicate=lambda obj: True,
            converter=_raise_type_exception,
            priority=Priority.EXTREMELY_LOW - 1,
        ),
        # Java identity converter
        Converter(
            predicate=lambda obj: not isjava(obj),
            converter=lambda obj: obj,
            priority=Priority.EXTREMELY_HIGH,
        ),
        # JBoolean converter
        Converter(
            predicate=lambda obj: isinstance(obj, JBoolean),
            converter=bool,
            priority=Priority.NORMAL + 1,
        ),
        # JInt/JLong/JShort converter
        Converter(
            predicate=lambda obj: isinstance(obj, (JByte, JInt, JLong, JShort)),
            converter=int,
            priority=Priority.NORMAL + 1,
        ),
        # JDouble/JFloat converter
        Converter(
            predicate=lambda obj: isinstance(obj, (JDouble, JFloat)),
            converter=float,
            priority=Priority.NORMAL + 1,
        ),
        # JChar converter
        Converter(
            predicate=lambda obj: isinstance(obj, JChar),
            converter=str,
            priority=Priority.NORMAL + 1,
        ),
        # Boolean converter
        Converter(
            predicate=lambda obj: isinstance(obj, Boolean),
            converter=lambda obj: obj.booleanValue(),
        ),
        # Byte converter
        Converter(
            predicate=lambda obj: isinstance(obj, Byte),
            converter=lambda obj: obj.byteValue(),
        ),
        # Char converter
        Converter(
            predicate=lambda obj: isinstance(obj, Character),
            converter=lambda obj: obj.toString(),
        ),
        # Double converter
        Converter(
            predicate=lambda obj: isinstance(obj, Double),
            converter=lambda obj: obj.doubleValue(),
        ),
        # Float converter
        Converter(
            predicate=lambda obj: isinstance(obj, Float),
            converter=lambda obj: obj.floatValue(),
        ),
        # Integer converter
        Converter(
            predicate=lambda obj: isinstance(obj, Integer),
            converter=lambda obj: obj.intValue(),
        ),
        # Long converter
        Converter(
            predicate=lambda obj: isinstance(obj, Long),
            converter=lambda obj: obj.longValue(),
        ),
        # Short converter
        Converter(
            predicate=lambda obj: isinstance(obj, Short),
            converter=lambda obj: obj.shortValue(),
        ),
        # Void converter
        Converter(
            predicate=lambda obj: isinstance(obj, Void),
            converter=lambda obj: None,
        ),
        # String converter
        Converter(
            predicate=lambda obj: isinstance(obj, String),
            converter=lambda obj: str(obj),
        ),
        # BigInteger converter
        Converter(
            predicate=lambda obj: isinstance(obj, BigInteger),
            converter=lambda obj: int(str(obj.toString())),
        ),
        # BigDecimal converter
        Converter(
            predicate=lambda obj: isinstance(obj, BigDecimal),
            converter=lambda obj: float(str(obj.toString())),
        ),
        # SciJava Table converter
        Converter(
            predicate=_is_table,
            converter=_convert_table,
        ),
        # List converter
        Converter(
            predicate=lambda obj: isinstance(obj, List),
            converter=JavaList,
        ),
        # Map converter
        Converter(
            predicate=lambda obj: isinstance(obj, Map),
            converter=JavaMap,
        ),
        # Set converter
        Converter(
            predicate=lambda obj: isinstance(obj, Set),
            converter=JavaSet,
        ),
        # Collection converter
        Converter(
            predicate=lambda obj: isinstance(obj, Collection),
            converter=JavaCollection,
            priority=Priority.NORMAL - 1,
        ),
        # Iterable converter
        Converter(
            predicate=lambda obj: isinstance(obj, Iterable),
            converter=JavaIterable,
            priority=Priority.NORMAL - 1,
        ),
        # Iterator converter
        Converter(
            predicate=lambda obj: isinstance(obj, Iterator),
            converter=JavaIterator,
            priority=Priority.NORMAL - 1,
        ),
        # JArray converter
        Converter(
            predicate=lambda obj: isinstance(obj, JArray),
            converter=lambda obj: [to_python(o) for o in obj],
            priority=Priority.VERY_LOW,
        ),
    ]


def _is_table(obj: Any) -> bool:
    """Checks if obj is a table"""
    try:
        return isinstance(obj, jimport("org.scijava.table.Table"))
    except BaseException:
        # No worries if scijava-table is not available.
        pass


def _convert_table(obj: Any):
    """Converts obj to a table."""
    try:
        return _table_to_pandas(obj)
    except BaseException:
        # No worries if scijava-table is not available.
        pass


def _import_java_classes():
    global Boolean
    global Byte
    global Character
    global Double
    global Float
    global Integer
    global Iterable
    global Long
    global Object
    global Short
    global String
    global Void
    global BigDecimal
    global BigInteger
    global ArrayList
    global Collection
    global Iterator
    global LinkedHashMap
    global LinkedHashSet
    global List
    global Map
    global Set

    _logger.debug("Importing Java classes...")

    # grab needed Java classes
    Boolean = jimport("java.lang.Boolean")
    Byte = jimport("java.lang.Byte")
    Character = jimport("java.lang.Character")
    Double = jimport("java.lang.Double")
    Float = jimport("java.lang.Float")
    Integer = jimport("java.lang.Integer")
    Iterable = jimport("java.lang.Iterable")
    Long = jimport("java.lang.Long")
    Object = jimport("java.lang.Object")
    Short = jimport("java.lang.Short")
    String = jimport("java.lang.String")
    Void = jimport("java.lang.Void")
    BigDecimal = jimport("java.math.BigDecimal")
    BigInteger = jimport("java.math.BigInteger")
    ArrayList = jimport("java.util.ArrayList")
    Collection = jimport("java.util.Collection")
    Iterator = jimport("java.util.Iterator")
    LinkedHashMap = jimport("java.util.LinkedHashMap")
    LinkedHashSet = jimport("java.util.LinkedHashSet")
    List = jimport("java.util.List")
    Map = jimport("java.util.Map")
    Set = jimport("java.util.Set")


def _import_pandas():
    try:
        import pandas as pd

        return pd
    except ImportError:
        msg = "The Pandas library is missing (http://pandas.pydata.org/). "
        msg += "Please install it before using this function."
        raise Exception(msg)


def _table_to_pandas(table):
    pd = _import_pandas()

    data = []
    headers = []
    for i, column in enumerate(table.toArray()):
        data.append(column.toArray())
        headers.append(str(table.getColumnHeader(i)))
    for j in range(len(data)):
        data[j] = to_python(data[j])
    df = pd.DataFrame(data).T
    df.columns = headers
    return df


def _pandas_to_table(df):
    if len(df.dtypes.unique()) > 1:
        TableClass = jimport("org.scijava.table.DefaultGenericTable")
    else:
        table_type = df.dtypes.unique()[0]
        if table_type.name.startswith("float"):
            TableClass = jimport("org.scijava.table.DefaultFloatTable")
        elif table_type.name.startswith("int"):
            TableClass = jimport("org.scijava.table.DefaultIntTable")
        elif table_type.name.startswith("bool"):
            TableClass = jimport("org.scijava.table.DefaultBoolTable")
        else:
            msg = "The type '{}' is not supported.".format(table_type.name)
            raise Exception(msg)

    table = TableClass(*df.shape[::-1])

    for c, column_name in enumerate(df.columns):
        table.setColumnHeader(c, column_name)

    for i, (_, row) in enumerate(df.iterrows()):
        for c, value in enumerate(row):
            header = df.columns[c]
            table.set(header, i, to_java(value))

    return table


# -- JVM startup callbacks --

# NB: These must be performed last, because if this class is imported after the
# JVM is already running -- for example, if we are running in Jep mode, where
# Python is started from inside the JVM -- then these functions execute the
# callbacks immediately, which means the involved functions must be defined and
# functional at this point.


def _initialize_converters():
    for converter in _stock_java_converters():
        _add_converter(converter, java_converters)
    for converter in _stock_py_converters():
        _add_converter(converter, py_converters)


when_jvm_starts(_initialize_converters)
