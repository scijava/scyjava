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
    # First, ensure that the version is correct
    assert _expected_version() == scyjava.__version__

    # Then, ensure that we get the correct version via get_version
    assert _expected_version() == scyjava.get_version("scyjava")
