"""
Utility functions for fetching JDK/JRE and Maven.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Union

import cjdk
import jpype

import scyjava.config

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)


def ensure_jvm_available() -> None:
    """Ensure that the JVM is available and Maven is installed."""
    fetch = scyjava.config.get_fetch_java()
    if fetch == "never":
        # Not allowed to use cjdk.
        return
    if fetch == "always" or not is_jvm_available():
        cjdk_fetch_java()
    if fetch == "always" or not shutil.which("mvn"):
        cjdk_fetch_maven()


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
    # on Darwin, may raise a CalledProcessError when invoking `/user/libexec/java_home`
    except (jpype.JVMNotFoundException, subprocess.CalledProcessError):
        return False
    return True


def cjdk_fetch_java(vendor: str | None = None, version: str | None = None) -> None:
    """Fetch java using cjdk and add it to the PATH."""
    if vendor is None:
        vendor = scyjava.config.get_java_vendor()
    if version is None:
        version = scyjava.config.get_java_version()

    _logger.info(f"Fetching {vendor}:{version} using cjdk...")
    java_home = cjdk.java_home(vendor=vendor, version=version)
    _logger.debug(f"java_home -> {java_home}")
    _add_to_path(str(java_home / "bin"), front=True)
    os.environ["JAVA_HOME"] = str(java_home)


def cjdk_fetch_maven(url: str = "", sha: str = "") -> None:
    """Fetch Maven using cjdk and add it to the PATH."""
    # if url was passed as an argument, use it with provided sha
    # otherwise, use default values for both
    if not url:
        url = scyjava.config.get_maven_url()
        sha = scyjava.config.get_maven_sha()

    # fix urls to have proper prefix for cjdk
    if url.startswith("http"):
        if url.endswith(".tar.gz"):
            url = url.replace("http", "tgz+http")
        elif url.endswith(".zip"):
            url = url.replace("http", "zip+http")

    # determine sha type based on length (cjdk requires specifying sha type)
    # assuming hex-encoded SHA, length should be 40, 64, or 128
    kwargs = {}
    if sha_len := len(sha):  # empty sha is fine... we just don't pass it
        sha_lengths = {40: "sha1", 64: "sha256", 128: "sha512"}
        if sha_len not in sha_lengths:  # pragma: no cover
            raise ValueError(
                "MAVEN_SHA be a valid sha1, sha256, or sha512 hash."
                f"Got invalid SHA length: {sha_len}. "
            )
        kwargs = {sha_lengths[sha_len]: sha}

    _logger.info("Fetching Maven using cjdk...")
    maven_dir = cjdk.cache_package("Maven", url, **kwargs)
    _logger.debug(f"maven_dir -> {maven_dir}")
    if maven_bin := next(maven_dir.rglob("apache-maven-*/**/mvn"), None):
        _add_to_path(maven_bin.parent, front=True)
    else:  # pragma: no cover
        raise RuntimeError(
            "Failed to find Maven executable on system "
            "PATH, and download via cjdk failed."
        )


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
