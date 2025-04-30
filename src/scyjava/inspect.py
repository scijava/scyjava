"""
High-level convenience functions for inspecting Java objects.
"""

from __future__ import annotations

from sys import stdout as _stdout

from scyjava import _introspect


def members(data, static: bool | None = None, source: bool | None = None, writer=None):
    """
    Print all the members (constructors, fields, and methods)
    for a Java class, object, or class name.

    :param data: The Java class, object, or fully qualified class name as string.
    :param writer: Function to which output will be sent, sys.stdout.write by default.
    """
    _print_data(data, aspect="all", static=static, source=source, writer=writer)


def constructors(
    data, static: bool | None = None, source: bool | None = None, writer=None
):
    """
    Print the constructors for a Java class, object, or class name.

    :param data: The Java class, object, or fully qualified class name as string.
    :param writer: Function to which output will be sent, sys.stdout.write by default.
    """
    _print_data(
        data, aspect="constructors", static=static, source=source, writer=writer
    )


def fields(data, static: bool | None = None, source: bool | None = None, writer=None):
    """
    Print the fields for a Java class, object, or class name.

    :param data: The Java class, object, or fully qualified class name as string.
    :param writer: Function to which output will be sent, sys.stdout.write by default.
    """
    _print_data(data, aspect="fields", static=static, source=source, writer=writer)


def methods(data, static: bool | None = None, source: bool | None = None, writer=None):
    """
    Print the methods for a Java class, object, or class name.

    :param data: The Java class, object, or fully qualified class name as string.
    :param writer: Function to which output will be sent, sys.stdout.write by default.
    """
    _print_data(data, aspect="methods")


def src(data, writer=None):
    """
    Print the source code URL for a Java class, object, or class name.

    :param data: The Java class, object, or fully qualified class name as string.
    :param writer: Function to which output will be sent, sys.stdout.write by default.
    """
    writer = writer or _stdout.write
    source_url = _introspect.jsource(data)
    writer(f"Source code URL: {source_url}\n")


def _map_syntax(base_type):
    """
    Map a Java BaseType annotation (see link below) in an Java array
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


def _pretty_string(entry, offset):
    """
    Print the entry with a specific formatting and aligned style.

    :param entry: Dictionary of class names, modifiers, arguments, and return values.
    :param offset: Offset between the return value and the method.
    """

    # A star implies that the method is a static method
    return_type = entry["returns"] or "void"
    return_val = f"{return_type.__str__():<{offset}}"
    # Handle whether to print static/instance modifiers
    obj_name = f"{entry['name']}"
    modifier = f"{'*':>4}" if "static" in entry["mods"] else f"{'':>4}"

    # Handle fields
    if entry["arguments"] is None:
        return f"{return_val} {modifier} = {obj_name}\n"

    # Handle methods with no arguments
    if len(entry["arguments"]) == 0:
        return f"{return_val} {modifier} = {obj_name}()\n"
    else:
        arg_string = ", ".join([r.__str__() for r in entry["arguments"]])
        return f"{return_val} {modifier} = {obj_name}({arg_string})\n"


def _print_data(
    data, aspect, static: bool | None = None, source: bool | None = None, writer=None
):
    """
    Write data to a printed table with inputs, static modifier,
    arguments, and return values.

    :param data: The object or class to inspect or fully qualified class name.
    :param static:
        Boolean filter on Static or Instance methods.
        Optional, default is None (prints all).
    :param source:
        Whether to discern and report a URL to the relevant source code.
        Requires org.scijava:scijava-search to be on the classpath.
        When set to None (the default), autodetects whether scijava-search
        is available, reporting source URL if so, or leaving it out if not.
    """
    writer = writer or _stdout.write
    table = _introspect.jreflect(data, aspect)
    if len(table) == 0:
        writer(f"No {aspect} found\n")
        return

    # Print source code
    offset = max(list(map(lambda entry: len(entry["returns"] or "void"), table)))
    all_methods = ""
    if source or source is None:
        try:
            urlstring = _introspect.jsource(data)
            writer(f"Source code URL: {urlstring}\n")
        except TypeError:
            if source:
                writer(
                    "Classpath lacks scijava-search; no source code URL detection is available.\n"
                )

    # Print methods
    for entry in table:
        if entry["returns"]:
            entry["returns"] = _map_syntax(entry["returns"])
        if entry["arguments"]:
            entry["arguments"] = [_map_syntax(e) for e in entry["arguments"]]
        if static is None:
            entry_string = _pretty_string(entry, offset)
            all_methods += entry_string

        elif static and "static" in entry["mods"]:
            entry_string = _pretty_string(entry, offset)
            all_methods += entry_string
        elif not static and "static" not in entry["mods"]:
            entry_string = _pretty_string(entry, offset)
            all_methods += entry_string
        else:
            continue
    all_methods += "\n"

    # 4 added to align the asterisk with output.
    writer(f"{'':<{offset + 4}}* indicates static modifier\n")
    writer(all_methods)
