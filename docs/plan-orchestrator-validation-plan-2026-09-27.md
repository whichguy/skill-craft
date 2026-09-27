# Plan Orchestrator validation plan (2026-09-27)

Execute: ask

Status (2026-09-27):
- D2–D5 are released (plan-dispatcher 0.4.0).
- N1 (exact calls; X8) and N2 (T1 scenario harness) are implemented with gates
  1–4.
- D1 is reopened.
- Audit conditions: X8, X5, X10 and X11 fixed; the rest recorded as known
  limits.
- Phases 3–6 are not started.

Goal: prove that Plan Orchestrator runs a dependency graph correctly under
fan-out, fan-in, failure, recovery and context loss. Every stage should be
checked by a script, isolated from any model. ShipLoop's SDLC should compose
with it through a single tested contract rather than a second graph engine.

This plan starts from the 2026-09-26 audit
([[plan-orchestrator-audit-2026-09-26]], artifact "Plan Orchestrator Audit")
and a read-only coverage inventory taken on fc09ef3d.

## Evidence this plan starts from

- **Dispatcher, hermetic.** Coverage is already good:
  - diamonds, and a 13-node graph with a 7-way join (`plan-dispatcher-compound.test.js:334`);
  - seeded random layered graphs checked against an independent readiness model (`:563`);
  - processes killed with SIGKILL at named points (`plan-dispatcher-state.test.js:274-324`);
  - 12 pairs of concurrent reporters (`:648`);
  - stale-attempt refusal and owner takeover.
- **Chain/Git, hermetic.** Covers competing and duplicate callbacks
  (`shiploop-chain-async.test.py`), an advancing target, conflicts, and crash
  after merge. But every test uses one four-node graph (A, B, C←A, J←{B,C};
  `test/shiploop_chain_support.py:166`). The worker
  (`test/fixtures/chain-code-worker.py`) can only succeed, and only for those
  four IDs.
- **Live.** Only opt-in: `test/experiments/shiploop_chain/run_native.py` and the
  `shiploop_e2e` cases (hello, battleship, battleship-scoring). None of them is
  shaped like a graph.

### Gaps

1. **Blocking below direct children is never checked.** `refreshBlockedStates`
   (`state.js:820`) should block everything downstream. Tests only check a
   direct child. Nothing checks that steps come back after a retry.
2. **Graph validation has untested cases:** duplicate step IDs, duplicate
   deps, self-loops, dangerous-key IDs (`state.js:334-412`).
3. **No reusable scripted worker.** Failure, slowness and crashes are built
   ad hoc (`reject_contribution`, `managed_non_success_handoff`, `mock.patch`).
4. **The chain suite runs the pinned `test/fixtures/plan-dispatcher-v3/`.**
   Its hashes equal the live package today. A change to the live package isn't
   exercised by the chain suite until someone re-pins.
5. **Missing product behavior:**
   - a lock left by a crashed process is never recovered (`state.js:260`);
   - there is no cancel, abandon or retry limit;
   - FAILED and BLOCKED both settle as `rejected`, so "BLOCKED returns to
     planning" is only prose.
6. **No test in this repo checks Backchain export output against the
   dispatcher's `validate-graph`.**
7. **Two graph executors.** Under `delegation: inline`, the default, ShipLoop
   walks the steps itself and `chain bind` refuses. So dispatcher coverage says
   nothing about most real runs. This is the audit's top gap.

## Organizing decision: compose, don't merge

| Layer | Owns | Never owns |
|---|---|---|
| Backchain | Producing the graph: steps, `deps`, `ready`/`done` contracts | Running anything |
| Plan Dispatcher | Graph state: ready set, claims, attempts, receipts, settling, blocking, recovery | Git, SDLC stages, model launching |
| Chain bridge + Ask Agent | Workspaces, bringing each step's work back into the target, cleanup | Choosing the next step |
| ShipLoop | Outer SDLC: planning, the current action, Improve/test loops, delivery | Walking a graph |

The one seam between them is the **execution graph plus the attempt/receipt
contract** (`skills/plan-dispatcher/references/protocol.md`). Validation effort
goes where the graph logic lives, which is the dispatcher. Higher layers reuse
the same scenarios instead of inventing their own.

