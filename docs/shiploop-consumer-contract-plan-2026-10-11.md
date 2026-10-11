---
Execute: ask
---

# Plan: ShipLoop's artifacts, designed for their consumers

Owner directive (2026-10-11, general): every outcome is produced because a named consumer wants to read it, in the form and at the moment that consumer reads it. An output with no consumer is not produced.

This plan applies that directive to what ShipLoop leaves in the user's repository (Layer 2 of `docs/shiploop-artifact-flow-2026-10-11.md`) and to how one stage hands work to the next. ShipLoop's own state management (the run folder) is a separate topic and stays as it is, except where a hand-off field is added to it.

Revision 2 (2026-10-11): every removed artifact, every new field and every owner decision is now anchored to the code that consumes it today and the code that will consume it after the change (section 3). Every assertion in this plan is traced to the step that builds it and the test that proves it (section 8). Two assertions in revision 1 had no plan and are fixed:
- "Architecture decisions that touch the paths an item changes" had no mechanism: an `AD-<n>` entry records no paths.
- "Lessons ride in the release-verify commit" relied on `outcome.md`, which this plan removes.

## 1. Why

The artifact-flow audit (66 claims checked, 23 corrected) found that Layer 2 mixes three jobs:
- the hand-off from planning to implementation inside one run;
- the memory a later run needs;
- a record for people.

Only the memory job is served well by repository files. Implementation already consumes structured fields in the run's state, which scripts check and quote into packets: `work_items`, `criteria`, `steps`, `paths`, `test_commands`, `expectations`. The markdown copies restate those fields. Several Layer 2 files have no reader the engine depends on. Meanwhile, what a later stage most needs travels as a path to prose that nothing checks.

## 2. The consumers

| Consumer | Reads when | Needs | Form it reads |
|---|---|---|---|
| C1 ShipLoop's scripts (the gates) | At a stage's done | Criteria, test case IDs, commands, expectations, paths | Typed fields, checked when written |
| C2 The next stage in the same run, with context cleared | At the start of its packet | Only its inputs: binding decisions, criteria, open items, uncovered behaviour, commands | The entries it needs, quoted into the packet by the script; stable living files by path for anything else |
| C3 The implementation stages (implement, test, verify) | Per work item | The item's criteria tied to test IDs and commands; the requirement and decision entries the item follows | The same quoted entries, chosen by an explicit citation in the step plan (not by guessing from paths) |
| C4 The next run on the same repository, cold, days later | Intake and planning | What must hold, how to build and run it, why it is built this way, what the last run learned and left open | Three living files with fixed headings, plus the last run's lessons quoted into intake |
| C5 The owner or a reviewer | After a run | What was done, what passed, what is open | One readable report per run |
| C6 The E2E harness and Run Review | After a run | Counters and records | The run folder and the repository's history |

## 3. Every artifact, anchored: today's consumers, its disposition, and its consumer afterwards

Symbols are in `skills/shiploop/scripts/` unless a path is given. "Incorporated" means the content moves to a named home and that home has a named consumer. "Eliminated" means no consumer remains and nothing replaces it.

### 3.1 Kept (C4 memory), with changes

| Artifact | Consumed today by | After the change | Step |
|---|---|---|---|
| `docs/shiploop/spec.md` (living contract, `R-<n>`) | `knowledge_home.check` retention loop (`_RETAINED`); `CLOSES["prepare"]`; `grounding()` "living spec"; the harness's `run.knowledge_facts`; the spec, plan, verify and release-verify prompts | Unchanged as a file. New: the script quotes the `R-<n>` entries an item implements into that item's implement, test and verify packets (C3), chosen by the step plan's `follows` (3.3) | 4a |
| `docs/shiploop/environment.md` (`SECTIONS`: Targets and runtimes, Commands, Skills, Access and accounts, Platform facts) | `STAGE_FILES` (ten stages); `CLOSES` prepare, release-plan, release-verify; `grounding()`; the inner prompts' "## Commands" lines | Gains two sections from `test-strategy.md`: "Harnesses and suites" and "ID convention". Same consumers, plus the test-spec and test prompts that today point at `test-strategy.md` | 4b |
| `docs/shiploop/architecture.md` (`AD-<n>`) | `_RETAINED`; `CLOSES["prepare"]`; `STAGE_FILES` plan, step-plan, implement, carry-forward; `grounding()`; `_knowledge_lines` duty sentences | Gains "Real-boundary checks" from `test-strategy.md` (under "Interfaces and boundaries"). New: the script quotes the `AD-<n>` entries an item follows into its inner packets, as for `R-<n>` | 4a, 4b |

