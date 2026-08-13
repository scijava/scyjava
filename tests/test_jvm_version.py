"""
Tests for functions in _versions submodule.
"""

from scyjava._jvm import _jvm_version_str_to_tuple


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
