# ShipLoop run-5 batch journal (2026-10-24)

This is the living record of the batch that comes before chess run 5 on Salesforce:

- one batch, one release (skill-craft 2.9.0);
- then remove run 4's kept app from org `de`;
- then run 5, with run 4's flags and a 5 h cap.

The rule for choosing work is its gain in the code ShipLoop produces on any project. Every fix is generic, never
specific to chess or Salesforce.

What prompted the batch:
- Run 4 on 2.8.0 reached release-plan ([chess journal F11](e2e-salesforce-chess-journal.md)).
- A quality review of run 4's product graded the code B-. It named four generic failure modes:
  - (a) a deferral, not-applicable or "inspection suffices" exit was too easy to take;
  - (b) a rule only the Improve reviewer held;
  - (c) a fact stranded in prose that later packets do not quote;
  - (d) refusal text that taught a workaround.
- The owner's answer is the F1-F6 spec, built as "structure, not prose". Each decision gets:
  - a required result field;
  - a placeholder that states the bar;
  - a CLI gate on the field;
  - packets that quote it by value.

## Changes, in commit order

| Unit | Question | Change | Evidence | Status |
|---|---|---|---|---|
| I1 look-back | Why did run 4 cite no earlier commit? | The look-back sat in an optional head tier and reached 0 of 9 printed implement heads. It is now required text, one line per commit. | `9c324cd9`; `test/shiploop-navigator-contract.test.py` `test_a_printed_implement_head_carries_the_look_back` | firm |
| I2 remote base run | Why did W2 of run 4 send back from `test`? | The base run ran a remote test against a target that already held the change. A command listed under a platform card's `## Remote tests` is now skipped on the base, with the reason recorded. | `e074ccd3`; `test/shiploop-test-loop.test.py` | firm; RED for stateful remote targets is F3's job |
| I3 context use | What fills the context between compactions? | Harness only: `metrics.py` `context_window_rows`. ShipLoop's own files are 30-34% of context. The Improve route card (47 KB) was read whole 13 times. | `7f6f1942`; run 4's `metrics.json` | firm (n=1) |
| F2 / Q2 real RED | Why did W3's RED pass? | W2's test IDs were rerun behind a `printf`/`test -f` guard. A focused command whose IDs all belong to an earlier item is now refused, and a printed path no longer counts as a load failure. | `195cf5e0`; `EarlierItemFocusedIdTests` | firm; the advisor additions are pending |
| Q1, Q3-Q7 stage texts | What did the product review find that the texts let through? | Duty and review-focus prose. The overlapping sentences are trimmed as fields replace them (D6). | `9ed4ec24` | interim: F1 replaced its Q1 and Q3 sentences |
| F1 test layers | How do we stop "the UI is unverified", "inspection suffices" and source-grep confirmations? | Result fields `surfaces` (renamed `test_layers` in the term-fix commit), `targets` and `harness_runs`, plus each criterion's `confirm`. Gates, required packet blocks and term fixes. See below. | `52789f8f`; `TestLayerGateTests`, the CLI fault table in `test/shiploop-callback-contract.test.py`, `test_a_step_plan_head_with_test_layers_at_their_limit_still_fits_the_cut` | firm offline; live in run 5 |
| Gate counts (harness) | Which refusal gates fire in a run, and are they fixed in stage? | `metrics.gate_counts`, from `GATE_SIGNATURES`. The F1 and F2 rows are read from the gates' own refusal text, built by the gate functions in a test. | `2535a7af`, plus the term-fix commit; run 4: 13/13 refusals classified, run 3: 5/5 | firm |
| Lean Improve route | Why is each Improve stage's reading 57.5 KB? | The route card was split: a 9.7 KB core read once per context, and case files opened only when their case arises. Run 4's events show that skill files come back whole whatever window is asked, so only the file size matters. | `d21c770e`; `docs/experiments/shiploop-eff-journal-rows/U18b.md` | firm offline (−65% per stage); live in run 5 |
| Term fixes | Does each concept have one term? | See "Term fixes (2026-10-24)" below. | `ed41369f`; [nomenclature-audit.md](shiploop-run5-batch-evidence/nomenclature-audit.md) | firm |
| R1 proof and settle | `check` had 7 meanings (audit cluster 1). Which renames remove the collision without a misnomer? | A step's command becomes `steps[].proof`. An open item's or unverified outcome's way to settle becomes `settle`, while a probed assumption keeps `check` for its probe. `check` now means only a command judged by its exit code. State version 9 refuses a version-8 run by name. The suite value `check` was **not** renamed `static`: it is one schema shared by `test_commands` (lint, type and build) and by `system_commands` and `consumer_checks` (exit-code checks such as a smoke request), so "static" would misname two of its three lists. **Owner decision (2026-10-24): keep `check`.** | the R1 commit; `glossary.md` rows Proof, check and settle; two retired-term rows | firm offline |
| R2 criterion and requirement | Audit cluster 5: "criterion" named both a step plan's C<n> and an R-level condition, and "requirement" named both R-<n> and a step's C<n>. | A criterion is only a step plan's `C<n>`. A requirement is only a spec entry `R-<n>`, whose conditions are its acceptance lines (the term the spec write-back gate already used). The implement exit condition and Work line, which carry the owner's D4/D7 wording, now say "each criterion assigned to this step". Verify compares each criterion's Confirm-by. The spec duty, spec row, plan and product-acceptance use "acceptance line(s)". The glossary defines acceptance line, and two retired-term rows cover the old phrases. The Run Review page's own stage defaults keep their text (a separate schema). | the R2 commit | firm offline |
| R3 due stage and due item | Audit cluster 6: an open item's `consumer` named a later stage (or carry-forward), but on the plan's open assumptions it named a work item. Elsewhere "consumer" also meant the product's user (`consumer_checks`, `consumer_entry`, the delivery contract) and the reading stage (CONSUMES). | An open item's field is `due_stage`, the same name `unverified[]` uses. The plan's open assumptions use `due_item`. `assumptions.due(row)` reads either for the renderers. "Consumer" keeps one meaning, the person or system that uses what the run delivers. The internal CONSUMES map keeps its name. The E2E gate rows match both the old and new refusal text, so runs 3 and 4 still classify. | the R3 commit | firm offline |
| 3b nomenclature in E2E | How does one term per concept stay true after this batch? | The glossary (`references/glossary.md`, about 30 terms plus a machine-read retired list) and its one reader `test/shiploop_e2e/glossary.py`. A hermetic retired-term suite scans the text a model reads, with a planted-term check. E2E SPEC clause S-16, a change-admission "Nomenclature" step and a harness-checks row. The `nomenclature` record in metrics.json counts retired terms in a run's packets and refusals. The E2E audit skill's audit and repair steps check terms. | the 3b commit; `test/shiploop-retired-terms.test.py`; `GateCountsTest.test_nomenclature_counts_each_retired_term_in_shiploop_output` | firm offline; the record is read live in run 5 |
| F2 rest: file guard and red bar | E3's smoke sample and run 4's W3 faked RED with a file guard ahead of the tests. Can a script close that route? | A step-plan CLI gate refuses a focused command that checks for a file (`test`, `[`, `[[`, `ls`, `stat`, `existsSync(`) or prints a path before its tests run (`test_loop.guarded`, ported from the fork's E3 evaluator `_GUARD`). Its named exit, running the tests directly, is tested through the real CLI. The test case's `red` placeholder states the bar: the assertion fails because the behaviour is missing, not because a file is. Not built: (1) **non-empty `ids` on focused commands**. Built, then dropped: it broke about 40 count-based fixtures that use id-less focused commands on purpose. The guard gate closes the route actually seen, no run showed an id-less focused command, the duty already asks for IDs, and KISS applies. (2) **a code item needs a focused command with a new ID**. Deferred: without required ids it reduces to "at least one focused command", no run showed a code item without one, and test-strategy's unit-or-component rule already asks for tests of all code. (3) **revisit lines that quote ShipLoop's verdict**. Deferred: an advisor nicety with no observed failure. | this commit; `FocusedGuardTests` (detector table, refuse and accept), the CLI fault row "a focused command guarded by a file check" | firm for the gate (two observed instances); (1)-(3) open, owner may revisit |
| I2 finish: per-command remote and RED unobserved | One remote command beside local ones made the mutation check run mutants it could never reach, and nothing said which REDs no base run saw. | `mutation.split_remote` leaves out each remote command, records `remote_commands_skipped`, and skips the check with a reason when none is local. Verify (its item) and product-acceptance (every item) print a "RED unobserved" block naming the focused commands the base run left out as remote. | this commit; `test/shiploop-test-loop.test.py` (`split_remote`, `test_a_remote_focused_command_left_out_of_the_base_run_is_named_red_unobserved`) | firm offline; live in run 5 |
| F3 command targets | Only a platform card could mark a test as running against a target that already holds the change. How does a generic run say so? | A test command may name its test-strategy `target`. When a targets row keeps state, the step-plan template asks for `target` on each focused and regression command, and the gate refuses a missing or unknown one (named exit: name the row, or leave target out for a checkout command; the unknown-target exit is tested through the real CLI). The base run and the mutation check treat a command on a target that keeps state as remote on any platform (`test_loop.stateful_targets`, `_remote_base`, `split_remote`). | this commit; `test_a_target_that_keeps_state_is_named_by_each_focused_and_regression_command`, `test_a_command_on_a_target_that_keeps_state_is_left_out_of_the_base_and_the_mutant_runs`, the CLI fault row "a test command naming a target that is no targets row"; GATE_SIGNATURES `targets` and `focused_guard` classified from the gates' own text | firm offline; live in run 5 |
| I1 subject cap | A long commit subject filled the look-back's 320-character line and cut the learnings off. | The subject is cut to `LOOK_BACK_SUBJECT` (100) before the learnings are added. | this commit; `test_the_look_back_quotes_the_last_two_commits_that_are_not_shiploop_records` | firm |
| Head budget for F2 rest and F3 | What did the duty line and the Checked-by phrase cost? | Step-plan whole +125 on both routes; ask-agent head +125 (19,420). The inline head is 19,879, down 62, because its optional Progress view line (a link for the user, not the model) no longer fits. Every head fits the 20,000 cut. | `test/shiploop_e2e/head_table.json` `_comment` | firm |

## Advisor pass 1 (2026-10-24)

The panel was four seats (Opus, Codex Astra, Grok and an Ollama seat). The brief is in
[advisors-pass1-brief.md](shiploop-run5-batch-evidence/advisors-pass1-brief.md). It asked whether each change implements
its intent, judged design choices D1-D7, and asked which failure modes are left open.

### Adopted for F1, and how each landed

| Finding | Landed as |
|---|---|
| `executed` must be backed by a command that runs more than a grep | `layers.search_only` and `check_confirms`. A criterion that no command names stays the coverage gate's refusal. |
| `inspected` must name the surface and the layer | criterion `layer`; the check matches (surface, layer) against an unverified row |
| Every code surface needs a unit or component row | `check_surfaces` |
| Exactly one of a non-empty `surfaces` and `surfaces_na` | test-strategy gate ("never both") |
| D7: `surfaces_na` is too easy an exit | a step plan whose paths hold code lists the item's own rows when test-strategy recorded `surfaces_na` |
| A `prerequisite` row needs proof at prepare | prepare `harness_runs`: the command that ran one test, and its saved output, else `blocked` |
| Reword the template and the refusals to ask for an observation | `CRITERION_PLACEHOLDER`; the refusals name the observing command |
| Criteria lines show how they are confirmed | `layers.criterion_label` in the Step block and the criteria hand-off |
| Print the reason of a row that is not available | grouped `packet_lines` |
| The layers block goes to the test stage too | the test-layers block at prepare, step-plan, test-spec and test |
| Fix test-spec duty 3's pointer | RED points at the Test targets block |
| Cap the block, test populated fixtures, no "+n more" | field limits plus `TEXT_LIMIT` 1,200 at the gate; a head test at the limit on both routes |

### Adopted, not yet built

These are the pending units of this batch (status 2026-10-24 evening: F2 rest, I2, F3 and I1 landed, see the rows above;
F4 dropped as fields and gates by the owner; F5 waits for R4; F6 and R4 are being built by workers):
- **F2:**
  - non-empty `ids` on focused commands;
  - a behavioural item needs a focused command with a new ID;
  - load-failure RED only for real loader errors;
  - the `red` placeholder;
  - revisit lines that quote ShipLoop's verdict;
  - a real-CLI route test.
- **I2:** a per-command mutation filter; a `target` field on `test_commands`; a "RED unobserved: remote" line at verify
  and product-acceptance.
- **F3, F4, F5, F6:** as specified, with F6's primacy recorded at spec time.
- **I1:** cap the commit subject separately.

## Experiments that bear on the batch

| Experiment | Question | Setup | Result | Status and effect on the batch |
|---|---|---|---|---|
| E1 (the inner-loop fork, reported 2026-10-24) | Does asking each test-spec row for the weaker implementation its oracle rejects (F4's `stand_in_rejected`), plus an entry-point list, catch weaker tests? | Case `stand-in-parser`, seeded at test-spec and stopped after test. Grok 4.7 medium, 3 samples per arm. Arms: A = 2.8.0 (`288075c9`), T = `9ed4ec24`, B = T plus the F4 overlay. The scripted evaluator swaps the planted stand-ins `empty` and `lenient` into the final tree and runs the focused command. | All 9 samples killed both stand-ins. Error-oracle rows per sample: A 2/3/2, T 4/3/2, B 2/3/2. Difference 0.0. | **Inconclusive** (a ceiling: crude stand-ins fail every arm's tests). F4 moves to the end of the batch; its field and gates wait for E1 redesigned with run 4's subtler misses (one missing rule with the right move count, an oracle true only at the tested positions, a bound that cannot trip). F4's text rules with run-4 evidence stay (`9ed4ec24`). If the redesign shows no effect either, dropping `stand_in_rejected` goes to the owner. Evidence: [E1/](shiploop-run5-batch-evidence/E1/) holds the three decisions and the nine scores, copied from `/Users/dadleet/e2e-runs/experiments-r1-20261024/E1/`, where the sample slices also are. Arm A's pin, `288075c9`, comes from the decisions' `arm_specs`, since its score files record `commit: null`. The harness is the fork's branch `worktree-agent-a34bc5d47d282ddad` at `d5b5a70b` (`experiment.py`, evaluator `test/shiploop_e2e/evaluators/e1_stand_ins.py`, overlay `overlays/e1-stand-in.json`). |
| E3 (the inner-loop fork, reported 2026-10-24) | Does F2's text (the earlier-item gate and RED-from-behaviour wording, `195cf5e0`) stop a redone focused command from faking RED with a file guard? | Case `stand-in-parser`, seeded at step-plan and stopped after test. Every sample opens with a revisit quoting run 4's file-guard send-back summary. Arms: A = 2.8.0 (`288075c9`) and T = `9ed4ec24`, 3 samples each. | All 6 scored samples were behavioural: the focused command loads the module, then runs the tests, with no guard. A pre-round smoke sample under A was guarded (`if test ! -f src/records.js; then echo 'Error: Cannot find module ...'; exit 1; fi`), so 2.8.0 faked RED in 1 of 4 samples and T in 0 of 3. ShipLoop's base run judged the smoke sample's echoed load error as behavioural. | **Inconclusive** on rate (3 samples cannot measure about 25%), but the pattern is real: run 4's W3, plus this sample. Keep `195cf5e0`. F2's remaining work adds a deterministic step-plan gate that refuses a focused command guarded by a file-existence check ahead of its tests. The rule is ported from the fork's `test/shiploop_e2e/evaluators/e3_red.py` `guarded` (`6feb104d`); it closes the advisor's "load-failure RED counts only for real loader errors" hole that the smoke sample showed. Evidence: [E3/](shiploop-run5-batch-evidence/E3/), copied from `/Users/dadleet/e2e-runs/experiments-r1-20261024/E3/` and the smoke folder `experiments-smoke-20261024/E3/A/1/`; the fork's journal is `docs/shiploop-template-experiments-journal.md` on its branch. |
| E1b (the inner-loop fork, reported 2026-10-24) | With stand-ins modelled on run 4's real misses, does F4's per-row "stand-in the oracle rejects" make tests stronger? | Case `stand-in-rules` (fixture node-orders), seeded at test-spec and stopped after test. Grok 4.7 medium, 4 samples per arm: A = 2.8.0, T = `9ed4ec24` (including pair-absence-with-count), B = T plus the stand-in overlay. Four subtle stand-ins: one rule missing with totals still right, correct only on the oracle inputs, a limit that never trips, and fields valid alone but inconsistent together. The evaluator was verified: a run-4-style weak test file lets all four survive, and a strong one kills all four. | All 12 samples killed all 4 stand-ins (value 1.0), and every sample's own tests pass. All three decisions are `ceiling`. | **Firm for this stage in isolation** (21 samples across E1 and E1b): at test-spec with the spec's rules stated, Grok writes strong tests even under 2.8.0. Run 4's weak tests arose under long-run conditions (compactions, a larger spec, platform limits), which an isolated prompt change cannot be shown to help. **Owner decision (2026-10-24): drop `stand_in_rejected` and the entry-point error-row gate, keep F4's text rules (`9ed4ec24`)**, and measure test strength in run 5's own product. Evidence: [E1b/](shiploop-run5-batch-evidence/E1b/), copied from `/Users/dadleet/e2e-runs/experiments-r2-20261024/E1b/`, with the fork's harness at `78ea131b`. |

## F1 design notes (2026-10-24)

- **The `searched` value is new.** It answers the advisors' open question: what label does a criterion take when only a
  check command confirms it? Without it, the step-plan duty's "a docs criterion gets a search command" would have no
  legal `confirm`.
  - Risk: a behavioural criterion marked `searched`. The criteria lines now print the label, so the reviews see it.
  - Not gated, because a script cannot tell a behaviour criterion from a text one.
- **Head budget.** Inline step-plan was 19,732 of the 20,000 cut.
  - The required text without the optional lookups is about 17,000, so a block of up to 1,200 fits. The optional
    lookups give way first, by design (`_select_head`).
  - Measured: inline step-plan 19,957 (+225), ask-agent 19,310 (+563). The test at the gate limit passes on both
    routes.
- **The implement review focus was over its bound.** It was 191 characters over the handoff's 4,500 bound (improve-route)
  after `9ed4ec24`. It was tightened without dropping a condition. The server access-posture line joined the public
  entry point line.
- **Term fixes inside F1:**
  - test-strategy's layers were "unit, integration, system, consumer" and are now unit, component and e2e as in
    `surfaces`;
  - test-spec's "Put surface (unit, public interface, …)" is now the case's Test layers row;
  - verify's send-back is worded by `confirm`.
- **"Surface" named two concepts** (superseded 2026-10-24 by the term-fix commit).
  - "Required surface" and "checked surface", in verify, system-test, product-acceptance and the release stages, mean
    where a requirement is observed.
  - F1's new `surfaces` rows named code.
  - Resolution: the cheaper side was renamed. F1 was unreleased, so its field became `test_layers`, keyed `code` +
    `layer`, matching the packet header "Test layers". "Surface" keeps its established meaning in eight stage texts
    and the testing guide. Test-spec names both: a case's Test layers row and the surface where it is observed.

## Term fixes (2026-10-24)

Source: the read-only nomenclature audit ([nomenclature-audit.md](shiploop-run5-batch-evidence/nomenclature-audit.md),
19 clusters). The owner's rule is one term per concept: a rename changes every use in one commit, with no live synonym.

| Cluster | Fix | Where |
|---|---|---|
| 2 surface/layer | F1's `surfaces` becomes `test_layers` with `code` + `layer`, and `surfaces_na` becomes `test_layers_na` | `shiploop_test_layers.py`, navigator, duties, tests, docs |
| 4 Revise | The test duty 8 heading and validate-existing duty 4 say "Send back" | `shiploop_prompts.py` |
| 3 blocked | COMMON's blocked sentence matches BLOCKED_RULE: only a person or an outside service unblocks; a missing tool or a broken command is repair work | COMMON |
| 7 open item | COMMON defines one concept: an open item is an open `assumptions` row where the template has the list, else a summary entry. Step-plan's unconfirmable line keeps "open item", and the refusal names the same exit | COMMON |
| 16 unconfirmable | Implement duty 6 drops "the criterion text does not say unconfirmable", because such a condition is not a criterion | implement duty 6 |
| 10 step vs stage | COMMON, the reference's "Rules for every stage", the Improve handoff's "Stage result", the command card and navigator.md say stage | several files |
| 9 RED | "Expected-RED" for a baseline repair becomes "expected failure"; the spelling is "characterisation" | test-strategy, discovery and other duties |
| 12 knowledge home | A sensitive locator goes in "an authorized private store, never in KNOWLEDGE/ (it is committed)" | intake 3, project-knowledge.md |
| 11 remote | The Salesforce card's Testing section no longer says to list org-bound tests in `red_na` (contradicted by `e074ccd3`), and "org-bound" is retired | `platforms/salesforce.md` |
| 8 target | An NFR's "target" becomes "bound"; a send-back's "target" becomes "destination" | spec 6, navigator.md |
| — retired outcomes | The `/shiploop-complete` card lists the four outcomes; `repeat` and `replan` are gone | `commands/shiploop-complete.md` |

**Left, with reasons:**
- R1-R4, the costly field renames the owner chose, each get their own commit.
- Cluster 3's Until Loop "Stop blocked" strings are the loop contract's `repeat_condition` and are left.
- Cluster 13's callback/complete-command pair is R4.
- Cluster 15's Definition of Done needs a decision on which source wins.
- Cluster 17's `considerations` vs `decisions` is a gated field rename.
- The ask-agent chain's item statuses (confirmed, inspected, failed, not_run, unconfirmable) and Backchain's confirm
  levels (execute, inspect, unconfirmable) are separate schemas from a criterion's `confirm`. The glossary names all
  three.
- **Reference doc.** The new reference section lives in `testing-and-documentation.md#test-layers`. `test-loop.md` is a
  split-card home capped at 8,192 bytes, with a ledger row per section.

## Test runs

| When | What | Result |
|---|---|---|
| 2026-10-24, F1 first pass | 95 suites | 14 suites red: every fixture lacked the new test-strategy fields |
| 2026-10-24, after fixture ports and closures | 95 suites | 12 red. Causes: the confirm check flagged a criterion no command names (a bug); the item-rows rule fired where setup skipped test-strategy; 8 wording pins; the card cap; the head journal; one fixture that reused W1's test ID |
| 2026-10-24, after fixes | the 12 red suites | all green except one cleanup-race flake (actual-improve-cli tearDown `Directory not empty`, already a spawned task); it passed alone |
| 2026-10-24, before commit | 95 suites | all 95 green; chain-lifecycle 52 tests in 1,463 s under 8-way load (its one run for this commit: F1 touches the step-plan contract) |
