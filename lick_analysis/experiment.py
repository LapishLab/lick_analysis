from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class ExperimentFiles:
    """Input files discovered within one experiment directory."""

    lickometer_csv: Path
    gpio_csvs: dict[str, Path]
    camera_files: dict[str, tuple[Path, Path]]


def discover_experiment(experiment_dir: Path) -> ExperimentFiles:
    """Discover the lickometer, GPIO, video, and frame timestamp files."""
    gpio_csvs = find_pi_gpio_csvs(experiment_dir)
    return ExperimentFiles(
        lickometer_csv=find_lickometer_csv(experiment_dir),
        gpio_csvs=gpio_csvs,
        camera_files=find_pi_camera_files(gpio_csvs),
    )


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


def find_pi_data_directory(experiment_dir: Path) -> Path:
    """Find the experiment's single top-level Pi data directory."""
    pi_data_directories = [
        directory
        for directory in experiment_dir.iterdir()
        if directory.is_dir() and directory.name.lower().startswith("pi-data")
    ]
    if len(pi_data_directories) != 1:
        raise RuntimeError(
            f"Expected one pi-data* folder under {experiment_dir}, "
            f"but found {len(pi_data_directories)}"
        )
    return pi_data_directories[0]


def find_pi_gpio_csvs(experiment_dir: Path) -> dict[str, Path]:
    """Find the GPIO event CSV belonging to each Raspberry Pi."""
    pi_data_directory = find_pi_data_directory(experiment_dir)
    gpio_csvs: dict[str, Path] = {}

    for pi_directory in pi_data_directory.iterdir():
        gpio_directory = pi_directory / "gpio"
        if not pi_directory.is_dir() or not gpio_directory.is_dir():
            continue

        csv_files = list(gpio_directory.glob("*.csv"))
        if len(csv_files) != 1:
            raise RuntimeError(
                f"Expected one GPIO CSV for {pi_directory.name}, "
                f"but found {len(csv_files)}"
            )
        gpio_csvs[pi_directory.name] = csv_files[0]

    if not gpio_csvs:
        raise FileNotFoundError(
            f"No Raspberry Pi GPIO CSV files were found under {pi_data_directory}"
        )

    return gpio_csvs


def find_pi_camera_files(
    gpio_csvs: dict[str, Path],
) -> dict[str, tuple[Path, Path]]:
    """Find each Pi's matching MP4 video and frame timestamp file."""
    camera_files: dict[str, tuple[Path, Path]] = {}

    for pi_name, gpio_csv_path in gpio_csvs.items():
        camera_directory = gpio_csv_path.parent.parent / "cam"
        video_files = list(camera_directory.glob("*.mp4"))
        if len(video_files) != 1:
            raise RuntimeError(
                f"Expected one MP4 for {pi_name}, but found {len(video_files)}"
            )

        video_path = video_files[0]
        pts_path = video_path.with_suffix(".pts")
        if not pts_path.is_file():
            raise FileNotFoundError(f"No matching PTS file was found for {video_path}")
        camera_files[pi_name] = (video_path, pts_path)

    return camera_files
