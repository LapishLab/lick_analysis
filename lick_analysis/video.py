from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .config import ViewerSettings


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
    cache_size: int
    sequential_decode_limit: int
    display_max_width: int
    frame_cache: OrderedDict[int, NDArray[np.uint8]] = field(
        default_factory=OrderedDict,
        init=False,
    )
    last_decoded_frame_index: int | None = field(default=None, init=False)

    @classmethod
    def open(
        cls,
        pi_name: str,
        video_path: Path,
        pts_path: Path,
        settings: ViewerSettings,
    ) -> "PiVideo":
        start_time = pd.Timestamp(
            pd.to_datetime(
                video_path.stem,
                format="%Y%m%d_%H%M%S_%f",
                errors="raise",
            )
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

        # Frame counts and PTS files can include trailing entries whose encoded
        # frames were never committed. Probe backward once at startup so later
        # out-of-range requests can clamp directly to the last valid frame.
        last_decodable_frame = None
        first_candidate = usable_frame_count - 1
        last_candidate = max(-1, first_candidate - 300)
        for candidate in range(first_candidate, last_candidate, -1):
            capture.set(cv2.CAP_PROP_POS_FRAMES, candidate)
            success, _ = capture.read()
            if success:
                last_decodable_frame = candidate
                break

        if last_decodable_frame is None:
            capture.release()
            raise RuntimeError(f"Could not decode frames from {video_path}")

        usable_frame_count = last_decodable_frame + 1
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
            cache_size=settings.frame_cache_size,
            sequential_decode_limit=settings.sequential_decode_limit,
            display_max_width=settings.display_max_width,
        )

    def _prepare_frame(self, frame_bgr) -> NDArray[np.uint8]:
        """Convert a decoded frame to a display-sized RGB array."""
        height, width = frame_bgr.shape[:2]
        if width > self.display_max_width:
            scale = self.display_max_width / width
            frame_bgr = cv2.resize(
                frame_bgr,
                (self.display_max_width, round(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        return np.asarray(
            cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
            dtype=np.uint8,
        )

    def _cache_frame(
        self,
        frame_index: int,
        frame_bgr,
    ) -> NDArray[np.uint8]:
        """Prepare and retain a recently decoded frame."""
        frame_rgb = self._prepare_frame(frame_bgr)
        self.frame_cache[frame_index] = frame_rgb
        self.frame_cache.move_to_end(frame_index)
        while len(self.frame_cache) > self.cache_size:
            self.frame_cache.popitem(last=False)
        self.last_decoded_frame_index = frame_index
        return frame_rgb

    def _decode_frame(
        self,
        requested_frame_index: int,
    ) -> tuple[NDArray[np.uint8], int]:
        """Decode via cache, sequential reads, or a random seek."""
        cached_frame = self.frame_cache.get(requested_frame_index)
        if cached_frame is not None:
            self.frame_cache.move_to_end(requested_frame_index)
            return cached_frame, requested_frame_index

        last_index = self.last_decoded_frame_index
        if (
            last_index is not None
            and last_index < requested_frame_index
            and requested_frame_index - last_index <= self.sequential_decode_limit
        ):
            sequential_success = True
            for frame_index in range(last_index + 1, requested_frame_index + 1):
                success, frame_bgr = self.capture.read()
                if not success:
                    sequential_success = False
                    break
                self._cache_frame(frame_index, frame_bgr)

            if sequential_success:
                return self.frame_cache[requested_frame_index], requested_frame_index

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
                success, frame_bgr = self.capture.read()
                if success:
                    return self._cache_frame(candidate, frame_bgr), candidate

        raise RuntimeError(
            f"Could not decode a frame near {requested_frame_index} from "
            f"{self.video_path}"
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
        frame_rgb, frame_index = self._decode_frame(requested_frame_index)
        frame_pts_ms = float(self.frame_pts_ms[frame_index])
        frame_time = pd.Timestamp(
            self.start_time + pd.to_timedelta(frame_pts_ms, unit="ms")
        )
        difference_ms = float(
            (frame_time - target_time).total_seconds() * 1_000
        )
        return frame_rgb, frame_index, frame_time, difference_ms

    def close(self) -> None:
        self.capture.release()


def open_pi_videos(
    camera_files: dict[str, tuple[Path, Path]],
    settings: ViewerSettings,
) -> dict[str, PiVideo]:
    """Open every Pi video, closing prior videos if a later one fails."""
    videos: dict[str, PiVideo] = {}
    try:
        for pi_name, (video_path, pts_path) in camera_files.items():
            videos[pi_name] = PiVideo.open(
                pi_name,
                video_path,
                pts_path,
                settings,
            )
    except Exception:
        for video in videos.values():
            video.close()
        raise
    return videos
