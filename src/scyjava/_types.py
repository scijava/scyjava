"""
Utility functions for working with and reasoning about Java types.
"""

from typing import Any, Callable, Sequence, Tuple, Union

import jpype

from scyjava._jvm import jimport, jvm_started, start_jvm
from scyjava.config import Mode, mode


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
            @JavaClasses.java_import
            def String(self): return "java.lang.String"
            @JavaClasses.java_import
            def Integer(self): return "java.lang.Integer"
            # ... and many more ...

        jc = MyJavaClasses()

        def parse_number_with_java(s: "jc.String") -> "jc.Integer":
            return jc.Integer.parseInt(s)
    """

    def java_import(func: Callable[[], str]) -> property:
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


def jclass(data):
    """
    Obtain a Java class object.

    Supported types include:

    A. Name of a class to look up -- e.g. "java.lang.String" --
       which returns the equivalent of Class.forName("java.lang.String").

    B. A static-style class reference -- e.g. String --
       which returns the equivalent of String.class.

    C. A Java object -- e.g. foo --
       which returns the equivalent of foo.getClass().

    Note that if you pass a java.lang.Class object, you will get back Class.class,
    i.e. the Java class for the Class class. :-)

    :param data: The object from which to glean the class.
    :return: A java.lang.Class object, suitable for use with reflection.
    :raise TypeError: if the argument is not one of the aforementioned types.
    """
    if isinstance(data, str):
        # Name of a class -- case (A) above.
        return jclass(jimport(data))

    if mode == Mode.JPYPE:
        start_jvm()
        if isinstance(data, jpype.JClass):
            # JPype object representing a static-style class -- case (B) above.
            return data.class_
    elif mode == Mode.JEP:
        if str(type(data.getClass())) == "<class 'jep.PyJClass'>":
            # Jep object representing a static-style class -- case (B) above.
            raise ValueError(
                "Jep does not support Java class objects "
                + "-- see https://github.com/ninia/jep/issues/405"
            )

    # A Java object -- case (C) above.
    if jinstance(data, "java.lang.Object"):
        return data.getClass()

    raise TypeError("Cannot glean class from data of type: " + str(type(data)))


def jstacktrace(exc) -> str:
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
    :return: A multi-line string containing the stack trace, or empty string
    if no stack trace could be extracted.
    """
    try:
        StringWriter = jimport("java.io.StringWriter")
        PrintWriter = jimport("java.io.PrintWriter")
        sw = StringWriter()
        exc.printStackTrace(PrintWriter(sw, True))
        return str(sw)
    except BaseException:
        return ""


def isjava(data) -> bool:
    """Return whether the given data object is a Java object."""
    if mode == Mode.JEP:
        return jinstance(data, "java.lang.Object")

    assert mode == Mode.JPYPE
    return isinstance(data, jpype.JClass) or isinstance(data, jpype.JObject)


