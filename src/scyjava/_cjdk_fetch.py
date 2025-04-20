from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_logger = logging.getLogger(__name__)
_DEFAULT_MAVEN_URL = "tgz+https://dlcdn.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz"  # noqa: E501
_DEFAULT_MAVEN_SHA = "a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b"  # noqa: E501
_DEFAULT_JAVA_VENDOR = "zulu-jre"
_DEFAULT_JAVA_VERSION = "11"


def cjdk_fetch_java(
    vendor: str = "", version: str = "", raise_on_error: bool = True
) -> None:
    """Fetch java using cjdk and add it to the PATH."""
    try:
        import cjdk
    except ImportError as e:
        if raise_on_error is True:
            raise ImportError(
                "No JVM found. Please install `cjdk` to use the fetch_java feature."
            ) from e
        _logger.info("cjdk is not installed. Skipping automatic fetching of java.")
        return

    if not vendor:
        vendor = os.getenv("JAVA_VENDOR", _DEFAULT_JAVA_VENDOR)
        version = os.getenv("JAVA_VERSION", _DEFAULT_JAVA_VERSION)

    _logger.info(f"No JVM found, fetching {vendor}:{version} using cjdk...")
    home = cjdk.java_home(vendor=vendor, version=version)
    _add_to_path(str(home / "bin"))
    os.environ["JAVA_HOME"] = str(home)


def cjdk_fetch_maven(url: str = "", sha: str = "", raise_on_error: bool = True) -> None:
    """Fetch Maven using cjdk and add it to the PATH."""
    try:
        import cjdk
    except ImportError as e:
        if raise_on_error is True:
            raise ImportError(
                "Please install `cjdk` to use the fetch_java feature."
            ) from e
        _logger.info("cjdk is not installed. Skipping automatic fetching of Maven.")
        return

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
        if sha_len not in sha_lengths:
            raise ValueError(
                "MAVEN_SHA be a valid sha1, sha256, or sha512 hash."
                f"Got invalid SHA length: {sha_len}. "
            )
        kwargs = {sha_lengths[sha_len]: sha}

    maven_dir = cjdk.cache_package("Maven", url, **kwargs)
    if maven_bin := next(maven_dir.rglob("apache-maven-*/**/mvn"), None):
        _add_to_path(maven_bin.parent, front=True)
    else:
        raise RuntimeError("Failed to find Maven executable in the downloaded package.")


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
