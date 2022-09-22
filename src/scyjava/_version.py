from importlib.util import find_spec


def _find_version():
    # First pass: use importlib.metadata
    if find_spec("importlib.metadata"):
        from importlib.metadata import version

        return version("scyjava")

    if find_spec("pkg_resources"):
        from pkg_resources import get_distribution

        return get_distribution("scyjava").version
    # Fourth pass: Give up
    return "Cannot determine version! Ensure pkg_resources is installed!"