### 3.2 Removed: each one either incorporated or eliminated

| Artifact | Consumed today by | Disposition | New home and its consumer | Step |
|---|---|---|---|---|
| Feature `features/<slug>/spec.md` | `CLOSES["prepare"]`; `knowledge_home.retire` and `_missing_ids`; `grounding()` "feature spec"; `shiploop_progress_data` row "feature-spec"; the spec prompt and loop work text | **Incorporated** | The changes this run makes to requirements become a spec result field, `requirement_changes = {added, modified, retired}` (lists of `R-<n>`), checked at spec done against the living spec's IDs (same reader `_ids`). Consumers: the plan packet (quoted, so the plan covers each), the release-verify packet (quoted, so the outcome is judged against them), and the report. The historical record of what was planned is the living spec at the commit recorded at plan done (next row) plus git history | 4a, 4c |
| `Spec: … @ <sha>` first line of `plan.md` (`spec_pin`) | Printed into the plan packet by `_knowledge_lines`; parsed by nothing | **Incorporated** | The script records the living spec's commit in state when plan is accepted, with no model involvement. Consumers: the report, and the release-verify packet ("the plan implemented spec.md as of <commit>") | 4c |
| `plan.md` | `CLOSES["prepare"]`, `CLOSES["test-spec"]`; `STAGE_FILES` plan, step-plan; loop work text for step-plan; carry-forward writes "## Open"; the system-test-author prompt reads "## Open" | **Incorporated** | The plan's content already lives in state: `work_items` (plan), and `criteria`, `steps`, `paths`, `test_commands` and `expectations` (step-plan). The scripts consume these today. "## Open" items move to the open-items list (3.3), which the system-test-author packet quotes. The human-readable plan is the report (Decision 3) | 4a, 4c, 4d |
| `test-spec.md` | `expectations.check_test_spec_ids` (the test-spec stage's done gate, called from the navigator's inner gates); loop work text for test-spec and test; `loops` resources "this item's test spec"; test-spec, test and verify prompts; progress row | **Decision 2** | Option A (recommended): a test-spec result field `test_cases = [{id, criterion, requirement R-<n>, oracle, red, green}]`. `check_test_spec_ids` is rewritten against state with the same rule (every case listed by a focused command, every focused ID has a case). The test and verify packets quote the item's cases; the report shows them; the tests carry the IDs in code. Option B: keep the file as the one per-run file because a gate reads it, and move it to the run folder (it serves the run, not the next run) | 4a or 4c |
| `system-tests.md` | `CLOSES["release-plan"]`; `STAGE_FILES["system-test-author"]`; read by no stage (the system-test stage runs the `system_commands` field) | **Incorporated** | The catalog is the `system_commands` field (existing; consumed by the system-test gate). A case's purpose and its requirement become two keys on each row (`purpose`, `requirement`), checked at system-test-author done. Consumers: the system-test and product-acceptance packets (quoted) and the report | 4a, 4c |
| `release-plan.md` | `CLOSES["release-plan"]`; `STAGE_FILES["release-plan"]`; the release-check prompt compares the review-return report "with the rollback in release-plan.md" | **Incorporated** | The release plan's steps and rollback become a release-plan result field, `release = {steps, rollback, prerequisites}`. Consumers: the release-check packet (quotes `rollback` for the comparison it already makes), release and release-verify (quoted), and the report | 4a, 4c |
| `outcome.md` | `CLOSES["release-verify"]`; `knowledge_home.learnings` reads its "Learned", "Key considerations" and "Open for the next run" sections; `commit()` writes them into the release-verify commit body; `check()` refuses empty sections | **Incorporated** | A release-verify result field, `lessons = {learned, considerations, open_next}`, checked non-empty at release-verify done (the same rule `check()` applies today, moved to the result). `commit()` writes it into the release-verify knowledge commit body as now. Consumer C4: the next run's intake packet quotes the newest commit whose subject is a release-verify knowledge commit, found by subject, not by a three-commit window (fixes audit row 7). Consumer C5: the report | 4a, 4c |
| `test-strategy.md` | `CLOSES["prepare"]`; `STAGE_FILES["test-strategy"]`; `SECTIONS`; `grounding()` "test strategy"; `loops` resources; test-spec, test and carry-forward prompts; progress row | **Incorporated** | Into `environment.md` (Harnesses and suites, Commands, ID convention) and `architecture.md` (Real-boundary checks). The test-strategy stage stays and writes those sections. `grounding()` drops its fifth label (the inner-loop session quotes `GROUNDING_LABELS`, so its packets follow) | 4b |
| Knowledge-home `README.md` | `CLOSES` prepare, release-verify; `STAGE_FILES` intake, plan, release-verify; `stage_lines`' first line names it as the home's entry point; `_knowledge_lines`' feature-list link sentence | **Eliminated** | No consumer needs an index of three files with fixed names: packets already name each living file by path through `grounding()` and `stage_lines`. The first line of `stage_lines` names the three files instead | 4b |
| `SHIPLOOP.md` | `knowledge_home.INDEX` in `KNOWLEDGE` (committed and credential-screened); `expectations.KNOWLEDGE_INDEX` (an item's scope treats it as knowledge); `shiploop_workspace` (a return plan cannot exclude it); the navigator's reference list and `shiploop_reference` ("host-authored, if present"); the document prompt ("link it from the index and SHIPLOOP.md") | **Eliminated as a ShipLoop product.** A user's own file is still read if present | ShipLoop stops asking models to write or link it and stops committing it as knowledge. The "host-authored, if present" pointer stays, because a user-written index has a consumer (the model reading the user's repository) | 4b |
| `features/README.md` (generated list) | `write_feature_list` inside `commit()` and `retire()`; `earlier_features()` clause in intake, discovery, research, spec and plan packets | **Eliminated** | It exists only to find feature folders, which no longer exist. The earlier-features clause is replaced by the lessons quote in intake (`outcome.md` row) | 4c |
| The retire step | `_knowledge_close(terminal=True)` calls `knowledge.retire`; `retired_by`, `is_retired_spec` in `_check_submitted_evidence`; progress "Retired" row; the handoff packet sentence | **Eliminated** | Nothing to retire once the feature spec is a state field | 4c |

