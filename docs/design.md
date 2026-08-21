---
type: Reference
title: Design notes
description: How the pieces fit together.
---

# Design notes

## What this is

Two programs want the same data. One talks to a slow, rate-limited,
authenticated upstream. The other serves a dashboard and wants answers in
milliseconds, for free, with no credentials. The snapshot seam is the
contract that lets both exist. The sync job owns the pull. The reader owns
nothing but files. They meet at an atomic snapshot whose completeness
marker lands last.

The failure this kills is quiet: a reader that consumes a half-written
export does not crash. It serves a plausible, wrong answer with perfect
uptime. Wrongness with good timing is the worst failure mode a data
surface has, because nobody files a ticket about it.

## How it works

```
 upstream API --> source.py --> sync.py --> data/snapshots/<run>.jsonl
 (429s, 5xx,     (Retry-After,   (tmp -> fsync -> os.replace)
  pagination)     backoff,              |
                  timeout)              v   only after the file is final
                                 data/runs.jsonl  <-- the marker, appended last
                                        |
                                        v
                                    read.py  --> items(), data_age_seconds()
                                 (verify count, fall back, cache)
```

One run produces two durable artifacts. The snapshot file holds one JSON
object per line. The marker row vouches for it:

```json
{"run_id":"20260821T015500-6abde6e1",
 "snapshot":"snapshots/20260821T015500-6abde6e1.jsonl",
 "items":100,"sha256":"c41d...","started":"...","finished":"..."}
```

The write order is the design. Items stream to `<run>.jsonl.tmp`. The file
syncs, then `os.replace` makes it final, and only then does the marker
append with the item count. A crash at any earlier point leaves files no
reader will ever consult. No cleanup step exists that correctness depends
on.

The reader walks `runs.jsonl` newest-first and serves the first row that
verifies: the snapshot exists and its line count matches. Anything else
gets skipped, with fallback to the newest run that checks out. Data age is
a number the surface can display, because stale and labeled beats fresh
and wrong.

## Worked example

Real output against the bundled flaky source, which answered one 500 and
one 429 during this pull:

```
$ python3 -m snapshot_sync serve-mock --port 8899 --fail-first 1 --rate-limit-every 7
$ python3 -m snapshot_sync sync --source http://127.0.0.1:8899 --data ./data
run 20260821T015500-6abde6e1: 100 items -> snapshots/20260821T015500-6abde6e1.jsonl
$ python3 -m snapshot_sync status --data ./data
run 20260821T015500-6abde6e1: 100 items, age 0s
```

The faults never surface in the result. That is the point of the retry
policy. The mock source exists so the failure paths run in tests and
demos, not for the first time in production.

Every rule and its citation: [rules.md](rules.md). Limits and provenance:
[lineage.md](lineage.md).
