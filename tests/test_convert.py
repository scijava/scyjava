import scyjava_config
scyjava_config.add_repositories({'imagej.public': 'https://maven.imagej.net/content/groups/public'})
scyjava_config.add_endpoints('org.scijava:scijava-table')

import unittest
import pandas as pd
import numpy as np
from scyjava.convert import jclass, to_java, to_python
import scyjava
import jnius


def assert_same_table(table, df):
    import numpy.testing as npt

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
        self.assertEqual(bi, int(jbi.toString()))
        pbi = to_python(jbi)
        self.assertEqual(bi, pbi)
        self.assertEqual(str(bi), str(pbi))

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

    def testPandasToTable(self):
        # Float table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5))

        df = pd.DataFrame(array, columns=columns)
        table = scyjava.to_java(df)

        assert_same_table(table, df)
        assert type(table) == jnius.autoclass('org.scijava.table.DefaultFloatTable')

        # Int table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5)) * 100
        array = array.astype('int')

        df = pd.DataFrame(array, columns=columns)
        table = scyjava.to_java(df)

        assert_same_table(table, df)
        assert type(table) == jnius.autoclass('org.scijava.table.DefaultIntTable')

        # Bool table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5)) > 0.5

        df = pd.DataFrame(array, columns=columns)
        table = scyjava.to_java(df)

        assert_same_table(table, df)
        assert type(table) == jnius.autoclass('org.scijava.table.DefaultBoolTable')

        # Mixed table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5))

        df = pd.DataFrame(array, columns=columns)

        # Convert column 0 to integer
        df.iloc[:, 0] = (df.iloc[:, 0] * 100).astype('int')
        # Convert column 1 to bool
        df.iloc[:, 1] = df.iloc[:, 1] > 0.5
        # Convert column 2 to string
        df.iloc[:, 2] = df.iloc[:, 2].to_string(index=False).split('\n')

        table = scyjava.to_java(df)

        # Table types cannot be the same here, unless we want to cast.
        # assert_same_table(table, df)
        assert type(table) == jnius.autoclass('org.scijava.table.DefaultGenericTable')


if __name__ == '__main__':
    unittest.main()
