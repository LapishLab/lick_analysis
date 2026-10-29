"""Collect session metadata from folders named like
``2026-10-26_08-58-30_NAc_dlight_rat1``.

Run with ``python data_sorting.py PATH_TO_SESSION_ROOT``. The report is written
to ``session_metadata.csv`` inside the selected root directory.
"""

import argparse
import csv
import re
from datetime import date, datetime
from pathlib import Path

problems = {
    1: 'Missing fiber01lick',
    2: 'Missing fiber01lick sync signal',
    3: 'Missing lickometer data',
    4: 'lick camera crashed'
}


DEFAULT_ROOT_DIRECTORY = Path(r"C:\Users\daswyga\Desktop\fiber_lick")
DEFAULT_START = '2026-10-26'
OUTPUT_FILENAME = "session_metadata.csv"
LICK_CAMERA_CRASH_THRESHOLD_MS = 5 * 60 * 1000
SESSION_NAME_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_"
    r"(?P<time>\d{2}-\d{2}-\d{2})_"
    r"(?P<experiment>.+)_rat(?P<rat_number>\d+)$",
    re.IGNORECASE,
)


def parse_session_folder(folder_name: str) -> dict[str, str] | None:
    """Return metadata for a session folder name, or None if it doesn't match."""
    match = SESSION_NAME_PATTERN.fullmatch(folder_name)
    if match is None:
        return None

    parts = match.groupdict()
    try:
        session_datetime = datetime.strptime(
            f"{parts['date']}_{parts['time']}", "%Y-%m-%d_%H-%M-%S"
        )
    except ValueError:
        return None

    return {
        "session_datetime": session_datetime.isoformat(sep=" "),
        "experiment_name": parts["experiment"],
        "rat_number": parts["rat_number"],
    }


def _last_pts_value(pts_path: Path) -> float | None:
    """Read the final numeric timestamp from a camera .pts file."""
    last_value = None
    try:
        with pts_path.open("r", encoding="utf-8-sig", errors="ignore") as pts_file:
            for line in pts_file:
                try:
                    last_value = float(line.strip())
                except ValueError:
                    continue
    except OSError:
        return None
    return last_value


def _camera_final_pts(pi_data_folders: list[Path], device_name: str) -> float | None:
    """Return the largest final timestamp among a device's camera .pts files."""
    final_values = [
        value
        for pi_data_folder in pi_data_folders
        for pts_path in (pi_data_folder / device_name / "cam").rglob("*.pts")
        if (value := _last_pts_value(pts_path)) is not None
    ]
    return max(final_values) if final_values else None


def _csv_has_data_rows(csv_path: Path) -> bool:
    """Return whether a CSV contains at least one nonblank row after its header."""
    try:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            next(reader, None)  # Header
            return any(any(value.strip() for value in row) for row in reader)
    except (OSError, UnicodeError, csv.Error):
        return False


def find_session_problems(session_folder: Path) -> list[int]:
    """Return problem keys for missing fiber01lick sync or lickometer data."""
    problem_keys: list[int] = []
    pi_data_folders = [
        path
        for path in session_folder.iterdir()
        if path.is_dir() and path.name.lower().startswith("pi-data_")
    ]
    fiber01lick_folders = [
        device_folder
        for pi_data_folder in pi_data_folders
        for device_folder in pi_data_folder.iterdir()
        if device_folder.is_dir() and device_folder.name.lower() == "fiber01lick"
    ]

    if not fiber01lick_folders:
        problem_keys.append(1)
    else:
        sync_csvs = [
            csv_path
            for device_folder in fiber01lick_folders
            for csv_path in (device_folder / "gpio").glob("*.csv")
            if csv_path.is_file() and _csv_has_data_rows(csv_path)
        ]
        if not sync_csvs:
            problem_keys.append(2)

    lickometer_csvs = [
        csv_path
        for lickometer_folder in session_folder.iterdir()
        if lickometer_folder.is_dir()
        and lickometer_folder.name.lower().startswith("lickometer")
        for csv_path in lickometer_folder.glob("*.csv")
        if csv_path.is_file() and csv_path.stat().st_size > 0
    ]
    if not lickometer_csvs:
        problem_keys.append(3)

    fiber01_final_pts = _camera_final_pts(pi_data_folders, "fiber01")
    fiber01lick_final_pts = _camera_final_pts(pi_data_folders, "fiber01lick")
    if (
        fiber01_final_pts is not None
        and fiber01lick_final_pts is not None
        and fiber01_final_pts - fiber01lick_final_pts
        > LICK_CAMERA_CRASH_THRESHOLD_MS
    ):
        problem_keys.append(4)

    return problem_keys


def collect_session_metadata(
    root_directory: Path,
    start_date: date | None = None,
    stop_date: date | None = None,
) -> tuple[Path, int, list[str]]:
    """Write metadata for session subfolders within an optional date range."""
    if not root_directory.is_dir():
        raise NotADirectoryError(f"Session root directory does not exist: {root_directory}")
    if start_date is not None and stop_date is not None and start_date > stop_date:
        raise ValueError("start_date must be on or before stop_date")

    output_path = root_directory / OUTPUT_FILENAME
    rows: list[dict[str, str]] = []
    skipped: list[str] = []

    for folder in sorted(root_directory.iterdir(), key=lambda path: path.name.lower()):
        if not folder.is_dir() or folder == output_path:
            continue

        metadata = parse_session_folder(folder.name)
        if metadata is None:
            skipped.append(folder.name)
            continue

        session_date = datetime.fromisoformat(metadata["session_datetime"]).date()
        if start_date is not None and session_date < start_date:
            continue
        if stop_date is not None and session_date > stop_date:
            continue

        problem_keys = find_session_problems(folder)
        rows.append(
            {
                "session_folder": folder.name,
                **metadata,
                "problems": ";".join(str(key) for key in problem_keys),
            }
        )

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "session_folder",
                "session_datetime",
                "experiment_name",
                "rat_number",
                "problems",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return output_path, len(rows), skipped


def main() -> None:
    def parse_date(value: str) -> date | None:
        if value.lower() == "none":
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"invalid date {value!r}; use YYYY-MM-DD or None"
            ) from exc

    parser = argparse.ArgumentParser(
        description="Extract session date/time, experiment, and rat number from folder names."
    )
    parser.add_argument(
        "root_directory",
        nargs="?",
        type=Path,
        default=DEFAULT_ROOT_DIRECTORY,
        help=f"directory containing session folders (default: {DEFAULT_ROOT_DIRECTORY})",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=DEFAULT_START,
        metavar="YYYY-MM-DD|None",
        help="include sessions on or after this date (default: None, no lower bound)",
    )
    parser.add_argument(
        "--stop-date",
        type=parse_date,
        default=None,
        metavar="YYYY-MM-DD|None",
        help="include sessions on or before this date (default: None, no upper bound)",
    )
    args = parser.parse_args()

    output_path, count, skipped = collect_session_metadata(
        args.root_directory, args.start_date, args.stop_date
    )
    print(f"Wrote {count} session(s) to {output_path}")
    for folder_name in skipped:
        print(f"Skipped folder with an unrecognized session name: {folder_name}")


if __name__ == "__main__":
    main()
