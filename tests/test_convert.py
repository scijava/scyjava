from jpype import JArray, JInt, JLong
from scyjava import Converter, config, jclass, jimport, start_jvm, to_java, to_python

config.endpoints.append("org.scijava:scijava-table")
config.add_option("-Djava.awt.headless=true")


def assert_same_table(table, df):
    assert len(table.toArray()) == df.shape[1]
    assert len(table.toArray()[0].toArray()) == df.shape[0]

    for i, column in enumerate(table.toArray()):
        npt.assert_array_almost_equal(df.iloc[:, i].values, column.toArray())

        assert table.getColumnHeader(i) == df.columns[i]


class TestConvert(object):
    def testClass(self):
        """
        Tests class detection from Java objects.
        """
        int_class = jclass(to_java(5))
        "java.lang.Integer" == int_class.getName()

        long_class = jclass(to_java(4000000001))
        "java.lang.Long" == long_class.getName()

        bigint_class = jclass(to_java(9879999999999999789))
        "java.math.BigInteger" == bigint_class.getName()

        string_class = jclass(to_java("foobar"))
        "java.lang.String" == string_class.getName()

        list_class = jclass(to_java([1, 2, 3]))
        assert "java.util.ArrayList" == list_class.getName()

        map_class = jclass(to_java({"a": "b"}))
        "java.util.LinkedHashMap" == map_class.getName()

        "java.util.Map" == jclass("java.util.Map").getName()

    def testBoolean(self):
        jt = to_java(True)
        assert True == jt.booleanValue()
        pt = to_python(jt)
        assert True == pt
        assert "True" == str(pt)
        jf = to_java(False)
        assert False == jf.booleanValue()
        pf = to_python(jf)
        assert False == pf
        assert "False" == str(pf)

    def testInteger(self):
        i = 5
        ji = to_java(i)
        assert i == ji.intValue()
        pi = to_python(ji)
        assert i == pi
        assert str(i) == str(pi)

    def testLong(self):
        l = 4000000001
        jl = to_java(l)
        assert l == jl.longValue()
        pl = to_python(jl)
        assert l == pl
        assert str(l) == str(pl)

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
        l = "The quick brown fox jumps over the lazy dogs".split()
        jl = to_java(l)
        for e, a in zip(l, jl):
            assert e == to_python(a)
        pl = to_python(jl)
        assert l == pl
        assert str(l) == str(pl)
        assert pl[1] == "quick"
        pl[7] = "silly"
        assert "The quick brown fox jumps over the silly dogs" == " ".join(pl)

    def testSet(self):
        s = set(["orange", "apple", "pineapple", "plum"])
        js = to_java(s)
        assert len(s) == js.size()
        for e in s:
            assert js.contains(to_java(e))
        ps = to_python(js)
        assert s == ps
        assert str(s) == str(ps)

    def testArray(self):
        start_jvm()
        arr = JArray(JInt)(4)
        for i in range(len(arr)):
            arr[i] = to_java(i)
        py_arr = to_python(arr)
        assert py_arr == [0, 1, 2, 3]

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

    def testMixed(self):
        d = {"a": "b", "c": "d"}
        l = ["e", "f", "g", "h"]
        s = set(["i", "j", "k"])

        # mixed types in a dictionary
        md = {"d": d, "l": l, "s": s, "str": "hello"}
        jmd = to_java(md)
        assert len(md) == jmd.size()
        for k, v in md.items():
            jk = to_java(k)
            jmd.containsKey(jk)
            assert v == to_python(jmd.get(jk))
        pmd = to_python(jmd)
        assert md == pmd
        assert str(md) == str(pmd)

        # mixed types in a list
        ml = [d, l, s, "hello"]
        jml = to_java(ml)
        for e, a in zip(ml, jml):
            assert e == to_python(a)
        pml = to_python(jml)
        assert ml == pml
        assert str(ml) == str(pml)

    def testNone(self):
        d = {"key": None, None: "value", "foo": "bar"}
        jd = to_java(d)
        assert 3 == jd.size()
        assert None == jd.get("key")
        assert "value" == jd.get(None)
        assert "bar" == jd.get("foo")
        pd = to_python(jd)
        assert d == pd

    def testGentle(self):
        Object = jimport("java.lang.Object")
        unknown_thing = Object()
        converted_thing = to_python(unknown_thing, gentle=True)
        assert type(converted_thing) == Object
        bad_conversion = None
        try:
            bad_conversion = to_python(unknown_thing)
        except:
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
        l = pdict["list"]
        assert pdict["list"][0] == "a"
        assert type(pdict["list"][1]) == Object
        assert pdict["list"][2] == 1
        assert "x" in pdict["set"]
        assert 2 in pdict["set"]
        assert len(pdict["set"]) == 3
        assert type(pdict["object"]) == Object
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
