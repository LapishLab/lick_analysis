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
    # A leading offset belongs to a pulse that started before recording began.
    if events["Event"].iloc[0] == 0:
        events = events.iloc[1:]
    # A trailing onset has no recorded offset, so it cannot form a complete pulse.
    if not events.empty and events["Event"].iloc[-1] == 1:
        events = events.iloc[:-1]

    onsets = events.loc[events["Event"].eq(1)].reset_index(drop=True)
    offsets = events.loc[events["Event"].eq(0)].reset_index(drop=True)
    observed_widths_ms = (
        offsets["pi_time"].sub(onsets["pi_time"]).dt.total_seconds() * 1_000
    )

    return pd.DataFrame(
        {
            "pulse_index": range(len(onsets)),
            "pi_time": onsets["pi_time"],
            "observed_pulse_ms": observed_widths_ms,
        }
    )


def build_pi_sync_lookup_tables(
    pi_name: str,
    gpio_csv_path: Path,
    capacitance: pd.DataFrame,
    parameters: SyncParameters,
) -> pd.DataFrame:
    """Match a contiguous run of Pi pulses to the ESP32 pulse sequence."""
    esp32_pulses = make_esp32_sync_table(capacitance, parameters)
    tolerance_ms = parameters.pulse_step_ms / 2

    pi_pulses = load_pi_sync_pulses(gpio_csv_path, parameters)
    if len(pi_pulses) < 2:
        raise ValueError(f"{pi_name} needs at least two synchronization pulses")
    if len(pi_pulses) > len(esp32_pulses):
        raise ValueError(
            f"{pi_name} has {len(pi_pulses)} synchronization pulses, but "
            f"the ESP32 data has {len(esp32_pulses)}"
        )

    expected_widths = esp32_pulses["expected_pulse_ms"].to_numpy()
    observed_widths = pi_pulses["observed_pulse_ms"].to_numpy()
    matching_starts = [
        start
        for start in range(len(expected_widths) - len(observed_widths) + 1)
        if np.all(
            np.abs(expected_widths[start : start + len(observed_widths)] - observed_widths)
            <= tolerance_ms
        )
    ]
    if not matching_starts:
        raise ValueError(
            f"{pi_name} synchronization pulses do not match a contiguous "
            "portion of the ESP32 pulse sequence"
        )
    if len(matching_starts) > 1:
        raise ValueError(
            f"{pi_name} synchronization pulses match {len(matching_starts)} "
            "positions in the repeating ESP32 sequence; alignment is ambiguous"
        )

    pi_pulses = pi_pulses.assign(
        pulse_index=pi_pulses["pulse_index"] + matching_starts[0]
    )
    lookup = esp32_pulses.merge(
        pi_pulses,
        on="pulse_index",
        how="inner",
        validate="one_to_one",
    )
    error = lookup["observed_pulse_ms"] - lookup["expected_pulse_ms"]
    max_error_ms = error.abs().max()
    print(
        f"{pi_name}: {len(lookup)} synchronization points "
        f"(maximum pulse-width error: {max_error_ms:.1f} ms)"
    )

    return lookup


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
