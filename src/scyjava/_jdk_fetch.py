"""
Utility functions for fetching JDK/JRE.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import TYPE_CHECKING, Union

import jpype

from jgo.exec import JavaLocator, JavaSource

import scyjava.config

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)


def ensure_jvm_available() -> None:
    """
    Ensure that the JVM is available.
    """
    fetch = scyjava.config.get_fetch_java()
    if fetch == "never":
        # Not allowed to fetch Java.
        return
    if fetch == "always" or not is_jvm_available():
        fetch_java()


def is_jvm_available() -> bool:
    """Return True if the JVM is available, suppressing stderr on macos."""
    from unittest.mock import patch

    subprocess_check_output = subprocess.check_output

    def _silent_check_output(*args, **kwargs):
        # also suppress stderr on calls to subprocess.check_output
        kwargs.setdefault("stderr", subprocess.DEVNULL)
        return subprocess_check_output(*args, **kwargs)

    try:
        with patch.object(subprocess, "check_output", new=_silent_check_output):
            jpype.getDefaultJVMPath()
    # on Darwin, may raise a CalledProcessError when invoking `/usr/libexec/java_home`
    except (jpype.JVMNotFoundException, subprocess.CalledProcessError):
        return False
    return True


def fetch_java(vendor: str | None = None, version: str | None = None) -> None:
    """
    Fetch Java and configure PATH/JAVA_HOME.

    Supports cjdk version syntax including "11", "17", "11+", "17+", etc.
    See https://pypi.org/project/cjdk for more information.
    """
    if vendor is None:
        vendor = scyjava.config.get_java_vendor()
    if version is None:
        version = scyjava.config.get_java_version()

    _logger.info(f"Fetching {vendor}:{version}...")

    locator = JavaLocator(
        java_source=JavaSource.AUTO,
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


def _add_to_path(path: Union[Path, str], front: bool = False) -> None:
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
