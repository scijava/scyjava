import logging
from functools import lru_cache
from typing import Any, Callable, Dict

from scyjava._arrays import (  # noqa: F401
    is_arraylike,
    is_memoryarraylike,
    is_xarraylike,
)
from scyjava._convert import (  # noqa: F401
    Converter,
    JavaCollection,
    JavaIterable,
    JavaIterator,
    JavaList,
    JavaMap,
    JavaObject,
    JavaSet,
    Priority,
    _stock_java_converters,
    _stock_py_converters,
    add_java_converter,
    add_py_converter,
    java_converters,
    py_converters,
    to_java,
    to_python,
)
from scyjava._java import (  # noqa: F401
    JavaClasses,
    is_awt_initialized,
    is_jvm_headless,
    isjava,
    jclass,
    jimport,
    jstacktrace,
    jvm_started,
    jvm_version,
    shutdown_jvm,
    start_jvm,
    when_jvm_starts,
    when_jvm_stops,
)
from scyjava._versions import (  # noqa: F401
    compare_version,
    get_version,
    is_version_at_least,
)

__version__ = get_version("scyjava")


_logger = logging.getLogger(__name__)

# Set of module properties
_CONSTANTS: Dict[str, Callable] = {}


def constant(func: Callable[[], Any], cache=True) -> Callable[[], Any]:
    """
    Turns a function into a property of this module
    Functions decorated with this property must have a
    leading underscore!
    :param func: The function to turn into a property
    """
    if func.__name__[0] != "_":
        raise ValueError(
            f"""Function {func.__name__} must have
            a leading underscore in its name
            to become a module property!"""
        )
    name = func.__name__[1:]
    if cache:
        func = (lru_cache(maxsize=None))(func)
    _CONSTANTS[name] = func
    return func


def __getattr__(name):
    """
    Runs as a fallback when this module does not have an
    attribute.
    :param name: The name of the attribute being searched for.
    """
    if name in _CONSTANTS:
        return _CONSTANTS[name]()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# -- JVM startup callbacks --

# NB: These must be performed last, because if this class is imported after the
# JVM is already running -- for example, if we are running in Jep mode, where
# Python is started from inside the JVM -- then these functions execute the
# callbacks immediately, which means the involved functions must be defined and
# functional at this point.


def _initialize_converters():
    for converter in _stock_java_converters():
        add_java_converter(converter)
    for converter in _stock_py_converters():
        add_py_converter(converter)


when_jvm_starts(_initialize_converters)
