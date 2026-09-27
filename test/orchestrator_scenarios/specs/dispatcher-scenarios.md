# Test spec: T1 dispatcher scenarios

Suite: `test/plan-dispatcher-scenarios.test.js`. Mutants:
`test/orchestrator_scenarios/mutants/dispatcher-scenarios.json`.

This is phase 1 / next step N2 of
`docs/plan-orchestrator-validation-plan-2026-09-27.md`: the T1 harness
(`harness.js`: fake host, scripted worker, memoryless driver, oracle) and the
scenario catalog (`scenarios/`, format in `scenarios/README.md`).

## Intent under test

The dispatcher runs any dependency graph correctly when every navigation
decision comes from its own responses, and when context is lost between any
two calls. Anchors:

- `references/protocol.md`:
  - "Graph";
  - "Categorical progress";
  - "Replanning";
  - "Recovery and limits";
  - every action carrying its exact `call`.
- [[shiploop-purpose]]: the script navigates; the model does one step;
  context can be lost at any time.

The driver has no graph logic. It picks the first actionable entry in
`actions` and runs its `call`, filling only placeholders, from its simulated
work. The one exception: it trims a claim to the steps it can run. The
scenarios check the following invariants:

- **I1:** a claim names only steps whose dependencies were all accepted.
- **I2:** a packet carries evidence from exactly its step's suppliers, with
  the receipts that were accepted.
- **I3:** the blocked steps are exactly those below a rejected step, and a
  retry clears them.
- **I4:** a refused duplicate or stale callback leaves the state file
  byte-identical.
- **I5:** `complete` is reported exactly when the oracle saw every step
  accepted, and a replan run ends with its replan steps.
- **I7:** a run with context loss accepts the same steps, with the same
  replan outcome, as the normal run.
- **I8:** in-flight work never exceeds the run's capacity.
- Each settlement outcome equals the independent verifier's verdict.
- The driver never stalls: the same actions repeated 25 times fails.

Context loss means two things. The driver discards every response after
acting and restarts from `dispatch.js next RUN`. It also loses context (seeded,
about 35%) between a start grant and the launch or work it authorizes. That
forces `reconcile` (the host has the task), a never-launched retry (the host
does not), and `resume` (main-context).

## Scenarios

| ID | Scenario | Failure signal |
|---|---|---|
| C1 | Linear chain of 12 | An invariant fails, the driver stalls, or the run doesn't complete |
| C2 | Root → 16-way fan-out → 16-way join; capacity 4; LIFO completions | I1, I2 or I8 fails, or the run doesn't complete |
| C3 | Three joins sharing three suppliers, then a top join; capacity 3; seeded order | I1 or I2 fails |
| C4 | Diamond of diamonds, main-context executor, capacity 1 | Resume after context loss fails, or an invariant fails |
| C5 | A→B→C→D→E plus X; B fails, then false success, then succeeds; X is BLOCKED (retried); late reports from retired B attempts | I3 or I4 fails; fewer than 2 refusals; a verdict mismatch |
| C6 | B settled `replan` while P/Q/R proceed; capacity 2 | The run completes; `replan` ≠ [B]; new work after the replan |
| C7 | A's report is duplicated; B's launch response is lost; LIFO | The duplicate is accepted or changes state; the lost launch is not reconciled |
| C8 | Disconnected components; X fails twice | The run doesn't complete, or an invariant fails |
| R1 | Seeded sweep R1–R4: layered random graphs (3–4 layers, width 2–4, then a join), mixed failures and false successes, random capacity and executor. `SCENARIO_SEEDS=1-40` widens the sweep. | Any invariant fails |

## Invariants and oracle

`Oracle` in `harness.js` never reads dispatcher state or imports its code. It
builds its own step statuses only from the claims it saw the driver make and
the settlement outcomes returned. It checks I1–I3 and I8 on every step, I4
around each injected refusal, and I5 at the end. I7 compares the two runs.
The verifier decides pass or fail from the artifact's value against
`expectedValue(step)`, never from the worker's reported status.

## Out of scope

- Git worktrees and integration (T2, chain).
- Real host timing. The fake host completes tasks one at a time, in schedule
  order.
- Planning-context drift. That is covered by E6 in
  `dispatcher-exact-calls.md`.

## Review

1. **Is every clause violable?** Yes:
   - readiness → C1, C3 (I1);
   - fan-in evidence → C2, C3 (I2);
   - transitive blocking and retry → C5 (I3);
   - stale and duplicate callbacks → C5, C7 (I4);
   - completion → C1 (I5);
   - replanning → C6;
   - recovery → C4, C7 and the context-loss runs (I7);
   - capacity → C2 (I8).
2. **Observable outcomes?** Yes: claim inputs, packet dependencies,
   settlement outcomes, `progress.blocked`, state file bytes, `complete`,
   and `replan`.
3. **Independent oracle?** It keeps its own model from observed calls and
   uses literal expectations from the scenario files. A shared bug would need
   the oracle's small fixed-point blocking rule to match a wrong engine rule.
   That is checked by the `never-unblock` mutant.
4. **Can every scenario fail?** Every row's failure signal is exercised by at
   least one mutant or fault. The 40-seed sweep passed (48 of 48) on
   2026-09-27.
5. **Anything outside the contract?** The driver's claim trimming is the
   caller policy that `protocol.md` explicitly permits.

## Adversarial

| ID | Class | Condition | Covered by |
|---|---|---|---|
| M1 | contrary | A step counts as ready when any one dependency is accepted | mutant `deps-any` (C3) |
| M2 | contrary | A join's packet drops a supplier | mutant `packet-drops-supplier` (C3) |
| M3 | contrary | Settle trusts the worker's SUCCEEDED | mutant `settle-ignores-verdict` (C5) |
| M4 | contrary | A retired attempt can still report | mutant `stale-accepted` (C5) |
| M5 | contrary | A blocked step is never unblocked | mutant `never-unblock` (C5) |
| M6 | contrary | The run is reported complete one step early | mutant `complete-early` (C1) |
| M7 | contrary | Reconcile gives no launched call | mutant `reconcile-no-call` (C7) |
| M8 | contrary | Resume gives no report call | mutant `resume-no-call` (C4) |
| M9 | contrary | The claim offer exceeds free capacity | mutant `offer-over-capacity` (C2) |
| M10 | contrary | New work is offered after a replan | mutant `join-skips-replan-stop` (C6) |
| H1 | hostile | A duplicate report with a different status | C7 |
| H2 | hostile | A late report from a retired attempt | C5 |
| U1 | unknown → decided | Context lost between the start grant and the launch, with no host task | C1–C8 context-loss runs: retired with the reconcile retry call; the next attempt proceeds; outcomes count only reported attempts |
| U2 | unknown → decided | Context lost after a main-context start | C4: `resume` returns the report call |