Existing repositories keep their old files (one supported version: nothing migrates them, and ShipLoop stops requiring, writing and naming them). The credential screen still reads every `docs/shiploop/*.md`, so an old file cannot hide a secret.

### 3.3 The hand-off fields (C2 and C3), anchored to producer, gate and consumer

To avoid a second home for one fact (S-12), structural decisions stay in `architecture.md` and requirements in `spec.md`. The hand-off fields carry IDs, and the script quotes the entry text from the living file.

| Field | Producer stage, and the gate at its done | Consumers (packets that quote it) | Replaces |
|---|---|---|---|
| `follows: [R-<n>, AD-<n>]` on each step-plan result | step-plan; every ID must exist in the living spec or the architecture (same readers as the retention loop) | That item's implement, test and verify packets quote each entry's text. This is the C3 mechanism and replaces "decisions that touch the paths it changes", which had no anchor | The packet line "cite the ID in the step plan" (prose today) |
| `changed_ids: [R-<n>, AD-<n>]` on any result that edited the living spec or the architecture | Any stage that changes either file; the IDs must exist; the retention loop still refuses a dropped ID | The next stage's packet quotes the changed entries; the report lists them | Stale summaries after an edit (audit row 3, in part) |
| Open items: extend the existing `assumptions` mechanism (`shiploop_assumptions`, today plan-only: each open item names a check, a reason and a consumer work item) to the stages that write "## Open" today: carry-forward, verify, system-test-author | Each of those stages; the same `assumptions` validation (an open item must name its consumer) | system-test-author (each open item becomes a system case or stays open with an owner), the release stages, and the report | `plan.md ## Open` |
| `not_covered: [{behaviour, reason}]` | implement, test, verify (the Done-when lines with no carrier today, audit row 2); shape check only | verify (confirm or cover), system-test-author (cover at system level or carry), and the report | Prose in summaries and the optional `notes/` |
| `requirement_changes`, `test_cases` (Option A), `release`, `lessons` | spec, test-spec, release-plan, release-verify respectively (3.2) | As in 3.2 | The feature files |

