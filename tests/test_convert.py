import unittest
from scyjava import config, jclass, jimport, to_java, to_python

config.endpoints.append('org.scijava:scijava-table')
config.add_option('-Djava.awt.headless=true')

def assert_same_table(table, df):
    assert len(table.toArray()) == df.shape[1]
    assert len(table.toArray()[0].toArray()) == df.shape[0]

    for i, column in enumerate(table.toArray()):
        npt.assert_array_almost_equal(df.iloc[:, i].values, column.toArray())

        assert table.getColumnHeader(i) == df.columns[i]


class TestConvert(unittest.TestCase):

    def testClass(self):
        """
        Tests class detection from Java objects.
        """
        int_class = jclass(to_java(5))
        self.assertEqual('java.lang.Integer', int_class.getName())

        long_class = jclass(to_java(4000000001))
        self.assertEqual('java.lang.Long', long_class.getName())

        bigint_class = jclass(to_java(9879999999999999789))
        self.assertEqual('java.math.BigInteger', bigint_class.getName())

        string_class = jclass(to_java('foobar'))
        self.assertEqual('java.lang.String', string_class.getName())

        list_class = jclass(to_java([1, 2, 3]))
        self.assertEqual('java.util.ArrayList', list_class.getName())

        map_class = jclass(to_java({'a':'b'}))
        self.assertEqual('java.util.LinkedHashMap', map_class.getName())

        self.assertEqual('java.util.Map', jclass('java.util.Map').getName())

    def testBoolean(self):
        jt = to_java(True)
        self.assertEqual(True, jt.booleanValue())
        pt = to_python(jt)
        self.assertEqual(True, pt)
        self.assertEqual('True', str(pt))
        jf = to_java(False)
        self.assertEqual(False, jf.booleanValue())
        pf = to_python(jf)
        self.assertEqual(False, pf)
        self.assertEqual('False', str(pf))

    def testInteger(self):
        i = 5
        ji = to_java(i)
        self.assertEqual(i, ji.intValue())
        pi = to_python(ji)
        self.assertEqual(i, pi)
        self.assertEqual(str(i), str(pi))

    def testLong(self):
        l = 4000000001
        jl = to_java(l)
        self.assertEqual(l, jl.longValue())
        pl = to_python(jl)
        self.assertEqual(l, pl)
        self.assertEqual(str(l), str(pl))

    def testBigInteger(self):
        bi = 9879999999999999789
        jbi = to_java(bi)
        self.assertEqual(bi, int(str(jbi.toString())))
        pbi = to_python(jbi)
        self.assertEqual(bi, pbi)
        self.assertEqual(str(bi), str(pbi))

    def testFloat(self):
        f = 5.
        jf = to_java(f)
        self.assertEqual(f, jf.floatValue())
        pf = to_python(jf)
        self.assertEqual(f, pf)
        self.assertEqual(str(f), str(pf))

    def testDouble(self):
        Float = jimport('java.lang.Float')
        d = Float.MAX_VALUE * 2
        jd = to_java(d)
        self.assertEqual(d, jd.doubleValue())
        pd = to_python(jd)
        self.assertEqual(d, pd)
        self.assertEqual(str(d), str(pd))

    def testString(self):
        s = 'Hello world!'
        js = to_java(s)
        for e, a in zip(s, js.toCharArray()):
            self.assertEqual(e, a)
        ps = to_python(js)
        self.assertEqual(s, ps)
        self.assertEqual(str(s), str(ps))

    def testList(self):
        l = 'The quick brown fox jumps over the lazy dogs'.split()
        jl = to_java(l)
        for e, a in zip(l, jl):
            self.assertEqual(e, to_python(a))
        pl = to_python(jl)
        self.assertEqual(l, pl)
        self.assertEqual(str(l), str(pl))
        self.assertEqual(pl[1], 'quick')
        pl[7] = 'silly'
        self.assertEqual('The quick brown fox jumps over the silly dogs', ' '.join(pl))

    def testSet(self):
        s = set(['orange', 'apple', 'pineapple', 'plum'])
        js = to_java(s)
        self.assertEqual(len(s), js.size())
        for e in s:
            self.assertTrue(js.contains(to_java(e)))
        ps = to_python(js)
        self.assertEqual(s, ps)
        self.assertEqual(str(s), str(ps))

    def testDict(self):
        d = {
            'access_log': [
                {'stored_proc': 'getsomething'},
                {'uses': [
                    {'usedin': 'some->bread->crumb'},
                    {'usedin': 'something else here'},
                    {'stored_proc': 'anothersp'}
                ]},
                {'uses': [
                    {'usedin': 'blahblah'}
                ]}
            ],
            'reporting': [
                {'stored_proc': 'reportingsp'},
                {'uses': [{'usedin': 'breadcrumb'}]}
            ]
        }
        jd = to_java(d)
        self.assertEqual(len(d), jd.size())
        for k, v in d.items():
            jk = to_java(k)
            self.assertTrue(jd.containsKey(jk))
            self.assertEqual(v, to_python(jd.get(jk)))
        pd = to_python(jd)
        self.assertEqual(d, pd)
        self.assertEqual(str(d), str(pd))

    def testMixed(self):
        d = {'a':'b', 'c':'d'}
        l = ['e', 'f', 'g', 'h']
        s = set(['i', 'j', 'k'])

        # mixed types in a dictionary
        md = {'d': d, 'l': l, 's': s, 'str': 'hello'}
        jmd = to_java(md)
        self.assertEqual(len(md), jmd.size())
        for k, v in md.items():
            jk = to_java(k)
            self.assertTrue(jmd.containsKey(jk))
            self.assertEqual(v, to_python(jmd.get(jk)))
        pmd = to_python(jmd)
        self.assertEqual(md, pmd)
        self.assertEqual(str(md), str(pmd))

        # mixed types in a list
        ml = [d, l, s, 'hello']
        jml = to_java(ml)
        for e, a in zip(ml, jml):
            self.assertEqual(e, to_python(a))
        pml = to_python(jml)
        self.assertEqual(ml, pml)
        self.assertEqual(str(ml), str(pml))

    def testNone(self):
        d = {'key':None, None:'value', 'foo':'bar'}
        jd = to_java(d)
        self.assertEqual(3, jd.size())
        self.assertEqual(None, jd.get('key'))
        self.assertEqual('value', jd.get(None))
        self.assertEqual('bar', jd.get('foo'))
        pd = to_python(jd)
        self.assertEqual(d, pd)

    def testGentle(self):
        Object = jimport('java.lang.Object')
        unknown_thing = Object()
        converted_thing = to_python(unknown_thing, gentle=True)
        assert type(converted_thing) == Object
        bad_conversion = None
        try:
            bad_conversion = to_python(unknown_thing)
        except:
            # NB: Failure is expected here.
            pass
        self.assertIsNone(bad_conversion)

    def testStructureWithSomeUnsupportedItems(self):
        # Create Java data structure with some challenging items.
        Object = jimport('java.lang.Object')
        jmap = to_java({
            'list': ['a', Object(), 1],
            'set': {'x', Object(), 2},
            'object': Object(),
            'foo': 'bar'
        })
        self.assertEqual('java.util.LinkedHashMap', jclass(jmap).getName())

        # Convert it back to Python.
        pdict = to_python(jmap)
        l = pdict['list']
        self.assertEqual(pdict['list'][0], 'a')
        assert type(pdict['list'][1]) == Object
        assert pdict['list'][2] == 1
        assert 'x' in pdict['set']
        assert 2 in pdict['set']
        assert len(pdict['set']) == 3
        assert type(pdict['object']) == Object
        self.assertEqual(pdict['foo'], 'bar')


    def test_conversion_priority(self):
        # Add a converter prioritized over the default converter
        String = jimport('java.lang.String')
        invader = 'Not Hello World'

        from scyjava import add_java_converter
        add_java_converter(
            predicate=lambda obj: isinstance(obj, str),
            converter=lambda obj: String(invader.encode('utf-8'), 'utf-8'),
            priority=100
        )

        # Ensure that the conversion uses our new converter
        s = 'Hello world!'
        js = to_java(s)
        for e, a in zip(invader, js.toCharArray()):
            self.assertEqual(e, a)


if __name__ == '__main__':
    unittest.main()
