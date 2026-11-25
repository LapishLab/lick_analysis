"""Locate the Raspberry Pi and lickometer files belonging to a session."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .lickometer import Lickometer
from .pi import Pi


SESSION_ID_PATTERN = re.compile(r"(?:^|_)(?:rat|group)([^_]*)(?=_|$)", re.IGNORECASE)
SESSION_DATETIME_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})(?:_|$)")


@dataclass(frozen=True)
class Session:
    """A session's recording files and metadata, keyed by Pi directory name."""

    directory: Path
    name: str = field(init=False)
    lickometer: Lickometer = field(init=False)
    pis: dict[str, Pi] = field(init=False)
    med_pc_file: Path | None = field(default=None, init=False)
    id: str | None = field(init=False)
    datetime: datetime | None = field(init=False)

    def __post_init__(self) -> None:
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Session directory not found: {self.directory}")

        pi_root = self._find_pi_root()
        pis = {
            p.name: Pi(p)
            for p in pi_root.iterdir()
            if p.is_dir() and p.name != "lickometer"
        }
        if not pis:
            raise FileNotFoundError(f"No Pi directories found in {pi_root}")

        id_match = SESSION_ID_PATTERN.search(self.directory.name)
        object.__setattr__(self, "name", self.directory.name)
        object.__setattr__(self, "lickometer", Lickometer(self.directory / "lickometer"))
        object.__setattr__(self, "pis", pis)
        object.__setattr__(self, "id", id_match.group(1).lower() if id_match else None)
        object.__setattr__(self, "datetime", self._parse_datetime())

    def _find_pi_root(self) -> Path:
        pi_roots = [
            p for p in self.directory.iterdir()
            if p.is_dir() and p.name.lower().startswith("pi-data")
        ]
        return pi_roots[0] if pi_roots else self.directory

    def _parse_datetime(self) -> datetime | None:
        match = SESSION_DATETIME_PATTERN.match(self.directory.name)
        if match is None:
            return None
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            return None
