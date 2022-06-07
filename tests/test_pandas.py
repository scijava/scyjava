import numpy as np
import numpy.testing as npt
import pandas as pd

from scyjava import config, jimport, to_java

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
        DefaultFloatTable = jimport("org.scijava.table.DefaultFloatTable")
        assert isinstance(table, DefaultFloatTable)

        # Int table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5)) * 100
        array = array.astype("int")

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        DefaultIntTable = jimport("org.scijava.table.DefaultIntTable")
        assert isinstance(table, DefaultIntTable)

        # Bool table.
        columns = ["header1", "header2", "header3", "header4", "header5"]
        array = np.random.random(size=(7, 5)) > 0.5

        df = pd.DataFrame(array, columns=columns)
        table = to_java(df)

        assert_same_table(table, df)
        DefaultBoolTable = jimport("org.scijava.table.DefaultBoolTable")
        assert isinstance(table, DefaultBoolTable)

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
        DefaultGenericTable = jimport("org.scijava.table.DefaultGenericTable")
        assert isinstance(table, DefaultGenericTable)
