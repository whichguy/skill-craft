# Test spec: dispatcher decisions D2–D5

Suite: `test/plan-dispatcher-decisions.test.js`. Mutants:
`test/orchestrator_scenarios/mutants/dispatcher-decisions.json`, run by
`test/orchestrator_scenarios/mutate.py`. Plan:
`docs/plan-orchestrator-validation-plan-2026-09-27.md`.

## Intent under test

- **D2 (lock recovery).** A lock whose recorded holder is a process that no
  longer exists on this host is recovered by the next writer. Every other
  holder is refused with `ELOCKED`, and the refusal names what to do. This
  covers a live holder, a holder on another host, an unreadable holder, and a
  recovery already in progress. Recovery never removes a lock that a live
  writer took after it was inspected. (`state.js` `acquireLock`,
  `removeDeadLock`; `references/protocol.md` "Run state authority")
- **D3 (no cap; exact recovery).** A rejected step has no retry limit. `next`
  offers a `retry` action carrying the attempt count, the rejection reason and
  a `call` (argv plus input) that works when run as given. Blocking reaches
  every downstream step and is undone after a retry.
- **D4 (verified BLOCKED routes to replanning).** A settlement with
  `verification.disposition: "replan"` (only with `passed: false`) marks the
  step as needing replanning. From then on the run starts no new work:
  - `claim` and a fresh `start` are refused with `EREPLAN`;
  - a retry of that attempt is refused;
  - `ready` is empty;
  - retries of other failed steps are not offered;
  - claimed attempts are offered a `release` call;
  - in-flight attempts can still finish and settle;
  - `next.replan` lists the replan steps, the accepted steps and the
    unfinished steps;
  - once nothing is in flight, the instruction says the run cannot complete.
- **D5 (fail closed with the recovery named).** A lost state file or a lost
  settled receipt fails with `ESTATELOST`. The message says to start a new run
  and leave out integrated steps. Nothing is rebuilt.

## Scenarios

| ID | Scenario | Failure signal |
|---|---|---|
| S1 | Lock left by a dead local process; `claim` runs | Claim fails, or the lock or recovery guard is left behind |
| S2 | Lock held by a live local process (this test) | Claim succeeds, or the lock bytes change |
| S3 | Lock from another host, with a dead PID | Claim succeeds, or the message doesn't name the host |
| S4 | Unreadable lock (garbage, string PID, negative PID) | Claim succeeds, or the lock bytes change |
| S5 | Recovery guard held by a live process, then by a dead one | Claim succeeds; the lock changes; the dead-guard message doesn't name the guard path |
| S6 | Lock is replaced by a live holder between inspection and removal | Live lock removed, or claim succeeds |
| S7 | Deep chain A→B→C→D plus E→F; B is rejected, retried 3 times, then accepted | C/D not blocked; not restored after retry; wrong attempt count; the returned `call` fails; a cap appears |
| S8 | B is settled `replan` while E is in flight; then E settles | Claims or retry allowed; `ready` not empty; `replan` fields wrong; in-flight E can't settle; no terminal instruction |
| S9 | X is claimed, then B is settled `replan` | Start succeeds; no `release` call; the `release` call fails when run |
| S10 | Disposition shape: `passed:true`+replan, `"REPLAN"`, SUCCEEDED receipt + `passed:false`+replan | Invalid shapes accepted; the valid SUCCEEDED+replan case refused |
| S11 | Replaying a replan settlement; a conflicting settlement | Replay not idempotent; conflict accepted |
| S12 | E FAILED while B needs replanning | A retry action is offered for E |
| S13 | State file deleted; settled receipt deleted | Wrong code, or no new-run recovery in the message |
| S14 | Owner takeover while replanning | Replan lost, or claims allowed after takeover |

## Invariants and oracle

