import csv
import tempfile
import unittest
from pathlib import Path

from lick_analysis import generate_session_csv
from lick_analysis.session_finder import CSV_FILENAME, DATA_DIRECTORY_FILENAME


class GenerateSessionCsvTests(unittest.TestCase):
    def test_default_pi_names_allow_missing_video(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            session = root / "2026-11-06_09-00-00_validation_rat33"
            lickometer = session / "lickometer" / "trace.csv"
            lickometer.parent.mkdir(parents=True)
            lickometer.touch()
            (session / "pi-data_001" / "fiber01lick" / "cam").mkdir(parents=True)
            top_video = session / "pi-data_001" / "fiber01" / "cam" / "top.mp4"
            top_video.parent.mkdir(parents=True)
            top_video.touch()

            with generate_session_csv(root).open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(rows[0]["lick_camera_video_path"], "")
            self.assertEqual(rows[0]["top_camera_video_path"], str(top_video.relative_to(root)))
            self.assertEqual(
                (root / DATA_DIRECTORY_FILENAME).read_text(encoding="utf-8"),
                f"{root.resolve()}\n",
            )

    def test_indexes_sessions_with_selected_and_missing_cameras(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "2026-11-05_12-06-58_validation_rat31"
            second = root / "2026-11-05_12-36-44_validation_rat32"
            for session in (first, second):
                (session / "lickometer").mkdir(parents=True)
                (session / "lickometer" / "trace.csv").touch()

            first_lick_video = first / "pi-data_001" / "lick-test-01" / "cam" / "lick.mp4"
            first_top_video = first / "pi-data_001" / "top-test-01" / "cam" / "top.mp4"
            second_top_video = second / "pi-data_002" / "top-test-01" / "cam" / "top.mp4"
            for video in (first_lick_video, first_top_video, second_top_video):
                video.parent.mkdir(parents=True)
                video.touch()
            (root / "predictions").mkdir()

            csv_path = generate_session_csv(
                root, lick_camera_pi="lick-test-01", top_camera_pi="top-test-01"
            )

            self.assertEqual(csv_path, root / CSV_FILENAME)
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0], {
                "session_name": first.name,
                "rat_id": "rat31",
                "capacitance_trace_path": str((first / "lickometer" / "trace.csv").relative_to(root)),
                "lick_camera_video_path": str(first_lick_video.relative_to(root)),
                "top_camera_video_path": str(first_top_video.relative_to(root)),
            })
            self.assertEqual(rows[1], {
                "session_name": second.name,
                "rat_id": "rat32",
                "capacitance_trace_path": str((second / "lickometer" / "trace.csv").relative_to(root)),
                "lick_camera_video_path": "",
                "top_camera_video_path": str(second_top_video.relative_to(root)),
            })

    def test_separate_output_directory_and_missing_lickometer(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_directory = root / "data"
            session = data_directory / "2026-11-06_09-00-00_validation_rat33"
            (session / "pi-data_001" / "fiber01").mkdir(parents=True)
            output_directory = root / "output"

            csv_path = generate_session_csv(data_directory, output_directory=output_directory)

            self.assertEqual(csv_path, output_directory / CSV_FILENAME)
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertEqual(rows[0]["capacitance_trace_path"], "")
            self.assertEqual(rows[0]["lick_camera_video_path"], "")
            self.assertEqual(rows[0]["top_camera_video_path"], "")
            self.assertEqual(
                (output_directory / DATA_DIRECTORY_FILENAME).read_text(encoding="utf-8"),
                f"{data_directory.resolve()}\n",
            )


if __name__ == "__main__":
    unittest.main()
