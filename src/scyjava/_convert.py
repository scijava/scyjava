"""
The scyjava conversion subsystem, and built-in conversion functions.
"""

import collections
import typing
from pathlib import Path
from typing import Any, Callable, NamedTuple

from jpype import JArray, JBoolean, JByte, JChar, JDouble, JFloat, JInt, JLong, JShort

from ._java import JavaClasses, isjava, jclass, jimport, start_jvm


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


# -- Python to Java --

# Adapted from code posted by vslotman on GitHub:
# https://github.com/kivy/pyjnius/issues/217#issue-145981070


def _raise_type_exception(obj: Any):
    raise TypeError("Unsupported type: " + str(type(obj)))


def _convertMap(obj: collections.abc.Mapping):
    jmap = _jc.LinkedHashMap()
    for k, v in obj.items():
        jk = to_java(k)
        jv = to_java(v)
        jmap.put(jk, jv)
    return jmap


def _convertSet(obj: collections.abc.Set):
    jset = _jc.LinkedHashSet()
    for item in obj:
        jitem = to_java(item)
        jset.add(jitem)
    return jset


def _convertIterable(obj: collections.abc.Iterable):
    jlist = _jc.ArrayList()
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
    java_converters.append(converter)


def to_java(obj: Any) -> Any:
    """
    Recursively convert a Python object to a Java object.

    Supported types include:
    * str -> String
    * bool -> Boolean
    * int -> Integer, Long or BigInteger as appropriate
    * float -> Float, Double or BigDecimal as appropriate
    * dict -> LinkedHashMap
    * set -> LinkedHashSet
    * list -> ArrayList

    :param obj: The Python object to convert.
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
        # None -> None
        Converter(
            predicate=lambda obj: obj is None,
            converter=lambda obj: None,
            priority=Priority.EXTREMELY_HIGH + 1,
        ),
        # Java object identity
        Converter(
            predicate=isjava,
            converter=lambda obj: obj,
            priority=Priority.EXTREMELY_HIGH,
        ),
        # str -> java.lang.String
        Converter(
            predicate=lambda obj: isinstance(obj, str),
            converter=lambda obj: _jc.String(obj.encode("utf-8"), "utf-8"),
        ),
        # bool -> java.lang.Boolean
        Converter(
            predicate=lambda obj: isinstance(obj, bool),
            converter=_jc.Boolean,
        ),
        # int -> java.lang.Integer
        Converter(
            predicate=lambda obj: isinstance(obj, int)
            and _jc.Integer.MIN_VALUE <= obj <= _jc.Integer.MAX_VALUE,
            converter=_jc.Integer,
        ),
        # int -> java.lang.Long
        Converter(
            predicate=lambda obj: isinstance(obj, int)
            and _jc.Long.MIN_VALUE <= obj <= _jc.Long.MAX_VALUE,
            converter=_jc.Long,
            priority=Priority.NORMAL - 1,
        ),
        # int -> java.math.BigInteger
        Converter(
            predicate=lambda obj: isinstance(obj, int),
            converter=lambda obj: _jc.BigInteger(str(obj)),
            priority=Priority.NORMAL - 2,
        ),
        # float -> java.lang.Float
        Converter(
            predicate=lambda obj: isinstance(obj, float)
            and _jc.Float.MIN_VALUE <= obj <= _jc.Float.MAX_VALUE,
            converter=_jc.Float,
        ),
        # float -> java.lang.Double
        Converter(
            predicate=lambda obj: isinstance(obj, float)
            and _jc.Double.MAX_VALUE <= obj <= _jc.Double.MAX_VALUE,
            converter=_jc.Double,
            priority=Priority.NORMAL - 1,
        ),
        # float -> java.math.BigDecimal
        Converter(
            predicate=lambda obj: isinstance(obj, float),
            converter=lambda obj: _jc.BigDecimal(str(obj)),
            priority=Priority.NORMAL - 2,
        ),
        # pathlib.Path -> java.nio.file.Path
        Converter(
            predicate=lambda obj: isinstance(obj, Path),
            converter=lambda obj: _jc.Paths.get(str(obj)),
            priority=Priority.NORMAL + 1,
        ),
        # pandas.DataFrame -> org.scijava.table.Table
        Converter(
            predicate=lambda obj: type(obj).__name__ == "DataFrame",
            converter=_pandas_to_table,
            priority=Priority.NORMAL + 1,
        ),
        # collections.abc.Mapping -> java.util.Map
        Converter(
            predicate=lambda obj: isinstance(obj, collections.abc.Mapping),
            converter=_convertMap,
        ),
        # collections.abc.Set -> java.util.Set
        Converter(
            predicate=lambda obj: isinstance(obj, collections.abc.Set),
            converter=_convertSet,
        ),
        # collections.abc.Iterable -> java.util.Iterable
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
            intended_class = _jc.Object
        if not isinstance(jobj, intended_class):
            raise TypeError(
                f"Not a {intended_class.getName()}: {jclass(jobj).getName()}"
            )
        self.jobj = jobj

    def __str__(self):
        return _jstr(self.jobj)


class JavaIterable(JavaObject, collections.abc.Iterable):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, _jc.Iterable)

    def __iter__(self):
        return to_python(self.jobj.iterator())

    def __str__(self):
        return "[" + ", ".join(_jstr(v) for v in self) + "]"


class JavaCollection(JavaIterable, collections.abc.Collection):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, _jc.Collection)

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
        JavaObject.__init__(self, jobj, _jc.Iterator)

    def __next__(self):
        if self.jobj.hasNext():
            # NB: Even if an element cannot be converted,
            # we still want to support Pythonic iteration.
            return to_python(self.jobj.next(), gentle=True)
        raise StopIteration


class JavaList(JavaCollection, collections.abc.MutableSequence):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, _jc.List)

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
        JavaObject.__init__(self, jobj, _jc.Map)

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
        JavaObject.__init__(self, jobj, _jc.Set)

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
    py_converters.append(converter)


def to_python(data: Any, gentle: bool = False) -> Any:
    """
    Recursively convert a Java object to a Python object.

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

    :param data: The Java object to convert.
    :param gentle: If set, and the type cannot be converted, leaves
                   the data alone rather than raising a TypeError.
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

    converters = [
        # Other (Exceptional) converter
        Converter(
            predicate=lambda obj: True,
            converter=_raise_type_exception,
            priority=Priority.EXTREMELY_LOW - 1,
        ),
        # Python object identity
        Converter(
            predicate=lambda obj: not isjava(obj),
            converter=lambda obj: obj,
            priority=Priority.EXTREMELY_HIGH,
        ),
        # JBoolean -> bool
        Converter(
            predicate=lambda obj: isinstance(obj, JBoolean),
            converter=bool,
            priority=Priority.NORMAL + 1,
        ),
        # JByte/JInt/JLong/JShort -> int
        Converter(
            predicate=lambda obj: isinstance(obj, (JByte, JInt, JLong, JShort)),
            converter=int,
            priority=Priority.NORMAL + 1,
        ),
        # JDouble/JFloat -> float
        Converter(
            predicate=lambda obj: isinstance(obj, (JDouble, JFloat)),
            converter=float,
            priority=Priority.NORMAL + 1,
        ),
        # JChar -> str
        Converter(
            predicate=lambda obj: isinstance(obj, JChar),
            converter=str,
            priority=Priority.NORMAL + 1,
        ),
        # java.lang.Boolean -> bool
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Boolean),
            converter=lambda obj: obj.booleanValue(),
        ),
        # java.lang.Byte -> int
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Byte),
            converter=lambda obj: int(obj.byteValue()),
        ),
        # java.lang.Character -> str
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Character),
            converter=lambda obj: str,
        ),
        # java.lang.Double -> float
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Double),
            converter=lambda obj: float(obj.doubleValue()),
        ),
        # java.lang.Float -> float
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Float),
            converter=lambda obj: float(obj.floatValue()),
        ),
        # java.lang.Integer -> int
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Integer),
            converter=lambda obj: int(obj.intValue()),
        ),
        # java.lang.Long -> int
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Long),
            converter=lambda obj: int(obj.longValue()),
        ),
        # java.lang.Short -> int
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Short),
            converter=lambda obj: int(obj.shortValue()),
        ),
        # java.lang.String -> str
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.String),
            converter=lambda obj: str(obj),
        ),
        # java.math.BigInteger -> int
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.BigInteger),
            converter=lambda obj: int(str(obj)),
        ),
        # java.math.BigDecimal -> float
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.BigDecimal),
            converter=lambda obj: float(str(obj)),
        ),
        # java.util.List -> scyjava.JavaList (list-like)
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.List),
            converter=JavaList,
        ),
        # java.util.Map -> scyjava.JavaMap (dict-like)
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Map),
            converter=JavaMap,
        ),
        # java.util.Set -> scyjava.JavaSet (set-like)
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Set),
            converter=JavaSet,
        ),
        # java.util.Collection -> scyjava.JavaCollection (collections.abc.Collection)
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Collection),
            converter=JavaCollection,
            priority=Priority.NORMAL - 1,
        ),
        # java.lang.Iterable -> scyjava.JavaIterable (collections.abc.Iterable)
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Iterable),
            converter=JavaIterable,
            priority=Priority.NORMAL - 1,
        ),
        # java.util.Iterator -> scyjava.JavaIterator (collections.abc.Iterator)
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Iterator),
            converter=JavaIterator,
            priority=Priority.NORMAL - 1,
        ),
        # java.nio.file.Path -> pathlib.Path
        Converter(
            predicate=lambda obj: isinstance(obj, _jc.Path),
            converter=lambda obj: Path(str(obj)),
            priority=Priority.NORMAL + 1,
        ),
        # JArray -> list
        Converter(
            predicate=lambda obj: isinstance(obj, JArray),
            converter=lambda obj: [to_python(o) for o in obj],
            priority=Priority.VERY_LOW,
        ),
    ]

    if _import_numpy():
        # primitive array -> numpy.ndarray
        converters.append(
            Converter(
                predicate=_supports_jarray_to_ndarray,
                converter=_jarray_to_ndarray,
            )
        )

    if _import_pandas():
        # org.scijava.table.Table -> pandas.DataFrame
        converters.append(
            Converter(
                predicate=_is_table,
                converter=_convert_table,
            )
        )

    return converters