**Proposed integration (owner decision D1):** inline ShipLoop runs go through
the dispatcher using its existing `main-context` executor.

- `start` already moves main-context work straight to `running` with no native
  launch.
- Inline and parallel runs would then share one graph engine.
- Every dispatcher scenario would cover ShipLoop's default route.

This reopens the 09-26 KISS deferral of work-item `depends_on` and the
chain/dispatcher fixes.

## Test development method: spec, spec review, adversarial pass

Every workstream below builds its tests through the same four gates, in order.
A gate is passed only when the stated script check passes. A model saying the
gate is done is not enough ([[test-pass-is-the-evidence]]).

### Gate 1: test spec

Before writing test code, write the spec in
`test/orchestrator_scenarios/specs/<workstream>.md`. It lists:

- **Intent under test:** the contract clauses being tested, cited by
  file:line in `protocol.md`, the relevant `SKILL.md` or a reference file.
- **Scenarios:** graph, per-step worker outcomes, interleaving, faults.
- **Invariants and oracle:** what must hold, and the independent reference
  model that decides it. The oracle must not import the code under test.
- **Out of scope:** what is excluded, and why.

### Gate 2: spec review

Review the spec against the contract, not against the current code. Answer
each question in the spec's `## Review` section:

1. Does every contract clause in scope have at least one scenario that could
   violate it?
2. Is every invariant stated as an observable outcome (state, target Git
   ancestry, receipt bytes, exit code), not as "the code calls X"?
3. Is the oracle independent? Could a bug shared by the oracle and the
   implementation make both agree?
4. Does each scenario name its failure signal? A scenario that can't fail is
   removed.
5. Is anything tested that isn't in the contract? Either cite the clause or
   classify it as an unknown in Gate 3.

Exit check: `spec_lint.py` confirms every scenario ID has an invariant and a
contract citation, and that the Review section answers all five questions.

### Gate 3: adversarial pass

Deliberately look for conditions the spec didn't imagine. There are three
classes, and each finding is recorded in the spec's `## Adversarial` table with
its class and the test that covers it.

**A. Contrary changes (mutants).** A plausible code change that breaks the
intent while looking reasonable. Each one becomes a named mutation applied by
script to a temporary copy of the package. At least one test must **fail**
against every mutant. Starter mutants for the dispatcher:

- `dependenciesAccepted` accepts when *any* dependency is accepted, or also
  accepts `claimed`/`running`;
- `refreshBlockedStates` stops after one level, or never unblocks after a retry;
- `currentAttempt` stops refusing stale attempts; `settle` skips the receipt
  hash check;
- `report` overwrites an existing receipt; `retry` drops `confirmed_stopped`;
- `claim` with explicit IDs claims the valid subset instead of refusing all;
- the fan-in packet omits one supplier's evidence;
- `assertOwner` ignores `generation`; the `withLock` exclusive create becomes a
  plain write;
- `validateGraph` loses cycle detection or the duplicate-ID check.

Chain/Git mutants:

- prepare against a stale HEAD without re-preparing;
- merge a rejected attempt;
- clean up before refill, or clean up a worktree that wasn't accepted;
- `finish` skips the ancestry audit;
- a join's base misses a supplier.

**B. Unknowns.** Behavior the contract doesn't specify. Starter list:

- a crashed process's leftover lock;
- a step that fails permanently: stall, abandon or retry limit;
- BLOCKED vs FAILED routing;
- a lost inbox or artifacts directory mid-run;
- a graph with several disconnected components where one fails;
- a receipt arriving for a step whose dependency was later retried;
- two joins that share suppliers and race to merge into the target;
- a worker that edits files outside its step's scope;
- a `done` string whose `Confirm by:` check cannot run.

Each unknown is handled in one of two ways:

- **Decided:** the owner decides, the contract text is updated, and a normal
  test is added.
- **Pinned:** a characterization test records today's behavior and is tagged
  `unknown:<id>` with a link to the pending decision. A pinned test fails
  loudly if the behavior changes, so it can't drift silently.

