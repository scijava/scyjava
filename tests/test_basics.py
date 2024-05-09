import re

import pytest

import scyjava
from scyjava.config import Mode, mode


class TestBasics(object):
    """
    Test basic scyjava functions.
    """

    def test_jclass(self):
        """
        Test the jclass function.
        """
        if mode == Mode.JEP:
            pytest.skip("Jep does not support Java class objects!")
        c = scyjava.jclass("java.lang.Object")
        assert scyjava.jinstance(c, "java.lang.Class")
        assert str(c.toString()) == "class java.lang.Object"

    def test_jimport(self):
        """
        Test the jimport function.
        """
        Object = scyjava.jimport("java.lang.Object")
        assert Object is not None
        assert str(Object)
        o = Object()
        assert scyjava.jinstance(o, "java.lang.Object")
        assert re.match("java.lang.Object@[0-9a-f]{7}", str(o.toString()))

    def test_jinstance(self):
        """
        Test the jinstance function.
        """
        jstr = scyjava.to_java("Hello")
        assert scyjava.jinstance(jstr, "java.lang.String")

        jint = scyjava.to_java(5)
        assert scyjava.jinstance(jint, "java.lang.Integer")

        jfloat = scyjava.to_java(3.5)
        assert scyjava.jinstance(jfloat, "java.lang.Float")

        jlist = scyjava.to_java([3, 2, 1])
        assert scyjava.jinstance(jlist, "java.util.List")
        assert scyjava.jinstance(jlist, "java.util.ArrayList")