###############################
# Java array -> NumPy ndarray #
###############################


def _jarray_to_ndarray(jarr):
    """
    Convert the given Java primitive array into a NumPy ndarray.

    :param jarr: The Java primitive array
    :return: The converted NumPy ndarray
    """
    np = _import_numpy()
    assert _supports_jarray_to_ndarray(jarr)
    element_type = _jarray_element_type(jarr)
    # fmt: off
    jarraytype_map = {
        JBoolean: np.bool8,
        JByte:    np.int8,
        # JChar:  np.???,
        JDouble:  np.float64,
        JFloat:   np.float32,
        JInt:     np.int32,
        JLong:    np.int64,
        JShort:   np.int16,
    }
    # fmt: on
    dtype = jarraytype_map[element_type]
    ndarray = np.frombuffer(memoryview(jarr), dtype=dtype)
    return ndarray.reshape(_jarray_shape(jarr))


def _supports_jarray_to_ndarray(obj):
    """
    Return True iff the given object is convertible to a NumPy ndarray
    via the _jarray_to_ndarray function.

    :param obj: The object to check for convertibility
    :return: True iff conversion to a NumPy ndarray is possible
    """
    element_type = _jarray_element_type(obj)
    return element_type in (JBoolean, JByte, JDouble, JFloat, JInt, JLong, JShort)


