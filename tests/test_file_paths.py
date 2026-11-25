import tempfile
import unittest
from pathlib import Path

from lick_analysis.file_paths import load_session_paths


class SessionPathsTests(unittest.TestCase):
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
