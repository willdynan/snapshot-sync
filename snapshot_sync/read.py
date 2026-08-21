"""The read surface. Trust nothing the marker does not vouch for.

A run row is only served if its snapshot file exists and its line count matches
the recorded item count; anything else is skipped and the reader falls back to
the newest run that verifies. The run index is cached on runs.jsonl's
(mtime, size), so repeated reads cost nothing until a new run lands.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class Reader:
    def __init__(self, data_dir):
        self.data = Path(data_dir)
        self._cache = (None, [])

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
        snap = self.data / row["snapshot"]
        if not snap.exists():
            return False
        with open(snap, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
        return count == row["items"]

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
