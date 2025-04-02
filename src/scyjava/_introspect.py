"""
Introspection functions for reporting java class 'methods', 'fields', and source code URL.
"""

from functools import partial
from typing import Any

from scyjava._jvm import jimport
from scyjava._types import isjava, jinstance, jclass


def find_java(data, aspect: str) -> list[dict[str, Any]]:
    """
    Use Java reflection to introspect the given Java object,
    returning a table of its available methods.

    :param data: The object or class or fully qualified class name to inspect.
    :param aspect: Either 'methods' or 'fields'
    :return: List of dicts with keys: "name", "static", "arguments", and "returns".
    """

    if not isjava(data) and isinstance(data, str):
        try:
            data = jimport(data)
        except Exception as err:
            raise ValueError(f"Not a Java object {err}")

    Modifier = jimport("java.lang.reflect.Modifier")
    jcls = data if jinstance(data, "java.lang.Class") else jclass(data)

    if aspect == "methods":
        cls_aspects = jcls.getMethods()
    elif aspect == "fields":
        cls_aspects = jcls.getFields()
    else:
        return "`aspect` must be either 'fields' or 'methods'"

    table = []

    for m in cls_aspects:
        name = m.getName()
        if aspect == "methods":
            args = [c.getName() for c in m.getParameterTypes()]
            returns = m.getReturnType().getName()
        elif aspect == "fields":
            args = None
            returns = m.getType().getName()
        mods = Modifier.isStatic(m.getModifiers())
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


def _map_syntax(base_type):
    """
    Maps a Java BaseType annotation (see link below) in an Java array
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

    # Handle fields
    if entry["arguments"] is None:
        return f"{return_val} {modifier} = {obj_name}\n"

    # Handle methods with no arguments
    if len(entry["arguments"]) == 0:
        return f"{return_val} {modifier} = {obj_name}()\n"
    else:
        arg_string = ", ".join([r.__str__() for r in entry["arguments"]])
        return f"{return_val} {modifier} = {obj_name}({arg_string})\n"


def java_source(data):
    """
    Tries to find the source code using Scijava's SourceFinder
    :param data: The object or class or fully qualified class name to check for source code.
    :return: The URL of the java class
    """
    types = jimport("org.scijava.util.Types")
    sf = jimport("org.scijava.search.SourceFinder")
    jstring = jimport("java.lang.String")
    try:
        if not isjava(data) and isinstance(data, str):
            try:
                data = jimport(data)  # check if data can be imported
            except Exception as err:
                raise ValueError(f"Not a Java object {err}")
        jcls = data if jinstance(data, "java.lang.Class") else jclass(data)
        if types.location(jcls).toString().startsWith(jstring("jrt")):
            # Handles Java RunTime (jrt) exceptions.
            raise ValueError("Java Builtin: GitHub source code not available")
        url = sf.sourceLocation(jcls, None)
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


def _print_data(data, aspect, static: bool | None = None, source: bool = True):
    """
    Writes data to a printed string of class methods with inputs, static modifier, arguments, and return values.

    :param data: The object or class to inspect or fully qualified class name.
    :param aspect: Whether to print class 'fields' or 'methods'.
    :param static: Boolean filter on Static or Instance methods. Optional, default is None (prints all).
    :param source: Whether to print any available source code. Default True.
    """
    table = find_java(data, aspect)
    if len(table) == 0:
        print(f"No {aspect} found")
        return

    # Print source code
    offset = max(list(map(lambda entry: len(entry["returns"]), table)))
    all_methods = ""
    if source:
        urlstring = java_source(data)
        print(f"Source code URL: {urlstring}")

    # Print methods
    for entry in table:
        entry["returns"] = _map_syntax(entry["returns"])
        if entry["arguments"]:
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
    print(f"{'':<{offset + 4}}* indicates static modifier")
    print(all_methods)


# The functions with short names for quick usage.
methods = partial(_print_data, aspect="methods")
fields = partial(_print_data, aspect="fields")
attrs = partial(_print_data, aspect="fields")


def src(data):
    """
    Prints the source code URL for a Java class, object, or class name.

    :param data: The Java class, object, or fully qualified class name as string
    """
    source_url = java_source(data)
    print(f"Source code URL: {source_url}")