The oracle is the test's own expectation for each scenario, computed from the
graph by hand. The test drives only the public `dispatch.js` CLI, one cold
process per call, except for the lock scenarios, which call `state.js`
directly in a child process. Recovery calls are executed exactly as `next`
returns them, with only the `reason` placeholder filled in. No test imports
dispatcher internals to decide an expected value.

## Out of scope

- Chain/ShipLoop handling of `replan`. It needs the chain's pinned dispatcher
  fixture to be re-pinned (plan gap 4).
- PID reuse. A reused PID reads as alive and is refused, which is the safe
  side, and it can't be produced deterministically.

## Review

1. **Is every clause violable by a scenario?** Yes:
   - D2 → S1–S6;
   - D3 → S7;
   - D4 → S8–S12 and S14;
   - D5 → S13.
2. **Are invariants observable?** Yes: exit status, error `code`, stderr
   text, lock-file bytes, `next` fields, and whether the returned call
   succeeds. None depend on internal calls.
3. **Is the oracle independent?** Expected values are literal step lists per
   scenario. A bug shared by oracle and code is possible only in reading the
   decisions themselves, and this spec states those.
4. **Can every scenario fail?** Each row lists its failure signal, and every
   mutant in the table below is confirmed killed by `mutate.py`.
5. **Is anything tested outside the contract?** No. S14 is pinned under U3
   below.

## Adversarial

| ID | Class | Condition | Covered by |
|---|---|---|---|
| M1 | contrary | A dead holder on another host is treated as recoverable | mutant `lock-ignores-host` (S3) |
| M2 | contrary | Every holder is treated as dead | mutant `lock-steals-live` (S2) |
| M3 | contrary | Removal skips the "bytes unchanged" check | mutant `lock-no-compare` (S6) |
| M4 | contrary | The recovery guard is never released | mutant `guard-leaks` (S1) |
| M5 | contrary | An unreadable lock is treated as dead | mutant `unreadable-is-dead` (S4) |
| M6 | contrary | `replan` is allowed with `passed: true` | mutant `replan-with-pass` (S10) |
| M7 | contrary | A replan attempt can be retried | mutant `retry-replan` (S8) |
| M8 | contrary | `claim` is not refused while replanning | mutant `claim-during-replan` (S8) |
| M9 | contrary | `ready` still lists steps while replanning | mutant `ready-during-replan` (S8) |
| M10 | contrary | A fresh `start` is allowed while replanning | mutant `start-during-replan` (S9) |
| M11 | contrary | Blocking stops one level down | mutant `shallow-block` (S7) |
| M12 | contrary | Retry is still offered for other failed steps while replanning | mutant `retry-offered-during-replan` (S12) |
| M13 | contrary | The retry call names the wrong verb | mutant `retry-call-verb` (S7) |
| M14 | contrary | The attempt count excludes retried attempts | mutant `attempt-count` (S7) |
| M15 | contrary | A lost state file loses its recovery code | mutant `state-lost-code` (S13) |
| M16 | contrary | Recovery is `retry` for replan attempts | mutant `replan-recovery` (S8) |
| M17 | contrary | The terminal replan instruction is never given | mutant `no-terminal-replan` (S8) |
| H1 | hostile | A disposition other than `"replan"` | S10 |
| H2 | hostile | A lock PID as a string, or negative | S4 |
| H3 | hostile | A settlement replay with a changed disposition | S11 |
| U1 | unknown → decided | A step in flight when a replan is decided | S8: it finishes and settles; accepted work is listed |
| U2 | unknown → decided | A claimed, unstarted attempt when a replan is decided | S9: `release` via retry; `start` refused |
| U3 | unknown → pinned | Owner takeover while replanning | S14: allowed; replan persists; claims still refused |
| U4 | unknown → decided | The recovery guard is left by a dead process | S5: refused, naming the guard file; the lock itself is still recovered after it's removed |
| U5 | unknown → decided | A SUCCEEDED receipt whose criteria can't be confirmed here | S10: `passed:false` with replan is allowed (matches the parent-verify rule) |
