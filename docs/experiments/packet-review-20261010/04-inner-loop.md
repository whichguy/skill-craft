# Packet review report: inner-loop

Verbatim final report of one read-only reviewer (2026-10-10). Packets: checkers-1, battleship-1, s6-after-spec (ShipLoop 0.58.0, release 1.26.0) and older runs. Scratch analysis scripts were not kept; counts are the reviewer's.

REVIEW: inner-loop packets (baseline, test-author, test-red, implement, test-green, test-refine, regression; static-checks briefly)

Evidence base. I read the real packets in checkers-1, battleship-1 and s6-after-spec, plus the older s6-inside-implement, r1-battleship-grok-none and r2-checkers-sonnet. I also read the engine source and SPEC S-1..S-10. I did not read the references line by line; I checked the packet anchors, which all resolve. The only missing paths are labelled "if present" (SHIPLOOP.md, environment-lifecycle.md, pass-log notes).
- All 18 run docs show every baseline..static-checks visit ending "done". The signal is the refusals (script lines) and the verify records.
- Verify records on disk, all runs: test-author refused 2 of 28 (both r2-checkers-sonnet, ids-missing), test-red 1 of 37, test-refine 1 of 34, test-green 0 of 33, regression 0 of 33.
- Loop-evidence refusals in 16 run docs: 6. The receipt was not listed in evidence_refs 3 times (checkers-1 and battleship-1 at test-green, r3-battleship-sonnet). The terminal packet was still 'active' once (checkers-1 regression). The loop was never run once (s6-after-spec test-green). One message was "terminal packet is not complete" (r1-checkers).
- Size. In checkers-1, 21.1 KB of every packet is made of lines found in at least 80% of its 37 packets. That is 67% of baseline and 48-56% of the others. Consecutive packets are 63-76% verbatim identical. Implement steps 2..N are 85-86% identical to the step before.
- The same blocks recur: generic stage guidance 6.3 KB, Progress paragraph 2.5 KB, workspace-return block 2.6 KB, recovery block 1.0 KB, Code craft 3.7 KB.
- Under S-6, repetition across packets is grounding. I count only irrelevant content within one packet as excess.

STAGE baseline (packets read: 4, 30.9-36 KB)
Accurate: yes. Checked-by (_COMMON_GATES), outcomes and "2 of 2 left" match navigator.py.
Grounded: yes. The ids, the step-plan/test-spec/test-strategy result paths and the item context are all real.
Sufficient: both. The stage-specific text is about 3 KB of 31 KB, and the model still has to find the commands itself.
P-baseline-1 (medium): the packet never lists the commands to run. They are the step plan's test_commands, which ShipLoop knows. It does not locate the initial baseline either. The duty says "Check whether the initial evidence still applies", but the discovery result (checkers-1 discovery evidence baseline.txt) is not named. Only the context-index is linked.
- Run evidence: checkers-1 baseline-item.txt held shell-loop error output, which the next stage's summary admits ("baseline-item.txt held shell-loop error output"). The baseline stage has no script check, so wrong evidence was accepted.
- Fix: in the navigator packet writer, print the stage_commands listing (test_loop._listing) and the discovery result path for baseline. Also list the checkers-1-style fact the stage must record: exit code and tests ran, per command.
P-baseline-2 (low-medium): the template shows "evidence_refs" and "headline" first, with placeholders. s6-inside-implement had 2 refusals for a "duplicate JSON key: 'evidence_refs'" (baseline and test-author). Add "each key once; replace the placeholders" under _result_template.
P-baseline-3 (low): Considerations say "fix nothing here". The generic guidance says a command that does not run what it claims is "a documentation fix made in this stage". Reword.
P-baseline-4 (low): execution-planning.md#baseline-tests-and-migrations is 3.7 KB, mostly migration and planning text, and is pointed to as the baseline-test guidance. Cite only #initial-repository-baseline (6.6 KB).

