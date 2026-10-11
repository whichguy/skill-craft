# Packet review report: prove-integrate

Verbatim final report of one read-only reviewer (2026-10-10). Packets: checkers-1, battleship-1, s6-after-spec (ShipLoop 0.58.0, release 1.26.0) and older runs. Scratch analysis scripts were not kept; counts are the reviewer's.

REVIEW OF ShipLoop PACKETS: document, skill-assess, skill-validate, static-checks, verify, integrate, integration-verify, carry-forward (+ carry-forward Improve packet)

Read: checkers-1 (all 8 stages plus carry-forward -improve), battleship-1 and s6-after-spec (same stages, diffed), engine source (shiploop_prompts.py DUTIES, shiploop_stage_spec.py, shiploop_navigator.py _checked_line/_item_commit, shiploop_item_scope.py, shiploop_test_loop.py, shiploop_lint.py) and the 17 run docs. Static checks I ran:
- All 3 runs: every absolute path in my stages' packets exists on disk, except the optional notes/, SHIPLOOP.md and environment-lifecycle.md, which are marked optional.
- Every reference "#anchor" in every packet resolves to a heading or <a id> in the build copy.
- No unfilled placeholder appears outside the legit result templates.
- Refusals in my 8 stages: 0 across all 17 runs. Every stage in the 3 newest runs ended "done" first time.
- Run evidence says the packets are sufficient to pass. It says nothing on whether they are lean.

Size facts (checkers-1):
- 21.6 KB of every packet (34 stages) is identical lines: 49% to 72% of a packet.
- A further 6.3 KB "Current stage guidance" block is identical in all stages.
- Code craft is 3.7 KB. It is carried by document, static-checks, verify, integrate and integration-verify.
- The "Test rerun" block is 1.8 KB in static-checks, verify and integration-verify.
- The lint block is 6.0 KB in static-checks and 4.2 KB in verify.

---
STAGE document (packets read: 4, bytes 34.8K-36.0K)
Accurate: yes. The Checked-by clause about "a skill file changed after the step plan recorded skill_na (report revise)" matches item_scope.skill_scope_refusal.
Grounded: issues. It never says which paths the step plan declared, and never says whether skill_na was recorded.
Sufficient: both. Insufficient on file scope, excessive on Code craft.

P-document-1 (medium). Document edits files that nobody tells the model will not be auto-committed.
- Packet: "ShipLoop commits the item's changed files that the step plan's paths declare" (integrate Develop text). Document's packet does not print the declared paths.
- Source: item_scope.commit_item skips undeclared files, and the document stage_spec row has edits={"docs"}.
- Run evidence: README.md or AGENTS.md was outside the step-plan paths in at least 3 of 16 runs. The model then committed by hand:
  - checkers-1: commit 365ab7f, authored by the user with a Co-Authored-By line, not "ShipLoop Workspace".
  - r3-battleship-sonnet, quote: "README.md (not in step-plan paths) committed separately".
  - v1230-battleship-grok-none, quote: "README.md is commit b4b5b4e because it is outside the step-plan paths".
  - r2-battleship-grok-none W2 and v1230-battleship-sonnet are probably the same pattern, but I could not confirm it.
- This breaks SPEC S-4/S-5 (the model runs git commit).
- Fix, script side: in item_scope.commit_item, also commit changed files in the path-classes "docs" class. The stage table already says document edits docs.
- Fix, packet side: document prints "declared paths: ..., files you add outside them are not committed by ShipLoop".

P-document-2 (low). The skill_na Checked-by clause is printed whether or not skill_na was recorded, and it does not say which files are the "skill files".
- The observed list (item_scope.skill_surface "observed": SKILL.md, skills/, agents/, .claude/) lives only in the step-plan packet text.
- Fix: print the clause only when item_scope._skill_na(state, item) is set, and name the surface.

P-document-3 (low, excess). Code craft, 3.7 KB, is carried by a docs-only stage (blocks={"code-craft"} on the document row). Rules 1, 2, 5 and 8 are about code. Replace it with the doc-contract sentence from testing-and-documentation.md#documentation, or drop the block for stages whose edits do not include code.

