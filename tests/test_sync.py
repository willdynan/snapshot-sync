import json
import tempfile
import threading
import unittest
from pathlib import Path

from snapshot_sync.mock_source import MockSource
from snapshot_sync.read import Reader
from snapshot_sync.source import SourceError, _get
from snapshot_sync.sync import LockHeld, run_sync


def serve(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


class HappyPath(unittest.TestCase):
    def test_full_pull_lands_and_reads_back(self):
        server = MockSource()
        serve(server)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                marker = run_sync(server.url, tmp, page_size=30)
                self.assertEqual(marker["items"], 100)
                reader = Reader(tmp)
                items = reader.items()
                self.assertEqual(len(items), 100)
                self.assertEqual(items[0]["name"], "item-000")
        finally:
            server.shutdown()
            server.server_close()


class Faults(unittest.TestCase):
    def test_completes_through_rate_limiting(self):
        server = MockSource(rate_limit_every=3)
        serve(server)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                marker = run_sync(server.url, tmp, page_size=20)
                self.assertEqual(marker["items"], 100)
                self.assertGreater(server.requests, 5,
                                   "429 responses must have forced retries")
        finally:
            server.shutdown()

    def test_completes_through_transient_500s(self):
        server = MockSource(fail_first=2)
        serve(server)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                marker = run_sync(server.url, tmp, page_size=50)
                self.assertEqual(marker["items"], 100)
        finally:
            server.shutdown()

    def test_persistent_failure_raises_instead_of_looping(self):
        server = MockSource(fail_first=10_000)  # never recovers
        serve(server)
        try:
            with self.assertRaises(SourceError):
                _get(f"{server.url}/items", sleeper=lambda s: None)
            self.assertEqual(server.requests, 6, "5 retries then give up")
        finally:
            server.shutdown()
            server.server_close()


class CrashMidRun(unittest.TestCase):
    def test_reader_stays_on_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = [{"id": i} for i in range(50)]
            run_sync(None, tmp, fetch=iter(good))

            def dying():
                for i in range(10):
                    yield {"id": i}
                raise RuntimeError("source died mid-pull")

            with self.assertRaises(RuntimeError):
                run_sync(None, tmp, fetch=dying())

            runs = Path(tmp, "runs.jsonl").read_text().splitlines()
            self.assertEqual(len(runs), 1, "a failed run must leave no marker")
            reader = Reader(tmp)
            self.assertEqual(len(reader.items()), 50)
            leftovers = list(Path(tmp, "snapshots").glob("*.tmp"))
            self.assertEqual(leftovers, [], "failed runs clean up their tmp file")


class Locking(unittest.TestCase):
    def test_second_sync_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".sync.lock").write_text("held")
            with self.assertRaises(LockHeld):
                run_sync(None, tmp, fetch=iter([]))

    def test_lock_released_after_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_sync(None, tmp, fetch=iter([{"id": 1}]))
            self.assertFalse(Path(tmp, ".sync.lock").exists())


class MarkerIntegrity(unittest.TestCase):
    def test_marker_hash_matches_file(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            marker = run_sync(None, tmp, fetch=iter([{"id": 1}, {"id": 2}]))
            body = Path(tmp, marker["snapshot"]).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), marker["sha256"])
            self.assertEqual(marker["items"], 2)
            row = json.loads(Path(tmp, "runs.jsonl").read_text())
            self.assertEqual(row, marker)


if __name__ == "__main__":
    unittest.main()