The engine owns the keys and gates. The inner-loop session owns the packet lines that quote them, and the report shows them.

### 3.4 Where everything lands (the tree the rest of ShipLoop references)

In the user's product repository, after the change:

```
<repo>/
  docs/shiploop/
    spec.md            the contract. SECTIONS: Requirements, Non-functional requirements, Retired. Stable R-<n>.
    environment.md     how to build, run and test it. SECTIONS: Targets and runtimes, Commands, Skills,
                       Harnesses and suites (from test-strategy.md), ID convention (from test-strategy.md),
                       Access and accounts, Platform facts.
    architecture.md    how it is built and why. SECTIONS: Stack, Structure, Conventions, Interfaces and
                       boundaries, Real-boundary checks (from test-strategy.md), Decisions (AD-<n>), Superseded.
  <product files>      committed by item commits; lessons travel in the release-verify knowledge commit.
  (no docs/shiploop/features/, no test-strategy.md, no docs/shiploop/README.md written by ShipLoop)
```

In ShipLoop's run folder (engine owned; the hand-off fields are keys in `state.md`'s accepted results):

```
<run>/state.md   accepted.<action>: requirement_changes, follows, changed_ids, not_covered, test_cases (Option A),
                 release, lessons, assumptions (open items); plus the plan's spec commit, recorded by the script
<run>/report.html  the human record (C5): work items, test cases, hand-off fields, open items, lessons
```

In ShipLoop's source (`skills/shiploop/scripts/`), where each change lands, so every other module references one place:

