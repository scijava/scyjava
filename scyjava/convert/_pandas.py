# Pandas <-> Scijava Table converters.
import jnius
import scyjava


def _import_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError:
        msg = "The Pandas library is missing (http://pandas.pydata.org/). "
        msg += "Please instal it using: "
        msg += "conda install pandas (prefered)"
        msg += " or "
        msg += "pip install pandas."
        raise Exception(msg)


def table_to_pandas(table):
    pd = _import_pandas()

    data = []
    headers = []
    for i, column in enumerate(table.toArray()):
        data.append(column.toArray())
        headers.append(table.getColumnHeader(i))
    df = pd.DataFrame(data).T
    df.columns = headers
    return df


def pandas_to_table(df):
    pd = _import_pandas()

    if len(df.dtypes.unique()) > 1:
        TableClass = jnius.autoclass('org.scijava.table.DefaultGenericTable')
    else:
        table_type = df.dtypes.unique()[0]
        if table_type.name.startswith('float'):
            TableClass = jnius.autoclass('org.scijava.table.DefaultFloatTable')
        elif table_type.name.startswith('int'):
            TableClass = jnius.autoclass('org.scijava.table.DefaultIntTable')
        elif table_type.name.startswith('bool'):
            TableClass = jnius.autoclass('org.scijava.table.DefaultBoolTable')
        else:
            msg = "The type '{}' is not supported.".format(table_type.name)
            raise Exception(msg)

    table = TableClass(*df.shape[::-1])

    for c, column_name in enumerate(df.columns):
        table.setColumnHeader(c, column_name)

    for i, (index, row) in enumerate(df.iterrows()):
        for c, value in enumerate(row):
            header = df.columns[c]
            table.set(header, i, scyjava.to_java(value))

    return table
