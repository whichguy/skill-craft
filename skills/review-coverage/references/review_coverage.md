## Review Coverage

*Improve to exhaustion after implement.*

**Run when:** implementation landed, suite green, and any first-pass post-impl
review is done. Not before.
**Do not merge / declare done** until residual Status is terminal **complete**
(or you explicitly accept a **stopped** halt).

| Field | Value |
|-------|--------|
| Base ref | `<sha before implementation>` |
| Repo | `<absolute git root>` |
| Target paths | `<repo-relative pathspecs — no TBD>` |
| Test command | `<exact cmd — or N/A — no automated tests: reason>` |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal (default) |
| Plan contract | `<absolute plan path>` bound at campaign start (SHA-256) |
| Specs | Spec anchors + Implementation Intent Questions (READ-ONLY in cycles) |

**Preconditions:** clean working tree for commits; pathspec-only commits; never `git add -A`.

### Objective (paste into /goal)

Post-ship review coverage for plan <plan_path> (hash <sha256>).
Base ref: <BASE_REF>. Target paths: <PATHS>. Test command: <CMD>.

Each turn: one /review-converge round.

1. Forward (specs → code): re-read bound plan contract; fix material drift vs
   anchors/intent questions; pathspec commit material fixes; evidence =
   diff hunk, named test, or command+exit in the ledger.
2. Reverse (code → specs): diff branch vs <BASE_REF>; find violated anchors,
   broken intent answers, regressions, blast-radius surprises; fix or waive
   under Feedback disposition with reason.

Update ledger rows Anchor ID → proof. Do not edit the plan file during cycles.
Anchor Status writeback (if any) uses status **verified** (never "proven").

Complete only after **two consecutive** rounds with zero material findings
**and** a successful terminal test run on the second clean candidate.
stopped(...) is a bounded unsuccessful halt, not objective-met.
Hard stops: same-error×3, no-progress×3, host max-turns/budget, max-cycles.
Never unlimited ralph. Minors → Deferred (P2).

### Cycle log

| # | Date | Forward | Reverse | Material? | Suite | Commit |
|---|------|---------|---------|-----------|-------|--------|
|   |      |         |         |           |       |        |

### Waiver

Replace the section body with:
None — residual loop waived: <reason>
