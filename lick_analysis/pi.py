"""Locate the files belonging to one Raspberry Pi."""

import re
from datetime import datetime
from pathlib import Path


PI_DATETIME_PATTERN = re.compile(r"\d{8}_\d{6}(?:_\d{1,6})?")


class Pi:
    """A Raspberry Pi's recording files and timestamps."""

    directory: Path
    video: Path | None
    video_pts: Path | None
    gpio_csv: Path | None
    audio: Path | None
    audio_csv: Path | None
    video_datetime: datetime | None
    gpio_datetime: datetime | None
    audio_datetime: datetime | None

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.gpio_csv = self._find_file("gpio", "*.csv")
        self.video = self._find_file("cam", "*.mp4")
        self.audio = self._find_file("mic", "*.wav")

        self.video_pts = self.video.with_suffix(".pts") if self.video is not None else None
        if self.video_pts is not None and not self.video_pts.is_file():
            self.video_pts = None
        self.audio_csv = self.audio.with_suffix(".csv") if self.audio is not None else None
        if self.audio_csv is not None and not self.audio_csv.is_file():
            self.audio_csv = None

        self.video_datetime = self.parse_datetime(self.video)
        self.gpio_datetime = self.parse_datetime(self.gpio_csv)
        self.audio_datetime = self.parse_datetime(self.audio)

    def _find_file(self, subdirectory: str, pattern: str) -> Path | None:
        matches = list((self.directory / subdirectory).glob(pattern))
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def parse_datetime(path: Path | None) -> datetime | None:
        """Parse a Pi recording timestamp from its filename."""
        if path is None or PI_DATETIME_PATTERN.fullmatch(path.stem) is None:
            return None
        timestamp_format = (
            "%Y%m%d_%H%M%S_%f" if path.stem.count("_") == 2 else "%Y%m%d_%H%M%S"
        )
        try:
            return datetime.strptime(path.stem, timestamp_format)
        except ValueError:
            return None
