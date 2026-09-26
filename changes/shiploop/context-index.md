---
bump: minor
---
Every stage now gets the run's global picture. Each save writes
`context-index.md`, a derived index of the request, every accepted planning
result with its summary, notes and Improve lessons, the plan's assumptions, each
work item's accepted results, the outer loop and superseded results. Every packet
names it right after the callback line, and active packets add a script-owned
"Read first" list of the accepted results that stage builds on (for example,
`verify` reads the spec, test strategy and the item's step-plan and test-spec).
`pause` now refuses context-housekeeping reasons (a clear, context boundary,
compaction or fresh conversation), and the keepalive log records why a run paused.
