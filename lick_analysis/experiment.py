from pathlib import Path

import pandas as pd


def load_lickometer_data(csv_path: Path) -> pd.DataFrame:
    """Load a lickometer CSV and add cumulative recording time in seconds."""
    data = pd.read_csv(csv_path)

    required_columns = ("elapsed_us", "left", "right")
    missing_columns = set(required_columns).difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{csv_path} is missing required columns: {missing}")
    if data.empty:
        raise ValueError(f"{csv_path} contains no data rows")

    for column in required_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")
    if data.loc[:, required_columns].isna().any().any():
        raise ValueError(f"{csv_path} contains missing or invalid numeric values")

    data["time_s"] = data["elapsed_us"].cumsum() / 1_000_000
    return data
