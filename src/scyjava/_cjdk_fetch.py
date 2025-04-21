from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Union

import cjdk
import jpype

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)
_DEFAULT_MAVEN_URL = "tgz+https://dlcdn.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz"  # noqa: E501
_DEFAULT_MAVEN_SHA = "a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b"  # noqa: E501
_DEFAULT_JAVA_VENDOR = "zulu-jre"
_DEFAULT_JAVA_VERSION = "11"


def ensure_jvm_available() -> None:
    """Ensure that the JVM is available and Maven is installed."""
    if not is_jvm_available():
        cjdk_fetch_java()
    if not shutil.which("mvn"):
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


def cjdk_fetch_java(vendor: str = "", version: str = "") -> None:
    """Fetch java using cjdk and add it to the PATH."""
    if not vendor:
        vendor = os.getenv("JAVA_VENDOR", _DEFAULT_JAVA_VENDOR)
        version = os.getenv("JAVA_VERSION", _DEFAULT_JAVA_VERSION)

    _logger.info(f"No JVM found, fetching {vendor}:{version} using cjdk...")
    home = cjdk.java_home(vendor=vendor, version=version)
    _add_to_path(str(home / "bin"))
    os.environ["JAVA_HOME"] = str(home)


def cjdk_fetch_maven(url: str = "", sha: str = "") -> None:
    """Fetch Maven using cjdk and add it to the PATH."""
    # if url was passed as an argument, or env_var, use it with provided sha
    # otherwise, use default values for both
    if url := url or os.getenv("MAVEN_URL", ""):
        sha = sha or os.getenv("MAVEN_SHA", "")
    else:
        url = _DEFAULT_MAVEN_URL
        sha = _DEFAULT_MAVEN_SHA

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

    maven_dir = cjdk.cache_package("Maven", url, **kwargs)
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
