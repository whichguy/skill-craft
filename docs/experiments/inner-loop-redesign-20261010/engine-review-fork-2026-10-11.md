# Engine review of the 8-stage inner loop (E2E fork, 2026-10-11)

Verbatim final report of one read-only Opus reviewer of origin/main 13d278dd (commits d7388043, 0e36a9af, b2b4cfc8, 8932b849, e4777c78, 13d278dd), checked against docs/experiments/packet-proposals-20261010/ and the release-A guards. Scratch outputs (walk packets, driven item) were not kept.

Read-only adversarial review of the 8-stage inner loop on origin/main 13d278dd. I reviewed d7388043, 0e36a9af, b2b4cfc8, 8932b849, e4777c78 and 13d278dd. be9272a4 never reached a branch; e4777c78 replaces it. I changed nothing in any repo, pushed nothing, and removed the scratch worktree.

**Verdict:** no blockers on main as of 13d278dd. Before e4777c78 there was one: every inner packet said "The loop contract is missing; report outcome blocked", whenever a stage was entered without a transition (a seeded run, a recovery, or my own no-model walk). On 13d278dd the walk writes all 7 contracts and no packet says it is missing. The rest are should-fix and nit items.

**What I ran**
- `packet_anatomy.py --walk`: 42 packets on d3c9eb30, then again on 13d278dd.
- A real-gate drive through the inner fixture (`RunDriver` and `nav.dispatch` complete, not `apply`) for one item with 2 steps and recorded commands: step-plan → test-spec → validate-existing (recorded by script, no packet) → implement S1 (Improve) → implement S2 (Improve) → test → document → verify → carry-forward (Improve) → system-test-author. Packets are in `scratchpad/drv/out/`.
- 19 touched suites run in parallel: all exit 0.
- e2e-apparatus `check_suite --suite all`: 345 tests, 0 failures.
- The serial `run-all --group shiploop` run passed its first 34 suites before I stopped it, as it was too slow.
- Three sub-agents checked the four obligation maps.

## Should-fix
1. **SPEC.md was not moved to 8 stages (S-3/S-10 card and spec disagreement).**
   - `test/shiploop_e2e/SPEC.md` still names `test-author`, `test-red`, `test-green` and `regression` as the gates that replace the planning review under none.
   - The 2026-10-10 cap carve-out still names "the test loop stages and `static-checks`".
   - The 2026-10-05 carve-out lists what starts an Improve child in every mode (system-test-author, release-plan, last carry-forward). It does not mention the new owner decision that every implement step gets an Improve child under `planning_review none` too (`_improve_checkpoint`).
   - The 7-fix-attempt stop now sits inside implement's loop contract (`loops.REPEAT["implement"]`). The carve-out says no cap applies to a loop and names only the test-loop duty and the chain step contract.
2. **The Improve child after each implement step runs with no rerun gate, and the packet says there is one.** `_improve_change_gate` reruns checks only when `child["stage"] == "carry-forward"`. Every Improve packet still prints "commit it; ShipLoop reruns the affected checks." (`shiploop_navigator.py`, the `Changes:` line). That is false at spec, plan, step-plan, test-spec and now after every implement step. A step child's edits are first rechecked by the next step's lint gate and by test and verify. The cost is one bind, start and complete cycle per step, about 25 KB plus 54 KB of packets. I found no measured cost evidence for it.
3. **Stale 17-stage text printed in packets.**
   - Every packet (42 of 42) prints "Inner integrate assembles here, not back into the original branch." (`shiploop_navigator.py`, the workspace lines builder).
   - The plan packet prints "The inner loop already plans, tests, documents, reviews and integrates each item" (`shiploop_prompts.py`, around line 1092). It leaves out validate-existing, verify and carry-forward.
   - The step-sizing refusal in `_check_step_sizing` says "Tests are not a step: test-author writes them before implement ... drop it if test-author already covers it". test-author no longer exists; the test stage writes the tests after implement. This is printed to the model on refusal.
4. **The test packet gives two different case end-state lists.**
   - The Considerations line (`stage_spec.case_end_states`) says: validated, validated another way, or unachievable → revise.
   - The duty text (`shiploop_prompts.py`, around line 1405) says: "...or pending (the result names its later due stage and owner)".
   - "pending" has no gate, and the second list drops unachievable. The release-A guard requires the case end states to match each stage's outcomes.
5. **Refusals with no printed rule (test the route, not the wording).**
   - **revise or blocked with an existing receipt.** `check_loop_packet` requires the receipt in evidence_refs and a loop that stopped blocked. The packet only says "ShipLoop refuses done without it."
   - **"Report outcome revise so the step plan records them"** (`test_loop.loop_lines`, no commands and no reason). `check_terminal` refuses that revise unless a stopped loop exists. Step-plan normalisation probably makes this unreachable in a real run; the walk reaches it.
   - **`_COMMON_GATES` are not printed.** No outcome or summary, a nonexistent absolute evidence path, or a credential pattern: `_checked_line` drops them for every stage with `complete_runs`, which is all 8 inner stages. The test-green and plan maps asked for them to be added.
   - **carry-forward's skill decision.** The template shows only decision and reason. The gate also refuses update or create without `path` and a nonempty `evidence` list, and the packet prints neither field.
   - **Plan gate** (from the plan-map agent): work-item ID pattern and duplicates, `assumptions` required on done, a relative or empty evidence path, and the fix for a dropped R-<n> ("Retired") are not printed.
