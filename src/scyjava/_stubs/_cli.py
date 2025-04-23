"""The scyjava-stubs executable."""

import argparse
import importlib
import importlib.util
import logging
import sys
from pathlib import Path

from ._genstubs import generate_stubs


def main() -> None:
    """The main entry point for the scyjava-stubs executable."""
    logging.basicConfig(level="INFO")
    parser = argparse.ArgumentParser(
        description="Generate Python Type Stubs for Java classes."
    )
    parser.add_argument(
        "endpoints",
        type=str,
        nargs="+",
        help="Maven endpoints to install and use (e.g. org.myproject:myproject:1.0.0)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        help="package prefixes to generate stubs for (e.g. org.myproject), "
        "may be used multiple times. If not specified, prefixes are gleaned from the "
        "downloaded artifacts.",
        action="append",
        default=[],
        metavar="PREFIX",
        dest="prefix",
    )
    path_group = parser.add_mutually_exclusive_group()
    path_group.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Filesystem path to write stubs to.",
    )
    path_group.add_argument(
        "--output-python-path",
        type=str,
        default=None,
        help="Python path to write stubs to (e.g. 'scyjava.types').",
    )
    parser.add_argument(
        "--convert-strings",
        dest="convert_strings",
        action="store_true",
        default=False,
        help="convert java.lang.String to python str in return types. "
        "consult the JPype documentation on the convertStrings flag for details",
    )
    parser.add_argument(
        "--no-javadoc",
        dest="with_javadoc",
        action="store_false",
        default=True,
        help="do not generate docstrings from JavaDoc where available",
    )

    rt_group = parser.add_mutually_exclusive_group()
    rt_group.add_argument(
        "--runtime-imports",
        dest="runtime_imports",
        action="store_true",
        default=True,
        help="Add runtime imports to the generated stubs. ",
    )
    rt_group.add_argument(
        "--no-runtime-imports", dest="runtime_imports", action="store_false"
    )

    parser.add_argument(
        "--remove-namespace-only-stubs",
        dest="remove_namespace_only_stubs",
        action="store_true",
        default=False,
        help="Remove stubs that export no names beyond a single __module_protocol__. "
        "This leaves some folders as PEP420 implicit namespace folders.",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    output_dir = _get_ouput_dir(args.output_dir, args.output_python_path)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    generate_stubs(
        endpoints=args.endpoints,
        prefixes=args.prefix,
        output_dir=output_dir,
        convert_strings=args.convert_strings,
        include_javadoc=args.with_javadoc,
        add_runtime_imports=args.runtime_imports,
        remove_namespace_only_stubs=args.remove_namespace_only_stubs,
    )


def _get_ouput_dir(output_dir: str | None, python_path: str | None) -> Path:
    if out_dir := output_dir:
        return Path(out_dir)
    if pp := python_path:
        return _glean_path(pp)
    try:
        import scyjava

        return Path(scyjava.__file__).parent / "types"
    except ImportError:
        return Path("stubs")


def _glean_path(pp: str) -> Path:
    try:
        importlib.import_module(pp.split(".")[0])
    except ModuleNotFoundError:
        # the top level module doesn't exist:
        raise ValueError(f"Module {pp} does not exist. Cannot install stubs there.")

    try:
        spec = importlib.util.find_spec(pp)
    except ModuleNotFoundError as e:
        # at least one of the middle levels doesn't exist:
        raise NotImplementedError(f"Cannot install stubs to {pp}: {e}")

    new_ns = None
    if not spec:
        # if we get here, it means everything but the last level exists:
        parent, new_ns = pp.rsplit(".", 1)
        spec = importlib.util.find_spec(parent)

    if not spec:
        # if we get here, it means the last level doesn't exist:
        raise ValueError(f"Module {pp} does not exist. Cannot install stubs there.")

    search_locations = spec.submodule_search_locations
    if not spec.loader and search_locations:
        # namespace package with submodules
        return Path(search_locations[0])
    if spec.origin:
        return Path(spec.origin).parent
    if new_ns and search_locations:
        # namespace package with submodules
        return Path(search_locations[0]) / new_ns

    raise ValueError(f"Error finding module {pp}. Cannot install stubs there.")