---
STAGE skill-assess (packets read: 4, bytes 31.1K-31.4K)
Accurate: yes.
Grounded: yes. The item, step plan and last-accepted summary are all real.
Sufficient: excessive. 31 KB for a decision the script could usually record.

STAGE skill-validate (packets read: 4, bytes 29.9K-30.5K)
Accurate: yes.
Grounded: yes.
Sufficient: excessive. About 1.3 KB of stage-specific duty sits inside 30 KB.

P-skill-1 (medium, tokens). In 12 of 12 runs where these stages were issued, both ended as no-skill or N/A.
- Cost: 24 packets of about 31 KB each, about 740 KB.
- The script only skips them when the step plan records skill_na. The 3 newest runs never recorded it (checkers-1's step plan has no skill_na).
- Skipped runs: r1/r2 battleship and s6-inside-implement. All 5 skipped runs are older engine runs.
- Source: item_scope.left_out and _record_not_applicable. skill-assess has no structured disposition field, so the script cannot skip skill-validate after an N/A assess.
- Fix:
  - Add a skill-assess result field such as "skill_change": false. Make navigator._record_not_applicable record skill-validate as N/A when it is false. This is S-5 mechanical work.
  - Optionally have the step-plan packet (shiploop_prompts.py around line 1210) make skill_na the default for tiny items.

P-skill-2 (low). Both packets carry the "Run-wide test strategy source" and "Current item test-decision source" blocks (about 1.7 KB) and the requirements-policy paragraphs (about 1.3 KB). None of that applies to a skill decision. Fix: suppress the block for stages whose reads do not name test-strategy or test-decision.

P-skill-3 (low). The skipped-visit case works. The model sees "skill-assess, skill-validate" in the completed list and a "Last accepted" summary reading "Not applicable to this item ... ShipLoop recorded this stage without running it" (seen in s6-inside-implement). That line is script-written but is labelled "untrusted host report". Fix wording: mark script-recorded rows as script records.

---
STAGE static-checks (packets read: 4, bytes 43.2K-44.0K)
Accurate: issues. One stale sentence in the lint block (P-static-1).
Grounded: yes. The loop contract, receipt, inventory and test commands are real; the Until Loop card, runtime CLI and rubric file all exist.
Sufficient: yes, with an ordering flaw. Judged against the rubric's three questions, the operational content is complete.

P-static-1 (low). The lint block says "ShipLoop gates only implement's done on it".
- Source: shiploop_lint.py around line 1157. GATE_STAGES = stage_spec.with_complete_run("lint-gate") is implement, test-green and regression.
- Fix: say "gates the done of implement, test-green and regression", or derive the sentence from GATE_STAGES.

P-static-2 (low). The Tools text says "(auto-fixing on first entry)" even when the run's lint option is report or off. The text is static in stage_spec.py. Fix: render it from the actual lint mode.

P-static-3 (low/medium). The actionable material is at the end of the file.
- The "Do" list at line 250 says to start the run with "the printed command" and "the Quality loop lines below".
- Those lines (Quality loop, Start, Receipt, Test rerun) sit at lines 422-437, after "Call this when done" (line 360), after the progress boilerplate and after the 6 KB lint block.
- Models still got there: 6 tool calls, 0 refusals.
- Fix: move the Quality loop and Test rerun lines to just under the duty text.

P-static-4 (low, duplication). The Code craft rubric (2.9 KB) is also written to run/quality/code-craft.md and listed as a resource in the loop contract. Keep one, or name the file in the packet.

---
STAGE verify (packets read: 4, bytes 44.9K-45.7K)
Accurate: yes. "Checked by ... reruns every recorded test command" is exactly the test-rerun complete_run.
Grounded: issues. The criteria are not printed.
Sufficient: insufficient on one point, excessive on another.

P-verify-1 (medium). The duty says "ShipLoop runs every command ... each tied to the criteria it confirms".
- The Test rerun listing (test_loop._listing) prints suite, command, ids and min_tests only. It leaves out row["criteria"].
- The Done-when also asks for "every completion criterion confirmed", but the criteria C1..Cn are not printed; the model must open the step-plan result.
- Fix: in _listing, append "(confirms: C1, C2)" from row["criteria"]. Print the item's criteria ids and "Confirm by" lines in the verify packet.

P-verify-2 (medium, unexercised). There is no guidance for a failed, confirmable criterion.
- The packet says "Do not accept the item when a confirmable criterion failed", but it offers repeat/blocked/revise and does not say which one fits a product bug.
- The stage_spec row for verify has no edits, so it is unclear whether verify may fix code. The edits field is never printed in any packet.
- Fix: add a sentence on failure routing, for example "a product defect: fix it, rerun and report done; a wrong criterion: revise". Or print the stage's edits scope.

P-verify-3 (low). The lint block (4.2 KB) is advisory and repeats static-checks' block. The same stale "only implement" sentence appears here.

---
STAGE integrate (packets read: 4, bytes 35.3K-35.8K)
Accurate: issues. Contradictory commit instructions.
Grounded: issues. It does not show which files are declared or undeclared.
Sufficient: both.

P-integrate-1 (high). The commit instructions contradict each other, and the packet gives no file list.
- Develop text: "ShipLoop commits the item's changed files that the step plan's paths declare ... do not write that commit yourself. It names any other changed file: commit the ones the product needs".
- The "Return route" line in the same packet: "plan-return commits files left uncommitted, so commit nothing for the return except a file it reports as not committed".
- The script prints "Not committed ..." only after acceptance (navigator._item_commit stdout). At packet time the model is not told which files are undeclared, even though the script knows both lists (item_scope.changed_paths and declared).
- Run evidence: checkers-1 committed 365ab7f itself, including undeclared AGENTS.md, before submitting integrate. Its summary says "committed on the run branch as 365ab7f". Compare battleship-1 and s6-after-spec, where the script made the "feat: W1 ..." commit and the model made none at this stage.
- Fix:
  - In the integrate packet, print "Changed, declared (ShipLoop will commit): ...; changed, undeclared: ...".
  - Reword the undeclared sentence to "delete generated output; product files stay for plan-return, which commits them" (consistent with the Return route line).
  - Better, P-document-1: have the script commit docs-class files.

P-integrate-2 (medium, tokens). The stage is mechanical: 36 KB for confirming git status.
- Run evidence: 0.1 minutes, 1 call.
- The Code craft block (3.7 KB) is irrelevant. Integrate never writes code as a judgment step.
- Fix: drop code-craft from integrate (blocks=frozenset({"code-craft"}) in its stage_spec row). Consider script-recording integrate when commit_item reports no undeclared files and no chain.

P-integrate-3 (low). Goal text: "integrate the candidate into the working branch". The Done-when and the Deploy line say assembly happens in the execution checkout and the original branch is returned only at final return. The Goal word "working branch" is misleading. Fix the goal in stage_spec.py.

---
STAGE integration-verify (packets read: 4, bytes 37.8K-38.1K)
Accurate: issues (minor).
Grounded: yes. The commands are real and the worktree path is real.
Sufficient: both.

P-iv-1 (low/medium). The Pass-or-stop block says "same check still failing after 3 genuine fix attempts -> revise". The Test rerun block says "at most 7 refused runs, then ... (revise)". Two different caps for the same outcome, with no explanation. Say which counts what, or unify.

P-iv-2 (medium). "Shared interfaces are checked" is a Done-when, but nothing names the shared interfaces. The packet lists the spec and the integrate result as reads, but not the step plan and its interfaces. Fix: add item:step-plan to the stage's reads, or print the files from "Work item context" as the interface set.

P-iv-3 (low). The reconciliation paragraph names "DOM structure alone cannot close a selected rendered interaction". It is UI-specific wording in a generic stage (SPEC S-8 allows examples; it should be labelled "for example").

---
STAGE carry-forward (packets read: 4, bytes 37.97K-38.4K) and its Improve packet (3, 52.0K-52.4K)
Accurate: yes. The Improve statements match _IMPROVE_STAGES and stage_spec.improve="last-item". The backchain-check line, improve-start/commit/complete commands, the 9,216-byte contract cap and the references all verify.
Grounded: yes.
Sufficient: both.

P-cf-1 (medium). Done-when 2 is "learnings and durable knowledge are recorded outside run notes". No packet text names the destination file, and the script does not check it. carry-forward is not in knowledge.CLOSES.
- carry-forward.md says "Record in the result summary and a linked run note", which seems to contradict the Done-when wording.
- Run evidence: checkers-1 recorded the learning only in the result summary. evidence_refs was spec.md, which carry-forward did not edit. No "knowledge after carry-forward" commit exists. The same lesson surfaced later in outcome.md at release-verify.
- battleship-1 wrote docs/shiploop/environment.md. s6-after-spec wrote docs/shiploop/test-strategy.md. So 2 of 3 complied.
- Fix: the packet names the target files, for example "append learnings to docs/shiploop/environment.md or the feature outcome.md". Add carry-forward to the knowledge gate if the Done-when is meant seriously. Or reword the Done-when to match the reference.

P-cf-2 (medium, tokens). The Backchain and loop-budget block is 5.2 KB (14% of the packet).
- It covers the Backchain audit and repair route, the Until Loop state budget and a measuring one-liner.
- 13 of 14 runs had an empty queue after W1.
- Add a condition: "Only when you supply work_items". Alternatively, print the block only when the queue is non-empty or when a candidate exists. The test-facility paragraph (0.9 KB) is likewise conditional.

P-cf-3 (low). The result template lacks the work_items shape. The text says "Optional work_items replaces the queue", but the shape {id,title,context} appears nowhere in the carry-forward packet. _normalise_work_items refuses "work item has unsupported or missing fields". Replan's template shows the shape (navigator ~3573). Unexercised so far. Fix: reuse that line.

P-cf-4 (Improve packet, medium). The packet is 52 KB, 40% identical to the producer packet.
- The stage-specific part is the end-of-work focus plus Code craft (about 4.0 KB).
- Conditional paragraphs follow that fit an end-of-work code review poorly:
  - UI/actor-interaction planning (1.2 KB)
  - "planning-producing candidate" (0.8 KB)
  - skill-selection candidate (0.7 KB)
  - state/data assessment (0.5 KB)
  - test-plan review (1.3 KB)
  - These total about 4.5 KB.
- The Done-when shown to the reviewer is the producer's queue/learning condition, not the end-of-work review's real objective (code and tests across items).
- Fix: in improve_prompt for last-item carry-forward, include only the paragraphs whose guard matches the candidate, and add the review's own Done-when.

---
The five findings I would fix first
1. P-integrate-1 plus P-document-1 (the same S-5 breach: model-written commits for undeclared docs). Script-side: commit docs-class files in item_scope.commit_item. Also print the declared and undeclared lists at integrate.
2. P-skill-1 (24 near-empty ~31 KB packets in 12 runs). Add a structured skill-assess result field so the script records skill-validate as N/A, and make skill_na the default for small items.
3. P-verify-1 and P-verify-2: print the item's criteria and the criteria-to-command tie in verify. Add failure routing for a failed criterion.
4. P-cf-1: give carry-forward a named durable destination and a check that matches its Done-when (checkers-1 recorded nothing outside the summary).
5. P-cf-2 and P-cf-4: condition the 5.2 KB Backchain block on a non-empty queue. Trim conditional paragraphs from the end-of-work Improve packet.

Unanswered from the files:
- Why exactly the checkers-1 model committed at integrate (no transcript). My explanation (undeclared AGENTS.md plus the "commit the ones the product needs" text) is an inference.
- Whether `choices.skill_required` (accepted at document by _normalise_choices) has any consumer. It is not mentioned in any packet and I found no reader. It looks like a dead field; that is a possible "one supported version" cleanup.
- Whether the end-of-work Improve review ever challenges the learnings recorded by carry-forward.

Key paths (all under /Users/dadleet/src/skill-craft/.claude/worktrees/rr23-9f8c87/skills/shiploop/scripts/): shiploop_item_scope.py (commit_item, skill_scope_refusal), shiploop_navigator.py (_item_commit, _checked_line, _record_not_applicable), shiploop_test_loop.py (_listing, COUNT_RULE), shiploop_lint.py (advisory sentence), shiploop_stage_spec.py (rows), shiploop_prompts.py (DUTIES). Scratch analysis: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8ee9a7a0-b6e5-4ea7-af94-1c3edde60d84/scratchpad/pkt-review/.
