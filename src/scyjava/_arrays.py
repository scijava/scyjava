"""
Utility functions for working with and reasoning about arrays.
"""

from typing import Any


def is_arraylike(arr: Any) -> bool:
    """
    Return True iff the object is arraylike: possessing
    .shape, .dtype, .__array__, and .ndim attributes.

    :param arr: The object to check for arraylike properties
    :return: True iff the object is arraylike
    """
    return (
        hasattr(arr, "shape")
        and hasattr(arr, "dtype")
        and hasattr(arr, "__array__")
        and hasattr(arr, "ndim")
    )


def is_memoryarraylike(arr: Any) -> bool:
    """
    Return True iff the object is memoryarraylike:
    an arraylike object whose .data type is memoryview.

    :param arr: The object to check for memoryarraylike properties
    :return: True iff the object is memoryarraylike
    """
    return (
        is_arraylike(arr)
        and hasattr(arr, "data")
        and type(arr.data).__name__ == "memoryview"
    )


def is_xarraylike(xarr: Any) -> bool:
    """
    Return True iff the object is xarraylike:
    possessing .values, .dims, and .coords attributes,
    and whose .values are arraylike.

    :param arr: The object to check for xarraylike properties
    :return: True iff the object is xarraylike
    """
    return (
        hasattr(xarr, "values")
        and hasattr(xarr, "dims")
        and hasattr(xarr, "coords")
        and is_arraylike(xarr.values)
    )
