# Release A adversarial review: SPEC conformance

Verbatim final report of one read-only Opus reviewer on integration branch pc1i-64ba2b (origin/main 658ff4e3..03f994be), 2026-10-10. Repro scripts were in the session scratchpad and are not kept.

## Spec-conformance review: integration branch pc1i-64ba2b (origin/main 658ff4e3..03f994be)

I changed and committed nothing. My scratch probes are in `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8ee9a7a0-b6e5-4ea7-af94-1c3edde60d84/scratchpad/review-conformance/` (`probe_system_test.py`, `probe_packets.py`, rendered packets `*.md`). I ran six changed suites and all are green: guidance, packet-completeness, packet-bounds, knowledge, e2e-packet-anatomy, callback-contract. The 77 test-loop tests also passed, collected inside my probe run.

### Blockers

**B1. At system-test, the new open-item exit for "a route that fails when the case is run" is refused by the real gate.** Rules broken: "test the route, not the wording", S-14, S-3.
- **The text:** `DUTIES["system-test"]` now says such a case "does not make this result blocked. Record it as an open item … Submit done once every other due check and ShipLoop's rerun pass".
- **Why it can't work:** the case's command was already recorded in system-test-author's `system_commands`. `test_loop.stage_commands` reruns every row of that result, and system-test cannot remove a row.
- **Probe evidence** (`probe_system_test.py`): system-test-author records `test -f page.txt` (check suite), which passes while authoring. At system-test the file is gone, and done is submitted with an open-item summary. Result: `NavigatorError: ShipLoop test run: system-test is not done … [check] test -f page.txt -> exit 1. Fix the code … never change a check … Refused runs for this action: 1 of 7; after that the outer loop takes corrective work items (replan).`
- **Consequence:** this is the v1230 scenario row 5 claims to fix. It now leads to up to 7 refusals and then a replan, instead of continuing.
- **The test that should have caught it** is `test_system_test_treats_a_route_that_fails_when_run_like_a_missing_route`, and it only checks wording. The one route test (`test_a_case_that_cannot_run_is_submitted_as_an_open_item_and_the_run_continues`) covers system-test-author only.
- **Fix, either:**
  - (a) Add a gated exit: a structured open-item list at system-test whose IDs `_test_rerun_gate` skips. Add a route test that submits it through `complete`.
  - (b) Drop "or the route fails when the case is run" from the system-test duty and from the change note until such a gate exists.

**B2. Inner test stages now offer the same open-item route, and their gates refuse it.** Rules broken: S-14 consistency, S-3, "test the route".
- **How it got there:** `INNER_CASE_END_STATES` is derived from group C's new `CASE_END_STATES`. So test-author, test-green and regression now say "record it as an open item in the summary with the stage it is due at and continue".
- **Why it can't work:** these gates need every focused command to pass (or, at test-author, every listed ID to show). A case that cannot run cannot be "continued past".
- **The test-green packet contradicts itself.** Rendered `test-green.md`:
  - line 19: "open item … continue";
  - line 72, the loop's repeat condition: "Stop blocked when … needs a tool, access or authority that is absent";
  - line 261: "revise when it stopped blocked".
- **SKILL.md disagrees too.** "Tests pass or the step stops" says "A check that needs a tool, access or authority that is absent ends `blocked` with `blocked_by`", and "Revise: back to the step plan" says a goal proved unachievable means `revise`.
- **The test pins the wrong text.** `CaseEndStateTests.STAGES` includes the inner stages, so wording-only tests pin the bad wording.
- **Fix:** give the inner stages their own end-state text: unachievable means `revise`, so the step plan reroutes the case and records the open item; `blocked` with `blocked_by access` only when nothing else can proceed. Restrict the open-item wording to the outer stages, and update `CaseEndStateTests`.

### Should-fix

