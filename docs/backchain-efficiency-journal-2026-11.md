# Backchain efficiency and effectiveness — journal (2026-11)

Question (owner, 2026-11-01): make Backchain as efficient and effective as possible.
Order of judgment, by the owner's rule: plan quality first, then tokens, then wall time.

Status words: **firm** (measured, reproducible from the cited evidence), **interim** (measured, but
on a sample that cannot settle it), **exploratory** (a reading of evidence, not a measurement),
**superseded** (kept, with the date and the reason).

Evidence: [`docs/experiments/backchain-efficiency-20261101/`](experiments/backchain-efficiency-20261101/)
(`audit.py` re-reads the 2026-10-16 study and writes `audit.json`). The study itself:
`/Users/dadleet/src/backchain/docs/experiments/2026-10-16-backchain-full-workflow.md`, raw runs under
`/Users/dadleet/src/backchain/results/full-workflow-20261016/` (local, ignored by that repository's Git).

## Owner decisions

- **D1 (2026-11-01), review gate:** the default stops at the first trivial review; a material or
  unresolved review is always followed by a fresh one. `Backchain passes: one` keeps its one cycle.
  ShipLoop's `converge` runs keep two reviews through an explicit `Backchain passes: converge` marker.
- **D2 (2026-11-01), measurement:** before any prompt change is adopted, a cohort reruns the six
  2026-10-16 cases and about four new held-out cases, designed blind by a separate agent, 3 repetitions
  per arm, with that study's subject and grader (gpt-6-astra medium through Codex, blind grading).

## Round 0 — audit of the 2026-10-16 study and of today's sources (2026-11-01)

Conditions: no model run. `audit.py` reads the 36 retained runs (6 cases × 3 repetitions × 2 arms,
gpt-6-astra medium, Codex CLI 0.163.0; control Backchain 0.6.3, candidate "lean") and the source
sizes of Backchain 0.6.6 at e81fdb55.

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R0-1 | The cost is the instructions. A control run's commands name ~194 KB of Backchain files and the Until Loop card and runtime document (38 KB in the study's Until Loop 0.8.3; 53 KB today); the context is re-billed on every command, though 91 % of input is cached. Medians per control run: 16.5 commands, 967,778 input tokens (84,170 uncached), 7,507 output tokens, 168 s, 349 KB of tool output. | firm | `audit.json` `summary.by_arm`, `runs[].instruction_files_named`; study `snapshots/until-loop/` |
| R0-2 | The model writes its own bookkeeping code: 5–16 Python or Node blocks per run (median 7 in both arms), to build the plan, the Until Loop contract, review records and identity checks. | firm | `runs[].hand_written_code_blocks` |
| R0-3 | Most disqualifications are mistakes in that hand-built bookkeeping. 12 of the 14 disqualified runs include at least one (a resource left out of the contract, the latest packet not retained, or a malformed review record), and 8 of them (4 per arm) have nothing else: `convergence.md` or the Until Loop script missing from the contract's bound resources, or the latest packet not retained. Their graders passed the plans' dependency logic and usability and failed the runs' completion claims for that reason. | firm (count); interim (that script-built contracts would have qualified them) | `summary.disqualified_with_binding_errors_only`, `summary.disqualifying_workflow_errors`; study `decision-analysis.json` `attempts[].criteria` |
| R0-8 | One disqualification is a plan defect, and the contract caused it: in `independent-inspection-scopes-current-r1` review 1 found that the elaborator's own null-origin inputs on S1 and S3 were not prerequisites, but kept them because "never remove an existing edge" covers generated edges too; the run stopped incomplete. | firm | that run's `artifacts/reviews/review-01.json` |
| R0-4 | The confirming review finds nothing. 12 runs used the two-review gate; 11 ran a review after a trivial one; none of the 11 changed anything, and every one saw the same candidate digest. | firm (n = 11) | `summary.confirming_reviews`, `runs[].review_classes`, `runs[].reviewed_candidate_digests` |
| R0-5 | Today's runs read more than the study measured: `convergence.md` grew from 11,228 to 19,006 bytes (0.6.4 chunk review, 0.6.5 mechanical preservation); about 12 KB of the 28.6 KB `SKILL.md` serves only the private development checkout. | firm | `instruction_bytes` |
| R0-6 | Native plans leave Backchain unvalidated: the native procedure keeps `parallel_groups: []` and structure "unknown" because no validator ships in the skill; the only Python validator is ShipLoop's `shiploop_backchain_graph.py`, and the Plan Dispatcher exporter exists only in the private checkout. | firm | `skills/backchain/SKILL.md` "Compatibility-native plan"; `skills/plan-dispatcher/SKILL.md` "Execute" |
| R0-7 | A standalone call has no stated Until Loop: the card says to read "the selected Until Loop card" and forbids an ambient installation, but names no default; the install text still names a `backchain` plugin, `~/.claude/skills` links and Hermes, all retired. | firm | `SKILL.md` "Native procedure", "Layout and verification"; `agents/backchain.md` |

