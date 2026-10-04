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
| Dispatcher fan-out and fan-in on dummy steps | Does a real host follow the dispatcher's calls, run A and B in parallel as native workers, and join J after both? | `python3 test/shiploop_e2e/fanout.py --host codex` | **PASS** on Claude, 2026-10-04 (1.17.0: A and B native, 29.9 s overlapped, J after both). Earlier **PASS** on Codex, 2026-09-27: A and B native, 29.3 s of their 30 s overlapped, J after both (`f810a78f`) |
| ShipLoop's own parallel chain | Does ShipLoop on the Ask-Agent route plan a step graph, bind a chain at `implement`, fan out and join? | `python3 test/shiploop_e2e/run.py --case temperature-report --host claude --seed-at step-plan` (starts at step-plan, ~20 min) | **PASS**, Claude Sonnet 5.5, 2026-10-03: graph S1, S2 then S3; S1 and S2 in flight together, S3 after both; 3/3 accepted, all native; every case check passes (22 min, $11.75). From intake (`--case temperature-report --host claude`, no seed): **PASS** the same day, same graph shape, S1 and S2 in flight together, every verdict passing; planning took minutes, not hours. Codex Luna xhigh seeded, 2026-10-03: stopped in the step-plan review after three 30-minute sessions; chain not reached (see LEARNINGS) |
| Does ShipLoop find parallel work when the request does not ask for it? | On an Ask-Agent run, a plain request with independent modules gets independent steps and the default parallel chain | `python3 test/shiploop_e2e/run.py --case temperature-plain --host claude --seed-at step-plan` | 1.19.0: linear plan, no chain. 1.19.1 (step-plan fix): independent steps, but still no chain: no graph was created and the model judged the work small. Chain policy for small work is an open owner decision (docs/orchestrator-improvement-passes.md, pass 1) |
| ShipLoop cases (smoke, web-service, CLI, stateful) | End-to-end delivery by case style | `--suite <name>` (see `test/shiploop_e2e/suites.json`) | See LEARNINGS |

Default host: Claude Sonnet 5.5 (`claude-sonnet-5-5`). Others: Grok `grok-4.7` medium;
Codex GPT-6 Luna (`gpt-6-luna`) at max (use `--effort xhigh` for ShipLoop runs). `--host`, `--model` and `--effort` switch them. A run
that stops while still active continues in place with `--resume-run <output>`,
on the same release.

## Next live checks (planned 2026-10-03)

Ordered by impact. Everything live so far is one passing run of one graph
shape (two parallel steps, then a join) on Claude, with nothing going wrong.

| # | Check | Why it matters | Pass when (script-graded) |
|---|---|---|---|
| 1 | Kill and resume during the chain | Surviving context loss is ShipLoop's purpose; a host dying mid-chain is only tested hermetically, and 30-minute kills happen in real use | the host is killed while a worker is in flight; a fresh session resumes; every step is accepted and integrated exactly once |
| 2 | Wider and deeper graphs | Only one shape has been planned and run by a real model | the model's graph has the expected width or depth; workers in flight reach the case's minimum; every step launches after its dependencies settle |
| 3 | Repeat runs | One pass does not show a reliable pass | the same verdicts hold across repeats |
| 4 | Other hosts | The chain is proven on Claude only | as 1-3, on Codex (after a runtime decision) and Grok (after credits) |
| 5 | Failure path live | Retry has now happened live (b1-word-report: two steps retried after test-oracle defects; c1 and c2: lost workers retried after a kill). Replan has never happened live | replan deferred: a forced replan is hard to make realistic |

Grouping:

- **A. Harness, built together** (one change, hermetic tests first): `--interrupt-at
  chain-launched` (1), per-case chain expectations and dependency-order grading,
  plus two shape cases (2). Both extend the same chain grader.
- **B. One live batch on Claude** (1-3 together, no engine changes mid-batch):
  kill-and-resume on temperature-report x2, the wide case x2, the deep case x2, one
  more seeded temperature-report. Each run is its own background task, three at a
  time, resumed after any 30-minute kill.
- **C. Fixes from B**: plan all fixes against the evidence, one release, one
  verification run.
- **B results (2026-10-03, 7 runs, see LEARNINGS "batch B"):** shapes pass (wide 2/2 with 4 in
  flight, deep 2/2 at depth 3, temperature 1/1; every run in dependency order, each step integrated
  once). Two ShipLoop defects: **F1** kill-and-resume 0/2, a fresh session cannot prove the dead
  host's workers stopped and pauses for the user; **F2** a retried step leaves a workspace that can
  never be closed, so chain finish is refused forever (1 of 1 runs with a retry). Group C fixes both.
- **C results (2026-10-04, skill-craft 1.17.0):** F1 and F2 fixed; kill-and-resume **PASS 2/2**
  (c1, c2): the fresh session retried the lost workers without a person, the replacements ran
  together, finish listed the kept attempts, and both runs returned their product. Recovery costs
  about 2.5x an uninterrupted run. Also: the report now lists what a run leaves in the repository,
  with removal commands (see LEARNINGS "what a run leaves in the repository").
- **D. Other hosts (4)**: after decisions on Codex's runtime and Grok credits.

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
- A lost worker is retried without proof that it stopped (owner decision, 2026-10-03).
  The model judges that its host session ended; the code stays safe in the attempt's
  isolated worktree, but a worker that outlived its session, or a step holding a port,
  database or deployment, could collide with its replacement. The guides tell such a
  step to wait for proof instead.

## Adding a test

- **Behavior that needs no model:** a suite under `test/`, registered in
  `test/suite_catalog.py`.
- **A dispatcher graph shape:** a JSON file in `test/orchestrator_scenarios/scenarios/`.
- **Live behavior:** a case in `test/shiploop_e2e/cases.json`, or a script-graded
  check like `fanout.py`. Record each run's result in `LEARNINGS.md`.
