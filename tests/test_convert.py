from os import getcwd
from pathlib import Path

from jpype import JByte

from scyjava import Converter, config, jarray, jclass, jimport, to_java, to_python

config.endpoints.append("org.scijava:scijava-table")
config.add_option("-Djava.awt.headless=true")


class TestConvert(object):
    def testClass(self):
        """
        Tests class detection from Java objects.
        """
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
        jt = to_java(True)
        assert jt.booleanValue()
        pt = to_python(jt)
        assert pt
        assert "True" == str(pt)
        jf = to_java(False)
        assert not jf.booleanValue()
        pf = to_python(jf)
        assert not pf
        assert "False" == str(pf)

    def testByte(self):
        # NB we can't (yet) convert TO Bytes, since there is not (yet)
        # a great type to convert FROM. We convert python ints to Integers
        i = 5
        ji = JByte(i)
        pi = to_python(ji)
        assert i == pi
        assert str(i) == str(pi)

    def testInteger(self):
        i = 5
        ji = to_java(i)
        assert i == ji.intValue()
        pi = to_python(ji)
        assert i == pi
        assert str(i) == str(pi)

    def testLong(self):
        long = 4000000001
        jlong = to_java(long)
        assert long == jlong.longValue()
        plong = to_python(jlong)
        assert long == plong
        assert str(long) == str(plong)

    def testBigInteger(self):
        bi = 9879999999999999789
        jbi = to_java(bi)
        assert bi == int(str(jbi.toString()))
        pbi = to_python(jbi)
        assert bi == pbi
        assert str(bi) == str(pbi)

    def testFloat(self):
        f = 5.0
        jf = to_java(f)
        assert f == jf.floatValue()
        pf = to_python(jf)
        assert f == pf
        assert str(f) == str(pf)

    def testDouble(self):
        Float = jimport("java.lang.Float")
        d = Float.MAX_VALUE * 2
        jd = to_java(d)
        assert d == jd.doubleValue()
        pd = to_python(jd)
        assert d == pd
        assert str(d) == str(pd)

    def testString(self):
        s = "Hello world!"
        js = to_java(s)
        for e, a in zip(s, js.toCharArray()):
            assert e == a
        ps = to_python(js)
        assert s == ps
        assert str(s) == str(ps)

    def testList(self):
        list = "The quick brown fox jumps over the lazy dogs".split()
        jlist = to_java(list)
        for e, a in zip(list, jlist):
            assert e == to_python(a)
        plist = to_python(jlist)
        assert list == plist
        assert str(list) == str(plist)
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
        assert type(py_arr).__name__ == "ndarray"
        # NB: Comparing ndarray vs list results in a list of bools.
        assert all(py_arr == [0, 1, 2, 3])

    def test2DStringArray(self):
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
        assert isinstance(j_path, jimport("java.nio.file.Path"))
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
        assert isinstance(converted_thing, Object)
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
        assert "java.util.LinkedHashMap" == jclass(jmap).getName()

        # Convert it back to Python.
        pdict = to_python(jmap)
        assert pdict["list"][0] == "a"
        assert isinstance(pdict["list"][1], Object)
        assert pdict["list"][2] == 1
        assert "x" in pdict["set"]
        assert 2 in pdict["set"]
        assert len(pdict["set"]) == 3
        assert isinstance(pdict["object"], Object)
        assert pdict["foo"] == "bar"

    def test_conversion_priority(self):
        # Add a converter prioritized over the default converter
        String = jimport("java.lang.String")
        invader = "Not Hello World"

        from scyjava import add_java_converter

        add_java_converter(
            Converter(
                predicate=lambda obj: isinstance(obj, str),
                converter=lambda obj: String(invader.encode("utf-8"), "utf-8"),
                priority=100,
            )
        )

        # Ensure that the conversion uses our new converter
        s = "Hello world!"
        js = to_java(s)
        for e, a in zip(invader, js.toCharArray()):
            assert e == a