6. **verify's contract has little room under the budget.** At the walk's 128-character workspace root, verify's contract is 7,943 bytes against `CONTRACT_BUDGET` 9,216, with the root repeated 21 times. With the `_build` stand-ins, verify goes over at a root of about 200 characters (9,552 bytes). `contract_writes` then raises, the transition swallows it, and the packet says "Unavailable ... Report outcome blocked". Step-plan's `command_list_problem` guards only the test stage. A deep worktree path, such as an E2E build directory, would block every item at verify.

## Nits
- `shiploop_quality.py` keeps re-export aliases (`check_loop_packet`, `condition_lines`, `RECEIPT_LINE` and others, "the test loop still imports through this module"). Nothing imports them now: dead shims under the one-supported-version rule.
- `_RENAMED_STAGES = {"select-work": "get-next-work-item"}` points at a stage that no longer exists. A v5 run cannot hold it; v4 runs are already refused by version.
- The status window went from 8,000 to 16,000 characters (0e36a9af). This drops the release-A guard as stated. The rationale is documented: a measured 30k Bash keep, and `PRINT_LIMIT`. Measured on main, 5 of 64 heads end past 8,000: step-plan 10,335, verify 8,820, plan 8,203. None is past 16,000.
- In the step-plan and verify packets the loop's Repeat line and Start command are at about 11.5–12.7 KB, after the status block and narrative. That matches release-A's order but is not in the head.
- Release-verify "Checked by" (map row 6, "kept and extended") is unchanged; the other refusals were not added. Plan map row 174 ("That review checks the result against the Done-when conditions") is still false as written.
- `## Open after release A` items are untouched, as expected.

## Lost obligation-map rows
**None lost.** The new packets keep the old layout, so every kept or shortened row survives, mostly word for word:

| Map | Kept or shortened rows checked | Lost |
|---|---|---|
| plan | 115 | 0 |
| test-green → test | 96 | 0 |
| release-verify | 92 | 0 |
| spec Improve parent | 105 | 0 |

- Release-verify rows 142, 143 and 145 (the test-rerun block) were not rendered in the walk only because its synthetic release-plan recorded no commands. `rerun_lines` still has them.
- Two test-green rows are weaker:
  - Row 127: the "run done_argv until complete or stopped" mechanics are now left to the until-loop card.
  - Row 129: revise is no longer tied to a stopped loop.

## Checked and clean
- **Starting the loop from the printed command.** I ran implement's printed `Start (...)` line verbatim with a shell, for S1 and S2. It returned rc 0 with `status: active`.
- **Contract schema.** All 8 contracts have exactly `workspace, work, exit_condition, repeat_condition, required_trivial_reviews, context{request, scope, authority, environment, resources[{purpose, locator}]}`. Sizes are 4.4–7.4 KB in the drive. The runtime's validator accepts them.
- **The loop is invoked by name.** On Claude Code via the Skill tool `until-loop` (the bundled ADAPTER.md now has `disable-model-invocation: false` and the Contract/Receipt form), otherwise via the card path. Note: the separately installed until-loop 0.7.0 plugin still has `disable-model-invocation: true`, and the catalog pin waits for the owner's go (b2b4cfc8). If the host resolves `until-loop` to that plugin instead of the bundled card, the Skill call is refused. The printed card path and Start command are the fallback.
- **Checked-by is generated from the stage table** for all 8 inner stages, with the loop receipt and the per-stage "it also refuses" or "then reruns" clauses.
- **Receipt and outcomes.** The receipt is prefilled in evidence_refs and kept on blocked. Allowed outcomes match `stage_spec` (no repeat).
- **Improve commit rules.** The Key learnings / Learned-from / Remote change lines sit right after `improve-start` in every Improve packet.
- **verify's commit rule** prints which changed files ShipLoop will and will not commit.
- **validate-existing is a real stage.** In the real drive, the script ran every expectation's check at entry and recorded the stage with no packet when all matched. Otherwise it has a full gate (`check_complete`: rerun every expectation, paths outside the mismatched expectations, `failed_expectations` on revise).
- **STATE_VERSION 5:** a version-4 run is refused with the eight-stage reason, and tests pin it.
- **Step-sizing gate:** the real route refused an uncovered criterion and accepted after the fix.
- **Old stage names:** none in SKILL.md, the references, README or the inner packets, apart from the items above. The run-review aliases are an intentional, documented mapping.
- **Improve wording on stages without a child** (test, document, verify, validate-existing, outer stages): the "advances directly; no Improve child runs" line and the generic Improve schedule sentence are still printed. This was already open as "Phase 2 diet", so it is not new.

## Evidence (scratchpad)
`/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8ee9a7a0-b6e5-4ea7-af94-1c3edde60d84/scratchpad/`:
- `walk8/` — walk on d3c9eb30, the missing-contract case
- `walk9/` and `anat9/` — walk on 13d278dd
- `drv/drive.py` and `drv/out/` — the real-gate drive and its packets
- `par/` — the suite logs
- `maps/` — the map agents' notes
