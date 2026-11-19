"""Explore per-frame contact predictions alongside their source video.

Usage: python prediction_video_viewer.py predictions.csv video.mp4
Click either trace to select a frame; use Left/Right to step one video frame.
"""

import argparse
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.patches import Rectangle


def load_predictions(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    required = {"frame", "timestamp_ms", "contact_probability"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    if data.empty:
        raise ValueError(f"{path} has no predictions")

    for name in required:
        data[name] = pd.to_numeric(data[name], errors="raise")
    if not np.isfinite(data[list(required)].to_numpy(dtype=float)).all():
        raise ValueError(f"{path} contains missing or non-finite prediction values")
    frames = data["frame"].to_numpy()
    if (frames < 0).any() or (frames != np.floor(frames)).any():
        raise ValueError("Frame numbers must be nonnegative integers")
    data["frame"] = data["frame"].astype(np.int64)
    data = data.sort_values("frame").reset_index(drop=True)
    if data["frame"].duplicated().any():
        raise ValueError("Frame numbers must be unique")
    if not data["timestamp_ms"].is_monotonic_increasing:
        raise ValueError("Prediction timestamps must increase with frame number")
    return data


class PredictionVideoViewer:
    """Three-panel Matplotlib viewer with direct video-frame navigation."""

    def __init__(self, predictions: pd.DataFrame, video_path: Path, zoom_seconds: float = 5.0):
        if zoom_seconds <= 0:
            raise ValueError("Zoom duration must be positive")
        self.capture = cv2.VideoCapture(str(video_path))
        if not self.capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        try:
            self.frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if self.frame_count <= 0:
                raise ValueError(f"Video has no frames: {video_path}")
            self.predictions = predictions.loc[predictions["frame"] < self.frame_count]
            if self.predictions.empty:
                raise ValueError("No prediction frames occur within the video")

            self.frame_numbers = self.predictions["frame"].to_numpy(dtype=np.int64)
            self.times_s = self.predictions["timestamp_ms"].to_numpy(dtype=float) / 1000
            self.probabilities = self.predictions["contact_probability"].to_numpy(dtype=float)
            self.start_s = float(self.times_s[0])
            self.end_s = float(self.times_s[-1])
            self.zoom_seconds = min(zoom_seconds, self.end_s - self.start_s)
            self.current_frame = int(self.frame_numbers[0])
            self.next_decoded_frame = None

            # Matplotlib's toolbar also assigns Left/Right to history navigation.
            for name in ("keymap.back", "keymap.forward"):
                plt.rcParams[name] = [key for key in plt.rcParams[name] if key not in ("left", "right")]

            self.figure = plt.figure(figsize=(13, 9), constrained_layout=True)
            grid = self.figure.add_gridspec(3, 1, height_ratios=(1, 1.2, 2.7))
            self.overview_axis = self.figure.add_subplot(grid[0])
            self.zoom_axis = self.figure.add_subplot(grid[1])
            self.video_axis = self.figure.add_subplot(grid[2])
            self.figure.suptitle(video_path.name)

            for axis in (self.overview_axis, self.zoom_axis):
                axis.plot(self.times_s, self.probabilities, color="tab:green", linewidth=0.8)
                axis.set_ylabel("Contact probability")
                axis.set_ylim(-0.05, 1.05)
                axis.grid(alpha=0.25)
            self.overview_axis.set_title("Full prediction trace", loc="left")
            self.zoom_axis.set_title("Zoomed prediction trace", loc="left")
            self.zoom_axis.set_xlabel("Video time (seconds)")
            self.overview_axis.set_xlim(self.start_s, self.end_s)

            self.zoom_window = Rectangle(
                (self.start_s, 0), self.zoom_seconds, 1,
                transform=self.overview_axis.get_xaxis_transform(),
                facecolor="tab:purple", alpha=0.16, edgecolor="tab:purple",
            )
            self.overview_axis.add_patch(self.zoom_window)
            self.overview_marker = self.overview_axis.axvline(self.start_s, color="tab:red")
            self.zoom_marker = self.zoom_axis.axvline(self.start_s, color="tab:red")

            self.video_axis.set_axis_off()
            self.image = None
            self.figure.canvas.mpl_connect("button_press_event", self._on_click)
            self.figure.canvas.mpl_connect("key_press_event", self._on_key)
            self.figure.canvas.mpl_connect("close_event", lambda event: self.close())
            self.show_frame(self.current_frame)
        except Exception:
            self.capture.release()
            raise

    def _time_for_frame(self, frame: int) -> float:
        return float(np.interp(frame, self.frame_numbers, self.times_s))

    def show_frame(self, frame: int) -> None:
        frame = int(np.clip(frame, 0, self.frame_count - 1))
        if frame != self.next_decoded_frame:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        success, image_bgr = self.capture.read()
        if not success:
            raise RuntimeError(f"Could not decode video frame {frame}")
        self.current_frame = frame
        self.next_decoded_frame = frame + 1

        height, width = image_bgr.shape[:2]
        if width > 640:
            image_bgr = cv2.resize(image_bgr, (640, round(height * 640 / width)),
                                   interpolation=cv2.INTER_AREA)
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        if self.image is None:
            self.image = self.video_axis.imshow(image_rgb)
        else:
            self.image.set_data(image_rgb)

        time_s = self._time_for_frame(frame)
        self.overview_marker.set_xdata([time_s, time_s])
        self.zoom_marker.set_xdata([time_s, time_s])
        if self.zoom_seconds > 0:
            start = float(np.clip(time_s - self.zoom_seconds / 2, self.start_s,
                                  self.end_s - self.zoom_seconds))
            self.zoom_axis.set_xlim(start, start + self.zoom_seconds)
            self.zoom_window.set_x(start)
        else:
            self.zoom_axis.set_xlim(time_s - 0.5, time_s + 0.5)
        self.video_axis.set_title(f"Frame {frame:,}  |  {time_s:.3f} s")
        self.figure.canvas.draw_idle()

    def _on_click(self, event: MouseEvent) -> None:
        if event.button != 1 or event.inaxes not in (self.overview_axis, self.zoom_axis):
            return
        if event.xdata is None:
            return
        index = int(np.searchsorted(self.times_s, event.xdata))
        candidates = [i for i in (index - 1, index) if 0 <= i < len(self.times_s)]
        nearest = min(candidates, key=lambda i: abs(self.times_s[i] - event.xdata))
        self.show_frame(int(self.frame_numbers[nearest]))

    def _on_key(self, event: KeyEvent) -> None:
        if event.key == "right":
            self.show_frame(self.current_frame + 1)
        elif event.key == "left":
            self.show_frame(self.current_frame - 1)

    def close(self) -> None:
        self.capture.release()

    def show(self) -> None:
        try:
            plt.show()
        finally:
            self.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions_csv", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("--zoom-seconds", type=float, default=5.0,
                        help="Width of the zoomed trace (default: 5 seconds)")
    args = parser.parse_args()
    predictions = load_predictions(args.predictions_csv)
    PredictionVideoViewer(predictions, args.video, args.zoom_seconds).show()


PRED = "/research/lapishla/dlc/jobs/PV2CAP_ephys2/videos/predictions/053_20250908.csv"
VID = "/research/lapishla/dlc/jobs/PV2CAP_ephys2/videos/053_20250908.mp4"
predictions = load_predictions(Path(PRED))

PredictionVideoViewer(predictions, Path(VID), zoom_seconds=30).show()
# if __name__ == "__main__":
#     main()