Related evidence outside the study: ShipLoop measured plan-stage Backchain work at 64 min (17 % of
planning) on Luna xhigh (`test/shiploop_e2e/LEARNINGS.md`, planning-time entries of 2026-10-05). On
Grok medium the whole plan stage was 8.38 min (38 %) of a 22-min window, of which the Backchain loop
itself was 2.7 min, about 12 % (`docs/planning-time-analysis-2026-10-06.md`, commit 41cf3cf4).
The deterministic validator found an orphan discovered step that one review pass added and the later
passes and Improve accepted (2026-10-04 Luna run).

Until Loop already supports what a script-owned binding needs: its card's "Start from a
parent-written contract" route takes `Contract:` and `Receipt:` paths, starts
`start --receipt <Receipt> < <Contract>` without interpretation, and writes every packet to the
receipt itself (`skills/improve/runtime/until-loop/ADAPTER.md`). Backchain's card instead asks the
model to build the contract and to read `references/runtime-ephemeral.md` in full.

An independent design pass (a Plan agent given the code and these measurements, not this plan)
reached the same order: script the binding and ship the validator first, separate generated from
inherited edges, then the gate, the reading diet and the synthesis prompts, measured on the repaired
baseline. It corrected four of the figures above before they were committed.

## Plan

Phases (each lands with its own tests and journal entry):

0. Base, baseline, this journal and the audit (this round).
1. Ship a deterministic toolkit in Backchain's package: the parity-tested validator moved from
   ShipLoop; packaging and the Plan Dispatcher export; and the binding through Until Loop's
   parent-written route (`prepare`, `freeze`, `record`, `verify`, `finish`). Generated edges become
   revisable and inherited ones stay protected, checked mechanically (R0-8).
2. Reading diet: a native card with one ordered read list; development-checkout material moved to
   `references/harness.md`; bookkeeping prose replaced by the toolkit's commands; lens cards by ID.
3. Review gate per D1.
4. Leaner synthesis prompts, adopted only if Phase 5 holds quality.
5. Measurement per D2, after an adversarial review of the candidate: a six-run smoke pilot of the
   repaired workflow first, then the cohort. Held-out cases carry seeded defects with mechanical
   answer keys where possible. Pre-registered rule, the owner's order: a material quality difference
   (outside the graders' test-retest noise) decides; otherwise fewer tokens (paired Wilcoxon signed-
   rank); otherwise less time. No invented thresholds.
6. Land, release, refresh hosts.

Deferred, not scheduled: an advisory confirmation lint (a check that executes a module needs a
supplier of that module), aimed at the missing-module class behind ShipLoop's 165.9-min redo; it
needs true and false positive counts first.

Baseline before any change (e81fdb55): `test/backchain-chunks.test.py` 49 tests,
`test/shiploop-backchain-check.test.py` 21, `test/marketplace-package.test.py` 30,
`test/until-loop-vendor.test.py` 10; all pass.

## Round 1 — the deterministic toolkit (2026-11-01)

Conditions: no model run; every result below is a script-run test or a direct comparison.

