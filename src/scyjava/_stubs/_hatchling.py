"""Hatchling build hook for generating Java stubs."""

import logging
import shutil
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

        # actually build the stubs
        generate_stubs(endpoints=endpoints, prefixes=prefixes, output_dir=dest)
        print(f"Generated stubs for {endpoints} in {dest}")
        # add all new packages to the build config
        build_data["artifacts"].append("src/scyjava/types")


@hookimpl
def hatch_register_build_hook():
    return ScyjavaBuildHook