**C. Hostile inputs.** Inputs a correct caller wouldn't send but a confused
model might:

- a forged or reordered receipt;
- a report for an attempt that belongs to another step;
- a symlinked state file or inbox entry;
- `__proto__`/`constructor` IDs; very large or deep graphs;
- a callback run from the wrong working directory;
- replayed `next_argv` from an earlier revision;
- JSON with extra fields, and concurrent identical requests.

### Gate 4: kill check

This gate is scripted: `mutate.py` applies each class A mutant in a temporary
copy, runs the workstream's tests, and requires a failure for every mutant. A
mutant that survives means a test is missing or too weak. Add or strengthen a
test and rerun, with no iteration cap ([[shiploop-loops-unbounded]]). Also:

- Classes B and C pass when their tagged tests exist and are green.
- The workstream is done when all mutants are killed and two consecutive
  adversarial reviews add no new material finding.

## Scenario harness (shared by every tier)

Everything lives in `test/orchestrator_scenarios/`:

- `scenarios/*.json` holds one scenario per file:
  - `graph`;
  - `workers`: per-step outcome sequence, from `succeed`, `fail`, `blocked`,
    `slow(until:<step>)`, `crash_before_report`, `report_twice`,
    `report_stale_attempt`, `conflict_with:<step>`, `edit_out_of_scope`;
  - `schedule`: fixed order, or a seed;
  - `faults`: `kill_parent_after_call:N`, `remove_lock:false`, `delete:inbox`;
  - `expect`: invariant IDs plus any final-state assertions.
- `worker.py` is the scripted worker. It plays the outcomes. At tier T2 it
  writes and commits real code, generalizing `chain-code-worker.py` beyond
  A/B/C/J.
- `driver.py` is the **amnesiac driver**. It keeps nothing between calls. It
  only runs the exact `next_argv` and argv each response returns, and the
  worker only reads its packet. If the driver can't finish a correct scenario,
  navigation is leaking to the model. This tests the premise that context can
  be lost between any two calls ([[shiploop-purpose]]) and directly measures
  the audit's finding that 18 of 42 calls are composed by the model. Where a
  response gives no executable argv, the driver fails with the call site named.
- `oracle.py` is an independent reference model plus the invariant checker:
  - I1: never claim before every dependency is accepted.
  - I2: every join packet holds evidence from every accepted supplier.
  - I3: blocking reaches all downstream steps, and a retry undoes it.
  - I4: stale or duplicate callbacks change nothing: state bytes, target HEAD,
    ledger.
  - I5: the run is complete if and only if every step is accepted.
  - I6 (Git): every accepted step's commits are ancestors of the final HEAD, and
    rejected worktrees are kept.
  - I7: recovery after a kill at any call boundary reaches the same final state
    as an uninterrupted run.
- `mutate.py` is the Gate 4 runner. `spec_lint.py` is the Gate 2 check.

**Starter catalog:**

- long linear chain (12 steps);
- wide 16-way fan-out and 16-way join;
- several joins sharing suppliers;
- a diamond of diamonds;
- disconnected components, one of which fails;
- blocking three levels deep, then retry;
- a burst of completions in reverse claim order;
- two joins racing to merge into the target;
- conflicting edits at a fan-in;
- the parent killed after each call in turn;
- a leftover lock.

A T1 seeded sweep generates random graphs. Any failing seed is frozen into
`scenarios/`.

## Tiers

| Tier | What runs | Target | CI |
|---|---|---|---|
| T1 dispatcher | Scenarios, driver, oracle, mutants | The **live** `skills/plan-dispatcher` | Quick tier |
| T2 chain/Git | Same scenarios; the worker commits code in worktrees managed by Ask Agent | Live dispatcher and live chain bridge (closes gap 4 on its own; the pinned-copy suite stays as the compatibility check it is) | Full tier |
| T3 ShipLoop composition | A ShipLoop run whose `implement` action is bound to a scenario graph, driven by `driver.py`, with kills between calls | ShipLoop CLI | Full tier |
| T4 live | 2–3 graph-shaped `shiploop_e2e` cases, e.g. two independent modules plus an integration step | Real host | Opt-in only |

