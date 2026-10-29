from collections.abc import Iterable
from typing import Protocol, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import DrawEvent, KeyEvent, MouseEvent
from matplotlib.image import AxesImage
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import BboxBase
from matplotlib.widgets import TextBox

from .config import ViewerSettings
from .synchronization import esp32_time_to_pi_time
from .video import PiVideo


class BlittingCanvas(Protocol):
    """Backend canvas operations omitted from Matplotlib's base canvas stub."""

    def copy_from_bbox(self, bbox: BboxBase) -> object: ...

    def restore_region(self, region: object) -> None: ...

    def blit(self, bbox: BboxBase | None = None) -> None: ...


class LickometerViewer:
    """Interactive capacitance and synchronized-video viewer."""

    def __init__(
        self,
        capacitance: pd.DataFrame,
        sync_tables: dict[str, pd.DataFrame],
        videos: dict[str, PiVideo],
        settings: ViewerSettings,
        title: str,
    ) -> None:
        if set(sync_tables) != set(videos):
            raise ValueError(
                "The synchronization tables and videos do not contain "
                "the same Raspberry Pis"
            )
        if not videos:
            raise ValueError("At least one Raspberry Pi video is required")

        self.capacitance = capacitance
        self.sync_tables = sync_tables
        self.videos = videos
        self.settings = settings
        self.pi_names = sorted(sync_tables)
        self.time_values = capacitance["time_s"].to_numpy(dtype=np.float64)
        self.current_sample_index = 0
        self.video_lag_s = 0.0

        self.figure = plt.figure(figsize=(14, 9), constrained_layout=True)
        self.use_blitting = self.figure.canvas.supports_blit
        self.blitting_canvas = cast(BlittingCanvas, self.figure.canvas)
        grid = self.figure.add_gridspec(
            3,
            len(self.pi_names),
            height_ratios=(0.65, 0.85, 1.1),
        )
        self.overview_axis = self.figure.add_subplot(grid[0, :])
        self.zoom_axis = self.figure.add_subplot(grid[1, :])
        self.video_axes = {
            pi_name: self.figure.add_subplot(grid[2, column])
            for column, pi_name in enumerate(self.pi_names)
        }
        self.lag_axis = self.figure.add_axes((0.86, 0.965, 0.09, 0.025))
        self.lag_text_box = TextBox(
            self.lag_axis,
            "Video lag (s): ",
            initial="0.000",
        )
        self.figure.suptitle(title)

        for axis in (self.overview_axis, self.zoom_axis):
            axis.plot(
                capacitance["time_s"],
                capacitance["left"],
                label="Left",
                linewidth=0.8,
            )
            axis.plot(
                capacitance["time_s"],
                capacitance["right"],
                label="Right",
                linewidth=0.8,
            )
            axis.set(ylabel="Capacitance")
            axis.grid(alpha=0.25)

        self.overview_axis.legend()
        self.zoom_axis.set_xlabel("Cumulative time (seconds)")

        chosen_time_s = float(self.time_values[self.current_sample_index])
        self.recording_start_s = float(self.time_values[0])
        self.recording_end_s = float(self.time_values[-1])
        self.zoom_duration_s = min(
            settings.zoom_duration_s,
            self.recording_end_s - self.recording_start_s,
        )
        self.zoom_window_start_s = self.recording_start_s
        self.zoom_window_end_s = self.recording_start_s + self.zoom_duration_s

        self.zoom_window = Rectangle(
            (self.zoom_window_start_s, 0),
            self.zoom_duration_s,
            1,
            transform=self.overview_axis.get_xaxis_transform(),
            facecolor="tab:purple",
            edgecolor="tab:purple",
            alpha=0.18,
            linewidth=1.2,
            animated=self.use_blitting,
        )
        self.overview_axis.add_patch(self.zoom_window)
        self.zoom_center_marker = self.overview_axis.axvline(
            self.zoom_window_start_s + self.zoom_duration_s / 2,
            color="tab:purple",
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
            animated=self.use_blitting,
        )
        self.overview_time_marker = self.overview_axis.axvline(
            chosen_time_s,
            color="tab:red",
            linewidth=1.5,
            zorder=3,
            animated=self.use_blitting,
        )
        self.zoom_time_marker = self.zoom_axis.axvline(
            chosen_time_s,
            color="tab:red",
            linewidth=1.5,
            animated=self.use_blitting,
        )
        self.chosen_time_text = self.zoom_axis.set_title("", loc="left", pad=2)
        self.chosen_time_text.set_animated(self.use_blitting)
        (self.measurement_line,) = self.zoom_axis.plot(
            [],
            [],
            color="tab:orange",
            marker="o",
            linewidth=1.5,
            markersize=5,
            zorder=5,
            animated=self.use_blitting,
        )
        self.measurement_text = self.zoom_axis.text(
            0.02, 0.96, "", transform=self.zoom_axis.transAxes,
            va="top", ha="left", color="tab:orange",
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
            animated=self.use_blitting,
        )
        self._measurement_start: tuple[float, float] | None = None
        self._measurement_dragged = False

        self.image_artists: dict[str, AxesImage] = {}
        self.displayed_frame_indices: dict[str, int] = {}
        self.video_title_artists: dict[str, Text] = {}
        self.axis_backgrounds: dict[Axes, object] = {}
        self.axis_blit_boxes: dict[Axes, BboxBase] = {}

        self.figure.canvas.mpl_connect(
            "button_press_event",
            self._choose_time_from_click,
        )
        self.figure.canvas.mpl_connect(
            "button_press_event", self._start_measurement
        )
        self.figure.canvas.mpl_connect(
            "motion_notify_event", self._update_measurement
        )
        self.figure.canvas.mpl_connect(
            "button_release_event", self._finish_measurement
        )
        self.figure.canvas.mpl_connect(
            "key_press_event",
            self._choose_time_from_key,
        )
        self.lag_text_box.on_submit(self._update_video_lag)
        self._update_zoom_window(
            self.recording_start_s + self.zoom_duration_s / 2
        )
        self._update_chosen_sample(self.current_sample_index)
        self.figure.canvas.mpl_connect(
            "draw_event",
            self._cache_axis_backgrounds,
        )
        self.figure.canvas.draw()

    def _dynamic_artists_for_axis(self, axis: Axes) -> list[Artist]:
        if axis is self.overview_axis:
            return [
                self.zoom_window,
                self.zoom_center_marker,
                self.overview_time_marker,
            ]
        if axis is self.zoom_axis:
            return [
                self.zoom_time_marker,
                self.chosen_time_text,
                self.measurement_line,
                self.measurement_text,
            ]

        for pi_name, video_axis in self.video_axes.items():
            if axis is video_axis and pi_name in self.image_artists:
                return [
                    self.image_artists[pi_name],
                    self.video_title_artists[pi_name],
                ]
        return []

    def _refresh_dynamic_axes(self, axes: Iterable[Axes]) -> None:
        """Blit only dynamic artists on the axes that changed."""
        if not self.use_blitting:
            self.figure.canvas.draw_idle()
            return
        if not self.axis_backgrounds:
            return

        for axis in axes:
            background = self.axis_backgrounds.get(axis)
            blit_box = self.axis_blit_boxes.get(axis)
            if background is None or blit_box is None:
                continue
            self.blitting_canvas.restore_region(background)
            for artist in self._dynamic_artists_for_axis(axis):
                axis.draw_artist(artist)
            self.blitting_canvas.blit(blit_box)

    def _cache_axis_backgrounds(self, event: DrawEvent) -> None:
        """Cache static panel backgrounds after a full draw or resize."""
        if not self.use_blitting:
            return

        axes = [self.overview_axis, self.zoom_axis, *self.video_axes.values()]
        self.axis_backgrounds.clear()
        self.axis_blit_boxes.clear()
        for axis in axes:
            blit_box = axis.get_tightbbox(event.renderer)
            if blit_box is None:
                continue
            self.axis_blit_boxes[axis] = blit_box
            self.axis_backgrounds[axis] = self.blitting_canvas.copy_from_bbox(
                blit_box
            )
        self._refresh_dynamic_axes(axes)

    def _update_zoom_window(self, center_time_s: float) -> None:
        self.zoom_window_start_s = float(
            np.clip(
                center_time_s - self.zoom_duration_s / 2,
                self.recording_start_s,
                self.recording_end_s - self.zoom_duration_s,
            )
        )
        self.zoom_window_end_s = self.zoom_window_start_s + self.zoom_duration_s
        self.zoom_window.set_x(self.zoom_window_start_s)
        self.zoom_window.set_width(self.zoom_duration_s)
        center_s = self.zoom_window_start_s + self.zoom_duration_s / 2
        self.zoom_center_marker.set_xdata([center_s, center_s])
        self.zoom_axis.set_xlim(
            self.zoom_window_start_s,
            self.zoom_window_end_s,
        )

        first_visible = int(
            np.searchsorted(self.time_values, self.zoom_window_start_s)
        )
        past_visible = int(
            np.searchsorted(
                self.time_values,
                self.zoom_window_end_s,
                side="right",
            )
        )
        visible = self.capacitance.iloc[first_visible:past_visible]
        if not visible.empty:
            minimum = float(visible[["left", "right"]].min().min())
            maximum = float(visible[["left", "right"]].max().max())
            padding = max((maximum - minimum) * 0.05, 1.0)
            self.zoom_axis.set_ylim(minimum - padding, maximum + padding)

        if not self.use_blitting:
            self.figure.canvas.draw_idle()
        elif self.axis_backgrounds:
            self.figure.canvas.draw()

    def _update_chosen_sample(self, new_sample_index: int) -> None:
        changed_axes = {self.overview_axis, self.zoom_axis}
        self.current_sample_index = int(
            np.clip(new_sample_index, 0, len(self.capacitance) - 1)
        )
        new_time_s = float(self.time_values[self.current_sample_index])
        if not self.zoom_window_start_s <= new_time_s <= self.zoom_window_end_s:
            self._update_zoom_window(new_time_s)
        self.overview_time_marker.set_xdata([new_time_s, new_time_s])
        self.zoom_time_marker.set_xdata([new_time_s, new_time_s])
        self.chosen_time_text.set_text(f"ESP32 time: {new_time_s:.3f}s")

        for pi_name in self.pi_names:
            target_pi_time = esp32_time_to_pi_time(
                new_time_s,
                self.sync_tables[pi_name],
            )
            target_pi_time = pd.Timestamp(
                target_pi_time + pd.to_timedelta(self.video_lag_s, unit="s")
            )
            frame, frame_index, _, difference_ms = self.videos[
                pi_name
            ].nearest_frame(target_pi_time)
            video_axis = self.video_axes[pi_name]

            frame_changed = (
                self.displayed_frame_indices.get(pi_name) != frame_index
            )
            if pi_name not in self.image_artists:
                self.image_artists[pi_name] = video_axis.imshow(
                    frame,
                    animated=self.use_blitting,
                )
                video_axis.set_axis_off()
            elif frame_changed:
                self.image_artists[pi_name].set_data(frame)

            if frame_changed:
                self.displayed_frame_indices[pi_name] = frame_index
                self.video_title_artists[pi_name] = video_axis.set_title(
                    f"{pi_name} - frame {frame_index:,} "
                    f"({difference_ms:+.0f} ms)"
                )
                self.video_title_artists[pi_name].set_animated(
                    self.use_blitting
                )
                changed_axes.add(video_axis)

        self._refresh_dynamic_axes(changed_axes)

    def _update_video_lag(self, text: str) -> None:
        try:
            new_lag_s = float(text)
        except ValueError:
            self.lag_text_box.ax.set_facecolor("mistyrose")
            self.figure.canvas.draw_idle()
            return

        self.video_lag_s = new_lag_s
        self.lag_text_box.ax.set_facecolor("white")
        self._update_chosen_sample(self.current_sample_index)

    def _choose_time_from_click(self, event: MouseEvent) -> None:
        if event.inaxes is self.overview_axis and event.xdata is not None:
            self._update_zoom_window(event.xdata)

    def _start_measurement(self, event: MouseEvent) -> None:
        if (
            event.inaxes is self.zoom_axis
            and event.button == 1
            and event.xdata is not None
            and event.ydata is not None
        ):
            self._measurement_start = (float(event.xdata), float(event.ydata))
            self._measurement_dragged = False

    def _update_measurement(self, event: MouseEvent) -> None:
        if self._measurement_start is None or event.button != 1:
            return
        if (
            event.inaxes is not self.zoom_axis
            or event.xdata is None
            or event.ydata is None
        ):
            return
        start_time, start_capacitance = self._measurement_start
        end_time, end_capacitance = float(event.xdata), float(event.ydata)
        start_pixel = self.zoom_axis.transData.transform(self._measurement_start)
        if np.hypot(event.x - start_pixel[0], event.y - start_pixel[1]) > 3:
            self._measurement_dragged = True
        self._set_measurement(start_time, start_capacitance, end_time, end_capacitance)

    def _finish_measurement(self, event: MouseEvent) -> None:
        if self._measurement_start is None:
            return
        self._update_measurement(event)
        if (
            not self._measurement_dragged
            and event.inaxes is self.zoom_axis
            and event.xdata is not None
        ):
            insertion_index = int(np.searchsorted(self.time_values, event.xdata))
            candidate_indices = [
                index
                for index in (insertion_index - 1, insertion_index)
                if 0 <= index < len(self.time_values)
            ]
            nearest_sample_index = min(
                candidate_indices,
                key=lambda index: abs(self.time_values[index] - event.xdata),
            )
            self._update_chosen_sample(nearest_sample_index)
        self._measurement_start = None

    def _set_measurement(
        self,
        start_time: float,
        start_capacitance: float,
        end_time: float,
        end_capacitance: float,
    ) -> None:
        self.measurement_line.set_data(
            [start_time, end_time], [start_capacitance, end_capacitance]
        )
        self.measurement_text.set_text(
            f"Δt: {end_time - start_time:+.4f} s    "
            f"Δcapacitance: {end_capacitance - start_capacitance:+.4f}"
        )
        self._refresh_dynamic_axes([self.zoom_axis])

    def _choose_time_from_key(self, event: KeyEvent) -> None:
        if event.inaxes is self.lag_axis:
            return
        if event.key == "left":
            self._update_chosen_sample(self.current_sample_index - 1)
        elif event.key == "right":
            self._update_chosen_sample(self.current_sample_index + 1)

    def show(self) -> None:
        """Show the viewer and release video handles when it closes."""
        try:
            plt.show()
        finally:
            self.close()

    def close(self) -> None:
        """Release every open video handle."""
        for video in self.videos.values():
            video.close()
