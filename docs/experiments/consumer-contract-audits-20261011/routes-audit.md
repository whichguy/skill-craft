## Audit: consumer contract, lens "main tenet and routes"

**Scope.** Read-only. I checked the contract against:
- the code at acf1f026 (= origin/main);
- the inner-loop packet branch `exp/four-part-packet-631117`;
- the three clear slices;
- the two Battleship probe repositories.

**Summary.** I found 1 blocker, 6 majors and 9 minors. The blocker is on the normal path of every isolated run. Most of the majors come from the draft being written against main without the packet branch, and from refusal texts that cannot meet their own 250-character test.

### BLOCKER

**B1. K4's empty lessons commit breaks the follow-up knowledge return on every isolated run where release-verify changes nothing in the home.**
- **What happens.** The return is made at release, before release-verify. The automatic follow-up return is `workspace.follow_up_knowledge_return`, which does `changed = git diff --name-only <candidate head> HEAD` and `if not changed ...: return None`. An empty commit changes no file, so nothing is returned. HEAD has still moved, so the receipt is stale and `protocol.workspace_completion_guard` refuses handoff ("the recorded one is stale ... Run a follow-up return: plan-return / review-return / return").
- **Evidence that this is the normal case.**
  - In both step 1 probes (`battleship-probe-28191c5b`, `battleship-scoring-probe-28191c5b`), the release-verify knowledge commit (cd17a33, 42e27df) touched only `features/README.md` and `outcome.md`, not `environment.md`.
  - Under the contract, both would be empty commits: 2 of 2.
  - E2E runs use `navigator-worktree`.
- **Smallest fix.** In `follow_up_knowledge_return`, when `changed` is empty, proceed if `git rev-list <head>..HEAD` is non-empty and every new commit's subject is a ShipLoop knowledge subject (reuse `LESSONS_SUBJECT` and `knowledge_subject`).
- **Test.** Add a full-runtime test in an isolated run: release-verify with an unchanged home reaches done with no stale-return refusal.

### MAJOR

**M1. Line 1 cannot pass the contract's own test (rule 4 and `test_every_refusal_line_one_...250-character cut`).**
- I substituted paths into the 24 drafted line-1 texts:
  - at a realistic run path (133-character result path, from the implement slice), 20 of 24 exceed 250 characters;
  - at the longest saved path (137 characters), "then run" starts after character 250 in 22 of 24.
- Precedent: `knowledge.check`'s improve-complete text was shortened for exactly this.
- The tenet also asks for "the exact next command with absolute paths" on line 1. That cannot fit in 250 characters: the full `complete` callback alone is about 300. The house practice is the verb only ("then run the same complete command again").
- **Smallest fix.**
  - Line 1: the fix, one absolute path, and the verb.
  - Line 2: the JSON shapes and the "consumers quote it" sentences.
  - Rule 4 should say that line 1 carries the verb, not the full argv. Otherwise the tenet's wording should change.

**M2. An improve-complete refusal on the seed result loops.**
- Rule 4 names `<run>/inbox/<action>-final-result.md` and "run the same improve-complete command again".
- The printed command is `improve-complete --run-dir=.. --action=..`, with no `--final-result`. When no final result was passed, `dispatch` re-checks `child["seed_result"]`, so writing the file and rerunning "the same command" refuses again.
- It triggers when the review changed a living file after the seed passed, and on the test-cases "report revise" exit.
- A second defect on the same route: the Improve packet's list of allowed final outcomes ("done, repeat, blocked or, at OUTER stages, replan") omits revise, which the refusal names as an exit.
- **Smallest fix.** `dispatch` passes `_handoff_gate` the exact next-command string (it has `core`). When final_result is None, line 1 says: "write a final result to <path>, then run improve-complete with --final-result=<path>". Also add revise for test-spec to verify in the Improve outcome list.
- **Test.** Add to `HandoffRouteTests`: a seed refusal on improve-complete whose named exit is accepted through the real CLI.

