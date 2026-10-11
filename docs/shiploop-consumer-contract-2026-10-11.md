# ShipLoop consumer contract (2026-10-11)

Step 3 of `docs/shiploop-consumer-contract-plan-2026-10-11.md` (Execute: ask). This is the contract an implementer builds
from in step 4. It has not been built.

**Revision 2 (2026-10-11, after three independent audits).** Section 0A lists every audit correction. Where 0A conflicts
with sections 1 to 11, 0A wins. The owner approved D1 to D4 as recommended (section 0A.3). Sections 1 to 11 now match 0A
and D1 to D4 (revision 2 body); the audited revision 1 body is in Git history (acf1f026). Section 0 rows that 0A
superseded are marked, not deleted.

Inputs:
- the plan (sections 2, 3, 6 and 8);
- the owner's four decisions and the step 0 and step 2 results (`docs/shiploop-consumer-contract-probes-2026-10-11.md`,
  `docs/experiments/consumer-reads-20261011/README.md`);
- the artifact-flow audit (`docs/shiploop-artifact-flow-2026-10-11.md`, section 4);
- the step 1 follow-on probe (Battleship, then the scoring follow-on continued from it; both passed);
- the code on origin/main.

Owner directive: every output is produced for a named consumer, in the form and at the moment it reads it. No consumer, no
output. Owner rules applied throughout:
- One supported version: no shims and no migration. Old files are left in place, and are no longer required, written or named.
- No invented thresholds or caps, and no character cap on a quote.
- The main tenet: a cleared stage works from its packet, and every refusal's line 1 states the fix and the exact next command.
- One home per concern (S-12).
- Fail-first tests.
- KISS.

Owners:
- **engine (this session):** result keys, gates, the knowledge home, the report, removals, and the harness.
- **packet text (inner-loop session):** the packet lines that print quotes, stage duty wording, loop work text, and
  reference cards.
- **exporter (E2E fork):** the Run Review exporter.

---

## 0. Corrections to the plan found while writing this

| # | The plan said | The code or evidence shows | This contract does |
|---|---|---|---|
| K1 (superseded by X11 and X13) | Per-run files become state fields, and the next run reads only the living files | Step 1: the cold follow-on opened the earlier run's `test-spec.md` (at test-spec), `system-tests.md` (at system-test-author) and `release-plan.md` (at release-plan) as precedent. Run state is not in the repository. | Each cross-run need gets a home in a living file, written by a named stage and checked by a named gate (section 3.10). Test cases: `environment.md` ID convention and Harnesses and suites, plus the IDs in the test code. System test catalog: `environment.md` Harnesses and suites. Release procedure: a new `environment.md` section, "Release and rollback". |
| K2 | Open items at carry-forward, verify and system-test-author | system-test-author also reads test-spec.md "## Due later" (`DUTIES["test-spec"]`, `DUTIES["system-test-author"]`) | test-spec joins the open-item stages: a due-later case is an open item whose consumer is an outer stage. "## Not tested here" is eliminated, because it can be derived: a criterion with no test case is confirmed by the check command the step plan names for it. |
| K3 (superseded by X9) | The plan's spec commit is "recorded in state" | `_STATE_KEYS` and the history rows are exact sets. The plan's knowledge commit happens after the state is saved (`_knowledge_close`). | The script writes the commit to a run-folder record after the plan's knowledge commit. The precedent is `expectations.PREPARATORY_COMMIT`. No state key is added. |
| K4 | Lessons ride in the release-verify knowledge commit | `knowledge_home.commit` commits only when the home changed (`_home_changed`). With outcome.md gone, a release-verify that changes nothing would make no commit. | `commit()` makes an empty commit with the lessons body when nothing else is recorded at release-verify (`shiploop_git.commit_paths(..., allow_empty=True)`). |
| K5 (superseded by X9) | changed_ids goes "on any result that edited the living spec or the architecture" | spec has `requirement_changes`, and step-plan's new IDs are ones the item follows. Prelude, outer and carry-forward edits already reach their readers through READS sections and Git. | `changed_ids` sits on implement, test, document and verify only. At spec and step-plan the same completeness rule applies to `requirement_changes` and `follows`. The script checks completeness against HEAD (`changed_entries`). |
| K6 (superseded by X12) | READS rows as in plan section 3.5 | Step 0: step-plan read test-strategy.md 5 times. `DUTIES["step-plan"]` consults Harnesses and suites and ID convention, `DUTIES["test"]` consults architecture Conventions, and `DUTIES["verify"]` consults Real-boundary checks and Conventions. | Those sections are added to those rows (section 5). |
| K7 | "The report: `shiploop_progress_data.py`" | The completion report is `navigator._render_report`. `shiploop_progress_data.build_snapshot` feeds the live progress view. | The report additions go in `_render_report`. The progress view only loses the removed rows. |
| K8 | READS is the one quoting table | Consumers also need hand-off fields by value, and a test must know which stage quotes which | A second table, `CONSUMES`, sits beside `_RESULT_KEYS` (section 4). |
| K9 (in part superseded by X9: the complete-only completeness checks) | The gate runs at "that stage's done" | An Improve-reviewed stage is accepted at improve-complete, from a seed or final result (`finish_improve`). `_inner_gates` runs only on complete, so today's test-spec ID check is skipped for a revised final result. | Every hand-off gate runs on both routes, as `_knowledge_gate` does. The completeness checks run on complete only, because on improve-complete the review's edits are already committed through improve-commit. |
| K10 (in part superseded by X11: system rows) | Test cases and system rows carry `requirement R-<n>` | Real cases and system tests cover several requirements. `_ids` is the one reader of the ID syntax. | `requirement` is a string that names one or more R-<n>, read by `_ids`. |
| K11 | plan.md's item sections move into state | The step-plan packet prints the item's `context` through `_required_excerpt`, which cuts it at 1200 characters. It does not print the item's open plan assumptions at all, although `expectations.check_step_plan` refuses until each is cited. | The context prints whole, and step-plan quotes the open plan items that name its work item. |
| K12 (in part superseded by X10: carry-forward is also a consumer) | The open-item consumer is named | The plan's consumer is a work item, which step-plan's `from` rule settles. A second producer of work-item consumers would collide on IDs (A1 from the plan, A1 from verify). | At the four new stages, an open item's consumer is a later outer stage. Work for a later item goes through carry-forward's `work_items`, as today. |
| K13 | (step 1) Lessons reach the next run | The follow-on's intake saw the learnings commit second in the last-three window, behind the retire commit and ahead of the leftovers commit. One more closing commit would have pushed it out. | The intake quote finds the commit by subject (section 3.9). |

---

## 0A. Audit corrections (revision 2)

Three read-only audits checked revision 1 against the code, the inner-loop packet branch `exp/four-part-packet-631117`,
the three cleared slices, and the saved runs (17 knowledge homes and 18 `state.md` files under
`/Users/dadleet/e2e-runs/20261010` and `20261011`):
- **routes:** the main tenet and every gate route (1 blocker, 6 majors, 9 minors);
- **KISS:** overbuilding and false refusals (1 blocker, 7 majors, 8 minors, measured on the saved homes);
- **consumer fit:** whether each consumer gets what it needs (1 blocker, 7 majors, 6 minors).

Every saved run had one work item, so no audit had multi-item evidence. Status of every finding below: **interim**
until step 5 reruns the probes on the built contract.

### 0A.1 Adopted: fixes inside the approved decisions

