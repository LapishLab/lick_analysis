from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


EXAMPLE_DATA_DIR = Path(
    r"C:\Users\daswyga\Desktop\fiber_lick\2026-10-26_08-58-30_NAc_dlight_rat1"
)

class SyncParameters:
    INTERVAL_SAMPLES: int = 1_000
    PULSE_STEP_MS: int = 100
    PULSE_MAX_MS: int = 9_000
    PIN: int = 25


def main() -> None:
    csv_path = find_lickometer_csv(EXAMPLE_DATA_DIR)
    capacitance = load_lickometer_data(csv_path)
    sync_tables = build_pi_sync_lookup_tables(EXAMPLE_DATA_DIR, capacitance)

    for pi_name, sync_table in sync_tables.items():
        maximum_error_ms = sync_table["pulse_width_error_ms"].abs().max()
        print(
            f"{pi_name}: {len(sync_table)} synchronization points "
            f"(maximum pulse-width error: {maximum_error_ms:.3f} ms)"
        )

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


def find_pi_gpio_csvs(experiment_dir: Path) -> dict[str, Path]:
    """Find the GPIO event CSV belonging to each Raspberry Pi."""
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

    gpio_csvs: dict[str, Path] = {}
    for pi_directory in pi_data_directories[0].iterdir():
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
            f"No Raspberry Pi GPIO CSV files were found under "
            f"{pi_data_directories[0]}"
        )

    return gpio_csvs


def make_esp32_sync_table(capacitance: pd.DataFrame) -> pd.DataFrame:
    """Create the expected ESP32 synchronization pulse sequence."""
    sample_indices = list(
        range(0, len(capacitance), SyncParameters.INTERVAL_SAMPLES)
    )
    pulses_per_cycle = SyncParameters.PULSE_MAX_MS // SyncParameters.PULSE_STEP_MS
    pulse_indices = list(range(len(sample_indices)))
    expected_widths_ms = [
        (pulse_index % pulses_per_cycle + 1) * SyncParameters.PULSE_STEP_MS
        for pulse_index in pulse_indices
    ]

    return pd.DataFrame(
        {
            "pulse_index": pulse_indices,
            "sample_index": sample_indices,
            "esp32_time_s": capacitance.iloc[sample_indices]["time_s"].to_numpy(),
            "expected_pulse_ms": expected_widths_ms,
        }
    )


def load_pi_sync_pulses(gpio_csv_path: Path) -> pd.DataFrame:
    """Load and pair synchronization pulse onsets and offsets for one Pi."""
    events = pd.read_csv(gpio_csv_path)
    required_columns = ("Time", "Pin", "Event")
    missing_columns = set(required_columns).difference(events.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{gpio_csv_path} is missing required columns: {missing}")

    events["Pin"] = pd.to_numeric(events["Pin"], errors="raise")
    events["Event"] = pd.to_numeric(events["Event"], errors="raise")
    events = events.loc[events["Pin"].eq(SyncParameters.PIN)].copy()
    if events.empty:
        raise ValueError(
            f"{gpio_csv_path} contains no events for pin {SyncParameters.PIN}"
        )

    events["pi_time"] = pd.to_datetime(
        events["Time"],
        format="%Y%m%d_%H%M%S_%f",
        errors="raise",
    )
    events = events.sort_values("pi_time", ignore_index=True)

    expected_events = [1, 0] * (len(events) // 2)
    if len(events) % 2 or events["Event"].tolist() != expected_events:
        raise ValueError(
            f"Synchronization events in {gpio_csv_path} are not alternating "
            "onset/offset pairs"
        )

    onsets = events.iloc[0::2].reset_index(drop=True)
    offsets = events.iloc[1::2].reset_index(drop=True)
    observed_widths_ms = (
        offsets["pi_time"].sub(onsets["pi_time"]).dt.total_seconds() * 1_000
    )
    if observed_widths_ms.le(0).any():
        raise ValueError(f"{gpio_csv_path} contains a non-positive pulse duration")

    return pd.DataFrame(
        {
            "pulse_index": range(len(onsets)),
            "pi_time": onsets["pi_time"],
            "observed_pulse_ms": observed_widths_ms,
        }
    )


def build_pi_sync_lookup_tables(
    experiment_dir: Path,
    capacitance: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Associate each ESP32 sync time with both Raspberry Pi clocks."""
    esp32_pulses = make_esp32_sync_table(capacitance)
    tolerance_ms = SyncParameters.PULSE_STEP_MS / 2
    lookup_tables: dict[str, pd.DataFrame] = {}

    for pi_name, gpio_csv_path in find_pi_gpio_csvs(experiment_dir).items():
        pi_pulses = load_pi_sync_pulses(gpio_csv_path)
        if len(pi_pulses) != len(esp32_pulses):
            raise ValueError(
                f"{pi_name} has {len(pi_pulses)} synchronization pulses, but "
                f"the ESP32 data has {len(esp32_pulses)}"
            )

        lookup = esp32_pulses.merge(
            pi_pulses,
            on="pulse_index",
            how="inner",
            validate="one_to_one",
        )
        lookup["pulse_width_error_ms"] = (
            lookup["observed_pulse_ms"] - lookup["expected_pulse_ms"]
        )
        lookup["pulse_width_matches"] = lookup["pulse_width_error_ms"].abs().le(
            tolerance_ms
        )

        mismatches = lookup.loc[~lookup["pulse_width_matches"]]
        if not mismatches.empty:
            first = mismatches.iloc[0]
            raise ValueError(
                f"{pi_name} failed pulse-width verification at pulse "
                f"{int(first['pulse_index'])}: expected "
                f"{first['expected_pulse_ms']:.0f} ms, observed "
                f"{first['observed_pulse_ms']:.3f} ms"
            )

        lookup_tables[pi_name] = lookup

    return lookup_tables


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
