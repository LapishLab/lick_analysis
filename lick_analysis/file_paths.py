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
    lickometer_csv: Path | None
    pis: dict[str, PiPaths]
    med_pc_file: Path | None = None

def find_lickometer_csv(session_directory: Path) -> Path | None:
    lickometer_directory = session_directory / "lickometer"
    if not lickometer_directory.is_dir():
        print(f"Lickometer directory not found in {session_directory.name}")

    matches = list(lickometer_directory.glob("*.csv"))
    if len(matches) == 1:
        return matches[0]
    else:
        print(f'Found {len(matches)} lickometer files for {session_directory}. Setting to None')
        return None

def find_pi_root_dir(session_directory: Path) -> Path:
    pi_root = [p for p in session_directory.iterdir()
                if p.is_dir() and p.name.lower().startswith("pi-data")]
    if len(pi_root) == 1:
        return pi_root[0]
    elif len(pi_root) > 1:
        FileNotFoundError(f"Why are there more than 1 directory starting with pi-data for {session_directory.name}!?!")
        return pi_root[0]
    else:
        return session_directory          
    
def load_session_paths(session_directory: Path) -> SessionPaths:
    """Find session files and paths for every Raspberry Pi and lickometer."""
    if not session_directory.is_dir():
        raise NotADirectoryError(f"Session directory not found: {session_directory}")

    pi_root = find_pi_root_dir(session_directory)

    pis: dict[str, PiPaths] = {}
    for p in pi_root.iterdir():
        if p.name == 'lickometer' or not p.is_dir():
            continue

        # find the GPIO CSV file
        csv_dir = p / "gpio"
        matches = list(csv_dir.glob("*.csv"))
        gpio_csv = matches[0] if len(matches) == 1 else None

        # find the camera video file
        video_dir = p / "cam"
        matches = list(video_dir.glob("*.mp4"))
        video = matches[0] if len(matches) == 1 else None
        video_pts = video.with_suffix(".pts") if video is not None else None
        if video_pts is not None and not video_pts.is_file():
            video_pts = None

        # find the audio file
        audio_dir = p / "mic"
        matches = list(audio_dir.glob("*.wav"))
        audio = matches[0] if len(matches) == 1 else None
        audio_csv = audio.with_suffix(".csv") if audio is not None else None
        if audio_csv is not None and not audio_csv.is_file():
            audio_csv = None

    
        pis[p.name] = PiPaths(
            video=video, video_pts=video_pts, gpio_csv=gpio_csv, audio=audio, audio_csv=audio_csv
        )

    if not pis:
        raise FileNotFoundError(f"No Pi directories found in {pi_root}")

    return SessionPaths(
        session_name=session_directory.name,
        session_directory=session_directory,
        lickometer_csv=find_lickometer_csv(session_directory),
        pis=pis,
    )
