# ShipLoop SDLC structure journal

Living journal for one question from the owner (2026-11-19): is ShipLoop's stage structure right, in particular the
planning sequence, how the dependency graph is made, and how the inner loop executes it, and should any of it change?

Evidence folder: `docs/experiments/sdlc-structure-20261119/` (scripts, their outputs under `evidence/`, the judges'
inputs and verdicts under `judge/`). Nothing in `skills/` changed in this round.

## Round 1 (2026-11-19): where the time goes, what each planning level contributes, what each review changes

### Question

ShipLoop runs 23 stages (`skills/shiploop/scripts/shiploop_stage_spec.py`, read at 2.2.0; the file is unchanged in
2.3.0, released the same day):

- once per run, before the work (PRELUDE): `intake`, `discovery`, `research`, `spec`, `test-strategy`, `plan`, `prepare`;
- per work item (INNER): `step-plan`, `test-spec`, `validate-existing`, then per step `implement`, `test`,
  `document`, then `carry-forward`;
- once per run, after the work (OUTER): `system-test-author`, `system-test`, `product-acceptance`, `release-plan`,
  `release-check`, `release`, `release-verify`, `operations`, `handoff`.

An Improve review (a second model pass that may edit the stage's output) follows `spec`, `test-strategy`, `plan`, the
first item's `step-plan`, each step's `document`, the last `carry-forward`, `system-test-author` and `release-plan`.

Three sub-questions: (1) is the planning sequence right, (2) is the dependency graph made in the right place and used,
(3) does the inner loop earn what it costs.

### Method

Offline, from records already on disk. No new ShipLoop run was launched.

- **Corpus.** Every run folder under `/Users/dadleet/e2e-runs*` with a navigator trace (`run/trace.jsonl`): 605 runs
  read, 420 on the current stage set (2026-10-29 to 2026-11-18), 273 of those finished. Host mix of the 273:
  Codex gpt-6.1-terra 263, Codex gpt-6.1-sol 4, Grok 4.6 4, Claude Sonnet 5.5 2. Median run 13.4 minutes, 90th
  percentile 23.5, longest 364 (the three Grok 4.6 xhigh `ticket-due-times` runs of 2026-11-14).
- **Time by stage** (`stage_census.py`): the seconds between two consecutive navigator commands belong to the stage
  the run was in. Review time is charged to the stage it reviews. Gaps over 45 minutes are idle, not stage time
  (0.0 h excluded).
- **Review yield** (`passes_census.py`): ShipLoop's own pass log, `run/improve/<action>/passes.md`, flags for each
  review pass whether it changed files or the stage result.
- **What a review changed** (`review_edits.py`): ShipLoop snapshots the working tree as a Git tree before each review
  (`run/improve/<action>-bind.md`). Diffing that tree against the first commit after it names the files the review
  itself changed, classed with ShipLoop's own catalog (`shiploop_item_scope.classify`). The pairing is exact where a
  commit follows the review directly: it agrees with the pass log's own flag in 99% of `spec`, 100% of
  `test-strategy`, 94% of `plan` and 84% of `document` reviews (the 16% are `.gitignore` written at commit time).
  It is wrong for `step-plan` (the next commit is the built step) and unreliable for `release-plan` (61%) and
  `system-test-author` (52%), so those are read only where the pass log flags a file edit.
- **Side test, judged** (`build_diffs.py`, `score_judges.py`): the real diffs that planning reviews made, sampled
  with a fixed seed (40 each of `spec`, `test-strategy`, `step-plan`; all 16 `plan`), 136 in all. Two independent
  Claude Opus 5.5 judges per batch read only the diffs and labelled each `substance` (changes what gets built or
  checked), `sharpening` (more exact, same work), `record` (bookkeeping) or `unclear`. The reviewer's own account of
  its work was not shown.
- **History** (an Opus 5.5 agent, read-only): commit messages and docs on every earlier change to the stage list,
  so that nothing already rejected is proposed again. Its findings are cited inline below with their sources.

### Results

**R1. Time by stage, 273 finished runs, 87.3 stage-hours** (`evidence/stage-census.txt`).

| Part of the run | Share of run time |
|---|---|
| Before the work (7 stages, 3 reviews) | 20.8% |
| The work items (7 stage kinds, 3 reviews) | 55.1% |
| After the work (9 stages, 2 reviews) | 24.1% |
| All Improve reviews together | 32.9% |
| `implement` + `test`, own time | 19.8% (`implement` alone 7.9%) |
| Everything before the first product edit (`intake` to `test-spec`, with reviews) | 36.2% |

Largest single lines, own time + review time: `document` 5.9 + 7.7, `test` 11.9 + 0.2, `step-plan` 6.2 + 5.7,
`implement` 7.9, `carry-forward` 2.7 + 3.4, `spec` 1.4 + 3.8, `plan` 2.2 + 3.0, `release-plan` 1.8 + 3.2,
`system-test-author` 2.2 + 2.7, `test-strategy` 1.8 + 3.1. The six runs of an hour or more have the same shape
(reviews 34.3%, before the first edit 33.8%, after the work 18.0%).

**R2. The planning window depends on the host, not on the stage list**
(`evidence/planning-window-steps-sendbacks.txt`). Start to the first `implement` packet: Codex terra median 4.7 min
(max 14.7, n=263), Codex sol 8.1, Claude Sonnet 7.8, Grok 4.6 xhigh 118.8 (4 of 4 over 30 minutes). In the three long
Grok runs Improve is 50 to 57 of the 115 to 124 planning minutes (history agent, from each run's `metrics.json`).

**R3. The work queue is one item** (`evidence/step-dependencies.txt`). 281 of 282 accepted `plan` results queue
exactly one work item. Finished runs end with 1 item in 265 of 273; the other 8 gained items later (`add-work` in 6
of 420 runs, or a `carry-forward` addition). The largest request in the corpus (ticket due times: 11 requirements,
config, storage, migration, a feature switch, rollback, 6 hours on Grok) is one work item with 9 steps. What the
`plan` stage produces that later stages use is its assumption list (584 assumptions over 272 plans: 288 evidenced,
142 probed, 154 open; 132 plans probe at least one), its per-item concern decisions and its architecture decisions,
not an order of work.

**R4. The dependency graph is the step list, and it is sound.** 431 step plans: 303 have one step (70%). Of the 128
with two or more, 90 are a straight chain (70%) and 32 are wider than one (25%, widths up to 5). Every multi-step
plan records `deps` on every step, and none lists a step before one it depends on, because `complete` refuses it
(`shiploop_navigator.py`, "step deps must name earlier steps"). `deps` has two consumers: the `implement` packet's
"Depends on:" line, which points at each dependency's accepted result, and the progress and trace views. Of 122
dependency-independent step pairs, 5 share a declared file (4%). The separate plan-graph JSON format and its
record-only `backchain-check` ran in 6 of 273 finished runs (`evidence/by-host-and-graph-check.txt`), none on Codex;
its text is 554 characters in each of three packets.

**R5. Plans hold.** 95 of 420 runs record a send-back (23%): 7.8% of `implement` results, 6.5% of `test-spec`, 2.7%
of `test`, 1.8% of `validate-existing`, 1.7% of `system-test`, 0.6% of `document`. The stage is accepted again a
median 1.1 to 2.7 minutes later (Codex). `product-acceptance` asks for more work in 1.4% of results. The refused
`step-plan` commands (249 `check`, 25 `complete`) are shape and consistency rules a script catches: a missing result
file, a test command without criterion IDs, a proof over two lines, a proof that runs a test file no step has
written yet, an open plan assumption not settled by the item (`evidence/more-cuts.txt`).

**R6. Review yield differs ninefold by stage** (`evidence/review-yield.txt`, 2,447 reviews).

| Reviewed stage | Reviews | Edit anything | Median lines edited | Share of run time |
|---|---|---|---|---|
| `step-plan` | 365 | 37% | 5 | 5.7% |
| `document` (the step's code review) | 436 | 36% | 14 | 7.7% |
| `spec` | 270 | 28% | 3 | 3.8% |
| `test-strategy` | 270 | 24% | 2 | 3.1% |
| `carry-forward` (end of work) | 278 | 15% | 14 | 3.4% |
| `release-plan` | 275 | 13% | 6 | 3.2% |
| `plan` | 270 | 6% | 15 | 3.0% |
| `system-test-author` | 283 | 4% | 12 | 2.7% |

49% of all review seconds are spent in reviews that edit nothing.

**R7. What the later reviews change** (`evidence/review-edits-all-pairings.txt`, restricted as in Method). Of 436
step reviews, 140 changed code or tests (32%) and 95 changed product code (22%), after that step's tests were already
passing. The end-of-work review changed code or tests in 10% of one-step items (n=200) and 21% of items with two or
more steps (n=78), so it is not a repeat of the step review. `spec` and `test-strategy` reviews edit only their own
documents. The 9 `system-test-author` reviews that edited files all edited tests.

**R8. Side test: what the planning reviews' edits are** (`evidence/judged-review-edits.txt`). Judges agree on 88% of
labels (Cohen's kappa 0.79; substance against the rest 92%, kappa 0.84, "almost perfect" on the Landis and Koch
bands). The range is both judges to either judge.

| Reviewed stage | Diffs judged | Judged substance | Reviews that edit | Reviews making a substantive edit |
|---|---|---|---|---|
| `step-plan` | 40 | 82 to 85% | 37% | 31% |
| `spec` | 40 | 40 to 48% | 28% | 11 to 13% |
| `test-strategy` | 40 | 30 to 40% | 24% | 7 to 10% |
| `plan` | 16 | 25 to 44% | 6% | 2 to 3% |

Typical substance: a step's proof changed to assert the real output; an acceptance line added for malformed input; a
missing edge case added to the test plan. Typical sharpening: a worked example of a rule already stated; a criterion
reworded to name its assertions. 8 to 10 of the 40 `test-strategy` edits fix a shape rule a script could check.

Review time per edit of the useful kind, in points of run time (`evidence/by-host-and-graph-check.txt`):
`step-plan` 18, step review 24, end-of-work 26, `spec` 29 to 35, `test-strategy` 31 to 44, `system-test-author` 90,
`plan` 100 to 150.

**R9. The yields are one host's.** Codex is 405 of the 436 step reviews. On Grok 4.6 xhigh (4 runs, one case) the
pattern is reversed: step reviews edited files in 5 of 29 and never code or tests, and all 9 planning reviews
edited. Two Claude runs are too few to read.

### Findings

- **F1 (firm).** Stage count is not where the time is. Reviews are a third of a run and the model's own work per
  packet is most of the rest. This matches the earlier record: cutting the inner loop from 17 stages to 8 made slices
  2 to 38% slower (LEARNINGS, "The 8-stage inner loop", 2026-10-10), and ShipLoop's commands are a small share.
- **F2 (firm).** ShipLoop does not loop over work items in practice. It makes one pass (before the work, one item,
  after the work) with a loop over steps inside it. The work-item level is used for corrective and added work.
- **F3 (firm).** The dependency graph is made at `step-plan`, is checked by the script, and has consumers. The `plan`
  stage decides design, not order.
- **F4 (firm on Codex terra, exploratory elsewhere).** The step review and the `step-plan` review earn their place:
  about one in three changes code, tests or the substance of the step plan. The `plan` review (2 to 3% substantive)
  and the `system-test-author` review (4% edit anything) do not show it. They cost 5.7% of run time together.
- **F5 (firm).** The planning sequence produces plans that hold (R5). Nothing here supports reordering or merging
  planning stages.
- **F6 (interim).** An edit is not an escape: a substantive edit might have been caught downstream anyway, and a
  review that edits nothing does not prove there was nothing to find. The defect-escape rate without planning reviews
  is still unmeasured (it was unmeasured in I5, commit 47c3e8b702f3e043d44fbb5b6b8917ed1a09f615, and the three-arm
  comparison approved on 2026-10-28, `docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md` Q2, was never run).
- **F7 (unknown).** Nothing in the corpus is larger than one item of 11 steps. Whether a single step plan stays
  sound for a request several times that size is not measured. `step-plan` is already the most refused and most
  edited planning stage.

### Recommendation (owner's decisions; nothing built)

1. **Keep the stage list and its order.** No stage is added, removed, merged or reordered. Earlier proposals to merge
   planning documents, skip `step-plan` or `test-spec`, or plan in a rolling wave were rejected on 2026-10-06, and the
   2026-11-13 lifecycle assessment defers stage and review-default changes until a registered comparison shows a gain
   without a regression (`docs/shiploop-lifecycle-assessment-2026-11-13.md`). This round found no reason to reopen
   them.
2. **Keep the dependency graph as it is made today**, at `step-plan`, with `deps` checked by the script.
3. **Keep the inner loop**, including the per-step review and the end-of-work review (R7).
4. **Review placement is the one thing worth changing**, and it is a product trade-off, so it is the owner's call:
   stop reviewing `plan` and `system-test-author` by default. Expected gain on Codex: 5.7% of run time. Bounded
   loss: a substantive plan edit in about 1 run in 40, with the `step-plan` review that follows still reading the
   plan; a test edit in about 1 run in 30. Because of R9 this should be read on the current default subject
   (Codex Sol 6.2 xhigh) first. That reading is free: the pass logs and snapshots of the next ordinary runs give the
   same tables with `passes_census.py` and `review_edits.py`, with no extra run.
5. **Optional cleanup, low value:** the plan-graph JSON format and `backchain-check` (about 41 KB of script) ran in
   2% of finished runs. Retiring them changes no ordinary run; it saves upkeep only.
6. **The open risk is size (F7), not structure.** If larger requests matter, one run on a request with several
   subsystems would show whether the model splits it into items and whether a long step plan degrades.

### Limits

- 96% of the finished runs are one model (Codex gpt-6.1-terra) on small one-application requests. The default E2E
  subject changed to Codex Sol 6.2 xhigh on 2026-11-19 (f4690f7066ce51b35033607fc8fefdb4f592f3fc); none of these runs used it.
- Run-time shares are wall-clock gaps between navigator commands. They include the model's waits on its own tools.
- The judges saw diffs cut at 5,000 characters, and both are the same model. `plan` has 16 diffs.
- `release-plan` review edits were not judged (the snapshot pairing is unreliable there).

### Evidence

| File | Holds |
|---|---|
| `evidence/stage-census.txt` | time by stage, outcomes, refusals, passes, packet sizes (R1, R5) |
| `evidence/planning-window-steps-sendbacks.txt` | planning window by host, per-step seconds, send-back recovery (R2, R5) |
| `evidence/step-dependencies.txt` | steps per plan, chain against graph, queue length (R3, R4) |
| `evidence/review-yield.txt` | pass-log yield by reviewed stage (R6) |
| `evidence/review-edits-all-pairings.txt` | file classes each review changed, all pairings (R7; read with Method's limits) |
| `evidence/more-cuts.txt` | assumptions by disposition, end-of-work yield by step count, refused step-plan commands |
| `evidence/by-host-and-graph-check.txt` | yield by host, runs that used the plan-graph check, cost per useful edit (R4, R8, R9) |
| `evidence/judged-review-edits.txt` | the judges' agreement and verdict shares (R8) |
| `judge/diffs-1.txt`, `judge/diffs-2.txt`, `judge/diff-key.json` | the 136 diffs as the judges saw them, and which run each came from |
| `judge/out-A-*.jsonl`, `judge/out-B-*.jsonl` | each judge's verdict and reason per diff |

To rerun: `python3 -I stage_census.py <work>/census.json` writes the run list the other scripts read
(`passes_census.py <work>/census.json <work>/samples.jsonl`, `review_edits.py <work>/census.json
<work>/review_edits.json`, `deps_census.py`, `extras_census.py`, `more_cuts.py <work>`, `build_diffs.py <work>`,
`score_judges.py judge`). The run folders are outside the repository and may be pruned; the outputs above are the
record.
