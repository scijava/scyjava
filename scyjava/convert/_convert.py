# General-purpose utility methods for Python <-> Java type conversion.

import jnius, collections

String        = jnius.autoclass('java.lang.String')
Boolean       = jnius.autoclass('java.lang.Boolean')
Integer       = jnius.autoclass('java.lang.Integer')
Long          = jnius.autoclass('java.lang.Long')
BigInteger    = jnius.autoclass('java.math.BigInteger')
Float         = jnius.autoclass('java.lang.Float')
Double        = jnius.autoclass('java.lang.Double')
BigDecimal    = jnius.autoclass('java.math.BigDecimal')
LinkedHashMap = jnius.autoclass('java.util.LinkedHashMap')
LinkedHashSet = jnius.autoclass('java.util.LinkedHashSet')
ArrayList     = jnius.autoclass('java.util.ArrayList')

# -- Python to Java --

# Adapted from code posted by vslotman on GitHub:
# https://github.com/kivy/pyjnius/issues/217#issue-145981070

def isjava(data):
    """Return whether the given data object is a Java object."""
    return isinstance(data, jnius.JavaClass) or isinstance(data, jnius.MetaJavaClass)


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
    if isinstance(data, jnius.JavaClass):
        return data.getClass()
    if isinstance(data, jnius.MetaJavaClass):
        return jnius.find_javaclass(data.__name__)
    if isinstance(data, str):
        return jnius.find_javaclass(data)
    raise TypeError('Cannot glean class from data of type: ' + str(type(data)))


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

    if isinstance(data, collections.Mapping):
        jmap = LinkedHashMap()
        for k, v in data.items():
            jk = to_java(k)
            jv = to_java(v)
            jmap.put(jk, jv)
        return jmap

    if isinstance(data, collections.Set):
        jset = LinkedHashSet()
        for item in data:
            jitem = to_java(item)
            jset.add(jitem)
        return jset

    if isinstance(data, collections.Iterable):
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


class JavaIterable(JavaObject, collections.Iterable):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, IterableClass)

    def __iter__(self):
        return to_python(self.jobj.iterator())

    def __str__(self):
        return '[' + ', '.join(_jstr(v) for v in self) + ']'


class JavaCollection(JavaIterable, collections.Collection):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, CollectionClass)

    def __contains__(self, item):
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


class JavaIterator(JavaObject, collections.Iterator):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, IteratorClass)

    def __next__(self):
        if self.jobj.hasNext():
            return to_python(self.jobj.next())
        raise StopIteration


class JavaList(JavaCollection, collections.MutableSequence):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, ListClass)

    def __getitem__(self, key):
        return to_python(self.jobj.get(key))

    def __setitem__(self, key, value):
        return to_python(self.jobj.set(key, value))

    def __delitem__(self, key):
        return to_python(self.jobj.remove(key))

    def insert(self, index, object):
        return to_python(self.jobj.set(index, object))


class JavaMap(JavaObject, collections.MutableMapping):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, MapClass)

    def __getitem__(self, key):
        return to_python(self.jobj.get(to_java(key)))

    def __setitem__(self, key, value):
        return to_python(self.jobj.put(to_java(key), to_java(value)))

    def __delitem__(self, key):
        return to_python(self.jobj.remove(to_python(key)))

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


class JavaSet(JavaCollection, collections.MutableSet):
    def __init__(self, jobj):
        JavaObject.__init__(self, jobj, SetClass)

    def add(self, item):
        return to_python(self.jobj.add(to_java(item)))

    def discard(self, item):
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


def to_python(data):
    """
    Recursively convert a Java object to a Python object.
    :param data: The Java object to convert.
    Supported types include:
    * String, Character -> str
    * Boolean -> bool
    * Byte, Short, Integer, Long, BigInteger -> int
    * Float, Double, BigDecimal -> float
    * Map -> collections.MutableMapping (dict-like)
    * Set -> collections.MutableSet (set-like)
    * List -> collections.MutableSequence (list-like)
    * Collection -> collections.Collection
    * Iterable -> collections.Iterable
    * Iterator -> collections.Iterator
    :returns: A corresponding Python object with the same contents.
    :raises TypeError: if the argument is not one of the aforementioned types.
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

    raise TypeError('Unsupported data type: ' + str(type(data)))
