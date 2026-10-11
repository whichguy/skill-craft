---
Execute: ask
---

# Plan: ShipLoop's artifacts, designed for their consumers

Owner directive (2026-10-11, general): every outcome is produced because a named consumer wants to read it, in the form and at the moment that consumer reads it; an output with no consumer is not produced. This plan applies that directive to what ShipLoop leaves in the user's repository (Layer 2 of `docs/shiploop-artifact-flow-2026-10-11.md`). It also applies it to how one stage hands work to the next. ShipLoop's own state management (the run folder) is a separate topic and stays as it is, except where a hand-off field is added to it.

## 1. Why

The artifact-flow audit (66 claims checked, 23 corrected) found that Layer 2 mixes three jobs:
- the hand-off from planning to implementation inside one run;
- the memory a later run needs;
- a record for people.

Only the memory job is served well by files in the repository. The hand-off that implementation actually consumes already lives as structured fields in the run's state, which scripts check and quote into packets. The markdown copies in the feature folder restate them. Several Layer 2 files have no reader the engine depends on: `SHIPLOOP.md`, `release-plan.md`, `system-tests.md`, `features/README.md`, and the free-text `README.md` index. Meanwhile, what a later stage most needs is passed as a path to prose that nothing checks: decisions, open questions, behaviour left uncovered.

## 2. The consumers (the design starts here)

| Consumer | Reads when | Needs | Form it reads |
|---|---|---|---|
| C1 ShipLoop's scripts (the gates) | At a stage's done | Criteria, test case IDs, commands, expectations, paths | Typed fields, checked when written |
| C2 The next stage in the same run, with context cleared | At the start of its packet | Only its own inputs: binding decisions, criteria, open questions, uncovered behaviour, commands | Short excerpts the script quotes into the packet; never a path it must go and read |
| C3 The implementation stages (implement, test, verify) | Per work item | The item's criteria tied to test IDs and commands; the architecture decisions that touch the paths it changes | The same excerpts, filtered to the item by the script |
| C4 The next run on the same repository, cold, days later | Intake and planning | What must hold, how to build and run it, why it is built this way, what was learned and left open | Three living files with fixed headings, plus commit messages |
| C5 The owner or a reviewer | After a run | What was done, what passed, what is open | One readable report per run |
| C6 The E2E harness and Run Review | After a run | Counters and records | The run folder and the repository's history |

## 3. The proposed shape (to be confirmed by the probes and the audit in steps 1 to 3)

**Kept, as living files, for C4:**
- `docs/shiploop/spec.md`: the contract, with stable `R-<n>` IDs.
- `docs/shiploop/environment.md`: how to build, run and test. It absorbs the commands, harnesses and ID convention that `test-strategy.md` holds today.
- `docs/shiploop/architecture.md`: stack, structure, conventions, interfaces, and `AD-<n>` decisions. It absorbs the test seams from `test-strategy.md`.

Each keeps its `SECTIONS` headings and its ID retention check.

**Added, a hand-off contract for C2 and C3:** structured result fields that the script quotes forward:
- `decisions[]`: an ID or a sentence that binds later stages, with the stage it binds;
- `open_questions[]`: each with an owner and the stage expected to settle it;
- `not_covered[]`: behaviour knowingly left untested, with the reason.

Each field has one producer stage, one gate that checks its shape at that stage's done, and a declared list of consuming stages whose packets quote it. The candidate list comes from the artifact-flow audit: Done-when lines with no carrier, stale summaries, carry-forward's unlisted files, and earlier implement steps dropping out of the reads.

**Kept, the record for C5:** the engine's `report.html`, extended to show the hand-off fields and the test cases. Lessons go in commit messages. Release-verify's learnings commit already carries them, and the plan's `Spec: ... @ <sha>` first line moves into a state field.

**Removed (no consumer, or a consumer better served above):**
- the per-run feature folder (`features/<slug>/{spec,plan,test-spec,system-tests,release-plan,outcome}.md`);
- the retire step and the generated `features/README.md` (they exist only because of the folder);
- `test-strategy.md` (merged into the two living files above);
- the knowledge `README.md` index and `SHIPLOOP.md`;
- the closes' required-file lists that name them.

**Open design choice: test cases (`test-spec.md`).** Today the test gate reads its `### <ID>` entries. Either the test cases become a state field (C1 and C3 read them, the report shows them for C5, and the tests carry the IDs in code), or the file stays as the one per-run file because a gate consumes it. The audit in step 3 recommends one; the owner decides.

## 4. Steps

