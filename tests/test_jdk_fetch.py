"""
Tests for functions in _jdk_fetch submodule.
"""

import os

import pytest

from scyjava._jdk_fetch import _java_home

posix_only = pytest.mark.skipif(os.name == "nt", reason="uses a shell script")


def _fake_java(path, stderr):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\ncat >&2 <<'EOF'\n{stderr}\nEOF\n")
    path.chmod(0o755)
    return path


@posix_only
def test_java_home_from_launcher_stub(tmp_path):
    # E.g. macOS's /usr/bin/java, which is not located inside its Java home.
    real_home = tmp_path / "jdk" / "Contents" / "Home"
    real_home.mkdir(parents=True)
    java = _fake_java(
        tmp_path / "usr" / "bin" / "java",
        f"Property settings:\n    java.home = {real_home}\n"
        '    java.version = 25.0.1\n\nopenjdk version "25.0.1"',
    )
    assert _java_home(java) == real_home


@posix_only
def test_java_home_fallback(tmp_path):
    java = _fake_java(tmp_path / "jdk" / "bin" / "java", "no properties here")
    assert _java_home(java) == tmp_path / "jdk"


def test_java_home_missing_executable(tmp_path):
    java = tmp_path / "jdk" / "bin" / "java"
    assert _java_home(java) == tmp_path / "jdk"
