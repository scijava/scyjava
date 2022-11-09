import numpy as np
import numpy.testing as npt
import pandas as pd
from jpype import JBoolean, JFloat, JInt, JString

from scyjava import config, jimport, jinstance, to_java, to_python

config.endpoints.append("org.scijava:scijava-table")
config.add_option("-Djava.awt.headless=true")


def assert_same_table(table, df):
    assert len(table.toArray()) == df.shape[1]
    assert len(table.toArray()[0].toArray()) == df.shape[0]

    for i, column in enumerate(table.toArray()):
        npt.assert_array_almost_equal(df.iloc[:, i].values, column.toArray())

        assert table.getColumnHeader(i) == df.columns[i]


class TestPandas(object):
    def testPandasToTable(self):
        # Float table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5))

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultFloatTable")

        # Int table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5)) * 100
        array = array.astype("int")

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultIntTable")

        # Bool table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5)) > 0.5

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        assert jinstance(table, "org.scijava.table.DefaultBoolTable")

        # Mixed table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
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
        # Float table
        table = jimport("org.scijava.table.DefaultFloatTable")()
        table.appendColumns(["header1", "header2", "header3", "header4", "header5"])
        table.setRowCount(7)
        array = np.random.random(size=(7, 5))

        table = self._fill_table(table, array, JFloat)
        df = to_python(table)

        assert_same_table(table, df)
        for col in df.columns:
            assert df.dtypes[col] == np.float64

        # Int table
        table = jimport("org.scijava.table.DefaultIntTable")()
        table.appendColumns(["header1", "header2", "header3", "header4", "header5"])
        table.setRowCount(7)
        array = np.random.random(size=(7, 5)) * 100
        array = array.astype("int32")

        table = self._fill_table(table, array, JInt)
        df = to_python(table)

        assert_same_table(table, df)
        for col in df.columns:
            assert df.dtypes[col] == np.int64

        # Bool table
        table = jimport("org.scijava.table.DefaultBoolTable")()
        table.appendColumns(["header1", "header2", "header3", "header4", "header5"])
        table.setRowCount(7)
        array = np.random.random(size=(7, 5)) > 0.5

        table = self._fill_table(table, array, JBoolean)
        df = to_python(table)

        assert_same_table(table, df)
        for col in df.columns:
            assert df.dtypes[col] == np.bool8

        # Mixed table
        table = jimport("org.scijava.table.DefaultGenericTable")()
        table.appendColumns(["header1", "header2", "header3", "header4"])
        table.setRowCount(7)
        array_float = np.random.random(size=(7, 1))
        array_int = np.random.random(size=(7, 1)) * 100
        array_int = array_int.astype("int32")
        array_bool = np.random.random(size=(7, 1)) > 0.5
        array_str = np.array(["foo", "bar", "foobar", "barfoo", "oofrab", "oof", "rab"])

        # fill mixed table
        for i in range(table.getRowCount()):
            table.set(0, i, JFloat(array_float[i]))
            table.set(1, i, JInt(array_int[i].item()))
            table.set(2, i, JBoolean(array_bool[i]))
            table.set(3, i, JString(array_str[i]))

        df = to_python(table)
        # Table types cannot be the same here, unless we want to cast.
        # assert_same_table(table, df)
        assert type(df["header1"][0]) == float
        assert type(df["header2"][0]) == int
        assert type(df["header3"][0]) == bool
        assert type(df["header4"][0]) == str

    def _fill_table(self, table, ndarr, type):
        for i in range(table.getColumnCount()):
            s = ndarr[:, i]
            for j in range(table.getRowCount()):
                table.setValue(i, j, type(s[j]))
        return table
