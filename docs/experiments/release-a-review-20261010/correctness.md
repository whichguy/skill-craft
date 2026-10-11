# Release A adversarial review: Correctness

Verbatim final report of one read-only Opus reviewer on integration branch pc1i-64ba2b (origin/main 658ff4e3..03f994be), 2026-10-10. Repro scripts were in the session scratchpad and are not kept.

Adversarial correctness review of pc1i-64ba2b (`origin/main...HEAD`, 658ff4e3..03f994be). Nothing was changed. Scratch scripts are in `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8ee9a7a0-b6e5-4ea7-af94-1c3edde60d84/scratchpad/review-correctness/`; an `origin/main` export for comparison is in `base/` there.

Ranked findings:

**1. BLOCKER: the loop lines push the regression milestone narrative out of the status-hook window, so on the Claude CLI the narrative is never shown.**
- **Where:** `shiploop_navigator.packet_head` and `render` now print `*_after_status_lines(...)` before `*narrative_lines(...)`. `shiploop_status_hook.narrative_text` reads only `stdout[:WINDOW]` (8000).
- **Why regression is hit:** `test-refine` is in `_GROUP_ENDS`, so every regression packet is a milestone.
- **Reproduced** (`repro_narr.py`; default temp dir, run dir 88 chars, 2 commands):
  - narrative BEGIN at 7905, END at 8430, and `hook.narrative_text(head)` returns None.
  - The head still tells the model "The host's status hook already shows the user this narrative; do not repeat it." Nobody shows it.
  - Per-stage measurement (`heads_n.py`): narrative END at regression is 9368 on the branch against 6510 on base. Every other stage stays under 8000.
- **Tests miss it:** `test/shiploop-narrative.test.py` checks the narrative END only at `init`.
- **Minimal fix:** print `narrative_lines` directly after `status_block` and put `_after_status_lines` after it, in both `packet_head` and `render`. Add a window assertion on narrative END for a loop-stage milestone.

**2. SHOULD-FIX: the prefilled receipt makes a `blocked` result at a loop stage refused before the loop ran.**
- **Where:** `navigator._result_template` (receipt prefill) plus `quality.RECEIPT_REF_LINE` ("keep it") plus `_outcome_shape_lines` ("Any other outcome keeps headline and evidence_refs").
- **What happens:** `quality.check_terminal` and `test_loop`'s check deliberately accept `blocked` with no terminal packet. Then `_check_submitted_evidence` refuses the nonexistent receipt path.
- **Reproduced** (`repro_blocked.py`): at both test-green and static-checks, a `blocked` result with `blocked_by: access` and the printed `evidence_refs` gets "NavigatorError evidence_refs cite files that do not exist: …/tests/nav-…-terminal.json. Write the file or remove the reference."
- **Minimal fix:**
  - Change the line to "keep it when you report done; for blocked before the loop ran, remove it".
  - Or have `_check_submitted_evidence` skip the action's own terminal path when the outcome is blocked and the file is absent.

**3. SHOULD-FIX: the new commit rule is false for in-place (`init`, `execution_mode` "navigator") runs.**
- **Where:** `stage_spec.ITEM_LEFT` / `ITEM_COMMIT_RULE`, which is static text in the document and integrate `develop`, and `navigator._item_commit`, which prints `ITEM_LEFT`.
- **What it says:** "plan-return commits files left uncommitted at the return, so commit nothing yourself."
- **What the code does:** plan-return (`workspace.commit_leftovers`) exists only for `navigator-worktree` runs. In-place mode is a documented route (SKILL.md direct `init` entry).
- **Reproduced** (`repro_inplace.py`, execution_mode "navigator"):
  - At integrate, `helper.py` is listed as "ShipLoop will not commit" and the model is told to commit nothing.
  - After done, `git status` still shows `?? helper.py`. Nothing will ever commit it.
  - The old text ("Commit the ones the product needs") was right for this mode.
- **Minimal fix:** pick the second sentence by `state["execution_mode"]`, keeping the old sentence for "navigator".

**4. SHOULD-FIX: `INNER_CASE_END_STATES` gives the inner stages an open-item route the gates don't support and no later stage carries.**
- **Where:** `stage_spec.CASE_END_STATES` changed for row 5, which targeted system-test-author and system-test. `_inner_case_end_states` copies it into test-author, test-green and regression.
- **The route:** "record it as an open item in the summary with the stage it is due at and continue".
- **Why it is wrong there:**
  - At test-green and regression, done is refused unless every recorded command passes. The unachievable case's command is fixed by the step plan, so "continue" can only be reached by weakening or skipping the test.
  - Nothing reads an inner open item. Product-acceptance's duty carries in only "system-test-author, system-test" items.
- **Minimal fix:** in `_inner_case_end_states`, also drop the open-item clause. The inner route stays "report blocked (access) or revise when the plan is wrong".

