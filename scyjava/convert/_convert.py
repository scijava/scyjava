# General-purpose utility methods for Python <-> Java type conversion.

import collections.abc
import jpype
import jpype.imports
from jpype.types import *

# Initialize JPype JVM
jpype.startJVM()

# EE: Not sure if these will still be needed after switch to JPype
from ._pandas import table_to_pandas
from ._pandas import pandas_to_table

# Java imports:
from java.lang import String
from java.lang import Boolean
from java.lang import Integer
from java.lang import Long
from java.math import BigInteger
from java.lang import Float
from java.lang import Double
from java.math import BigDecimal
from java.util import LinkedHashMap
from java.util import LinkedHashSet
from java.util import ArrayList

# -- Python to Java --

# Adapted from code posted by vslotman on GitHub:
# https://github.com/kivy/pyjnius/issues/217#issue-145981070

def isjava(data):
    # NOTE: removed jnius.MetaJavaClass and jnius.PythonJavaClass -- metajavaclass should 
    # be covered by jpype.JClass, I don't think jpype supports python --> java class implementation

    """Return whether the given data object is a Java object."""
    return isinstance(data, jpype.JClass)
    
def jclass(data):
    """
    Obtain a Java class object.

    :param data: The object from which to glean the class.
    Supported types include:
    A. Name of a class to look up, analogous to
    Class.forName("java.lang.String");
    B. A jnius.MetaJavaClass object e.g. from jnius.autoclass, analogous to
    String.class;
    C. A jnius.JavaClass object e.g. instantiated from a jnius.MetaJavaClass,
    analogous to "Hello".getClass().
    :returns: A java.lang.Class object, suitable for use with reflection.
    :raises TypeError: if the argument is not one of the aforementioned types.
    """

    # import the java class
    data_str = data
    data = jpype.JClass(data)

    if isinstance(data, jpype.JClass):
        print('[DEBUG] Class: {0} JClass: {1}'.format(data_str, isinstance(data, jpype.JClass(data))))
        return data.getClass()
    #if isinstance(data, jnius.MetaJavaClass):
    #    return jnius.find_javaclass(data.__name__)
    #if isinstance(data, str):
    #    return jnius.find_javaclass(data)
    raise TypeError('Cannot glean class from data of type: ' + str(type(data)))


def jstacktrace(exc):
    """
    Extract the Java-side stack trace from a wrapped Java exception.

    Example of usage:

        from jnius import autoclass
        try:
            Integer = autoclass('java.lang.Integer')
            nan = Integer.parseInt('not a number')
        except Exception as exc:
            print(jstacktrace(exc))

    :param exc: The JavaException from which to extract the stack trace.
    :returns: A multi-line string containing the stack trace, or empty string
    if no stack trace could be extracted.
    """
    if not hasattr(exc, 'classname') or exc.classname is None:
        return str(exc)
    return '' if not exc.stacktrace else '\n\tat '.join(exc.stacktrace)


def to_java(data):
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

    if data is None:
        return None

    if isjava(data):
        return data

    if isinstance(data, str):
        return String(data.encode('utf-8'), 'utf-8')

    if isinstance(data, bool):
        return Boolean(data)

    if isinstance(data, int):
        if data <= Integer.MAX_VALUE:
            return Integer(data)
        elif data <= Long.MAX_VALUE:
            return Long(data)
        else:
            return BigInteger(str(data))

    if isinstance(data, float):
        if data <= Float.MAX_VALUE:
            return Float(data)
        elif data <= Double.MAX_VALUE:
            return Double(data)
        else:
            return BigDecimal(str(data))

    # Trying to get the type without importing Pandas.
    if type(data).__name__ == 'DataFrame':
        return pandas_to_table(data)

    if isinstance(data, collections.abc.Mapping):
        jmap = LinkedHashMap()
        for k, v in data.items():
            jk = to_java(k)
            jv = to_java(v)
            jmap.put(jk, jv)
        return jmap

    if isinstance(data, collections.abc.Set):
        jset = LinkedHashSet()
        for item in data:
            jitem = to_java(item)
            jset.add(jitem)
        return jset

    if isinstance(data, collections.abc.Iterable):
        jlist = ArrayList()
        for item in data:
            jitem = to_java(item)
            jlist.add(jitem)
        return jlist

    raise TypeError('Unsupported type: ' + str(type(data)))

