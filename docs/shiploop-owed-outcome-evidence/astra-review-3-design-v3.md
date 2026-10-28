# Astra review: design v3

Run 2026-10-27 through the `ask` agent: model_used `gpt-6-astra`, persona `codex-astra`, effort `max`, fallback `False`, exit `0`. Read-only request; no files changed in the repository. Code citations are Astra's own and were checked as recorded in [the journal](../shiploop-owed-outcome-journal.md).

## Question

Use MAX reasoning effort. Follow-up design review of the same ShipLoop question, now design v3 (it supersedes v2). Repository: the skill-craft repository (read-only; do not edit anything). Read the code you need; cite file and symbol for every code claim and mark each claim verified (you read it) or inferred. Keep the answer under 1,000 words.

Read the section "Design v3: the step is an Until Loop" in docs/shiploop-owed-outcome-journal.md, and the section "Where v2 conflicts with the Until Loop" in the same file.

v3 in one line: each inner stage keeps one bound Until Loop; ShipLoop adds the stage's checkable criteria (including `complete --check-only` where the stage has one) as the contract's `exit_checks`, so the runtime refuses `satisfied` until they pass on the current tree; the stop hook asks for whichever report is owed (the loop's done while the receipt is active, the step callback once it is terminal).

Questions (answer each, numbered):
1. Can ShipLoop's gates (test rerun with floors, base and candidate runs, mutation check, lint, step proof) run as exit checks inside the loop without losing anything, given check-only reuse of test runs? Which cannot, and why?
2. Contracts must name no install path (shiploop_loops module docstring). Is a stable per-run launcher in the run directory the right way for an exit check to call ShipLoop, or is there a simpler one?
3. Hand-back: keep the step callback as a second command, or add a runtime option that prints a parent-supplied return command at the terminal packet? Does the latter break the card's "parent must not synthesize callbacks" rule?
4. What else in today's inner-stage packets and `complete` gates becomes redundant once exit checks are in the contract, so it can be removed without losing a feature?

End with your single strongest recommendation on v3.

## Answer, verbatim

**Verified** means inspected source or test bodies; tests were not executed. **Inferred** marks design conclusions.

1. **All five gate judgments fit inside the loop, but today’s check-only path is not equivalent to acceptance (inferred).**

   **Verified:** Base/candidate/mutation, reruns, and inline step Proof have non-counting paths. Lint’s check-only path forces report mode. [shiploop_navigator.py — `_test_loop_gate`, `_step_proof_gate`, `_test_rerun_gate`](skills/shiploop/scripts/shiploop_navigator.py:4408), [shiploop_navigator.py — `_lint_gate`](skills/shiploop/scripts/shiploop_navigator.py:4617).

   **The critical mismatch is floors. Verified:** `red_check` writes an uncounted record that `floor_detail` does not consume; the counted base run establishes the fresh floor later. An existing test explicitly demonstrates check-only passing **two tests**, followed by `complete` refusing because the base establishes **three**. [shiploop_test_loop.py — `floor_detail`](skills/shiploop/scripts/shiploop_test_loop.py:930), [shiploop-test-loop.test.py — `test_a_check_only_run_below_the_floor_the_base_run_sets_at_complete_is_run_again_not_taken`](test/shiploop-test-loop.test.py:2341). **Inferred:** As written, v3 still permits precisely the post-loop refusal it intends to eliminate. Feed the fresh base counts into the exit evaluation, preserve historical floor ratcheting, and retain accepted/counting records.

   **Verified:** Candidate/rerun evidence and Proof can be reused; mutation also reuses matching evidence. `base_check` still executes its base run. Reuse therefore does not eliminate every repeated execution. [shiploop_test_loop.py — `_reused`](skills/shiploop/scripts/shiploop_test_loop.py:1131), [same — `step_proof`](skills/shiploop/scripts/shiploop_test_loop.py:1394), [shiploop_mutation.py — `_reusable`](skills/shiploop/scripts/shiploop_mutation.py:429), [shiploop_test_loop.py — `base_check`](skills/shiploop/scripts/shiploop_test_loop.py:1829).

   **Inferred:** Preserve these evaluators, including RED exceptions, retired tests, mutation dispositions, waivers and explicit skips. Raw base-test exit codes cannot replace their judgment. Lint autofixing belongs in Work before final verification; commits, graph advancement and Improve acceptance remain outside exit checks. Unobservable criteria remain semantic assessments, as the card requires. [ADAPTER.md — exit-check rules](skills/improve/runtime/until-loop/ADAPTER.md:106).

   Require a fully validated **done** draft for the success check. **Verified:** Gate helpers skip non-done outcomes, and check-only returns before `apply`; successful preview alone is not complete acceptance validation. [shiploop_navigator.py — `dispatch`](skills/shiploop/scripts/shiploop_navigator.py:9329).

2. **A stable run-local locator is right; a symlink is simpler than generated launcher code (inferred).**

   **Verified:** The restriction concerns deterministic contract bytes across installation changes. The entrypoint resolves `__file__` before locating sibling imports and `PACKAGE_ROOT`. [shiploop_loops.py — module contract](skills/shiploop/scripts/shiploop_loops.py:11), [shiploop — module initialization](skills/shiploop/scripts/shiploop:19).

   **Inferred:** On these POSIX hosts, use `python3 <run>/shiploop complete … --check-only`, with `<run>/shiploop` symlinked to the selected entrypoint. Installation relocation changes the binding, not contract text. Detect a missing target explicitly. A small launcher is justified only if resolving relocations requires more than updating that link; do not assume a global PATH installation.

3. **Keep the second command initially; terminal printing is an optional usability improvement (inferred).**

   **Verified:** The card explicitly assigns the parent its own callback while forbidding synthesis of the loop’s callbacks. The runtime’s terminal packet clears its `done_argv` and `next_argv`. [ADAPTER.md — parent hand-back](skills/improve/runtime/until-loop/ADAPTER.md:59), [same — caller boundary](skills/improve/runtime/until-loop/ADAPTER.md:255), [until_loop_ephemeral.py — `_terminal_packet`](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:887).

   **Inferred:** Printing an opaque, parent-supplied return command does **not** synthesize a loop callback. It still requires the second command. Label it as a parent handoff, preserve ownership on delegated routes, and never automatically submit success for `stopped`. Update the card’s wording and strict packet consumers if adding this field.

4. **Remove duplicated orchestration only after making the receipt sufficient for acceptance (inferred).**

   **Verified deletion candidates:** `_CHECK_ONLY` finish reminders, repeated `REPORT_FIELDS`, and restart-after-refusal instructions duplicate responsibilities the runtime would own. The exceptional send-back bypasses compensate for gates failing after terminal completion. [shiploop_loops.py — `WORK`, `_CHECK_ONLY`](skills/shiploop/scripts/shiploop_loops.py:66), [same — `REPORT_FIELDS`, `RESULT_LINE`](skills/shiploop/scripts/shiploop_loops.py:613), [same — `check_terminal`](skills/shiploop/scripts/shiploop_loops.py:815). **Inferred:** Remove those inner-stage compensations once failures reliably remain inside the active loop; retain blocked-before-start recovery.

   **Verified blocker:** `check_loop_packet` currently compares neither expected `exit_checks` nor their successful results. The runtime also permits command repairs. [shiploop_loops.py — `check_loop_packet`](skills/shiploop/scripts/shiploop_loops.py:724), [until_loop_ephemeral.py — `_transition`](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1009). **Inferred:** Removing parent gates now would permit a receipt from a weakened check contract. Validate the exact checks and an explicit repair policy.

   **Verified:** Workspace hashing excludes `.shiploop`; missing Git fingerprints bypass the tree comparison. Consequently it does not bind an inbox draft, and “current tree” is conditional. [until_loop_ephemeral.py — `_workspace_tree`](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:456), [same — `_transition`](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1033). **Inferred:** Bind the draft and relevant evidence explicitly before replacing acceptance checks with receipt consumption. Preserve per-edit checks: exit verification alone does not preserve that cadence. [shiploop_prompts.py — `_IMPLEMENT_CHECK_INLINE`](skills/shiploop/scripts/shiploop_prompts.py:727).

**Strongest recommendation:** Adopt v3 around one shared stage evaluator whose verdict binds the action, contract, draft, candidate, base and floors. Let Until Loop enforce that verdict and `complete` consume it. Establish this equivalence before deleting gates or extending the hand-back API.
