from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


EXAMPLE_DATA_DIR = Path(
    r"C:\Users\daswyga\Desktop\fiber_lick\2026-10-26_08-58-30_NAc_dlight_rat1"
)

def main() -> None:
    csv_path = find_lickometer_csv(EXAMPLE_DATA_DIR)
    capacitance = load_lickometer_data(csv_path)
    plot_lickometer_data(capacitance, title=csv_path.stem)


def find_lickometer_csv(experiment_dir: Path) -> Path:
    """Find the CSV in the experiment's top-level lickometer directory."""
    csv_files = [
        csv_file
        for directory in experiment_dir.iterdir()
        if directory.is_dir() and directory.name.lower().startswith("lickometer")
        for csv_file in directory.glob("*.csv")
    ]

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV was found in a lickometer* folder under {experiment_dir}"
        )
    if len(csv_files) > 1:
        paths = "\n".join(f"  - {path}" for path in csv_files)
        raise RuntimeError(f"Expected one lickometer CSV, but found:\n{paths}")

    return csv_files[0]


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


def plot_lickometer_data(
    data: pd.DataFrame,
    title: str,
) -> None:
    """Plot left and right capacitance against cumulative recording time."""
    _, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    axis.plot(data["time_s"], data["left"], label="Left", linewidth=0.8)
    axis.plot(data["time_s"], data["right"], label="Right", linewidth=0.8)
    axis.set(
        title=title,
        xlabel="Cumulative time (seconds)",
        ylabel="Capacitance",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    plt.show()





if __name__ == "__main__":
    main()
