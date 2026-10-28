from pathlib import Path

from lick_analysis import (
    LickometerViewer,
    SyncParameters,
    ViewerSettings,
    build_pi_sync_lookup_tables,
    discover_experiment,
    load_lickometer_data,
    open_pi_videos,
)


EXAMPLE_DATA_DIR = Path(
    r"C:\Users\daswyga\Desktop\fiber_lick\2026-10-26_08-58-30_NAc_dlight_rat1"
)


def main() -> None:
    sync_parameters = SyncParameters()
    viewer_settings = ViewerSettings()
    files = discover_experiment(EXAMPLE_DATA_DIR)
    capacitance = load_lickometer_data(files.lickometer_csv)
    sync_tables = build_pi_sync_lookup_tables(
        files.gpio_csvs,
        capacitance,
        sync_parameters,
    )

    for pi_name, sync_table in sync_tables.items():
        maximum_error_ms = sync_table["pulse_width_error_ms"].abs().max()
        print(
            f"{pi_name}: {len(sync_table)} synchronization points "
            f"(maximum pulse-width error: {maximum_error_ms:.3f} ms)"
        )

    videos = open_pi_videos(files.camera_files, viewer_settings)
    try:
        viewer = LickometerViewer(
            capacitance,
            sync_tables,
            videos,
            viewer_settings,
            title=files.lickometer_csv.stem,
        )
    except Exception:
        for video in videos.values():
            video.close()
        raise
    viewer.show()


if __name__ == "__main__":
    main()
