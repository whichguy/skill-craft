# Orchestrator improvement passes

A journal of improvement passes over the Plan Orchestrator (ShipLoop's parallel
chain, Plan Dispatcher, Ask Agent and the chain E2E harness), started
2026-10-04 under the goal: plan improvements from the learnings, research as
needed, implement and deploy, until two consecutive passes find only trivial
improvements.

Each pass reviews the learnings (`test/shiploop_e2e/LEARNINGS.md`, the test
map, the ledger, recent commits), lists candidates and classifies each:

- **Material:** a normal run fails, stalls or is misled (wrong guidance, a wrong
  or misleading verdict), or an expectation the spec sets is untested. Fixed in
  the pass, tested, released and verified.
- **Trivial:** wording, stale names, cosmetics; no change to any run's behaviour
  or verdict. Fixed when cheap; a pass whose candidates are all trivial counts
  toward the two clean passes.
- **Out of scope:** owner decisions not yet made, another session's active
  area (Improve, Backchain, planning prompts, cost work on main), or
  adversarial-only gaps (KISS: documented as known limits).

## Pass 1 — 2026-10-04

Base: main at bc3046db (skill-craft 1.19.0, ShipLoop 0.51.0).

| # | Candidate | Evidence | Class | Action |
|---|---|---|---|---|
| 1 | Does ShipLoop find parallel work when the request does not ask for it? | Every chain case says "implement in parallel as separate chain steps". step-plan's done-criteria say "one step is fine"; its chain guidance applies "for a plan with dependency-independent implementation steps", once the model has already split the work | material (an expectation the chain guide sets is untested) | New case `temperature-plain` (temperature-report without the delivery sentence); live run p1-temperature-plain on Claude, 1.19.0 |
| 2 | Interrupted runs are held to the 30-minute budget | c1 30.9 min: the deliberate kill replays the lost workers' work, so "over" measured recovery | material (a misleading verdict) | `budget_facts(..., interrupted=True)` reports "n/a" with the reason; test |
| 3 | Plan Dispatcher SKILL.md still says "Retry only after confirming the old worker stopped" | Contradicts the protocol and the F1 fix since 0.6.0; a standalone user who loses a host session is steered back into the deadlock | material (wrong guidance) | Card names the lost-worker case and points to the protocol's limits; change note |
| 4 | Native pilot README says it uses the "frozen Plan Dispatcher v3 fixture" | `DISPATCHER_V3` points at `skills/plan-dispatcher`; the fixture was removed in 4a7720fb | trivial | README wording |
| 5 | Batch B/C Claude runs had the user's claude.ai connectors loaded | bc3046db (another session): runs without `--strict-mcp-config` loaded 15 connectors | trivial for this work (fixed upstream; only confounds those runs' token counts) | Note in LEARNINGS |
| 6 | Fragile test reading real Git state | flagged 2026-10-03 | done upstream (04af25ba) | none |
| 7 | Script-made proof that a host is gone | design review 2026-10-04 | out of scope (KISS: no normal-run failure; documented limit) | none |
| 8 | The chain on Codex and Grok | runtime decision and credits pending | out of scope (owner decision) | none |

### Pass 1, candidate 1: evidence and fix

- **Expected** (source: parallel-chain.md, the default parallel route for dependency-independent work on an
  Ask-Agent run): the plain request's step plan gives convert.py and stats.py separate independent steps.
- **Observed** (p1-temperature-plain-080452, Claude claude-sonnet-5-5, 1.19.0): `S1 convert.py and stats.py`
  (deps []), `S2 measure.py` (S1), `S3 tests` (S1, S2). A linear graph: nothing for the chain to run in parallel.
- **Why**: the step-plan done-criterion says "one step is fine" and the chain paragraph applies "for a plan with
  dependency-independent implementation steps", that is, only once the model has already split the work.
  Nothing asks it to split independent changes.
- **Triage**: the check is right (the accepted result); not environment; trigger clear in the packet text; the
  expectation is the purpose of Ask-Agent delegation, not a "how"; every typical request hits it; the inline
  "one step is fine" rule does not conflict (it only governs inline runs, which run steps in order). Decision:
  **product**.
- **Change**: the Ask-Agent step-plan duty (shiploop_prompts.py) asks for each change that does not need
  another to be its own step with deps [], joined by a later step; combine only when one needs the other. The
  inline swap text changes in lockstep, so inline packets are unchanged (delegation test asserts both).
- **Verified by**: `test_ask_agent_step_plan_splits_independent_changes_into_separate_steps`, the inline
  absence check (DELEGATED_ROUTE_TEXT), packet bounds 8/8; live rerun of temperature-plain after release.