def _jarray_element_type(jarr):
    if not isinstance(jarr, JArray):
        return None
    element = jarr
    while isinstance(element, JArray):
        element = element[0]
    return type(element)


def _jarray_shape(jarr):
    if not isinstance(jarr, JArray):
        return None
    shape = []
    element = jarr
    while isinstance(element, JArray):
        shape.append(len(element))
        element = element[0]
    return shape


def _import_numpy():
    try:
        import numpy as np

        return np
    except ImportError as e:
        msg = "The NumPy library is missing (https://numpy.org/). "
        msg += "Please install it before using this function."
        raise RuntimeError(msg) from e


######################################
# SciJava table <-> pandas DataFrame #
######################################


def _is_table(obj: Any) -> bool:
    """Check if obj is a table."""
    try:
        return isinstance(obj, jimport("org.scijava.table.Table"))
    except BaseException:
        # No worries if scijava-table is not available.
        pass


def _convert_table(obj: Any):
    """Convert obj to a table."""
    try:
        return _table_to_pandas(obj)
    except BaseException:
        # No worries if scijava-table is not available.
        pass


def _import_pandas():
    try:
        import pandas as pd

        return pd
    except ImportError as e:
        msg = "The Pandas library is missing (http://pandas.pydata.org/). "
        msg += "Please install it before using this function."
        raise RuntimeError(msg) from e


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


