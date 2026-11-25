"""Create a CSV index of recording sessions and their input files."""

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .file_paths import load_session_paths


CSV_FILENAME = "sessions.csv"
DATA_DIRECTORY_FILENAME = "data_root.txt"


@dataclass
class Row:
    session_name: str
    id: str
    capacitance_trace_path: str
    lick_camera_video_path: str
    top_camera_video_path: str

def generate_row(
    session_directory: Path,
    lick_camera_pi: str,
    top_camera_pi: str,
) -> Row:
    paths = load_session_paths(session_directory)
    lick_pi = paths.pis.get(lick_camera_pi)
    top_pi = paths.pis.get(top_camera_pi)

    def relative_path(path: Path | None) -> str:
        return str(path.relative_to(session_directory.parent)) if path is not None else ""

    return Row(
        session_name=paths.session_name,
        id=paths.id if paths.id is not None else "",
        capacitance_trace_path=relative_path(paths.lickometer_csv),
        lick_camera_video_path=relative_path(lick_pi.video) if lick_pi else "",
        top_camera_video_path=relative_path(top_pi.video) if top_pi else "",
    )

def generate_session_csv(
    data_directory: Path | str,
    output_directory: Path | str | None = None,
    lick_camera_pi: str = "fiber01lick",
    top_camera_pi: str = "fiber01",
) -> Path:
    """Index immediate session folders in ``data_directory``.

    Camera arguments are Pi directory names, as used by ``load_session_paths``.
    Missing files produce empty CSV cells. File paths in the CSV are relative
    to ``data_directory``. By default, the CSV is written to ``data_directory``;
    pass ``output_directory`` to choose another destination. The destination
    is created if needed, and ``data_root.txt`` records the resolved data
    directory beside the CSV. The returned path points to the written CSV.
    """
    data_directory = Path(data_directory).resolve()
    if not data_directory.is_dir():
        raise NotADirectoryError(f"Data directory not found: {data_directory}")

    rows = []
    sessions = data_directory.iterdir()
    sessions  = sorted(sessions, key=lambda path: path.name.lower())
    for session in sessions:
        if not session.is_dir():
            continue
        try:
            r = generate_row(session, lick_camera_pi, top_camera_pi)
        except Exception as e:
            print(f"Error processing session {session.name}: {e}")
            continue
        rows.append(r)

    if output_directory is None:
        output_directory = data_directory
    output_directory = Path(output_directory).expanduser()
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / CSV_FILENAME
    columns = tuple(f.name for f in fields(Row))
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    (output_directory / DATA_DIRECTORY_FILENAME).write_text(
        f"{data_directory}\n", encoding="utf-8"
    )
    return output_path
