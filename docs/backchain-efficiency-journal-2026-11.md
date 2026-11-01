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
