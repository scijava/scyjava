"""Setuptools build hook for generating Java stubs.

To use this hook, add the following to your `pyproject.toml`:

```toml
[build-system]
requires      = ["setuptools>=69", "wheel", "scyjava"]
build-backend = "setuptools.build_meta"

[tool.setuptools.cmdclass]
build_py = "scyjava_stubgen.build:build_py"
# optional project-specific defaults
maven_coordinates = ["org.scijava:parsington:3.1.0"]
prefixes          = ["org.scijava"]
```

This will generate stubs for the given maven coordinates and prefixes. The generated
stubs will be placed in `src/scyjava/types` and will be included in the wheel package.
This hook is only run when building a wheel package.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from setuptools.command.build_py import build_py as _build_py
from scyjava._stubs._genstubs import generate_stubs

log = logging.getLogger("scyjava")


class build_py(_build_py):  # type: ignore[misc]
    """
    A drop-in replacement for setuptools' build_py that
    generates Java type stubs before Python sources are copied
    into *build_lib*.
    """

    # expose two optional CLI/pyproject options so users can override defaults
    user_options: List[tuple[str, str | None, str]] = _build_py.user_options + [
        ("maven-coordinates=", None, "List of Maven coordinates to stub"),
        ("prefixes=", None, "Java package prefixes to include"),
    ]

    def initialize_options(self) -> None:  # noqa: D401
        super().initialize_options()
        self.maven_coordinates: list[str] | None = None
        self.prefixes: list[str] | None = None

    def finalize_options(self) -> None:  # noqa: D401
        """Fill in options that may come from pyproject metadata."""
        super().finalize_options()
        dist = self.distribution  # alias
        if self.maven_coordinates is None:
            self.maven_coordinates = getattr(dist, "maven_coordinates", [])
        if self.prefixes is None:
            self.prefixes = getattr(dist, "prefixes", [])

    def run(self) -> None:  # noqa: D401
        """Generate stubs, then let the normal build_py proceed."""
        if self.maven_coordinates:
            dest = Path(self.build_lib, "scyjava", "types")
            dest.parent.mkdir(parents=True, exist_ok=True)
            (dest.parent / "py.typed").touch()

            generate_stubs(
                endpoints=self.maven_coordinates,
                prefixes=self.prefixes,
                output_dir=dest,
                remove_namespace_only_stubs=True,
            )
            log.info("Generated stubs for %s", ", ".join(self.maven_coordinates))

            # make sure the wheel knows about them
            self.package_data.setdefault("scyjava", []).append("types/**/*.pyi")

        super().run()
