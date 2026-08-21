import json
import tempfile
import unittest
from pathlib import Path

from snapshot_sync.read import Reader
from snapshot_sync.sync import run_sync


class RefusesUnvouched(unittest.TestCase):
    def test_snapshot_without_marker_is_invisible(self):
        with tempfile.TemporaryDirectory() as tmp:
            snaps = Path(tmp, "snapshots")
            snaps.mkdir()
            (snaps / "orphan.jsonl").write_text('{"id": 1}\n')
            self.assertIsNone(Reader(tmp).latest())
            self.assertEqual(Reader(tmp).items(), [])

    def test_count_mismatch_falls_back_to_older_good_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_sync(None, tmp, fetch=iter([{"id": i} for i in range(5)]))
            damaged = run_sync(None, tmp, fetch=iter([{"id": i} for i in range(9)]))
            snap = Path(tmp, damaged["snapshot"])
            lines = snap.read_text().splitlines()
            snap.write_text("\n".join(lines[:3]) + "\n")
            reader = Reader(tmp)
            row = reader.latest()
            self.assertIsNotNone(row)
            self.assertEqual(row["items"], 5, "must fall back to the run that verifies")
            self.assertEqual(len(reader.items()), 5)

    def test_marker_with_missing_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = run_sync(None, tmp, fetch=iter([{"id": 1}]))
            Path(tmp, marker["snapshot"]).unlink()
            self.assertIsNone(Reader(tmp).latest())


class Cache(unittest.TestCase):
    def test_run_index_cached_until_mtime_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_sync(None, tmp, fetch=iter([{"id": 1}]))
            reader = Reader(tmp)
            first = reader._runs()
            self.assertIs(first, reader._runs(), "unchanged file must serve the cache")
            with open(Path(tmp, "runs.jsonl"), "a") as f:
                f.write(json.dumps({"run_id": "x", "snapshot": "snapshots/x.jsonl",
                                    "items": 0, "finished": "2026-01-01T00:00:00+00:00"}) + "\n")
            self.assertIsNot(first, reader._runs(), "a new marker must bust the cache")


class Age(unittest.TestCase):
    def test_data_age_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(Reader(tmp).data_age_seconds())
            run_sync(None, tmp, fetch=iter([{"id": 1}]))
            age = Reader(tmp).data_age_seconds()
            self.assertIsNotNone(age)
            self.assertLess(age, 60)
            self.assertGreaterEqual(age, 0)


if __name__ == "__main__":
    unittest.main()
