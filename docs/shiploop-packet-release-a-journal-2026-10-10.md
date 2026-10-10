# ShipLoop packet fixes, release A: journal (2026-10-10)

Plan: `docs/shiploop-packet-compaction-plan-2026-10-10.md` Phase 0 and Phase 1 (on branch rr23-9f8c87, commits a7d4a34b and
53b41262). Review that set the rows: `docs/shiploop-packet-review-2026-10-10.md` (c79e1294). Integration branch: pc1i-64ba2b
from origin/main 658ff4e3.

## Round 1: build (four branches, parallel worktrees from f950fd0d)

| Branch | Rows | Commit | Fail-first evidence (from each commit message) |
|---|---|---|---|
| pc1d (Phase 0) | packet anatomy tool; improve-bind packet keeps its own file | 1dcda7fd, 31ac161e | bind test red on `assertNotEqual(start, bind)`; tool pinned by 13 tests |
| pc1a | 2, 6, 7, 9, 10, 11 | 92a32a1d | 23 failures + 1 error in packet-completeness before the fix; route tests for check-row ids and assumption keys |
| pc1b | 1, 3, 8, 12, 13 | 1787e264 | release-verify gate, loop receipt and exit lines, test-author probe lines, Improve commit placement, implement progress |
| pc1c | 4, 5 | 6bd20ec1 | docs-class commits at integrate; one commit sentence; open-item route at system-test-author |

Merge: two textual conflicts (stage_spec, `_checked_line`), both sides kept. Found only by the combined run: the Run Review
real-engine seed left no `-improve.md` after the bind fix; the seed now binds the card (every label carried, 5 of 5).
Phase 0 baseline (checkers-1, 45 packets, 1,799,188 B): absolute paths 23.05% of bytes; lines shared by at least 80% of
packets 55.2%; status: firm. Evidence: `docs/experiments/packet-anatomy-20261010/`.

## Round 2: adversarial review (two Opus reviewers, read-only)

Evidence: `docs/experiments/release-a-review-20261010/` (03019f9a). Three blockers: (1) the loop lines pushed the regression
milestone narrative past the 8000-byte status-hook window (END at 8430 to 9368; the CLI never showed it); (2) the system-test
"route fails when run" open-item exit is refused by the rerun gate; (3) inner test stages offered an open-item route their
gates cannot accept. Should-fix: the commit rule false for in-place runs; two texts for one leftover rule; docs commits ignored
`--exclude`; a blocked loop result refused for its own prefilled receipt; a negative Improve lead in none mode; S-8 wording.
Fixed on pc2b (add26b4c, e9a7f610) and pc2a (ba08993b), merged. Decision recorded: the system-test run-time failure has no
gated exit yet (the promise was removed, not implemented); status: open follow-up needing design.

## Round 3: verification run

Case checkers, host claude, model claude-sonnet-5-5, `--source checkout` (this branch, built as skill-craft 1.26.1 /
ShipLoop 0.58.0), planning review stage (default). Output `/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet`; compact
evidence `docs/experiments/release-a-verification-20261010/` (run doc, facts, result head, a no-model walk table).
Compared with checkers-1 (release 1.26.0, same case, host and model):

| Measure | checkers-1 | this branch |
|---|---|---|
| outcome | PASS, done in 13 min | PASS, done in 13 min (770.6 s, 0 resumes) |
| refusals | 3: test-green receipt not in evidence_refs; regression terminal packet still active; release-plan check row with ids | 2, both at step-plan: one check row carrying a TC id, then the same result resubmitted after the model's own `sed -i` failed |
| calls / glue scripts | 112 / 3 | 103 / 0 |
| Improve | 8 children, 14 passes | 8 children, 16 passes |
| product commits by the model | 1 (365ab7f, undeclared AGENTS.md at integrate) | 0 (all by ShipLoop Workspace) |
| packet bytes (37 stages) | 1,397,032 | 1,388,217 |
| README nobody asked for | yes | yes, from the step-plan duty's own example; fixed in d4da685b (not yet run live) |

Findings (n = 1 run each side, so read as signals, not rates):
- The three refusal classes of checkers-1 did not recur. Status: interim (one run).
- The check-row id refusal moved from release-plan to step-plan: the test strategy gives a check case a TC id and the step plan
  is told to declare TC ids; the sentence "a check row carries no ids" is printed but was missed once. Candidate follow-up: the
  refusal names the row and says where the case's id goes. Status: exploratory.
- The model made no git commit; ShipLoop committed W1 (README included, as documentation) and the leftover system test before
  the return. Status: interim.
- Calls fell by 9 and glue scripts by 3; time is unchanged. Status: interim.

## Open after release A

- System-test: a recorded case whose route fails at run time has no gated open-item exit (needs a recorded host-unavailable
  disposition); review N5 (baseline commands re-run by hand) and N6 (head grows with the command list).
- Negative Improve lines still allowlisted in none mode (for the Phase 2 diet).
- One pre-existing test failure on origin/main: shiploop-status-display
  `test_packet_carries_block_early_and_status_file_matches_cli` (progress-observer files appear during the check).
