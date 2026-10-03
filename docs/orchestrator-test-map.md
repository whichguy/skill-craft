# Orchestrator test map

Which test covers each part of the Plan Orchestrator, how to run it, and what
is left untested on purpose. The tests are the specification; this page only
points at them. Learnings from live runs go in
[`test/shiploop_e2e/LEARNINGS.md`](../test/shiploop_e2e/LEARNINGS.md), and
decisions go in commit messages. The design history is in
[`plan-orchestrator-validation-plan-2026-09-27.md`](plan-orchestrator-validation-plan-2026-09-27.md),
which this page supersedes.

## Hermetic: no model, runs in CI

CI's quick tier runs these on every push when their files change. The full
tier runs everything on release commits.

| Part | What is proven | Suites |
|---|---|---|
| Plan Dispatcher state and CLI | Readiness, claims, attempts, settlement, crash and lock recovery, owner takeover | `test/plan-dispatcher-state.test.js`, `-cli`, `-progress`, `-planning-context`, `-compound` |
| Dispatcher decisions | Verified BLOCKED goes to replanning; no retry cap; dead-writer lock recovery; lost state fails with the recovery named | `test/plan-dispatcher-decisions.test.js` |
| Exact calls | Every action carries its runnable call; capacity; planning-blocked steps are not offered for claim; cleaning up a rejected attempt is safe; writers wait for the lock | `test/plan-dispatcher-exact-calls.test.js` |
| Fan-out and fan-in on any graph | Linear, 16-way fan-out and join, shared joins, diamond of diamonds, deep blocking, replanning and faults, each run normally and with context loss. An independent oracle checks readiness, supplier evidence, blocking, refused callbacks, completion and capacity | `test/plan-dispatcher-scenarios.test.js` (`test/orchestrator_scenarios/`; `SCENARIO_SEEDS=1-40` for a wider sweep) |
| The tests catch broken code | 37 deliberate code breaks, each caught by the scenario its spec names (release tier only) | `test/plan-dispatcher-mutants.test.py` (specs in `test/orchestrator_scenarios/specs/`) |
| Chain bridge and Git | Per-step integration, competing and duplicate callbacks, crash recovery, conflicts, all against the live dispatcher | `test/shiploop-chain*.test.py` (7 suites), `test/integration-boundaries.test.py` |
| Backchain to dispatcher | An exported plan, with and without confirm methods, passes `validate-graph` | `test/export-execution-graph.test.js` in the Backchain repo |
| ShipLoop Improve routes | ShipLoop writes the contract and starts the child on both routes; restart; import | `test/shiploop-actual-improve-cli.test.py`, `test/shiploop-delegation.test.py`, `test/shiploop-navigator-v4.test.py` |
| E2E harness | Host interface (Grok, Claude, Codex), stream translation, `--resume-run`, fan-out grader | `test/shiploop-e2e.test.py` |

## Live: a real host; on demand; costs money

| Check | What it answers | Run | Latest result |
|---|---|---|---|
| Dispatcher fan-out and fan-in on dummy steps | Does a real host follow the dispatcher's calls, run A and B in parallel as native workers, and join J after both? | `python3 test/shiploop_e2e/fanout.py --host codex` | **PASS**, Codex, 2026-09-27: A and B native, 29.3 s of their 30 s overlapped, J after both (`f810a78f`) |
| ShipLoop's own parallel chain | Does ShipLoop on the Ask-Agent route plan a step graph, bind a chain at `implement`, fan out and join? | `python3 test/shiploop_e2e/run.py --case temperature-report --host claude --seed-at step-plan` (starts at step-plan, ~20 min) | **PASS**, Claude Sonnet 5.5, 2026-10-03: graph S1, S2 then S3; S1 and S2 in flight together, S3 after both; 3/3 accepted, all native; every case check passes (22 min, $11.75). A full run from intake is still to do |
| ShipLoop cases (smoke, web-service, CLI, stateful) | End-to-end delivery by case style | `--suite <name>` (see `test/shiploop_e2e/suites.json`) | See LEARNINGS |

Default host: Claude Sonnet 5.5 (`claude-sonnet-5-5`). Others: Grok `grok-4.7` medium;
Codex GPT-6 Luna (`gpt-6-luna`) at max (use `--effort xhigh` for ShipLoop runs). `--host`, `--model` and `--effort` switch them. A run
that stops while still active continues in place with `--resume-run <output>`,
on the same release.

## Known limits (acceptable by design)

ShipLoop and Plan Dispatcher guard against drift and context loss, not against
deliberate forgery. Each of the following can happen; none has been seen in a
real run. The detail is in the superseded plan's "Known limits" section.

- A hand-forged loop terminal packet or printed test summary passes the gates (X1, X7).
- Two simultaneous `complete` calls: one result is lost (X2).
- One-pass Improve exits: a rewritten result, or edits to ignored, `.shiploop/` or
  outside-workspace files, are not seen (X3, X4).
- About 18 judgment stages accept a bare `done` (X6).
- In-place runs commit the user's own edits in declared files (X9).
- Recovery details: the head does not name the implement step, and the integrate
  notice prints once (X12, X13). There are return-guard gaps (X14), and keepalive
  continues while a background task runs (X15).

## Adding a test

- **Behavior that needs no model:** a suite under `test/`, registered in
  `test/suite_catalog.py`.
- **A dispatcher graph shape:** a JSON file in `test/orchestrator_scenarios/scenarios/`.
- **Live behavior:** a case in `test/shiploop_e2e/cases.json`, or a script-graded
  check like `fanout.py`. Record each run's result in `LEARNINGS.md`.
