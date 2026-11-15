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
  *Superseded for ShipLoop's `converge` on 2026-11-01 by D-D (Round 10): that marker never reached a printed
  packet, so converge ran the default gate; the owner chose to keep that meaning.*
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
| R2-1 | A fresh request's full reads fall from 231,784 to 140,574 bytes (−39.4 %): `SKILL.md` 28,636 → 13,503, `convergence.md` 19,006 → 16,529, the Until Loop runtime document (27,913) and the lens cards (36,412) and interactions (9,608) no longer read whole; the review prompt and lens index grow by 333 bytes. The generator and elaborator (70,305) are now the largest block. *Superseded 2026-11-01 (Round 10, R10-9): these are the bytes the card asks for, not what hosts read; all 30 candidate cohort runs still read the runtime document and the interactions whole.* | firm (bytes asked); superseded as a read measure | sizes from `git cat-file -s` at e81fdb55 and the work tree |
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
| R3-1 | A fresh request's full reads are 79,187 bytes, or 96,441 when its dependency review calls for the elaborator, against 231,784 at 0.6.6 (−65.8 % / −58.4 %). *Superseded 2026-11-01 as a read measure (Round 10, R10-9): hosts also read the 27,913-byte runtime document and the 9,608-byte interactions whole in 30 of 30 candidate runs.* | firm (bytes asked); superseded as a read measure | `git cat-file -s` at e81fdb55; work-tree sizes |
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

Round 5 landed as a0178072f8298be3276580544101a8b528434d89.

