"""Locate the files belonging to one Raspberry Pi."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


PI_DATETIME_PATTERN = re.compile(r"\d{8}_\d{6}(?:_\d{1,6})?")


@dataclass(frozen=True)
class Pi:
    """A Raspberry Pi's recording files and timestamps."""

    directory: Path
    video: Path | None = field(init=False)
    video_pts: Path | None = field(init=False)
    gpio_csv: Path | None = field(init=False)
    audio: Path | None = field(init=False)
    audio_csv: Path | None = field(init=False)
    video_datetime: datetime | None = field(init=False)
    gpio_datetime: datetime | None = field(init=False)
    audio_datetime: datetime | None = field(init=False)

    def __post_init__(self) -> None:
        gpio_csv = self._find_file("gpio", "*.csv")
        video = self._find_file("cam", "*.mp4")
        audio = self._find_file("mic", "*.wav")

        video_pts = video.with_suffix(".pts") if video is not None else None
        if video_pts is not None and not video_pts.is_file():
            video_pts = None
        audio_csv = audio.with_suffix(".csv") if audio is not None else None
        if audio_csv is not None and not audio_csv.is_file():
            audio_csv = None

        object.__setattr__(self, "gpio_csv", gpio_csv)
        object.__setattr__(self, "video", video)
        object.__setattr__(self, "video_pts", video_pts)
        object.__setattr__(self, "audio", audio)
        object.__setattr__(self, "audio_csv", audio_csv)
        object.__setattr__(self, "video_datetime", self.parse_datetime(video))
        object.__setattr__(self, "gpio_datetime", self.parse_datetime(gpio_csv))
        object.__setattr__(self, "audio_datetime", self.parse_datetime(audio))

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