**F1. The integrate commit rule is false in in-place runs** (`execution_mode: "navigator"`). Rules: S-11, S-3, S-6.
- `stage_spec.ITEM_LEFT` / `ITEM_COMMIT_RULE` are printed unconditionally in the document and integrate packets and in `_item_commit`'s "Not committed" notice: "plan-return commits files left uncommitted at the return, so commit nothing yourself".
- An in-place run has no workspace and no plan-return (`workspace-lifecycle.md`: "An in-place run has no workspace"). The in-place handoff commits knowledge files only.
- So an undeclared, non-doc file is never committed, and the model is told not to commit it. Confirmed: the rendered in-place `integrate.md` prints the plan-return sentence next to "Changed, ShipLoop will not commit: fixed.txt, retained.txt".
- `workspace._LEFTOVERS_CLAUSE` is correctly printed only in worktree mode.
- **Fix:** choose the second sentence by `execution_mode`, or have `commit_item` commit leftovers in in-place mode. Add a route test for in-place.

**F2. The commit rule's second half exists as two divergent texts.** Rule: S-12. Both describe `commit_leftovers`:
- `ITEM_LEFT`: "… so commit nothing yourself; delete generated output …"
- `workspace._LEFTOVERS_CLAUSE`: "… so commit nothing for the return except a file it reports as not committed"
- `ITEM_LEFT` drops the credential-skip exception.
- **Fix:** one constant, used by both.

**F3. The `planning_review: none` lead adds a negative Improve mention to stages with no Improve child.** Rule: Improve is mentioned only as a directive.
- `_REVIEW_FOCUS_LEAD_NONE` reads "Planning review focus (no Improve child reviews this result in this run; meet these conditions …)".
- Instead of avoiding it, the change adds it to the allowlist in `shiploop-navigator-contract.test.py` (`PlanningReviewNoneTest`).
- **Fix:** use "Planning review focus (meet these conditions before you submit):" and drop the allowlist entry.

**F4. Reference cards now disagree with the changed behaviour.** Rule: S-3.
- **SKILL.md, skill_na paragraph:** "removing the file from `paths` would leave it uncommitted". `commit_scope` now commits any undeclared docs-class file, and the `docs` class is `**/*.md`. That covers SKILL.md, AGENTS.md, CLAUDE.md, GEMINI.md, agents/*.md and .claude/**/*.md, so the sentence is now false for them.
- **testing-and-documentation.md**, the person-only paragraph: still reads "where the discovery and test-strategy records show this host has no route". The system-test duty widened this to "or the route fails when the case is run". Fix after B1 is decided.
- **SKILL.md, "Tests pass or the step stops":** see B2.

**F5. Change notes are inaccurate.**
- `commit-docs-and-open-item-route.md` says ShipLoop commits "documentation files (README.md, files under docs/)". `commit_scope` commits the whole `docs` path class: `**/*.md`, `*.rst`, `*.adoc`, `docs/**`, LICENSE*, CHANGELOG*, minus test-class paths. That includes scratch `.md` files and skill `.md` files.
- The same note says "system-test treats a route that fails at run time like a missing route", which is not reachable (B1).
- `packet-loop-gates-probe-lines.md` is accurate.

**F6. The test-strategy duty names a technology as the rule.** Rule: S-8.
- The text: "When the request names a page or screen people use, the strategy holds either a case that drives it in a browser …".
- A native, desktop or device screen is not driven in a browser.
- **Fix:** "a case that drives it through its user interface (for example in a browser or on a device), with the tool named and probed …".

### Nits

