"""Copy root-level lickometer recordings into their matching session folders.

Lickometer files are paired to the start timestamp in each session's
``pi-data_*/fiber01/cam/*.pts`` filename. A lickometer file can start from
five minutes before through thirty minutes after the video start.

Run with ``python copy_lickometer_to_sessions.py PATH_TO_SESSION_ROOT``.
"""

import argparse
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


LICKOMETER_FOLDER_NAME = "lickometer"
EARLY_START_TOLERANCE = timedelta(minutes=5)
LATE_START_TOLERANCE = timedelta(minutes=30)

SESSION_NAME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_.+_rat\d+$",
    re.IGNORECASE,
)
VIDEO_TIMESTAMP_PATTERN = re.compile(
    r"^(?P<date>\d{8})_(?P<time>\d{6})(?:_(?P<fraction>\d{1,6}))?$"
)
LICKOMETER_TIMESTAMP_PATTERN = re.compile(
    r"^fiber01lickometer_(?P<date>\d{4}_\d{2}_\d{2})_"
    r"(?P<time>\d{6})$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LickometerFile:
    csv_path: Path
    start_time: datetime


@dataclass(frozen=True)
class SessionVideo:
    folder: Path
    start_time: datetime


def parse_video_start(pts_path: Path) -> datetime | None:
    """Parse a camera start time from names like YYYYMMDD_HHMMSS_ffffff.pts."""
    match = VIDEO_TIMESTAMP_PATTERN.fullmatch(pts_path.stem)
    if match is None:
        return None

    try:
        start_time = datetime.strptime(
            f"{match['date']}_{match['time']}", "%Y%m%d_%H%M%S"
        )
    except ValueError:
        return None

    fraction = match["fraction"]
    if fraction:
        start_time += timedelta(microseconds=int(fraction.ljust(6, "0")))
    return start_time


def parse_lickometer_start(csv_path: Path) -> datetime | None:
    """Parse the start time from a fiber01Lickometer CSV filename."""
    match = LICKOMETER_TIMESTAMP_PATTERN.fullmatch(csv_path.stem)
    if match is None:
        return None

    try:
        return datetime.strptime(
            f"{match['date']}_{match['time']}", "%Y_%m_%d_%H%M%S"
        )
    except ValueError:
        return None


def find_session_videos(session_root: Path) -> tuple[list[SessionVideo], list[Path]]:
    """Find each session's earliest fiber01 camera timestamp."""
    sessions: list[SessionVideo] = []
    skipped: list[Path] = []

    for session_folder in sorted(session_root.iterdir(), key=lambda path: path.name.lower()):
        if not session_folder.is_dir() or not SESSION_NAME_PATTERN.fullmatch(
            session_folder.name
        ):
            continue

        video_starts = [
            start_time
            for pi_data_folder in session_folder.iterdir()
            if pi_data_folder.is_dir() and pi_data_folder.name.lower().startswith("pi-data_")
            for pts_path in (pi_data_folder / "fiber01" / "cam").glob("*.pts")
            if (start_time := parse_video_start(pts_path)) is not None
        ]
        if not video_starts:
            skipped.append(session_folder)
            continue

        sessions.append(SessionVideo(session_folder, min(video_starts)))

    return sessions, skipped


def find_lickometer_files(session_root: Path) -> list[LickometerFile]:
    source_folder = session_root / LICKOMETER_FOLDER_NAME
    if not source_folder.is_dir():
        raise NotADirectoryError(f"Root lickometer folder not found: {source_folder}")

    files = []
    for csv_path in source_folder.rglob("*.csv"):
        start_time = parse_lickometer_start(csv_path)
        if start_time is not None:
            files.append(LickometerFile(csv_path, start_time))
    return files


def match_files(
    sessions: list[SessionVideo], lickometer_files: list[LickometerFile]
) -> tuple[dict[Path, list[LickometerFile]], list[LickometerFile]]:
    """Match every lickometer CSV in the allowed window to each session."""
    matches: dict[Path, list[LickometerFile]] = {}
    matched_files: set[Path] = set()
    for session in sessions:
        earliest = session.start_time - EARLY_START_TOLERANCE
        latest = session.start_time + LATE_START_TOLERANCE
        session_matches = [
            lickometer_file
            for lickometer_file in lickometer_files
            if earliest <= lickometer_file.start_time <= latest
        ]
        if session_matches:
            matches[session.folder] = sorted(
                session_matches, key=lambda item: item.start_time
            )
            matched_files.update(item.csv_path for item in session_matches)

    unmatched_files = [
        lickometer_file
        for lickometer_file in lickometer_files
        if lickometer_file.csv_path not in matched_files
    ]
    return matches, unmatched_files


def copy_recording(lickometer_file: LickometerFile, session_folder: Path) -> list[str]:
    """Copy a matched CSV and its optional same-stem MLK file."""
    destination_folder = session_folder / LICKOMETER_FOLDER_NAME
    source_files = [lickometer_file.csv_path]
    mlk_path = lickometer_file.csv_path.with_suffix(".mlk")
    if mlk_path.is_file():
        source_files.append(mlk_path)

    destination_files = [destination_folder / source.name for source in source_files]
    for source, destination in zip(source_files, destination_files):
        if destination.exists() and not _same_file_contents(source, destination):
            raise FileExistsError(
                f"Refusing to overwrite different existing file: {destination}"
            )

    destination_folder.mkdir(parents=True, exist_ok=True)
    copied = []
    for source, destination in zip(source_files, destination_files):
        if destination.exists():
            copied.append(f"already present: {destination.name}")
            continue
        shutil.copy2(source, destination)
        copied.append(f"copied: {destination.name}")
    return copied


def _same_file_contents(first: Path, second: Path) -> bool:
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as first_file, second.open("rb") as second_file:
        while True:
            first_chunk = first_file.read(1024 * 1024)
            second_chunk = second_file.read(1024 * 1024)
            if first_chunk != second_chunk:
                return False
            if not first_chunk:
                return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match root lickometer files to sessions by recording timestamps."
    )
    parser.add_argument(
        "session_root",
        nargs="?",
        type=Path,
        default=Path(r"C:\Users\daswyga\Desktop\fiber_lick"),
        help="root containing session folders and the root lickometer folder",
    )
    args = parser.parse_args()

    if not args.session_root.is_dir():
        raise NotADirectoryError(f"Session root does not exist: {args.session_root}")

    sessions, sessions_without_video = find_session_videos(args.session_root)
    lickometer_files = find_lickometer_files(args.session_root)
    matches, unmatched_files = match_files(sessions, lickometer_files)

    for session in sessions:
        session_matches = matches.get(session.folder, [])
        if not session_matches:
            print(f"No lickometer file matched: {session.folder.name}")
            continue

        for lickometer_file in session_matches:
            offset = lickometer_file.start_time - session.start_time
            try:
                actions = copy_recording(lickometer_file, session.folder)
            except FileExistsError as error:
                print(f"Conflict for {session.folder.name}: {error}")
                continue
            print(
                f"{session.folder.name}: {lickometer_file.csv_path.name} "
                f"(start offset {offset.total_seconds():.1f} s); {', '.join(actions)}"
            )

    for session_folder in sessions_without_video:
        print(f"No fiber01 camera timestamp found: {session_folder.name}")
    for lickometer_file in unmatched_files:
        print(f"Unmatched lickometer file: {lickometer_file.csv_path}")


if __name__ == "__main__":
    main()
