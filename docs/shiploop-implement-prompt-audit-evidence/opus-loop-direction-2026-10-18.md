# Loop-direction plan review

Verified served model: `claude-opus-5-5`; effort: `xhigh`; fallback: false; process/envelope exit: 0.

The read-only consultation began before the owner requested main re-anchoring. It inspected integration c70a33f4; its architecture advice was evaluated against main by the coordinator. Integration code status is not main code status.

Transcript: `/tmp/shiploop-loop-direction-20261018/transcript/20261018T143549Z-36286`. Exact envelope is retained beside this file.

I didn't edit anything. My plan-mode tools didn't include a way to write the plan file, so the full review is below.

**Decision: adopt B, with five corrections. Don't do C.** The pinned source shows the duplication is in the wording, not in the loops. The producer loop and the Improve loop end on different conditions and do different jobs. Nothing in the evidence supports removing or merging one.

## 1. Goal
Shorten the inline implement step's Until Loop wording and keep the producer and Improve phases separate. The step's scope, authority, repeat/stop rules, recovery locators and D4/D5 must survive unchanged.

## 2. Material issues

**M1. The duplication is real, and it is in the text (answers Q1).**
- Work (`WORK_STEP`, `shiploop_loops.py:100-103`) says "until each requirement assigned to this step is satisfied and none of the others is broken".
- Exit 1 (`STEP_CRITERIA_CONDITION`, `shiploop_stage_spec.py:76`) contains the same clause word for word, plus "shown by a command or file after the last edit, and no later step's work is in the change".
- So the D4 clause prints twice in one argument. That also breaks the Until Loop rule that "until" clauses stay out of Work (`until-loop-nested-20261017/SKILL.md:164`).

The loops themselves are not duplicates:

| | Producer loop | Improve loop |
|---|---|---|
| Review gate | `TRIVIAL_REVIEWS` implement=0 (`:159`) | gate 2/3 (`shiploop_standalone_improve.py:615-618`) |
| Ends when | first pass whose exit is satisfied; a non-trivial final report is accepted (`:719`) | a pass with unchanged content |

The run failures were about validity: future artifacts, an invalid procedure, a source-grep proof. Neither loop caught them, and the Improve passes are labelled self-passes (`shiploop_navigator.py:6839`). So the evidence says "fix the step's proof and procedure inputs". It says nothing about how many loops to run. B saves about 250 characters against a 16k head, so justify it by keeping Work and Exit separate, not by size.

**M2. D4's placement is pinned by tests.** Both `test/shiploop-loops.test.py:212-214` (T12) and `test/shiploop-delegation.test.py:625` (T11) assert the D4 phrase is in `work` ("in the owner's D4 words"). B moves it so it lives only in Exit 1. Exit 1 already holds the words exactly, but this changes where an owner decision lives. Record it as an owner decision and update both tests; otherwise "keeps D4" isn't true.

**M3. B could interact with the §3.3 change and drop the regression clause.** The §3.3 rewrite of condition 1 (plan lines 391-392) leaves out "none of the others is broken" and "no later step's work is in the change".
- If B removes the clause from Work and §3.3 lands as written, "none of the others is broken" disappears from the frozen contract.
- `context.scope`'s "Preserve every other change" covers files, not behaviour.
- Fix: keep both clauses in Exit 1, exactly once, whichever wording wins.

**M4. B's example Work drops frozen content.** "Carry out the Step S1 directive and Method in …/A17.md" loses three things:
- the criterion, R-n and AD-n IDs, which T11 asserts, including that other steps' IDs are absent;
- "Write no tests", which appears nowhere else in the contract;
- "start no later step".

This matters because the runtime and its recovery hooks show `work`, `conditions` and `context`, not the ShipLoop packet (SKILL.md:225-233). Work has to carry the assignment and its exclusions on its own.

**M5. The Improve side doesn't yet match B's claim.** The step block does reach Improve (`improve_handoff_text`, navigator `:6409`). But `IMPLEMENT_STEP_REVIEW_FOCUS_HEAD` (`shiploop_prompts.py:2501-2538`) has no bullet for evidence adequacy or procedure validity. Its first bullet, "misses a criterion as the spec's R-<n> states it", invites judging whole-R-n completion inside a step review, which is the opposite of the constraint.
- Fix: reword that bullet and fold it into the bullet §3.5 already plans to add (plan line 545), rather than adding a separate one.
- Size risk: the focus prints before the Commit section, and the comment at navigator `:6526-6527` says the improve-commit line ends inside 4,500 characters with "6 characters to spare". Any extra focus text will break that bound. Following the owner's rule, raise the bound rather than trim, and run the delegation test.

