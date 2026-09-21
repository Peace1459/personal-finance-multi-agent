import pandas as pd

def read_transactions(file_path: str):
    return pd.read_csv(file_path)