| Concern | Module and symbol (one home each) |
|---|---|
| The living files, their sections and section text | `shiploop_knowledge_home.py`: `LIVING`, `SECTIONS`, `ARCHITECTURE_HOLDS`, `grounding()`, a new `section_text(repo, file, heading)`, and `entry_text(repo, id)` for one `R-<n>`/`AD-<n>` entry |
| Which stage writes which file; which close requires it | `shiploop_knowledge_home.py`: `STAGE_FILES`, `CLOSES` |
| Which stage reads which sections (the reference map in 3.5) | `shiploop_knowledge_home.py`: a new `READS = {stage: ((file, heading), ...)}`, the one table the packets and tests use |
| Hand-off result keys and their gates | `shiploop_navigator.py`: `_RESULT_KEYS`, `_canonical_result`; open items in `shiploop_assumptions.py` |
| Quoting into packets | Engine supplies `section_text`, `entry_text` and `READS`; the inner-loop session's `_knowledge_lines` and the inner prompts print them |
| The report | `shiploop_progress_data.py` (the completion report's data) |

### 3.5 Reference map: which stage reads which section (consumed through `READS`)

The test strategy no longer has its own file. Every test stage reads it from named sections of `environment.md` and `architecture.md`, and the build phase reads both files. The script quotes the named sections into the packet, so a cleared stage has them without opening a file. Other sections stay available by path through `grounding()`.

Agreed with the packet owner (the inner-loop session, 2026-10-11):
- **Shape:** `READS` is `{stage: ((file, heading), ...)}`, with headings spelled exactly as in `SECTIONS`. Every inner stage has a row, even an empty one, so a packet prints "consult: none" deliberately and never by omission.
- **The renderer:** its References block is generated from knowledge_home's tables (`SECTIONS`, `grounding()`, `STAGE_FILES`, `READS`), so removing a file is a table change.
- **Quote length:** no cap on quote length. A fixed character cap would cut the text a stage needs, and the owner's rules forbid invented thresholds and trimming guidance. Quoted text stays small by choosing what is quoted: the entries a step plan `follows` (one requirement or decision each) and the few sections `READS` names. The harness's `metrics.packets` measures packet bytes per stage; if a stage's packet grows too far, the fix is a narrower `READS` row, not a truncated quote.

| Stage | Reads (file, section) | Writes |
|---|---|---|
| test-strategy | spec.md (Requirements, Non-functional requirements) | environment.md (Harnesses and suites, Commands, ID convention); architecture.md (Real-boundary checks) |
| plan | spec.md; architecture.md (Stack, Structure, Decisions); environment.md (Targets and runtimes) | architecture.md (Decisions) |
| step-plan | spec.md entries; architecture.md (Structure, Conventions, Interfaces and boundaries, Decisions); environment.md (Commands, Skills) | `follows`; architecture.md (Decisions) when the item makes a structural choice; environment.md (Commands) |
| test-spec (test strategy applied) | the item's `follows` entries; environment.md (Harnesses and suites, ID convention); architecture.md (Interfaces and boundaries, Real-boundary checks) | `test_cases` (Option A) |
| validate-existing | environment.md (Commands) | environment.md (Commands) when a command is found to work |
| implement (build phase) | the item's `follows` entries; architecture.md (Structure, Conventions, Interfaces and boundaries, Decisions); environment.md (Commands, Skills, Targets and runtimes, Platform facts) | product code; architecture.md (Decisions) for a deviation; environment.md (Commands); `not_covered` |
| test (test strategy applied) | the item's `test_cases`; environment.md (Harnesses and suites, Commands, ID convention); architecture.md (Real-boundary checks) | tests; `not_covered` |
| document | spec.md entries the item changed; architecture.md (Structure) | docs; `changed_ids` |
| verify | the item's `follows` entries; architecture.md (Interfaces and boundaries, Decisions); environment.md (Commands) | `not_covered` confirmed or covered |
| carry-forward | the run's open items and `not_covered` | architecture.md (Decisions, Superseded); environment.md (Commands); open items |
| system-test-author, system-test | open items; `not_covered`; environment.md (Targets and runtimes, Harnesses and suites, Commands); architecture.md (Real-boundary checks) | `system_commands` rows with `purpose` and `requirement` |
| release-plan, release-check, release | environment.md (Targets and runtimes, Access and accounts); `release` | `release` (release-plan) |
| release-verify | `requirement_changes`; the plan's spec commit; `release` | `lessons` |
| intake (next run) | the last run's `lessons`, quoted from the release-verify commit found by subject; spec.md; environment.md; architecture.md | — |

## 4. Steps

### Step 0: consumer-read measure (evidence script, no engine change)
- A read-only script under `docs/experiments/consumer-reads-20261011/` classifies, from a saved run's events, every file the model opened, by artifact family and stage.
- Run it over the 2026-10-10 and 2026-10-11 runs as the baseline.
- **Output:** a table per artifact in section 3 giving reads, stage, and whether the read was followed by a citation.

### Step 1: probe the next-run consumer (C4) on the current build
- Run a fresh `battleship`, then `battleship-scoring --continue-from <that output>` (the existing follow-on case; retention checks included).
- Claude Sonnet 5.5, `--source checkout`. Expected cost is about $10 to $15 for the pair.
- **Output:** what the follow-on opened from the earlier run and when; whether its plan cites earlier `R-`/`AD-` IDs; `cited_earlier_run`; the retention checks.

### Step 2: probe the cleared-context consumer (C2, C3) on the current build
- Run `slice.py --clear-at` on one step case at `implement`, `test:inside` and `verify`.
- **Output:** the redone work (S-6), what the fresh session opened before acting (step 0's script), and whether it needed anything its packet did not quote.

### Step 3: write and audit the consumer contract
- Sections 2, 3 and 8 of this plan become the contract, corrected by steps 0 to 2.
- Each field gets its exact schema, gate text (line 1 = the fix and the command) and quote format.
- An independent audit runs with three lenses:
  - consumer fit: every artifact has a reader, every reader's need is met, and nothing has two homes;
  - main tenet: a cleared stage works from its packet;
  - KISS and false refusals.
- The audit's corrections are applied before the owner sees the contract.

### Step 4: owner decision, then build (Execute: ask)
Each slice is built fail-first, gets two independent reviews and a fix round, and ships with a journal entry and a change note.
- **4a. Hand-off fields:** `follows`, `changed_ids`, `not_covered`, `requirement_changes`, `release`, `lessons`, `test_cases` (if Option A), and open items through `assumptions`. Their gates, the quoting into the consuming packets (packet lines placed by the inner-loop session), and the intake lessons quote found by subject. The engine adds `section_text`, `entry_text` and the `READS` table (3.4, 3.5); the inner-loop session's packets print the sections `READS` names for each stage. A test pins that the test-spec, test, system-test stages and the build phase (step-plan, implement, verify) quote their `environment.md` and `architecture.md` sections.
- **4b. Living files:**
  - `test-strategy.md` merged into `environment.md` and `architecture.md`; `SECTIONS`, `STAGE_FILES`, `CLOSES`, `GROUNDING_LABELS` and `loops` resources updated;
  - the knowledge `README.md` and ShipLoop's own `SHIPLOOP.md` writing dropped;
  - `stage_lines` names the three files.
- **4c. Removal of the per-run files and their machinery:**
  - feature `spec.md`, `plan.md`, `system-tests.md`, `release-plan.md`, `outcome.md` and `test-spec.md` (if Option A);
  - `retire`, `features/README.md`, `earlier_features`, the `spec_pin` line, `learnings()` and the progress rows;
  - the state records for the plan's spec commit;
  - every test that pins the removed behaviour, replaced by tests of the new homes.
- **4d. The report:** shows the work items, test cases, hand-off fields, open items, lessons and the plan's spec commit.
- **4e. Harness and others:**
  - E2E SPEC amendments (S-6, S-9, S-10, S-11) in their own commits;
  - `test/shiploop_e2e/fidelity.py`, `review.py` and `packet_anatomy.py` updated where they read `plan.md`, `test-strategy.md` or the feature folder;
  - `counters.py` keeps recognising old retire commits in saved runs (it reads history);
  - the Run Review exporter (`skills/shiploop-run-review/scripts/export.py`) updated by its owner, the E2E fork;
  - consumer-read counts folded into `metrics.json` if step 0 proved them useful.

### Step 5: verify
- Rerun steps 1 and 2 on the new build and compare consumer reads, redone work, follow-on use and `cited_earlier_run`.
- Run hello and Checkers cells of three or more against the current build's spread.
- No claim of change unless the distributions clearly differ.

## 5. Who owns what

| Area | Owner |
|---|---|
| Result keys, gates, knowledge home, report contents, removals, harness evidence | This session (engine) |
| Packet lines that quote the hand-off fields; stage duty wording | The inner-loop session |
| Run Review exporter | The E2E fork |
| Release | The owner. The pending inner-loop note already makes ShipLoop a major release |

## 6. Owner decisions, each anchored where ShipLoop would consume the answer

**Answered 2026-10-11** (recorded in `docs/shiploop-consumer-contract-probes-2026-10-11.md`):
1. Removals approved.
2. Test cases are a state field (Option A).
3. Report only; no plan copy in the repository.
4. Lessons go in a release-verify field and its commit, and are quoted at the next intake by subject.

The engine work lands with the inner-loop session's packet work on the shared branch `integrate/refs-consumer-contract`, verified once on the combined result.

1. **Approve the contract and the removals (3.2).**
   - Consumed by: steps 4a to 4e as a whole.
   - Reverses three earlier decisions: knowledge retained as files at planning, the feature-spec lifecycle, and the features list.
   - The owner's 2026-10-10 requirement that the feature spec be a historical record merged into the living spec is met differently: the merge happens in place (models already edit the living spec), the record is the living spec at the commit recorded at plan done plus git history, and the per-run delta is `requirement_changes` in state and in the report.
2. **Test cases: Option A (state field) or Option B (one per-run file in the run folder).**
   - Consumed by: `expectations.check_test_spec_ids` (the test-spec done gate), the test and verify packets, `loops` resources, and the report.
   - A changes the gate to read state. B moves the file and keeps the gate reading it.
3. **A human-readable plan in the repository, or the report only.**
   - Consumed by: C5 only; no stage or script reads `plan.md` once the plan is in state.
   - If kept, it is a generated copy written by the script from state at plan done (no model effort, no second source).
4. **Where lessons live.**
   - Consumed by: `commit()` (the release-verify commit body), the next run's intake packet (the lessons quote, by subject), and the report.
   - Recommended: the `lessons` result field, written into that commit and quoted at the next intake, with no file.
   - Alternative: a "## Lessons" section in a living file. That adds a second home unless the commit body stops carrying them.

## 7. Risks

- **Few runs.** The probes are one pair and three slices. The contract states every figure with its count.
- **Coordination.** Packet lines and the exporter are owned by other sessions. Their changes land in the same release, or the shape is half-built.
- **Models keep writing removed files.** Prompts must stop asking for them in the same release (4a, 4b, 4c remove every duty line and loop work text that names them; a test pins that no packet names a removed file).
- **Work built on 2026-10-10 is removed.** The retire step and the feature list are dropped deliberately; the directive outranks sunk work.

## 8. Every assertion in this plan, traced to its step and its test

| # | Assertion | Step that builds or measures it | Test or evidence that proves it |
|---|---|---|---|
| A1 | Implementation consumes state fields, not the markdown copies | 0 (measure) | Consumer-read table: no gate reads `plan.md`; read counts per stage |
| A2 | Several Layer 2 files have no reader the engine depends on | 0 | Code anchors in 3.2, plus the consumer-read table |
| A3 | The next run uses the living files and the last run's lessons | 1, 5 | Follow-on reads, citations of earlier IDs, `cited_earlier_run`, retention checks |
| A4 | A cleared stage can work from its packet | 2, 5 | S-6 redone work = 0; no file opened that the packet should have quoted |
| A5 | Each removed artifact is incorporated or eliminated | 3, 4c | 3.2 table; a test that no packet, loop work text or `CLOSES`/`STAGE_FILES` entry names a removed file |
| A6 | Each new field has one producer, one gate, named consumers | 3, 4a | Per field: a route test that the gate refuses a bad value and accepts the fix; a test that each consumer packet quotes it |
| A7 | No fact has two homes | 3 (audit lens), 4a | `follows`/`changed_ids` carry IDs only; the entry text is read from the living file; test that the quote equals the file's entry |
| A8 | C3 gets the decisions an item follows (replaces "touch the paths") | 4a | A test that implement, test and verify packets of an item quote exactly its `follows` entries |
| A9 | Lessons reach the next run despite the commit window | 4a | A test that intake quotes the newest release-verify commit found by subject when other commits follow it |
| A10 | Old repositories keep working | 4b, 4c | A test on a fixture home with every old file present: no refusal, no write to old files, credential screen still covers them |
| A11 | Models stop writing removed files | 4a to 4c, 5 | The "no packet names a removed file" test, plus step 5 runs: no removed file created |
| A12 | The report shows what C5 needs | 4d | A test of the report data on a fixture state with every field |
| A13 | No cost regression | 5 | Hello and Checkers cells, n of 3 or more, against the current spread |
| A14 | Harness and exporter stay correct | 4e | Harness suites green; the exporter's owner confirms on saved and new runs |
| A15 | The test strategy is read from named sections of `environment.md` and `architecture.md` by every test stage | 4a, 4b | `READS` names them for test-strategy, test-spec, test, system-test-author and system-test; a test that each of those packets quotes the sections; step 5 runs show the sections filled |
| A16 | The build phase references `environment.md` and `architecture.md` | 4a | `READS` names them for step-plan, implement and verify; a test that each packet quotes them (plus the item's `follows` entries) |
| A17 | Every module references one home per concern (3.4) | 4a, 4b | A test that `READS`, `SECTIONS` and `STAGE_FILES` name only living files and headings that exist in `SECTIONS` |
| A18 | Every worktree for steps 4a to 4e starts from a commit that holds this plan | before step 4 | The plan is on `origin/main` before any worktree is created; each worktree is created from `origin/main` |