def is_jbyte(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Byte")


def is_jshort(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Short")


def is_jinteger(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Integer")


def is_jlong(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Long")


def is_jfloat(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Float")


def is_jdouble(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Double")


def is_jboolean(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Boolean")


def is_jcharacter(the_type: type) -> bool:
    return _is_jtype(the_type, "java.lang.Character")


def is_jarray(data: Any) -> bool:
    """Return whether the given data object is a Java array."""
    if mode == Mode.JEP:
        return str(type(data)) == "<class 'jep.PyJArray'>"

    assert mode == Mode.JPYPE
    return isinstance(data, jpype.JArray)


def jinstance(obj, jtype) -> bool:
    """
    Test if the given object is an instance of a particular Java type.

    :param obj: The object to check.
    :param jtype: The Java type, as either a jimported class or as a string.
    :return: True iff the object is an instance of that Java type.
    """
    if isinstance(jtype, str):
        jtype = jimport(jtype)

    if mode == Mode.JEP:
        return isinstance(obj, jtype.__pytype__)

    assert mode == Mode.JPYPE
    return isinstance(obj, jtype)


def jarray(kind, lengths: Sequence):
    """
    Create a new n-dimensional Java array.

    :param kind: The type of array to create. This can either be a particular
    type of object as obtained from jimport, or else a special code for one of
    the eight primitive array types:
    * 'b' for byte
    * 'c' for char
    * 'd' for double
    * 'f' for float
    * 'i' for int
    * 'j' for long
    * 's' for short
    * 'z' for boolean
    :param lengths: List of lengths for the array. For example:
    `jarray('z', [3, 7])` is the equivalent of `new boolean[3][7]` in Java.
    You can pass a single integer to make a 1-dimensional array of that length.
    :return: The newly allocated array
    """
    if isinstance(kind, str):
        kind = kind.lower()
    if isinstance(lengths, int):
        lengths = [lengths]
    arraytype = kind

    if mode == Mode.JEP:
        import jep  # noqa: F401

        if len(lengths) == 1:
            # Fast case: 1-d array (we can use primitives)
            arr = jep.jarray(lengths[0], arraytype)
        else:
            # Slow case: n-d array (we cannot use primitives)
            # See https://github.com/ninia/jep/issues/439
            kinds = {
                "b": jimport("java.lang.Byte"),
                "c": jimport("java.lang.Character"),
                "d": jimport("java.lang.Double"),
                "f": jimport("java.lang.Float"),
                "i": jimport("java.lang.Integer"),
                "j": jimport("java.lang.Long"),
                "s": jimport("java.lang.Short"),
                "z": jimport("java.lang.Boolean"),
            }
            if arraytype in kinds:
                arraytype = kinds[arraytype]
                kind = arraytype
            # build up the array type
            for _ in range(len(lengths) - 1):
                arraytype = jep.jarray(0, arraytype)
            # instantiate the n-dimensional array
            arr = jep.jarray(lengths[0], arraytype)

    elif mode == Mode.JPYPE:
        start_jvm()

        # build up the array type
        kinds = {
            "b": jpype.JByte,
            "c": jpype.JChar,
            "d": jpype.JDouble,
            "f": jpype.JFloat,
            "i": jpype.JInt,
            "j": jpype.JLong,
            "s": jpype.JShort,
            "z": jpype.JBoolean,
        }
        if arraytype in kinds:
            arraytype = kinds[arraytype]
        for _ in range(len(lengths)):
            arraytype = jpype.JArray(arraytype)
        # instantiate the n-dimensional array
        arr = arraytype(lengths[0])

    else:
        raise RuntimeError(f"Invalid mode: {mode}")

    if len(lengths) > 1:
        for i in range(len(arr)):
            arr[i] = jarray(kind, lengths[1:])
    return arr


def numeric_bounds(
    the_type: type,
) -> Union[Tuple[int, int], Tuple[float, float], Tuple[None, None]]:
    """
    Get the minimum and maximum values for the given numeric type.
    For example, a Java long returns (int(Long.MIN_VALUE), int(Long.MAX_VALUE)),
    whereas a Java double returns (float(-Double.MAX_VALUE), float(Double.MAX_VALUE)).

    :param the_type: The type whose minimum and maximum values are needed.
    :return:
        The minimum and maximum values as a two-element tuple of int or float,
        or a two-element tuple of None if no known bounds.
    """
    if is_jbyte(the_type):
        Byte = jimport("java.lang.Byte")
        return int(Byte.MIN_VALUE), int(Byte.MAX_VALUE)

    if is_jshort(the_type):
        Short = jimport("java.lang.Short")
        return int(Short.MIN_VALUE), int(Short.MAX_VALUE)

    if is_jinteger(the_type):
        Integer = jimport("java.lang.Integer")
        return int(Integer.MIN_VALUE), int(Integer.MAX_VALUE)

    if is_jlong(the_type):
        Long = jimport("java.lang.Long")
        return int(Long.MIN_VALUE), int(Long.MAX_VALUE)

    if is_jfloat(the_type):
        Float = jimport("java.lang.Float")
        return float(-Float.MAX_VALUE), float(Float.MAX_VALUE)

    if is_jdouble(the_type):
        Double = jimport("java.lang.Double")
        return float(-Double.MAX_VALUE), float(Double.MAX_VALUE)

    return None, None


def find_java_methods(data) -> list[dict[str, Any]]:
    """
    Use Java reflection to introspect the given Java object,
    returning a table of its available methods.

    :param data: The object or class to inspect.
    :return: List of table rows with columns "name", "static", "arguments", and "returns".
    """

    if not isjava(data):
        raise ValueError("Not a Java object")

    jcls = data if jinstance(data, "java.lang.Class") else jclass(data)

    methods = jcls.getMethods()

    # NB: Methods are returned in inconsistent order.
    # Arrays.sort(methods, (m1, m2) -> {
    #    final int nameComp = m1.getName().compareTo(m2.getName())
    #    if (nameComp != 0) return nameComp
    #    final int pCount1 = m1.getParameterCount()
    #    final int pCount2 = m2.getParameterCount()
    #    if (pCount1 != pCount2) return pCount1 - pCount2
    #    final Class<?>[] pTypes1 = m1.getParameterTypes()
    #    final Class<?>[] pTypes2 = m2.getParameterTypes()
    #    for (int i = 0; i < pTypes1.length; i++) {
    #        final int typeComp = ClassUtils.compare(pTypes1[i], pTypes2[i])
    #        if (typeComp != 0) return typeComp
    #    }
    #    return ClassUtils.compare(m1.getReturnType(), m2.getReturnType())
    # })

    table = []
    Modifier = jimport("java.lang.reflect.Modifier")

    for m in methods:
        name = m.getName()
        args = [c.getName() for c in m.getParameterTypes()]
        mods = Modifier.isStatic(m.getModifiers())
        returns = m.getReturnType().getName()
        table.append(
            {
                "name": name,
                "static": mods,
                "arguments": args,
                "returns": returns,
            }
        )
    sorted_table = sorted(table, key=lambda d: d["name"])

    return sorted_table


# TODO
def find_java_fields(data) -> list[dict[str, Any]]:
    """
    Use Java reflection to introspect the given Java object,
    returning a table of its available fields.

    :param data: The object or class to inspect.
    :return: List of table rows with columns "name", "arguments", and "returns".
    """
    if not isjava(data):
        raise ValueError("Not a Java object")

    jcls = data if jinstance(data, "java.lang.Class") else jclass(data)

    fields = jcls.getFields()
    table = []

    for f in fields:
        name = f.getName()
        table.append(name)

    return table


def _map_syntax(base_type):
    """
    Maps a java BaseType annotation (see link below) in an Java array
    to a specific type with an Python interpretable syntax.
    https://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.3
    """
    basetype_mapping = {
        "[B": "byte[]",
        "[C": "char[]",
        "[D": "double[]",
        "[F": "float[]",
        "[I": "int[]",
        "[J": "long[]",
        "[L": "[]",  # array
        "[S": "short[]",
        "[Z": "boolean[]",
    }

    if base_type in basetype_mapping:
        return basetype_mapping[base_type]
    # Handle the case of a returned array of an object
    elif base_type.__str__().startswith("[L"):
        return base_type.__str__()[2:-1] + "[]"
    else:
        return base_type


def _make_pretty_string(entry, offset):
    """
    Prints the entry with a specific formatting and aligned style
    :param entry: Dictionary of class names, modifiers, arguments, and return values.
    :param offset: Offset between the return value and the method.
    """

    # A star implies that the method is a static method
    return_val = f"{entry['returns'].__str__():<{offset}}"
    # Handle whether to print static/instance modifiers
    obj_name = f"{entry['name']}"
    modifier = f"{'*':>4}" if entry["static"] else f"{'':>4}"

    # Handle methods with no arguments
    if not entry["arguments"]:
        return f"{return_val} {modifier} = {obj_name}()\n"
    else:
        arg_string = ", ".join([r.__str__() for r in entry["arguments"]])
        return f"{return_val} {modifier} = {obj_name}({arg_string})\n"


# TODO
def fields(data) -> str:
    """
    Writes data to a printed field names with the field value.
    :param data: The object or class to inspect.
    """
    # table = find_java_fields(data)

    all_fields = ""
    ################
    # FILL THIS IN #
    ################

    print(all_fields)


# TODO
def attrs(data):
    """
    Writes data to a printed field names with the field value. Alias for `fields(data)`.
    :param data: The object or class to inspect.
    """
    fields(data)


def get_source_code(data):
    """
    Tries to find the source code using Scijava's SourceFinder'
    :param data: The object or class to check for source code.
    """
    types = jimport("org.scijava.util.Types")
    sf = jimport("org.scijava.search.SourceFinder")
    jstring = jimport("java.lang.String")
    try:
        jcls = data if jinstance(data, "java.lang.Class") else jclass(data)
        if types.location(jcls).toString().startsWith(jstring("jrt")):
            # Handles Java RunTime (jrt) exceptions.
            return "GitHub source code not available"
        url = sf.sourceLocation(jcls, None)
        urlstring = url.toString()
        return urlstring
    except jimport("java.lang.IllegalArgumentException") as err:
        return f"Illegal argument provided {err=},  {type(err)=}"
    except Exception as err:
        return f"Unexpected {err=}, {type(err)=}"


def methods(data, static: bool | None = None, source: bool = True) -> str:
    """
    Writes data to a printed string of class methods with inputs, static modifier, arguments, and return values.

    :param data: The object or class to inspect.
    :param static: Which methods to print. Can be set as boolean to filter the class methods based on
    static vs. instance methods. Optional, default is None (prints all methods).
    :param source: Whether to print any available source code. Default True.
    """
    table = find_java_methods(data)

    # Print source code
    offset = max(list(map(lambda entry: len(entry["returns"]), table)))
    all_methods = ""
    if source:
        urlstring = get_source_code(data)
        print(f"URL: {urlstring}")
    else:
        pass

    # Print methods
    for entry in table:
        entry["returns"] = _map_syntax(entry["returns"])
        entry["arguments"] = [_map_syntax(e) for e in entry["arguments"]]
        if static is None:
            entry_string = _make_pretty_string(entry, offset)
            all_methods += entry_string

        elif static and entry["static"]:
            entry_string = _make_pretty_string(entry, offset)
            all_methods += entry_string
        elif not static and not entry["static"]:
            entry_string = _make_pretty_string(entry, offset)
            all_methods += entry_string
        else:
            continue

    # 4 added to align the asterisk with output.
    print(f"{'':<{offset + 4}}* indicates a static method")
    print(all_methods)


def _is_jtype(the_type: type, class_name: str) -> bool:
    """
    Test if the given type object is *exactly* the specified Java type.

    :param the_type: The type object to check.
    :param class_name: The fully qualified Java class name in string form.
    :return: True iff the type is exactly that Java type.
    """
    # NB: Stringify the type to support both bridge modes. Ex:
    # * JPype: <java class 'java.lang.Integer'>
    # * Jep: <class 'java.lang.Integer'>
    return f"class '{class_name}'" in str(the_type)
