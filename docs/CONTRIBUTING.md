---
type: Runbook
title: Contributing
description: One-time hook setup for a fresh clone.
---

# Contributing

One-time setup after cloning:

```
git config core.hooksPath .githooks
```

The pre-commit hook runs the test suite. On the author's machine it also
runs a private style audit. A rule without an enforcer is a wish, so the
gate runs at commit time, not on the honor system.
