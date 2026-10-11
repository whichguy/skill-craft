# Packet review report: release-handoff

Verbatim final report of one read-only reviewer (2026-10-10). Packets: checkers-1, battleship-1, s6-after-spec (ShipLoop 0.58.0, release 1.26.0) and older runs. Scratch analysis scripts were not kept; counts are the reviewer's.

PACKET REVIEW: delivery stages (system-test-author ... handoff, plus Improve children of system-test-author and release-plan)

Method. Read in full: checkers-1 system-test-author and its -improve packet. For the other stages I read the stage-specific part, which is every line not common to all 9 outer packets. In checkers-1 that is 4.7-13.6 KB per packet; the other 25.9 KB (75%) is byte-identical across the 9 outer packets. I diffed those parts against battleship-1 and s6-after-spec, and against the older r1/v1230 packets. Refusals come from the run docs' fidelity.byStage for the 3 newest runs. For the other 11 I used transcript.md, attributed by the last packet printed, which can lag by one stage. Checks that came out clean:
- All 38 reference anchors the packets cite resolve.
- Every CLI verb the packets print exists.
- No unfilled placeholders and no repeated line inside any packet.
- No stale stage names.

Run evidence in my stages. Every stage ended "done" in every run that reached it. Two Grok runs ended BLOCKED: r1-battleship-grok-none at system-test-author and v1230-battleship-grok-none at system-test. The old release/workspace refusals (3 runs on 1.23/1.24) and the r1 release-plan "write the knowledge files" refusals (3) have not recurred in 1.26. The 1.26 packets add the return dry-run text and the rollback recipes, and list system-tests.md among the files release-plan keeps up to date.

STAGE system-test-author (packets read: 14 + 2 Improve; 34.6-38.6 KB, newest 35.9-36.5 KB)
Accurate: yes. The Checked-by gates equal _RECORDED_GATES, and the host_dependent rule equals test_loop.default_suite_drift.
Grounded: yes. The Results list (spec, test-strategy, plan) equals stage_spec reads, and the ids and paths exist.
Sufficient: both. About 3 KB is stage-specific. Another 2.8 KB is the shared test-planning text, and the rest is the shared 6.4 KB stage guidance, progress rules and locators.
P-sta-1 (medium) A check row is refused for carrying ids. The packet says "(same shape as a step plan's test_commands; suite focused, regression or check)". Its template shows ids only on a focused row. The rule is in shiploop_test_loop.normalise_commands. The refusal "a check command is judged by its exit code and takes no ids or min_tests" came 4+ times: r3-checkers-sonnet (system-test-author), s6-inside-implement-k2 and -mtime, checkers-1 (release-plan), r2-battleship-grok-none (stage not attributed). Fix: in shiploop_prompts.py add "a check row carries no ids or min_tests" to the system-test-author text (~line 1608) and to the release-plan text (~line 1701).
P-sta-2 (high) The packet contradicts itself on a case that cannot run. The case-end-states line and the system_commands paragraph say "report blocked with blocked_by access". The unattended rule (S-14) in the same packet says to record an open item and continue. system-test has a person-only-case paragraph and system-test-author has none. r1-battleship-grok-none ended BLOCKED at system-test-author because "TC-16 needs a browser" ("Headless Chrome ... did not return"). Fix: put the open-item route and a "no field, write it in summary and name the due stage" sentence into the system-test-author text, and demote "blocked" to "nothing else can proceed" (stage_spec CASE_END_STATES).
P-sta-3 (low-medium) "select the latest done test-decision record for every relevant completed item: step-plan, test-spec, test-author, test-refine or regression" gives no paths. They are only in context-index.md, which the script could print (S-5/S-6).

STAGE system-test (14; 33.9-37.4 KB, newest 34.8-35.1 KB)
Accurate: yes. The 7-refused-runs cap equals MAX_REFUSED_RUNS, and "(must run: ST-1, ST-2)" matches the recorded ids.
Grounded: yes. It names the worktree commands and uses the real ids.
Sufficient: yes, with excess. The unique part is 8.7 KB, including a 1.1 KB selected-case reconciliation block.
P-st-1 (medium) The person-only rule applies only when "the discovery and test-strategy records show this host has no route". v1230-battleship-grok-none ended BLOCKED at system-test because Chrome existed but never loaded the page ("document stays about:blank"). Fix: extend the paragraph in shiploop_prompts.py to "or the route fails at run time".

