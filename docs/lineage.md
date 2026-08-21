---
type: Reference
title: Lineage
description: Honest limits and provenance.
---

# Honest limits

- Full refresh per run, not a delta. Right for sources without a reliable
  modified-since filter, wasteful for large corpora.
- The lockfile is per-machine. The production versions ran as scheduled
  single-instance jobs. A shared lock is a deployment concern.
- The reader re-counts a snapshot's lines on access. Cheap at demo scale.
  At production scale the count moved behind the cache.
- The mock source has no auth. Credential handling stays out of scope on
  purpose. The seam is the point, and readers never hold source
  credentials at all.

# Lineage

This is a distillation, not a port. The pattern matured across several
production loaders and syncs during 2026. Each one fed an internal read
surface from a rate-limited upstream. The marker-last rule exists because
partial runs happen, and the partial runs that stayed invisible to every
consumer are the reason the rule survived. The systems, schedules, and row
counts stay out of this repo on purpose. The architecture is the artifact,
and the mock source is synthetic.

Distilled: August 2026. This repository began at distillation. The dates
above describe the pattern's history, not this commit log.