STAGE test-author (packets read: 4, 37-42 KB)
Accurate: issues. Three defects, listed below.
Grounded: yes. The sources are real.
Sufficient: insufficient. ShipLoop runs the focused commands on done, but the packet never prints them or their IDs. The test-red, test-green, test-refine and regression packets do print them.
P-test-author-1 (high): no command list in the test-author packet.
- Evidence: r2-checkers-sonnet test-author was refused twice with ids-missing, from titles like "TC-10c" against the listed "TC-10". The packet had no 'Test command list'.
- Source: navigator.py around L3490 attaches test_loop.red_lines for RED_STAGE and render_lines/rerun_lines for the others. PROBE_STAGE gets nothing.
- Fix: add probe_lines in shiploop_test_loop.py (commands, IDs, min_tests, the ID-word rule and the count floor).
P-test-author-2 (medium): the duty says "a counted test with every listed ID shown, or a failing test". But judge() red mode returns ids-missing for a failing run that lacks a listed ID. Reword it to "a failing test that shows every listed ID" (shiploop_prompts.py test-author duty).
P-test-author-3 (medium): CASE_END_STATES says "revise or replan when the plan is wrong". Stage_spec._finish gives replan only to outer stages, and the packet's Allowed outcomes lacks it. The same sentence is in test-green and regression. Fix: in shiploop_stage_spec.py, give inner stages a variant without "replan".
P-test-author-4 (low): the duty requires a production placeholder (PROBE_RULE). testing-and-documentation.md#iteration says baseline/test-author/test-red record RED "without production edits". By S-3 the script wins, so fix the reference.

STAGE test-red (packets read: 3, 35-42 KB)
Accurate: yes. Checked-by, the expected-RED rule and the IDs match test_loop.judge and red_lines.
Grounded: yes. The listed IDs and counts equal the step-plan test_commands.
Sufficient: both. The goal and callback are complete, but there is padding (below).
P-test-red-1 (medium): red_na is named in prose, but the template has no field for it. It is a top-level key, allowed only on a done test-red (navigator.py:709). Add an optional line to _result_template("test-red").
P-test-red-2 (low): the listing prints "(at least 9 tests)" under Expected-RED. judge() red mode never applies min_tests; only the accepted-count floor applies. Say so, or drop the annotation here.
P-test-red-3 (medium, tokens): Code craft is 3,687 B (about 10%) in a stage that is test-only and forbids product edits. Drop "code-craft" from test-red's blocks in shiploop_stage_spec.py.
- The RED contract is also stated four times: Checked by, the Test consideration, the duty, and the tail section (about 1.2 KB).

STAGE implement (packets read: 6, 38-47 KB)
Accurate: issues. The progress snapshot is wrong on steps after the first.
Grounded: yes on steps, accepted-step summaries and lint command. No on the progress snapshot.
Sufficient: both. The criteria are not printed, and the exit rules are written for the whole item.
P-implement-1 (medium): on steps 2..N the snapshot says "Current item stages completed (accepted done): ..., test-red, implement" and removes implement from the pending list, while the same snapshot says "Current: implement". Seen in checkers-1 packets 94f3b09e, 378d4244 and e9a119a1 (lines 64-66). A model that has lost context could skip the step. Cause: the progress rendering counts any done history row (navigator.py _progress_lines). Fix: list implement as "in progress (k of N accepted)".
P-implement-2 (medium): "Exit criteria", "finished only when you have confirmed each one" and "rerun every check in one pass" are item-level. The packet is "Step S1 (1 of 4), the only work for this packet", and server tests cannot pass at S1.
- The criteria C1-C5 live only in the step-plan result. The packet does not say which criteria a step covers.
- The instruction to report each criterion's level was ignored in all four checkers-1 summaries, and nothing checks it.
- Fix: print the criteria and use step-scoped wording ("earlier steps: the checks this step covers; last step: all").
P-implement-3 (low): the lint command is the last line of the packet, after Halt. "Tools" cites a non-runnable `shiploop lint --action`. The lint_waivers shape appears only in prose. Prefill it in the template or place it next to the callback.

