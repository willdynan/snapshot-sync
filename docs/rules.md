---
type: Reference
title: Rules
description: The reasoning behind every rule.
---

# The rules, with their citations

Every rule exists because the easy version fails in a specific way. The
test file after each rule is the citation.

## The marker lands last (`tests/test_sync.py`)

The crash test kills the source generator mid-pull and asserts two things:
no marker landed, and the reader still serves the previous snapshot. The
tmp file cleans up on failure, and even a leftover tmp is invisible — the
reader only trusts what a marker vouches for.

## Readers refuse what the marker does not vouch for (`tests/test_read.py`)

An orphan snapshot with no marker is invisible. A marker whose file is
missing gets skipped. A marker whose count disagrees with the file gets
skipped, with fallback to the newest run that verifies. A partial snapshot
is not mostly fresh data. It is a wrong answer with good timing.

## Backoff belongs to the source (`tests/test_sync.py`)

A 429 sleeps what the source asks through Retry-After, capped at 30
seconds — the source knows its limits and you do not. Transient 5xx and
network errors get bounded exponential backoff. Every request carries an
explicit timeout, because an unbounded network call is a hang nobody pages
on. A source that stays down raises after six attempts instead of looping.
A sync that loops forever is an outage nobody notices.

## One sync at a time (`tests/test_sync.py`)

An exclusive-create lockfile guards the run and always releases through
`finally`. A second sync fails with a clear message naming the lock,
rather than interleaving two writers into one snapshot.

## Readers stay cheap (`tests/test_read.py`)

The run index caches on the file's mtime and size together. Mtime alone is
not a safe key: two appends can land inside one filesystem timestamp tick.
This repo's own test caught exactly that on its first run. Size moves on
every append.

## Extending it

- **A real source**: replace `fetch_all()` with any generator of dicts.
  `run_sync(fetch=...)` accepts the iterator directly, which is also how
  the crash tests inject a dying source.
- **Incremental pulls**: keep the marker semantics and add a `since`
  parameter to the fetch. The marker-last rule does not care how the items
  arrived.
- **A different store**: the reader only needs three operations — list
  markers, count lines, read lines. Object storage versions of all three
  exist.