Changes:
- 90b9ac99e02d89efa8102f8686321da9ccccf554 moves the lib.js port from ShipLoop to
  `skills/backchain/scripts/backchain_graph.py`; ShipLoop's `backchain-check` imports it from the sibling package.
  Its parity tests move with it to `test/backchain-graph.test.py`.
- 44d30f052c4648f5727202922a269327579d506f adds `scripts/backchain.py` `check`, `package` and `export`.
- The next commit adds the run commands `prepare`, `freeze`, `record`, `verify` and `finish` (this entry is
  committed with it).

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R1-1 | The move changed nothing ShipLoop prints: old and new modules gave byte-identical receipts on all 95 inputs tried (88 corpus plans, 7 chunk fixtures). The quick tier for those paths (21 suites) passed. | firm | 90b9ac99 message |
| R1-2 | The Python export agrees with the checkout's JS exporter: the same accept/refuse verdict on all 88 packaged corpus plans and identical graphs for the 33 both export. Plan Dispatcher's `validate-graph` accepts all 33. | firm | `test/fixtures/backchain-export/` (three goldens and MANIFEST.json); `test/backchain-toolkit.test.py` `ExportTests` |
| R1-3 | A script-written contract binds every resource whose absence disqualified runs in the study (R0-3): the request, `references/convergence.md`, the Until Loop card and runtime, and the latest packet, which the runtime itself writes to `--receipt`. | firm (by construction and test); interim (that live runs then qualify) | `RunTests.test_a_fresh_run_converges_on_its_first_trivial_review` |
| R1-4 | The loop classification is measured, not claimed: a cycle whose packaged plan changed is reported non-trivial even when its assessment says trivial, and gets a fresh review under every gate. | firm (test) | `RunTests.test_a_changed_plan_is_never_trivial_and_gets_a_fresh_review` |
| R1-5 | Generated and inherited content are separated mechanically: freezing a plan that dropped an inherited input edge fails; the same removal of an edge the run generated is recorded as a non-trivial repair (the R0-8 defect). | firm (test) | `RunTests.test_inherited_edges_stay_while_generated_edges_may_go` |

Live use is untested: no model has yet run the toolkit. That is the pilot's question (Phase 5).

The run commands landed as 1f2d7ae31f752c0027c199fd808112763ed10108.

## Round 2 — the card uses the toolkit; the first trivial review completes (2026-11-01)

Conditions: no model run. Byte counts are static UTF-8 sizes of the files a fresh-request run is told to read in
full, at e81fdb55 (0.6.6) and in this commit; they are not token measurements.

Changes (one commit, because ShipLoop's gate-document pins read Backchain's text and the gate must change in both
together):
- `SKILL.md` is the native procedure only: prepare, plan, freeze, loop, finish on `scripts/backchain.py`, plus the
  unchanged plan contract and invariants; the development-checkout material moved to `references/harness.md`.
- `references/convergence.md` describes the scripted binding: the markers and the three gates, the contract
  `freeze` writes for Until Loop's parent-written route, the obligations table (generated vs inherited), each
  cycle's duties and the terminal evidence per gate. Every semantic review rule is kept; the bookkeeping prose the
  scripts now own is gone.
- `backchain.py lenses ID…` prints only the named lens cards; the review prompt and the lens index use it.
- Owner decision D1: by default the first trivial review completes (gate 1); `Backchain passes: one` is unchanged;
  `Backchain passes: converge` keeps two consecutive trivial reviews. ShipLoop's `converge` packets now print that
  marker so a ShipLoop `converge` run keeps two reviews; of 207 rendered ShipLoop Backchain texts (every stage,
  delegation and mode) only the 7 `converge` ones changed.
- `references/caller-contract.md`, the review prompt, `agents/backchain.md` (stale install line) and the evals follow
  (eval 15 is now the converge case; two new evals: the default gate and generated-edge removal).

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R2-1 | A fresh request's full reads fall from 231,784 to 140,574 bytes (−39.4 %): `SKILL.md` 28,636 → 13,503, `convergence.md` 19,006 → 16,529, the Until Loop runtime document (27,913) and the lens cards (36,412) and interactions (9,608) no longer read whole; the review prompt and lens index grow by 333 bytes. The generator and elaborator (70,305) are now the largest block. | firm (bytes) | sizes from `git cat-file -s` at e81fdb55 and the work tree |
| R2-2 | ShipLoop's default packets are byte-identical: 200 of 207 renders unchanged, the 7 changed all in `converge` mode. | firm | render comparison over `prompts.prompt` and `_backchain_guidance` for every stage, delegation and mode |