Decision D3 (owner, 2026-11-01): this cohort keeps its own runner, `cohort.py` (the 2026-10-16 study's design), with
gpt-6-astra medium, and does not use `test/shiploop_e2e/run.py` on Terra xhigh. I asked because the approved plan
conflicts with a standing rule, recorded earlier that day, that every live-model measurement goes through `run.py`.

## Round 6 — the pilot: six live runs of the candidate (2026-11-01)

Conditions: `cohort.py freeze --pilot-only` at a0178072, then `cohort.py pilot`. The candidate arm ran on the six
2026-10-16 cases, one repetition each, two at a time: gpt-6-astra medium through Codex CLI 0.166.0, a 30-minute
deadline, no retries. The backend did not report the served model. The pilot is excluded from the cohort. Evidence:
[`experiments/backchain-efficiency-20261101/pilot-1/pilot.json`](experiments/backchain-efficiency-20261101/pilot-1/pilot.json)
(the six attempt summaries); raw run folders under
`/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/cohort/pilot-1/`.

| Case | Outcome checks | Wall s | Tokens (in + out) | Uncached in | Commands | Code blocks | Loop end |
|------|----------------|-------:|------------------:|------------:|---------:|------------:|----------|
| stale-build-receipt-identity | pass | 158.6 | 576,218 | 62,862 | 14 | 3 | complete |
| bounded-source-edge-repair | fail: the loop never ran | 93.4 | 515,472 | 50,094 | 12 | 2 | none |
| known-external-approval-blocker | pass | 107.8 | 693,112 | 64,705 | 14 | 3 | complete |
| legacy-draft-discovers-mapping | pass | 117.5 | 719,261 | 60,383 | 15 | 3 | complete |
| missing-normative-redaction-source | pass (an honest stop) | 101.7 | 543,143 | 72,534 | 18 | 5 | stopped |
| independent-inspection-scopes | pass | 137.3 | 694,428 | 67,874 | 14 | 3 | complete |

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R6-1 | Live models follow the scripted route. All six ran prepare and freeze; the five that froze ran record, verify, the loop's start and done, and finish. None hand-built a contract, receipt or identity check. Their 2–5 code blocks write the plan, assessment or review JSON, make a repair edit, or run the runtime's own `verify_script`. | firm (n = 6) | `pilot.json` `conformance`; event logs |
| R6-2 | The new card lines took. 6 of 6 put the run directory under `artifacts/`, and 6 of 6 passed `--binding cohort-<case>`, so the caller's binding marker reached the loop. | firm (n = 6) | prepare commands in the event logs; `conformance.binding_marker_in_loop` |
| R6-3 | A workflow-stopping defect, mine, from Round 4's F3 fix: the bounds check required every caller protected fact to be in `initial_state`. The bounded-repair case protects an accepted fact the inherited plan never stated ("S1 is already complete and its accepted article inventory is recorded in artifacts/article-inventory.json"), so `freeze` refused a correct, authorized repair. The model then refused to go beyond its edit bounds and stopped honestly. Fixed: a protected fact the inherited plan states must stay; one it never stated is not added. | firm (live, then test) | that attempt's events; `test_a_protected_fact_the_plan_never_stated_is_not_required` (fails on a0178072) |
| R6-4 | Every attempt still read the Until Loop runtime document (28 KB), which the card no longer asks for; the Until Loop card points to it. The Until Loop tree must be identical in both arms, so this is out of scope here; it costs both arms alike. | exploratory | event logs |
| R6-5 | Cost, descriptive only, with no control in the pilot. The five passing attempts' medians are 117.5 s, 689,601 input tokens (64,705 uncached), 3,921 output tokens and 14 commands. The 2026-10-16 control medians were 168 s, 967,778 input tokens (84,170 uncached), 7,507 output and 16.5 commands. The cohort's control arm is the comparison that counts. | exploratory | `pilot.json`; Round 0 R0-1 |

Next: rerun the pilot at the fix's commit. The first pilot's folder moves to `cohort/pilot-1/`, because `freeze`
refuses to overwrite a campaign.

Round 6's fix landed as b655b804a7c1a3d2cfed33f118ded73c350a38fb.

## Round 7 — the pilot again, at the fix (2026-11-01)

Conditions: Round 6's, at b655b804. Evidence:
[`experiments/backchain-efficiency-20261101/pilot-2/pilot.json`](experiments/backchain-efficiency-20261101/pilot-2/pilot.json);
raw run folders under `/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/cohort/pilot/`.

| Case | Outcome checks | Wall s | Tokens (in + out) | Commands | Code blocks | Loop end |
|------|----------------|-------:|------------------:|---------:|------------:|----------|
| bounded-source-edge-repair | pass | 79.8 | 606,660 | 13 | 4 | complete |
| independent-inspection-scopes | pass | 116.9 | 566,936 | 13 | 4 | complete |
| known-external-approval-blocker | pass | 127.7 | 667,635 | 14 | 3 | complete |
| legacy-draft-discovers-mapping | pass | 101.0 | 581,495 | 13 | 5 | complete |
| missing-normative-redaction-source | pass (an honest stop) | 82.7 | 740,812 | 14 | 4 | stopped |
| stale-build-receipt-identity | pass | 139.7 | 715,311 | 15 | 3 | complete |

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R7-1 | Every attempt passes every outcome check, including the bounded repair that Round 6 stopped on. All six used the toolkit route; 6 of 6 carried the caller's binding into the loop. | firm (n = 6) | `pilot.json` |
| R7-2 | Medians of the six: 108.9 s, 633,685 input tokens (62,273 uncached), 3,514 output, 13.5 commands, 4 code blocks. Descriptive only. | exploratory | `pilot.json` |

No workflow-stopping defect remains, so the cohort is frozen next, on this commit. Its skill trees are b655b804's;
this commit changes only docs.

## Round 8 — the cohort is frozen and running; amendment A1 before any grade (2026-11-01)

The cohort was frozen at 1e77f30b1006ab95e24dc476d0151370ee296f53: 30 jobs, 60 attempts, control e81fdb55, Until Loop
trees identical in both arms; `cohort.py verify` passes. Copies of the frozen protocol and of `freeze.json` are in
[`experiments/backchain-efficiency-20261101/cohort/`](experiments/backchain-efficiency-20261101/cohort/).

Two conditions of the run:
- The branch merged `origin/main` (c28866a6) while the first attempts ran; the attempts run from frozen snapshots
  and are unaffected.
- `test/test-groups.test.py` (249 s) ran on the same machine during the first two attempts, so their wall times
  carry that extra load. The quick tier was deferred until the runs end, for the same reason.

Amendment A1, decided at about 09:50, before any grade or analysis (`AMENDMENTS.md` beside the protocol copy):
- The first control attempt failed the registered structure check on invariant 6. Its plan keeps
  `parallel_groups: []`, exactly as 0.6.6's card instructs when no validator receipt exists. 0.6.6 ships no
  validator, and this cohort's prompt, unlike the 2026-10-16 study's, supplies no `check-plan.js`. That is R0-6,
  observed live.
- The registered checks stand. A packaging-normalized structure check and qualification are added, and the
  candidate-win blocks fire under either definition, which is stricter on the candidate.
- The quality comparison is also reported without `dependency-logic`, the one universal criterion that mentions
  parallelism.

## Round 9 — cohort results: inconclusive on quality, decisive on cost (2026-11-01)

Conditions: Round 8's frozen cohort. 60 attempts (10 cases × 3 repetitions × 2 arms), 180 blind grading passes
(gpt-6-astra medium, read-only, none invalid, 1 quote lowered by the quote check). Then `cohort.py analyze`,
amendment A1 (`a1_sensitivity.py`) and the post-hoc regrade R1 (`regrade_r1.py`, A2), whose rule was committed
(21cc2d05) before it ran. Evidence:
[`experiments/backchain-efficiency-20261101/cohort/`](experiments/backchain-efficiency-20261101/cohort/)
(`analysis.json`/`.md`, `a1.json`/`.md`, `r1-analysis.json`/`.md`, `attempts.json`, `AMENDMENTS.md`).

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R9-1 | Registered decision: inconclusive. Quality, candidate minus control, is −1.19 points, 95% [−8.85, +6.26], Wilcoxon p = 0.75, against grader noise ±1.05. Neither near-identical nor a significant difference, so the rule gives no winner. | firm | `analysis.json` `decision` |
| R9-2 | Cost decides nothing under the rule, but it is unambiguous. Per cell the candidate uses −630,081 tokens [−877,056, −422,651] and −124 s [−151, −100], 30 of 30 cells lower, p = 0.005 (10 cases). Arm totals: 20.0M against 38.9M tokens. Medians: 653,619 against 1,192,680 tokens and 115 s against 234 s. Also −25,210 uncached tokens, −5.1 commands and −3.7 code blocks per cell. | firm | `analysis.json` `paired`, `arms` |
| R9-3 | Every control attempt hand-built its bookkeeping (30 of 30); every candidate attempt used the toolkit (30 of 30). | firm | `attempts.json` `route` |
| R9-4 | Qualification as registered: candidate 19, control 7 (+0.40 [+0.13, +0.70]). Packaging-normalized (A1): 19 and 19. 13 of the control's 23 outcome failures are only the `parallel_groups: []` its card asks for; none of the candidate's 8 are. | firm | `a1.json` `packaging` |
| R9-5 | The candidate's two largest quality losses are a derived-field artifact, found after seeing the grades (post-hoc). Graders mention `parallel_groups` in 76 candidate rows and 0 control rows. All 49 partial or missed ones are in the two edit-bounded repair cases, read as a change outside the caller's bounds. The candidate's toolkit recomputes the field; 0.6.6 keeps `[]`. With the field removed (R1), bounded-source-edge-repair goes from −26.6 to 0.0 (96.4 in all 9 passes of both arms) and revenue-export-lineage from −9.1 to −2.4; the control's scores do not move. | firm (diagnosis by R1) | `analysis.json` `per_case`; `r1-analysis.json` `per_case` |
| R9-6 | R1, the post-hoc sensitivity: still inconclusive. Quality +2.18, 95% [−1.93, +7.49], p = 0.92, against its own grader noise ±0.62; qualification candidate 22, control 7; F7's pooled block does not fire (candidate 9 of 9). | firm (post-hoc) | `r1-analysis.json` |
| R9-7 | One genuine candidate loss: orders-cancel-rpc, −8.5 registered and −7.8 in R1. Both arms stop on the seeded defects that preservation forbids repairing, but graders judged the candidate's stop worse (terminal-disposition missed in 8 of 9 candidate verdicts). *Annotated 2026-11-01 (Round 10, R10-3): the stop is the one the contract requires (convergence.md forbids the split the oracle rewards, and S3's frozen partial confirmation is a second contract gap), so the case's oracle is wrong; graders also split by arm on equivalent stops (control met 8 of 9, candidate missed 8 of 9). This is an oracle and grader-validity problem, not a planner loss.* | firm (n = 3 per arm) | `grades/p*/orders-cancel-rpc-*` |
| R9-8 | The candidate's biggest gains: independent-inspection-scopes +16.7 (largely one control attempt scoring 47.4) and billing-late-fee +17.8. | firm | `analysis.json` `per_case` |
| R9-9 | F6: the control ran 7 confirming reviews and none was non-trivial. With the 2026-10-16 prior that is 0 of 18 confirming reviews changing anything, which supports D1. | firm (n = 18) | `analysis.json` `confirming_review_yield` |
| R9-10 | The design could hardly reach "near-identical". Its band is the grader noise (±0.62 to ±1.05 points), while 10 cases with a few large per-case swings give an interval about 9 to 15 points wide. So "inconclusive" here mostly reflects how little power the design has for small differences, not evidence of a difference. | exploratory | `analysis.json`; `r1-analysis.json` |

