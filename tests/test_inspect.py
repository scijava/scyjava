"""
Tests for functions in inspect submodule.
"""

from scyjava import inspect
from scyjava.config import mode, Mode


class TestInspect(object):
    """
    Test scyjava.inspect convenience functions.
    """

    def test_inspect_members(self):
        if mode == Mode.JEP:
            # JEP does not support the jclass function.
            return
        members = []
        inspect.members("java.lang.Iterable", writer=members.append)
        expected = [
            "Source code URL: java.lang.NullPointerException",
            "                         * indicates static modifier",
            "java.util.Iterator         = iterator()",
            "java.util.Spliterator      = spliterator()",
            "void                       = forEach(java.util.function.Consumer)",
            "",
            "",
        ]
        assert expected == "".join(members).split("\n")
