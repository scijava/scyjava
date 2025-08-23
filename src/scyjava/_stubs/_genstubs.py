"""Type stub generation utilities using stubgen.

This module provides utilities for generating type stubs for Java classes
using the stubgenj library.  `stubgenj` must be installed for this to work
(it, in turn, only depends on JPype).

See `generate_stubs` for most functionality.  For the command-line tool,
see `scyjava._stubs.cli`, which provides a CLI interface for the `generate_stubs`
function.
"""

from __future__ import annotations

import ast
import logging
import os
import shutil
import subprocess
import sys
from importlib import import_module
from itertools import chain
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from zipfile import ZipFile

import scyjava
import scyjava.config

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


def generate_stubs(
    endpoints: Sequence[str],
    prefixes: Sequence[str] = (),
    output_dir: str | Path = "stubs",
    convert_strings: bool = True,
    include_javadoc: bool = True,
    add_runtime_imports: bool = True,
    remove_namespace_only_stubs: bool = False,
) -> None:
    """Generate stubs for the given maven endpoints.

    Parameters
    ----------
    endpoints : Sequence[str]
        The maven endpoints to generate stubs for. This should be a list of GAV
        coordinates, e.g. ["org.apache.commons:commons-lang3:3.12.0"].
    prefixes : Sequence[str], optional
        The prefixes to generate stubs for. This should be a list of Java class
        prefixes that you expect to find in the endpoints. For example,
        ["org.apache.commons"].  If not provided, the prefixes will be
        automatically determined from the jar files provided by endpoints (see the
        `_list_top_level_packages` helper function).
    output_dir : str | Path, optional
        The directory to write the generated stubs to. Defaults to "stubs" in the
        current working directory.
    convert_strings : bool, optional
        Whether to cast Java strings to Python strings in the stubs. Defaults to True.
        NOTE: This leads to type stubs that may not be strictly accurate at runtime.
        The actual runtime type of strings is determined by whether jpype.startJVM is
        called with the `convertStrings` argument set to True or False.  By setting
        this `convert_strings` argument to true, the type stubs will be generated as if
        `convertStrings` is set to True: that is, all string types will be listed as
        `str` rather than `java.lang.String | str`.  This is a safer default (as `str`)
        is a subtype of `java.lang.String`), but may lead to type errors in some cases.
    include_javadoc : bool, optional
        Whether to include Javadoc in the generated stubs. Defaults to True.
    add_runtime_imports : bool, optional
        Whether to add runtime imports to the generated stubs. Defaults to True.
        This is useful if you want to actually import the stubs as a runtime package
        with type safety.  The runtime import "magic" depends on the
        `scyjava._stubs.setup_java_imports` function.  See its documentation for
        more details.
    remove_namespace_only_stubs : bool, optional
        Whether to remove stubs that export no names beyond a single
        `__module_protocol__`. This leaves some folders as PEP420 implicit namespace
        folders. Defaults to False.  Setting this to `True` is useful if you want to
        merge the generated stubs with other stubs in the same namespace.  Without this,
        the `__init__.pyi` for any given module will be whatever whatever the *last*
        stub generator wrote to it (and therefore inaccurate).
    """
    try:
        import stubgenj
    except ImportError as e:
        raise ImportError(
            "stubgenj is not installed, but is required to generate java stubs. "
            "Please install it with `pip/conda install stubgenj`."
        ) from e
    print("GENERATE")
    import jpype

    startJVM = jpype.startJVM

    scyjava.config.endpoints.extend(endpoints)

    def _patched_start(*args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("convertStrings", convert_strings)
        startJVM(*args, **kwargs)

    with patch.object(jpype, "startJVM", new=_patched_start):
        scyjava.start_jvm()

    _prefixes = set(prefixes)
    if not _prefixes:
        cp = jpype.getClassPath(env=False)
        ep_artifacts = tuple(ep.split(":")[1] for ep in endpoints)
        for j in cp.split(os.pathsep):
            if Path(j).name.startswith(ep_artifacts):
                _prefixes.update(_list_top_level_packages(j))

    prefixes = sorted(_prefixes)
    logger.info(f"Using endpoints: {scyjava.config.endpoints!r}")
    logger.info(f"Generating stubs for: {prefixes}")
    logger.info(f"Writing stubs to: {output_dir}")

    metapath = sys.meta_path
    try:
        import jpype.imports

        jmodules = [import_module(prefix) for prefix in prefixes]
    finally:
        # remove the jpype.imports magic from the import system
        # if it wasn't there to begin with
        sys.meta_path = metapath

    stubgenj.generateJavaStubs(
        jmodules,
        useStubsSuffix=False,
        outputDir=str(output_dir),
        jpypeJPackageStubs=False,
        includeJavadoc=include_javadoc,
    )

    output_dir = Path(output_dir)
    if add_runtime_imports:
        logger.info("Adding runtime imports to generated stubs")

    for stub in output_dir.rglob("*.pyi"):
        stub_ast = ast.parse(stub.read_text())
        members = {node.name for node in stub_ast.body if hasattr(node, "name")}
        if members == {"__module_protocol__"}:
            # this is simply a module stub... no exports
            if remove_namespace_only_stubs:
                logger.info("Removing namespace only stub %s", stub)
                stub.unlink()
            continue
        if add_runtime_imports:
            real_import = stub.with_suffix(".py")
            base_prefix = stub.relative_to(output_dir).parts[0]
            real_import.write_text(
                INIT_TEMPLATE.format(
                    endpoints=repr(endpoints),
                    base_prefix=repr(base_prefix),
                )
            )

    ruff_check(output_dir.absolute())


# the "real" init file that goes into the stub package
INIT_TEMPLATE = """\
# this file was autogenerated by scyjava-stubgen
# it creates a __getattr__ function that will dynamically import
# the requested class from the Java namespace corresponding to this module.
# see scyjava._stubs for implementation details.
from scyjava._stubs import setup_java_imports

__all__, __getattr__ = setup_java_imports(
    __name__,
    __file__,
    endpoints={endpoints},
    base_prefix={base_prefix},
)
"""


def ruff_check(output: Path, select: str = "E,W,F,I,UP,C4,B,RUF,TC,TID") -> None:
    """Run ruff check and format on the generated stubs."""
    if not shutil.which("ruff"):
        return

    py_files = [str(x) for x in chain(output.rglob("*.py"), output.rglob("*.pyi"))]
    logger.info(
        "Running ruff check on %d generated stubs in % s",
        len(py_files),
        str(output),
    )
    subprocess.run(
        [
            "ruff",
            "check",
            *py_files,
            "--quiet",
            "--fix-only",
            "--unsafe-fixes",
            f"--select={select}",
        ]
    )
    logger.info("Running ruff format")
    subprocess.run(["ruff", "format", *py_files, "--quiet"])


def _list_top_level_packages(jar_path: str) -> set[str]:
    """Inspect a JAR file and return the set of top-level Java package names."""
    packages: set[str] = set()
    with ZipFile(jar_path, "r") as jar:
        # find all classes
        class_dirs = {
            entry.parent
            for x in jar.namelist()
            if (entry := PurePath(x)).suffix == ".class"
        }

        roots: set[PurePath] = set()
        for p in sorted(class_dirs, key=lambda p: len(p.parts)):
            # If none of the already accepted roots is a parent of p, keep p
            if not any(root in p.parents for root in roots):
                roots.add(p)
        packages.update({str(p).replace(os.sep, ".") for p in roots})

    return packages
