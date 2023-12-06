"""
Utility functions for working with and reasoning about software component versions.
"""

import logging
from importlib.metadata import version

from scyjava._jvm import jimport
from scyjava._types import isjava

_logger = logging.getLogger(__name__)


def get_version(java_class_or_python_package) -> str:
    """
    Return the version of a Java class or Python package.

    For Python package, uses importlib.metadata.version if available
    (Python 3.8+), with pkg_resources.get_distribution as a fallback.

    For Java classes, requires org.scijava:scijava-common on the classpath.

    The version string is extracted from the given class's associated JAR
    artifact (if any), either the embedded Maven POM if the project was built
    with Maven, or the JAR manifest's Specification-Version value if it exists.

    See org.scijava.VersionUtils.getVersion(Class) for further details.
    """

    if isjava(java_class_or_python_package):
        # Assume we were given a Java class object.
        VersionUtils = jimport("org.scijava.util.VersionUtils")
        return str(VersionUtils.getVersion(java_class_or_python_package))

    # Assume we were given a Python package name.
    return version(java_class_or_python_package)


def is_version_at_least(actual_version: str, minimum_version: str) -> bool:
    """
    Return a boolean on a version comparison.
    Requires org.scijava:scijava-common on the classpath.

    Returns True if the given actual version is greater than or
    equal to the specified minimum version, or False otherwise.

    See org.scijava.VersionUtils.compare(String, String) for further details.
    """
    VersionUtils = jimport("org.scijava.util.VersionUtils")
    return bool(VersionUtils.compare(actual_version, minimum_version) >= 0)


def compare_version(version, java_class_version):
    """
    This function is deprecated. Use is_version_at_least instead.
    """
    _logger.warning(
        "The compare_version function is deprecated. Use is_version_at_least instead."
    )
    return version != java_class_version and is_version_at_least(
        java_class_version, version
    )
