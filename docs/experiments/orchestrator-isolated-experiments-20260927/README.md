# Orchestrator isolated experiments (2026-09-27)

Before any further material change to the Plan Orchestrator (ShipLoop, Until Loop, Plan
Dispatcher), the owner asked that every claimed defect and every suspected side effect of
recent changes be checked **in isolation**. This document records the method, every
verdict, and the conditions that follow from them. Clause IDs (S-1 … S-13) refer to
`test/shiploop_e2e/SPEC.md`.

## Method

- **Source under test:** `git archive b3e466c7` (local `main` on 2026-09-27) extracted beside the
  scripts. No repository file was edited by any experiment.
- **Scripted experiments** drive the real CLIs and ShipLoop's own fixture drivers
  (`test/shiploop-test-loop.test.py`, `test/shiploop-actual-improve-cli.test.py`) in temporary
  Git repositories, with real test loops and the real bundled Until Loop runtime. Model
  judgments are replaced by fixed, synthetic results.
- **Transcript mining** reads the recorded Grok 4.7 (medium) E2E runs 6, 6b, 7, 7b and 8b
  (skill-craft 1.4.0 to 1.6.0) read-only.
- Each experiment states a **prediction** first, then the observation and a verdict. A claim is
  a hypothesis until an experiment confirms it; two of the audit session's suspected defects
  were disproved this way.

### Rerunning

```sh
cd docs/experiments/orchestrator-isolated-experiments-20260927/scripts
mkdir src && git -C ../../../.. archive b3e466c7 skills test scripts catalog | tar -x -C src
python3 tier1/exp45_invariants.py      # any tier1/, round2/, e10-12/ script
node dispatcher/p2_complete_next_argv.js
E2E_RUNS_DIR=<dir with e2e-run*> python3 e4/analyze.py
```

`scripts/src` is the snapshot and is not committed. Swap the commit to re-check a later source.

## Verdicts

### Confirmed defects

