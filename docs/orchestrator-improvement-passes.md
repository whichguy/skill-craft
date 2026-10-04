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

### Pass 1 results (released as skill-craft 1.19.1, deployed to Claude, Codex and Grok)

| Run (Claude claude-sonnet-5-5, temperature-plain, seeded) | Step plan | Chain | Checks | Time, cost |
|---|---|---|---|---|
| p1-temperature-plain-080452 (1.19.0, before) | `S1 convert+stats`, `S2 measure (S1)`, `S3 tests` — linear | none bound | 6/6 | 19.1 min, $11.84 |
| p1v-temperature-plain-1df460 (1.19.1, after) | `S1 convert []`, `S2 stats []`, `S3 measure (S1, S2)` — independent | none bound | 1/6 (modules placed in `temperature/`) | 17.1 min, $6.53 |

- The step-plan fix works: the model now splits independent changes.
- The 1.18.0 leftovers section rendered in a live report.html for the first time (p1), and both runs wrote
  `mismatch.md` for their failing verdicts, as designed.
- **Check placement (trivial, test fix):** the plain prompt had dropped the framing that kept modules at the
  root, and the request never said where `measure.py` lives, so the checks assumed what the request did not
  state (triage 1: the check was wrong). The prompt now says "as modules in the repository root, run as
  `python3 measure.py`"; it adds no hint of parallel work.

### Pass 1, owner decision: when should an Ask-Agent run use the chain?

- **Expected** (parallel-chain.md): independent steps on an Ask-Agent run use the parallel chain by default.
- **Observed** (p1v): independent steps, yet no chain. The model's recorded reason: "no reviewed dispatcher graph
  was created at step-plan, and the change is three small files". The step-plan duty asks for the graph
  ("create and review its initial steps and graph here"), but it was not created, nothing checked it, and
  implement took the one-writer route instead of the guide's late-creation route. "Small" is not a blocker the
  guide allows.
- **Cost evidence:** for this small request, one writer took 17.1-19.1 min at $6.53-11.84; the chain runs of
  the same case took 16-22 min at $8.60-11.20. No time gained at this size.
- **Why it is the owner's call** (triage 6): two deliberate intents conflict, the guide's "parallel by
  default" (and the user's opt-in to Ask-Agent delegation) against doing small work the cheaper way (the
  standing rule: near-identical quality, fewer tokens wins). The fixes are policy choices with cost effects,
  and two of them touch the Backchain and planning-prompt area another session is changing.
- **Options:** (A) a script check at step-plan: independent steps on an Ask-Agent run need a graph locator or
  an explicit "no parallel chain" with its reason; (B) the script derives the execution graph from the step
  list, so no separate model-written graph is needed; (C) allow a recorded size judgment ("worker setup
  outweighs parallel running"), making the model's choice explicit instead of a silent deviation.
- **Until decided:** temperature-plain keeps its must-level chain expectation, so it reports this open question
  as a failing verdict rather than hiding it.

## Pass 2 — 2026-10-04

Base: main after the 1.19.1 release (CI green for 3115b4ea).

| # | Candidate | Evidence | Class | Action |
|---|---|---|---|---|
| 1 | The chain guide's `finish` row says finish needs "completed cleanup"; its worked example says finish "confirms every owned worker worktree was removed" | Both false since 0.49.0 when an attempt was retried or lost (kept, listed under `retained_superseded`); a model reading them in a retry run could remove a kept workspace directly (forbidden) or stop again | material (wrong guidance in a normal run) | Both lines now say accepted workers' worktrees are removed and superseded ones are kept and listed; change note |
| 2 | `mismatch.md` records a failing check only as "non-zero exit" | p1v: the cause (`No module named 'convert'`) was in the captured output but not the record | trivial (no verdict changes; diagnosis convenience) | The record shows the exit code and the output's last line; test |
| 3 | Test map and ledger lack the plain case | pass 1 | trivial | Row in each |
| 4 | Both pass-1 runs, my areas | 0 ShipLoop failures, 0 glue, 0 questions, all script verifications passed | none | — |
| 5 | Chain policy for small work | pass 1 | out of scope (owner decision, options A-C) | — |

Pass 2 is not clean: it found one material item.
