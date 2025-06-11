import pandas as pd


def build_dataframe(data: dict, columns=None):
    if columns is None or not isinstance(columns, (list, tuple)):
        raise ValueError("Columns must be a list of strings.")
    
    # Build the index
    index = pd.MultiIndex.from_tuples(list(data.keys()))
    # Build the DataFrame
    df = pd.DataFrame(list(data.values()), index=index)
    # Reset the index and set the column names
    df = df.reset_index()
    df.columns = columns
    return df