| # | Found by | Finding | Correction |
|---|---|---|---|
| X1 | routes B1, consumer fit B1 | **Blocker.** The empty lessons commit (K4) is never returned on an isolated run. `workspace.follow_up_knowledge_return` returns None when `git diff --name-only <head> HEAD` is empty. The receipt is then stale, and `protocol.workspace_completion_guard` refuses handoff. Both step 1 probes would hit this: their release-verify commits touched only `outcome.md` and `features/README.md`, both removed. | `follow_up_knowledge_return` also returns when the diff is empty but `git rev-list <head>..HEAD` is non-empty and every new commit is a ShipLoop knowledge commit (`knowledge_subject` or the lessons subject). Test: an isolated full-runtime run whose release-verify changes no home file reaches done with no stale-return refusal, and a fresh intake on the source branch quotes the lessons. |
| X2 | routes M6, consumer fit B1 | On a working-tree return no commit reaches the user's branch, so the lessons never reach the next run. | The handoff packet and the report print the lessons body and the exact commit message, and tell the user to commit it. S-11 records this route's limit. |
| X3 | routes M1, KISS M7 | Refusal line 1 cannot fit its own 250-character test: 20 of 24 drafted texts exceed it at a realistic run path. The full `complete` callback is about 300 characters by itself. | Rule 4 becomes: line 1 carries the fix, one absolute path and the verb ("then run the same complete command again"); line 2 carries the JSON shape and the "consumers quote it" sentence. The test uses the longest saved inbox path (173 characters). |
| X4 | routes M2 | An improve-complete refusal on the seed result loops. The printed command has no `--final-result`, so rerunning it re-checks the seed. The Improve packet's outcome list also omits `revise`. | `dispatch` passes the next command to `_handoff_gate`. With no final result, line 1 says "write a final result to <path>, then run improve-complete with --final-result=<path>". Add `revise` (test-spec to verify) to the Improve outcome list. Test: a seed refusal whose named exit is accepted through the real CLI. |
| X5 | routes M3 | `_handoff_gate` would see raw JSON before `_canonical_result`, so a wrong type crashes it with a TypeError instead of refusing. | The gate canonicalises first (precedent: `_check_submitted_assumptions`), then checks meaning. |
| X6 | routes M4 | The packet branch calls `feature_dir`, `FEATURE_LIST`, `_GROUNDING`, `earlier_features`, `spec_pin` and `STAGE_FILES` with README.md. If the removals land first, every `next` crashes. | Order on `integrate/refs-consumer-contract`: the packet branch, then 4a, then the renderer swap (`_CONSULT = knowledge.READS`; `_PRODUCTS`' feature pointers become hand-off sources), then the 4b/4c removals. Section 7.2 adds `_reference_global_lines`, `_writer`, `_CONSULT`/`consult_lines`, `_PRODUCTS` and `_builds_on_lines`. The section 7 grep runs on the combined branch. Packets name files by symbol; refusals by absolute path. |
| X7 | routes M5, consumer fit M5 | CONSUMES misses inputs the gates and duties use. | Add: test-spec `criteria`, `test_commands` (focused rows); implement `criteria`; document `follows`; product-acceptance the spec diff (X9) and open items; system-test-author every item's latest `test_cases`; test-strategy and carry-forward the spec diff; handoff `lessons`; release-plan `system_commands`. The cleared-packet test covers test-spec. |
| X8 | all three | Removing the last-commits window breaks the owner's 2026-10-10 requirement 4 (look back at the last commits on every step), drops the lessons in Improve commits, and hides user commits made since the last run. | Keep `recent_commits`. Add the lessons quote, found by subject, when that commit is not already in the window. Quote at intake and discovery: context is cleared between them, and both print the window today. |
| X9 | KISS M2, M3; consumer fit M7 | `requirement_changes` and `changed_ids` are model-typed copies of a fact the script computes (`changed_entries`). Saved runs: implement, test, document and verify made 0 edits to `spec.md` or `architecture.md`. Spec reviews added requirements through improve-commit (for example "R-15, R-16"), which the complete-only check never sees. | **Awaits D3.** The script records one run baseline (the workspace manifest's `baseline_commit`, or one run-folder record) and derives added, modified and retired IDs from the diff since it. This replaces both model fields, their refusals, the completeness checks, and `PLAN_SPEC_RECORD`/`record_plan_spec`/`plan_spec`. `follows` stays model-written (choosing what an item follows is a judgement), with an existence check only. |
| X10 | KISS M5, consumer fit M4 | Three carriers for "not proven yet" (`not_covered`, the new open items, product-acceptance's `unverified`). Open items had missing producers, no settlement and no owner. | Open items are the one carrier for new stages. `not_covered` is optional and implement-only (its consumer is test). verify records uncovered behaviour as open items. Producers add system-test, release-plan and release-verify. Settlement needs no new key: a row is open until its consumer stage's done result; a row carried forward is that result's own row (corrected after the 4a review). Open rows at the new stages carry `owner` (a person) where the duty names one. Allowed consumers: a later outer stage, or carry-forward. `unverified` is unchanged. |
| X11 | KISS B1, M6; consumer fit M1 | **Blocker (KISS).** The "Release and rollback" section gate refuses all 17 saved homes. 7 of 17 already record the procedure under other names ("Delivery", "Release verification"). The notice's own fix ("write 'none'") passes the gate with filler. The system-catalog gate would refuse 14 of 15 runs with system IDs. | Drop both gates. "Release and rollback" stays out of `SECTIONS`. Duty text asks release-plan to keep the standing procedure in `environment.md`, and system-test-author to keep the catalog there; the next run gets the file quoted (X12). Purpose and requirement live in the catalog only; `system_commands` rows keep command, suite and IDs. The release field itself: **D2**. |
| X12 | KISS M1, consumer fit M6 | Quoting by heading misses most real homes: "Commands" matched 8 of 17, "Harnesses and suites" and "ID convention" 0 of 17. On the current build, `architecture.md` had no level-2 heading at all, and the scoring follow-on wrote "## Targets" after 8 section notices. The files are small: `spec.md` ≤ 5.3 KB, `environment.md` ≤ 1.8 KB, `architecture.md` ≤ 1.9 KB. | **Awaits D1.** `READS = {stage: (files)}`, each file quoted whole and uncut. This removes `section_text`, `_section_spans`, the five-status `ReadQuote` and the `inside` rule, and makes the consumer-fit READS gaps moot. The test stages and the build phase get `environment.md` and `architecture.md` whole, which includes the harness, command, ID and boundary sections the owner named. The section notice stays as the existing counted nudge. |
| X13 | consumer fit M2 | The requirement-to-test map had three homes (spec.md "Satisfied by tests", the catalog, the test files), and the ID high-water mark goes stale. | The test code is the one home. Remove carry-forward's "with its test IDs" duty. The catalog names suites, files, commands, and the one command that lists the IDs already taken. |
| X14 | consumer fit M3 | Removed-file content with no named home: the step-plan "Plan note", the plan's "Namespace and data map", the carry-forward "explain removals in plan.md" lines, test-strategy's allocation table, and test sub-cases. | Cross-item namespace and data map: architecture Structure, with an AD-n per decision. Per-item note: the work item's `context` or the step-plan summary, with the duty reworded. The unconfirmable mark: in the criterion text. The allocation table: eliminated (carried by item context and `test_cases.requirement`). Sub-cases: the test code only. Add "plan note", "Namespace and data map", "Repository knowledge index" and "README/index links" to the removal grep and the 4c test. |
| X15 | KISS m2, m3, m4; routes minors | Small shape and route fixes. | `test_cases` missing or `[]` is accepted when the item has no focused IDs. Rename the contract's `LESSON_LABELS` (it collides with `shiploop_lessons.LESSON_LABELS`). Improve parent and child packets print the same quotes. A quoted entry now under Retired or Superseded prints a marker. On improve-complete, a refusal whose fix is a living-file edit says "improve-commit it first". The script appends open items left at release-verify to the lessons commit body as generated text. A test checks each CONSUMES producer is in that stage's `stage_spec` `reads`. |
| X16 | KISS tests | Some planned tests cannot fail or are circular. | The packet test uses an expected table written from section 3, not `CONSUMES`. The entry test compares to a literal fixture string. Cut the two READS-against-itself tests. The retire-subject test uses a literal saved subject. Add: heading variants (`## Targets`, `## Delivery`) cause no refusal; a two-item fixture for per-item `test_cases`; the 250-character cut at the 173-character path. |

Accepted as known limits:
- A failed release-verify commit leaves the lessons out (Q7). Only the failure case; the empty commit is fixed by X1.
- On an old repository, harness facts that live only in the old `test-strategy.md` are not pointed at. Step 1 showed
  models open precedent files on their own.
- `record_plan_spec` (if D3 keeps it) is skipped when the plan's knowledge commit raises.
- The "Current planning sources" path blocks to `results/*.md` stay for now; step 5 measures whether CONSUMES quoting makes
  them unused.

### 0A.2 Open questions after the audits

| # | Answer | Basis |
|---|---|---|
| Q1 | Bump `STATE_VERSION` 5 to 6, once, on the integration branch only. | All three audits. 5 is unreleased, so this refuses only dev-checkout runs on 5, which would otherwise half-continue. |
| Q2 | Lessons at intake and discovery, beside the kept window (X8). | All three audits; owner requirement 4. |
| Q3 | **D4.** | KISS: no required key (no observed reader; filler risk). Consumer fit: add it (test and verify use it). |
| Q4 | **D2.** | KISS: keep the `release` field with a presence gate (step 0: release, release-check and operations read `release-plan.md` in-run). Consumer fit: drop it (one home: the living procedure, quoted whole, plus the script's `rollback_lines`; release-check cannot correct a release-plan field). |
| Q5 | Superseded by X9 (D3). | KISS and consumer fit. |
| Q6 | Yes, plus carry-forward (X10). | All three. |
| Q7 | Accept for a failed commit only (X1 fixes the normal case). | All three. |
| Q8 | Superseded by X9 if D3 is adopted; otherwise fine. | All three. |

### 0A.3 Owner decisions (each changes the approved plan's shape)

**Decided 2026-10-11: the owner approved all four recommendations** (D1 yes, D2 drop, D3 yes, D4 no). X9, X11 and X12 are therefore adopted in full.

| # | Decision | Recommendation |
|---|---|---|
| D1 | Quote `spec.md`, `environment.md` and `architecture.md` **whole** into each stage that reads them, instead of by section heading (X12). Changes plan section 3.5's table shape, agreed with the inner-loop session. | Yes. Heading matching fails on most real homes, and the files are under 6 KB. |
| D2 | Keep or drop the `release` field at release-plan (Q4). | Drop. One home: the standing procedure in `environment.md` (quoted whole) plus the script's `rollback_lines`; run-specific prerequisites become open items. |
| D3 | Replace the model-written `requirement_changes` and `changed_ids` with a script-derived diff from one run baseline (X9). | Yes. Same consumer content, fewer refusals, and it catches review edits the model fields miss. |
| D4 | Add a required `surface` key to `test_cases` (Q3). | No. The oracle names the surface; setup and teardown stay once per suite in `environment.md`. |

---

## 1. Rules every field follows

1. **One home.**
   - A hand-off field carries IDs or its own text.
   - Requirement and decision text stays in `spec.md` and `architecture.md` and is quoted from there.
   - The cross-run part of a run's record lives in a living file, kept current by the producing stage's duty text and
     quoted whole to the next run (section 3.6). No gate checks a heading in it (X11).
   - The test code is the one home of test IDs and of the requirement-to-test map (X13).
2. **Shape on load, meaning at the gate.**
   - `_canonical_result` checks a field's shape and the stage and outcome it may sit on, because `validate()`
     re-canonicalises every saved result.
   - Meaning is checked only at the CLI gates, in one new function, `_handoff_gate`. It canonicalises the submitted
     fields first and then checks meaning on the canonical value (X5; precedent: `_check_submitted_assumptions`). A wrong
     type is therefore a shape refusal, never a TypeError.
3. **Both routes.**
   - `_handoff_gate(root, state, stage, result, next_step)` runs on `complete` (including `--check-only`) and on
     `improve-complete`. It runs right after `_knowledge_gate`, on the same result those gates check
     (`child["seed_result"] if final_result is None else final_result`).
   - Every check runs on both routes. No check is complete-only.
   - The test-spec call moves out of `_inner_gates` into `_handoff_gate`.
4. **Refusal text (X3, X4).**
   - Line 1 is the fix, one absolute path, and `next_step`. The path is the result file when the fix is in the result,
     or the living file when the fix is there.
   - The result file is `<run>/inbox/<action>.md` on complete, or `<run>/inbox/<action>-final-result.md` on
     improve-complete.
   - `dispatch` builds `next_step` and passes it in:
     - on complete: "then run the same complete command again";
     - on improve-complete with `--final-result`: "then run the same improve-complete command again";
     - on improve-complete without it, the fix is worded "write a final result to <path> that <fix>", and `next_step`
       is "then run improve-complete again with --final-result set to that file". Rerunning the printed command would
       re-check the seed and refuse again.
   - On improve-complete, a fix that edits a living file adds "improve-commit it first" (X15), as `knowledge_home.check`
     does.
   - Line 2 is the JSON shape and the sentence that names who quotes the field.
   - Failing IDs and rows go on line 3 and after, in full, so a long list never pushes the fix off line 1.
   - Shape refusals from `_canonical_result` cannot know the route, so their line 1 ends "then run the same command
     again."
   - Test: with the longest saved inbox path (173 characters), every line 1 is at most 250 characters, the
     `knowledge_home.check` rule.
5. **Placeholders.** `_result_template` prints placeholder strings, collected in one constant, `HANDOFF_PLACEHOLDERS`.
   The gate refuses any hand-off string equal to one of them, as headline and unverified placeholders are refused today.
6. **Done only.** The four new keys (`follows`, `not_covered`, `test_cases`, `lessons`) join `_DONE_ONLY_FIELDS`.
7. **Quotes are never cut.**
   - No `_bounded_packet_text`, `_required_excerpt` or character cap applies to a quoted file, an entry or a hand-off
     value.
   - Each quoted line is printed with the prefix `"  | "`, the prefix today's commit quote uses, so a quoted heading never
     becomes packet structure.
   - Quotes go in the packet file, not the printed head (S-7). Step 2 found that a fresh session reads the whole packet
     file first.
   - Packets name files by their References symbol (`HOME/spec.md`); refusals name them by absolute path (X6).
   - ~~An Improve parent or child packet prints the same quotes as its stage's packet (X15).~~ Superseded 2026-10-11 by
     the owner's direction, relayed by the inner-loop session. An Improve packet carries no stage context. It says
     only: here is the result to improve, run /improve, and run the done command when it finishes. ShipLoop binds its
     own Improve card and writes the opening file from state: the result, the done-when conditions and the focus
     items.
8. **Render reads files only.** `reads_quotes`, `entry_text` and the state readers run no Git, as `grounding()` does
   today. The exceptions, each one Git read:
   - `recent_commits` and `last_lessons` at intake and discovery (`git log`);
   - `spec_diff` in a packet whose `CONSUMES` row names it, and in the report (one `git diff` from the run
     baseline).

---

## 2. Knowledge-home primitives (engine, `shiploop_knowledge_home.py`)

### 2.1 Tables after the change

```python
HOME = "docs/shiploop"
KNOWLEDGE = (HOME,)                      # SHIPLOOP.md is no longer ShipLoop's (INDEX removed)
ARCHITECTURE = "architecture.md"
ARCHITECTURE_HOLDS = ("the stack (language, frameworks, dependencies and why), the structure (modules and who owns each), "
                      "conventions, interfaces and boundaries, the real-boundary checks a local test cannot prove (each "
                      "with its owner), and a '## Decisions' section of stable IDs AD-<n> (choice, why, alternatives, "
                      "status) with a '## Superseded' section for decisions that no longer hold")
LIVING = ("spec.md", "environment.md", ARCHITECTURE)
SECTIONS = {
    "spec.md": ("Requirements", "Non-functional requirements", "Retired"),
    "environment.md": ("Targets and runtimes", "Commands", "Skills", "Harnesses and suites", "ID convention",
                       "Access and accounts", "Platform facts"),
    ARCHITECTURE: ("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Real-boundary checks",
                   "Decisions", "Superseded"),
}
CLOSES = {
    "prepare": ("spec.md", "environment.md", ARCHITECTURE),
    "release-plan": ("environment.md",),
    "release-verify": ("environment.md",),
}
STAGE_FILES = {
    "discovery": ("environment.md",), "research": ("environment.md",), "spec": ("spec.md",),
    "test-strategy": ("environment.md", ARCHITECTURE), "plan": (ARCHITECTURE,), "prepare": ("environment.md",),
    "step-plan": (ARCHITECTURE, "environment.md"), "validate-existing": ("environment.md",),
    "implement": ("environment.md", ARCHITECTURE), "test": ("environment.md",),
    "carry-forward": (ARCHITECTURE, "environment.md"), "system-test-author": ("environment.md",),
    "release-plan": ("environment.md",), "release-check": ("environment.md",), "release-verify": ("environment.md",),
}
_GROUNDING = (("living spec", "spec.md"), ("environment", "environment.md"), ("architecture", ARCHITECTURE))
LESSON_FIELDS = (("learned", "Learned"), ("considerations", "Key considerations"), ("open_next", "Open for the next run"))
KNOWLEDGE_SUBJECT = re.compile(r"^docs\(shiploop\): record (\S+) knowledge (?:at|after) \S+$")
LESSONS_SUBJECT = re.compile(r"^docs\(shiploop\): record (\S+) knowledge at release-verify$")
RUN_BASELINE = "run-baseline.txt"        # run-relative
READS = {...}                            # section 5
```

Notes on the tables:
- **test-spec is no longer a close.** Nothing is required at its done, because its cases are in state. Its knowledge
  commit still happens when it changed the home, with the subject "... after test-spec".
- **intake leaves `STAGE_FILES`**, because its only file was README.md.
- **"Real-boundary checks" is a level-2 section** placed after "Interfaces and boundaries", not nested under it.
- **"Release and rollback" is not a section (X11).** release-plan's duty asks it to keep the standing procedure in
  `environment.md`, under whatever heading the run uses (7 of 17 saved homes already say "Delivery"). release-check
  gains `environment.md` in `STAGE_FILES`, because its duty corrects that procedure when the rollback differs (D2).
- **"ID convention" holds the scheme and the one command that lists the IDs already taken**, not a high-water mark
  (X13).
- **`SECTIONS` feeds only the section notice**, a counted nudge that now covers three files (three lines at most). It
  never refuses, and no quote depends on a heading (D1).
- **`LESSON_FIELDS`** is named apart from `shiploop_lessons.LESSON_LABELS`, which means something different (X15).

### 2.2 Whole-file quotes: `reads_quotes(state, stage) -> list[FileQuote]` (D1, X12)

`FileQuote(name, path, text)` is produced in the `READS` row's order. A stage not in `READS` raises `ValueError`.
- `path` is absolute, in `state["repo"]`.
- `text` is the whole file, read as `section_notices` reads it (`utf-8-sig`, `errors="replace"`), never cut.
- `text` is `None` when the file is absent, blank, non-regular or unreadable.

What the packet prints (the inner-loop session renders it):
- A block titled "Knowledge this stage reads, quoted whole from the living files:".
- For each file: `HOME/<name>:`, then each line prefixed `"  | "`. A `None` file prints
  `HOME/<name>: not written yet (<reference_writer(name)>)`.
- An empty row prints "Knowledge this stage reads: none quoted; the living files are named above by path."

How a model spells a heading never matters: a home with `## Targets`, `## Delivery` or no level-2 heading at all is
quoted the same way.

### 2.3 Entries: `entry_text(repo, ident) -> Optional[str]`

One parser, `_entries(text, prefix) -> dict[id, Entry(text: str, retired: bool)]`, serves `entry_text` (quoting the
entries an item `follows`) and the existence check on `follows`.

Which file:
- `ident` must fullmatch `^(R|AD)-\d+$`; anything else raises `ValueError`.
- `R-` IDs are read from `spec.md`, and `AD-` IDs from `architecture.md`.
- A file that is absent, blank or unreadable gives `None`.
- Only lines outside fenced code count.

**Entry start.** A line is an entry start for ID X when it matches

    ^\s*(?:#{1,4}\s+|[-*+]\s+|\d+[.)]\s+|\|\s*)?(?:\*\*|__|\*|_|`|\[)?(X)(?!\d)

That is: optional indentation; then optionally a heading mark, a list marker, an ordered marker or a table pipe; then
optionally one emphasis, code or bracket opener; then X, not followed by a digit (so R-1 is not R-10).

Every shape in the saved specs matches: `- R-1: ...`, `- **R-1** ...`, `| R-1 | ... |`, `### R-1 ...` and `R-1: ...`
(0 of 153 saved IDs lacked an entry start). A mention inside another entry ("except R-9", "verifies R-1") is not a
start. The first start for X in the file is its entry, and later starts for X are ignored.

**Span.** How far an entry runs depends on its start line:
- **Heading form** (the start line is a heading by `_HEADING`): to the line before the next heading of the same or a
  higher level, or the end of the file.
- **Table form** (the start line begins with `|`): the start line only.
- **List or paragraph form:** the start line, then each following line while one of these holds:
  1. it is inside a fence opened within the span;
  2. it is non-blank and indented more than the start line (tabs count four), as a continuation or nested item;
  3. it directly follows a span line and is non-blank, and is not a heading, a table row, a list item at the start line's
     indentation or less, or another entry start of the same prefix (a lazy continuation);
  4. it is blank and the next line qualifies under 2.

  The span ends at the first line that qualifies under none of these.

Trailing blank lines are dropped. The text is the span's lines exactly as in the file, never cut.

**Retired.** An entry is retired when a heading enclosing its start line (the chain of headings above it, each of a lower
level than the one below it) has a title that starts, in any case, with "Retired" (`spec.md`) or "Superseded"
(`architecture.md`). A quoted retired entry prints a marker: "(now under Retired in HOME/spec.md)" or "(now under
Superseded in HOME/architecture.md)" (X15).

### 2.4 `run_label(state)` (replaces `feature_dir`)

`run_label(state)` gives the same string `feature_dir(state).rsplit("/", 1)[-1]` gives today: the first six
`[a-z0-9]+` words of the request, joined by `-` (or `feature`), cut to 48 characters, then `-` and the last six
characters of `run_id`.

It names no folder. `knowledge_subject(state, stage)` uses it, so a new run's subjects have the same shape as old runs'
(the harness's `counters.KNOWLEDGE_SUBJECT` already matches both).

### 2.5 Lessons: `commit()`, `lessons_body()`, `last_lessons(repo)`

**`lessons_body(lessons, open_rows)`** builds this text from `LESSON_FIELDS`:

    Learned
    <learned>

    Key considerations
    <considerations>

    Open for the next run
    <open_next>

Each value has its outer whitespace stripped. This is the layout today's `commit()` builds from outcome.md, so old and new
commits read the same. When open items are still open at release-verify (`assumptions.open_items`, section 3.5), the
script appends a generated block (X15):

    Open items left at release-verify (generated by ShipLoop)
    - <id> (<producer stage>[ <item>]): <assumption>; check: <check>; consumer: <consumer>[; owner: <owner>]

**`commit(state, stage)` at release-verify:**
1. The message is `knowledge_subject(state, "release-verify")`, a blank line, and `lessons_body` of the `lessons` in the
   newest done release-verify result in `state["history"]` and the open rows.
2. The home commit runs as today: `commit_paths(repo, [HOME], message)`.
3. When it records nothing (the home is unchanged, or every change was skipped by the secret screen), ShipLoop makes
   `commit_paths(repo, [], message, allow_empty=True)`. The lessons always travel (K4).
4. At every other stage, `commit()` is unchanged, except that `write_feature_list` is gone.

An isolated run returns that commit to the user's branch through the follow-up return (X1, section 3.4). A working-tree
return carries no commit, so the handoff packet and the report print the message instead (X2, section 3.4).

**`last_lessons(repo) -> Optional[Lessons(commit, subject, body)]`:** see section 3.4.

### 2.6 Run baseline and spec diff (D3, X9)

**The baseline.** At `init` (in `shiploop_protocol`, right after `navigator.save`), `write_run_baseline(root, repo)`
writes `root / RUN_BASELINE` once, with `store.atomic_write_text`: the 40-hex `git rev-parse HEAD` of the execution
checkout and a newline, or an empty file when the checkout has no commit or is not a checkout. In an isolated run the
execution checkout starts at the workspace manifest's `baseline_commit`, so the record holds that commit: one record for
both modes. Nothing rewrites it. `run_baseline(root) -> Optional[str]` returns the hash, or `None` for an empty file.

**`spec_diff(root, state) -> Optional[str]`:**
- `git diff <baseline> -- docs/shiploop/spec.md docs/shiploop/architecture.md` in the execution checkout, against the
  working tree, uncut.
- It returns `""` when nothing changed, and `None` outside a checkout or with no baseline.
- It compares the working tree, so a stage sees its own uncommitted edits, and an edit a review committed through
  improve-commit shows too.
- An edit the user left uncommitted in their own checkout before the run counts as this run's.

There is no model field, no refusal and no ID parser. This replaces the model-typed requirement and changed-ID lists,
their completeness checks and the plan's spec-commit record (section 3.7). An earlier draft of this revision derived
added, modified and retired ID lists (`run_changes`). That was superseded on 2026-10-11 by the uncut diff, which is
simpler, cannot misclassify, and also shows edits outside ID entries, such as non-functional requirements.

**What a consumer packet prints** (inner-loop session), where `CONSUMES` names `spec_diff`:
- `Spec and architecture changes since the run began (baseline <12 hex>), the uncut diff:`
- Then each diff line prefixed `"  | "`.
- `""`: "none since the run began".
- `None`: "not computed: <repo> is not a Git checkout, or the run has no baseline".

---

## 3. The hand-off fields

`_RESULT_KEYS` gains `follows`, `not_covered`, `test_cases` and `lessons`. `assumptions` is extended. `system_commands`
is unchanged (X11). Each field below gives its shape, producer, gate, consumers, and the code anchor it replaces or
extends. The refusal texts follow rule 4: `<result>` is the result file and `<next step>` is `dispatch`'s tail.

### 3.1 `follows` (step-plan)

```json
"follows": ["R-3", "R-5", "AD-2"]
```

**Shape:** a list, possibly empty, of unique strings matching `^(R|AD)-\d+$`. Allowed only on a done step-plan result.
Choosing what an item follows is a judgement, so the field stays model-written (X9).

**Gate at step-plan done** (existence only):
- **Missing.** Line 1: `Add follows to <result> (the R-<n> this item implements and the AD-<n> it follows; [] only when it serves none), <next step>.` Line 2: `Shape: "follows": ["R-3", "AD-2"]. This item's test-spec, implement, test, document and verify packets quote each entry.`
- **No entry.** Line 1: `In <result>, drop from follows each ID that has no entry, or add its entry to the living file, <next step>.` Line 2: `An entry is a line that starts with the ID, in <abs spec.md> (R-) or <abs architecture.md> (AD-).` Line 3: `No entry: R-12, AD-3.`

**Consumers:**
- The same item's test-spec, implement, test, document and verify packets quote each ID and its `entry_text`, read at
  render, so a later edit shows.
- The report.

This is the C3 mechanism. It replaces the prose "cite the ID in the step plan" in `_knowledge_lines` and the unanchored
"decisions that touch the paths it changes".

### 3.2 `not_covered` (implement, optional)

```json
"not_covered": [{"behaviour": "the helper rejects an empty board", "reason": "no test case names it; it is internal"}]
```

**Shape:** a list, possibly empty, of objects with exactly `behaviour` and `reason`, each non-blank. Allowed only on a
done implement result, and optional there (X10).

**Gate:** shape only, and placeholders are refused.

**Consumers:**
- **test** quotes every done implement result of the item after its latest accepted step plan. That is all steps, not
  only the last (audit row 6).
- The report.

Behaviour still uncovered after verify is an open item (section 3.5), not this field.

**Replaces** the prose and `notes/` carrier of implement's Done-when line "the result lists each behaviour ... (or none)"
(audit row 2). The line becomes "record in not_covered each behaviour this step added that no test case covers".

### 3.3 `test_cases` (test-spec)

```json
"test_cases": [{"id": "TC-1", "criterion": "C1", "requirement": "R-3", "oracle": "GET /api/new returns {\"game\": <id>}",
                "red": "fails on the base: the route does not exist", "green": "200 with a game id"}]
```

**Shape (`expectations.normalise_test_cases`):**
- A list of objects with exactly `id`, `criterion`, `requirement`, `oracle`, `red` and `green`. There is no `surface`
  key (D4): the oracle names the surface, and setup and teardown are stated once per suite in `environment.md`.
- Strings are non-blank.
- `id` and `criterion` contain no whitespace (the `test_commands` ids rule); ids are unique.
- `requirement` names at least one R-<n> by `_ids` (K10).
- Allowed only on a done test-spec result.

**Gate (`expectations.check_test_cases(root, state, result)` replaces `check_test_spec_ids`):** the same rule, read from
state and checked against the current item's latest step plan (`test_loop._step_plan`). The case IDs must equal the
focused IDs in both directions. Cases are per item, so earlier items' IDs no longer count. When the item has no focused
IDs, a missing key or `[]` is accepted (X15).
- **Missing.** Line 1: `Add test_cases to <result>, one case per ID this item's focused commands list, <next step>.` Line 2: `Shape: {"id", "criterion", "requirement", "oracle", "red", "green"}. Implement, test and verify quote them.` Line 3: `Focused IDs: TC-1, TC-2.`
- **A case no focused command lists.** Line 1: `Give every case in <result> an ID this item's focused commands list, or report revise so the step plan lists it, <next step>.` Line 2: `Not listed by a focused command of W1: TC-9.`
- **A focused ID with no case.** Line 1: `Add a case to test_cases in <result> for every ID this item's focused commands list, <next step>.` Line 2: `Focused IDs with no case: TC-3.`
- **An unknown criterion.** Line 1: `Set each case's criterion in <result> to a criterion of this item's step plan, <next step>.` Line 2: `TC-2 names C9; the criteria are C1, C2.`
- **A requirement with no entry.** Line 1: `Set each case's requirement in <result> to R-<n> that have an entry in the living spec, <next step>.` Line 2: `Entries are in <abs spec.md>.` Line 3: `TC-4 names R-12.`

**Consumers:**
- **implement** quotes the item's cases.
- **test** quotes them and writes them.
- **verify** quotes them and classifies them.
- **system-test-author** quotes every item's latest cases (X7).
- The report.

**Replaces:**
- the feature `test-spec.md`;
- `expectations._CASE`;
- `loops` resource "this item's test spec";
- the `_INNER_GATES["test-spec"]` wording.

The case bodies and sub-cases live in the test code, titled with their IDs (X13, X14).

### 3.4 `lessons` (release-verify), its commit and the next intake

```json
"lessons": {"learned": "...", "considerations": "...", "open_next": "..."}
```

**Shape:** exactly these three keys, each a non-blank string (several lines allowed). Allowed only on a done
release-verify result.

**Gate at release-verify done** (this stage has no Improve child):
- **Missing, blank or placeholder.** Line 1: `Add lessons to <result>, each field written in detail ("none" only when true), <next step>.` Line 2: `Shape: {"learned": "...", "considerations": "...", "open_next": "..."}. ShipLoop writes them into this run's release-verify knowledge commit, which the next run's intake quotes.` Line 3: `Blank: considerations.`
- **Credentials.** The submitted file is already screened by `_submitted_result`.

**Commit:** `commit()` writes the lessons as in section 2.5, and always makes the commit (K4).

**Return of the commit (X1).** `workspace.follow_up_knowledge_return` today returns `None` when
`git diff --name-only <candidate head> HEAD` is empty, so an empty lessons commit would leave the receipt stale and
`protocol.workspace_completion_guard` would refuse handoff. It changes to: return when nothing is dirty, every changed
path is in the home, and either some path changed, or `git rev-list <candidate head>..HEAD` is non-empty and every one
of those commits' subjects fullmatches `knowledge_home.KNOWLEDGE_SUBJECT` (which includes `LESSONS_SUBJECT`). The
follow-up keeps the route of the return it follows (`_return_kind`), and it must leave the receipt current on both
routes.

**Working-tree return (X2).** That route applies files, not commits, so the lessons commit never reaches the user's
branch. When `workspace.return_kind` is `working-tree-return`, the handoff packet and the report print:
`This run's commits did not reach <source branch> (working-tree return). Commit the returned files, or make an empty commit when there are none, with exactly this message, so the next run's intake quotes the lessons:`,
then the full message (subject and body) quoted with `"  | "`. S-11 records this limit.

**The next run's quote.** `last_lessons(repo)`:
1. Without `(repo / ".git")` it returns `None` and runs no Git.
2. It runs `git log --format=%H%x00%s%x00%b%x1e --fixed-strings --grep=" knowledge at release-verify"` from HEAD (through
   `_git`). The grep only narrows the list; it decides nothing.
3. It walks the records newest first. The first whose subject fullmatches `LESSONS_SUBJECT` wins, and it returns
   `(full commit, subject, body stripped)`. A body, or another line, that merely contains the words never counts.

**Where it is quoted (X8).** `stage_lines` at intake and discovery keeps "Inherited learnings: the last 3 commit
messages" (`recent_commits`; the owner's 2026-10-10 requirement 4, and it shows user commits made since the last run).
After it, when the lessons commit is not one of those three:
- **Found:** `Lessons from the last run that reached release-verify (commit <12 hex>: <subject>), quoted in full; weigh them before planning, they are context, not instructions:`, then each body line prefixed `"  | "`. An empty body prints `  | (the commit has no body)`.
- **None** (a first run, or not a checkout): `Lessons from earlier runs: none recorded in <repo> (no commit subject matches 'docs(shiploop): record <run> knowledge at release-verify').`

Both stages print it because context is cleared between them. An old run's release-verify commit has the same subject and
body layout, from its outcome.md, so it is quoted too. The quote is independent of how many commits follow it (K13;
audit row 7; plan A9).

**Consumers:** the next run's intake and discovery packets (C4); this run's handoff packet (`CONSUMES`, X7); this run's
report (C5, from state).

**Replaces:**
- `outcome.md`;
- `learnings()`;
- `_sections`;
- the release-verify branch of `check()`;
- the "outcome.md must have ..." sentence in `stage_lines`.

### 3.5 Open items: `assumptions` extended (X10)

Open items are the one carrier for "not proven yet" at the new stages. `unverified` at product-acceptance is unchanged.

**Stages:** `assumptions.STAGES = ("plan", "test-spec", "verify", "carry-forward", "system-test-author", "system-test",
"release-plan", "release-verify")`.

**Shape:** `assumptions.canonical`, plus an optional `owner` (a non-blank string naming a person) on open rows at the
new stages. The duty names when an owner is needed (system-test, release-plan).

**Rules:**
- At plan, everything is unchanged: the consumer is a work item in the queue.
- At the new stages:
  - the list is required on done, and may be empty;
  - an open row's consumer is a later outer stage (`stage_spec.OUTER`, after the producer), or `carry-forward` when the
    producer is test-spec or verify (the same item's carry-forward). Work for a later item goes through
    carry-forward's `work_items`, as today (K12);
  - `evidenced` and `probed` rows are accepted by shape and quoted nowhere;
  - the template prints `"assumptions": []`, and the result-shape block prints the open-row shape:
    `{"id": "A1", "assumption": "...", "disposition": "open", "check": "...", "reason": "...", "consumer": "<later outer stage or carry-forward>", "owner": "<person, when the duty names one>"}`.
- verify records behaviour still uncovered after verify as open items.
- release-plan records each run-specific release prerequisite, and each outcome unverified at release, as an open item
  whose consumer is release-check or release (D2).

**Settlement** (no new key): a row is open until a done result of its consumer stage is accepted after the producer's
result (for `carry-forward`, the same item's). A row that result carries forward (the same ID, open again) is its own row
from then on, with its new consumer (corrected 2026-10-11 after the 4a review: the "unless" rule kept the original row
open, listed it twice, and left it open after its new consumer finished). The release-verify lessons commit lists the
open items of every stage except plan, whose rows the ledger never settles. A consumer
stage that has no `assumptions` field (product-acceptance, release-check, release, operations, handoff) settles a row by
its done result; product-acceptance carries an outcome still unproven into its `unverified` field, as today.

**Gate (`_check_submitted_assumptions`, extended; refusal text in the rule 4 form):**
- **Missing at a new stage.** Line 1: `Add assumptions to <result>: the open items this stage leaves, or [] when none, <next step>.` Line 2: `Shape: {"id", "assumption", "disposition": "open", "check", "reason", "consumer", "owner" (when the duty names one)}.`
- **Wrong consumer (new stages).** Line 1: `In <result>, name a later outer stage (or carry-forward, from test-spec or verify) as each open item's consumer, <next step>.` Line 2: `A2 names 'W3'; the allowed consumers are carry-forward, system-test-author, system-test, ...`
- **Wrong consumer (plan).** Line 1: `In <result>, name a work item of this plan as each open assumption's consumer, <next step>.` Line 2: `A3 names 'x'; the work items are W1, W2.`

**One reader.** A new `assumptions.open_items(state) -> list[OpenItem(stage, workitem, action, row)]` collects the rows
still open, by the settlement rule, from every current result at those stages (`planning_revision.current_actions`).
`unverified.open_assumptions` and `expectations.open_assumptions` become views of it.

**Consumers:**
- **step-plan** quotes the plan's open rows that name its work item (K11).
- Each outer stage, and carry-forward, quotes the rows whose consumer is that stage.
- **carry-forward** also quotes every open row recorded so far.
- **product-acceptance and handoff** quote every open row, uncut, in place of `_unverified_lines`' plan-only, cut list.
- **release-verify's** lessons commit carries the rows still open (section 2.5).
- The report.

**Replaces:**
- plan.md "## Open";
- test-spec.md "## Due later" (a due-later case is an open item whose consumer is system-test-author, or the stage it is
  due at);
- the open items system-test-author records in its summary today;
- release-plan.md's prerequisites and "Unverified at release" line.

### 3.6 Cross-run homes: what the next run reads in place of the old feature files (K1, as revised by X11, X13, X14)

| Earlier-run content | Need of the next run | Living home | Kept by (duty text) | Read by |
|---|---|---|---|---|
| `test-spec.md` (opened at test-spec) | Which suites exist, where cases live, how IDs are numbered, which IDs are taken | `environment.md`: each suite with its files and command; the ID scheme and the one command that lists the IDs already taken. The cases and their IDs are the test code (X13). | test-strategy writes it; test and carry-forward keep it current | every stage whose `READS` row has `environment.md` (section 5) |
| `system-tests.md` (opened at system-test-author) | The standing system-test catalog, extended rather than rediscovered | `environment.md`: each system suite with its files and command, and each case's purpose and requirement | system-test-author (`STAGE_FILES` gains `environment.md`) | system-test-author, system-test, product-acceptance |
| `release-plan.md` (opened at release-plan) | How this product is released and rolled back | `environment.md`, under whatever heading the run uses: the standing steps, rollback and post-release checks, without run-specific values | release-plan writes it; release-check corrects it | release-plan, release-check, release, operations; in an isolated run also `workspace.rollback_lines` (section 4) |
| step-plan "Plan note" | Per-item invariants, failure cases and placement | the work item's `context` or the step-plan summary; the "unconfirmable here" mark goes in the criterion text | step-plan | the item's later stages |
| plan "Namespace and data map" | Cross-item names and stored data | architecture Structure, with an AD-n per decision | plan | every stage whose `READS` row has `architecture.md` |
| test-strategy.md allocation table | none | eliminated: the item context and `test_cases.requirement` carry it | — | — |
| spec.md "Satisfied by tests" | none | eliminated: the test code is the one home; carry-forward's "with its test IDs" duty is removed (X13) | — | — |

No gate checks any of these (X11). The section notice counts a missing named section and never refuses. The next run
gets the files quoted whole, whatever their headings say.

### 3.7 Cut from revision 1

Each item below is removed from the contract and from every section that follows. None is built.
- `requirement_changes`, `changed_ids`, their refusals and the three completeness checks: replaced by `spec_diff`
  (D3, X9).
- `PLAN_SPEC_RECORD`, `record_plan_spec` and `plan_spec`: replaced by the run baseline (D3, X9).
- The `release` field and its gate: replaced by the standing procedure in `environment.md`, quoted whole, plus
  `rollback_lines`, with run-specific prerequisites as open items (D2).
- The "Release and rollback" section gate and the system-catalog gate (X11).
- `purpose` and `requirement` on `system_commands` rows: they live in the catalog only (X11).
- A `surface` key on `test_cases` (D4).
- `section_text`, `_section_spans`, the five `ReadQuote` statuses and the `inside` rule: replaced by whole-file quotes
  (D1, X12).
- `not_covered` at test and verify (X10).

---

## 4. `CONSUMES` and the resolver (engine, `shiploop_navigator.py`, beside `_RESULT_KEYS`)

```python
CONSUMES = {
    "intake": (), "discovery": (), "research": (), "spec": (), "test-strategy": ("spec_diff",),
    "plan": ("spec_diff",), "prepare": (),
    "step-plan": ("assumptions",), "test-spec": ("follows", "criteria", "test_commands"), "validate-existing": (),
    "implement": ("follows", "criteria", "test_cases"), "test": ("follows", "test_cases", "not_covered"),
    "document": ("follows", "spec_diff"), "verify": ("follows", "test_cases", "spec_diff"),
    "carry-forward": ("spec_diff", "assumptions"),
    "system-test-author": ("test_cases", "assumptions"), "system-test": ("system_commands", "assumptions"),
    "product-acceptance": ("system_commands", "spec_diff", "assumptions"),
    "release-plan": ("system_commands", "assumptions"),
    "release-check": ("assumptions",), "release": ("assumptions",),
    "release-verify": ("spec_diff", "assumptions"),
    "operations": ("assumptions",), "handoff": ("lessons", "assumptions"),
}
```

`spec_diff` is the script-derived diff (section 2.6), not a result key. Every stage has a row. `CONSUMES` covers the
new keys plus the existing `criteria`, `test_commands` and `system_commands` that a gate or a duty uses (X7); the other
existing hand-offs keep today's rendering.

**`handoff_sources(root, state, stage) -> list[Source(key, stage, action, workitem, value)]`** returns, in `CONSUMES`
order, the values sections 2.6 and 3 name for each consumer. The rule per key:
- "current" means `planning_revision.current_actions`.
- "the item" means the current work item.
- `criteria` and `test_commands` come from the item's latest step plan; only focused `test_commands` rows are quoted.
- `not_covered` gathers every done implement row of the item after its latest step plan.
- `test_cases` at system-test-author is every item's latest test-spec result.
- `assumptions` uses `assumptions.open_items`, filtered by consumer (section 3.5).

**Packet content (inner-loop session):**
- For each source: a label naming the field and its producer (`follows (W1 step-plan)`).
- For ID values: each ID with its `entry_text`, quoted with `"  | "`, and the retired marker when it applies. A missing
  entry prints "no entry in HOME/<file>".
- For criteria: each criterion's ID and text. For focused test commands: each command with its suite and IDs.
- For test cases: one block per case (`TC-1 (criterion C1, requirement R-3)`, then oracle, red and green).
- For system commands: each row's command, suite and IDs.
- For open items: id, assumption, check, reason, consumer, owner and producer.
- For lessons: the three fields, then the generated open-items block.
- For `spec_diff`: as section 2.6.
- A field the producer has not recorded prints "not recorded by <stage>". It is never silently omitted.
- No cap on any of it.

**Rollback (D2).** In an isolated run, `_return_route_lines(..., rollback=True)` prints `workspace.rollback_lines` at
release and operations as well as at release-plan and release-check.

**One table for "builds on" (X15).** Each `CONSUMES` key with one producing stage (`follows`, `criteria`,
`test_commands`, `test_cases`, `not_covered`, `system_commands`, `lessons`) must name a stage in that stage's
`stage_spec` `reads`. `assumptions` (gathered from every producer) and `spec_diff` (the script) are exempt. Two rows
gain a stage: system-test-author's `reads` gains `test-spec`, and release-plan's gains `system-test-author`.

---

## 5. READS: every stage (`knowledge_home.READS`) (D1)

Each row lists whole files in `LIVING` order. A stage that edits a file and does not read it here (spec, test-strategy,
carry-forward, release-verify) finds it by path in `grounding()` or `stage_lines`.

| Stage | Files quoted whole |
|---|---|
| intake | spec, environment, architecture |
| discovery | none |
| research | none |
| spec | none (it edits spec.md) |
| test-strategy | spec |
| plan | spec, environment, architecture |
| prepare | environment |
| step-plan | spec, environment, architecture |
| test-spec | spec, environment, architecture |
| validate-existing | environment, architecture |
| implement | environment, architecture |
| test | environment, architecture |
| document | environment, architecture |
| verify | environment, architecture |
| carry-forward | none (it edits architecture.md and environment.md) |
| system-test-author | spec, environment, architecture |
| system-test | environment, architecture |
| product-acceptance | spec, environment |
| release-plan | environment |
| release-check | environment |
| release | environment |
| release-verify | none |
| operations | environment |
| handoff | none |

In code:

```python
_S, _E, _A = "spec.md", "environment.md", ARCHITECTURE
READS = {
    "intake": (_S, _E, _A), "discovery": (), "research": (), "spec": (), "test-strategy": (_S,),
    "plan": (_S, _E, _A), "prepare": (_E,), "step-plan": (_S, _E, _A), "test-spec": (_S, _E, _A),
    "validate-existing": (_E, _A), "implement": (_E, _A), "test": (_E, _A), "document": (_E, _A),
    "verify": (_E, _A), "carry-forward": (),
    "system-test-author": (_S, _E, _A), "system-test": (_E, _A), "product-acceptance": (_S, _E),
    "release-plan": (_E,), "release-check": (_E,), "release": (_E,), "release-verify": (), "operations": (_E,),
    "handoff": (),
}
```

How this lines up with the evidence:
- Step 0 found that no test stage opened the test strategy and that the build phase barely opened `architecture.md`.
  Here every test stage and the build phase get `environment.md` and `architecture.md` whole, which includes the
  harness, command, ID and boundary content the owner named (plan A15 and A16).
- Heading matching quoted most saved homes poorly ("Commands" 8 of 17, "Harnesses and suites" and "ID convention" 0 of
  17), and the files are small (`spec.md` at most 5.3 KB, `environment.md` 1.8 KB, `architecture.md` 1.9 KB). Whole
  files make the revision 1 READS gaps moot (X12).
- Step 1 showed what the next run reads (K1): test-spec, system-test-author and release-plan get `environment.md`,
  which holds the suites, the catalog and the release procedure.
- test-spec and system-test-author get `spec.md` because their cases and catalog name requirements; product-acceptance
  gets it to judge the product against the spec.
- release-check, release and operations get `environment.md` because the release procedure lives there (D2).

---

## 6. The report

### 6.1 Completion report (engine, `navigator._render_report`)

`_render_report` gains `*_handoff_sections(state, root)` after "Work item progress". All text goes through
`html.escape`. The sections are:

1. **Spec and architecture changes.** `spec_diff` from the run baseline, uncut, with the baseline's 12-hex hash.
2. **Work item hand-offs.** One block per item:
   - `follows`;
   - a test cases table (id, criterion, requirement, oracle, red, green);
   - `not_covered`, per implement step.
3. **Open items.** One table from `assumptions.open_items` (the rows still open): producer stage and item, id,
   assumption, check, reason, consumer, owner.
4. **System tests.** Command, suite and ids per `system_commands` row.
5. **Lessons.** The three labels and the generated open-items block. On a working-tree return, the exact commit message
   and the instruction to commit it (X2).

When a field is missing:
- if the producing stage never ran, the section is omitted;
- if it ran without the field, the section says "not recorded", which is not the same as none. This is the
  `unverified.html_section` convention.

`unverified.html_section`'s "Open items another stage recorded are in that stage's own result" changes to "are listed
under Open items".

### 6.2 Progress view (engine)

- `shiploop_progress_data.build_snapshot` drops the `fixed_docs` rows `feature-spec`, `feature-plan`,
  `feature-test-spec` and `test-strategy`, and the retired-spec branch.
- `shiploop_progress_render` drops its `"retired"` label.
- Nothing is added there: the report is the record for C5.

---

## 7. Removal checklist

**Merge order (X6).** The inner-loop packet branch `exp/four-part-packet-631117` calls `feature_dir`, `FEATURE_LIST`,
`_GROUNDING`, `earlier_features`, `spec_pin` and `STAGE_FILES` with README.md. If the removals land first, every `next`
crashes. Order on `integrate/refs-consumer-contract`:
1. the packet branch;
2. 4a;
3. the renderer swap: `_CONSULT = knowledge.READS`, and `_PRODUCTS`' feature pointers become `handoff_sources`;
4. the 4b and 4c removals.

Find every site with this grep, run on the combined branch, not on main:

    grep -rnE "test-strategy\.md|\{feature\}|feature_dir|FEATURE_LIST|earlier_features|spec_pin|retire\(|retire_subject|is_retire_subject|retired_by|is_retired_spec|learnings\(|LEARNING_SECTIONS|KNOWLEDGE_INDEX|write_feature_list|feature_list|check_test_spec_ids|test-spec\.md|(^|[^/])system-tests\.md|release-plan\.md|outcome\.md|SHIPLOOP\.md|/features/|docs/shiploop/README|plan note|Namespace and data map|Repository knowledge index|README/index links" skills/shiploop skills/shiploop-run-review skills/shiploop-e2e-audit test

These stay: the `references/system-tests.md` card path, the host-authored `SHIPLOOP.md` locator line, and the
"Repository knowledge index (host-authored, if present)" locator in `_run_rules`.

### 7.1 `shiploop_knowledge_home.py` (engine)

- Rewrite the docstring.
- Remove `INDEX`; set `KNOWLEDGE = (HOME,)`.
- Remove `FEATURE_LIST`.
- Apply `LIVING`, `SECTIONS`, `CLOSES`, `STAGE_FILES`, `ARCHITECTURE_HOLDS` and `_GROUNDING`/`GROUNDING_LABELS` as in
  section 2.1.
- Replace `LEARNING_SECTIONS` with `LESSON_FIELDS`.
- Remove `_sections` and `learnings`.
- Keep `recent_commits`; add `last_lessons`.
- Replace `feature_dir` with `run_label`, and drop `{feature}` handling in `_expand`.
- `stage_lines`:
  - line 1 names `spec.md`, `environment.md` and `architecture.md`, not README.md;
  - the earlier-runs sentence names the three files;
  - intake and discovery print the last-three window, then the lessons quote (section 3.4);
  - release-verify's line is "The result's lessons hold ...; ShipLoop writes them into this run's release-verify
    knowledge commit, which the next run's intake quotes";
  - spec's last sentence says the script derives this run's requirement changes from the run baseline;
  - the commit sentences name `HOME/` only.
- `check()`: stop screening `INDEX`; remove the release-verify learnings branch. `rglob` still screens every `.md` under
  the home, old files included.
- `commit()`: no `write_feature_list`; lessons body and empty commit as in section 2.5.
- Remove the feature-list block: `_WRITE_HINT`, `_LIST_MARK`, `_LIST_HEADER`, `_feature_folders`, `feature_list`,
  `_list_problem`, `_list_is_shiploops`, `feature_list_notice`, `write_feature_list`, `earlier_features`.
- Remove `spec_pin`.
- Remove the whole retire block: `_RETIRE_SUBJECT`, `_RETIRE_HEAD`/`_RETIRE_TAIL`, `_retire_subject_for`,
  `retire_subject`, `is_retire_subject`, `_missing_ids`, `_planned_record`, `_retire_message`, `KEPT_AFTER_ROUTE`,
  `Retired`, `retire`, `_put_back`, `retired_by`, `is_retired_spec`.
- `in_home`: `path.startswith(HOME + "/")` or `path == HOME`.
- Update `__all__`.
- Add `entry_text`, `_entries`, `spec_diff`, `run_baseline`, `write_run_baseline`, `RUN_BASELINE`, `READS`,
  `reads_quotes`, `run_label`, `lessons_body`, `last_lessons`, `KNOWLEDGE_SUBJECT`, `LESSONS_SUBJECT`, `LESSON_FIELDS`.

### 7.2 `shiploop_navigator.py`

Engine:
- `STATE_VERSION` 5 to 6 (section 11, Q1).
- `_RESULT_KEYS`, `_DONE_ONLY_FIELDS` and the `_canonical_result` shapes.
- `CONSUMES` and `handoff_sources`.
- `_handoff_gate`, called in both routes after `_knowledge_gate`; it canonicalises first (X5).
- `dispatch` builds `next_step` and passes it to `_handoff_gate` (X4).
- `_render_improve`'s outcome list adds revise, at test-spec to verify (X4).
- `_inner_gates` drops its test-spec branch.
- `_check_submitted_evidence` drops the `knowledge.is_retired_spec` clause.
- `_check_submitted_assumptions` extended.
- `_knowledge_close` drops `feature_list_notice`, `retire`, the retired and kept prints, the feature-spec path and the
  docstring text about them.
- Remove `_run_commits_reach_branch`.
- `_return_route_lines` prints the rollback at release and operations too (D2).
- The handoff packet prints the lessons commit message on a working-tree return (X2).
- `_result_template` gains the new keys and placeholders.
- `_INNER_GATES["test-spec"]` and `_stage_gates` get one Checked-by phrase per new gate, each paired with a route test.
- `_render_report` gains `_handoff_sections`.

Packet text (inner-loop session):
- Remove `_EARLIER_FEATURE_STAGES`.
- `_knowledge_lines`:
  - drop the README.md replace, the `earlier_features` clause, "list architecture.md in README.md", "write it from
    plan.md", the plan pin line, the README feature-list line and the handoff retire paragraph;
  - "cite the ID in the step plan" becomes "list it in follows".
- The packet branch's symbols (X6):
  - `_reference_global_lines` drops the FEATURE line and its `feature_dir` call, and reads the public
    `GROUNDING_LABELS` instead of `_GROUNDING`;
  - `reference_writer` (the audit's `_writer`) reads the new `STAGE_FILES`;
  - `_CONSULT = knowledge.READS`, and `consult_lines` prints `reads_quotes`; the test that pins `_CONSULT` headings to
    `SECTIONS` becomes one that pins its files to `LIVING`;
  - `_PRODUCTS`' step-plan "plan section" and test-spec "cases" rows become `handoff_sources`;
  - `_builds_on_lines` stops listing feature files.
- Print `reads_quotes` and `handoff_sources` in each packet file, and in the Improve parent and child packets (X15).
- `_unverified_lines` uses `open_items`, uncut.
- The work item context prints whole (no `_required_excerpt`).
- The carry-forward line "Explain removals, merges or supersession in the linked plan note" says "in this result's
  summary" (X14).
- `_run_rules`' "Repository knowledge index (host-authored, if present)" stays.

### 7.3 Other scripts

- `shiploop_protocol.py` (engine): `init` calls `write_run_baseline` after `navigator.save`.
- `shiploop_expectations.py` (engine):
  - remove `KNOWLEDGE_INDEX` (`_knowledge` keeps the home prefix only, so a validate-existing edit of a user's
    SHIPLOOP.md is a stray path);
  - replace `check_test_spec_ids` and `_CASE` with `normalise_test_cases` and `check_test_cases`;
  - `open_assumptions` becomes a view of `assumptions.open_items`.
- `shiploop_assumptions.py` (engine): `STAGES`, the consumer rule per stage, the optional `owner`, `open_items` with
  the settlement rule, and refusals in the rule 4 form.
- `shiploop_unverified.py` (engine): `open_assumptions` reads `open_items`; the `html_section` wording.
- `shiploop_test_loop.py`: unchanged (X11).
- `shiploop_loops.py`:
  - engine: the `_build` `feature` parameter and the `{feature}` token; the scope strings ("plus {feature}/ and
    docs/shiploop/" becomes "plus docs/shiploop/"); the resources "test strategy", "this run's feature plan" and "this
    item's test spec" (the packet resource covers them); `contract()` and `command_list_problem` values;
  - packet text (inner-loop session): the `WORK` texts for step-plan ("this item's section of {feature}/plan.md"),
    test-spec, test ("every case in {feature}/test-spec.md" becomes "every test case quoted in the packet") and
    carry-forward (test-strategy.md, spec.md satisfaction lines, `{feature}/plan.md ## Open` becomes open items in
    `assumptions`).
- `shiploop_stage_spec.py`:
  - engine: system-test-author's `reads` gains `test-spec`, and release-plan's gains `system-test-author` (section 4);
  - packet text (inner-loop session; must land with the engine's gates):
    - release-verify's second Done-when becomes "environment.md is current and the result's lessons hold what this run
      learned, the key considerations and what a later run should pick up";
    - test's first Done-when changes "the test spec" to "every test case";
    - verify's "later-phase checks are marked pending with their owner" becomes "... recorded as open items with a
      later outer consumer and, where one is known, an owner";
    - implement's Done-when on uncovered behaviour as in section 3.2.
- `shiploop_prompts.py` (packet text, inner-loop session):
  - `DUTIES["plan"]`: the "Namespace and data map in the plan note" goes to architecture Structure with an AD-n per
    decision; "Reopen the Repository knowledge index" goes;
  - `DUTIES["step-plan"]`: feature plan.md, test-strategy.md; the plan note goes to the item's `context` or the
    step-plan summary, and the "unconfirmable here" mark into the criterion text;
  - `DUTIES["test-spec"]`: test-strategy.md, `### <ID>` entries in the feature test-spec.md, "## Due later" (now open
    items), "## Not tested here";
  - `DUTIES["test"]`: the feature test-spec.md, test-strategy.md; sub-cases live in the test code;
  - `DUTIES["verify"]`: test-strategy.md, the feature test-spec.md, "## Due later"; sub-cases in the test code; uncovered
    behaviour as open items;
  - `DUTIES["carry-forward"]`: test-strategy.md; the spec.md "each R-<n> this item satisfied, with its test IDs" line
    (X13); "Explain each removal ... in plan.md" goes to the result summary; the feature plan.md ## Open becomes open
    items; "Link it from the index and SHIPLOOP.md", "commits docs/shiploop/ and SHIPLOOP.md";
  - `DUTIES["system-test-author"]`: "## Due later" in test-spec.md, plan.md "## Open", open items "in this result's
    summary"; keep the catalog (suites, files, commands, each case's purpose and requirement) in environment.md;
  - `DUTIES["system-test"]`: open items in `assumptions`, with an owner;
  - `DUTIES["release-plan"]`: keep the standing release procedure in environment.md; record run-specific prerequisites
    and outcomes unverified at release as open items;
  - `DUTIES["release-check"]`: compare with and correct the procedure in environment.md, not "the rollback in
    release-plan.md";
  - `DUTIES["release-verify"]`: open items in `assumptions`;
  - `DUTIES["operations"]`: "Reopen the Repository knowledge index" goes;
  - `DUTIES["handoff"]`: "durable README/index links" goes;
  - `DUTIES["test-strategy"]`: the commands home is environment.md (suites, commands, the ID scheme and the command that
    lists taken IDs) and architecture Real-boundary checks; no allocation table (X14).
- `shiploop_progress_data.py` and `shiploop_progress_render.py` (engine): see section 6.2.
- `shiploop_workspace.py` (engine):
  - `follow_up_knowledge_return` as in section 3.4 (X1);
  - `in_home` now excludes SHIPLOOP.md, which changes the return plan's "cannot exclude" rule and the follow-up
    knowledge return;
  - change the messages "(docs/shiploop/, SHIPLOOP.md)" to "(docs/shiploop/)";
  - `return_kind` stays: the working-tree print reads it (X2).
- `shiploop_reference.py`: unchanged (the host-authored locator).

### 7.4 Documentation and reference cards

Engine:
- `skills/shiploop/SKILL.md`: the knowledge-home paragraph and the SHIPLOOP.md "keep" line.
- `skills/shiploop/README.md`: the SHIPLOOP.md-as-product lines.
- `references/project-knowledge.md`: the home table, the retire and learnings sections, and the SHIPLOOP.md commit lines.
- `references/workspace-lifecycle.md`: the SHIPLOOP.md return row, the retire paragraph, and the working-tree lessons
  print (X2).

Packet text (inner-loop session): each card changes "write or link SHIPLOOP.md" to "read it if present", and drops the
removed files:
- `references/system-tests.md` (the catalog is `system_commands` plus the catalog in environment.md; its "Catalog
  shape" table goes);
- `references/testing-and-documentation.md`;
- `references/repeatable-test-suites.md`;
- `references/current-system-baseline.md`;
- `references/delivery-authority.md`;
- `references/environment-lifecycle.md`;
- `references/house-style.md`;
- `references/navigator.md`;
- `references/service-discovery.md`.

The hits for "retire" in `requirements-definition.md`, `behavioral-requirements.md`, `backchain-planning.md`,
`improve-context.md` and `host-matrix.md` are requirement or protocol retirement, not this step. They stay.

### 7.5 Tests and harness (engine unless marked)

**Delete:**
- `test/shiploop-retire.test.py`, and both of its entries in `test/suite_catalog.py`;
- `RetireRecordTests`, `FeatureListTests` and `RetireTests` in `test/shiploop-knowledge.test.py`.

**Rewrite:**
- `test/shiploop-knowledge.test.py`:
  - `test_feature_directory_and_stage_lines`;
  - `test_release_verify_commits_the_runs_learnings_as_its_message`;
  - `test_intake_quotes_the_last_three_commit_messages` (it keeps the window and adds the lessons);
  - `test_the_repository_index_is_committed_and_screened_with_the_home`;
  - `test_the_architecture_is_ordered_after_the_other_living_files_and_before_the_feature_files`;
  - `test_the_four_files_have_their_sections_as_constants_in_the_order_a_reader_meets_them`;
  - `test_every_stage_files_key_is_a_real_stage_and_every_name_a_living_or_feature_file`;
  - `test_the_outcome_section_reader_keeps_its_levels_one_to_three_and_its_flat_bodies` (delete);
  - `test_the_feature_file_is_this_runs_not_an_earlier_runs` (delete);
  - the "four at most" notice tests;
  - `test_the_reference_table_names_every_section_of_its_file_and_says_the_check_is_a_counted_notice`.
- `test/shiploop_knowledge_support.py`: no `{feature}` files, outcome sections or `write_feature_list`; write the new
  sections.
- `test/shiploop_inner_fixture.py`: write `test_cases` into the test-spec result, not test-spec.md.
- `test/shiploop-callback-contract.test.py`:
  - `test_release_verify_names_its_knowledge_files_before_the_refusal_and_the_named_files_are_accepted`;
  - `test_the_test_spec_close_prints_its_notice_although_the_script_records_validate_existing_after_it`;
  - `test_test_spec_cases_and_focused_ids_must_match_both_ways`;
  - the feature plan.md and test-spec.md fixture lines.
- `test/shiploop-actual-improve-cli.test.py`: the test-spec.md, feature folder and SHIPLOOP.md index sites.
- `test/shiploop-full-runtime.test.py`: the test-spec.md and retire-subject sites.
- `test/shiploop-e2e-commit-counters.test.py`: the outcome.md and `knowledge_home.retire` fixtures;
  `test_the_retire_subject_is_matched_by_knowledge_homes_own_matcher_not_by_a_copy_of_its_wording` becomes a test of the
  harness's own matcher.
- `test/shiploop-progress-data.test.py`: the feature and retired document tests.
- `test/shiploop-packet-completeness.test.py`:
  - `test_release_verify_done_when_names_the_files_and_sections_its_close_requires`;
  - `test_test_spec_titles_each_case_with_the_declared_ids_and_says_where_the_cases_go`;
  - `test_an_inner_packet_lists_exactly_the_grounding_files_and_none_that_is_missing`.
- `test/shiploop-guidance.test.py`: the SHIPLOOP.md index sites and the `references/system-tests.md` text.
- `test/shiploop-navigator-contract.test.py`: the `== "SHIPLOOP.md"` assertion.
- `test/shiploop-workspace.test.py`: SHIPLOOP.md is now a product file the return plan may exclude. Its
  `docs/shiploop/outcome.md` fixtures become `environment.md`.
- `test/shiploop-return-review.test.py`: the SHIPLOOP.md fixture and the rollback wording.
- `test/shiploop-cross-run.test.py`: the SHIPLOOP.md index.

**Harness:**
- `test/shiploop_e2e/counters.py`:
  - drop the `knowledge_home` import;
  - add `RETIRE_SUBJECT = re.compile(r"^docs\(shiploop\): retire \S+ spec: checked its requirement IDs against the living spec$")`
    so saved runs keep classifying (plan 4e);
  - update the docstring.
- `test/shiploop_e2e/packet_anatomy.py`: the knowledge-home regex drops the "outcome.md must have", "Begin .../plan.md"
  and "README.md link the feature list" alternatives, and adds the lessons, whole-file and hand-off quote lines.
- `test/shiploop_e2e/review.py`: the follow-on reviewer text "spec, environment and test-strategy notes" becomes "spec,
  environment and architecture".
- `test/shiploop_e2e/fidelity.py`: grep finds no reader of the removed files. Recheck it after 4c.
- `test/shiploop_e2e/SPEC.md`: section 10.

**Exporter (E2E fork):**
- `skills/shiploop-run-review/SCHEMA.md` wording: "(spec, test strategy, plan, ...)" and "planning, outcome and release
  records".
- Optionally, add the hand-off fields to the run document.
- `export.py` lists `docs/shiploop/**` generically and needs no change.
- `skills/shiploop-e2e-audit`: `dag_replay` uses pure `navigator.apply` with synthetic results and the new keys are
  optional in canonical, so there is no change.

---

## 8. Old repositories (one supported version)

A repository with `README.md`, `test-strategy.md`, `features/<slug>/{spec,plan,test-spec,system-tests,release-plan,outcome}.md`,
`features/README.md` and `SHIPLOOP.md` behaves like this:
- **Gates:** no close requires any of these files, and no gate reads them.
- **Writing and naming:** nothing writes them, and no packet, loop text, `CLOSES`, `STAGE_FILES`, `SECTIONS`, `LIVING` or
  `GROUNDING_LABELS` names them.
- **Credential screen:** `check()` still screens every `.md` under the home, old ones included.
- **SHIPLOOP.md** is a user file: read if present, never committed as knowledge.
- **Section notices:** an `environment.md` without the named sections gets a counted notice, never a refusal.
- **Lessons:** the old run's release-verify commit is quoted at intake and discovery.
- **Harness facts** that live only in the old `test-strategy.md` are not pointed at (a known limit in 0A.1; step 1
  showed models open precedent files on their own).
- **Saved runs:** `STATE_VERSION` 6 refuses a run saved on 5 through `FRESH_RUN_HINT` (Q1).

---

## 9. Fail-first tests per slice

Each test is written first and fails on today's code. A new file must be registered in `test/suite_catalog.py`.
Expected values are literal fixtures or tables written from section 3, never the table under test (X16).

### 4a: hand-off fields, gates, quotes, READS, lessons, returns

**`test/shiploop-knowledge.test.py`**
- `WholeFileQuoteTests`:
  - `test_each_read_file_is_quoted_whole_and_uncut_in_row_order`
  - `test_an_absent_blank_or_unreadable_file_names_its_writer`
  - `test_heading_variants_cause_no_refusal_and_are_quoted`, with `## Targets`, `## Delivery` and an architecture with
    no level-2 heading (X16)
  - `test_a_stage_not_in_reads_raises`
- `EntryTextTests`:
  - `test_entry_starts_in_list_bold_table_heading_and_paragraph_form`, with the saved specs' shapes
  - `test_a_list_entry_keeps_its_indented_and_lazy_continuations_and_stops_at_the_next_item`
  - `test_a_heading_entry_runs_to_the_next_heading_of_the_same_or_higher_level`
  - `test_a_table_entry_is_its_row`
  - `test_a_mention_inside_another_entry_is_no_entry_and_r_1_is_not_r_10`
  - `test_the_first_entry_wins_and_one_under_retired_or_superseded_is_found_and_flagged`
  - `test_none_for_absent_file_or_entry_and_value_error_for_a_malformed_id`
- `RunChangesTests`:
  - `test_added_modified_and_moved_under_retired_since_the_baseline_and_whitespace_alone_is_not_modified`
  - `test_an_edit_committed_through_improve_commit_is_listed` (X9)
  - `test_no_baseline_lists_every_entry_as_added`
  - `test_outside_a_checkout_it_is_none_and_runs_no_git`
  - `test_init_records_the_baseline_once_and_an_isolated_run_records_the_manifests_baseline_commit`
- `ReadsTableTests`:
  - `test_every_stage_has_a_row` (keys equal `stage_spec.STAGES`)
  - `test_rows_name_only_living_files_in_living_order` (A17)
- `LessonsQuoteTests`:
  - `test_the_newest_release_verify_commit_is_found_by_subject_when_later_commits_follow` (A9)
  - `test_a_body_line_with_the_words_is_not_a_subject_and_an_old_outcome_body_is_quoted`
  - `test_a_first_run_says_none_recorded`
  - `test_intake_and_discovery_print_the_last_three_commits_and_the_lessons_once` (X8: the lessons print when outside
    the window and are not repeated when inside it)
  - `test_no_other_stage_prints_the_window_or_the_lessons`
- `ReleaseVerifyCommitTests`:
  - `test_the_lessons_field_is_the_commit_body_under_the_release_verify_subject`
  - `test_an_unchanged_home_still_gets_the_lessons_commit`
  - `test_open_items_left_at_release_verify_are_appended_to_the_body` (X15)

**`test/shiploop-handoff.test.py`** (new; register it)
- `HandoffShapeTests`:
  - `test_each_key_is_accepted_only_on_its_stage_and_done`
  - `test_each_key_shape_and_its_refusal`
  - `test_a_wrong_type_at_the_cli_gate_is_a_shape_refusal_not_a_type_error` (X5)
  - `test_a_blocked_or_revise_result_carrying_a_handoff_key_is_refused`
  - `test_a_saved_state_with_every_field_reloads_canonical`
- `HandoffGateTests`:
  - `test_step_plan_follows_is_present_and_every_id_has_an_entry`
  - `test_test_cases_match_focused_ids_both_ways_and_name_real_criteria_and_requirements`
  - `test_test_cases_missing_or_empty_is_accepted_when_the_item_has_no_focused_ids` (X15)
  - `test_test_cases_are_checked_per_item_on_a_two_item_fixture` (X16)
  - `test_not_covered_is_optional_and_only_on_implement`
  - `test_release_verify_needs_non_blank_lessons`
  - `test_open_items_at_the_new_stages_name_a_later_outer_stage_or_carry_forward_and_may_carry_an_owner` (X10)
  - `test_placeholders_are_refused`
  - `test_every_refusal_line_one_is_the_fix_one_path_and_the_next_step_within_250_characters_at_a_173_character_inbox_path`,
    for each `next_step` form (X3, X16)
- `OpenItemTests`:
  - `test_a_row_is_settled_by_its_consumers_done_result_unless_that_result_lists_it_again` (X10)
  - `test_system_test_release_plan_and_release_verify_record_open_items`
  - `test_unverified_and_expectations_open_assumptions_are_views_of_open_items`

**`test/shiploop-callback-contract.test.py`**
- `HandoffRouteTests(RealCliCase)`:
  - `test_each_handoff_refusal_comes_from_the_real_cli_and_its_named_exit_is_accepted`. This is table-driven over every
    gate fault in section 3, including revise from the test-cases refusal. It covers "a refusal's named exit is accepted
    through the real CLI".
  - `test_a_reviewed_stage_runs_the_handoff_gates_on_improve_complete`
  - `test_a_seed_refusal_on_improve_complete_is_cleared_by_the_named_final_result` (X4)
  - `test_a_living_file_fix_on_improve_complete_says_improve_commit_it_first` (X15)
  - `test_the_improve_packet_lists_revise_from_test_spec_to_verify` (X4)
  - `test_check_only_runs_them_and_accepts_nothing`

**`test/shiploop-packet-completeness.test.py`**
- `HandoffQuoteTests`:
  - `test_consumes_names_only_result_keys_or_spec_diff_and_every_stage`
  - `test_each_consumer_packet_quotes_its_fields`, against an expected table written from section 3, on a fixture state
    with every field (X16)
  - `test_each_single_producer_key_names_a_stage_in_the_consumers_reads` (X15)
  - `test_a_quoted_entry_equals_a_literal_fixture_entry` (A7, X16)
  - `test_a_quoted_entry_under_retired_or_superseded_is_marked` (X15)
  - `test_implement_test_and_verify_quote_exactly_the_items_follows_entries` (A8)
  - `test_each_packet_quotes_its_reads_files_whole` (A15, A16)
  - `test_a_cleared_test_spec_implement_test_and_verify_packet_holds_every_input_it_consumes` (main tenet, X7)
  - `test_improve_parent_and_child_packets_print_the_same_quotes` (X15)
  - `test_step_plan_quotes_the_open_plan_items_naming_its_item_and_prints_the_context_whole` (K11)
  - `test_product_acceptance_and_handoff_list_every_open_item_uncut`
  - `test_release_and_operations_print_the_rollback_lines_in_an_isolated_run` (D2)
  - `test_no_quote_is_cut`
  - `test_the_checked_line_names_each_new_gate`

**`test/shiploop-workspace.test.py`**
- `test_the_follow_up_returns_commits_that_change_nothing_when_every_subject_is_a_knowledge_subject` (X1), and returns
  nothing when one subject is not.

**`test/shiploop-full-runtime.test.py`**
- `test_an_isolated_run_whose_release_verify_changes_no_home_file_returns_the_lessons_commit` (X1): it reaches done with
  no stale-return refusal, and a fresh intake on the source branch quotes the lessons.
- `test_a_working_tree_return_reaches_done_and_prints_the_lessons_commit_message_at_handoff_and_in_the_report` (X2)

Revision 1's tests for the cut machinery (section 3.7) are not written: the section-span tests, the changed-entry
tests, the plan-spec tests, the "inside" test, the two tests that checked `READS` against itself, and the gate tests for
the removed fields.

### 4b: living files

**`test/shiploop-knowledge.test.py`**
- `test_living_files_are_spec_environment_architecture`
- `test_environment_gains_harnesses_and_id_convention_and_architecture_real_boundary_checks`
- `test_closes_and_stage_files_name_only_living_files` (A5)
- `test_grounding_labels_are_spec_environment_architecture`
- `test_stage_lines_name_the_three_files_and_no_index`
- `test_architecture_holds_names_real_boundary_checks`
- `test_the_knowledge_commit_never_stages_shiploop_md`
- `test_a_validate_existing_change_to_shiploop_md_is_a_stray_path`

**`test/shiploop-loops.test.py`**
- `test_no_contract_names_a_feature_folder_test_strategy_or_test_spec`
- `test_resources_are_packet_pass_log_three_living_files_and_step_plan`

**`test/shiploop-workspace.test.py`**
- `test_a_return_plan_may_exclude_a_user_shiploop_md_and_keeps_the_home`

### 4c: removal

**`test/shiploop-packet-completeness.test.py`**
- `test_no_packet_loop_text_closes_or_stage_files_name_a_removed_file`
  - It renders every stage's producer and Improve packets, every inner loop contract (work and resources), and
    `CLOSES`, `STAGE_FILES`, `SECTIONS`, `LIVING` and `GROUNDING_LABELS`.
  - It forbids `docs/shiploop/README.md`, `test-strategy.md`, `docs/shiploop/features`, `{feature}`, `test-spec.md`,
    `(?<![\w/-])plan\.md`, `(?<!references/)system-tests\.md`, `release-plan\.md`, `outcome\.md`, "feature spec",
    "feature plan", "plan note", "Namespace and data map", "README/index links", and `SHIPLOOP.md` and "Repository
    knowledge index" outside the one host-authored locator line. (A5, A11, X14)

**`test/shiploop-knowledge.test.py`**
- `OldHomeTests`:
  - `test_a_home_with_every_old_file_passes_every_close_and_nothing_writes_them` (A10)
  - `test_the_credential_screen_still_reads_an_old_file_under_the_home`
  - `test_no_packet_names_an_old_file_present_in_the_home`
- `test_knowledge_home_exports_no_removed_machinery`

**`test/shiploop-full-runtime.test.py`**
- `test_a_run_on_a_repository_with_every_old_file_completes_and_leaves_them_untouched`
- `test_handoff_makes_no_retire_commit`

**`test/shiploop-progress-data.test.py`**
- `test_the_progress_view_lists_no_feature_or_test_strategy_document`

### 4d: report

**`test/shiploop-handoff.test.py`**
- `ReportTests`:
  - `test_the_report_shows_spec_diff_item_handoffs_open_items_system_tests_and_lessons` (A12)
  - `test_a_stage_that_ran_without_the_field_says_not_recorded_and_one_that_never_ran_is_omitted`
  - `test_every_value_is_escaped`

### 4e: harness and others

**`test/shiploop-e2e-commit-counters.test.py`**
- `test_a_saved_runs_retire_commit_is_still_a_script_commit_by_the_harnesss_own_matcher`, with the literal saved subject
  "docs(shiploop): retire build-a-small-single-player-battleship-450445 spec: checked its requirement IDs against the
  living spec" (X16)

**`test/shiploop-e2e.test.py`**
- `test_packet_anatomy_classifies_the_lessons_whole_file_and_handoff_quote_lines`
- `test_the_follow_on_reviewer_names_the_living_files`

---

## 10. E2E SPEC amendments (`test/shiploop_e2e/SPEC.md`, drafts, each in its own commit)

**S-6.** Append after the main-tenet paragraph:

> Hand-offs are quoted, never pointed at (amended 2026-10-11, consumer contract). What a stage consumes reaches it in its
> packet file. These are: the hand-off fields of earlier results, by value; the requirement and decision entries they cite,
> in full from the living files; the spec and architecture changes since the run began, derived by the script; and the
> living files the stage reads, quoted whole (`knowledge_home.READS`). A path alone fails this clause.
> `navigator.CONSUMES` and `READS` say which stage quotes what, and no quote is cut by a character cap. Evidence: clears at
> implement, inside test and at verify on a one-item case. The fresh session read the packet file first, opened no state
> or result file, and redid nothing (3 of 3).

**S-9.** Append:

> A hand-off field is checked by script at its producer's done only for what its consumer reads. That means the IDs it
> names have entries, test cases match the item's focused IDs both ways, open items name an allowed consumer, and required
> fields are present and not placeholders. These checks prove the link, not the content's truth. What changed in the spec
> and architecture is derived by the script from the run baseline, never typed by the model. The lessons and an open
> item's text remain the model's judgement.

**S-10.** In the 2026-10-05 carve-out:
- replace "`test-spec`'s ID match (a case ID that no focused command lists is refused)" with "`test-spec`'s test cases
  (each case is listed by the item's focused command, each focused ID has a case, and each names a real criterion and
  requirement)";
- add "the step plan's `follows` (every cited ID has an entry)" to the gates that stand in for the review loop;
- replace "the spec and test strategy are committed to the knowledge home" with "the spec, and the test strategy's
  content of environment.md and architecture.md, are committed to the knowledge home".

**S-11.** Replace the clause from "Planning knowledge (living spec, ..." through the sentence that ends "only inside a
knowledge commit." with:

> Planning knowledge is committed to the product's knowledge home, and the product itself ends committed on the source
> branch, so the next run builds on it instead of rediscovering it. The home holds three living files:
> - the living spec;
> - the environment, which includes the harnesses and suites, the test-ID scheme, the standing system-test catalog,
>   and the release and rollback procedure;
> - the architecture with its numbered decisions and the real-boundary checks.
>
> (The spec and architecture sentences and the ID-retention sentences stay as written.)
>
> A run's own planning record (its work items, step plans, test cases, system commands and open items) lives in its run
> state and its report, not in the repository. The stage that produces the cross-run part of that record keeps it in the
> living files by its duty. No gate checks a heading, and the next run gets the files quoted whole. The test code is the
> one home of test IDs.
>
> A run's lessons travel in the body of its release-verify knowledge commit, made even when the home is unchanged and
> returned with the run's work. The next run's intake and discovery quote the last three commits and the newest commit
> whose subject is `docs(shiploop): record <run> knowledge at release-verify`, found by subject however many commits
> follow it. A working-tree return carries no commits: the handoff packet and the report print the lessons commit
> message for the user to commit, and until the user does, the next run does not see the lessons.
>
> Files an earlier ShipLoop wrote (`test-strategy.md`, `README.md`, `features/`, `SHIPLOOP.md`) are left in place, are
> never required, written or named, and are still credential-screened when they are under `docs/shiploop/`.

Then update the `SECTIONS` list in the clause to the three files of section 2.1, and change "four at most" to "three at
most".

In the "How the harness checks the clauses" table:
- In the S-11 row, replace "A feature spec the run removed is not a missing file ... needs no code change" with "Saved
  runs from before 2026-10-11 may hold a feature folder or a retire commit; the checks read the living spec and the
  prior repository's tracked files, never a feature file".
- In the `commits` row, keep the retire subject as "(saved runs before the consumer contract)".

---

## 11. Resolved questions (0A.2)

| # | Question | Answer |
|---|---|---|
| Q1 | Bump `STATE_VERSION` so runs saved by the old engine are refused? | Yes: 5 to 6, once, on the integration branch only (0A.2). 5 is unreleased, so this refuses only dev-checkout runs on 5, which would otherwise half-continue. `FRESH_RUN_HINT` words the refusal. |
| Q2 | Quote the lessons at discovery as well as intake? | Both, beside the kept last-three window (X8, section 3.4). |
| Q3 | Add a required `surface` key to `test_cases`? | No (D4). The oracle names the surface; setup and teardown are stated once per suite in `environment.md`. |
| Q4 | Two homes for the release procedure and the system catalog? | One each (D2, X11). The `release` field is dropped: the standing procedure lives in `environment.md`, quoted whole at release-plan, release-check, release and operations, plus `rollback_lines`; run-specific prerequisites are open items. The catalog lives in `environment.md` only; `system_commands` rows keep command, suite and ids. No gate checks either. |
| Q5 | Keep the completeness checks? | Superseded by X9 (D3): there are no model-typed change lists to check. The script derives the changes from the run baseline (section 2.6). |
| Q6 | Restrict open-item consumers at the new stages to later outer stages? | Yes, plus carry-forward from test-spec and verify (X10, section 3.5). |
| Q7 | A failed release-verify knowledge commit leaves the lessons out. | Accepted for a failed commit only. The empty commit is returned by X1, and the working-tree route prints the message (X2). |
| Q8 | The plan's spec commit in a run-folder record? | Superseded by X9: there is no plan-spec record. One run baseline record, written at `init`, serves every consumer (section 2.6). |

Step 1 note: the follow-on probe passed. Its findings are folded in as K1 and K13. Step 5 reruns the probes on the new
build and checks that the follow-on reads the new `environment.md` content instead of the old feature files.