| ID | Finding | Evidence | Clauses |
|---|---|---|---|
| X1 | **A hand-written terminal packet passes.** A packet built only from the contract file ShipLoop writes (the 14 keys, a `state_file` path that never existed, the expected receipt path, a trivial report) is accepted at `static-checks`, so the quality review never runs, and at `test-green`. Nothing binds the packet to a real runtime run. The audit's C1 is **not** closed by the receipt work. | `round2/e5_forge.py` | S-9, S-10 |
| X2 | **Racing callbacks lose a result silently.** Two `complete` calls with different results, started together: both exit 0 in 20 of 20; one result wins and the other host receives the next packet as if accepted. Both hosts write the one generated path `inbox/<action>.md` before either locked read. Started 0.6 s apart, the second is refused ("conflicting producer replay") 10 of 10. No state corruption. | `e10-12/e11_concurrent.py` | S-1, S-6 |
| X3 | **An Improve review can rewrite a stage result and close on one unchanged pass.** At the spec checkpoint, one trivial pass with no repository edit completed the loop, and `improve-complete` accepted a rewritten `final_result`. The one-pass guard looks only at repository files. | `round2/e2_revised_onepass.py` | S-10 |
| X4 | **The one-pass exit cannot see some edits.** After one trivial pass the loop completed with an edit to a git-ignored file, to a file under `.shiploop/`, and to a file outside the workspace. Tracked and new untracked files are seen. | `tier1/exp3_onepass.py` | S-10 |
| X5 | **The lint gate now runs on each implement step (regression from per-step implement).** With lint `report` or `fix`, step S1's `done` is refused for an unused import S2 will use (F401) and for a call to a helper S2 will define (F821). Before per-step implement, lint ran once after the item's whole implementation. | `round2/e8_lint_steps.py` | S-2, S-9 |
| X6 | **About 18 of 34 stages accept a bare `{outcome: done}`** with no script check, in an in-place run without a delivery contract: intake, discovery, research, spec, test-strategy, select-work, baseline, test-author, document, skill-assess, skill-validate, integrate, carry-forward, product-acceptance, release-check, release, operations, handoff. Some are judgment by nature; `baseline` (run the recorded commands before the change) and `test-author` (the named tests exist and run) are mechanical. | `round2/e1_gates.py` | S-5, S-9 |
| X7 | **Test evidence can be printed.** Focused commands need a readable test count (`true`, a bare fake summary and a zero-test runner are refused; `red_na` does not rescue them). But a command that prints a unittest-style summary around a real condition passes red, green and regression, and a regression command `true` is accepted. | `round2/e6_trivial_cmds.py` | S-9 |
| X8 | **All six Plan Dispatcher dead ends still reproduce** (this is the `Execute: schedule` path): BLOCKED offers only retry; `complete:true` still returns `next_argv`; 16 of 19 calls in a 3-step walk are composed by the caller (only `report_argv` is returned); deleting a rejected attempt's workspace or ready evidence bricks `next`, `packet`, `retry` and `takeover`; 20 concurrent claims give 16 `ELOCKED` with no retry, and an orphan lock blocks every write; no capacity input, and a planning-blocked step is listed as ready. **Fixed in skill-craft 1.9.0** (plan-dispatcher 0.5.0, `55cab541`): exact calls for every action, no `next_argv` after completion, a `capacity` input, planning-blocked steps not claimable, safe cleanup of rejected attempts, and lock waiting and recovery; scenarios E1–E7 in `test/orchestrator_scenarios/` reproduce these probes. | `dispatcher/p1…p6` | S-4, S-6 |
| X9 | **In-place auto-commit takes the user's work.** On an in-place run, the user's uncommitted edits in a declared file the item changed, and a file the user creates at a declared path mid-run, are committed as the item's work. The default workspace route is protected (see H4). | `tier1/exp2_autocommit.py` | S-5, S-11 |
| X10 | **Mid-loop recovery restarts the loop.** The recovered packet names the receipt (which holds the live `done_argv`) but gives no "continue from the receipt" instruction; rerunning the printed `Start` creates a second loop and leaves the first state file behind. Recovery after the loop finished works. | `round2/e9_loop_recovery.py` | S-5, S-6 |
| X11 | **Whole-printed packets can exceed Grok's limit.** Active heads peak at 5.6 KB (30 heavy work items), but paused, halted and blocked packets print whole and reach 20.4 to 22.7 KB with long data, over Grok's ~20,000-character cut; repeated long paths drive most of it. | `e10-12/e12_head_size.py` | S-7 |
| X12 | **The printed head does not name the implement step**; the step line is only in the packet file. 5 of 14 implement steps in the E2E runs completed without reading the file (they still did the right work; see H6). | `e4/`, transcript mining | S-6, S-7 |
| X13 | **Integrate's "Not committed … delete generated output" notice is printed once**, by `complete`, and not repeated by recovery `next`. | `tier1/exp45_invariants.py` | S-6 |
| X14 | **The return guard has two small gaps:** a git-ignored file is outside the source fingerprint, and the refusal does not name the path that drifted. | `e10-12/e10_return_guard.py` | S-6 |
| X15 | **Keepalive continues without bound while a background task runs** (30 of 30 continuations with no progress). No harm was observed in the E2E runs (background tasks all ended inside one action). | `tier1/exp1_keepalive.py`, `e4/` | S-10 |

### Held (pin these as regression scenarios)

| ID | Behaviour | Evidence |
|---|---|---|
| H1 | A refused callback changes nothing: 164 probes (bogus outcome, missing file, stale action, wrong verb) over a 41-action walk left `state.md` byte-identical. | `tier1/exp45_invariants.py` |
| H2 | `next` is idempotent (41 of 41), and a fresh-process `next` after every boundary rewrites a byte-identical packet file and head. | `tier1/exp45_invariants.py` |
| H3 | Keepalive's 14-continuation limit counts refused callbacks only; a turn with no callback is released at the second stop by the no-progress rule; an accepted result resets the count. | `tier1/exp1_keepalive.py` |
| H4 | The workspace return guard refused all 12 source-drift variants (tracked, unrelated tracked, untracked, same path as the candidate; before or after plan-return); the user's edits were untouched. | `e10-12/e10_return_guard.py` |
| H5 | Per-step implement follows the accepted plan exactly: Improve shrinking or growing the steps, `repeat`, blocked then resume, and `revise` then replan. | `round2/e7_steps.py` |
| H6 | In the E2E runs: unread implement steps did their own step's work; the four never-read stages (select-work, baseline, test-author, test-red) met their done-when in 20 of 20; post-compaction recovery used `shiploop next` or `status` in 5 of 6 compactions with no refusals; per-step packets averaged 9.5 KB with no reference re-reads outside compactions. | `e2e-transcript-mining.md`, `e4/` |
| H7 | A full scripted walk to `handoff` takes about 1 s in process, so scenario tests fit the quick tier. | `tier1/`, `round2/` |

### Disproved or unsupported: do not act on these

