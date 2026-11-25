"""Locate a session's lickometer recording and parse its filename."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


LICKOMETER_FILENAME_PATTERN = re.compile(
    r"(?P<board_id>.+)_(?P<timestamp>\d{4}_\d{2}_\d{2}_\d{6})"
)


@dataclass(frozen=True)
class Lickometer:
    """A lickometer recording file and metadata parsed from its filename."""

    directory: Path
    csv: Path | None = field(init=False)
    datetime: datetime | None = field(init=False)
    board_id: str | None = field(init=False)

    def __post_init__(self) -> None:
        csv = self._find_csv()
        board_id, recording_datetime = self.parse_filename(csv)
        object.__setattr__(self, "csv", csv)
        object.__setattr__(self, "datetime", recording_datetime)
        object.__setattr__(self, "board_id", board_id)

    def _find_csv(self) -> Path | None:
        if not self.directory.is_dir():
            print(f"Lickometer directory not found in {self.directory.parent.name}")
        matches = list(self.directory.glob("*.csv"))
        if len(matches) == 1:
            return matches[0]
        print(f"Found {len(matches)} lickometer files for {self.directory.parent}. Setting to None")
        return None

    @staticmethod
    def parse_filename(path: Path | None) -> tuple[str | None, datetime | None]:
        """Parse the board ID and recording time from a CSV filename."""
        if path is None:
            return None, None
        match = LICKOMETER_FILENAME_PATTERN.fullmatch(path.stem)
        if match is None:
            return None, None
        try:
            recording_datetime = datetime.strptime(match["timestamp"], "%Y_%m_%d_%H%M%S")
        except ValueError:
            return None, None
        return match["board_id"], recording_datetime
