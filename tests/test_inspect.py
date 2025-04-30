"""
Tests for functions in inspect submodule.
"""

import re

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
            "Source code URL: https://github.com/openjdk/jdk/blob/"
            ".../share/classes/java/lang/Iterable.java",
            "                         * indicates static modifier",
            "java.util.Iterator         = iterator()",
            "java.util.Spliterator      = spliterator()",
            "void                       = forEach(java.util.function.Consumer)",
            "",
            "",
        ]
        pattern = (
            r"(https://github.com/openjdk/jdk/blob/)"
            "[^ ]*(/share/classes/java/lang/Iterable\.java)"
        )
        members_string = re.sub(pattern, r"\1...\2", "".join(members))
        assert members_string.split("\n") == expected
