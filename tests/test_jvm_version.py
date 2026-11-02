"""
Tests for functions in _versions submodule.
"""

import os
import subprocess
from unittest import mock

import jpype

from scyjava._jvm import _jvm_version_str_to_tuple, jvm_version


def test_jvm_version():
    assert _jvm_version_str_to_tuple(' version "17.0.1"', "java") == (17, 0, 1)
    assert _jvm_version_str_to_tuple(' version "17.0.18-internal"', "java") == (
        17,
        0,
        18,
    )
    assert _jvm_version_str_to_tuple(' version "11.0.9.1-internal"', "java") == (
        11,
        0,
        9,
        1,
    )
    assert _jvm_version_str_to_tuple(' version "1.8.0_312"', "java") == (1, 8, 0)
    assert _jvm_version_str_to_tuple(' version "25"', "java") == (25,)


def test_jvm_version_from_java_home_bytes(tmp_path):
    # JPype's macOS java_home fallback yields a Java home directory as bytes.
    java = tmp_path / "bin" / ("java.exe" if os.name == "nt" else "java")
    java.parent.mkdir()
    java.touch()
    output = b'openjdk version "25.0.1" 2025-10-21'
    with (
        mock.patch.object(jpype, "getJVMVersion", return_value=(0, 0, 0)),
        mock.patch.object(
            jpype, "getDefaultJVMPath", return_value=os.fsencode(tmp_path)
        ),
        mock.patch.object(subprocess, "check_output", return_value=output) as co,
    ):
        assert jvm_version() == (25, 0, 1)
    assert co.call_args.args[0] == [str(java), "-version"]
