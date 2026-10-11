## Audit of the consumer contract (lens: KISS, YAGNI, false refusals). Read-only; nothing was edited.

Document audited: `/Users/dadleet/src/skill-craft/.claude/worktrees/b1011z-aaa47e/docs/shiploop-consumer-contract-2026-10-11.md`. I checked it against the plan, the probes journal, the code on HEAD (which contains origin/main), and the saved runs under `/Users/dadleet/e2e-runs/20261010` and `/Users/dadleet/e2e-runs/20261011`: 17 final `work/docs/shiploop` homes and 18 `state.md` files. Every saved run had exactly one work item, so there is no multi-item evidence for anything in the contract. The measurement scripts are in the session scratchpad (`entries.py`, `sections.py`, `cat.py`, `st.py`).

### Blocker

**B1. The release-plan gate on a "Release and rollback" section refuses normal runs and proves nothing (§3.10).**
- **Evidence:**
  - None of the 17 saved `environment.md` files has a section with that name.
  - 7 of 17 already record the standing procedure in `environment.md` under another name: "## Delivery" (battleship-1, battleship-probe, scoring-probe, hello-8stage), "## Delivery (W1 release plan)", "## Release verification", "## Release outcome (W1)".
  - On the current build (28191c5b), the scoring follow-on was shown the `environment.md` section notice 8 times and still wrote "## Targets" instead of "Targets and runtimes". Its `architecture.md` had no level-2 headings at all.
- **Concrete false refusal:** battleship-probe's "## Delivery: Local only: the result is returned to the source checkout's main branch…" would be refused at release-plan.
- **It proves nothing:** the section notice's own fix text says "write 'none' there if it does not apply", and `section_text` returns non-empty for "none". The gate is therefore passed by filler.
- **It misleads earlier:** adding the heading to `SECTIONS` makes the prepare-close notice demand a section that release-plan owns. The model writes "none" at prepare, which then passes release-plan's gate with no procedure written.
- **Smallest fix:** drop the gate and leave "Release and rollback" out of `SECTIONS`. release-plan's duty text asks it to keep the standing procedure in `environment.md` (most models already do, as "Delivery"). The next run's release-plan gets `environment.md` quoted whole (see M1), whatever the heading is called.

### Major

**M1. Quoting by section heading misses most real homes; quote whole files instead (§2.2, §2.4, §5).**
- **Evidence:** I ran the contract's matching rule (title starts with the heading) over the 17 saved homes:

  | File and heading | Homes where it would quote |
  |---|---|
  | environment.md: Targets and runtimes | 5 of 17 |
  | environment.md: Commands | 8 of 17 |
  | environment.md: Skills, Access and accounts | 5 of 17 |
  | environment.md: Platform facts | 7 of 17 |
  | spec.md: Non-functional requirements | 5 of 17 |
  | architecture.md: Stack, Structure, Conventions | 6 of 9 existing files |
  | Harnesses and suites, ID convention, Release and rollback | 0 of 17 |

- **Result:** most quotes would print "this file has no '<heading>' section", so plan assertions A15 and A16 fail in practice on the build being changed.
- **File sizes are tiny:** `spec.md` is at most 5.3 KB, `environment.md` at most 1.8 KB, `architecture.md` at most 1.9 KB.
- **Smallest fix:** `READS = {stage: (files)}`, and quote each file whole, uncut.
  - This removes `section_text`, `_section_spans`, the five-status `ReadQuote` table and the `inside` de-duplication.
  - It no longer depends on how a model spells a heading.
  - The section notice stays as the existing counted nudge.

**M2. `changed_ids` has no observed consumer need and duplicates the spec-commit diff (§3.3).**
- **Evidence:** across all saved runs, implement, test, document and verify made 0 edits to `spec.md` or `architecture.md`.
  - Knowledge commits by stage: after implement 1 (not touching those files), after test, document or verify 0.
  - Every spec or architecture edit came from spec, test-strategy, plan or carry-forward, or from an Improve review commit (11 such commits).
- **Overlap:** at release-verify, the `plan_spec` diff already covers every requirement change after planning, including the Improve and carry-forward edits that `changed_ids` cannot see.
- **Fix:** cut the field, its two gates, its four consumer rows and its report block.

