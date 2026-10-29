from pathlib import Path

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def load_financial_file(file_path: str) -> pd.DataFrame:
    """
    Load a supported financial data file into a pandas DataFrame.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path)

    raise ValueError(
        f"Unsupported file type: {path.suffix}. "
        f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )
