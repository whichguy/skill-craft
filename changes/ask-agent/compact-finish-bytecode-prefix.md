---
bump: patch
---

Accept exactly one redundant `PYTHONDONTWRITEBYTECODE=1` assignment before the pinned compact-v4 `python3 -B` finish command. Preserve exact matching of every remaining argument, binding digest, worker, and working directory. Reject other or duplicate assignments, `env` wrappers, and wrong digests.

The live r4 worker really completed its finish call, but this harmless prefix made the native audit fail. Retain the original failed verdict. A separate read-only replay passes all 28 gates without modifying the evidence; 84 native and compact regression tests pass. Fresh live qualification remains required.
