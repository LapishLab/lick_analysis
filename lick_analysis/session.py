"""Locate the Raspberry Pi and lickometer files belonging to a session."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .lickometer import Lickometer
from .pi import Pi


SESSION_NAME_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_"
    r"(?P<experiment>.+)_(?:rat|group)(?P<id>[^_]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Session:
    """A session's recording files and metadata, keyed by Pi directory name."""

    directory: Path
    name: str = field(init=False)
    experiment: str = field(init=False)
    lickometer: Lickometer = field(init=False)
    pis: dict[str, Pi] = field(init=False)
    med_pc_file: Path | None = field(default=None, init=False)
    id: str = field(init=False)
    datetime: datetime = field(init=False)

    def __post_init__(self) -> None:
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Session directory not found: {self.directory}")

        session_datetime, experiment, session_id = self.parse_name(self.directory.name)
        pi_root = self._find_pi_root()
        pis = {
            p.name: Pi(p)
            for p in pi_root.iterdir()
            if p.is_dir() and p.name != "lickometer"
        }
        if not pis:
            raise FileNotFoundError(f"No Pi directories found in {pi_root}")

        object.__setattr__(self, "name", self.directory.name)
        object.__setattr__(self, "experiment", experiment)
        object.__setattr__(self, "lickometer", Lickometer(self.directory / "lickometer"))
        object.__setattr__(self, "pis", pis)
        object.__setattr__(self, "id", session_id)
        object.__setattr__(self, "datetime", session_datetime)

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
