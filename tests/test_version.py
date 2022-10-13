import sys
from pathlib import Path

import pytest
import toml

import scyjava
from scyjava import get_version


def _expected_version():
    """
    Get the project version from pyproject.toml.
    """
    pyproject = toml.load(Path(__file__).parents[1] / "pyproject.toml")
    return pyproject["project"]["version"]


def test_version_dunder():
    """
    Ensure that the dunder variable matches _expected_version.
    """
    assert _expected_version() == scyjava.__version__


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python >= 3.8")
def test_version_importlib():
    """
    Ensure that, with scyjava.version.version unavailable,
    importlib.metadata is used next WITH python 3.8+.
    """
    # Remove scyjava.version
    sys.modules["scyjava.version"] = None
    # Ensure scyjava.__version__ matches importlib.metadata.version()

    assert _expected_version() == get_version("scyjava")


@pytest.mark.skipif(
    sys.version_info >= (3, 8), reason="importlib used instead for Python 3.8+"
)
def test_version_pkg_resources():
    """
    Ensure that, with scyjava.version.version AND
    importlib.metadata unavailable,
    pkg_resources is used next.
    """
    # Remove importlib.metadata
    sys.modules["importlib.metadata"] = None
    # Ensure scyjava.__version__ matches
    # pkg_resources.get_distribution().version

    assert _expected_version() == get_version("scyjava")


def test_version_unavailable():
    """
    Ensure that an exception is raised if none of these strategies works.
    """
    # Remove importlib.metadata
    sys.modules["importlib.metadata"] = None
    # Remove pkg_resources
    sys.modules["pkg_resources"] = None
    # Ensure scyjava.__version__ raises an exception.
    with pytest.raises(RuntimeError) as e_info:
        get_version("scyjava")
    assert (
        "RuntimeError: Cannot determine version! Is pkg_resources installed?"
    ) == e_info.exconly()
