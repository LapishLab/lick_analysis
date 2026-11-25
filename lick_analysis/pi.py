"""Locate the files belonging to one Raspberry Pi."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


PI_DATETIME_PATTERN = re.compile(r"\d{8}_\d{6}(?:_\d{1,6})?")


class Pi:
    """A Raspberry Pi with separate GPIO, microphone, and camera recordings."""

    directory: Path
    gpio: GpioPi | None
    microphone: AudioPi | None
    camera: VideoPi | None

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._load_recordings()

    def _load_recordings(self) -> None:
        try:
            self.gpio = GpioPi(self.directory)
        except Exception:
            self.gpio = None
        try:
            self.microphone = AudioPi(self.directory)
        except Exception:
            self.microphone = None
        try:
            self.camera = VideoPi(self.directory)
        except Exception:
            self.camera = None

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


class GpioPi(Pi):
    """GPIO event recording from a Raspberry Pi."""

    csv: Path | None
    datetime: datetime | None

    def _load_recordings(self) -> None:
        self.csv = self._find_file("gpio", "*.csv")
        self.datetime = self.parse_datetime(self.csv)


class AudioPi(Pi):
    """Microphone recording and its companion CSV from a Raspberry Pi."""

    audio: Path | None
    csv: Path | None
    datetime: datetime | None

    def _load_recordings(self) -> None:
        self.audio = self._find_file("mic", "*.wav")
        self.csv = self.audio.with_suffix(".csv") if self.audio is not None else None
        if self.csv is not None and not self.csv.is_file():
            self.csv = None
        self.datetime = self.parse_datetime(self.audio)


class VideoPi(Pi):
    """Camera recording and its frame timestamps from a Raspberry Pi."""

    video: Path | None
    pts: Path | None
    datetime: datetime | None

    def _load_recordings(self) -> None:
        self.video = self._find_file("cam", "*.mp4")
        self.pts = self.video.with_suffix(".pts") if self.video is not None else None
        if self.pts is not None and not self.pts.is_file():
            self.pts = None
        self.datetime = self.parse_datetime(self.video)
