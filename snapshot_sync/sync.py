"""The write path. The completeness marker is written last — that is the design.

Order of operations: items stream to <run>.jsonl.tmp; fsync; os.replace to the
final name; only then is a run row appended (and fsynced) to runs.jsonl. A crash
at any point before the marker leaves files no reader will ever consult. There
is no cleanup step a crash can skip that correctness depends on.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .source import fetch_all


class LockHeld(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_sync(source_url, data_dir, page_size: int = 50, fetch=None) -> dict:
    data = Path(data_dir)
    (data / "snapshots").mkdir(parents=True, exist_ok=True)
    lock = data / ".sync.lock"
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise LockHeld(f"another sync holds {lock}; remove it only if that process is dead")
    try:
        os.write(lock_fd, str(os.getpid()).encode())
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        started = _now()
        tmp = data / "snapshots" / f"{run_id}.jsonl.tmp"
        final = data / "snapshots" / f"{run_id}.jsonl"
        digest = hashlib.sha256()
        count = 0
        items = fetch if fetch is not None else fetch_all(source_url, page_size)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                for item in items:
                    line = json.dumps(item, separators=(",", ":")) + "\n"
                    f.write(line)
                    digest.update(line.encode("utf-8"))
                    count += 1
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        os.replace(tmp, final)
        marker = {
            "run_id": run_id,
            "snapshot": f"snapshots/{run_id}.jsonl",
            "items": count,
            "sha256": digest.hexdigest(),
            "started": started,
            "finished": _now(),
        }
        with open(data / "runs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(marker) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return marker
    finally:
        os.close(lock_fd)
        lock.unlink(missing_ok=True)