## 3. Problems with "anchor all delivery items concretely … above" (Q2)
- **"above"** has nothing to point to in the runtime packet. SKILL.md:188 forbids exactly this kind of relative reference ("the directory above").
- **"anchor"** already has two meanings in the plan: "Anchored in" means grounding in R-n/AD-n, and "code anchors" means locators. "Anchor concretely" invites file:line citations as proof of completion, which is the Battleship source-grep failure (T36).
- **"all required delivery items"** can be read as the whole item, which is the chess future-artifact failure (§0.1 row 1).
- **"until … can"** puts a stop condition inside Work and measures capability rather than an observation.

Suggested wording, which also adds the observation requirement to D4:
- Work: "Implement step S1's assigned criteria (C1, C2), within R-1 and AD-1, following the Method in <abs packet>. Write no permanent tests; start no later step."
- Exit 1: "each criterion assigned to this step is shown working at the boundary it names, by a check or inspection after the last edit; none of the others is broken; no later step's work is in the change."

Use one home for it. Don't add a paraphrase to the Step block; `DONE_WHEN_LOOP` already points there.

## 4. Does the directive need a frozen value? (Q3)
No new schema is needed. Today the contract freezes `work`, `exit`, `repeat`, `context` and the review count, and `check_loop_packet` compares each against the copy rebuilt from state (`:691-698`). T12 already shows the anchors come from state, not from the living HOME files.
- The packet file is rewritten on every emit and includes content from HOME files, so it can serve as the Method locator but not as the authority for the assignment.
- The immutable accepted step-plan result is already listed in `context.resources` (`:423-425`).
- So the minimal frozen value is what exists now: IDs and exclusions held by value in Work. Build any directive text from state only: no HOME text, sizes, commits or status.
- If you swap `Do duty items {items}` for "the Method": `_duty_items` currently guarantees Work only cites items the packet prints. You need an equivalent, such as T22's missing-heading check on `## Method`. The navigator contract test (`:1251-1255`) pins `Do duty items {items}`, so it will need updating.

## 5. Smaller corrections
- The example's receipt path is wrong: the code writes `loops/<id>-terminal.json` (`terminal_path`, `:249-251`), not `-receipt.json`. Plan §3.4 has the same error.
- In the directive's "Record …" sentence, put the current observation first and the code locator last, matching the `criterion_evidence` fields, so a locator doesn't read as evidence.
- "this packet's Method" is fine inside the Step block but not in Work.

## 6. Open questions to check before implementing
1. Does the owner accept the D4 words living only in Exit 1?
2. Has the §3.3 rewrite of condition 1 landed on integration? Merge order matters for M3.
3. Can an implement-step Improve route a procedure defect to revise? `shiploop-route.md:273` only mentions a revised step result "when the review changed a decision". If it can't, B's procedure-validity check has no way out.
4. How much headroom does the 4,500-character Improve window have after the focus edit?
5. Does the recovery packet print `context.resources`? It is likely; `context` is a packet key.
6. To measure overhead: how many iterations (`action_number`) did producer loops take in the retained runs, and how many Improve passes?

## 7. Order of work (Q4: sites and smallest checks)
1. Record the owner's decision on where the D4 words live, then reconcile the §3.3 Exit 1 wording so both clauses stay.
2. `WORK_STEP`: remove the "until…" clause; keep the IDs, "no tests", "no later step" and the locator. Leave `REPEAT_STEP`, `TRIVIAL_REVIEWS`, `_improve_change_gate` and the standalone gates unchanged.
3. `IMPLEMENT_STEP_REVIEW_FOCUS_HEAD`: reword the first bullet and add evidence/procedure checks, merged with the §3.5 bullet. Raise the 4,500 bound if needed.
4. Hermetic checks:
   - **A1** (update T11/T12): Work has the step's own IDs only, plus "no tests" and "no later step", and no "until"/"above"/"below". Exit 1 has both clauses. The D4 phrase appears once across Work and Exit.
   - **A2:** T12's rebuild-equals-entry still passes after HOME edits.
   - **A3:** T31 (ask-agent Work unchanged) still passes; inline repeat is still `REPEAT_STEP` and the review count is still 0.
   - **A4:** the Improve handoff contains the step block, and the commit line stays inside its window.
   - **A5:** T33 still passes: Improve import reruns the Proof on a changed candidate and reuses it on an unchanged one.
5. Measure cost only from the receipts in step 6 of the open questions, and only with a paired pilot (T32). Don't infer it from character counts.
