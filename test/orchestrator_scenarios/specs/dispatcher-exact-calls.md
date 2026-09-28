# Test spec: dispatcher exact calls and dead ends (X8)

Suite: `test/plan-dispatcher-exact-calls.test.js`. Mutants:
`test/orchestrator_scenarios/mutants/dispatcher-exact-calls.json`.

This covers condition 6 of
`docs/experiments/orchestrator-isolated-experiments-20260927/README.md`
(X8, probes `scripts/dispatcher/p2…p6`) and next step N1 of
`docs/plan-orchestrator-validation-plan-2026-09-27.md`.

## Admission

- **Failing scenarios first.** E1–E7 were written and run against the
  pre-change package (`origin/main` `85b73a31`), and every one failed there.
  E4 failed with 15 of 20 concurrent claims refused `ELOCKED`. E7 failed only
  because the claim action had no call. Each failing scenario reproduces its
  probe:
  - E1 is `p3`: in a 3-step walk, 16 of 19 calls were composed by the caller.
  - E2 is `p2`: `complete:true` still returned `next_argv`.
  - E3 is `p4` scenario 1: deleting a rejected attempt's workspace and ready
    evidence bricks the run.
  - E4 is `p5`: concurrent writers raise `ELOCKED` with no wait.
  - E5 is `p6` 6b: there is no capacity input.
  - E6 is `p6` 6c: a planning-blocked step is still offered for claim.
- **Anchors:** the owning spec's clauses S-4 (steps are measurable by a
  script) and S-6 (nothing is lost between stages; context loss), plus the
  premise in [[shiploop-purpose]]: the script names the exact next call.
- **Non-regression.** The existing dispatcher suites keep passing. Their only
  intended change is the E2 contract, where a completed run returns no
  `next_argv`; `cli` and `progress` are updated to that. Runs without
  `capacity` claim as before. `ready` stays dependency-derived, as
  documented, and only the claim action and `claim` exclude planning-blocked
  steps.

## Intent under test

- **Exact calls.** Every action in `next`, plus the follow-up in `claim` and
  `start` responses, carries a `call` (or `calls`). Running it with only its
  placeholders filled performs that action. A caller never composes argv or
  picks an operation. The settle call pre-fills the receipt digest.
- **Completion.** A response with `complete: true` carries no `next_argv`.
- **Rejected cleanup.** A rejected attempt's workspace and ready evidence may be
  deleted. `next`, `retry` and `takeover` still work, and the step can run
  again with a fresh context.
- **Contention.** Concurrent writers against a live holder wait briefly instead
  of failing at once.
- **Capacity.** `init` accepts an optional positive integer `capacity`.
  - The claim action offers at most the free slots (capacity minus claimed,
    launching and running attempts), and no claim action is offered when
    none are free.
  - `claim` beyond capacity fails with `ECAPACITY`.
  - Without `capacity`, claiming is unlimited.
- **Planning-blocked steps.** They are left out of the claim action, and
  `claim` refuses them with `EPLANNING_CONTEXT`.

## Scenarios

| ID | Scenario | Failure signal |
|---|---|---|
| E1 | 3-step chain driven only by the returned calls, with placeholders filled | An action without a call, a composed argv, the settle receipt digest not pre-filled, or the run not completing |
| E2 | Final settle, and `next` on a complete run | `next_argv` present when `complete: true` |
| E3 | A rejected, then delete its workspace and ready evidence; then next, takeover, retry and rerun | Any of those fails, or A cannot be accepted on a fresh attempt |
| E4 | 20 ready steps claimed by 20 concurrent processes | Any `ELOCKED`, or claimed count ≠ 20 |
| E5 | `capacity: 3`, 10 ready steps | Claim offers ≠ 3; a 4th claim is accepted; offers not refilled after a settle; invalid capacity accepted |
| E6 | Planning context of B drifts | B offered in the claim action, or `claim` of B accepted |
| E7 | Run with no capacity, 10 ready | Claim offers fewer than 10, or claiming all 10 is refused |

## Invariants and oracle

Expected values are written as literal step lists per scenario. The driver
in E1 keeps no state between calls beyond the last response. It fills
placeholders from its own simulated work: workspace, handle, the artifact
digest it computed, and its own verification. It never reads dispatcher
internals.

## Out of scope

- Chain use of these calls (T2). Chain tests pin a copy of the dispatcher.
- Deleting an accepted attempt's evidence. That stays fail-closed by design
  ("keep original evidence bytes available").

## Review

1. **Is every clause violable?** Yes:
   - exact calls → E1;
   - completion → E2;
   - cleanup → E3;
   - contention → E4;
   - capacity → E5 and E7;
   - planning-blocked steps → E6.
2. **Observable outcomes?** Yes: exit codes, error codes, `actions[].call`
   contents, `next_argv` presence, claimed counts, and final acceptance.
3. **Independent oracle?** Yes: literal expectations. E1's driver learns
   argv only from responses.
4. **Can every scenario fail?** Each has a failure signal, and every one
   failed on the old package.
5. **Anything outside the contract?** No. E7 pins that runs without
   `capacity` are unchanged.

## Adversarial

| ID | Class | Condition | Covered by |
|---|---|---|---|
| M1 | contrary | The claim action has no call | mutant `claim-no-call` (E1) |
| M2 | contrary | The settle call leaves the receipt digest as a placeholder | mutant `settle-digest-unfilled` (E1) |
| M3 | contrary | The start response gives no follow-up call | mutant `start-no-followup` (E1) |
| M4 | contrary | `next_argv` is returned on completion | mutant `complete-next-argv` (E2) |
| M5 | contrary | A rejected attempt still requires live evidence | mutant `rejected-live-evidence` (E3) |
| M6 | contrary | The lock never waits | mutant `lock-no-wait` (E4) |
| M7 | contrary | `claim` ignores capacity | mutant `claim-ignores-capacity` (E5) |
| M8 | contrary | The claim action is not trimmed to free slots | mutant `offer-ignores-capacity` (E5) |
| M9 | contrary | Planning-blocked steps are offered for claim | mutant `offer-planning-blocked` (E6) |
| M10 | contrary | `claim` accepts a planning-blocked step | mutant `claim-planning-blocked` (E6) |
| H1 | hostile | `capacity` of 0, negative, fractional or a string | E5 |
| U1 | unknown → decided | A claim when capacity is exactly full | E5: `ECAPACITY` and no claim action; offers refill after a settle |
| U2 | unknown → decided | Runs created before `capacity` existed | E7: none is unlimited; old state files have no key and hydrate unchanged |