**M3. `requirement_changes` misses review edits and is derivable by the script (§3.1, K9).**
- **The hole:** the completeness check runs on `complete` only, so edits a spec review commits through improve-commit are never listed.
- **Evidence:** saved Improve commits added requirements: pc1i "Spec: add state endpoint and HTTP status rules (R-15, R-16)" and checkers-1 "(R-15)". The plan packet's "added" list would omit them.
- **Derivable:** `changed_entries` already computes the same fact. Asking the model to restate it and refusing on a mismatch costs a turn and adds nothing.
  - A whitespace-insensitive "modified" check also flags formatting edits, such as a follow-on rewriting `- R-1:` as `- **R-1**`.
  - The "retired ID not under 'Retired'" refusal is stricter than the retention loop, which deliberately accepts a mention anywhere.
- **Smallest fix:** record one baseline commit when the run starts. The script derives added, modified and retired IDs (or simply prints `git diff <baseline> -- docs/shiploop/spec.md`, uncut) into the plan and release-verify packets and the report.
  - This replaces the model field and its 4 refusals.
  - It replaces `changed_ids` for release-verify.
  - It also replaces `PLAN_SPEC_RECORD`, if the baseline is taken from the workspace manifest's existing `baseline_commit` or one run-folder record.

**M4. Removing `recent_commits` breaks an owner requirement (§2.6, §3.9).**
- The owner's 2026-10-10 requirement 4 is "reference the last couple of git commits on every step iteration". The contract replaces the last-three window with only the lessons commit.
- That also hides user commits made since the last run (a hotfix or a revert).
- **Fix:** keep the window, and add the lessons quote found by subject when that commit is not already in the window. K13 still holds.

**M5. Three carriers for "not proven yet" (§3.4, §3.6).**
- At verify, `not_covered` ({behaviour, reason}, consumer system-test-author) overlaps the new open items (consumer: a later outer stage). Both overlap product-acceptance's existing `unverified` field (`due_stage`, mostly "handoff" in 14 of 18 states).
- The model must choose between them, and each required key is a refusal waiting to happen.
- **Fix:**
  - Verify records uncovered behaviour as open items only.
  - `not_covered` becomes optional and implement-only, with test as its consumer. Alternatively, drop it together with its Done-when line: there is no evidence that test ever lacked it.
  - Requiring it on every implement step (1 to 4 per saved run) costs a refusal whenever a model omits it.

**M6. The system-catalog gate (every system ID literally in "Harnesses and suites") would refuse most runs (§3.10).**
- **Evidence:** as a proxy I used today's `test-strategy.md` "Harnesses and suites". Only 1 of 15 runs with system IDs had all of them there.
  - The scoring probe listed ST-1 and ST-2 but not ST-3 and ST-4.
  - It also wrote ranges ("TC-1..6, 13, 15"), which a literal-ID check refuses.
  - 5 of 15 runs use TC- IDs as their system IDs, so the gate would make models re-list inner cases as "system cases".
- **Fix:** drop the gate. Use duty text, plus the whole `environment.md` quoted to the next run's system-test-author.

**M7. The contract's own refusal texts fail its own 250-character test (§1 rule 4, §9).**
- The longest saved inbox path is 173 characters. At that length, line 1 is 379 characters (`requirement_changes`), 326 (`follows`), 348 (`test_cases`) and 309 (release-and-rollback).
- `cut -c1-250` drops "then run the same … command again", which is the part the main tenet requires.
- **Fix:** follow `check()`'s pattern: fix, path and command on line 1, and the JSON shape and IDs on line 2.

### Minor

- **m1.** `purpose` and `requirement` are required on every `system_commands` row, including `check` rows (present in 14 of 17 runs) and `regression` rows. A syntax check has no requirement, so this invites filler. Require them only on rows that carry `ids`.
- **m2.** `test_cases` for an item with no focused IDs (a docs-only item, or `test_commands_na`) is not specified. State that a missing key or `[]` is accepted when there are no focused IDs.
- **m3.** The wrong-consumer gate at test-spec and verify refuses "carry-forward" and a later work item (example refusal: "A2 names 'W3'"). Carry-forward quotes every open row and owns `work_items`, so this routes the model to an unrelated outer stage. Allow "carry-forward" as a consumer. No saved multi-item data exists to test this.
- **m4.** The contract's `LESSON_LABELS` collides by name with `shiploop_lessons.LESSON_LABELS`, which means something different ("Key considerations" is explicitly not a lesson there). Rename it.
- **m5.** Small redundancies in `test_cases`: `green` mostly restates `oracle`, and `criterion` repeats the focused command's `criteria`. 31 of 102 saved cases named no R-ID, so expect first-pass refusals on `requirement`. The shape was owner-approved; noted only.
- **m6.** If `follows` is kept, its completeness check ("a changed entry not followed") should be derived by the script, not refused. With whole-file READS on single-item runs, `follows` amounts to every ID, so it is a YAGNI candidate. If kept, check existence only.
- **m7.** The entry parser checks out: 0 of 153 IDs in saved spec and architecture files (124 R, 29 AD) lacked an entry start. It is a second reader of ID syntax beside `_RETAINED`, which only matters if entry quoting is kept.
- **m8.** On an old repository, the harness facts that live only in the old `test-strategy.md` are never pointed at, because the 4c test forbids naming the file. This is acceptable: step 1 showed models open precedent files on their own.

