from pathlib import Path

from lick_analysis import (
    LickometerViewer,
    SyncParameters,
    ViewerSettings,
    build_pi_sync_lookup_tables,
    load_lickometer_data,
    load_session_paths,
    open_pi_videos,
)


root = r"C:\Users\daswyga\Desktop\fiber_lick\\"
f = r"2026-10-26_08-58-30_NAc_dlight_rat1" # Good but video cut short and no LED
# f = r"C:\Users\daswyga\Desktop\fiber_lick\2026-10-28_08-52-18_NAc_dlight_rat1"
f = r"2026-10-28_15-47-49_NAc_dlight_rat2"

EXAMPLE_DATA_DIR = Path(root + f)

# Configure each Pi by the name of its directory under pi-data*.
PI_PARAMETERS = {
    "fiber01": SyncParameters(pin=25),
    "fiber01lick": SyncParameters(pin=16),
}


def main() -> None:
    viewer_settings = ViewerSettings()
    paths = load_session_paths(EXAMPLE_DATA_DIR)
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
        sync_tables[pi_name] = build_pi_sync_lookup_tables(
            {pi_name: pi_paths.gpio_csv}, capacitance, parameters
        )[pi_name]
        camera_files[pi_name] = (pi_paths.video, pi_paths.video_pts)

    for pi_name, sync_table in sync_tables.items():
        maximum_error_ms = sync_table["pulse_width_error_ms"].abs().max()
        print(
            f"{pi_name}: {len(sync_table)} synchronization points "
            f"(maximum pulse-width error: {maximum_error_ms:.3f} ms)"
        )

    videos = open_pi_videos(camera_files, viewer_settings)
    try:
        viewer = LickometerViewer(
            capacitance,
            sync_tables,
            videos,
            viewer_settings,
            title=paths.lickometer_csv.stem,
        )
    except Exception:
        for video in videos.values():
            video.close()
        raise
    viewer.show()


if __name__ == "__main__":
    main()
