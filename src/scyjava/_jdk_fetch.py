"""
Utility functions for fetching JDK/JRE.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from jgo.exec import JavaLocator, JavaSource

import scyjava.config

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)


def resolve_java(vendor: str | None = None, version: str | None = None) -> None:
    """
    Resolve JDK installation location and configure PATH/JAVA_HOME.
    Might download Java or use the system Java, depending on the
    scyjava.config.fetch_java setting.

    Supports cjdk version syntax including "11", "17", "11+", "17+", etc.
    See https://pypi.org/project/cjdk for more information.
    """
    if vendor is None:
        vendor = scyjava.config.get_java_vendor()
    if version is None:
        version = scyjava.config.get_java_version()

    _logger.info(f"Fetching {vendor}:{version}...")

    fetch = scyjava.config.get_fetch_java()

    # Map scyjava fetch mode to jgo JavaSource strategy.
    # "always" -> DOWNLOAD: always use cjdk-managed Java, ignoring system Java.
    # "never"  -> SYSTEM:   always use system Java, never downloading via cjdk.
    # "auto"   -> AUTO:     prefer system Java, fall back to cjdk if absent/too old.
    _FETCH_MODES = {
        "always": JavaSource.DOWNLOAD,
        "download": JavaSource.DOWNLOAD,
        "never": JavaSource.SYSTEM,
        "system": JavaSource.SYSTEM,
    }
    java_source = _FETCH_MODES.get(fetch, JavaSource.AUTO)

    locator = JavaLocator(
        java_source=java_source,
        java_version=version,  # Pass string directly (e.g. "11", "17", "11+", "17+")
        java_vendor=vendor,
        verbose=True,
    )

    # Locate returns path to java executable (e.g., /path/to/java/bin/java)
    java_exe = locator.locate()
    java_home = java_exe.parent.parent  # Navigate from bin/java to JAVA_HOME

    _logger.debug(f"java_home -> {java_home}")
    _add_to_path(str(java_home / "bin"), front=True)
    os.environ["JAVA_HOME"] = str(java_home)


def _add_to_path(path: Path | str, front: bool = False) -> None:
    """Add a path to the PATH environment variable.

    If front is True, the path is added to the front of the PATH.
    By default, the path is added to the end of the PATH.
    If the path is already in the PATH, it is not added again.
    """

    current_path = os.environ.get("PATH", "")
    if (path := str(path)) in current_path:
        return
    new_path = [path, current_path] if front else [current_path, path]
    os.environ["PATH"] = os.pathsep.join(new_path)
