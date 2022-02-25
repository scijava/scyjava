import atexit
import collections.abc
import traceback
from typing import Any, Callable, NamedTuple
import typing
import jgo
import jpype
import jpype.config
import logging
import os
import re
import scyjava.config
import subprocess
from pathlib import Path
from jpype.types import *
from _jpype import _JObject

_logger = logging.getLogger(__name__)


# -- JVM setup --

_startup_callbacks = []
_shutdown_callbacks = []


def jvm_version():
    """
    Gets the version of the JVM as a tuple, with each dot-separated digit as one element.
    Characters in the version string beyond only numbers and dots are ignored, in line
    with the java.version system property.

    Examples:
    * OpenJDK 17.0.1 -> [17, 0, 1]
    * OpenJDK 11.0.9.1-internal -> [11, 0, 9, 1]
    * OpenJDK 1.8.0_312 -> [1, 8, 0]

    If the JVM is already started, this function should return the equivalent of:
       jimport('java.lang.System').getProperty('java.version').split('.')

    In case the JVM is not started yet, a best effort is made to deduce the
    version from the environment without actually starting up the JVM in-process.
    If the version cannot be deduced, a RuntimeError with the cause is raised.
    """
    jvm_version = jpype.getJVMVersion()
    if jvm_version and jvm_version[0]:
        # JPype already knew the version.
        # JVM is probably already started.
        # Or JPype got smarter since 1.3.0.
        return jvm_version

    # JPype was clueless, which means the JVM has probably not started yet.
    # Let's look for a java executable, and ask it directly with 'java -version'.

    default_jvm_path = jpype.getDefaultJVMPath()
    if not default_jvm_path:
        raise RuntimeError("Cannot glean the default JVM path")

    p = Path(default_jvm_path)
    if not p.exists():
        raise RuntimeError(f"Invalid default JVM path: {p}")

    java = None
    for _ in range(3): # The bin folder is always <=3 levels up from libjvm.
        p = p.parent
        if p.name == 'lib':
            java = p.parent / 'bin' / 'java'
        elif p.name == 'bin':
            java = p / 'java'

        if java is not None:
            if os.name == 'nt':
                # Good ol' Windows! Nothing beats Windows.
                java = java.with_suffix('.exe')
            if not java.is_file():
                raise RuntimeError(f"No ../bin/java found at: {p}")
            break
    if java is None:
        raise RuntimeError(f"No java executable found inside: {p}")

    version = subprocess.check_output([java, '-version'], stderr=subprocess.STDOUT).decode()
    m = re.match('.*version "(([0-9]+\\.)+[0-9]+)', version)
    if not m:
        raise RuntimeError(f"Inscrutable java command output:\n{version}")

    return tuple(map(int, m.group(1).split('.')))


def start_jvm(options=scyjava.config.get_options()):
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
        _logger.debug('The JVM is already running.')
        return

    # retrieve endpoint and repositories from scyjava config
    endpoints = scyjava.config.endpoints
    repositories = scyjava.config.get_repositories()

    # use the logger to notify user that endpoints are being added
    _logger.debug('Adding jars from endpoints {0}'.format(endpoints))

    # get endpoints and add to JPype class path
    if len(endpoints) > 0:
        endpoints = endpoints[:1] + sorted(endpoints[1:])
        _logger.debug('Using endpoints %s', endpoints)
        _, workspace = jgo.resolve_dependencies(
            '+'.join(endpoints),
            m2_repo=scyjava.config.get_m2_repo(),
            cache_dir=scyjava.config.get_cache_dir(),
            manage_dependencies=scyjava.config.get_manage_deps(),
            repositories=repositories,
            verbose=scyjava.config.get_verbose()
        )
        jpype.addClassPath(os.path.join(workspace, '*'))

    # initialize JPype JVM
    jpype.startJVM(*options, interrupt=True)

    # replace JPype/JVM shutdown handling with our own
    jpype.config.onexit = False
    jpype.config.free_resources = False
    atexit.register(shutdown_jvm)

    # grab needed Java classes
    global Boolean; Boolean = jimport('java.lang.Boolean')
    global Byte; Byte = jimport('java.lang.Byte')
    global Character; Character = jimport('java.lang.Character')
    global Double; Double = jimport('java.lang.Double')
    global Float; Float = jimport('java.lang.Float')
    global Integer; Integer = jimport('java.lang.Integer')
    global Iterable; Iterable = jimport('java.lang.Iterable')
    global Long; Long = jimport('java.lang.Long')
    global Object; Object = jimport('java.lang.Object')
    global Short; Short = jimport('java.lang.Short')
    global String; String = jimport('java.lang.String')
    global Void; Void = jimport('java.lang.Void')
    global BigDecimal; BigDecimal = jimport('java.math.BigDecimal')
    global BigInteger; BigInteger = jimport('java.math.BigInteger')
    global ArrayList; ArrayList = jimport('java.util.ArrayList')
    global Collection; Collection = jimport('java.util.Collection')
    global Iterator; Iterator = jimport('java.util.Iterator')
    global LinkedHashMap; LinkedHashMap = jimport('java.util.LinkedHashMap')
    global LinkedHashSet; LinkedHashSet = jimport('java.util.LinkedHashSet')
    global List; List = jimport('java.util.List')
    global Map; Map = jimport('java.util.Map')
    global Set; Set = jimport('java.util.Set')

    # invoke registered callback functions
    for callback in _startup_callbacks:
        callback()