STAGE product-acceptance (14; 34.3-38.8 KB, newest 36.5 KB)
Accurate: yes. The unverified shape equals shiploop_unverified, and no run was refused here.
Grounded: yes. It lists open assumption A3 with its ids and quotes the system-test summary.
Sufficient: excessive. The Backchain repair/revise block plus the Until Loop budget one-liner is 2.9 KB, plus 4 pointer lines, in a stage that says "no Improve child runs". backchain-check was run 0 times in the 3 newest runs.
P-pa-1 (medium, tokens) Drop the block from stages that do not start a loop; guidance.BACKCHAIN_STAGES currently includes this stage.

STAGE release-plan (14 + 2 Improve; 36.9-42.7 KB, newest 39.5-40.1 KB)
Accurate: yes. The rollback recipes equal workspace.rollback_lines, and the baseline sha 46d43ee equals workspace.md.
Grounded: yes. The run branch, SHAs and original-checkout path are the real ones.
Sufficient: insufficient on authority and excessive on examples. The unique part is 13.6 KB, the largest of the 9 stages.
P-rp-1 (medium) The done-when "delivery authority is recorded before the plan is accepted" has no inline rule and no script gate. The rules (the request is the grant when it names a target, otherwise ask once, run versus standing scope) live only in delivery-authority.md. The model invented a bullet in release-plan.md ("Delivery authority: the request names only local files"). No notes/environment-lifecycle.md existed in checkers-1. Fix: state in two lines inside the release-plan prompt where to record it and what counts as the grant for a workspace return.
P-rp-2 (low, S-8) All three examples are Salesforce ("App Launcher name and URL path", "permission set", "activating an app or tab").
P-rp-3 (low) The rollback header says "never this run's absolute paths", but the recipes it prints use git -C <absolute source path>.

STAGE release-check (14; 30.3-36.0 KB, newest 33.3 KB)
Accurate: yes. The plan-return dry run matches workspace-lifecycle step 1.
Grounded: yes.
Sufficient: yes. The 1.26 packets add the dry run and the recipes, and no workspace refusal has recurred.
P-rc-1 (low-medium) The text does not say where the confirm command runs before the return. checkers-1 chose the original /work checkout, which is correct. Fix: print source_repo, since workspace.md has it.
P-rc-2 (low) Its only deploy example is `sf project deploy validate`.

STAGE release (14; 30.7-33.9 KB, newest 31.4 KB)
Accurate: yes.
Grounded: yes. The return command is exact.
Sufficient: insufficient on authority and rollback.
P-r-1 (medium) "After review and authorization at this planned final integration boundary" never says who authorizes the return. checkers-1 wrote "Authority: local files only" unprompted. The rollback recipes are printed only at release-plan and release-check (navigator `rollback=stage in (...)`), not here where the return happens. Before 1.25 the stage gave 3 runs "return plan has unresolved path dispositions", and a model hand-edited return-plan.md with sed (r1-checkers). Fix: a one-line "the request's own workspace route is the authority; no push" and the rollback recipes at release.

STAGE release-verify (14; 34.7-38.0 KB, newest 35.5-35.8 KB)
Accurate: issues. "Checked by" lists only the test rerun.
Grounded: yes. The clean-copy path consumer-check, the sha ce8ea9479bf8 and the check rows are real.
Sufficient: insufficient on one gate. The unique part is 9.4 KB.
P-rv-1 (medium, most frequent) "Checked by" and Done-when omit the outcome.md gate. `_checked_line` in shiploop_navigator.py returns early when row.complete_runs, so _stage_gates never adds the knowledge.CLOSES gate: outcome.md, environment.md and README.md. The refusal "Before release-verify is done, write: .../outcome.md" and the follow-up "Write these sections ... '## Learned', '## Key considerations', '## Open for the next run'" occurred in 4 runs: s6-after-spec (twice), s6-inside-implement-mtime, s6-inside-test-strategy, r2-battleship-grok-none. The instruction exists only in a "keeps these up to date" line mid-packet. Fix: append _stage_gates to the complete_runs text, and add a Done-when line.
P-rv-2 (low) COUNT_RULE (about 0.9 KB on test counts and ids) is printed although every row is `[check]` with no ids.
P-rv-3 (low) The packet does not say that ShipLoop's own knowledge commit at release-verify advances the source HEAD by a follow-up return. checkers-1 released at ce8ea94 and the handoff HEAD was 6c66259.