**M3. `_handoff_gate` sees raw JSON before `_canonical_result`.**
- `_submitted_result` returns the raw record. Every CLI gate runs before `apply()` canonicalises it.
- Rule 2 ("shape on load, meaning at the gate") therefore has the order backwards. A `follows: "R-1"` string, or `test_cases` holding a non-object, would crash the gate as a TypeError instead of giving a refusal.
- Precedent: `_check_submitted_assumptions` canonicalises the field itself.
- **Fix.** `_handoff_gate` first runs `_canonical_result(result, stage=...)` and then checks meaning on the canonical value.

**M4. The contract does not see the packet branch, so ordering on the shared branch will break rendering.**
- `exp/four-part-packet-631117` (3 commits on c52c318e) adds a References block that calls `knowledge.feature_dir`, `FEATURE_LIST`, `_GROUNDING` (private), `earlier_features`, `spec_pin`, and `STAGE_FILES` with README.md.
- It also adds a `_CONSULT` table with `test-strategy.md` and `FEATURE/plan.md "Open"` rows, and `_PRODUCTS` pointers to `FEATURE/plan.md` and `FEATURE/test-spec.md`.
- If the 4b/4c removals land first, every `next` raises AttributeError. That is a crash, not a refusal.
- Section 7.2's packet-text list omits `_reference_global_lines`, `_writer`, `_CONSULT`/`consult_lines`, `_PRODUCTS` and `_builds_on_lines`.
- The branch says "the packet names files by these symbols", while the contract's quote header is `<abs path> ## <heading>:`. One convention is needed: symbols in packets, absolute paths in refusals.
- **Fix.**
  - Set `_CONSULT = knowledge.READS`.
  - Replace `_PRODUCTS`' feature pointers with `handoff_sources`.
  - Merge order on `integrate/refs-consumer-contract`: the packet branch first, then 4a, then the renderer swap, then the 4b/4c removals.
  - Run the section 7 grep on the combined branch, not on main.

**M5. test-spec's CONSUMES omits what its gate checks.**
- `check_test_cases` compares the cases with the item's focused `test_commands` IDs and `criteria`.
- Today the test-spec packet only points at the step-plan result by path (the `_accepted_test_source_lines` locators and the loop resource "accepted step plan"). The contract's own S-6 text says "a path alone fails this clause".
- **Fix.** CONSUMES for test-spec becomes `("follows", "criteria", "test_commands")` (focused rows), and implement also gets criteria. Extend `test_a_cleared_..._packet_holds_every_input` to test-spec.

**M6. Lessons never reach the user's branch on a working-tree return.**
- That route applies files, not commits ("no Git merge or commit").
- The old engine still delivered `outcome.md` as a file there; under the contract, C4 gets nothing and nothing says so.
- **Smallest fix.** On a working-tree route, the handoff packet and the report print the lessons body and tell the user to commit it with that message. Otherwise record it as a known limit in S-11.

### MINOR

1. **Commit-gate ordering on improve-complete.** Handoff refusals whose fix is a living-file edit (no entry, the catalog, Release and rollback) run before `_improve_change_gate`. The edit then needs improve-commit. As in `knowledge.check`, the improve-complete variant should say "if you edit a living file, improve-commit it first".
2. **Two tables for "what a stage builds on".** `CONSUMES` duplicates `stage_spec.Stage.reads`, which already exists on main (S-12). Add a test that each CONSUMES producer is in that stage's `reads`, or derive one table from the other.
3. **system-test-author's requirement check has no quote.** The gate requires `requirement` to have an entry in spec.md, but neither READS nor CONSUMES quotes spec Requirements or `requirement_changes` for it. Product-acceptance likewise gets no requirement text.
4. **Catalog check by substring.** "every ID appears in the section's text" lets ST-1 match ST-10. Use the `(?!\d)` boundary from the entry rule.
5. **Improve packets.** The contract does not say whether the Improve parent and child packets print the READS/CONSUMES quotes. The review judges the same result after a clear, so they should.
6. **Retired entries.** A quoted entry that later moved under Retired or Superseded needs a printed marker. `Entry.retired` is computed but its rendering is not specified.
7. **Completeness after a failed or skipped knowledge commit.** If a commit fails ("the next accepted stage commits it") or a file is skipped by the secret screen, the next stage's `changed_entries` includes the earlier stage's IDs. That stage must then list IDs it never changed.
8. **Old repositories orphan `test-strategy.md`.** The removal test forbids naming it, so a follow-on run's test-strategy stage rediscovers suites instead of carrying them into environment.md. Allow one "if present, carry it into these sections" line, or accept the loss knowingly.
9. **`record_plan_spec` can be skipped.** It is not reached when the plan's knowledge commit raises: `_knowledge_close` returns first. The result is "not recorded", which is acceptable but should be stated.