STAGE test-green (packets read: 3, 37-41 KB)
Accurate: issues. The packet paraphrases the exit condition.
Grounded: yes. The command list, contract path and Start command all exist.
Sufficient: insufficient on the loop contract and callback, and excessive in size.
P-test-green-1 (high by count): the packet requires the receipt path in evidence_refs only in Do step 3. That is at line ~263 of 370, and the template placeholder is generic ("absolute path of each file this stage wrote").
- Evidence: refused 3 times in 16 runs. Line: "list the saved terminal packet in evidence_refs: <run>/run/tests/nav-...-terminal.json".
- Source: shiploop_quality.check_loop_packet.
- Fix: prefill evidence_refs with test_loop.terminal_path(action) in _result_template for loop stages. Add "the terminal packet path must be in evidence_refs" to _CHECK_TEXT["test-loop"] and ["quality-terminal"].
P-test-green-2 (medium): the exit contract is not printed.
- The packet says "until every command in its test command list passes". The contract exit_condition is: one complete iteration after the last edit, every command at exit 0 with the IDs, and the iteration changed nothing. So a first iteration that fixed code needs a second one.
- Evidence: 'status active' (checkers-1 regression), 'loop has not run' (s6-after-spec), 'not complete' (r1-checkers).
- The Start, Receipt and command list sit at the packet tail (lines 369-378), after Code craft and Progress.
- Fix: print exit_condition, repeat_condition and the Start/Receipt lines directly under the callback, for S-6 and S-7.
P-test-green-3 (low): the model must read the 18.9 KB ADAPTER.md "in full once per context" in each of up to three loop stages per item. The first runtime packet already carries the work, done_argv and report_schema.
P-test-green-4 (low): COUNT_RULE has node-specific examples (`--verbose`, spec/tap reporter, TC-4a) in every counted packet, including the Python hello run. They are labelled "for example", which is acceptable under S-8.

STAGE test-refine (packets read: 3, 38-43 KB)
Accurate: yes. REFINE_RULE ("not held to an earlier count") matches accepted_counts, and the rerun listing matches.
Grounded: yes. The sources and the test-decision source are real.
Sufficient: both. Stage-specific text is about 10 KB (duty 1.8, facilities 1.1, test-decision 1.3, pass-or-stop 1.9, Code craft 3.7), which is mostly needed.
P-test-refine-1 (low): the done-when "tests are tightened" is not verifiable; only the rerun is checked. State that the script checks only the rerun.

STAGE regression (packets read: 3, 40-46 KB)
Accurate: issues. One done-when is not checkable.
Grounded: yes. It includes the baseline result and all four commands.
Sufficient: both. Same loop gaps as test-green.
P-regression-1 (medium): the done-when "nothing that passed at baseline fails now" cannot be checked. The loop contract differs from test-green only in the request text, the exit condition ignores baseline, and the baseline is free prose. Either derive baseline-passing commands in script (S-9) or reword. The same loop gaps as P-test-green-1 and -2 apply (the checkers-1 regression refusal is the 'active' status).

STAGE static-checks (packets read: 2, 42-47 KB)
Accurate and grounded: yes. The change inventory is real, and the lint block is labelled advisory. Sufficient: both, with the same receipt and exit-condition gaps. Its quality exit condition ("only trivial findings") is also not restated.

CROSS-STAGE
P-all-1 (medium, tokens): the workspace-return block (plan-return and review-return --keep/--exclude, "unavailable here") is 2,572 B, plus Access-readiness, Requirements-definition and Requested-runtime text, in every inner test stage. All of it is irrelevant there. Gate it on release and handoff stages. That is about 12% of a 31 KB packet with no grounding lost.
P-all-2 (low): implement carries "Delegation ... ask-agent chains" and "service changes" text that does not apply to this stage.
P-all-3 (low): the Implementation constitution and the Code craft rubric overlap.

FIVE FIXES FIRST
1. Loop stages (test-green, regression, static-checks): prefill the receipt in evidence_refs, print exit_condition and repeat_condition, and move Start/Receipt/commands under the callback (P-test-green-1 and -2).
2. test-author: print the focused commands, IDs and the ID-word rule, and correct the "or a failing test" wording (P-test-author-1 and -2).
3. implement: fix the progress snapshot that marks implement completed mid-stage, and print the criteria with step-scoped exit wording (P-implement-1 and -2).
4. Remove "or replan" from inner stages' CASE_END_STATES, add a red_na template line, and add "each key once" (P-test-author-3, P-test-red-1, P-baseline-2).
5. baseline: list the commands and the discovery baseline evidence. Drop code-craft from test-red and gate the workspace-return block off inner stages (P-baseline-1, P-test-red-3, P-all-1).

UNANSWERED
- Which stage the four "a check command is judged by its exit code..." refusals came from. In checkers-1 it was release-plan, so I did not count it here.
- Whether hosts show the model the whole packet. A cat of a 31 KB packet here returned only a 2 KB preview. That bears on the packet's head-versus-tail layout.
- Whether the Until Loop card read is needed.
