"""
Tests for functions in _versions submodule.
"""

from importlib.metadata import version
from pathlib import Path

import toml

import scyjava


def _expected_version():
    """
    Get the project version from pyproject.toml.
    """
    pyproject = toml.load(Path(__file__).parents[1] / "pyproject.toml")
    return pyproject["project"]["version"]


def test_version():
    sjver = _expected_version()

    # First, ensure that the version is correct.
    assert sjver == scyjava.__version__

    # Then, ensure that we get the correct version via get_version.
    assert sjver == scyjava.get_version("scyjava")
    assert sjver == scyjava.get_version(scyjava)
    assert sjver == scyjava.get_version("scyjava.config")
    assert sjver == scyjava.get_version(scyjava.config)
    assert sjver == scyjava.get_version(scyjava.config.mode)
    assert sjver == scyjava.get_version(scyjava.config.Mode)

    # And that we get the correct version of other things, too.
    assert version("toml") == scyjava.get_version(toml)
