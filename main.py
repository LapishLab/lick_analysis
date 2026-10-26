from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from numpy.typing import NDArray


EXAMPLE_DATA_DIR = Path(
    r"C:\Users\daswyga\Desktop\fiber_lick\2026-10-26_08-58-30_NAc_dlight_rat1"
)

class SyncParameters:
    INTERVAL_SAMPLES: int = 1_000
    PULSE_STEP_MS: int = 100
    PULSE_MAX_MS: int = 9_000
    PIN: int = 25


@dataclass
class PiVideo:
    """A Pi video with its wall-clock frame timestamps and decoder."""

    pi_name: str
    video_path: Path
    start_time: pd.Timestamp
    frame_pts_ms: NDArray[np.float64]
    sorted_pts_ms: NDArray[np.float64]
    sorted_frame_indices: NDArray[np.int64]
    capture: cv2.VideoCapture

    @classmethod
    def open(cls, pi_name: str, video_path: Path, pts_path: Path) -> "PiVideo":
        start_time = pd.to_datetime(
            video_path.stem,
            format="%Y%m%d_%H%M%S_%f",
            errors="raise",
        )
        pts_ms = pd.to_numeric(
            pd.read_csv(pts_path, header=None).iloc[:, 0],
            errors="raise",
        ).to_numpy(dtype=np.float64)

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video {video_path}")

        video_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        usable_frame_count = min(len(pts_ms), video_frame_count)
        if usable_frame_count == 0:
            capture.release()
            raise ValueError(f"No timestamped frames were found for {video_path}")

        # A recorder can write one final PTS even if its frame was not committed
        # to the MP4, so only retain timestamps with a corresponding video frame.
        pts_ms = pts_ms[:usable_frame_count]
        frame_indices = np.arange(usable_frame_count, dtype=np.int64)
        sort_order = np.argsort(pts_ms, kind="stable")

        return cls(
            pi_name=pi_name,
            video_path=video_path,
            start_time=start_time,
            frame_pts_ms=pts_ms,
            sorted_pts_ms=pts_ms[sort_order],
            sorted_frame_indices=frame_indices[sort_order],
            capture=capture,
        )

    def nearest_frame(
        self,
        target_time: pd.Timestamp,
    ) -> tuple[NDArray[np.uint8], int, pd.Timestamp, float]:
        """Decode the video frame nearest to a Pi wall-clock time."""
        target_pts_ms = (target_time - self.start_time).total_seconds() * 1_000
        insertion_index = int(np.searchsorted(self.sorted_pts_ms, target_pts_ms))
        candidate_indices = [
            index
            for index in (insertion_index - 1, insertion_index)
            if 0 <= index < len(self.sorted_pts_ms)
        ]
        nearest_index = min(
            candidate_indices,
            key=lambda index: abs(self.sorted_pts_ms[index] - target_pts_ms),
        )

        requested_frame_index = int(self.sorted_frame_indices[nearest_index])
        frame_index = requested_frame_index
        frame_bgr = None

        # Some MP4s report a few uncommitted frames at the end. Search nearby
        # indices so a boundary selection still returns the closest decodable
        # frame instead of failing the interaction.
        for distance in range(100):
            candidates = (
                [requested_frame_index]
                if distance == 0
                else [requested_frame_index - distance, requested_frame_index + distance]
            )
            for candidate in candidates:
                if not 0 <= candidate < len(self.frame_pts_ms):
                    continue
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, candidate)
                success, candidate_frame = self.capture.read()
                if success:
                    frame_index = candidate
                    frame_bgr = candidate_frame
                    break
            if frame_bgr is not None:
                break

        if frame_bgr is None:
            raise RuntimeError(
                f"Could not decode a frame near {requested_frame_index} from "
                f"{self.video_path}"
            )

        frame_pts_ms = float(self.frame_pts_ms[frame_index])
        frame_rgb = np.asarray(
            cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
            dtype=np.uint8,
        )
        frame_time = pd.Timestamp(
            self.start_time + pd.to_timedelta(frame_pts_ms, unit="ms")
        )
        difference_ms = float(
            (frame_time - target_time).total_seconds() * 1_000
        )
        return frame_rgb, frame_index, frame_time, difference_ms

    def close(self) -> None:
        self.capture.release()


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

    camera_files = find_pi_camera_files(EXAMPLE_DATA_DIR)
    plot_lickometer_data(
        capacitance,
        sync_tables,
        camera_files,
        title=csv_path.stem,
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


def find_pi_camera_files(
    experiment_dir: Path,
) -> dict[str, tuple[Path, Path]]:
    """Find each Pi's matching MP4 video and frame timestamp file."""
    camera_files: dict[str, tuple[Path, Path]] = {}

    for pi_name, gpio_csv_path in find_pi_gpio_csvs(experiment_dir).items():
        camera_directory = gpio_csv_path.parent.parent / "cam"
        video_files = list(camera_directory.glob("*.mp4"))
        if len(video_files) != 1:
            raise RuntimeError(
                f"Expected one MP4 for {pi_name}, but found {len(video_files)}"
            )

        video_path = video_files[0]
        pts_path = video_path.with_suffix(".pts")
        if not pts_path.is_file():
            raise FileNotFoundError(
                f"No matching PTS file was found for {video_path}"
            )
        camera_files[pi_name] = (video_path, pts_path)

    return camera_files


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
    return base_pi_time + pd.to_timedelta(target_elapsed_s, unit="s")


def plot_lickometer_data(
    data: pd.DataFrame,
    sync_tables: dict[str, pd.DataFrame],
    camera_files: dict[str, tuple[Path, Path]],
    title: str,
) -> None:
    """Interactively show capacitance and synchronized Pi video frames."""
    if set(sync_tables) != set(camera_files):
        raise ValueError(
            "The synchronization tables and camera recordings do not contain "
            "the same Raspberry Pis"
        )

    pi_names = sorted(sync_tables)
    videos = {
        pi_name: PiVideo.open(pi_name, *camera_files[pi_name])
        for pi_name in pi_names
    }

    figure = plt.figure(figsize=(14, 9), constrained_layout=True)
    grid = figure.add_gridspec(
        3,
        len(pi_names),
        height_ratios=(0.65, 0.85, 1.1),
    )
    overview_axis = figure.add_subplot(grid[0, :])
    zoom_axis = figure.add_subplot(grid[1, :])
    video_axes = {
        pi_name: figure.add_subplot(grid[2, column])
        for column, pi_name in enumerate(pi_names)
    }

    for axis in (overview_axis, zoom_axis):
        axis.plot(data["time_s"], data["left"], label="Left", linewidth=0.8)
        axis.plot(data["time_s"], data["right"], label="Right", linewidth=0.8)
        axis.set(ylabel="Capacitance")
        axis.grid(alpha=0.25)

    overview_axis.set(
        title=title,
    )
    overview_axis.legend()
    zoom_axis.set_xlabel("Cumulative time (seconds)")

    time_values = data["time_s"].to_numpy(dtype=np.float64)
    current_sample_index = 0
    chosen_time_s = float(time_values[current_sample_index])
    recording_start_s = float(time_values[0])
    recording_end_s = float(time_values[-1])
    zoom_duration_s = min(5.0, recording_end_s - recording_start_s)
    zoom_window_start_s = recording_start_s
    zoom_window_end_s = recording_start_s + zoom_duration_s

    zoom_window = Rectangle(
        (zoom_window_start_s, 0),
        zoom_duration_s,
        1,
        transform=overview_axis.get_xaxis_transform(),
        facecolor="tab:purple",
        edgecolor="tab:purple",
        alpha=0.18,
        linewidth=1.2,
    )
    overview_axis.add_patch(zoom_window)
    zoom_center_marker = overview_axis.axvline(
        zoom_window_start_s + zoom_duration_s / 2,
        color="tab:purple",
        linestyle="--",
        linewidth=1.2,
        alpha=0.9,
    )
    overview_time_marker = overview_axis.axvline(
        chosen_time_s,
        color="tab:red",
        linewidth=1.5,
        zorder=3,
    )
    zoom_time_marker = zoom_axis.axvline(
        chosen_time_s,
        color="tab:red",
        linewidth=1.5,
    )
    chosen_time_text = zoom_axis.set_title("", loc="left", pad=2)
    image_artists = {}

    def update_zoom_window(center_time_s: float) -> None:
        nonlocal zoom_window_start_s, zoom_window_end_s
        zoom_window_start_s = float(
            np.clip(
                center_time_s - zoom_duration_s / 2,
                recording_start_s,
                recording_end_s - zoom_duration_s,
            )
        )
        zoom_window_end_s = zoom_window_start_s + zoom_duration_s
        zoom_window.set_x(zoom_window_start_s)
        zoom_window.set_width(zoom_duration_s)
        zoom_center_marker.set_xdata(
            [
                zoom_window_start_s + zoom_duration_s / 2,
                zoom_window_start_s + zoom_duration_s / 2,
            ]
        )
        zoom_axis.set_xlim(zoom_window_start_s, zoom_window_end_s)

        first_visible = int(np.searchsorted(time_values, zoom_window_start_s))
        past_visible = int(np.searchsorted(time_values, zoom_window_end_s, side="right"))
        visible = data.iloc[first_visible:past_visible]
        if not visible.empty:
            minimum = float(visible[["left", "right"]].min().min())
            maximum = float(visible[["left", "right"]].max().max())
            padding = max((maximum - minimum) * 0.05, 1.0)
            zoom_axis.set_ylim(minimum - padding, maximum + padding)

        figure.canvas.draw_idle()

    def update_chosen_sample(new_sample_index: int) -> None:
        nonlocal current_sample_index
        current_sample_index = int(np.clip(new_sample_index, 0, len(data) - 1))
        new_time_s = float(time_values[current_sample_index])
        if not zoom_window_start_s <= new_time_s <= zoom_window_end_s:
            update_zoom_window(new_time_s)
        overview_time_marker.set_xdata([new_time_s, new_time_s])
        zoom_time_marker.set_xdata([new_time_s, new_time_s])
        chosen_time_text.set_text(f"ESP32 time: {new_time_s:.3f}s")

        for pi_name in pi_names:
            target_pi_time = esp32_time_to_pi_time(
                new_time_s,
                sync_tables[pi_name],
            )
            frame, frame_index, _, difference_ms = videos[
                pi_name
            ].nearest_frame(target_pi_time)
            video_axis = video_axes[pi_name]

            if pi_name in image_artists:
                image_artists[pi_name].set_data(frame)
            else:
                image_artists[pi_name] = video_axis.imshow(frame)
                video_axis.set_axis_off()

            video_axis.set_title(
                f"{pi_name} - frame {frame_index:,} ({difference_ms:+.0f} ms)"
            )

        figure.canvas.draw_idle()

    def choose_time_from_click(event) -> None:
        if event.inaxes is overview_axis and event.xdata is not None:
            update_zoom_window(event.xdata)
        elif event.inaxes is zoom_axis and event.xdata is not None:
            insertion_index = int(np.searchsorted(time_values, event.xdata))
            candidate_indices = [
                index
                for index in (insertion_index - 1, insertion_index)
                if 0 <= index < len(time_values)
            ]
            nearest_sample_index = min(
                candidate_indices,
                key=lambda index: abs(time_values[index] - event.xdata),
            )
            update_chosen_sample(nearest_sample_index)

    def choose_time_from_key(event) -> None:
        if event.key == "left":
            update_chosen_sample(current_sample_index - 1)
        elif event.key == "right":
            update_chosen_sample(current_sample_index + 1)

    figure.canvas.mpl_connect("button_press_event", choose_time_from_click)
    figure.canvas.mpl_connect("key_press_event", choose_time_from_key)
    update_zoom_window(recording_start_s + zoom_duration_s / 2)
    update_chosen_sample(current_sample_index)

    try:
        plt.show()
    finally:
        for video in videos.values():
            video.close()


if __name__ == "__main__":
    main()