### Open questions

- **Q1 (STATE_VERSION).**
  - Released ShipLoop (6f86c8cf) is version 4. Version 5 is unreleased: it comes from d7388043, whose pending note is the major `eight-stage-inner-loop.md`.
  - Users' in-flight runs are already refused by 4→5. Bumping to 6 refuses only dev-checkout runs on 5, such as `--resume-run` batches on 28191c5b. Those would otherwise half-continue (contract-mismatched loop receipts, missing fields printed as "not recorded").
  - **Recommendation:** bump once, on the integration branch only. The packet branch does not touch it, so make sure it doesn't also bump to 7.
  - The existing `FRESH_RUN_HINT` does not name `workspace return` for an isolated run, so unreturned run-branch work can be stranded. This is pre-existing and worth a line.
- **Q2 (lessons at discovery too).** Quote at both. After a clear, plan never sees the lessons, and "Open for the next run" is a planning input, so consider plan as well (one `git log` each).
- **Q5 (completeness checks).** Keep them on complete. Note minor 7, and that review edits made after the seed are unchecked.
- **Q6 (outer-stage consumers).** Yes. Work-item IDs and stage names cannot collide, so `expectations.open_assumptions`' `consumer == work_item` filter stays correct.
- **Q7 (failed release-verify commit).** The failure case is fine as a known limit, but the empty-commit path is not a failure case: see B1.
- **Q8 (record file, not a state key).** Fine.

### Checks that held

- `_knowledge_gate` runs on both routes. The test-spec ID check runs only from `_inner_gates` on complete (K9 is correct).
- K11: `_required_excerpt` cuts the work item context at 1200 characters, and open plan assumptions are not printed at step-plan.
- `commit_paths(..., [], allow_empty=True)` exists and does not take staged files.
- Lessons by subject:
  - `knowledge_subject` gives "at release-verify", because it stays in CLOSES;
  - the label is `[a-z0-9-]`, which matches `\S+`;
  - old commits have the same subject and layout;
  - the lookup works on a first run, on a follow-on, and with later commits.
- Clear slices: the first calls after each clear were `next` and then a whole read of the packet file, with no `state.md` or `results/` reads. No ShipLoop refusal happened after any clear, so none of the probes exercised a refusal route. Step 5 should add a cleared slice that hits one handoff refusal on each route.

### Paths

- Contract: `/Users/dadleet/src/skill-craft/.claude/worktrees/b1011z-aaa47e/docs/shiploop-consumer-contract-2026-10-11.md`
- Code checked (`/Users/dadleet/src/skill-craft/.claude/worktrees/b1011z-aaa47e/skills/shiploop/scripts/`):
  - `shiploop_navigator.py`: `dispatch`, `_submitted_result`, `_knowledge_close`, `_improve_change_gate`, `_render_improve`
  - `shiploop_workspace.py`: `follow_up_knowledge_return`
  - `shiploop_protocol.py`: `workspace_completion_guard`
  - `shiploop_knowledge_home.py`: `check`, `commit`
  - `shiploop_stage_spec.py`: `reads`
- Probe evidence:
  - `/Users/dadleet/e2e-runs/20261011/battleship-probe-28191c5b/.shiploop-runs/work-20261011-145021-80a4f9/worktree` (commit cd17a33)
  - `/Users/dadleet/e2e-runs/20261011/battleship-scoring-probe-28191c5b/.shiploop-runs/work-20261011-150423-3ce2b9/worktree` (commit 42e27df)
  - `/Users/dadleet/e2e-runs/20261011/slice-clear-{implement,test-inside,verify}-28191c5b/events.jsonl`
- Packet branch: `exp/four-part-packet-631117` (`_reference_global_lines`, `_CONSULT`, `_PRODUCTS`, `_builds_on_lines`)