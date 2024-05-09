"""
Supercharged Java access from Python, built on JPype and jgo.

Use Java classes from Python:

    >>> from scyjava import jimport
    >>> System = jimport('java.lang.System')
    >>> System.getProperty('java.version')
    '1.8.0_252'

Use Maven artifacts from remote repositories:

    >>> from scyjava import config, jimport
    >>> config.enable_headless_mode()
    >>> config.add_repositories({
    ... 'scijava.public': 'https://maven.scijava.org/content/groups/public',
    ... })
    >>> config.endpoints.append('net.imagej:imagej:2.1.0')
    >>> ImageJ = jimport('net.imagej.ImageJ')
    >>> ij = ImageJ()
    >>> formula = "10 * (Math.cos(0.3*p[0]) + Math.sin(0.3*p[1]))"
    >>> ArrayImgs = jimport('net.imglib2.img.array.ArrayImgs')
    >>> blank = ArrayImgs.floats(64, 16)
    >>> sinusoid = ij.op().image().equation(blank, formula)
    >>> print(ij.op().image().ascii(sinusoid))
    ,,,--+oo******oo+--,,,,,--+oo******o++--,,,,,--+oo******o++--,,,
    ...,--+ooo**oo++--,....,,--+ooo**oo++-,,....,,--+ooo**oo++-,,...
     ...,--++oooo++--,... ...,--++oooo++--,... ...,--++oooo++-,,...
       ..,--++++++--,..     ..,--++o+++--,..     .,,--++o+++--,..
       ..,,-++++++-,,.      ..,,-++++++-,,.      ..,--++++++-,,.
        .,,--++++--,,.       .,,--++++--,,.       .,,--++++--,..
        .,,--++++--,,.       .,,-+++++--,,.       .,,-+++++--,,.
       ..,--++++++--,..     ..,--++++++--,..     ..,--++++++-,,..
      ..,,-++oooo++-,,..   ..,,-++oooo++-,,..   ..,,-++ooo+++-,,..
    ...,,-++oooooo++-,,.....,,-++oooooo++-,,.....,,-++oooooo+--,,...
    .,,,-++oo****oo++-,,,.,,,-++oo****oo+--,,,.,,,-++oo****oo+--,,,.
    ,,--++o***OO**oo++-,,,,--++o***OO**oo+--,,,,--++o***OO**oo+--,,,
    ---++o**OOOOOO**o++-----++o**OOOOOO*oo++-----++o**OOOOOO*oo++---
    --++oo*OO####OO*oo++---++oo*OO####OO*oo++---++o**OO####OO*oo++--
    +++oo*OO######O**oo+++++oo*OO######O**oo+++++oo*OO######O**oo+++
    +++oo*OO######OO*oo+++++oo*OO######OO*oo+++++oo*OO######OO*oo+++

Convert Java collections to Python:

    >>> from scyjava import jimport
    >>> HashSet = jimport('java.util.HashSet')
    >>> moves = {'jump', 'duck', 'dodge'}
    >>> fish = {'walleye', 'pike', 'trout'}
    >>> jbirds = HashSet()
    >>> for bird in ('duck', 'goose', 'swan'): jbirds.add(bird)
    >>> from scyjava import to_python as j2p
    >>> j2p(jbirds).isdisjoint(moves)
    False
    >>> j2p(jbirds).isdisjoint(fish)
    True

Convert Python collections to Java:

    >>> from scyjava import jimport
    >>> HashSet = jimport('java.util.HashSet')
    >>> jset = HashSet()
    >>> pset = {1, 2, 3}
    >>> from scyjava import to_java as p2j
    >>> jset.addAll(p2j(pset))
    True
    >>> jset.toString()
    '[1, 2, 3]'
"""

import logging
from functools import lru_cache
from typing import Any, Callable, Dict

from ._arrays import is_arraylike, is_memoryarraylike, is_xarraylike
from ._convert import (
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
from ._jvm import (  # noqa: F401
    available_processors,
    gc,
    is_awt_initialized,
    is_jvm_headless,
    jimport,
    jvm_started,
    jvm_version,
    memory_max,
    memory_total,
    memory_used,
    shutdown_jvm,
    start_jvm,
    when_jvm_starts,
    when_jvm_stops,
)
from ._script import enable_python_scripting
from ._types import (
    JavaClasses,
    is_jarray,
    isjava,
    jarray,
    jclass,
    jinstance,
    jstacktrace,
    numeric_bounds,
)
from ._versions import compare_version, get_version, is_version_at_least

__version__ = get_version("scyjava")
__all__ = [
    k
    for k, v in globals().items()
    if not k.startswith("_")
    and hasattr(v, "__module__")
    and v.__module__.startswith("scyjava.")
]

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
    Runs as a fallback when this module does not have an attribute.
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
    _logger.debug("Initializing type converters")

    for converter in _stock_java_converters():
        add_java_converter(converter)
    _logger.debug("Java converters:{'\n-'.join(java_converters)}")

    for converter in _stock_py_converters():
        add_py_converter(converter)
    _logger.debug("Python converters:{'\n-'.join(py_converters)}")


when_jvm_starts(_initialize_converters)
