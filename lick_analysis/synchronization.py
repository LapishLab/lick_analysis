from pathlib import Path

import numpy as np
import pandas as pd

from .config import SyncParameters


def make_esp32_sync_table(
    capacitance: pd.DataFrame,
    parameters: SyncParameters,
) -> pd.DataFrame:
    """Create the expected ESP32 synchronization pulse sequence."""
    sample_indices = list(
        range(0, len(capacitance), parameters.interval_samples)
    )
    pulses_per_cycle = parameters.pulse_max_ms // parameters.pulse_step_ms
    pulse_indices = list(range(len(sample_indices)))
    expected_widths_ms = [
        (pulse_index % pulses_per_cycle + 1) * parameters.pulse_step_ms
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


def load_pi_sync_pulses(
    gpio_csv_path: Path,
    parameters: SyncParameters,
) -> pd.DataFrame:
    """Load and pair synchronization pulse onsets and offsets for one Pi."""
    events = pd.read_csv(gpio_csv_path)
    required_columns = ("Time", "Pin", "Event")
    missing_columns = set(required_columns).difference(events.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{gpio_csv_path} is missing required columns: {missing}")

    events["Pin"] = pd.to_numeric(events["Pin"], errors="raise")
    events["Event"] = pd.to_numeric(events["Event"], errors="raise")
    events = events.loc[events["Pin"].eq(parameters.pin)].copy()
    if events.empty:
        raise ValueError(
            f"{gpio_csv_path} contains no events for pin {parameters.pin}"
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
    gpio_csvs: dict[str, Path],
    capacitance: pd.DataFrame,
    parameters: SyncParameters,
) -> dict[str, pd.DataFrame]:
    """Associate each ESP32 sync time with each Raspberry Pi clock."""
    esp32_pulses = make_esp32_sync_table(capacitance, parameters)
    tolerance_ms = parameters.pulse_step_ms / 2
    lookup_tables: dict[str, pd.DataFrame] = {}

    for pi_name, gpio_csv_path in gpio_csvs.items():
        pi_pulses = load_pi_sync_pulses(gpio_csv_path, parameters)
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


def esp32_time_to_pi_time(
    esp32_time_s: float,
    sync_table: pd.DataFrame,
) -> pd.Timestamp:
    """Interpolate an ESP32 recording time onto a Pi wall clock."""
    esp32_times = sync_table["esp32_time_s"].to_numpy(dtype=np.float64)
    if len(esp32_times) < 2:
        raise ValueError("At least two synchronization points are required")
    if np.any(np.diff(esp32_times) <= 0):
        raise ValueError("ESP32 synchronization times must be strictly increasing")

    base_pi_time = sync_table["pi_time"].iloc[0]
    pi_elapsed_s = (
        sync_table["pi_time"].sub(base_pi_time).dt.total_seconds().to_numpy()
    )

    insertion_index = int(np.searchsorted(esp32_times, esp32_time_s))
    if insertion_index == 0:
        left_index, right_index = 0, 1
    elif insertion_index == len(esp32_times):
        left_index, right_index = len(esp32_times) - 2, len(esp32_times) - 1
    else:
        left_index, right_index = insertion_index - 1, insertion_index

    fraction = (esp32_time_s - esp32_times[left_index]) / (
        esp32_times[right_index] - esp32_times[left_index]
    )
    target_elapsed_s = pi_elapsed_s[left_index] + fraction * (
        pi_elapsed_s[right_index] - pi_elapsed_s[left_index]
    )
    return pd.Timestamp(
        base_pi_time + pd.to_timedelta(target_elapsed_s, unit="s")
    )
