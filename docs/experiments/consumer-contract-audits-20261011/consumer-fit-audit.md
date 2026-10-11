Consumer-fit audit of docs/shiploop-consumer-contract-2026-10-11.md. Read-only: nothing was edited and no git command changed anything.

Paths cited below:
- Code is under /Users/dadleet/src/skill-craft/.claude/worktrees/b1011z-aaa47e/skills/shiploop/scripts.
- Runs are under /Users/dadleet/e2e-runs/20261011 and /Users/dadleet/e2e-runs/20261010.

## Blocker

**B1. The lessons do not reach the next run in an isolated run whose release-verify changes no other home file. After this contract, that is the normal case.**
- Evidence:
  - In the step 1 follow-on (`battleship-scoring-probe-28191c5b/work`), the release-verify commit 42e27df touched only `outcome.md` and `features/README.md`. Both files are removed by this contract, so the release-verify stage would change nothing in the home.
  - K4 makes an empty commit in that case. The commit is made only on the run branch.
  - `shiploop_workspace.follow_up_knowledge_return` computes `changed = git diff --name-only <returned head> HEAD` and returns None when `changed` is empty. An empty commit is therefore never returned.
  - A working-tree return carries no commit bodies at all.
  - Result: the next run in the user's checkout prints "none recorded". A9 fails on exactly the step 1 scenario.
- Smallest fix:
  - Return when every commit in `head..HEAD` touches only knowledge paths or is empty (a rev-list test), instead of requiring a non-empty diff.
  - Add a route test: in an isolated fast-forward run with an unchanged home, the lessons commit lands on the source branch and a fresh intake there quotes it.
  - State the working-tree limit, or put it to the owner as an amendment to decision 4.

## Major

**M1. Q4: the system catalog and the release procedure each have two homes.**
- **System catalog.** `purpose` and `requirement` per ST-ID are written twice, by the same stage at the same moment, and both copies are checked:
  - once on the `system_commands` row (3.7);
  - once in environment.md "Harnesses and suites" (3.10).
- **Release.** The two probes' `release-plan.md` files say the same thing:
  - The "Release" line is word for word the same in both.
  - The rollback is the same procedure with a different SHA.
  - environment.md already carries `## Delivery` and `## Delivery (scoring run)` with that procedure.
- **The rollback already has a third home, owned by the script.** In an isolated run, the return rollback comes from `workspace.rollback_lines`, printed by `_return_route_lines(rollback=True)` at release-plan and release-check. `release.rollback` is a model copy of a script fact.
- **release-check cannot do what its duty asks.** `DUTIES["release-check"]` tells it to "correct that file" when the rollback differs. A release-plan result field cannot be corrected by release-check, and the contract names no route for it.
- Fix:
  - Keep `system_commands` rows as the selection only (command, suite, ids).
  - Put purpose and requirement in the catalog only. Quote it through READS: add Harnesses and suites to the product-acceptance row. Gate on each ID having a catalog entry.
  - Drop `release.steps` and `release.rollback`. Add "Release and rollback" to READS for release-check, release and operations.
  - Print `rollback_lines` at release and operations as well.
  - Carry run-specific prerequisites as open items.
  - release-check then corrects the living section, which needs `STAGE_FILES` to add environment.md.

**M2. The mapping from requirement to test has three permanent homes, and the ID high-water mark goes stale.**
- The three homes:
  - spec.md `## Satisfied by tests`, written by carry-forward (`DUTIES["carry-forward"]`: "spec.md: each R-<n> this item satisfied, with its test IDs"). It is present in battleship-scoring-probe's spec.md. The contract's 7.3 never touches this line, and SECTIONS does not include it.
  - The new catalog's per-ST requirement.
  - Each test file's opening lines (`DUTIES["system-test-author"]`).
- Putting test IDs in spec.md also breaks the rule that spec and architecture stay separate.
- The ID convention's "highest ID used per prefix" and each suite's "ID range":
  - copy facts that already live in the test code;
  - are written by test-strategy, which runs before test-spec;
  - are kept current by no gated stage (test-spec has no `STAGE_FILES`).