Held-out cases for Phase 5, frozen before the candidate: designed blind by a separate agent (it reported only paths,
digests and counts), 4 cases with 7, 10, 7 and 10 mechanical keys, at
`/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/heldout/`, MANIFEST.json SHA-256
`7c81681f9a1e558dfd5a4b0a06786943744abc07ce2d7b5fb02d7665b115e07a` (17 files); its `validate.sh` passes. Not opened.

Round 2 landed as 39af8ce04222fb49aa6d612e08b4dbabd73e5db3. The first quick-tier run of it failed four
subtests of `shiploop-navigator-dry-run`, whose two converge tests still pinned the old no-marker text; they moved to
D1 and the rerun passed (39 suites, 315.9 s).

## Round 3 — the lean synthesis prompts (2026-11-01)

Conditions: no model run. The two prompts are copied byte for byte from the 2026-10-16 study's frozen lean snapshot:
`direct.v1.md` SHA-256 `2e25db77c52d41c0646ce368f65b70216af896678b0aa9b71a35240d78d31407` and the compact
`elaborator.v1.md` `8d69665758266ff18313c35232153012fcae90760e3383d7ce1c6fbdb5510544`, both matching that study's
`candidate-source-manifest-v2.json`. The replaced elaborator was unchanged since that study (0.6.3 = 0.6.6), and the
compact one keeps the same four placeholders the checkout's harness renders.

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R3-1 | A fresh request's full reads are 79,187 bytes, or 96,441 when its dependency review calls for the elaborator, against 231,784 at 0.6.6 (−65.8 % / −58.4 %). | firm (bytes) | `git cat-file -s` at e81fdb55; work-tree sizes |
| R3-2 | The prompts carry the measured design: direct synthesis, then the dependency review, then the elaborator only on a change (`prepare` prints that order; the generator is in no native route). | firm (test) | `RunTests.test_each_route_reads_its_prompts_once_in_order` |

Risk carried into the cohort: the 2026-10-16 adversarial review's false-edge hazard of direct synthesis is now
mitigated by the generated-vs-inherited rule (a review may remove an edge its own run generated); its frequency is
unmeasured, and the held-out `inherited-edges` and `seeded-defect` cases are where it would show.

## Round 4 — adversarial review of the candidate, and its fixes (2026-11-01)

Conditions: one adversarial review (the adversarial-review skill) by `codex:gpt-6.1-sol` at medium effort of the
candidate as it stood at 07:16: 39af8ce04222fb49aa6d612e08b4dbabd73e5db3 plus the lean-prompt step that landed as
090e37f5b222486c258e39c88a2d8e7557b939ef. The reviewer had a 238 KB change packet (17 source-file diffs against
e81fdb55, tests and the byte-for-byte validator move left out) and an evidence brief. It returned eight findings,
each with a refutation condition. Evidence:
[`experiments/backchain-efficiency-20261101/adversarial/`](experiments/backchain-efficiency-20261101/adversarial/)
(`findings.json`, `findings.md`, `evidence.md`, `dispositions.md`).

