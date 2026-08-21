# snapshot-sync

![tests](https://github.com/willdynan/snapshot-sync/actions/workflows/tests.yml/badge.svg)

Internal dashboards die one of two deaths. Either every page load queries
the upstream API — slow, rate-limited, billed — or the dashboard reads a
half-written export and serves it as truth. The second death is worse
because nothing crashes: the surface stays up, fast, and wrong, and
nobody files a ticket about an answer that merely looks right.

The snapshot seam kills both. A sync job owns the pull. Readers own
nothing but files. They meet at an atomic snapshot whose completeness
marker lands *last* — and until the marker says a snapshot exists, it
doesn't, no matter what's on disk. Crash the sync anywhere you like:
readers keep serving the previous good snapshot, and data age is a number
the surface can show, because stale-and-labeled beats fresh-and-wrong.

The retries are boring on purpose. A 429 sleeps what Retry-After asks.
Transient errors back off under a hard timeout. A source that stays down
raises instead of looping, because a sync that loops forever is an outage
nobody notices. The bundled mock source throws 429s and 500s at the tests
so the failure paths run every day, not for the first time in production.

## Quickstart

```
python3 -m unittest discover -s tests            # no dependencies
python3 -m snapshot_sync serve-mock --port 8811  # a flaky demo source
python3 -m snapshot_sync sync --source http://127.0.0.1:8811 --data ./data
python3 -m snapshot_sync status --data ./data
```

## Going deeper

[docs/design.md](docs/design.md) walks the pieces with captured output.
[docs/rules.md](docs/rules.md) gives every rule its reason and its test.
[docs/lineage.md](docs/lineage.md) holds the honest limits and provenance.

Distilled August 2026 from production loaders that earned each rule the
hard way. The commit log starts at the distillation.
