You are an independent reviewer. Read-only: do not edit files and do not start any model, host CLI or network service. You may run local read-only commands (grep, reading files, `python3 -c` parsing). Run hermetic unit tests only if your sandbox lets them write under /tmp.

Repository: skill-craft, a public monorepo of portable agent skills, exported in the current directory from origin/main (see REVIEW-CONTEXT/SOURCE.txt). Git history is not available here. REVIEW-CONTEXT/recent-commits-full.txt holds the full messages of the last 40 commits that touch the E2E skill or harness; REVIEW-CONTEXT/older-commits-oneline.txt lists the older ones. REVIEW-CONTEXT/latest-campaign-E2E-FINDINGS-20261118.md is the findings report of the most recent improvement campaign run with this skill (its linked evidence files are not in the repository).

Subject: the ShipLoop E2E test skill, `skills/shiploop-e2e-audit/` (the SKILL.md card, IMPROVE.md, AUDIT.md, scripts/resolve_harness.py, and the bundled `harness/` with its tests), together with the source harness it drives for improvement campaigns, `test/shiploop_e2e/` (run.py, iterate.py, cycle.py, hosts.py, review.py, SPEC.md, README.md, LEARNINGS.md, cases.json and the rest). Related parts you may need: `skills/shiploop/` (the skill under test), `skills/closed-loop/` and `test/shiploop_e2e/adapter/` (a generic improvement loop with a ShipLoop adapter), the journals under `docs/`, the suites under `test/` and their groups in `test/run_suites.py`, and `.github/workflows/`.

Question: inspect this E2E skill deeply and recommend whether there is anything the owner should do: fix, simplify, delete, document, measure, or leave alone. Judge by value to the owner's goal, not by tidiness.

The owner's stated goals and rules (quoted where marked):
1. Purpose (test/shiploop_e2e/SPEC.md, owner 2026-09-27): the E2E loop verifies ShipLoop's behavior; the product it builds is a probe. ShipLoop is a general SDLC execution engine. Example apps exemplify the SDLC; ShipLoop is never tuned for a sample.
2. Owner 2026-11-15: "I only care about modifying Shiploop as a generic facility or the end-to-end test for Shiploop as a generic facility. If we're doing something outside of that, I don't know if it's actually valuable because I'll end up deleting the Salesforce-specific run of Shiploop later." The test for any harness item: would it still matter if every Salesforce case were deleted?
3. Owner 2026-11-18: "Do not put artificial mandates which are not specifically necessary, such as the min python version." A requirement is only what the code needs, found by running it.
4. Owner 2026-11-14: no change unless outcomes differ; naming alone never justifies one. Keep it simple: fix what breaks a normal run and document the rest, rather than building guards against unlikely misuse.
5. Progress is a script-run test that passed, or a measured run, never a model's judgment.
6. Owner 2026-11-18, as recorded in commit 3c81b3ae: stop asking for routine preflight approval, focus on ShipLoop as a general SDLC skill, and start the first pass from a clean repository.
7. Every completed experiment is journaled with its evidence kept in the repository.

Cover, wherever you find something material:
- Does the skill do its job for a fresh operator on Claude Code, Codex and Grok, on macOS and Linux? Walk the card, then IMPROVE.md or AUDIT.md, then the commands as written. Would they run as written? What would break?
- Correctness defects on the code paths a normal campaign uses (launch, preflight, review, judge, qualification, promotion, evidence). Give a reproduction where you can.
- Measurement validity: can a campaign actually detect a ShipLoop improvement or regression? Consider the case oracles, held-out checks, calibration, ceiling effects, model-judged steps, and the token and efficiency counters.
- Duplication, dead code, Salesforce-only code, stale documentation, and maintenance cost against value. What could be deleted or merged with no loss?
- Overlaps or conflicts between the components named above.
- Anything that makes results non-reproducible or non-comparable across runs.

For each recommendation give: priority (P0 must fix, P1 should, P2 could, P3 leave), kind (bug, measurement, simplify or delete, docs, owner decision), evidence (file path plus symbol or line, quoting at most two lines), a concrete action, rough cost, and the outcome it changes. Then list the things you checked that look right and should be left alone, and the decisions only the owner can make. Lead with a three-sentence verdict. Be concrete, do not pad, and say "not checked" where you did not look.