Method: each code finding became a test in `test/backchain-toolkit.test.py`, written from the reviewer's refutation
condition before its fix; the fixes followed. F6 and F7 are measurement findings and became pre-registered measures of
the cohort before its freeze (`/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/cohort/PROTOCOL.md`).

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R4-1 (F1) | `finish` certified convergence from any receipt reading `complete`, a fabricated one or another run's. It now accepts only the run's own terminal packet: the frozen contract's workspace, work, conditions, context and exit checks, this receipt path and gate, no more actions than recorded cycles, the last cycle's report, and, when complete, every frozen exit check passing. A genuine run's terminal packet matched on every one of those fields. | firm (test) | `test_finish_refuses_a_receipt_that_is_not_this_runs`, `test_finish_refuses_a_callback_submitted_without_record`; `backchain.py` `receipt_problems` |
| R4-2 (F2) | The run's frozen request, caller packet, baseline, contract and resolved resources could change unnoticed. `verify` (the `backchain-evidence` exit check), `record` and `finish` now recheck every digest. | firm (test) | `test_verify_rejects_a_changed_binding` (6 targets); `binding_problems` |
| R4-3 (F3) | A caller's `edit_bounds` were bound into the contract but no command enforced them. `freeze`, `record` and `verify` now do, as `references/caller-contract.md` states them; the edge-key form (`consumer<-supplier`, `null` for an `initial_state` input) is now documented there. One deliberate difference from the 2026-10-16 study's own check: that check keyed edges per input object, this one per consumer/supplier pair. | firm (test) | `test_caller_edit_bounds_are_enforced`; `bound_errors`; the study's `study.py` bounds block |
| R4-4 (F4) | A stale or empty assessment was recorded as a qualifying review. `record` now requires `candidate_identity` to be the sha256 of the candidate the cycle began with (`freeze` prints cycle 1's, each `record` prints the next, and its report's handoff repeats it), and a non-empty `checks`. On 090e37f5 all three bad assessments were recorded, as cycles 1 to 3. | firm (test) | `test_record_binds_the_assessment_to_the_candidate_it_reviewed`; `review_problems` |
| R4-5 (F5) | A source-aware run returned `{plan, convergence}`, not the documented `{plan, review}`. `finish --review FILE` is now required with a caller packet. It checks the review's interface, action, stage and action ID against the packet, restores the caller's identities, records the output digest, takes `structural_plan_status` from the check receipt and adds `review.convergence`. A final review's planning gaps also prevent converged. | firm (test) | `test_a_source_aware_run_returns_plan_and_review`; `caller_review` |
| R4-6 (F8) | The contract forbade network access, installation and contact that a request or caller may grant, and that 0.6.6 had not forbidden. Its authority is 0.6.6's scope again (no commit, push, merge or project execution, no broadened scope), plus "any other access is only what the request and the caller packet grant". | firm (test) | `test_the_contract_grants_only_the_callers_authority`; `AUTHORITY` |
| R4-7 (F6) | Dropping the confirming review rests on 0 changes in 11 confirming reviews, from one study. D1 stands as the owner's decision. The cohort now reports the control arm's confirming-review yield, and a real material defect that only a confirming review found goes to the owner. | open (cohort) | PROTOCOL.md, secondary measures |
| R4-8 (F7) | The lean prompts are adopted before their quality cohort. That cohort (D2) is the experiment the finding asks for. Added before the freeze: per-case reporting, a pooled report over the three cases where lean qualified less on 2026-10-16, and that pooled qualification as a block on a candidate win. | open (cohort) | PROTOCOL.md, measures and blocks |

Fail-first, and after: the final test file run against 090e37f5 fails 16 times in 8 tests, each in the finding it
targets: F1 3, F2 6, F3 4, F4 1, F5 1, F8 1. F4's first failure is the new printed-identity assertion; without that
assertion, its three substantive subtests fail. With the fixes, all 31 toolkit tests pass (29.7 s). Before the last
correction below, the quick tier for the changed paths (17 suites) passed in 322.5 s; after it, the toolkit,
`BackchainGateDocumentsTest` (9 tests) and `shiploop-navigator-dry-run` (36 tests) pass.

A correction made while fixing, kept by a test: the first F1 fix required exactly one loop action per recorded cycle.
That would refuse a normal run in which the model edits after `record`, records again and submits the second report
in the same callback. The rule is now "no more actions than recorded cycles": an action with no record behind it
still means a hand-written report, and is refused. `test_a_cycle_recorded_twice_in_one_callback_still_finishes`
passes on 090e37f5 and after; it is a guard, not a fail-first test.