STAGE operations (14; 30.0-33.1 KB, newest 31.2 KB)
Accurate: yes.
Grounded: yes.
Sufficient: excessive. It is 4.7 KB unique and 30 KB in total to produce a two-line "not applicable" in 14/14 runs, which is consistent with S-6.
P-op-1 (low) "Reopen the Repository knowledge index and current observability coverage note" gives no path for the note.

STAGE handoff (14; 32.5-36.9 KB, newest 34.3-35.0 KB)
Accurate: issues. When the return is verified the packet still prints "After review and authorization ... workspace return". "Checked by" omits the receipt gate, workspace_completion_guard "handoff requires a verified workspace return".
Grounded: yes. Open assumption A3, product-acceptance's unverified row (case TC-11, due handoff) and the "Consumer checks (release-verify) ran in a clean copy" line are all real.
Sufficient: insufficient on release content.
P-h-1 (medium) stage_spec reads for handoff is (intake, spec, plan, product-acceptance, release-verify, operations), which has no release-plan and no release. Nothing tells the handoff to give the person the rollback recipe, the kept run branch and worktree, or the knowledge commits. The "Left in your repository: 1 branch" line appears only in the done packet. checkers-1's handoff has no rollback. Fix: add release-plan and release to reads, and a duty line "state how to undo the return (recipes), what ShipLoop left in place, and the final HEAD".
P-h-2 (low) Use the ("release","handoff") branch in navigator.py ~3199 only when no verified return exists.

Improve child packets (system-test-author-improve and release-plan-improve; 46.6 and 50.7 KB on disk)
Accurate: issues (release-plan only).
Grounded: yes. The Step result is embedded verbatim, and the review-file paths and commit-message path are real.
Sufficient: both. 41% (16 KB) and 43% (18 KB) of the bytes are identical to the producer packet the same model read seconds earlier (inline delegation), and there are 42 blank lines.
P-imp-1 (medium) release_guard (shiploop_prompts.py ~2576) is added to release-plan's Improve packet: "Improve may perform deployments, MCP interactions and other release operations". The same packet says "without executing release", and environment-lifecycle.md says "A stage-scoped Improve ... cannot execute or replay a release effect" (S-3). Fix: restrict that sentence to the release stage, or reword it to "assess only".
P-imp-2 (low-medium) Conditional text that never applies is printed: UI/interaction (1.1 KB), repository-local skill (1.1 KB), "author coherent supporting reference material" (1.3 KB), and "State and data assessment" in release-plan (0.6 KB).
P-imp-3 (medium) The pass-count rule is ambiguous. One line says two trivial passes, and the evidence line says "imports the last two passes (the last one when the first pass changed nothing)". It never says to write one review-<n>.md per pass the runtime counts. s6-after-spec was refused ("needs the last 2 review file(s) ... found: review-1.md") and then wrote the two missing files after the fact.

Cross-stage
P-x-1 (low-medium) Consumer-delivery pointers (product-acceptance, release-check, release, release-verify) are printed in every run, but consumer-delivery.md says to read it only when a packet names delivery_contract_version, and that the guard is opt-in.
P-x-2 (low-medium) The plan-return and review-return commands ("To review the final candidate for return", ~2.3 KB) are printed in all 9 stages, including the 6 that say "The return operation is unavailable here". plan-return can commit files to the run branch, so it could be run too early. It was not observed.

Five findings I would fix first
1. P-rv-1: add the outcome.md gate to "Checked by" and Done-when (4 runs refused).
2. P-sta-1: "check rows carry no ids" in system-test-author and release-plan (5 refusals).
3. P-sta-2 / P-st-1: one open-item rule for a case that cannot run, replacing the "blocked" wording (both Grok BLOCKED runs).
4. P-imp-1: remove "Improve may perform deployments" from planning-stage Improve packets.
5. P-h-1 + P-r-1: give handoff the release-plan and release results plus the rollback recipe and left-behind items, and say who authorizes the return.

Could not answer from the files
- The improve-bind packet (revision 41, "Next command (bind the selected Improve card)") is printed to the model but not saved in run/packets/. Only the revision-42 -improve.md is. I could not review it.
- Run docs carry no stage on failures[], so the older refusals are attributed by transcript and may lag by one stage.