def shutdown_jvm():
    """Shutdown the JVM.

    Shutdown the JVM. Set the jpype .config.destroy_jvm flag to true
    to ask JPype to destory the JVM itself. Note that enabling 
    jpype.config.destroy_jvm can lead to delayed shutdown times while
    the JVM is waiting for threads to finish.
    """
    # invoke registered shutdown callback functions
    for callback in _shutdown_callbacks:
        try:
            callback()
        except Exception as e:
            print(f"Exception during shutdown callback: {e}")
            
    # clean up remaining awt windows
    Window = jimport('java.awt.Window')
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
    Registers a function to be called when the JVM starts (or immediately).
    This is useful to defer construction of Java-dependent data structures
    until the JVM is known to be available. If the JVM has already been
    started, the function executes immediately.

    :param f: Function to invoke when scyjava.start_jvm() is called.
    """
    global _shutdown_callbacks
    _shutdown_callbacks.append(f)


# -- Utility functions --

def get_version(java_class):
    """Return the version of a Java class. """
    VersionUtils = jimport('org.scijava.util.VersionUtils')
    version = VersionUtils.getVersion(java_class)
    return version

def compare_version(version, java_class_version):
    """
    Return a boolean on a version comparison. True is returned
    if the Java class version is higher than the specified version. False
    is returned if the specified version is higher than the Java class version.
    """
    VersionUtils = jimport('org.scijava.util.VersionUtils')
    comparison = VersionUtils.compare(version, java_class_version) < 0
    return comparison

# -- Type Conversion Utilities --

# TODO: It would be cool to just use org.scijava.priority.Priority.
# Unfortunately, we cannot do that without bringing in all of SJC.
# Once SciJava 3 is mainstream, we could use a SciJava Priority module :)
class Priority:
    FIRST = 1E300
    EXTREMELY_HIGH = 1E6
    VERY_HIGH = 1E4
    HIGH = 1E2
    NORMAL = 0
    LOW = -1E2
    VERY_LOW = -1E4
    EXTREMELY_LOW = -1E6
    LAST = -1E300

class Converter(NamedTuple):
    predicate: Callable[[Any], bool]
    converter: Callable[[Any], Any]
    priority: float = Priority.NORMAL


def _convert(obj: Any, converters: typing.List[Converter]) -> Any:
    suitable_converters = filter(lambda c: c.predicate(obj), converters)
    prioritized = max(suitable_converters, key = lambda c: c.priority)
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
    raise TypeError('Cannot glean class from data of type: ' + str(type(data)))


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
        StringWriter = jimport('java.io.StringWriter')
        PrintWriter = jimport('java.io.PrintWriter')
        sw = StringWriter()
        exc.printStackTrace(PrintWriter(sw, True))
        return sw.toString()
    except:
        return ''


def _raise_type_exception(obj: Any):
    raise TypeError('Unsupported type: ' + str(type(obj)))
    

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


java_converters : typing.List[Converter] = []


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
            priority=Priority.EXTREMELY_LOW - 1
        ),
        # NoneType converter
        Converter(
            predicate=lambda obj: obj is None,
            converter=lambda obj: None,
            priority=Priority.EXTREMELY_HIGH + 1
        ),
        # Java identity converter
        Converter(
            predicate=isjava,
            converter=lambda obj: obj,
            priority=Priority.EXTREMELY_HIGH
        ),
        # String converter
        Converter(
            predicate=lambda obj: isinstance(obj, str), 
            converter=lambda obj: String(obj.encode('utf-8'), 'utf-8'),
        ),
        # Boolean converter
        Converter(
            predicate=lambda obj: isinstance(obj, bool),
            converter=Boolean,
        ),
        # Integer converter
        Converter(
            predicate=lambda obj: isinstance(obj, int) and obj <= Integer.MAX_VALUE and obj >= Integer.MIN_VALUE,
            converter= Integer,
        ),
        # Long converter
        Converter(
            predicate=lambda obj: isinstance(obj, int) and obj <= Long.MAX_VALUE,
            converter=Long,
            priority=Priority.NORMAL - 1
        ),
        # BigInteger converter
        Converter(
            predicate=lambda obj: isinstance(obj, int),
            converter=lambda obj: BigInteger(str(obj)),
            priority=Priority.NORMAL - 2
        ),
        # Float converter
        Converter(
            predicate=lambda obj: isinstance(obj, float) and obj <= Float.MAX_VALUE and obj >= Float.MIN_VALUE,
            converter= Float,
        ),
        # Double converter
        Converter(
            predicate=lambda obj: isinstance(obj, float) and obj <= Double.MAX_VALUE and obj >= Float.MIN_VALUE,
            converter=Double,
            priority=Priority.NORMAL - 1
        ),
        # BigDecimal converter
        Converter(
            predicate=lambda obj: isinstance(obj, float),
            converter=lambda obj: BigDecimal(str(obj)),
            priority=Priority.NORMAL - 2
        ),
        # Pandas table converter
        Converter(
            predicate=lambda obj: type(obj).__name__ == 'DataFrame',
            converter=_pandas_to_table,
            priority=Priority.NORMAL + 1
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
            priority=Priority.NORMAL -1
        ),
    ]


when_jvm_starts(
    lambda : [_add_converter(c, java_converters) for c in _stock_java_converters()]
)


# -- Java to Python --


def _jstr(data):
    if isinstance(data, JavaObject):
        return str(data)
    # NB: We want Python strings to render in single quotes.
    return '{!r}'.format(data)


class JavaObject():
    def __init__(self, jobj, intended_class=None):
        if intended_class is None:
            intended_class = Object
        if not isinstance(jobj, intended_class):
            raise TypeError('Not a ' + intended_class.getName() + ': ' + jclass(jobj).getName())
        self.jobj = jobj

    def __str__(self):
        return _jstr(self.jobj)


class JavaIterable(JavaObject, collections.abc.Iterable):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Iterable)

    def __iter__(self):
        return to_python(self.jobj.iterator())

    def __str__(self):
        return '[' + ', '.join(_jstr(v) for v in self) + ']'


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
        # NB: List.set(int, Object) returns inserted element, so be gentle here.
        return to_python(self.jobj.set(key, to_java(value)), gentle=True)

    def __delitem__(self, key):
        # NB: List.remove(Object) returns boolean, so no need for gentleness.
        return to_python(self.jobj.remove(to_java(key)))

    def insert(self, index, object):
        # NB: List.set(int, Object) returns inserted element, so be gentle here.
        return to_python(self.jobj.set(index, to_java(object)), gentle=True)


class JavaMap(JavaObject, collections.abc.MutableMapping):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, Map)

    def __getitem__(self, key):
        # NB: Even if an element cannot be converted,
        # we still want Pythonic access to elements.
        return to_python(self.jobj.get(to_java(key)), gentle=True)

    def __setitem__(self, key, value):
        # NB: Map.put(Object, Object) returns inserted value, so be gentle here.
        return to_python(self.jobj.put(to_java(key), to_java(value)), gentle=True)

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
                if not k in other or self[k] != other[k]:
                    return False
            return True
        except TypeError:
            return False

    def __str__(self):
        return '{' + ', '.join(_jstr(k) + ': ' + _jstr(v) for k,v in self.items()) + '}'


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
                if not k in other:
                    return False
            return True
        except TypeError:
            return False

    def __str__(self):
        return '{' + ', '.join(_jstr(v) for v in self) + '}'


py_converters : typing.List[Converter] = []


def add_py_converter(converter: Converter):
    """
    Adds a converter to the list used by to_python
    :param converter: A Converter from java to python
    """
    _add_converter(converter, py_converters)


def to_python(data: Any, gentle: bool =False) -> Any:
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
        if gentle: return data
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
            priority=Priority.EXTREMELY_LOW - 1
        ),
        # Java identity converter
        Converter(
            predicate=lambda obj: not isjava(obj),
            converter=lambda obj: obj,
            priority=Priority.EXTREMELY_HIGH
        ),
        # JBoolean converter
        Converter(
            predicate=lambda obj: isinstance(obj, JBoolean),
            converter=bool,
            priority=Priority.NORMAL + 1
        ),
        # JInt/JLong/JShort converter
        Converter(
            predicate=lambda obj: isinstance(obj, (JInt, JLong, JShort)),
            converter=int,
            priority=Priority.NORMAL + 1
        ),
        # JDouble/JFloat converter
        Converter(
            predicate=lambda obj: isinstance(obj, (JDouble, JFloat)),
            converter=float,
            priority=Priority.NORMAL + 1
        ),
        # JChar converter
        Converter(
            predicate=lambda obj: isinstance(obj, JChar),
            converter=str,
            priority=Priority.NORMAL + 1
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
            converter=lambda obj: float(obj.toString),
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
            priority=Priority.NORMAL -1
        ),
        # Iterable converter
        Converter(
            predicate=lambda obj: isinstance(obj, Iterable),
            converter=JavaIterable,
            priority=Priority.NORMAL -1
        ),
        # Iterator converter
        Converter(
            predicate=lambda obj: isinstance(obj, Iterator),
            converter=JavaIterator,
            priority=Priority.NORMAL - 1
        ),
        # JArray converter
        Converter(
            predicate=lambda obj: isinstance(obj, JArray),
            converter=lambda obj:[to_python(o) for o in obj],
            priority=Priority.VERY_LOW
        ),
    ]


when_jvm_starts(
    lambda : [_add_converter(c, py_converters) for c in _stock_py_converters()]
)


def _is_table(obj: Any) -> bool:
    """Checks if obj is a table"""
    try:
        return isinstance(obj, jimport('org.scijava.table.Table'))
    except:
        # No worries if scijava-table is not available.
        pass


def _convert_table(obj: Any):
    """Converts obj to a table."""
    try:
            return _table_to_pandas(obj)
    except:
        # No worries if scijava-table is not available.
        pass


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
    df = pd.DataFrame(data).T
    df.columns = headers
    return df


def _pandas_to_table(df):
    pd = _import_pandas()

    if len(df.dtypes.unique()) > 1:
        TableClass = jimport('org.scijava.table.DefaultGenericTable')
    else:
        table_type = df.dtypes.unique()[0]
        if table_type.name.startswith('float'):
            TableClass = jimport('org.scijava.table.DefaultFloatTable')
        elif table_type.name.startswith('int'):
            TableClass = jimport('org.scijava.table.DefaultIntTable')
        elif table_type.name.startswith('bool'):
            TableClass = jimport('org.scijava.table.DefaultBoolTable')
        else:
            msg = "The type '{}' is not supported.".format(table_type.name)
            raise Exception(msg)

    table = TableClass(*df.shape[::-1])

    for c, column_name in enumerate(df.columns):
        table.setColumnHeader(c, column_name)

    for i, (index, row) in enumerate(df.iterrows()):
        for c, value in enumerate(row):
            header = df.columns[c]
            table.set(header, i, to_java(value))

    return table