**5. SHOULD-FIX (low): `item_scope.commit_scope` / `commit_item` ignore the workspace's `--exclude` paths.**
- **The gap:** `commit_leftovers` filters `_forbidden` and `manifest["excluded"]`. `commit_item` now commits every changed `docs`-class file (`**/*.md`, `docs/**`) without that check.
- **Why it matters:** `references/workspace-lifecycle.md` says `--exclude` is how run-specific transient files such as a `notes.md` are declared.
- **Consequence:** such a file is committed into the run branch's history at integrate. If the model later deletes it, the history row has disposition exclude, so `_fast_forward_ok` fails and a clean-start run falls to the working-tree route.
- **Minimal fix:** in `commit_item`, when the run has a workspace manifest, leave paths matching `manifest["excluded"]` or `_forbidden` out of `chosen`.

**6. NIT (repo rule: Improve mentioned only where a child runs).**
- **Where:** `prompts._REVIEW_FOCUS_LEAD_NONE` reads "Planning review focus (no Improve child reviews this result in this run; …)".
- **Confirmed:** `duty('spec'|'test-strategy', planning_review='none')` prints that line, while the other `_NO_REVIEW_SWAPS` remove Improve wording.
- **Fix:** "Planning review focus (meet these conditions before you submit):".

**7. NIT: the outer stages still offer `revise`.**
- `CASE_END_STATES` (system-test-author, system-test) says "revise or replan", but those stages' outcomes are done, repeat, blocked and replan, with no revise.
- The INNER variant fixed this only for the inner stages. Add an outer variant without "revise".

**8. NIT: S-8 wording.**
- The test-strategy duty's rule "a case that drives it in a browser" for "a page or screen people use" is technology-specific as a rule; a native screen cannot be driven in a browser.
- The system-test-author parenthetical "(a browser or an account this host cannot reach…)" is not labelled "for example".

**9. NIT: the release-stage Improve text contradicts its own reference.**
- `prompts` `release_guard` keeps "Improve may perform deployments…" for `stage == "release"`.
- `environment-lifecycle.md#release-operation-ownership` says any stage-scoped Improve "cannot execute or replay a release effect".

**10. NIT: tidy-ups.**
- `quality.py`: the comment "# Shown once the receipt exists…" now sits above `RECEIPT_REF_LINE` instead of `RESUME_LINE`.
- `test_loop.render_lines` is now used only by tests.
- `_item_commit` still prints "…'s declared changes" although it now commits docs too.
- The Checked-by text for prepare and test-spec says "a docs/shiploop file this stage must have written", which contradicts the new "Written by earlier stages" knowledge line.

**Checked and found clean:**
- **Status block in the 8000-byte window:** it stays inside for every stage's head. I measured all 34 stages with a long temp path and compared against base; step-plan is still the largest at 7582.
- **The receipt prefill is not a bypass:** `check_loop_packet` still requires an existing, complete packet from this action's contract, so a done that cites the template without running the loop is refused.
- **Improve-bind file name:**
  - `packet_path` requires the `skill` key, which `validate` guarantees.
  - Run Review `export.py` reads `-improve.md` by its exact name and ignores the bind file.
  - `metrics.py` and `packet_anatomy.py` handle it.
  - The keepalive scripts don't depend on the name.
- **`stage_lines`, `next_close`, `required_earlier`:** no crash for any `STAGES` entry, `done`, `handoff` or an unknown stage. All `CLOSES` and `STAGE_FILES` keys are in `STAGES`, and the expanded lists are correct.
- **Credential screen:** it still applies to docs commits (`shiploop_git.commit_paths` runs `looks_secret`).
- **Gate claims match the code:**
  - check rows reject ids and min_tests (`normalise_commands`).
  - assumption field sets are exact and the consumer must be a work item.
  - duplicate JSON keys are refused (`store._reject_duplicate_keys`).
  - `red_na` is accepted only on a done test-red.
  - the probe line matches `judge` in probe mode.
- **Placement:**
  - `INNER_CASE_END_STATES` is applied only to inner stages.
  - The improve-commit line moved with the same `planning_reconcile` condition.
  - The implement progress change only alters the display for inline runs.
- **Tests run:** test-loop, packet-completeness, guidance, callback-contract, delegation, run-review, e2e-packet-anatomy, workspace, knowledge, packet-bounds and navigator-contract all pass. status-display has one failure (`progress.html`, `progress-observer.json`, `.progress.lock` written by `next`) that also fails on the `origin/main` export, so it is not from this branch.
- **Not checked:** the template placeholders `<criterion>` and `<exit-code check command>` are not refused by any recording-stage gate, but the earlier `...` / `grep '...'` placeholders weren't either. A leftover check row fails at its first ShipLoop run, not at step-plan or system-test-author. I did not reproduce this.
