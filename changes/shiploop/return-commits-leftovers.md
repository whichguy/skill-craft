---
bump: patch
---
`workspace plan-return` first commits product files still uncommitted in the candidate onto the run branch, so a reviewed return fast-forwards instead of falling back to uncommitted working-tree changes. Run evidence, protected paths, caller exclusions and files that look like credentials are never committed. A release plan whose `consumer_entry` sources are absolute paths is refused with a clear message instead of crashing.
