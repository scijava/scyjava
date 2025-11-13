"""Dynamic type-safe imports for scyjava types with lazy initialization.

This module provides a meta path finder that intercepts imports from scyjava.types
and dynamically generates the requested modules at import time.

The generator function will be called at import time with the full module name
(e.g., "scyjava.types.SomeClass") and should return a populated module.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import types
    from collections.abc import Sequence
    from importlib.machinery import ModuleSpec


# where generated stubs should land (defaults to this dir: `scyjava.types`)
STUBS_DIR = os.getenv("SCYJAVA_STUBS_DIR", str(Path(__file__).parent))
# namespace under which generated stubs will be placed
STUBS_NAMESPACE = __name__
# module lock to prevent concurrent stub generation
_STUBS_LOCK = threading.Lock()


class ScyJavaTypesMetaFinder:
    """Meta path finder for scyjava.types that generates stubs on demand."""

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> ModuleSpec | None:
        """Return a spec for names under scyjava.types (except the base)."""
        # if this is an import from this module ('scyjava.types.<name>')
        # check if the module exists, and if not, call generation routines
        if fullname.startswith(f"{__name__}."):
            with _STUBS_LOCK:
                # check if the spec already exists
                # under the module lock to avoid duplicate work
                if not _find_spec(fullname, path, target, skip=self):
                    _generate_stubs()

        return None


def _generate_stubs() -> None:
    """Install stubs for all endpoints detected in `scyjava.config`.

    This could be expanded to include additional endpoints detected in, for example,
    python entry-points discovered in packages in the environment.
    """
    from scyjava import config
    from scyjava._stubs import generate_stubs

    generate_stubs(
        config.endpoints,
        output_dir=STUBS_DIR,
        add_runtime_imports=True,
        remove_namespace_only_stubs=True,
    )


def _find_spec(
    fullname: str,
    path: Sequence[str] | None,
    target: types.ModuleType | None = None,
    skip: object | None = None,
) -> ModuleSpec | None:
    """Find a module spec, skipping finder `skip` to avoid recursion."""
    # if the module is already loaded and has a spec, return it
    if module := sys.modules.get(fullname):
        try:
            if module.__spec__ is not None:
                return module.__spec__
        except AttributeError:
            pass

    for finder in sys.meta_path:
        if finder is not skip:
            try:
                spec = finder.find_spec(fullname, path, target)
            except AttributeError:
                continue
            else:
                if spec is not None:
                    return spec
    return None


def _install_meta_finder() -> None:
    """Install the ScyJavaTypesMetaFinder into sys.meta_path if not already there."""
    if any(isinstance(finder, ScyJavaTypesMetaFinder) for finder in sys.meta_path):
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