Not defended, by the KISS rule (fix what breaks a normal run, document the rest): a hand-edited `run.json` can
change what the binding check compares against, and a deliberately forged packet that copies every contract field
and the last report would pass `receipt_problems`. The 2026-10-16 failures were hand-built bindings, not tampering.

Round 4 landed as 26d4785541fedbfba91bb32e61d525ed8f4a19f2.

## Round 5 — a second adversarial review, of the fixes, and the cohort runner (2026-11-01)

Conditions: the same reviewer (`codex:gpt-6.1-sol`, medium) on 26d47855 against 090e37f5. The packet was the diff of
`skills/` and `changes/` with a header quoting round 1's claims (49,791 bytes), plus an evidence brief. Five findings.
Evidence: [`experiments/backchain-efficiency-20261101/adversarial/round2/`](experiments/backchain-efficiency-20261101/adversarial/round2/).

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R5-1 (R2-F1) | `finish --review` stamped the final digest on any review whose identity fields matched, including an empty shell or the inherited candidate's assessment. It now requires the review to assess the final candidate: `candidate.output_sha256` the final sha256 (the last `record` printed it), `findings` a list, `coverage.source_review_status` set. | firm (test) | `test_finish_refuses_a_final_review_that_is_not_of_the_final_candidate` |
| R5-2 (R2-F2) | Round 4's corrected count ("no more actions than recorded cycles") still let a hand-written callback hide behind an extra record. The count is gone. `record` now runs inside a callback: it reads the loop's packet from the receipt, stamps the cycle with the callback number, and refuses when the previous callback submitted anything but the last report `record` wrote in it. `finish` requires a recorded cycle for every callback. | firm (test) | `test_a_callback_submitted_without_record_is_found`; `record`, `receipt_problems` |
| R5-3 (R2-F3) | `checks: [null]` passed as a non-empty list. Checks must now be non-blank strings. Their content stays the reviewer's claim: checking substance would need a structured checks format, an unmeasured prompt change. The cohort's blind grading measures what the reviews achieve. | firm (shape); judgement (substance) | `test_record_binds_the_assessment_to_the_candidate_it_reviewed` |
| R5-4 (R2-F4) | Keying edges per consumer/supplier pair (Round 4's decision) let a provisional edge gain inputs without `allow_new_edges`. An edge that ends with more inputs than it had now needs it; rewording or dropping an input is still a change. | firm (test) | `test_a_provisional_edge_gains_inputs_only_with_allow_new_edges` |
| R5-5 (R2-F5) | The contract's work text said "never an inherited one" even where caller bounds authorize the removal. With bounds it now says a review may remove an inherited edge or step only where the bounds make it provisional. The live check of this is the cohort's bounded source-edge repair case. | firm (text, test); open (live) | `test_the_contract_lets_a_review_remove_what_the_bounds_make_provisional` |

Fail-first, and after: the final test file run against 26d47855 fails 8 times in 5 tests: R2-F1 3, R2-F2 1 (`record`
after a hand-written callback 1 succeeded), R2-F3 2, R2-F4 1, R2-F5 1. After the fixes all 34 toolkit tests pass.

The cohort runner is in. A separate agent built `cohort.py` from the brief: dry run 48 expectations, 0 problems; 48
unit tests on Python 3.15.1 and 3.9.6; no model launched. It reproduces the 2026-10-16 prior of 11 confirming
reviews, 0 non-trivial, and extracts all 36 retained receipts. I accepted its eight implementation deviations before
the freeze. They apply to both arms and are recorded in the cohort protocol's "Runner implementation notes".
- The packet extraction now counts a helper script's output: the 2026-10-16 study's own post-hoc correction,
  applied up front.
- The input one-liners no longer hint at each case's trap.

Two card fixes came from the runner's pilot watch-list:
- The card said "choose a new run directory outside the project", which conflicts with a caller that confines
  writes. It now says to use a run directory where the caller or request lets you write, otherwise outside the
  project.
- The card never mentioned `--binding`, so a caller's `Backchain standalone Until Loop binding: ID` was replaced by a
  generated ID. `prepare --binding ID` now carries it.

Neither card fix is measured yet; the pilot is their first live use.
