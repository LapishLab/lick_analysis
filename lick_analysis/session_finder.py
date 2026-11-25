"""Create a CSV index of recording sessions and their input files."""

import csv
import re
from pathlib import Path

from .file_paths import load_session_paths


CSV_FILENAME = "session_index.csv"
CSV_COLUMNS = (
    "session_name",
    "rat_id",
    "capacitance_trace_path",
    "lick_camera_video_path",
    "top_camera_video_path",
)
RAT_ID_PATTERN = re.compile(r"(?:^|_)(rat\d+)$", re.IGNORECASE)


def generate_session_csv(
    data_directory: Path | str,
    *,
    output_directory: Path | str | None = None,
    lick_camera_pi: str = "fiber01lick",
    top_camera_pi: str = "fiber01",
) -> Path:
    """Index immediate session folders in ``data_directory``.

    Camera arguments are Pi directory names, as used by ``load_session_paths``.
    A missing Pi or camera video produces an empty CSV cell. Paths in the CSV
    are absolute. By default, the CSV is written to ``data_directory``; pass
    ``output_directory`` to choose another destination. The destination is
    created if needed, and the returned path points to the written CSV.
    """
    data_directory = Path(data_directory).resolve()
    if not data_directory.is_dir():
        raise NotADirectoryError(f"Data directory not found: {data_directory}")

    rows = []
    for session_directory in sorted(data_directory.iterdir(), key=lambda path: path.name.lower()):
        if not session_directory.is_dir() or not any(
            child.is_dir() and child.name.lower().startswith("lickometer")
            for child in session_directory.iterdir()
        ):
            continue

        paths = load_session_paths(session_directory)
        rat_match = RAT_ID_PATTERN.search(paths.session_name)
        lick_pi = paths.pis.get(lick_camera_pi)
        top_pi = paths.pis.get(top_camera_pi)
        rows.append(
            {
                "session_name": paths.session_name,
                "rat_id": rat_match.group(1).lower() if rat_match else "",
                "capacitance_trace_path": str(paths.lickometer_csv),
                "lick_camera_video_path": str(lick_pi.video) if lick_pi and lick_pi.video else "",
                "top_camera_video_path": str(top_pi.video) if top_pi and top_pi.video else "",
            }
        )
    if output_directory is None:
        output_directory = data_directory
    output_directory = Path(output_directory).expanduser()
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / CSV_FILENAME
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