Register every new top-level suite in `test/suite_catalog.py`
([[register-new-test-suites]]). Hermes is out of scope ([[no-hermes-test-suite]]).

## Phases

1. **T1 harness and dispatcher tests.** Build the worker, driver, oracle,
   `mutate.py` and `spec_lint.py`. Run gates 1–4 for the dispatcher, including
   gaps 1 and 2. Exit when T1 is green in the quick tier, every dispatcher
   mutant is killed, and each unknown is either decided or pinned.
2. **Owner decisions** raised by phase 1 (see below). Each decision updates
   the contract text, turns its pinned test into a normal one, and adds the
   product change with its change note.
3. **Backchain conformance.** Exported plans pass `validate-graph`, and
   `Confirm by:` done-strings render as `skills/backchain/SKILL.md:268-271`
   describes. This needs a fixture plan set in this repo. Gates 1–4 apply.
4. **T2 chain/Git.** Same scenarios with real commits; wide fan-out and
   conflicting fan-in. Gates 1–4 with the chain mutants.
5. **D1 unification** (if approved): inline `implement` drives the dispatcher
   through the `main-context` executor. Then T3, with gates 1–4 applied to
   ShipLoop's composition.
6. **T4 live cases**, recorded with learnings per
   [[e2e-run-commit-learnings]].

Phases 1, 3 and 4 do not depend on D1.

## Owner decisions (decided 2026-09-27)

- **D2. Leftover lock: implemented.**
  - The lock records `{pid, host}`. The next writer removes a lock whose
    holder is dead on the same host.
  - Removal runs under `.dispatcher.lock.recover` and only when the lock's
    bytes are unchanged since inspection.
  - Every other holder is refused with `ELOCKED`, and the message names what
    to do. There is no lease.
- **D3. Permanent failure: implemented.**
  - No retry limit and no `abandon` verb.
  - `next` returns `retry` actions carrying `attempts`, `reason` and an exact
    `call`.
  - Downstream blocking is transitive, and it is now tested three levels deep.
- **D4. Verified BLOCKED goes to replanning: implemented.**
  - The parent settles with `verification.disposition: "replan"` (only with
    `passed: false`).
  - From then on:
    - `claim`, a fresh `start` and a retry of that attempt fail with `EREPLAN`;
    - `ready` is empty;
    - `next` returns `replan`/`release` actions and `next.replan`
      (steps, accepted, unfinished);
    - work already in flight can still settle.
  - Once nothing is in flight, the run reports that it cannot complete.
  - See `protocol.md` "Replanning".
- **D5. Lost state: implemented.** A lost state file or settled receipt fails
  closed with `ESTATELOST`, and the message names the recovery: start a new
  run and leave out integrated steps.
- **D1. Inline ShipLoop through the dispatcher: reopened.** The premise was
  out of date.
  - The KISS follow-up of 09-26 (32640ce..ef019f1) already has the script
    issue one inline `implement` action per planned step, counted from
    history (`implement_progress`). So the model no longer walks the steps.
  - Inline steps are a linear list with no `depends_on`. Routing them through
    the dispatcher would unify the engine and give inline runs D3/D4
    semantics, but it would reverse a deliberate simplification.
  - The audit session's experiments (below) also show that the dispatcher
    returns an exact call for only a few actions. Exact argv for every action
    is therefore a prerequisite for D1 and for `driver.py`.
  - D1 waits for that work and a fresh owner decision.

Not yet done for D4: the ShipLoop chain passes `verification` through with
exact keys, and its tests use the pinned dispatcher fixture
(`test/fixtures/plan-dispatcher-v3/`). Chain handling of `replan` needs that
fixture re-pinned to the live package (gap 4).

## Go-forward plan (2026-09-27, after the KISS triage)

How far each layer can be tested today:

