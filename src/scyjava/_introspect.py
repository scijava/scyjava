"""
Introspection functions for reporting Java
class methods, fields, and source code URL.
"""

from typing import Any, Dict, List

from scyjava._jvm import jimport, jvm_version
from scyjava._types import isjava, jinstance, jclass


def jreflect(data, aspect: str = "all") -> List[Dict[str, Any]]:
    """
    Use Java reflection to introspect the given Java object,
    returning a table of its available methods or fields.

    :param data: The object or class or fully qualified class name to inspect.
    :param aspect: One of: "all", "constructors", "fields", or "methods".
    :return: List of dicts with keys: "name", "mods", "arguments", and "returns".
    """

    aspects = ["all", "constructors", "fields", "methods"]
    if aspect not in aspects:
        raise ValueError("aspect must be one of {aspects}")

    if not isjava(data) and isinstance(data, str):
        try:
            data = jimport(data)
        except Exception as e:
            raise ValueError(
                f"Object of type '{type(data).__name__}' is not a Java object"
            ) from e

    jcls = data if jinstance(data, "java.lang.Class") else jclass(data)

    Modifier = jimport("java.lang.reflect.Modifier")
    modifiers = {
        attr[2:].lower(): getattr(Modifier, attr)
        for attr in dir(Modifier)
        if attr.startswith("is")
    }

    members = []
    if aspect in ["all", "constructors"]:
        members.extend(jcls.getConstructors())
    if aspect in ["all", "fields"]:
        members.extend(jcls.getFields())
    if aspect in ["all", "methods"]:
        members.extend(jcls.getMethods())

    table = []

    for member in members:
        mtype = str(member.getClass().getName()).split(".")[-1].lower()
        name = member.getName()
        modflags = member.getModifiers()
        mods = [name for name, hasmod in modifiers.items() if hasmod(modflags)]
        args = (
            [ptype.getName() for ptype in member.getParameterTypes()]
            if hasattr(member, "getParameterTypes")
            else None
        )
        returns = (
            member.getReturnType().getName()
            if hasattr(member, "getReturnType")
            else (member.getType().getName() if hasattr(member, "getType") else name)
        )
        table.append(
            {
                "type": mtype,
                "name": name,
                "mods": mods,
                "arguments": args,
                "returns": returns,
            }
        )

    return table


def jsource(data) -> str:
    """
    Try to find the source code URL for the given Java object, class, or class name.
    Requires org.scijava:scijava-search on the classpath.
    :param data:
        Object, class, or fully qualified class name for which to discern the source code location.
    :return: URL of the class's source code.
    """

    if not isjava(data) and isinstance(data, str):
        try:
            data = jimport(data)  # check if data can be imported
        except Exception as err:
            raise ValueError(f"Not a Java object {err}")
    jcls = data if jinstance(data, "java.lang.Class") else jclass(data)

    if jcls.getClassLoader() is None:
        # Class is from the Java standard library.
        cls_path = str(jcls.getName()).replace(".", "/")

        # Discern the Java version.
        jv_digits = jvm_version()
        assert jv_digits is not None and len(jv_digits) > 1
        java_version = jv_digits[1] if jv_digits[0] == 1 else jv_digits[0]

        # Note: some classes (e.g. corba and jaxp) will not be located correctly before
        # Java 10, because they fall under a different subtree than `jdk`. But Java 11+
        # dispenses with such subtrees in favor of using only the module designations.
        if java_version <= 7:
            return f"https://github.com/openjdk/jdk/blob/jdk7-b147/jdk/src/share/classes/{cls_path}.java"
        elif java_version == 8:
            return f"https://github.com/openjdk/jdk/blob/jdk8-b120/jdk/src/share/classes/{cls_path}.java"
        else:  # java_version >= 9
            module_name = jcls.getModule().getName()
            # if module_name is null, it's in the unnamed module
            if java_version == 9:
                suffix = "%2B181/jdk"
            elif java_version == 10:
                suffix = "%2B46"
            else:
                suffix = "-ga"
            return f"https://github.com/openjdk/jdk/blob/jdk-{java_version}{suffix}/src/{module_name}/share/classes/{cls_path}.java"

    # Ask scijava-search for the source location.
    SourceFinder = jimport("org.scijava.search.SourceFinder")
    url = SourceFinder.sourceLocation(jcls, None)
    urlstring = url.toString()
    return urlstring