### Step 0: consumer-read measure (harness evidence script, no engine change)
- A read-only script under `docs/experiments/consumer-reads-20261011/` that classifies, from a saved run's events, every file the model opened by artifact family and stage: each living file, each feature-folder file, `results/*.md`, `state.md`, the packet file, `context-index.md`, `report.html`.
- Run it over the saved runs from 2026-10-10 and 2026-10-11 as the baseline.
- This makes "who consumes it" observable instead of argued.
- No harness change yet. If the counts prove useful, fold them into `metrics.json` in step 4.

### Step 1: probe the next-run consumer (C4) on the current build
- A fresh `battleship` run, then `battleship-scoring --continue-from <that output>`. This is the existing follow-on case: it runs in a copy of the earlier repository and checks retention.
- Claude Sonnet 5.5, `--source checkout`. Expected cost about $10 to $15 for the pair, from recent rows.
- Measure, with no thresholds:
  - which earlier files the follow-on opened, at which stage, and whether its plan cites them;
  - `cited_earlier_run`;
  - the retention checks;
  - the reviewer's judgement of whether the earlier spec, environment and modules were used.

### Step 2: probe the cleared-context consumer (C2 and C3) on the current build
- `slice.py --clear-at` on one step case at three points: `implement` (boundary), `test:inside`, and `verify` (boundary). Use `node-add-function`, or `node-fix-bug` for a second case.
- Measure:
  - redone work (S-6);
  - what the fresh session opened before it acted (step 0's script);
  - whether it needed anything a packet did not quote. This is the direct test of "path to prose" against "quoted excerpt".

### Step 3: write the consumer contract
- One design doc: the consumer table, then per artifact or field:
  - its consumer;
  - when it is read;
  - its form;
  - its producer stage;
  - the gate that checks exactly what the consumer reads;
  - its size, a measured figure, not a cap.
- Feed it with steps 0 to 2. It also covers:
  - the removal list and its effect on existing repositories. One supported version: old files are left in place, and ShipLoop stops requiring and reading them;
  - the effect on the E2E SPEC (S-6, S-9, S-10, S-11), on the Run Review exporter, and on the packet text.
- An independent audit with three lenses:
  - consumer fit: does every artifact have a reader, and is every reader's need met;
  - main tenet: can a cleared stage work from its packet alone;
  - KISS and false refusals.
- The audit's corrections are applied before the owner sees it.

### Step 4: owner decision, then build (Execute: ask)
Build only after the owner approves the contract, in this order. Each slice is fail-first, gets two independent reviews and a fix round, and carries a journal entry and a change note.
- 4a. Hand-off fields: result keys, their gates, and quoting into the consuming packets. The engine owns the keys and gates; the packet owner (the inner-loop session) places the quoted lines.
- 4b. Knowledge home slimming: `STAGE_FILES`, `CLOSES` and `SECTIONS` reduced to the three living files; the `test-strategy.md` content merged; `README.md` and `SHIPLOOP.md` dropped.
- 4c. Removal of the feature folder, the retire step, `features/README.md`, `spec_pin` as a file line, and their tests. This is dead code once 4b lands.
- 4d. The report shows the hand-off fields and the test cases. Lessons stay in commit messages.
- 4e. Harness: SPEC amendments in their own commits; the consumer-read counts folded into `metrics.json` if step 0 proved them useful; the Run Review exporter updated by its owner (the E2E fork).

### Step 5: verify
- Rerun steps 1 and 2 on the new build. Compare consumer reads, redone work, follow-on use of earlier knowledge, and `cited_earlier_run`.
- Run a hello and Checkers cell of three or more each to check cost and turns against the current build's spread.
- No claim of change unless the distributions clearly differ.

## 5. Who owns what

| Area | Owner |
|---|---|
| Result keys, gates, knowledge home, report contents, removals | This session (engine) |
| Packet text that quotes the hand-off fields; any stage-duty wording | The inner-loop session |
| Run Review exporter | The E2E fork |
| Harness SPEC and evidence | This session |
| Release | The owner. The pending inner-loop note already makes ShipLoop a major |

## 6. Decisions the owner will be asked (after step 3)
1. Approve the consumer contract and the removal list, which reverses three earlier decisions: planning knowledge retained as files, the feature-spec lifecycle, and the features list.
2. Test cases: a state field or the one remaining per-run file.
3. Keep a human-readable plan in the repository (a `plan.md` copy), or rely on the report.
4. Lessons in commit messages only, or also in a living file section (for example a `## Lessons` heading in `architecture.md`).

## 7. Risks
- Few runs. The probes are one pair and three slices; a cell would need more. The contract states every figure with its count.
- Coordination. Packet text and the exporter are owned by other sessions; their changes land in the same release or the shape is half-built.
- Removing files models already write. Prompts must stop asking for them in the same release, or models keep writing files nothing reads.
- The retire step and the feature list were built on 2026-10-10. Removing them is deliberate: the directive outranks sunk work.