| Layer | Tests without a model | Live | Gap |
|---|---|---|---|
| Plan Dispatcher | Strong: 8 suites, T1 scenarios with context loss, 37 mutants | Not needed | None worth chasing |
| Chain bridge + Ask Agent | About 30 real-Git lifecycle tests, one 4-node graph, pinned to a frozen Plan Dispatcher 0.3.0 | Opt-in Grok pilot (09-20) | Unknown whether it works with dispatcher 0.5.0 |
| ShipLoop inline route | Fast in-process walks; refusal and recovery invariants | `shiploop_e2e` cases | Not graph-shaped, by design |
| Backchain export | None in this repo | None | Export never checked against `validate-graph` |
| End to end, real fan-out/fan-in | None | Only the 09-20 pilot | Never run through the current release |

Steps, smallest first:

1. **Chain against the live dispatcher.** Re-pin
   `test/fixtures/plan-dispatcher-v3/` to the current package and run the chain
   suites; fix the chain if they break. Add `replan` pass-through only if it is
   trivial.
2. **Backchain conformance.** One test: a sample Backchain export passes
   `validate-graph`.
3. **One live, graph-shaped run.** Add a `shiploop_e2e` case with two
   independent modules and an integration step on the Ask-Agent parallel
   route. Run it once on Grok (opt-in; recent runs cost about $25 and 60–90
   minutes) and commit its learnings.
4. **D1.** Recommended: close as not doing. The inline route is simple and
   works; routing it through the dispatcher pays off only if parallel inline
   steps are wanted. Awaiting the owner's confirmation.
5. **Stop.** Port the harness to the chain (T2) only if step 1 or 3 shows a
   problem. Leave the gate machinery as is; it runs only on release commits.

## Next steps (2026-09-27, executed)

1. **N1: exact calls (audit condition 6, X8). Done.**
   - Every action carries a `call` (argv plus input with placeholders). The
     settle call pre-fills the receipt digest, and claim and start responses
     carry the follow-up calls.
   - A complete run returns no `next_argv`.
   - Optional `capacity` at `init`; `ECAPACITY` beyond it.
   - Planning-blocked steps are not offered for claim, and a claim for one is
     refused.
   - A rejected attempt's workspace and evidence may be cleaned up.
   - Concurrent writers wait up to 3 s for the lock.
   - Tests: spec `test/orchestrator_scenarios/specs/dispatcher-exact-calls.md`
     and suite `test/plan-dispatcher-exact-calls.test.js` (E1–E7). Every
     scenario failed on the pre-change package; 10 of 10 mutants are killed.
2. **N2: T1 harness. Done.** The pieces live in
   `test/orchestrator_scenarios/`:
   - `harness.js`: fake host, scripted worker, memoryless driver and an
     independent oracle checking I1–I5, I7 and I8;
   - `scenarios/*.json`: C1–C8;
   - a seeded sweep (R1–R4 in CI; `SCENARIO_SEEDS=1-40` passed 48 of 48).

   The driver only runs returned calls. In context-loss mode it discards
   every response and also loses context between a start grant and the
   launch or work that grant authorizes, which exercises reconcile, resume
   and retry after a launch that never happened. Suite:
   `test/plan-dispatcher-scenarios.test.js` (about 50 s in the quick tier);
   10 of 10 mutants killed.
3. **Gates in CI.** `test/plan-dispatcher-mutants.test.py` runs `spec_lint.py`
   on every spec and `mutate.py` on every mutants file. It is heavy, so it runs
   in the full tier only.
4. **Next.**
   - Re-pin the chain's dispatcher fixture, then T2 (chain/Git with the same
     scenarios, and chain handling of `replan` and calls).
   - Decide D1 again; its prerequisite, exact calls, now exists.
   - The remaining audit conditions below.

## Audit conditions X1–X15 (triaged 2026-09-27 under KISS/YAGNI)

The owner's rule: fix what breaks or misleads a normal run. Adversarial
constructions and gaps nobody has hit are acceptable by design; record them
here and revisit only when a real run shows them.

