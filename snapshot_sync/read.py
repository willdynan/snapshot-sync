"""The read surface. Trust nothing the marker does not vouch for.

The reader serves a run row only when its snapshot verifies: the file
exists, the line count matches, and the bytes hash to the recorded sha256.
It skips anything else and falls back to the newest run that verifies. The
run index caches on runs.jsonl's (mtime, size), and verified snapshots are
remembered — they are write-once, so one hash per snapshot per reader.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class Reader:
    def __init__(self, data_dir):
        self.data = Path(data_dir)
        self._cache = (None, [])
        self._verified = set()

    def _runs(self) -> list[dict]:
        path = self.data / "runs.jsonl"
        try:
            stat = path.stat()
        except FileNotFoundError:
            return []
        # mtime alone is not a safe key: two appends can land inside one
        # filesystem timestamp tick. Size changes on every append.
        key = (stat.st_mtime_ns, stat.st_size)
        if self._cache[0] == key:
            return self._cache[1]
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self._cache = (key, rows)
        return rows

    def _verifies(self, row: dict) -> bool:
        # The count is the cheap screen; the hash is the verdict. A marker
        # whose hash nobody checks is decoration, and decoration is how a
        # corrupt snapshot serves with perfect uptime.
        if row["run_id"] in self._verified:
            return True
        snap = self.data / row["snapshot"]
        if not snap.exists():
            return False
        body = snap.read_bytes()
        if body.count(b"\n") != row["items"]:
            return False
        if hashlib.sha256(body).hexdigest() != row.get("sha256"):
            return False
        self._verified.add(row["run_id"])
        return True

    def latest(self) -> dict | None:
        for row in reversed(self._runs()):
            if self._verifies(row):
                return row
        return None

    def items(self) -> list[dict]:
        row = self.latest()
        if row is None:
            return []
        with open(self.data / row["snapshot"], "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def data_age_seconds(self) -> float | None:
        row = self.latest()
        if row is None:
            return None
        finished = datetime.fromisoformat(row["finished"])
        return (datetime.now(timezone.utc) - finished).total_seconds()