# -- Java to Python --

BooleanClass    = jclass('java.lang.Boolean')
ByteClass       = jclass('java.lang.Byte')
CharacterClass  = jclass('java.lang.Character')
DoubleClass     = jclass('java.lang.Double')
FloatClass      = jclass('java.lang.Float')
IntegerClass    = jclass('java.lang.Integer')
LongClass       = jclass('java.lang.Long')
ShortClass      = jclass('java.lang.Short')
VoidClass       = jclass('java.lang.Void')

BigIntegerClass = jclass('java.math.BigInteger')
BigDecimalClass = jclass('java.math.BigDecimal')
StringClass     = jclass('java.lang.String')

ObjectClass     = jclass('java.lang.Object')
IterableClass   = jclass('java.lang.Iterable')
CollectionClass = jclass('java.util.Collection')
IteratorClass   = jclass('java.util.Iterator')
ListClass       = jclass('java.util.List')
MapClass        = jclass('java.util.Map')
SetClass        = jclass('java.util.Set')


def _jstr(data):
    if isinstance(data, JavaObject):
        return str(data)
    # NB: We want Python strings to render in single quotes.
    return '{!r}'.format(data)


class JavaObject():
    def __init__(self, jobj, intended_class=ObjectClass):
        if not intended_class.isInstance(jobj):
            raise TypeError('Not a ' + intended_class.getName() + ': ' + jclass(jobj).getName())
        self.jobj = jobj

    def __str__(self):
        return _jstr(self.jobj)


class JavaIterable(JavaObject, collections.abc.Iterable):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, IterableClass)

    def __iter__(self):
        return to_python(self.jobj.iterator())

    def __str__(self):
        return '[' + ', '.join(_jstr(v) for v in self) + ']'


class JavaCollection(JavaIterable, collections.abc.Collection):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, CollectionClass)

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
        JavaObject.__init__(self, jobj, IteratorClass)

    def __next__(self):
        if self.jobj.hasNext():
            # NB: Even if an element cannot be converted,
            # we still want to support Pythonic iteration.
            return to_python(self.jobj.next(), gentle=True)
        raise StopIteration


class JavaList(JavaCollection, collections.abc.MutableSequence):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, ListClass)

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
        JavaObject.__init__(self, jobj, MapClass)

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
        JavaObject.__init__(self, jobj, SetClass)

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


def to_python(data, gentle=False):
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
    if not isjava(data):
        return data

    if BooleanClass.isInstance(data):
        return data.booleanValue()
    if ByteClass.isInstance(data):
        return data.byteValue()
    if CharacterClass.isInstance(data):
        return data.toString()
    if DoubleClass.isInstance(data):
        return data.doubleValue()
    if FloatClass.isInstance(data):
        return data.floatValue()
    if IntegerClass.isInstance(data):
        return data.intValue()
    if LongClass.isInstance(data):
        return data.longValue()
    if ShortClass.isInstance(data):
        return data.shortValue()
    if VoidClass.isInstance(data):
        return None

    if BigIntegerClass.isInstance(data):
        return int(data.toString())
    if BigDecimalClass.isInstance(data):
        return float(data.toString())
    if StringClass.isInstance(data):
        return data.toString()

    try:
        if jclass('org.scijava.table.Table').isInstance(data):
            return table_to_pandas(data)
    except:
        # No worries if scijava-table is not available.
        pass

    if ListClass.isInstance(data):
        return JavaList(data)
    if MapClass.isInstance(data):
        return JavaMap(data)
    if SetClass.isInstance(data):
        return JavaSet(data)
    if CollectionClass.isInstance(data):
        return JavaCollection(data)
    if IterableClass.isInstance(data):
        return JavaIterable(data)
    if IteratorClass.isInstance(data):
        return JavaIterator(data)

    if gentle:
        return data
    raise TypeError('Unsupported data type: ' + str(type(data)))
