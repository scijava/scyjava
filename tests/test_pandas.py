import numpy as np
import numpy.testing as npt
import pandas as pd

from scyjava import config, jarray, jimport, jinstance, to_java, to_python

config.endpoints.append("org.scijava:scijava-table")
config.enable_headless_mode()


def assert_same_table(table, df):
    assert len(table.toArray()) == df.shape[1]
    assert len(table.toArray()[0].toArray()) == df.shape[0]

    for i, column in enumerate(table.toArray()):
        npt.assert_array_almost_equal(df.iloc[:, i].values, column.toArray())

        assert table.getColumnHeader(i) == df.columns[i]


class TestPandas(object):
    def testPandasToTable(self):
        columns = ["header1", "header2", "header3", "header4", "header5"]

        # Float table.
        array = np.random.random(size=(7, 5))

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultFloatTable")

        # Int table.
        array = np.random.random(size=(7, 5)) * 100
        array = array.astype("int")

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultIntTable")

        # Bool table.
        array = np.random.random(size=(7, 5)) > 0.5

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultBoolTable")

        # Mixed table.
        array = np.random.random(size=(7, 5))

        df = pd.DataFrame(array, columns=columns)

        # Convert column 0 to integer
        df.iloc[:, 0] = (df.iloc[:, 0] * 100).astype("int")
        # Convert column 1 to bool
        df.iloc[:, 1] = df.iloc[:, 1] > 0.5
        # Convert column 2 to string
        df.iloc[:, 2] = df.iloc[:, 2].to_string(index=False).split("\n")

        table = to_java(df)

        # Table types cannot be the same here, unless we want to cast.
        # assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultGenericTable")

    def testTabletoPandas(self):
        Boolean = jimport("java.lang.Boolean")
        Double = jimport("java.lang.Double")
        Float = jimport("java.lang.Float")
        Integer = jimport("java.lang.Integer")
        String = jimport("java.lang.String")

        columns = jarray(String, [5])
        for i in range(5):
            columns[i] = f"header{i + 1}"

        # Float table
        table = jimport("org.scijava.table.DefaultFloatTable")()
        table.appendColumns(columns)
        table.setRowCount(7)
        array = np.random.random(size=(7, 5))

        table = self._fill_table(table, array, lambda v: Float(float(v)))
        df = to_python(table)

        assert_same_table(table, df)
        for col in df.columns:
            assert df.dtypes[col] == np.float64

        # Int table
        table = jimport("org.scijava.table.DefaultIntTable")()
        table.appendColumns(columns)
        table.setRowCount(7)
        array = np.random.random(size=(7, 5)) * 100
        array = array.astype("int32")

        table = self._fill_table(table, array, lambda v: Integer(int(v)))
        df = to_python(table)

        assert_same_table(table, df)
        for col in df.columns:
            assert df.dtypes[col] == np.int64

        # Bool table
        table = jimport("org.scijava.table.DefaultBoolTable")()
        table.appendColumns(columns)
        table.setRowCount(7)
        array = np.random.random(size=(7, 5)) > 0.5

        table = self._fill_table(table, array, lambda v: Boolean(bool(v)))
        df = to_python(table)

        assert_same_table(table, df)
        for col in df.columns:
            assert df.dtypes[col] == np.bool_

        # Mixed table
        table = jimport("org.scijava.table.DefaultGenericTable")()
        table.appendColumns(columns)
        table.setRowCount(7)
        array_float = np.random.random(size=(7, 1))
        array_int = np.random.random(size=(7, 1)) * 100
        array_int = array_int.astype("int32")
        array_bool = np.random.random(size=(7, 1)) > 0.5
        array_str = np.array(["foo", "bar", "foobar", "barfoo", "oofrab", "oof", "rab"])
        array_double = np.random.random(size=(7, 1))
        array_double = array_double.astype("float64")

        # fill mixed table
        for i in range(table.getRowCount()):
            table.set(0, i, Float(float(array_float[i])))
            table.set(1, i, Integer(int(array_int[i].item())))
            table.set(2, i, Boolean(bool(array_bool[i])))
            table.set(3, i, String(array_str[i]))
            table.set(4, i, Double(float(array_double[i])))

        df = to_python(table)
        # Table types cannot be the same here, unless we want to cast.
        # assert_same_table(table, df)
        assert type(df["header1"][0]) is float
        assert type(df["header2"][0]) is int
        assert type(df["header3"][0]) is bool
        assert type(df["header4"][0]) is str
        assert type(df["header5"][0]) is float

    def _fill_table(self, table, ndarr, ctor):
        for i in range(table.getColumnCount()):
            s = ndarr[:, i]
            for j in range(table.getRowCount()):
                table.setValue(i, j, ctor(s[j]))
        return table