- **N1.** The release-guard branch `if stage == "release"` in `_improve_prompt` is unreachable: no Improve child runs at `release` (the stage row has no `improve=`). The "may perform deployments" text survives only in `IMPROVE_PROMPTS["release"]`, which no child receives. Delete the branch, or say why it is kept.
- **N2.** `test_loop.render_lines` (`loop_lines` + `rule_lines`) is no longer called by the engine, only by tests (`shiploop-test-loop.test.py` around `CountFloorTests`). Those tests check a composition no packet prints (S-12). Point them at `loop_lines` / `rule_lines`.
- **N3.** The product-acceptance duty says "Carry in the open items an earlier stage recorded (system-test-author, system-test)", but its `reads` is `("intake", "spec", "system-test")`. The packet gives no path to system-test-author's result (S-6). Add it to `reads` or name only system-test.
- **N4.** The system-test duty says "run any this stage can now" of system-test-author's open items. Such a run is never recorded or rerun, so it is not S-9 evidence. Say it is reported, not counted.
- **N5.** `baseline_lines` codifies "ShipLoop does not run them at this stage; record its exit code". This is a recorded-command rerun the model reports by hand, where S-5 says the script should own reruns of recorded checks. Pre-existing behaviour, now printed; consider a script-run probe like test-author's.
- **N6.** S-7: `_after_status_lines` puts the full test command list into the printed active head. The commit message measures head totals up to 8389 bytes, and `PRINT_LIMIT` is not applied to active heads. The status-block window was respected. Note the head now grows with the number of commands.
- **N7.** `navigator.md` (Recovery paragraph) still says recovery rewrites `<run>/packets/<action>.md`. It does not mention the `-improve` and `-improve-bind` files that SKILL.md now names. In the Run Review export (`export.py`, `NO_IMPROVE_PACKET_FILE`), a child stopped before bind leaves only `-improve-bind.md` and would be reported as "left no packets/<action>-improve.md file".
- **N8.** S-13: `packet_anatomy.walk` hard-codes the Checkers case prompt (game, Node.js) instead of reading the case catalog. The new system-test-author route test's summary says "the board renders". Use neutral text.
- **N9.** `REVIEW_FOCUS_CONDITIONS` in the spec and test-strategy duties includes "a missing prerequisite, wrong order or unowned verification in the steps", which does not apply to those producers. This is irrelevant text by the compaction plan's own rule.

### Checked and conformant

- **S-12, review focus:** one constant (`REVIEW_FOCUS_CONDITIONS`) feeds both `PLANNING_REVIEW_FOCUS` and the duties. The spec and test-strategy producer packets each hold one copy (rendered count 1), so there is no repetition within a packet.
- **S-12, commit mechanism:** `commit_item` and `commit_leftovers` both commit through `shiploop_git.commit_paths`; `commit_scope` is the single selection rule `commit_item` and the integrate packet lists share. Runtime paths stay excluded (`lint._runtime_path`).
- **S-4 / S-5:** no new text asks the model to run `git commit`, use heredocs or hand-write JSON beyond the result file. The improve-commit line now sits beside improve-start and is printed once on both delegation routes. The integrate/document text removed "commit the ones the product needs".
- **Inner replan:** removed from inner stages; consistent with `navigator.md` ("replan, outer only") and `test_an_inner_stage_never_offers_replan_and_an_outer_one_still_does`.
- **One supported version:** `INNER_CASE_END_STATES` raises at import if `CASE_END_STATES` drifts, which is acceptable. `stage_files` was removed with no callers left. No compatibility path was found.
- **Improve-bind file name:** `packet_path` matches SKILL.md, the change note, and `packet_anatomy.packet_kind`. The bound-packet test (`test_the_improve_bind_packet_keeps_its_own_file_when_improve_start_prints`) was red, then green.
- **Rows 1, 2, 3 and 11a:** each has a fail-first test through the real `complete` gate (release-verify files, the check row with ids, test-green template accepted, the assumption extra key). The commit messages record red counts and evidence files and cite related commits.
- **Row 13:** implement progress shows "in progress k of N".
- **release-verify:** Done-when and Checked-by now name the knowledge-close gate.
- **Knowledge-home lines:** `next_close` and `required_earlier` are generated from `CLOSES` and checked against the real `knowledge.check` refusals.
- **Templates:** the step-plan template no longer carries README content.
- **Change notes and test registration:** every touched skill has a patch note (shiploop and shiploop-run-review), and the new anatomy test is registered in `suite_catalog.py`.

Relevant files: `skills/shiploop/scripts/shiploop_stage_spec.py`, `shiploop_prompts.py`, `shiploop_navigator.py`, `shiploop_item_scope.py`, `shiploop_test_loop.py`, `shiploop_workspace.py` (`commit_leftovers`, `_LEFTOVERS_CLAUSE`), `skills/shiploop/SKILL.md`, `skills/shiploop/references/testing-and-documentation.md`, `skills/shiploop/references/path-classes.json`, `changes/shiploop/commit-docs-and-open-item-route.md` (all under `/Users/dadleet/src/skill-craft/.claude/worktrees/pc1i-64ba2b/`).
