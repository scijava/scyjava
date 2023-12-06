import math
from os import getcwd
from pathlib import Path

import numpy as np
import pytest

from scyjava import (
    Converter,
    add_java_converter,
    config,
    jarray,
    java_converters,
    jclass,
    jimport,
    jinstance,
    py_converters,
    to_java,
    to_python,
)
from scyjava.config import Mode, mode

config.endpoints.append("org.scijava:scijava-table")
config.enable_headless_mode()


class TestConvert(object):
    def testClass(self):
        """
        Test class detection from Java objects.
        """
        if mode == Mode.JEP:
            pytest.skip("The jclass function does not work yet in Jep mode.")

        int_class = jclass(to_java(5))
        assert "java.lang.Integer" == int_class.getName()

        long_class = jclass(to_java(4000000001))
        assert "java.lang.Long" == long_class.getName()

        bigint_class = jclass(to_java(9879999999999999789))
        assert "java.math.BigInteger" == bigint_class.getName()

        string_class = jclass(to_java("foobar"))
        assert "java.lang.String" == string_class.getName()

        list_class = jclass(to_java([1, 2, 3]))
        assert "java.util.ArrayList" == list_class.getName()

        map_class = jclass(to_java({"a": "b"}))
        assert "java.util.LinkedHashMap" == map_class.getName()

        assert "java.util.Map" == jclass("java.util.Map").getName()

    def testBoolean(self):
        jtrue = to_java(True)
        assert jinstance(jtrue, "java.lang.Boolean")
        assert jtrue.booleanValue() is True
        ptrue = to_python(jtrue)
        assert isinstance(ptrue, bool)
        assert ptrue is True

        jfalse = to_java(False)
        assert jinstance(jfalse, "java.lang.Boolean")
        assert jfalse.booleanValue() is False
        pfalse = to_python(jfalse)
        assert isinstance(pfalse, bool)
        assert pfalse is False

    def testByte(self):
        obyte = 5
        jbyte = to_java(obyte, type="b")
        assert jinstance(jbyte, "java.lang.Byte")
        assert obyte == jbyte.byteValue()
        pbyte = to_python(jbyte)
        assert isinstance(pbyte, int)
        assert obyte == pbyte

    def testShort(self):
        oshort = 5
        jshort = to_java(oshort, type="s")
        assert jinstance(jshort, "java.lang.Short")
        assert oshort == jshort.shortValue()
        pshort = to_python(jshort)
        assert isinstance(pshort, int)
        assert oshort == pshort

    def testInteger(self):
        oint = 5
        jint = to_java(oint)
        assert jinstance(jint, "java.lang.Integer")
        assert oint == jint.intValue()
        pint = to_python(jint)
        assert isinstance(pint, int)
        assert oint == pint

    def testLong(self):
        olong = 4000000001
        jlong = to_java(olong)
        assert jinstance(jlong, "java.lang.Long")
        assert olong == jlong.longValue()
        plong = to_python(jlong)
        assert isinstance(plong, int)
        assert olong == plong

    def testBigInteger(self):
        obi = 9879999999999999789
        jbi = to_java(obi)
        assert jinstance(jbi, "java.math.BigInteger")
        assert str(obi) == str(jbi.toString())
        pbi = to_python(jbi)
        assert isinstance(pbi, int)
        assert obi == pbi

    def testFloat(self):
        ofloat = 5.0
        jfloat = to_java(ofloat)
        assert jinstance(jfloat, "java.lang.Float")
        assert ofloat == jfloat.floatValue()
        pfloat = to_python(jfloat)
        assert isinstance(pfloat, float)
        assert ofloat == pfloat

    def testDouble(self):
        odouble = 4.56e123
        jdouble = to_java(odouble)
        assert jinstance(jdouble, "java.lang.Double")
        assert odouble == jdouble.doubleValue()
        pdouble = to_python(jdouble)
        assert isinstance(pdouble, float)
        assert odouble == pdouble

    def testInf(self):
        jinf = to_java(math.inf)
        assert jinstance(jinf, "java.lang.Float")
        assert math.inf == jinf.floatValue()
        pinf = to_python(jinf)
        assert isinstance(pinf, float)
        assert math.inf == pinf

        jninf = to_java(-math.inf)
        assert jinstance(jninf, "java.lang.Float")
        assert -math.inf == jninf.floatValue()
        pninf = to_python(jninf)
        assert isinstance(pninf, float)
        assert -math.inf == pninf

    def testNaN(self):
        jnan = to_java(math.nan)
        assert jinstance(jnan, "java.lang.Float")
        assert math.isnan(jnan.floatValue())
        pnan = to_python(jnan)
        assert isinstance(pnan, float)
        assert math.isnan(pnan)

    def testString(self):
        ostring = "Hello world!"
        jstring = to_java(ostring)
        assert jinstance(jstring, "java.lang.String")
        for e, a in zip(ostring, jstring.toCharArray()):
            assert e == a
        pstring = to_python(jstring)
        assert ostring == pstring

    def testList(self):
        olist = "The quick brown fox jumps over the lazy dogs".split()
        jlist = to_java(olist)
        for e, a in zip(olist, jlist):
            assert e == to_python(a)
        plist = to_python(jlist)
        assert olist == plist
        assert str(olist) == str(plist)
        assert plist[1] == "quick"
        plist[7] = "silly"
        assert "The quick brown fox jumps over the silly dogs" == " ".join(plist)

    def testSet(self):
        s = set(["orange", "apple", "pineapple", "plum"])
        js = to_java(s)
        assert len(s) == js.size()
        for e in s:
            assert js.contains(to_java(e))
        ps = to_python(js)
        assert s == ps
        assert str(s) == str(ps)

    def testPrimitiveIntArray(self):
        arr = jarray("i", 4)
        for i in range(len(arr)):
            arr[i] = i  # NB: assign Python int into Java int!
        py_arr = to_python(arr)
        if mode == Mode.JEP:
            assert type(py_arr).__name__ == "list"
        # JPype brings in a Numpy dependency from the start.
        # This dependency enables the Numpy converters
        # Since they take precedence, we'll actually see a ndarray
        # output from the conversion.
        elif mode == Mode.JPYPE:
            assert type(py_arr).__name__ == "ndarray"
        # NB: Comparing ndarray vs list results in a list of bools.
        assert np.array_equal(py_arr, [0, 1, 2, 3])

    def test2DStringArray(self):
        if mode == Mode.JEP:
            pytest.skip("jep cannot support 2+ dimensional arrays!")

        String = jimport("java.lang.String")
        arr = jarray(String, [3, 5])
        for i in range(len(arr)):
            for j in range(len(arr[i])):
                s = f"{i}, {j}"
                arr[i][j] = s  # NB: assign Python str to Java String!
        py_arr = to_python(arr)
        assert isinstance(py_arr, list)
        assert py_arr == [
            ["0, 0", "0, 1", "0, 2", "0, 3", "0, 4"],
            ["1, 0", "1, 1", "1, 2", "1, 3", "1, 4"],
            ["2, 0", "2, 1", "2, 2", "2, 3", "2, 4"],
        ]

    def testDict(self):
        d = {
            "access_log": [
                {"stored_proc": "getsomething"},
                {
                    "uses": [
                        {"usedin": "some->bread->crumb"},
                        {"usedin": "something else here"},
                        {"stored_proc": "anothersp"},
                    ]
                },
                {"uses": [{"usedin": "blahblah"}]},
            ],
            "reporting": [
                {"stored_proc": "reportingsp"},
                {"uses": [{"usedin": "breadcrumb"}]},
            ],
        }
        jd = to_java(d)
        assert len(d) == jd.size()
        for k, v in d.items():
            jk = to_java(k)
            jd.containsKey(jk)
            assert v == to_python(jd.get(jk))
        pd = to_python(jd)
        assert d == pd
        assert str(d) == str(pd)

    def testPath(self):
        py_path = Path(getcwd())
        j_path = to_java(py_path)
        assert jinstance(j_path, "java.nio.file.Path")
        assert str(j_path) == str(py_path)

        actual = to_python(j_path)
        assert actual == py_path

    def testMixed(self):
        test_dict = {"a": "b", "c": "d"}
        test_list = ["e", "f", "g", "h"]
        test_set = set(["i", "j", "k"])

        # mixed types in a dictionary
        mixed_dict = {"d": test_dict, "l": test_list, "s": test_set, "str": "hello"}
        j_mixed_dict = to_java(mixed_dict)
        assert len(mixed_dict) == j_mixed_dict.size()
        for k, v in mixed_dict.items():
            j_k = to_java(k)
            j_mixed_dict.containsKey(j_k)
            assert v == to_python(j_mixed_dict.get(j_k))
        p_mixed_dict = to_python(j_mixed_dict)
        assert mixed_dict == p_mixed_dict
        assert str(mixed_dict) == str(p_mixed_dict)

        # mixed types in a list
        mixed_list = [test_dict, test_list, test_set, "hello"]
        j_mixed_list = to_java(mixed_list)
        for e, a in zip(mixed_list, j_mixed_list):
            assert e == to_python(a)
        p_mixed_list = to_python(j_mixed_list)
        assert mixed_list == p_mixed_list
        assert str(mixed_list) == str(p_mixed_list)

    def testNone(self):
        d = {"key": None, None: "value", "foo": "bar"}
        jd = to_java(d)
        assert 3 == jd.size()
        assert None is jd.get("key")
        assert "value" == jd.get(None)
        assert "bar" == jd.get("foo")
        pd = to_python(jd)
        assert d == pd

    def testGentle(self):
        Object = jimport("java.lang.Object")
        unknown_thing = Object()
        converted_thing = to_python(unknown_thing, gentle=True)
        assert jinstance(converted_thing, Object)
        bad_conversion = None
        try:
            bad_conversion = to_python(unknown_thing)
        except BaseException:
            # NB: Failure is expected here.
            pass
        assert bad_conversion is None

    def testStructureWithSomeUnsupportedItems(self):
        # Create Java data structure with some challenging items.
        Object = jimport("java.lang.Object")
        jmap = to_java(
            {
                "list": ["a", Object(), 1],
                "set": {"x", Object(), 2},
                "object": Object(),
                "foo": "bar",
            }
        )

        if mode == Mode.JPYPE:
            assert "java.util.LinkedHashMap" == jclass(jmap).getName()
        elif mode == Mode.JEP:
            with pytest.raises(ValueError) as exc:
                assert "java.util.LinkedHashMap" == jclass(jmap).getName()
            assert (
                "ValueError: Jep does not support Java class objects "
                + "-- see https://github.com/ninia/jep/issues/405"
            ) == exc.exconly()

        # Convert it back to Python.
        pdict = to_python(jmap)
        assert pdict["list"][0] == "a"
        assert jinstance(pdict["list"][1], Object)
        assert pdict["list"][2] == 1
        assert "x" in pdict["set"]
        assert 2 in pdict["set"]
        assert len(pdict["set"]) == 3
        assert jinstance(pdict["object"], Object)
        assert pdict["foo"] == "bar"

    def test_conversion_priority(self):
        # Add a converter prioritized over the default converter
        String = jimport("java.lang.String")
        invader = "Not Hello World"

        bad_converter = Converter(
            name=f"test_conversion_priority: str -> '{invader}'",
            predicate=lambda obj: isinstance(obj, str),
            converter=lambda obj: String(invader.encode("utf-8"), "utf-8"),
            priority=100,
        )
        add_java_converter(bad_converter)

        # Ensure that the conversion uses our new converter
        s = "Hello world!"
        js = to_java(s)
        for e, a in zip(invader, js.toCharArray()):
            assert e == a

        java_converters.remove(bad_converter)

    def test_converter_priority(self):
        assert len(java_converters) > 0
        assert sorted(java_converters) == java_converters
        assert len(py_converters) > 0
        assert sorted(py_converters) == py_converters
