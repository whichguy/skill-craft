---
bump: patch
---

Repair compact-v4 live experiment evidence after the three-worker Grok trial exposed a truncated preparation result and auditor assumptions about prompt ownership, Python interpreter identity, and inspection-specific patch locations.

Keep full setup and dispatch evidence on disk and emit small versioned, hash-bound summaries. Bind worker ownership through the exact native launch and pinned action packet. Use the producer runtime evidenced by the frozen script invocation instead of the auditor process runtime. Compare semantic commit evidence while independently checking patch bytes and containment. Retain fail-closed checks for truncation, hash drift, cross-worker packets, foreign paths, and unsafe patch artifacts.

The original trial remains failed. Offline qualification passed 239 tests, including seven new regressions. These changes affect the experiment harness and auditor; they do not establish a speedup or live qualification. Fresh live delivery cases remain required before a live-pass claim.
