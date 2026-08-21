# snapshot-sync

The snapshot seam: an expensive, rate-limited pull decoupled from a free,
instant read surface by an atomic snapshot. The completeness marker lands
last.

Internal dashboards die two deaths. They query the upstream API on every
page load, or they read a half-written export and serve it as truth. This
pattern kills both. One job owns the pull. Readers own nothing but a file.
A snapshot does not exist until its marker says so.

## Quickstart

```
python3 -m unittest discover -s tests            # no dependencies
python3 -m snapshot_sync serve-mock --port 8811  # a flaky demo source
python3 -m snapshot_sync sync --source http://127.0.0.1:8811 --data ./data
python3 -m snapshot_sync status --data ./data
```

The mock source paginates 100 items and injects 429s and 500s. The sync
completes anyway. That is the demo.

## Layout

```
snapshot_sync/source.py       fetch with Retry-After and bounded backoff
snapshot_sync/sync.py         atomic writes, marker last
snapshot_sync/read.py         verify, fall back, report age
snapshot_sync/mock_source.py  a flaky paginated source for tests
```

The walkthrough: [docs/design.md](docs/design.md). The rules:
[docs/rules.md](docs/rules.md). Limits and provenance:
[docs/lineage.md](docs/lineage.md). Distilled August 2026 from production
practice. The commit log starts at distillation.
