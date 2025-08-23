"""Dynamic type-safe imports for scyjava types with lazy initialization.

This module provides a meta path finder that intercepts imports from scyjava.types
and dynamically generates the requested modules at import time.

The generator function will be called at import time with the full module name
(e.g., "scyjava.types.SomeClass") and should return a populated module.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import types
from ast import mod
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import TYPE_CHECKING

import scyjava
from scyjava._stubs import generate_stubs

if TYPE_CHECKING:
    from collections.abc import Sequence
    from importlib.machinery import ModuleSpec


_STUBS_LOCK = threading.Lock()
TYPES_DIR = Path(__file__).parent


class ScyJavaTypesMetaFinder(MetaPathFinder):
    """Meta path finder for scyjava.types that delegates to our loader."""

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
        /,
    ) -> ModuleSpec | None:
        """Return a spec for names under scyjava.types (except the base)."""
        base_package = __name__

        if not fullname.startswith(base_package + ".") or fullname == base_package:
            return None

        return importlib.util.spec_from_loader(
            fullname,
            ScyJavaTypesLoader(fullname),
            origin="dynamic",
        )


class ScyJavaTypesLoader(Loader):
    """Loader that lazily generates stubs and loads/synthesizes modules."""

    def __init__(self, fullname: str) -> None:
        self.fullname = fullname

    def create_module(self, spec: ModuleSpec) -> types.ModuleType | None:
        """Load an existing module/package or lazily generate stubs then load."""
        pkg_dir, pkg_init, mod_file = _paths_for(spec.name, TYPES_DIR)

        def _load_module() -> types.ModuleType | None:
            # Fast paths: concrete module file or package present
            if pkg_init.exists() or mod_file.exists():
                return _load_generated_module(spec.name, TYPES_DIR)
            if pkg_dir.is_dir():
                return _namespace_package(spec, pkg_dir)
            return None

        if module := _load_module():
            return module

        # Nothing exists for this name: generate once under a lock
        with _STUBS_LOCK:
            # Re-check under the lock to avoid duplicate work
            if not (pkg_init.exists() or mod_file.exists() or pkg_dir.exists()):
                endpoints = ["org.scijava:parsington:3.1.0"]  # TODO
                generate_stubs(endpoints, output_dir=TYPES_DIR)

        # Retry after generation (or if another thread created it)
        if module := _load_module():
            return module

        raise ImportError(f"Generated module not found: {spec.name} under {pkg_dir}")

    def exec_module(self, module: types.ModuleType) -> None:
        pass


def _paths_for(fullname: str, out_dir: Path) -> tuple[Path, Path, Path]:
    """Return (pkg_dir, pkg_init, mod_file) for a scyjava.types.* fullname."""
    rel = fullname.split("scyjava.types.", 1)[1]
    pkg_dir = out_dir / rel.replace(".", "/")
    pkg_init = pkg_dir / "__init__.py"
    mod_file = out_dir / (rel.replace(".", "/") + ".py")
    return pkg_dir, pkg_init, mod_file


def _namespace_package(spec: ModuleSpec, pkg_dir: Path) -> types.ModuleType:
    """Create a simple package module pointing at pkg_dir.

    This fills the role of a namespace package, (a folder with no __init__.py).
    """
    module = types.ModuleType(spec.name)
    module.__package__ = spec.name
    module.__path__ = [str(pkg_dir)]
    module.__spec__ = spec
    return module


def _load_generated_module(fullname: str, out_dir: Path) -> types.ModuleType:
    """Load a just-generated module/package from disk and return it."""
    _, pkg_init, mod_file = _paths_for(fullname, out_dir)
    path = pkg_init if pkg_init.exists() else mod_file
    if not path.exists():
        raise ImportError(f"Generated module not found: {fullname} at {path}")

    loader = SourceFileLoader(fullname, str(path))
    spec = importlib.util.spec_from_loader(fullname, loader, origin=str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to build spec for: {fullname}")

    spec.has_location = True  # populate __file__
    sys.modules[fullname] = module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# -----------------------------------------------------------


def _install_meta_finder() -> None:
    for finder in sys.meta_path:
        if isinstance(finder, ScyJavaTypesMetaFinder):
            return

    sys.meta_path.insert(0, ScyJavaTypesMetaFinder())


def uninstall_meta_finder() -> None:
    """Uninstall the ScyJavaTypesMetaFinder from sys.meta_path."""
    sys.meta_path[:] = [
        finder
        for finder in sys.meta_path
        if not isinstance(finder, ScyJavaTypesMetaFinder)
    ]


_install_meta_finder()