Adoption is the owner's decision (A2): the registered rule names no winner.

Decision D4 (owner, 2026-11-01): ship the candidate. Asked with the registered result (inconclusive), R1 (inconclusive,
no harm detected once the artifact is removed) and the cost result (halved) side by side. Follow-ups:
- orders-cancel-rpc's stop, which graders judged worse in the candidate (R9-7);
- the cases' bounded-repair criteria, which should tell graders that `parallel_groups` is derived (R9-5).

## Round 10 — Astra's review, verified; the follow-up plan and its owner decisions (2026-11-01)

Question (owner): ask Astra at max effort how Backchain works and what to improve; adopt what holds, plan and
implement. Conditions: gpt-6-astra, max effort, read-only, no fallback (`ask.sh astra`). Then 8 independent read-only
verifiers (workflow wf_350d73a0-70d), each told to refute one claim group, probing a `git archive` of
f5fb7d6446bb461e1a771a7bc64effaabd6822d1 (2.32.1) and the 2026-11 cohort's runs. Then 3 critics of the draft plan
(wf_5dde4b74-958): feasibility against the code, completeness and order, rules and history. Evidence:
[`experiments/backchain-efficiency-20261101/astra-review/`](experiments/backchain-efficiency-20261101/astra-review/)
(`astra.json`, `verification.json`, `plan-critique.json`, `probes/`).

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R10-1 | A caller-backed `finish` converges, and prints the export hint, on a final review whose `source_review_status` is `incomplete`, even with a material stale-source finding: the predicate ignores the status. A `planning_gaps` given as a string or object crashes with a traceback and exit 1. 0 of 9 caller-backed cohort runs hit it (each incomplete review also listed a gap). | firm (reproduced end to end) | `verification.json` R1; `probes/r1-*` |
| R10-2 | At the legacy inherited boundary, a changed goal, a changed step origin, or an invented `initial_state` fact ("Release approved.") passes preservation; the fact flips completion to complete and allows export. Strict initial_state equality would have refused 6 of 15 control runs whose inspection-derived additions all graders accepted, so only additions that close an inherited goal need or null-edge need are the defect (the "silent inv-7 repair"). Edge keys split on `<-`, and a supplier ID `null` collides, but no case or caller uses such IDs. | firm | `verification.json` R2; `probes/r2-*` |
| R10-3 | orders-cancel-rpc's oracle rewards a store-supplier split that `references/convergence.md` forbids (inherited seed work may not move to a discovered step; lines from 2eaeb47a and e498d0b6, 2026-10-17). All 6 attempts reported the split as a planning gap, 4 of them citing the rule. The case has a second contract conflict: S3's partial confirmation is material yet frozen. The repair passes every mechanical check, so only the prose rule stands in the way. | firm | `verification.json` R3; `probes/r3-*` |
| R10-4 | Astra's "stop only on a structured blocker" would not have changed one of the 9 stops examined. revenue-export-lineage stopped on a *provisional* step's (S3) confirmation that the request froze; under the contract a partial confirmation on a step the cycle may change is material, and `edit_bounds` cannot freeze a single field. The free-text gaps already named obligation, repair and missing authority. library-reminders' stop is justified (an unqualified exactly-once goal over a read-then-mark interface); its case is under-specified. | firm | `verification.json` R4; `probes/r4-*` |
| R10-5 | 17 to 18 of 42 billing-late-fee key verdicts are false failures: the selectors expect a fixture filename and treat a step that configures `npm test` as one that runs it, while all six attempts chose a pretest-hook design the grader accepted. No qualification or block decision changes. | firm | `verification.json` R5 |
| R10-6 | `export PLAN` exports a plan edited after `finish`, and an incomplete run's plan. Plan Dispatcher's card and protocol name `scripts/export-execution-graph.js`, which no package ships, and protocol.md forbids resolving the sibling path. | firm (probes) | `verification.json` R7; `probes/r7-*` |
| R10-7 | A `submit --run` helper that runs `verify_script` itself breaks Until Loop's sole-caller rule (ADAPTER.md) and hooks-see-every-command. In the 30 candidate runs, record → verify → done took 3 shell calls in 30 of 31 cycles and every submission was accepted; 10 of 31 used a hand-written Python wrapper. | firm | `verification.json` R7-R8; `probes/r7-r8-*` |
| R10-8 | The fresh-route question phase caught gaps before freeze in 4 of 15 runs (an external approval in 3 of 3 known-external runs, an authored test suite once); its catches overlapped the loop's in 3 of 15. Moving a catch into cycle 1 forces a second review under D1 (one such run cost 988k tokens against 584-736k). | firm (n = 15) | `verification.json` R9-R10 |
| R10-9 | Every candidate cohort run read the Until Loop `references/runtime-ephemeral.md` (27,913 bytes) and Backchain's `technical-interactions.md` (9,608) whole: 30 of 30 each. The first is triggered by the vendored ADAPTER.md's "Read the callback adapter", the second by "read the relevant sections" with no section fetch. Lens cards, fetched by `lenses`, were read whole in 0 of 30. `prepare` also misnumbers its cross-references on the caller-without-draft route, and SKILL.md tells "generator drafts" to keep `unresolved: []` while the direct planner permits honest unresolved needs (15 of 15 direct drafts left it empty). | firm | `verification.json` R9-R10 |
| R10-10 | Rubric-eval's near-identical band is grader noise ÷ √passes, so a noisier judge widens what counts as equal: a 2-point loss is called near-identical 83% of the time at judge SD 10 and never at SD 2 (simulation, n = 10 clusters). Requiring the bootstrap and Wilcoxon to agree behaves like Wilcoxon with a sign check (false positives 4.7% vs 5.0%). 95.2% of the cohort's per-cell saving is cached input (−599,740 of −630,081); critical misses are computed but never reported. | firm | `verification.json` EVAL |
| R10-11 | In the 2026-11 paired differences the SD splits into 5.5 between cases and 9.8 between repeats (R1 grading; 11.1 and 10.7 registered). A new case buys more precision than a repeat: 20 cases × 1 run gives ±5.2 against ±5.6 for 10 × 3, with 20 fewer runs. | firm (t-based; this cohort's variance) | variance split of `r1-analysis.json` / `analysis.json` attempts |
| R10-12 | ShipLoop's `converge` mode never delivered its marker: the plan item says `required_trivial_reviews: 2` with no `Backchain passes: converge` line, and the spec item prints an empty marker, so since 0.7.0 the host runs `prepare` without `--passes` and freeze writes gate 1. The two converge texts that carry the marker reach no packet (BACKCHAIN_FOLDED_STAGES); the tests pin them. | firm (rendered packets) | `plan-critique.json` feasibility |

Dispositions, each with its reason:
- Astra 1 (R10-1): adopt. finish requires a complete source review for caller convergence; gap lists must be lists of strings.
- Astra 2 (R10-2): adopt, narrowed to goal, origin and need-closing initial facts; edge keys get a documented trust boundary only (the owner's KISS rule: no exposure).
- Astra 3 (R10-3): keep the rule and fix the oracle (owner D-B).
- Astra 4 (R10-4): rejected as specified; replaced by an input-only edit-bounds permission (owner item 4).
- Astra 5 (R10-5): adopt for the next cohort; the registered 2026-11 analysis is not regraded.
- Astra 6 (audit packet, invalidation threats): not adopted; no failure of that kind in 60 runs.
- Astra 7 (R10-6): adopt `export --run` and the pointer fix; scheduler integration tests deferred (no measured failure).
- Astra 8 (R10-7): rejected; residue only, `record` prints the done line, measured in cohort B.
- Astra 9 (R10-8): deferred; re-check against cohort B.
- Astra 10 (R10-9): adopt, without editing the shared Until Loop card, which is also ShipLoop's and Improve's.
- Evaluation (R10-10): adopt (owner D-A).
- Owner item 9, the release preflight's merge counting: already shipped in 39b417c26d24f2344a7b6c84617f8b94a9a554b8.

Owner decisions (2026-11-01):
- **D-A:** rubric-eval's near-identical becomes non-inferiority against an owner-set, pre-registered margin δ; noise/√passes above δ blocks. This amends the owner's 2026-09-27 rule (de621ab0cf8e8f7cd9d04a5f694036926cf89cd2, 7ff46b2cb85d480149318eb03c2eb61eeedac0ce); the order quality > tokens > time stays.
- **D-B:** keep the seed-narrowing rule; orders-cancel-rpc's oracle accepts "incomplete, with the split and confirmation gaps named".
- **D-C:** δ = 5 points.
- **Cohort size:** 20 cases × 1 run (R10-11), not 10 × 3.
- **D-D:** ShipLoop's `converge` completes at the first trivial review (Backchain's default gate), superseding D1's two reviews for converge. It is how converge has behaved since 0.7.0 (R10-12); 0 of 18 confirming reviews changed anything (R9-9).
- **Live ShipLoop runs:** one per release (the E2E gate), with a forced Backchain child.
- **D2's scope:** reference docs may state what a new script check refuses; text meant to change model behaviour waits for the cohort.
- **Cohort B's harness:** run.py on Codex Terra xhigh, graded by Opus. D3 is not extended; comparability with the 2026-11 numbers is given up.

Plan: release A ships the defect fixes (ShipLoop's Backchain-child packets and converge text, the Run Review exporter,
Plan Dispatcher's exporter pointer, finish/preservation/export checks) with one live ShipLoop round. Release B ships the
read and card cleanup and the input-only bounds once cohort B (40 runs plus a 4-run pilot and 2 targeted checks)
adopts them under the new rule. Rubric-eval's rule and the cohort tooling land when ready.

## Round 11 — release A re-scoped after two weeks, and its one live round (2026-11-15)

Question (owner, 2026-11-15): "we might need to rebase and reconsider where we left off on this." The branch was rebased
onto the 2026-11-15 origin/main. The owner chose to ship W3 (toolkit checks), W2 (Plan Dispatcher's
exporter pointer) and a rebuilt W1 (ShipLoop's Backchain child on 0.7.0's own route) as release A, with its one live
round. Cohort B and the rubric-eval rule (W7) are shelved; W4, W5 and W8 wait with them. Release A's commits:
76cc10ba3f19e512ac4fed0e041aa4082f9a0006 (W3), 0ec551ccb52f9c3bb1e1624735327d9944ad441d (W2),
3f9554a2b6820b65a3511f7c5ad3137dfa75c594 (W1) and d69438aae189e00c9cd4ab269e1bee7f0caeb11c (review round 1's two
material findings: the one-pass item did not say `--passes one`, and the start named only part of `prepare`). Main was
then merged in, at f896ec7a788913429a843e61b42ecfcf866d23d3.

| ID | Finding | Status | Evidence |
|----|---------|--------|----------|
| R11-1 | Given the rebuilt packet, a Codex Terra xhigh host ran Backchain's route itself. It ran `prepare` (`--run` the printed run directory, `--request`, `--caller`, `--binding`, `--passes one`), then `freeze`, `lenses`, `record`, `check` and `finish`, and hand-wrote no contract or receipt. `freeze` wrote gate 0. The child converged at its first review (trivial, one advisory finding) with a complete 2-step plan. R10-12's converge defect is fixed by text and hermetic tests only (D-D); no live run measures converge. | firm (n = 1, one host) | `test/shiploop_e2e/LEARNINGS.md` entry of 2026-11-15; the run's `events.jsonl` tool calls and `RUN/backchain/<action>/run/` |
| R11-2 | Release A's exporter reads a real 0.7.0 run: one "Plan loop" document (1 pass, complete, option `one`, candidate match yes, 4 min accept to accept) and no duplicate graph-check document. | firm (n = 1) | the run's `review-export/docs/backchain/` |
| R11-3 | The delivery passed all 5 held-out checks of `csv-report` in 1,479 s. The plan stage took 222 s with 20 tool calls; Codex reports no per-stage tokens. One run gives no comparison with earlier plan stages. | firm (n = 1); exploratory as a cost figure | `metrics.json`; `baselines.jsonl` row of 2026-11-15 |

Release order from here: the LEARNINGS commit (the last commit touching `skills/shiploop/` or `changes/shiploop/`), the
landing gate, then the push, `scripts/release.py`, CI and the host refresh. The gate passed: main's only commit since the
tested merge is b0285785374570c88f534480cf361778030018ac, which is docs-only.
