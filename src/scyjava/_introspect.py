"""
Introspection functions for reporting Java
class methods, fields, and source code URL.
"""

from typing import Any, Dict, List

from scyjava._jvm import jimport
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


def jsource(data):
    """
    Try to find the source code using SciJava's SourceFinder.
    :param data:
        The object or class or fully qualified class name to check for source code.
    :return: The URL of the java class
    """
    Types = jimport("org.scijava.util.Types")
    SourceFinder = jimport("org.scijava.search.SourceFinder")
    String = jimport("java.lang.String")
    try:
        if not isjava(data) and isinstance(data, str):
            try:
                data = jimport(data)  # check if data can be imported
            except Exception as err:
                raise ValueError(f"Not a Java object {err}")
        jcls = data if jinstance(data, "java.lang.Class") else jclass(data)
        if Types.location(jcls).toString().startsWith(String("jrt")):
            # Handles Java RunTime (jrt) exceptions.
            raise ValueError("Java Builtin: GitHub source code not available")
        url = SourceFinder.sourceLocation(jcls, None)
        urlstring = url.toString()
        return urlstring
    except jimport("java.lang.IllegalArgumentException") as err:
        return f"Illegal argument provided {err=},  {type(err)=}"
    except ValueError as err:
        return f"{err}"
    except TypeError:
        return f"Not a Java class {str(type(data))}"
    except Exception as err:
        return f"Unexpected {err=}, {type(err)=}"
