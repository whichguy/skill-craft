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
mkdir src && git -C ../../../.. archive <commit> skills test scripts catalog | tar -x -C src   # b3e466c7 originally; e707b794 for the 2026-10-25 re-verification
python3 tier1/exp45_invariants.py      # any tier1/, round2/, e10-12/ script
node dispatcher/p2_complete_next_argv.js
E2E_RUNS_DIR=<dir with e2e-run*> python3 e4/analyze.py
```

`scripts/src` is the snapshot and is not committed. Swap the commit to re-check a later source.

## Re-verification on skill-craft 2.9.0 (2026-10-25)

Every claim below was re-run on a fresh `git archive` of `origin/main` **e707b794** (skill-craft 2.9.0,
about 1,150 commits after b3e466c7) and re-anchored by symbol. The 2026-09-27 verdicts further down
are kept as measured; this table supersedes them where it differs.

Several original scripts no longer run unchanged, because modules moved (for example
`shiploop_quality._PACKET_KEYS` now lives in `shiploop_loops`) and the fixture driver now
fills each stage's required fields before submitting (`inner.fill` in `test/shiploop-test-loop.test.py`).
The original `round2/e1_gates.py` therefore reports almost every stage as accepting a bare `done`, and
**that output is invalid on 2.9.0**. Use `round2/e1_gates_v3.py`, which submits a truly bare result
through the real `dispatch(check_only=True)`.

| ID | 2026-10-25 verdict on e707b794 | Anchor (current symbols) | Evidence |
|---|---|---|---|
| X1 | **Still accurate.** A hand-written terminal packet (the current key set, including the Until Loop 0.8+ keys `exit_checks`, `check_repairs`, `last_check_results`, `verify_script`) was accepted at `verify` (the former static-checks) and at `test` (the former test-green) when the commands really pass; with failing commands ShipLoop's own rerun refuses it. Nothing ties the receipt to a real runtime run. | `shiploop_loops.check_loop_packet`, `_PACKET_KEYS`, `_PROGRESS_KEYS`, `check_terminal` | `round2/e5_forge_v2.py` |
| X2 | **Still accurate.** Two racing `complete` calls with different results both exit 0 and one result is silently lost (10 of 10 in both write modes); started 0.6 s apart, the second is refused "conflicting producer replay" (10 of 10). Identical results and concurrent `next` are clean; state stays valid. | `shiploop_navigator.apply` treats an accepted action as a replay unless the submission differs from both `seed_result` and the accepted result; both racers write the one path `inbox/<action>.md` before either locked read. | `e10-12/e11_concurrent.py`, `e11_staggered.py` (unchanged) |
| X3 | **Changed, wider.** An Improve child now closes on any single trivial pass: a revised `final_result` with no edit (A), the unrevised control (B), **and a pass that edited the repository (C)** all completed after one pass and were accepted; only a non-trivial first pass (D) stays active. The unchanged-tree check no longer decides it. | `shiploop_navigator.IMPROVE_TRIVIAL_REVIEWS = 1` (owner 2026-10-20, `5e377ff7`, released in 2.8.0); ShipLoop starts the child itself and imports it with `complete --final-result`. | `round2/e2_v2.py` |
| X4 | **Still accurate at the runtime, but out of ShipLoop's path.** On the vendored Until Loop **0.10.0**, with a gate of 2: no edit, ignored file, `.shiploop/` file and outside-workspace edits all complete after one trivial pass; tracked and new untracked files stay active. ShipLoop's own gates are now 0 or 1 (verify 1, other inner loops 0, Improve 1), and `start_tree` is recorded only for gates of 2 or more, so only gate-2 loops such as Backchain's `converge` can reach this exit. | `until_loop_ephemeral._workspace_tree`, `_RUNTIME_EXCLUDES`, `_transition` (`unchanged_first_pass`); `shiploop_loops.TRIVIAL_REVIEWS` | `tier1/exp3_matrix.py` |
| X5 | **Changed: the 1.10.0 fix was deliberately reverted.** Step S1 is refused again in all four cases (lint `report` and `fix`, an unused import S2 will use and a helper S2 will define): "ShipLoop lint gate: implement is not done while 1 new lint finding…". Every implement step is gated because each step is now followed by its own Improve review; the way out is `lint_waivers`. | `shiploop_navigator._lint_gate` (comment "Owner decision 2026-10-10: every implement step is gated"); fix `0abcfb87`, reverted by the inner-loop redesign `d7388043` | `round2/e8_lint_steps_v2.py` |
| X6 | **Changed.** The graph is now 23 stages (was 34). A bare `{outcome, summary}` is accepted at 8: intake, discovery, research, document, release-check, release, operations, handoff. The others refuse, but several only for required fields that an empty list satisfies (`assumptions`, `learned` and `decisions`, `unverified`, `primary`, `test_layers`), which checks shape rather than evidence. | The `_check_submitted_*` gates in `shiploop_navigator.dispatch` (`_check_submitted_test_commands`, `_check_submitted_recorded_commands` and others), the knowledge gate at `prepare`, and the test rerun gates. | `round2/e1_gates_v3.py` (new) |
| X7 | **Still accurate.** The test stage now runs a base run (must be red), a candidate run (green) and a mutation check. Focused `true`, a bare fake summary and a zero-test runner are refused; a fake summary with listed IDs is refused. A command that prints a unittest-style summary around a real condition is **accepted** through base, candidate, mutation and the verify rerun; a regression command `true`, and a regression command printing a bare fake summary, are **accepted**. | `shiploop_test_loop.judge` (a regression command without `min_tests` is `passed-uncounted`, a pass), `base_check`, `loop_run`, `mutation_check` | `round2/e6_v2.py` |
| X8 | **Fixed, no regression.** A finished run has no `next_argv`; following only returned calls completes a walk (22 of 23 calls from a response; only `init` composed); `capacity` is enforced when set (claims are unbounded without it); planning-blocked steps are left out of the claim action and a direct claim fails `EPLANNING_CONTEXT`; cleaning up a rejected attempt no longer bricks `next`, `packet`, `retry` or `takeover` (deleting an *accepted* attempt's evidence still fails `next`, closed); 20 concurrent claims give 20 successes and 0 `ELOCKED`; a dead local lock holder is recovered and a live one is waited for; a settle with `verification.disposition: "replan"` makes `replan` the only action. | `dispatch.js` `CALL_RULE` and `action.call`; `state.js` `requireCapacity` (`ECAPACITY`), `acquireLock`, `waitForLock`, `LOCK_WAIT_MS`, `deadLocalHolder`, `removeDeadLock`, `replanAttempts`, `needsReplan` (`EREPLAN`). Commits `f1af4618`, `0ec60788`, released in `55cab541`. | `dispatcher/p1b`, `p2`, `p3b`, `p4`, `p5`, `p5b`, `p6`, `p6b` (new or adapted) |
| X9 | **Still accurate, and earlier.** There is no integrate stage: ShipLoop commits each accepted inline step (`feat(W1/S1)`) and whatever remains at verify. On an in-place run the user's uncommitted work in a declared file the step changed went into the step commit (A); a declared file the user created during implement went into the step commit (C1), and one created after it into verify's commit (C2); a declared file dirty before the run and left untouched was not taken (B, it is in the item's base snapshot); an undeclared file was left and named (D). | `shiploop_navigator._step_commit` (`32e66660`) and `_item_commit` → `shiploop_item_scope.commit_item` / `commit_scope` → `shiploop_git.commit_paths` (`git add -A -- <paths>`); base from `shiploop_lint.capture_base` | `tier1/exp2_autocommit_v2.py` |
| X10 | **Fixed.** Mid-loop, the recovered packet says the loop already started, not to start it again, and to run its `next_argv` once; it no longer prints the start command, and the runtime now refuses a second start. Continuing from the receipt completed the loop and `complete` was accepted. Recovery after the loop still works. | `shiploop_loops.RESUME_LINE`, `RESUME_RESULT_LINE` (`0abcfb87`, released 1.10.0); runtime `_check_start_receipt` | `round2/e9_v2.py` |
| X11 | **Still fixed, and the design changed.** Since 2026-10-11 a packet of up to 16,000 characters prints whole; above that an active packet prints its head and others print a pointer. Paused, halted and blocked packets are now 9 to 11 K (the status reason is cut to 200 characters) and print whole; a forced 32 K paused text printed a 15,992-character pointer. **New: active heads are no longer small.** With ordinary data heads fill to about 20,000 (mean about 12.9 K, against 5.6 K before); with long synthetic data (1,500-character summaries, ten 300-character criteria) implement heads reach **22,541, past Grok's ~20,000 cut**, because the required Step block (the accepted-step summaries alone are 6.1 K) is never trimmed. The repository's own head table shows nothing over the cut because it uses ordinary data. | `shiploop_navigator.printed_text`, `packet_head`, `PRINT_LIMIT = 16_000`, `HEAD_LIMIT = 20_000`, required tiers `P0`/`P1` (`3c99addc`); `_status_text` | `e10-12/e12_v2.py` |
| X12 | **Fixed.** 150 of 150 implement prints, and every head, contain "Step S<n> (k of N)". | `step_block`, printed by `render`, `packet_head` and `improve_handoff_text` (`12151c49`) | `e10-12/e12_v2.py` |
| X13 | **Still accurate in substance; the details changed.** There is no integrate stage. The post-commit notice now comes after verify's commit and is printed once by `complete`; recovery `next` at carry-forward does not repeat it. New: the verify packet warns before the commit ("Changed, ShipLoop will not commit: …"), so `next` at verify does show that warning. The in-place wording is now "…otherwise delete it"; "delete generated output" appears only in the worktree text. `complete` also prints other one-time notices recovery never repeats: discovery's request notice, implement's "Gates: step-proof …" and document's "Gates: base / candidate …" (4 of 22 heads differ for this reason). | `_item_commit` (notice), `_commit_scope_lines` (`6bd20ec1`), `shiploop_stage_spec.item_left`, `_LEFT_IN_PLACE`, `_LEFT_FOR_RETURN` | `tier1/exp45_invariants.py`, `tier1/exp2_autocommit_v2.py` |
| X14 | **Still accurate (both gaps).** A git-ignored file changed in the source checkout does not block the return (fast-forward in 4 of 4); all 24 refusals read only "source checkout drifted since preparation; return is blocked", without the path. | `shiploop_workspace._fingerprint` uses `_snapshot_tree` and `_untracked`, which lists only untracked, non-ignored files; `plan_return` and `execute_return` call `_fail(...)` with no path. | `e10-12/e10_return_guard.py` (unchanged) |
| X15 | **Still accurate.** 30 of 30 continuations with no progress while a background task runs. | `shiploop_keepalive._decide` skips the no-progress and stuck counts when `waiting`. | `tier1/exp1_keepalive.py` |
| H1 | **Still accurate.** 124 probes (bogus outcome, missing file, stale action, wrong verb) over a 31-action walk all exit 2 and leave `state.md` unchanged. | Gates run before `apply`; `save` only after acceptance. | `tier1/exp45_invariants.py` |
| H2 | **Still accurate** for the packet: `next` idempotent 31 of 31, packet file byte-identical 22 of 22. The printed head differs from `complete`'s output only by the one-time notices in X13. | `shiploop_navigator.emit` and `packet_head`. | `tier1/exp45_invariants.py` |
| H3 | **Changed in number only.** The limit is now `STUCK_CONTINUATIONS = 22` (2 × `MAX_REFUSED_RUNS` = 11, raised in `46e3326b`): refused callbacks continue 22 times and the stop is allowed at the 23rd. A turn with no callback is still released at the 2nd stop; `CONTINUATION_CAPS = {"grok": 8}` is still only a warning. | `shiploop_keepalive._decide`, `STUCK_CONTINUATIONS`, `CONTINUATION_CAPS`. | `tier1/exp1_keepalive.py` |
| H4 | **Still accurate.** All 16 source-drift variants in the script's matrix were refused with the user's edits intact (the 2026-09-27 row says 12; the matrix has 16). | `shiploop_workspace.plan_return`, `execute_return`. | `e10-12/e10_return_guard.py` |
| H5 | **Still accurate; the outcomes changed.** Three steps, Improve shrinking 3→1 and growing 1→3, blocked (awaiting) then resumed, and send-back then a new plan all follow the accepted plan, with an Improve after each step. `repeat` and `revise` at implement are now refused ("implement accepts only done, blocked, send-back"), and `blocked_by` became `awaiting`. | `step_view`, `implement_progress`, `finish_improve(final_result)`, `control("resume")` | `round2/e7_steps_v2.py` |
| H6 | Not re-run (transcript evidence from runs 6 to 8b on 1.4.0 to 1.6.0). | | `e2e-transcript-mining.md` |
| H7 | **Changed.** A 31-action walk with probes now takes about 55 s (was 14 s for 41 actions). | | `tier1/exp45_invariants.py` |

### Summary of the re-verification

Pinned to `e707b794`. Releases 2.9.1 and 2.9.2, which followed it, were read but not re-run: ShipLoop's
navigator changed only refusal wording, Improve's bound instructions now default to one qualifying review
(consistent with X3), and the vendored Until Loop's provenance moved to 0.10.1 with no change to its runtime
scripts.

- **Fixed:** X8, X10, X12. **Still fixed, design changed:** X11.
- **Still accurate:** X1, X2, X7, X14, X15, H1, H2, H4. **Still accurate, details changed:** X9 (now at the step
  commit too), X13, H5.
- **Changed:** X3 (wider: any single trivial Improve pass closes, even after a repository edit), X4 (still in the
  runtime, but ShipLoop's loops no longer reach it), X5 (the fix was deliberately reverted), X6 (8 of 23 stages accept
  a bare `done`), H3 (limit 22), H7 (slower).
- **New:** active heads can exceed Grok's ~20,000 cut with long data (X11 row), and a planning-stage Improve can edit
  files and close on one pass with no step proof rerun (X3 row; the implement-step plan relies on re-proof, which
  only exists for implement steps).

The 2026-09-27 triage of record (`docs/plan-orchestrator-validation-plan-2026-09-27.md`, "Known limits") was
decided on the earlier facts; X3, X5, X6 and X13 now read differently there.

**Related plan:** `docs/shiploop-implement-step-fix-plan-2026-10-17.md` (refreshed 2026-10-25 on the same commit)
overlaps X7 (R08/T37, the candidate judge; a different hole in the same `shiploop_test_loop.judge`), X10 (R19/T49,
run-owned loop state), X3 (R14/T52 and T33 re-proof), X12 (R02/T8, the shared Step block), X11 (R13/T16/T43, the
16,000 / 19,500 / 20,000 limits), X13 (R17/T47, the pending-review message) and X6 (R16/T46, release-check
accepts a bare `done`).

## Verdicts (as measured on b3e466c7, 2026-09-27)

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
