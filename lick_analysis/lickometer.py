"""Locate a session's lickometer recording and parse its filename."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


LICKOMETER_FILENAME_PATTERN = re.compile(
    r"(?P<board_id>.+)_(?P<timestamp>\d{4}_\d{2}_\d{2}_\d{6})"
)


class Lickometer:
    """A lickometer recording file and metadata parsed from its filename."""

    directory: Path
    csv: Path
    datetime: datetime
    board_id: str

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.csv = self._find_csv()
        self.board_id, self.datetime = self.parse_filename(self.csv)

    def _find_csv(self) -> Path:
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Lickometer directory not found: {self.directory}")
        matches = list(self.directory.glob("*.csv"))
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise FileNotFoundError(f"No lickometer CSV found in {self.directory}")
        raise ValueError(f"Found {len(matches)} lickometer CSVs in {self.directory}")

    @staticmethod
    def parse_filename(path: Path) -> tuple[str, datetime]:
        """Parse the board ID and recording time from a CSV filename."""
        if path is None:
            raise ValueError("Lickometer CSV path is missing")
        match = LICKOMETER_FILENAME_PATTERN.fullmatch(path.stem)
        if match is None:
            raise ValueError(f"Invalid lickometer CSV filename: {path.name}")
        recording_datetime = datetime.strptime(match["timestamp"], "%Y_%m_%d_%H%M%S")
        return match["board_id"], recording_datetime
