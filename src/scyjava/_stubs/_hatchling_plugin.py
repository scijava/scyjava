"""Hatchling build hook for generating Java stubs.

To use this hook, add the following to your `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling", "scyjava"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.scyjava]
maven_coordinates = ["org.scijava:parsington:3.1.0"]
prefixes = ["org.scijava"]  # optional ... can be auto-determined from the jar files
```

This will generate stubs for the given maven coordinates and prefixes. The generated
stubs will be placed in `src/scyjava/types` and will be included in the wheel package.
This hook is only run when building a wheel package.
"""

import logging
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl


from scyjava._stubs._genstubs import generate_stubs

logger = logging.getLogger("scyjava")


class ScyjavaBuildHook(BuildHookInterface):
    """Custom build hook for generating Java stubs."""

    PLUGIN_NAME = "scyjava"

    def initialize(self, version: str, build_data: dict) -> None:
        """Initialize the build hook with the version and build data."""
        if self.target_name != "wheel":
            return

        endpoints = self.config.get("maven_coordinates", [])
        if not endpoints:
            logger.warning("No maven coordinates provided. Skipping stub generation.")
            return

        prefixes = self.config.get("prefixes", [])
        dest = Path(self.root, "src", "scyjava", "types")
        (dest.parent / "py.typed").touch()

        # actually build the stubs
        generate_stubs(
            endpoints=endpoints,
            prefixes=prefixes,
            output_dir=dest,
            remove_namespace_only_stubs=True,
        )
        print(f"Generated stubs for {endpoints} in {dest}")
        # add all new packages to the build config
        build_data["force_include"].update({str(dest.parent): "scyjava"})


@hookimpl
def hatch_register_build_hook():
    return ScyjavaBuildHook
