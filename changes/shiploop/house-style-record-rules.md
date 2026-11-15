---
bump: patch
---
House-style extraction now records the records a repository requires with a change (decision records, changelog entries, version bumps): where each lives, its template and index, and which changes trigger it. Later stages then carry the rule with the work item instead of relying on a contribution file read once at discovery.
