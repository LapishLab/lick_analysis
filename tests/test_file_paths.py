import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from lick_analysis.file_paths import (
    LickometerPaths,
    get_lickometer_paths,
    load_session_paths,
    parse_lickometer_filename,
    parse_pi_datetime,
)


class SessionPathsTests(unittest.TestCase):
    def test_lickometer_paths_handle_missing_and_invalid_filename(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            session = Path(temporary_directory)
            self.assertEqual(
                get_lickometer_paths(session),
                LickometerPaths(csv=None, datetime=None, board_id=None),
            )

            csv = session / "lickometer" / "trace.csv"
            csv.parent.mkdir()
            csv.touch()
            self.assertEqual(
                get_lickometer_paths(session),
                LickometerPaths(csv=csv, datetime=None, board_id=None),
            )

    def test_load_session_paths_extracts_recording_datetimes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            session = Path(temporary_directory) / "2026-11-05_12-06-58_validation_rat31"
            pi = session / "fiber01"
            for relative_path in (
                "cam/20261105_120729_126317.mp4",
                "gpio/20261105_120728_023100.csv",
                "mic/20261105_120730_000001.wav",
            ):
                path = pi / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            lickometer = session / "lickometer" / "test_2026_11_05_130812.csv"
            lickometer.parent.mkdir()
            lickometer.touch()

            paths = load_session_paths(session)
            self.assertEqual(paths.pis["fiber01"].video_datetime, datetime(2026, 11, 5, 12, 7, 29, 126317))
            self.assertEqual(paths.pis["fiber01"].gpio_datetime, datetime(2026, 11, 5, 12, 7, 28, 23100))
            self.assertEqual(paths.pis["fiber01"].audio_datetime, datetime(2026, 11, 5, 12, 7, 30, 1))
            self.assertIsInstance(paths.lickometer, LickometerPaths)
            self.assertEqual(paths.lickometer.csv, lickometer)
            self.assertEqual(paths.lickometer.datetime, datetime(2026, 11, 5, 13, 8, 12))
            self.assertEqual(paths.lickometer.board_id, "test")

    def test_recording_datetime_parsers_handle_missing_and_invalid_names(self):
        self.assertIsNone(parse_pi_datetime(None))
        self.assertIsNone(parse_pi_datetime(Path("video.mp4")))
        self.assertIsNone(parse_pi_datetime(Path("20260230_120729_126317.mp4")))
        self.assertEqual(parse_pi_datetime(Path("20261105_120729.mp4")), datetime(2026, 11, 5, 12, 7, 29))
        self.assertEqual(parse_lickometer_filename(None), (None, None))
        self.assertEqual(parse_lickometer_filename(Path("trace.csv")), (None, None))
        self.assertEqual(parse_lickometer_filename(Path("2026_11_05_130812.csv")), (None, None))
        self.assertEqual(parse_lickometer_filename(Path("test_2026_02_30_130812.csv")), (None, None))
        self.assertEqual(
            parse_lickometer_filename(Path("fiber01Lickometer_2026_11_05_130812.csv")),
            ("fiber01Lickometer", datetime(2026, 11, 5, 13, 8, 12)),
        )
        self.assertEqual(
            parse_lickometer_filename(Path("board_A_2026_11_05_130812.csv")),
            ("board_A", datetime(2026, 11, 5, 13, 8, 12)),
        )

    def test_load_session_paths_extracts_datetime_from_session_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for name, expected in (
                ("2026-11-05_12-06-58_validation_rat31", datetime(2026, 11, 5, 12, 6, 58)),
                ("2026-11-05_12-06-58", datetime(2026, 11, 5, 12, 6, 58)),
                ("2026-11-05_validation_rat31", None),
                ("2026-02-30_12-06-58_validation_rat31", None),
                ("2026-11-05_25-06-58_validation_rat31", None),
            ):
                with self.subTest(name=name):
                    session = root / name
                    (session / "fiber01").mkdir(parents=True)
                    (session / "lickometer").mkdir()
                    self.assertEqual(load_session_paths(session).session_datetime, expected)

    def test_load_session_paths_extracts_id_from_session_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for name, expected in (
                ("2026-11-05_validation_RAT31", "31"),
                ("2026-11-05_groupAlpha_validation", "alpha"),
                ("2026-11-05_ratA-1_validation", "a-1"),
                ("2026-11-05_validation", None),
                ("2026-11-05_rat_validation", ""),
                ("2026-11-05_group_", ""),
            ):
                with self.subTest(name=name):
                    session = root / name
                    (session / "fiber01").mkdir(parents=True)
                    lickometer_csv = session / "lickometer" / "trace.csv"
                    lickometer_csv.parent.mkdir()
                    lickometer_csv.touch()
                    self.assertEqual(load_session_paths(session).id, expected)


if __name__ == "__main__":
    unittest.main()
