from pathlib import Path

import pandas as pd

from lick_analysis import (
    LickometerViewer,
    SyncParameters,
    ViewerSettings,
    build_pi_sync_lookup_tables,
    load_lickometer_data,
    load_session_paths,
    open_pi_videos,
)
root = r"/datastar/behavior_rooms/fiber/A/"
# f = r"2026-10-26_08-58-30_NAc_dlight_rat1" # Good but video cut short and no LED
f = r"2026-10-28_15-47-49_NAc_dlight_rat2"
# f = r"2026-10-28_14-06-18_NAc_dlight_rat6"
# f = "2026-10-30_15-35-22_NAc_dlight_rat7"

f = "2026-11-04_16-16-29_test_rat"


EXAMPLE_DATA_DIR = Path(root + f)
LICKOMETER_CSV = EXAMPLE_DATA_DIR / "lickometer/fiber01Lickometer_2026_10_28_155207.csv"

LICK_PREDICTION = Path("/datastar/davidSwygart/labels/predictions/20261028_155145_422145_repaired.csv")
# Set LICK_PREDICTION to None to hide the prediction trace.

# Configure each Pi by the name of its directory under pi-data*.
PI_PARAMETERS = {
    "fiber01": SyncParameters(pin=25),
    "fiber01lick": SyncParameters(pin=16),
}


def load_lick_prediction(csv_path: Path, video_path: Path) -> pd.DataFrame:
    """Read per-frame predictions on the fiber01lick video's Pi clock."""
    data = pd.read_csv(csv_path)
    required = {"timestamp_ms", "contact_probability"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"{csv_path} is missing required columns: {sorted(missing)}")
    if data.empty:
        raise ValueError(f"{csv_path} contains no data rows")
    for column in required:
        data[column] = pd.to_numeric(data[column], errors="raise")
    if data[list(required)].isna().any().any():
        raise ValueError(f"{csv_path} contains missing prediction values")
    video_start = pd.to_datetime(video_path.stem, format="%Y%m%d_%H%M%S_%f")
    data["pi_time"] = video_start + pd.to_timedelta(data["timestamp_ms"], unit="ms")
    return data


def main() -> None:
    viewer_settings = ViewerSettings()
    paths = load_session_paths(EXAMPLE_DATA_DIR, lickometer_csv=LICKOMETER_CSV)
    if not PI_PARAMETERS:
        raise ValueError("PI_PARAMETERS must name at least one Pi")
    missing_pis = set(PI_PARAMETERS).difference(paths.pis)
    if missing_pis:
        raise ValueError(f"Configured Pis not found in session: {sorted(missing_pis)}")

    capacitance = load_lickometer_data(paths.lickometer_csv)
    sync_tables = {}
    camera_files = {}
    for pi_name, parameters in PI_PARAMETERS.items():
        pi_paths = paths.pis[pi_name]
        if pi_paths.gpio_csv is None:
            raise FileNotFoundError(f"GPIO CSV not found for {pi_name}")
        if pi_paths.video is None or pi_paths.video_pts is None:
            raise FileNotFoundError(f"Video or frame timestamps not found for {pi_name}")
        sync_tables[pi_name] = build_pi_sync_lookup_tables(pi_name, pi_paths.gpio_csv, capacitance, parameters)
        camera_files[pi_name] = (pi_paths.video, pi_paths.video_pts)

    prediction = None
    if LICK_PREDICTION is not None:
        if "fiber01lick" not in camera_files:
            raise ValueError("fiber01lick must be configured to plot lick predictions")
        prediction = load_lick_prediction(
            LICK_PREDICTION, camera_files["fiber01lick"][0]
        )

    videos = open_pi_videos(camera_files, viewer_settings)
    try:
        viewer = LickometerViewer(
            capacitance,
            sync_tables,
            videos,
            viewer_settings,
            title=paths.lickometer_csv.stem,
            lick_prediction=prediction,
        )
    except Exception:
        for video in videos.values():
            video.close()
        raise
    viewer.show()


if __name__ == "__main__":
    main()
