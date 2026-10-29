"""Locate the files belonging to a session and its Raspberry Pis."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PiPaths:
    """Paths belonging to one Raspberry Pi in a session."""

    video: Path | None
    video_pts: Path | None
    gpio_csv: Path | None
    audio: Path | None = None
    audio_csv: Path | None = None


@dataclass(frozen=True)
class SessionPaths:
    """Session paths, keyed by the Raspberry Pi directory name."""

    session_name: str
    session_directory: Path
    lickometer_csv: Path
    pis: dict[str, PiPaths]
    med_pc_file: Path | None = None


def _one_file(directory: Path, pattern: str, description: str) -> Path:
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one {description} in {directory}, found {len(matches)}"
        )
    return matches[0]


def _optional_one_file(directory: Path, pattern: str, description: str) -> Path | None:
    matches = list(directory.glob(pattern))
    if len(matches) > 1:
        raise RuntimeError(
            f"Expected at most one {description} in {directory}, found {len(matches)}"
        )
    return matches[0] if matches else None


def load_session_paths(session_directory: Path) -> SessionPaths:
    """Find session files and paths for every Raspberry Pi directory."""
    if not session_directory.is_dir():
        raise NotADirectoryError(f"Session directory not found: {session_directory}")

    lickometer_directories = [
        path
        for path in session_directory.iterdir()
        if path.is_dir() and path.name.lower().startswith("lickometer")
    ]
    if len(lickometer_directories) != 1:
        raise FileNotFoundError(
            f"Expected one lickometer directory in {session_directory}, "
            f"found {len(lickometer_directories)}"
        )
    lickometer_csv = _one_file(
        lickometer_directories[0], "*.csv", "lickometer CSV"
    )

    pi_data_directories = [
        path
        for path in session_directory.iterdir()
        if path.is_dir() and path.name.lower().startswith("pi-data")
    ]
    if len(pi_data_directories) != 1:
        raise FileNotFoundError(
            f"Expected one pi-data directory in {session_directory}, "
            f"found {len(pi_data_directories)}"
        )
    pi_data_directory = pi_data_directories[0]

    pis: dict[str, PiPaths] = {}
    for pi_directory in sorted(pi_data_directory.iterdir()):
        if not pi_directory.is_dir():
            continue
        gpio_csv = _optional_one_file(
            pi_directory / "gpio", "*.csv", "GPIO CSV"
        )
        video = _optional_one_file(pi_directory / "cam", "*.mp4", "camera video")
        video_pts = video.with_suffix(".pts") if video is not None else None
        if video_pts is not None and not video_pts.is_file():
            video_pts = None
        pis[pi_directory.name] = PiPaths(
            video=video, video_pts=video_pts, gpio_csv=gpio_csv
        )

    if not pis:
        raise FileNotFoundError(f"No Pi directories found in {pi_data_directory}")

    return SessionPaths(
        session_name=session_directory.name,
        session_directory=session_directory,
        lickometer_csv=lickometer_csv,
        pis=pis,
    )