# fmt: off
class _JavaClasses(JavaClasses):
    @JavaClasses.java_import
    def Boolean(self):       return "java.lang.Boolean"        # noqa: E272
    @JavaClasses.java_import
    def Byte(self):          return "java.lang.Byte"           # noqa: E272
    @JavaClasses.java_import
    def Character(self):     return "java.lang.Character"      # noqa: E272
    @JavaClasses.java_import
    def Double(self):        return "java.lang.Double"         # noqa: E272
    @JavaClasses.java_import
    def Float(self):         return "java.lang.Float"          # noqa: E272
    @JavaClasses.java_import
    def Integer(self):       return "java.lang.Integer"        # noqa: E272
    @JavaClasses.java_import
    def Iterable(self):      return "java.lang.Iterable"       # noqa: E272
    @JavaClasses.java_import
    def Long(self):          return "java.lang.Long"           # noqa: E272
    @JavaClasses.java_import
    def Object(self):        return "java.lang.Object"         # noqa: E272
    @JavaClasses.java_import
    def Short(self):         return "java.lang.Short"          # noqa: E272
    @JavaClasses.java_import
    def String(self):        return "java.lang.String"         # noqa: E272
    @JavaClasses.java_import
    def BigDecimal(self):    return "java.math.BigDecimal"     # noqa: E272
    @JavaClasses.java_import
    def BigInteger(self):    return "java.math.BigInteger"     # noqa: E272
    @JavaClasses.java_import
    def Path(self):          return "java.nio.file.Path"       # noqa: E272
    @JavaClasses.java_import
    def Paths(self):         return "java.nio.file.Paths"      # noqa: E272
    @JavaClasses.java_import
    def ArrayList(self):     return "java.util.ArrayList"      # noqa: E272
    @JavaClasses.java_import
    def Collection(self):    return "java.util.Collection"     # noqa: E272
    @JavaClasses.java_import
    def Iterator(self):      return "java.util.Iterator"       # noqa: E272
    @JavaClasses.java_import
    def LinkedHashMap(self): return "java.util.LinkedHashMap"  # noqa: E272
    @JavaClasses.java_import
    def LinkedHashSet(self): return "java.util.LinkedHashSet"  # noqa: E272
    @JavaClasses.java_import
    def List(self):          return "java.util.List"           # noqa: E272
    @JavaClasses.java_import
    def Map(self):           return "java.util.Map"            # noqa: E272
    @JavaClasses.java_import
    def Set(self):           return "java.util.Set"            # noqa: E272
# fmt: on


_jc = _JavaClasses()