### Tests that cannot fail, or are circular

- `test_each_consumer_packet_quotes_its_fields`, table-driven over `CONSUMES`, is circular if the renderer is also driven by `CONSUMES`: a missing row passes. Use an independent expected table taken from §3.
- `test_a_quoted_entry_equals_the_living_files_entry` should compare against a literal fixture string, not `entry_text`.
- `test_test_stages_and_the_build_phase_quote_their_environment_and_architecture_sections` and `test_the_next_runs_precedent_sections_are_read_by_…` assert `READS` against itself. They are change-detectors; the packet test already covers the behaviour. Cut them.
- `test_a_saved_runs_retire_commit_is_still_a_script_commit_by_the_harnesss_own_matcher` must use a literal saved subject, for example "docs(shiploop): retire build-a-small-single-player-battleship-450445 spec: checked its requirement IDs against the living spec".
- **Missing tests:**
  - heading variants do not refuse (`## Targets`, `## Delivery`, `## Test harnesses and suites`);
  - a two-item fixture for per-item `test_cases` and for gathering results after the item's latest step plan;
  - the 250-character cut using the 173-character inbox path.

### Parts to cut

- `changed_ids`, with its field, gates, `CONSUMES` rows and report block.
- `requirement_changes` as a model field and its four refusals; derive it by script.
- All three completeness checks (this is Q5).
- The release-plan section gate. "Release and rollback" stays out of `SECTIONS`.
- The system-catalog gate.
- `section_text`, `_section_spans`, the five-status `ReadQuote` table and the `inside` rule (replaced by whole-file READS).
- `PLAN_SPEC_RECORD`, `record_plan_spec` and `plan_spec`, folded into one run baseline.
- `not_covered` at verify and test.
- `purpose` and `requirement` on rows without `ids`.
- The two change-detector tests.
- If whole-file READS is adopted: `follows` and `entry_text`, or keep `follows` with an existence check only.

### Kept as sound

- K11, which prints the work-item context whole and quotes the open plan items. The existing uncited-assumption refusal fired in 3 saved runs.
- `lessons`, found by subject, plus the empty commit (K4).
- `test_cases` in state.
- Open items at test-spec, carry-forward and system-test-author. Every observed "Due later" consumer (system-test, owner system-test-author) is a later outer stage.
- `run_label`.
- The removals.

### Open questions

- **Q1 (bump `STATE_VERSION`):** Yes. It is the existing one-version mechanism and one line, and it gives a clean refusal through `FRESH_RUN_HINT`. Otherwise an old run would hit new-field refusals mid-run. `dag_replay` cold-loads only runs it created, so the harness is unaffected.
- **Q2 (lessons at discovery too):** Both stages. Context is cleared between stages, so discovery's packet must carry the lessons itself, at the cost of one `git log`. Keep the last-commits window as well (M4).
- **Q3 (required `surface` key):** No. Step 0 found the test stage opened `test-spec.md` 0 times, so there is no observed consumer. The oracle's wording can name the surface, and a required key is a refusal and filler risk.
- **Q4 (two homes):** Keep the `release` field, with a presence and shape gate. Step 0 shows release, release-check and operations read `release-plan.md` in-run. Drop the living-section gate (B1); the standing procedure is duty text plus the whole-file quote, matching what 7 of 17 runs already do. Same treatment for the system catalog (M6).
- **Q5:** Drop the completeness checks and derive the lists by script (M3).
- **Q6:** Yes, but also allow carry-forward (m3).
- **Q7:** Accept as a known limit.
- **Q8:** Replace the record with a single run baseline if M3 is adopted; otherwise the record file is fine.