| Item | Condition | Outcome |
|---|---|---|
| 6 | X8: dispatcher exact calls and dead ends | **Done** in 1.9.0 (N1) |
| 4 | X5: lint refused step S1 for a finding step S2 resolves | **Fixed.** Earlier implement steps report without auto-fix; the item's last step gates |
| 8 | X10: after context loss mid-loop, nothing said to continue from the receipt | **Fixed.** Once the receipt exists, the loop packet says not to start again and to run the receipt's `next_argv` |
| 9 | X11: paused, halted and blocked packets printed whole past Grok's ~20 KB cut | **Fixed.** Over 16,000 characters they print a pointer to the full packet file and what fits |
| 1 | X1: a hand-forged terminal packet passes | Known limit |
| 2 | X2: two simultaneous `complete` calls | Known limit |
| 3 | X3: a revised result closes on one pass; X4: fingerprint blind spots | Known limit (X4 decided: no change) |
| 5 | X6: bare `done` at judgment stages; X7: printed test summaries | Known limit (X7 decided: document) |
| 7 | X9: in-place auto-commit includes the user's edits in declared files | Known limit (decided: document) |
| 8 | X12, X13: step name not in the head; integrate notice not repeated | Known limit (runs did the right work) |
| 10 | X14, X15: return-guard gaps; keepalive while a background task runs | Known limit (no harm observed) |
| 11 | Pin H1–H5 | Not needed; existing suites cover the invariants that matter |

### Known limits (acceptable by design)

ShipLoop and Plan Dispatcher trust the host model to follow the packets. They
guard against drift and context loss, not against deliberate forgery. Each of
these can happen, and none has been seen in a real run:

- **Forged evidence.** A model that writes a loop's terminal packet by hand
  (X1), or prints a fake test summary (X7), can pass the loop and test gates.
- **Simultaneous callbacks.** One parent conversation drives a run. Two
  `complete` calls started together can both exit 0, and one result is lost
  (X2). Calls even 0.6 s apart are refused.
- **One-pass exits.** An Improve review that rewrites a stage result can
  close on one unchanged pass (X3). Edits to git-ignored files, files under
  `.shiploop/`, or files outside the workspace are invisible to that exit (X4).
- **Judgment stages.** About 18 stages accept `done` with no script check
  (X6); their output is judged by later stages and reviews.
- **In-place runs.** Auto-commit on an in-place run commits everything in the
  item's declared files, including the user's own uncommitted edits there
  (X9). The default workspace route is protected.
- **Recovery details.** The printed head does not name the implement step
  (X12). Integrate's "not committed" notice prints once (X13).
- **Return guard and keepalive.** Git-ignored files are outside the return
  fingerprint, and a refusal does not name the drifted path (X14). Keepalive
  keeps continuing while a background task runs (X15).

## Audit-session experiment findings (2026-09-27, snapshot b3e466c7)

These came from the parallel "Plan orchestrator audit and improvements"
session, using scripted probes with no repository edits.

Dispatcher findings:
- Lock and BLOCKED dead ends reproduced; now addressed by D2 and D4.
- Still open:
  - `complete: true` still returns `next_argv`;
  - in a 3-step walk, 16 of 19 calls were composed by the caller;
  - deleting a rejected attempt's workspace or ready evidence bricks `next`,
    `packet`, `retry` and `takeover`;
  - 20 concurrent claims gave 16 `ELOCKED` with no retry;
  - there is no capacity input, and one claim took all 10 ready steps;
  - a planning-blocked step is listed as ready, then `start` refuses it.

A second workstream, **ShipLoop SDLC gates**, uses the same four gates:
- The Until Loop one-unchanged-pass exit ignores git-ignored files, files
  under `.shiploop/`, and changes outside the workspace.
- The integrate auto-commit on in-place runs can commit the user's own edits
  at declared paths.
- The packet head does not name the implement step; 58 of 179 E2E actions
  never read the packet file.
- Keepalive continues without bound while a background task runs.

Invariants that already hold on ShipLoop (I4, I7):
- 164 refusal probes left `state.md` byte-identical;
- `next` was idempotent at every one of 41 actions;
- recovery matched after every boundary;
- a full in-process walk takes about 1 s, which fits the quick tier.

## Done means

- T1–T3 are green in CI at their tiers.
- `mutate.py` reports zero surviving mutants for the dispatcher and chain.
- Every Gate 3 finding maps to a test (decided or pinned).
- `driver.py` completes every correct scenario using only the argv it was
  given.
- Evidence (suite summaries and mutant reports) is pasted into the phase
  commits.
