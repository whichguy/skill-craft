---
bump: patch
---
Agents Improve packets and context now require a coordinated wait (blocking preferred; async ≥120 s with same-handle retry) and interpreting the worker's native return before `complete`; F17 fan-out notes tell the parent to synthesize collected findings.
