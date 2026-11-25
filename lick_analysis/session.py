"""Locate the Raspberry Pi and lickometer files belonging to a session."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .lickometer import Lickometer
from .pi import Pi


SESSION_NAME_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_"
    r"(?P<experiment>.+)_(?:rat|group)(?P<id>[^_]+)",
    re.IGNORECASE,
)


class Session:
    """A session's recording files and metadata, keyed by Pi directory name."""

    directory: Path
    name: str
    experiment: str
    lickometer: Lickometer
    pis: dict[str, Pi]
    med_pc_file: Path | None
    id: str
    datetime: datetime

    def __init__(self, directory: Path) -> None:
        if not directory.is_dir():
            raise NotADirectoryError(f"Session directory not found: {directory}")

        self.directory = directory
        self.name = directory.name
        self.datetime, self.experiment, self.id = self.parse_name(self.name)
        pi_root = self._find_pi_root()
        self.pis = {
            p.name: Pi(p)
            for p in pi_root.iterdir()
            if p.is_dir() and p.name != "lickometer"
        }
        if not self.pis:
            raise FileNotFoundError(f"No Pi directories found in {pi_root}")

        self.lickometer = Lickometer(directory / "lickometer")
        self.med_pc_file = None

    def _find_pi_root(self) -> Path:
        pi_roots = [
            p for p in self.directory.iterdir()
            if p.is_dir() and p.name.lower().startswith("pi-data")
        ]
        return pi_roots[0] if pi_roots else self.directory

    @staticmethod
    def parse_name(name: str) -> tuple[datetime, str, str]:
        """Parse a session folder's metadata, raising ValueError for invalid names."""
        match = SESSION_NAME_PATTERN.fullmatch(name)
        if match is None:
            raise ValueError(f"Invalid session name: {name}")
        try:
            session_datetime = datetime.strptime(match["timestamp"], "%Y-%m-%d_%H-%M-%S")
        except ValueError as exc:
            raise ValueError(f"Invalid session datetime in name: {name}") from exc
        return session_datetime, match["experiment"], match["id"].lower()