- Fix:
  - Make the test code the one home.
  - Remove carry-forward's "with its test IDs" duty.
  - The catalog names suites, files and commands, plus the one command that lists the IDs already taken.

**M3. Content of removed files that has no named home and is not in the removal checklist.**
- **(a) The step-plan "Plan note".** `DUTIES["step-plan"]` asks for invariants, failure cases, diagnostics, namespace and schema placement, docs to change, release prerequisites, and the `Confirm by: unconfirmable here` mark. Two stages consume it:
  - implement, condition (b): "a criterion the plan did not mark…";
  - verify: "names outside the planned namespace", "stored data off the planned schema".
- **(b) The plan's own note.** `DUTIES["plan"]` asks for a "Namespace and data map in the plan note", plus independent branches and conflicts:
  - `DUTIES["plan"]` is missing from 7.3 entirely.
  - The navigator's carry-forward line "Explain removals, merges or supersession in the linked plan note" and `DUTIES["carry-forward"]` "Explain each removal… in plan.md" are missing from 7.2 and 7.3.
- **(c) test-strategy.md's allocation table.** About half of the follow-on's file is the "Req | Check | Surface | Due" table. No section of environment.md or architecture.md receives it. plan read test-strategy.md 6 times in step 0, yet plan's READS row holds no test-strategy section.
- **(d) Sub-cases.** `DUTIES["test"]` and `DUTIES["verify"]` write sub-cases into test-spec.md. The contract names no new home for them.
- Fix:
  - The cross-item namespace and data map go to architecture Structure, with an AD-n for each decision.
  - The per-item note goes to the work item's `context` or the step-plan summary, with the duty rewritten.
  - The unconfirmable mark goes in the criterion text.
  - The allocation table is eliminated: it is carried by the item context and `test_cases.requirement`.
  - Sub-cases live in the test code only.
  - Add "plan note" and "Namespace and data map" to the removal grep and the 4c test.

**M4. Open items: missing producers, no way to settle one, and no owner.**
- **(a) Missing producers.** system-test, release-plan and release-verify all record open items by their duties. Both probes' release-plan.md also have an "Unverified at release" line. None of these three stages is in `assumptions.STAGES`, so handoff still reads prose, contrary to 3.6.
- **(b) No settlement.**
  - `assumptions` never updates a disposition.
  - Under the contract, test-spec's due-later TC-18 would stay "open" in `open_items`. In the follow-on it became ST-4 and passed.
  - So product-acceptance, handoff and the report would show a stale open item.
- **(c) No owner.**
  - The open-row shape has `consumer` (a stage) but no person.
  - handoff needs "who reports what", and system-test requires "owner (a person)".
  - `unverified` has `owner` and `due_stage`, which makes two shapes for one concept.
- Fix:
  - Add the three stages as producers.
  - Settlement with no new key: a row is open only until its consumer stage's done result, unless that result lists the row's id again.
  - Add `owner` to open rows at the new stages.

**M5. CONSUMES and READS rows miss consumers that the prompts and step 0 show.**

CONSUMES gaps (the field to add, then the evidence):

| Stage | Add | Evidence |
|---|---|---|
| document | `follows` | It needs "the R-<n> this item changed". implement rarely edits spec.md, so `changed_ids` is usually empty. Step 0: document opened spec.md 3 times. |
| product-acceptance | `requirement_changes`, R entries, `not_covered` | It judges the product against the acceptance criteria and the incoming spec. |
| system-test-author | every item's `test_cases` | Its duty reads "the latest done test-decision record for every relevant completed item". |
| test-strategy | `requirement_changes` | It allocates this run's delta. The follow-on's test strategy is organised by R-9 to R-12. |
| handoff | `lessons` | Step 0: handoff read outcome.md 2 times. |
| release-plan | `system_commands` | Step 0: release-plan read system-tests.md. Its post-release checks reuse the system tests. |
| carry-forward | `requirement_changes` | — |