- The keepalive limit stopping long legitimate work (see H3).
- Per-step packets inflating context (see H6).
- Removing the compaction hook breaking recovery (see H6). Recovery does re-read `SKILL.md` plus references (48 to 91 KB) by the model's own choice.

## Status after owner triage (2026-09-27)

The owner cut this list under KISS/YAGNI: fix only what breaks or misleads a normal run, and
record adversarial constructions and never-seen gaps as known limits, acceptable by design.
The authoritative list is `docs/plan-orchestrator-validation-plan-2026-09-27.md` ("Audit
conditions X1–X15" and "Known limits").

- **Fixed:** X8 in skill-craft 1.9.0 (`55cab541`); X5 (lint gates only an item's last implement
  step), X10 (loop packets continue from the receipt's `next_argv`) and X11 (long paused, halted
  and blocked packets print a pointer) in 1.10.0 (`6248a774`).
- **Known limits, no guards planned:** X1, X2, X3, X4, X6, X7, X9, X12, X13, X14, X15, and pinning
  H1–H5. The conditions below are kept as the original proposal; do not implement the dropped ones.

## Conditions to address (original proposal, superseded by the triage above)

Each item enters through the spec's change admission: a failing scenario first, an anchor,
a non-regression statement, then the change. Items marked **decision** need the owner.

1. **Bind loop evidence to a real run (X1).** A terminal packet must prove it came from the
   runtime, for example a run token ShipLoop records when it starts the loop, or ShipLoop
   starting the loop itself. Scenario: the forged packet from `e5_forge.py` is refused at
   `static-checks` and `test-green`.
2. **Make racing callbacks safe (X2).** Each submission must be distinguishable (for example,
   per-submission result paths, or a content digest read under the lock) so that a loser is
   refused, not told it was accepted. Scenario: `e11_concurrent.py` case (b) yields exactly one
   exit 0 and one conflict refusal.
3. **A revised stage result counts as a change (X3, X4).** An Improve child whose final result
   differs from the seed must not close on one unchanged pass; decide whether ignored, runtime
   and outside-workspace candidates can ever use the one-pass exit (**decision**). Scenarios:
   `e2_revised_onepass.py` case A and the ignored and `.shiploop/` rows of `exp3_onepass.py`
   stay active.
4. **Lint at the right boundary (X5).** Choose: lint at the item's last implement step, lint
   each step but let later steps clear earlier findings, or keep per-step lint (**decision**).
   Scenario: `e8_lint_steps.py`.
5. **Script-check the mechanical stages (X6, X7).** At least `baseline` (ShipLoop runs the
   recorded commands) and `test-author` (the recorded test IDs exist and run), and a runner
   check for regression commands; decide how far to trust printed summaries
   (**decision**, S-8 tool catalog). Scenarios: `e1_gates.py` rows and `e6_trivial_cmds.py`.
6. **Done in 1.9.0.** **Dispatcher actions are exact calls (X8).** Every action carries its argv and a
   pre-filled input; `complete:true` returns no `next_argv`; rejected-attempt cleanup cannot
   brick the run; capacity is an input; planning-blocked steps are not offered for claim;
   concurrent claims retry or queue. This precedes D1 (inline through the dispatcher) and the
   amnesiac driver. Scenarios: `dispatcher/p1…p6`.
7. **Protect user work on in-place runs (X9)** (**decision**: refuse in-place when a declared
   file was dirty at the item's base, commit only the item's own hunks, or document the
   limit). Scenario: `exp2_autocommit.py` cases A and C.
8. **Recovery covers every boundary (X10, X12, X13).** A mid-loop packet says to continue from
   the receipt's `next_argv`; the head names the implement step; the integrate notice is
   repeated until acted on. Scenarios: `e9_loop_recovery.py` case A, a head check, and
   `exp45_invariants.py` at integrate.
9. **Keep whole-printed packets under the host limit (X11)**, for example by printing the head
   plus the file path for paused, halted and blocked packets too. Scenario: `e12_head_size.py`.
10. **Small guards (X14, X15):** include ignored product paths in the return fingerprint or
    document that they are excluded, and name the drifted path; decide whether a waiting
    background task needs a bound (**decision**; no harm observed).
11. **Pin H1 to H5 as regression scenarios** so they cannot drift.

Suggested order: 1, 2, 3 (evidence integrity), then 6 (the `Execute: schedule` path), then
4 and 8 (per-step and recovery), then 5, 7, 9, 10.