READS gaps against the stage duties:

| Stage | Add |
|---|---|
| step-plan | environment Targets and runtimes |
| validate-existing | architecture Structure, Interfaces and boundaries |
| document | architecture Decisions |
| plan | environment Harnesses and suites, architecture Real-boundary checks |

**M6. READS quotes almost nothing on the homes that runs on the current build actually write.**
- In both current-build probes (28191c5b):
  - architecture.md has no level-2 heading. It has "Stack:" and "Structure:" paragraphs, then an AD list.
  - environment.md uses `## Targets`, `## Delivery` and `## Readiness (scoring run)`.
- So `section_text` returns None for: Targets and runtimes, Skills, Access and accounts, Stack, Structure, Conventions, Interfaces and boundaries, and Decisions. `entry_text` still finds AD-5.
- Because headings stay a notice, A15/A16 fail on every existing repository, including follow-on runs.
- Fix:
  - On `no-section` for a file that exists, quote the whole file once, with a new status "whole file". The no-cap rule allows this.
  - Or make the headings that READS names a refusal at the writing close.

**M7. `requirement_changes` and `changed_ids` are model-typed copies of a fact the script computes.**
- `changed_entries` (contract 2.3) classifies new, edited and moved-under-Retired, which is exactly added, modified and retired. The gate refuses when the two disagree.
- Fix: the script records both at `_knowledge_close`, from the stage's base commit to after it.
  - This also covers the improve-complete route that K9 leaves unchecked.
  - Keep `follows` model-written, because choosing what an item follows is a judgement.

## Minor

- **m1. CONSUMES scope.** It covers the new keys plus `system_commands` only. Existing hand-offs are not listed: steps, criteria, test_commands, consumer_checks, unverified, expectations. Say so, or the "each consumer packet quotes its fields" test is partial.
- **m2. Catalog gate.** Substring matching passes "ST-1" inside "ST-10". Use the entry-start rule.
- **m3. `plan_spec`.** It caches a git fact: `_planned_record` already finds the commit by subject. Its only unique consumer is the report, since release-verify already gets the R- entries in `changed_ids`.
- **m4. References the grep misses.**
  - "Repository knowledge index" in the plan and operations duties, after README.md is removed.
  - handoff's "durable README/index links".
  - The "Run-wide test strategy source" and "Current planning sources" path blocks point to `results/*.md`, which step 0 found opened 4 times in 7 runs. The contract should decide whether to keep or drop them.
- **m5. Open items left at release-verify.** The script could append them to the lessons commit body as generated text, so the next run does not depend on the model writing `open_next`.
- **m6. The commit window.** Replacing `recent_commits` with one release-verify commit drops two things:
  - the lessons in Improve commits;
  - the owner's 2026-10-10 requirement 4 (look back at the last commits).

  A run that stopped before release-verify leaves its lessons only in Improve commits. Keep the window beside the lessons quote, with duplicates removed.

## Open questions

| # | Answer | Reason |
|---|---|---|
| Q1 | Yes | — |
| Q2 | Both | Discovery reads the commit window today, and the lessons quote has one home. |
| Q3 | Add `surface` | test and verify use it. Setup and teardown belong once in Harnesses and suites, as a suite convention: the Battleship test-spec stated isolation and teardown once for all cases. |
| Q4 | One home each | See M1: the catalog for purpose and requirement, the "Release and rollback" section plus `rollback_lines` for the release. Drop `release` steps and rollback, and the two row keys. |
| Q5 | Make the script record both | See M7. This removes the completeness refusals for those two fields. Keep the existence check on `follows`. |
| Q6 | Yes | Add the settlement rule, the owner field and the three missing producers (M4). |
| Q7 | Accept for a failed commit | The return gap in B1 is not a commit failure: it happens in a normal run, so it cannot be accepted as a known limit. |
| Q8 | Acceptable | Deriving the commit from git by subject is simpler. |
