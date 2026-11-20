# ShipLoop SDLC structure journal

Living journal for one question from the owner (2026-11-19): is ShipLoop's stage structure right, in particular the
planning sequence, how the dependency graph is made, and how the inner loop executes it, and should any of it change?

Evidence folder: `docs/experiments/sdlc-structure-20261119/` (scripts, their outputs under `evidence/`, the judges'
inputs and verdicts under `judge/`, and round 3's under `judge-replay/`). Nothing in `skills/` changed in any round.

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

## Round 2 (2026-11-19): where Ask Agent could run workers at once in one directory, and whether planning can mark it

### Question

Owner, the same day: is there anywhere in the phases where using Ask Agent should be discussed, meaning work that
several agents could do at once in the same directory without stepping on each other, and can the planning phase
identify it?

### Method

Offline again; no run and no worker was launched.

- **What already exists** (read): Ask Agent's current-workspace route (`skills/ask-agent/references/current-workspace.md`),
  In Parallel's card, ShipLoop's `delegation: ask-agent` route (`references/run-options.md`, `references/navigator.md`),
  and the parallel-execution study's contract (`docs/experiments/parallel-plan-execution-20261114/skill-layer-contract.md`
  sections 6 and 7).
- **Which gates assume one writer** (an Opus 5.5 agent read the scripts; I checked `write_problem`, `commit_scope`,
  the mutation docstring and the navigator's delegated-work row myself).
- **What could overlap** (`overlap_ceiling.py`): at the stage level from `Stage.reads` in the stage table; at the step
  level from each recorded plan's `deps` against the trace's per-step time (every ready step at once, no overhead).
- **Whether a plan's file declarations hold** (`write_set_fidelity.py`, `shared_files.py`): each step's declared
  `paths` against the files its commit changed, 586 step commits of 377 step plans.
- **How long one read-mostly piece is, by host** (`task_sizes.py`), beside the study's break-even.

### Results

**R10. The rule already written.** Ask Agent in the current directory allows any number of `report-only` workers
(nothing tracked or untracked is written) and at most one `in-place` writer, limited to a declared write set, while
the parent keeps its own writes off the checkout; `verify-return` reports any other change as `drift`. In Parallel
repeats it: "report-only readers may run in parallel, but edits require one exclusive writer and capacity one."
ShipLoop's `delegation: ask-agent` starts one fresh worker at a time, never two.

**R11. Every ShipLoop gate reads the whole directory** (the audit; symbols in `skills/shiploop/scripts/`).

| Gate or record | Reads or writes | With a second writer on other files |
|---|---|---|
| Step commit (`_commit_stage`, `item_scope.commit_scope`, `git.commit_paths`) | the whole diff, filtered to the item's declared paths, `docs/shiploop/` and any documentation file; the shared Git index | sweeps the other agent's files in; index collisions |
| Lint gate (`lint.lint_pass`) | the whole tree against the item base; rewrites lines in fix mode | flags and rewrites the other agent's lines |
| Step proof, candidate test run (`test_loop.step_proof`, `verify`) | run in place | include unfinished edits |
| Base test run (`test_loop._BaseTree`) | a temporary worktree, with every changed test file copied in | copies the other agent's tests |
| Mutation check (`shiploop_mutation._check`) | a temporary copy, never the checkout | mutates the other agent's code too |
| Document applicability and rerun (`item_scope.no_document_item`, `_document_rerun`) | the whole tree | wrong applicability, forced reruns |
| Review snapshot and review commit (`improve_changes.review_changes`, `_improve_commit`) | whole trees | false refusal; commits the other agent's files |
| Expectation checks (`expectations.run`) | `git status` before and after | a false "the check wrote" |
| `state.md` | one lock, one cursor (`_active_cursor`, "stale navigator action ID") | one action at a time by design |
| `loops/`, review scratch folders, the Until Loop stack | per action or per session | safe |

A reusable piece exists: `expectations.write_problem(command)` decides from a command's shape whether it writes.
And the navigator guide already lets the owner of `step-plan`, `implement` or a step's review split its own work
by "bounded task/file ownership" and check the combined result "before its one completion" (navigator.md,
responsibility table, "Own delegated work").

**R12. Stages form a near-strict chain** (`evidence/overlap-ceiling.txt`). Only three neighbouring pairs exist where
the later stage is not given the earlier one's result: `test-spec` then `validate-existing` (script-run, 0.0%),
`carry-forward` then `system-test-author`, and `product-acceptance` then `release-plan`. Overlapping them could save
at most 6.2% of run time, and each pair is two writers or one outcome that can cancel the other.

**R13. Step overlap would pay only on a slow host** (`evidence/overlap-ceiling.txt`). Ideal overlap of ready steps
saves 9.7% of build-step time in the 36 eligible Codex terra runs (10 have any width), which is 0.6% of all run time
on that host. On the two eligible Grok 4.6 runs it saves 43.9% of build-step time, 34.7% counting only steps with no
declared file in common: 62 and 48 minutes of runs of 364 and 348 minutes, with a median step of 17 minutes.

**R14. A plan's file declarations do not predict what a step writes** (`evidence/write-set-fidelity.txt`,
`evidence/shared-files.txt`). Of 586 step commits, 10 changed only the paths the step declared (2%). Undeclared:
the knowledge home in 86%, a test file in 84%, a document in 61%, product code in 12%. Of the 114 step pairs that
the plan makes independent and file-disjoint, all 114 wrote a file in common: the knowledge home in 105, a test file
in 77, a document in 18, product code in none. In 49 of 78 multi-step items (63%) every step writes one and the same
test file; the median item has one test file.

**R15. One read-mostly piece is short on the fast hosts and long on the slow one** (`evidence/task-sizes.txt`).
Median seconds per run, Codex terra / Claude Sonnet 5.5 / Grok 4.6: `discovery` 18 / 25 / 236; `research` 9 / 19 /
97; review of `spec` 32 / 68 / 647; review of `step-plan` 43 / 34 / 947; the step review, per step, 32 / 107 / 337.
The study's break-even, in seconds of the model's own time per task below which fresh workers lose to one context:
Claude 10 to 14, Grok 3 to 21, Codex 43 to 60. A fresh Claude worker costs about 86,000 tokens of fixed startup
(current-workspace.md), and one fresh worker per stage, one at a time, took 4.1 times the inline time on the one
case measured (LEARNINGS, the per-step ask-agent route).

### Findings

- **F8 (firm).** In one directory the safe shape is many readers beside one writer. Two writers are not safe under
  ShipLoop even on different files: its gates read the whole tree (R11) and the steps share files in practice (R14).
- **F9 (firm).** Plans cannot mark safe write-pairs today. The declaration covers product code, where it holds (no
  independent pair shared a code file), and leaves out the test file, the documents and the knowledge home that
  every step writes.
- **F10 (firm).** Nothing at the stage level is worth overlapping (R12).
- **F11 (interim).** The read-only work large enough to share is the finding half of the reviews, which are a third
  of a run. It fits inside one stage, under one owner and one completion, so it needs no change to the cursor, the
  gates or the directory rule. Whether several lens readers find more than one reviewer is not measured.
  *Measured 2026-11-20 for the step review (round 3, F13): they do not, on the recorded misses.*
- **F12 (interim, two runs).** Step overlap is the only large time prize (R13) and it is a two-writer shape. The
  earlier study priced a worktree per attempt at 0 to 11 seconds over a shared checkout (contract section 7, E13),
  so the same directory buys nothing for writers; it would also need a test file per step and one serial point for
  documents and the knowledge home.

### Recommendation (owner's decisions; nothing built)

1. Discuss Ask Agent in one place first: read-only lens workers inside the `step-plan` review and the step review,
   the two reviews that change something about one time in three (R6 to R8). The owner of the review applies the
   edits and completes once. The plan already names the units: each step's criteria and paths.
   *Superseded 2026-11-20 for the step review: round 3 found no gain from three lens readers or three plain
   readers on 18 recorded misses, so this is withdrawn there. The step-plan review was not tested.*
2. Do not pursue two writers in one directory. If step overlap is wanted for slow hosts, it is the worktree route
   already studied, and its first requirement is that each step declares its own test file.
3. Add no planning-time "may overlap" marker now: computed from today's plans it would be wrong for every pair (R14).
4. Readers need no marker from the plan. What makes a worker a reader is that it writes nothing, which Ask Agent's
   `report-only` mode and its drift check enforce, and `write_problem` can screen its commands.

### Limits

- The step-overlap figures for the slow host are two runs of one case; they assume no overhead and unlimited
  workers.
- R14 compares against each step's own `paths`; the item's `paths` (which the step commit uses) do list the test
  file and the documents.
- No worker was launched: the costs quoted are the earlier study's, on Claude Code 2.1.325, Codex 0.169.0 and Grok
  Build 1.0.77.

## Round 3 (2026-11-20): do several read-only reviewers catch what one step reviewer missed?

### Question

F11 left one thing unmeasured: whether several lens readers find more than one reviewer. The owner said "Yes" on
2026-11-20 to testing it on the recorded cases where a step review passed and the end-of-work review then fixed
code or tests. Consumer: the owner's decision whether to discuss read-only reviewers inside the step review.
Improve already has the switch: its review policy runs "a fresh, read-only independent reviewer" only when the
owner binding selects one (`skills/improve/references/review-policy.md`, "Independent review"); ShipLoop's
binding does not, and every recorded review is `self-review (inline default)`.

### Registered design (written and committed before any counted reviewer ran)

**Cases** (`replay_cases.py`, `evidence/replay-cases.txt`, `judge-replay/cases.json`). Of 37 end-of-work reviews
that changed code or tests, 18 pass both rules: the fix's code and test patch applies cleanly to the tree the step
review was bound on (the fixed lines were in front of the step reviewer, unchanged), and every fixed file is part
of that step's own change. 11 are items of one step (c01 to c11) and 7 are the last step of a longer item (m01 to
m07). All 18 were written and reviewed by Codex gpt-6.1-terra, on 8 example applications; by fix subject they are
12 distinct defects (large integers on newer Python 3 cases, long CSV fields 2, encoded group IDs 2, large page
numbers 2, repeated ticket filters 2, seven others once each). The 19 others are left out because the step review
or the carry-forward stage had since edited the same lines (15) or the fix lay in an earlier step's files (4).

**What a reviewer is handed** (`replay_build.py`): the bound tree as a read-only folder, the step's diff, the
recorded review's own hand-off (what the review looks for, the code craft rules, the step with its criteria, test
cases and proof, the stage's result) and the run records that hand-off names. Paths of the original run are
replaced by symbols. The reviewer reports and changes nothing; it may copy the tree to its own folder and run it.

**Arms** (`replay_run.py`, `evidence/replay-briefs.txt`): six reviewers per case, all reading the one case folder
at the same time.

- p1, p2, p3: the plain brief, the whole review against the hand-off's full list. Three independent draws.
- lb, lt, ld: one lens each. Behaviour (does the code do what the spec and criteria say for every input), tests
  (would a test fail if the behaviour broke), documents and craft. The three lenses together cover the hand-off's
  list; the wording was fixed before any fix was read.

**Models.** Reviewers: `claude-sonnet-5-5`, effort high, headless Claude Code 2.1.328 in safe mode with Read, Grep,
Glob and Bash only. Judges: two independent Claude Opus 5.5 agents per packet, blind to which report came from
which arm (`replay_judge_packets.py` shuffles the six reports under letters with a fixed seed).

**Scoring.** For each report a judge answers against the end-of-work fix: `caught` (a finding names the same
defect, the same wrong behaviour or the same missing test, closely enough that acting on it would produce the fix
in substance), `near` (the same function or symptom without the defect itself) or `missed`. A report counts as
caught only when both judges say caught; the either-judge count is reported beside it.

- M1, one plain reader: the share of plain reports that caught, over 54.
- M2, three plain readers: cases where any of p1 to p3 caught, of 18.
- M3, three lens readers: cases where any of lb, lt, ld caught, of 18.
- Also: caught by lens; findings per report; seconds, tokens and dollars per reader and per arm; whether the
  shared folder changed; paths a reader used outside its two folders.

**Readings.**

- Lenses add over extra readers if M3 is at least 3 cases above M2 (about 15 points, the bar this project uses);
  no lens effect is seen if they differ by 2 or fewer; lenses lose if M2 is at least 3 above M3.
- More readers add over one if M2 is at least 15 points above M1.
- M1 is reported with its interval and has no bar: it says how often one fresh reader finds these at all.

**What each outcome would lead me to recommend** (the owner decides; a live check would come before any default).

- Lenses add: discuss lens readers in the step review through Improve's existing independent-review selection.
- No lens effect, but three readers add over one: the gain is in more reads, not in lenses; the simplest form is
  the one fresh independent reviewer Improve already describes.
- Three readers catch few (under a quarter of cases): fresh readers do not find these defects; leave the step
  review as it is and let the end-of-work review keep catching them.

**Limits known before the run.**

- Every case was chosen because one reviewer (terra) missed the defect, so a fresh reader will catch some by
  chance alone; that is why three plain draws are the control for three lenses.
- The readers are Sonnet 5.5 and the code and the recorded review are terra's: a different model reading is part
  of any effect on M1 and M2. The lens comparison (M3 against M2) is within one model.
- One defect per case is the yardstick. A reader's other findings are counted, not verified.
- The end-of-work review already catches these defects one stage later; the replay measures whether more readers
  at the step would catch them, not what escapes the whole run.
- 18 cases, 12 distinct defects, 8 small example applications.

**Rules for a failed reviewer.** One that times out, returns no report, or reads the judges' key, another report,
another case, the original runs or this repository is rerun once in a fresh folder; a second failure counts as
missed and is reported. Budget: at most $2 a reviewer and $60 in all.

**Rehearsal** (one excluded case, x01, not counted): six reviewers took 50 to 91 seconds and $0.14 to $0.22 each
($1.07 together), and the shared folder's manifest was identical afterwards. Three of the six wrote a probe file
with the same name in `/tmp` (`/tmp/x.csv`) at the same time, so readers that run code can step on each other
outside the directory they share. Apparatus fix before the counted run: each reviewer gets its own `TMPDIR` and a
rule to create temporary files only in its own folder. The lens wording was not changed.

### Results (run 2026-11-20; the design above was committed first as e68a5fc4be47fd030f783ef2e250105683b60b4a)

**R16. The run** (`evidence/replay-results.txt`, `judge-replay/reviewers.json`). 108 reviewers ran, twelve at a
time, in about 12 minutes. Every one returned a report; none timed out; all were served by `claude-sonnet-5-5`.
Per reader, median: 60 seconds, $0.19, 7 turns, 5 findings. $21.18 in all. A case's six readers were done when the
slowest finished, a median 85 seconds (396 seconds if run one after another).

**R17. The judges** (`judge-replay/out-A-*.jsonl`, `out-B-*.jsonl`). The two judges gave the same verdict on 107 of
108 reports (kappa 0.98). The one difference is c10's behaviour-lens report, caught for one and near for the other.

**R18. The registered measures.** Counted when both judges say caught; the either-judge count in brackets.

| Measure | Result |
|---|---|
| M1, one plain reader | 6 of 54 reports, 11% (95% interval 5% to 22%) |
| M2, three plain readers | 3 of 18 cases, 17% |
| M3, three lens readers | 4 of 18 cases, 22% (5 of 18) |
| Any of the six readers | 5 of 18 cases (6 of 18) |
| By lens | behaviour 4 (5), tests 2, documents and craft 1 |
| Items of one step, three plain / three lens | 3 of 11 / 3 of 11 |
| Longer items, three plain / three lens | 0 of 7 / 1 of 7 |

Which cases: c05 (a missing test of half-even ties) by all six; c08 (invalid Unicode IDs) by two plain readers and
the behaviour lens; c07 (large integers) by the behaviour lens only; c11 (large page numbers) by one plain reader;
m07 (the same defect in a longer item) by the behaviour and tests lenses. Thirteen cases were caught by no reader.
By distinct defect, 4 of the 12 were caught at least once.

**R19. What the readers did see** (exploratory, not registered). Counting a report when both judges say caught or
near, a reader had the same behaviour in hand in 21 of 54 plain reports and 19 of 54 lens reports; in 11 of 18
cases for three plain readers, 10 of 18 for three lens readers, and 10 of 18 for the behaviour lens alone. In 16 of
the 26 near reports, across 6 cases, both judges' sentences say the reader argued for another outcome than the fix:
reject or bound the input, or call the rejection correct, where the end-of-work review made the code accept it (a
5,000-digit unit count, a 400-digit page number, a field over the CSV parser's limit).

**R20. Volume.** The 108 reports hold 531 numbered findings, 262 from the plain readers and 269 from the lens
readers: about 5 a reader and about 30 a case. Only the one finding per case that matches the fix was checked.

**R21. Conduct outside the shared folder** (`replay_conduct.py`, `evidence/replay-conduct.txt`). All 18 case
folders had the same manifest before and after their six readers. 106 of the 108 readers ran the code or its tests
in their own copy. Outside the shared folder they could still disturb each other:

- 7 readers stopped processes by a name pattern (`pkill -f`). Three patterns were wide enough to match another
  reader's process or anything else on the machine: `server.py`, `tree/server.js` and `node --test`.
- In 3 cases two readers of the same case used the same network port; one reader's output shows an
  address-in-use error.
- One reader wrote its scratch copies in the folder above its own. In the rehearsal three readers wrote
  `/tmp/x.csv` at once.
- 49 readers hit a permission error first, because a copy of a read-only tree is read-only too.

The path audit flagged two readers (c08 tests lens, m02 documents lens). I read both commands: one listed and
cleaned the folder above its own, the other named a path that does not exist. Neither read the judges' key, a
report, another case, an original run or this repository, so the rerun rule did not apply; neither report was
judged caught.

### Registered readings

- **No lens effect is seen.** Three lens readers caught 1 case more than three plain readers (4 against 3; the
  bar was 3 cases).
- **More readers do not add over one by the bar.** Three plain readers reach 17% of cases against 11% for one
  (6 points; the bar was 15).
- **Three readers catch few.** 17% and 22% of cases, under a quarter. The registered consequence: fresh readers
  do not find these defects; leave the step review as it is and let the end-of-work review keep catching them.

### Findings

- **F13 (firm for these cases).** Read-only reviewers at the step, plain or lens, do not reproduce what the
  end-of-work review finds. Six readers together found its defect in 5 of 18 cases.
- **F14 (interim).** Many of these fixes are a judgement about a limit nobody stated. In 6 cases readers had the
  very input in hand and argued for the opposite outcome (R19). More readers then bring conflicting advice that
  one owner still has to settle; the disagreement is about the spec, not about reading skill.
- **F15 (exploratory).** Within the lens arm the behaviour lens did the work: it caught 4 of 18 by itself, the
  tests and documents lenses added no case, and it alone had the behaviour in hand as often as three lens readers
  together. A single reader that runs the code against the spec's inputs is the only form that showed anything,
  and it was not a registered arm.
- **F16 (firm).** The cost of readers is not money or time (19 cents and a minute each). It is triage: about 30
  unverified findings a step from six readers, where the recorded step review edits anything in 36% of steps.
- **F17 (firm).** Readers do not step on each other in the directory they share: 18 of 18 folders were untouched.
  Readers that run code step on each other outside it, through process names, ports and shared temporary names
  (R21). A contract for concurrent readers needs four lines: your own temporary folder, your own ports, stop only
  process IDs you started, and copy the tree with write permission.

### Recommendation (owner's decisions; nothing built)

1. Do not add read-only reviewers to the step review, as lenses or as extra plain readers, and leave Improve's
   independent review unselected in ShipLoop's binding. The end-of-work review is the second look that finds
   these defects and it already runs one stage later.
2. Round 2's first recommendation (discuss Ask Agent for read-only lens workers inside the step-plan review and
   the step review) is withdrawn for the step review. The step-plan review was not tested: the records hold no
   list of what it missed, and nothing here argues for it.
3. If concurrent readers are used anywhere, give them F17's four rules. `report-only` and the drift check protect
   the directory and nothing else.
4. Not measured, for the owner to weigh: seven of the 18 fixes are about how large an input may be (integer
   digits, field length, page number), and in six of those cases readers argued for rejecting what the fix
   accepts. Where the spec states the limit, a reviewer has something to check instead of something to decide.

### Limits

- The yardstick is one reviewer's fix (terra's end-of-work review). A reader's other findings, about 5 a report,
  were not checked; some may be real defects that no recorded review found. The replay cannot say.
- Sonnet 5.5 read what terra wrote and reviewed. Another reader model, or the same model as the writer, may differ.
- 18 cases, 12 distinct defects, 8 small example applications; one run per reader; M1's interval is 5% to 22%.
- Readers reported and did not fix. Improve's loop lets a reviewer change the code and check again.
- Both judges are the same model; a lens report can give its lens away by what it covers.
- Two readers' `pkill -f` patterns (`node --test`, `server.py`) could have ended unrelated processes on this
  machine while they ran; whether they did was not checked.

## Round 4 (2026-11-20): where does the build loop iterate, and are the order, the step criteria or the Until Loop the cause?

### Question

Owner, 2026-11-20: execution is slow when the first implementation is only moderately correct, running real tests
then finds gaps in the logic, and the model iterates to tune it. Are the planning stages, the inner-loop stages, the
Until Loop and the step criteria ordered and used appropriately, or is some of it unnecessary? The intended drivers
are less capable than the strongest models: GPT Sol 6.2 at medium, Claude Sonnet 5.5 at high, Grok 4.6 at extra
high. Research the outside world, but prioritize side experiments on ShipLoop itself or pieces of it.

Consumer: the owner's decisions on what to optimize for those drivers. Nothing in `skills/` changes in this round.

### How to evaluate it (the frame used below)

A run can lose time to an imperfect first implementation in only a few places, and each leaves a record:

1. the step's own Proof fails at `implement` (ShipLoop's step-proof records and the model's own runs);
2. the tests written at `test` fail and the product code is changed (the model's own test runs, and the Git tree
   ShipLoop snapshots at every lint gate, diffed for product-code lines);
3. ShipLoop refuses the `test` result (the refused command's own output says why);
4. the step review or the end-of-work review changes product code (the review snapshots);
5. a system test or the acceptance stage sends work back;
6. the delivered product still fails checks the model never saw (the E2E harness's held-out acceptance).

For each place the questions are: how often does it fire, what does it cost, and was the fix needed for the
product to be right by a yardstick the model never saw. The last one is answered by grading every snapshot of a
run, not only the delivered product, with the held-out checks.

### Method

Offline, on the 273 finished runs of round 1's census (no model called):

- **Iteration census** (`iteration_census.py`): per build step, the model's own test runs and their exit codes
  inside `implement` and `test`, ShipLoop's refusals and their reasons, the Until Loop receipt's iteration count,
  and the product-code lines changed during `test`, during `document` and by the step review, from the trees
  ShipLoop snapshots (`lint/<action>.*.md`, `improve/<action>-bind.md`, the step commit).
- **Turn census** (`turn_census.py`): each tool call is charged the seconds from the end of the call before it to
  its own end, and classed by what it touches (the Until Loop runtime, a ShipLoop callback, a packet fetch, run
  records, the skill's guides, review notes, the knowledge home, the product's tests, the product).
- **Snapshot acceptance** (`snapshot_acceptance.py`): for the 92 finished runs whose case has held-out acceptance,
  each snapshot (the last step's base, `implement` accepted, `test` accepted, before the step review, the step
  commit, before the end-of-work review, delivered) is exported and graded by the harness's own
  `quality.acceptance`. Exploratory: no reading was registered before the data.
- **Outside evidence**: three Claude Opus 5.5 research agents (published measurements, open-source harness
  designs, practitioner and vendor reports); their reports are in `research/` with the briefs they were given.

Live, registered below before any counted slice ran: step slices of the inner loop on the owner's three drivers.

### Registered design: inner-loop slices on the target drivers (written and committed before any counted slice ran)

**Apparatus.** `test/shiploop_e2e/slice.py`: one work item run from `step-plan` to the end of `carry-forward` on a
fixture repository, the stages before `step-plan` recorded without doing them, inline delegation, this checkout's
build of ShipLoop 2.3.0, no overlay. Outputs under `/Users/dadleet/e2e-runs-sdlc4/20261120/`.

**Cases** (`step_cases.json`).

- `tickets-assign`: one endpoint added to an existing help-desk service of about 1,700 source lines (a brownfield
  change of one step).
- `shared-expenses-w1`: a small service built from an empty repository whose rules must be exact (equal and exact
  splits with left-over cents, balances, greedy settlements with ties, restart, concurrent writes); earlier runs
  split it into 3 or 4 steps.

**Drivers.** Codex `gpt-6.2-sol` at medium; Claude `claude-sonnet-5-5` at high; Grok `grok-4.6` at xhigh; and, as
the reference the E2E default uses, Codex `gpt-6.2-sol` at xhigh. One slice per driver and case first, a second
where time allows. Grok runs `tickets-assign` only: a background task here is ended at about two hours and a slice
cannot be resumed, so its slice is given 105 minutes.

**Yardstick the model never sees.**

- `tickets-assign`: 14 of the 18 held-out checks of the full `ticket-assignment` case
  (`checks/ticket_assignment_accept`): the six "unchanged" checks (`ticket-lifecycle-unchanged`,
  `listing-unchanged`, `notifications-unchanged`, `restart-keeps-state`, `cli-raw-columns`, `old-data-loads`) and
  the eight that the slice's request asks for (`assign-and-unassign`, `assignee-validation`,
  `assign-state-and-missing`, `assign-same-agent-noop`, `assign-audited`, `assignee-notified`,
  `assignee-persists`, `old-tickets-unassigned`). The other four test the listing filter and the command line,
  which the one-step request leaves out; they are expected to fail everywhere and are reported, not scored. If
  one of the 14 fails on every slice for a reason tied to the missing filter, it is reported apart, not rescored.
- `shared-expenses-w1`: the six checks of the full `shared-expenses` case (`checks/expense_service.py`: unit,
  contract, split, settle, restart, concurrency). The slice's own check is only `node --check server.js`.

**Measures**, each per slice.

- M1: minutes for the slice and per stage, with reviews apart.
- M2: share of the model's time by kind of command (turn census).
- M3: iterations of each stage's Until Loop (the receipt's `action_number`).
- M4: the model's own failing test runs inside `test`, and product-code lines changed during `test`, during
  `document` and by the step review.
- M5: refusals of the `test` result and their reasons.
- M6: hidden checks passing at each snapshot: `implement` accepted, `test` accepted, before the step review, the
  step commit, the end of the slice.

**Readings**, stated before the data.

- *The first implementation is what iterates* on a driver if its `implement` snapshot of the last step fails a
  hidden check in at least half of that driver's slices and a later stage of the same slice makes it pass. Then
  giving the implementer executable tests first is worth a registered comparison. If every `implement` snapshot
  passes every hidden check, the first implementation is not where these runs lose time.
- *Ceremony is the cost* on a driver if the Until Loop runtime, callbacks, packet fetches, run records, guides
  and review notes together take at least half of the model's time.
- *The stage Until Loop does not iterate* on these drivers if at least 90% of stage loops end on their first
  iteration.

**Limits known before the run.** One or two slices per cell, two small cases, a seeded start (the spec is the
request and no planning stage ran), and slices that run at the same time may meet on a network port. The hidden
`tickets-assign` checks were written for the larger request.

**Budget and failures.** At most $20 for a Claude slice, about $90 in all. A slice that ends without its
`carry-forward` accepted is reported as it ended and run once more.

**Not in this registration.** A slice with the stage Until Loop switched off in a build copy (an overlay) was
considered; it would be registered by itself after the records are read.

### Registered addition: arm L0, the stage Until Loop switched off (written after its rehearsal, before any counted L0 slice)

**Why.** The records say the stage loop never repeats (R24) and that its commands take a visible share of the
model's time (R25). But the turn census cannot price it: a stage's first command is the loop's `start`, so the
time the model spends reading the packet and deciding the stage's work is charged to it. On the first counted
slice (Sol 6.2 medium, `tickets-assign`) `start` alone is 46% of the model's time and `done` 1.6%. Only a run
without the loop says what it costs.

**The arm** (`overlays/l0-no-stage-loop.json`: seven edits applied to a build copy by `slice.py --overlay`, never
to the checkout). Every inner stage's packet still prints the stage's Work, Exit and Repeat conditions, the loop
contract's own words. No loop command is started, no receipt is written, `complete` asks for none, and a
result's `evidence_refs` lists none. ShipLoop's gates at `check` and `complete` are unchanged, and so is the
Improve review's own loop.

**Rehearsal** (one L0 slice, Sol 6.2 medium, `tickets-assign`, not counted). Every slice verdict passed, with
no stage receipt, in 10.2 minutes beside 9.5 for the baseline slice. `check` was refused five times beside two;
the three extra were record rules (a mock's fields, the `learned` list, a spec line), and both slices met the
same first refusal (a Proof naming a test file not yet written) and the same two surviving seeded faults (the
name limit 64 changed to 65, and 200 to 201).

**Runs.** Codex `gpt-6.2-sol` at medium, both cases, two slices per arm and case: the registered baseline slice
plus one more, and two L0 slices, with the arms alternating inside each lane. Claude Sonnet 5.5 at high: one L0
slice per case beside its registered baseline slice. No Grok.

**Readings.** Two slices a cell read only large effects.

- *L0 completes* if every L0 slice has its `carry-forward` accepted.
- *Time*: L0 saves time on a driver and case if its slices' mean minutes are at least 15% below the baseline's;
  within 15% either way no difference is readable.
- *Quality*: no loss is seen if every L0 slice passes at least as many hidden checks at its end as the baseline
  slices of its case pass at the least. Refusals of `check` and `complete` are reported without a bar: with no
  loop report, `check` is the model's only exit test, so more calls of it are expected.

**Limits known before the run.** A slice is ten minutes to an hour of one item: it cannot show drift over long
work or a cleared context, which is what the loop is for. The overlay's wording is one of several possible. Lanes
that run at once share the provider's capacity, so minutes are compared only between arms that alternate in a
lane.

### Results from the records (273 finished runs; 96% Codex gpt-6.1-terra)

**R22. The step's own tests rarely fail, and the test stage rarely changes the product**
(`evidence/iteration-census.txt`; 460 build steps, 448 with a test stage, 451 with every snapshot).

| Place the first implementation could be found wanting | How often |
|---|---|
| The model's own Proof or test run fails inside `implement` | under 1% of steps |
| ShipLoop refuses the `implement` result | 1% of steps |
| One of the model's own test runs fails inside `test` | 5% of steps (terra xhigh 5%, terra high 3%, Grok 4.6 4 of 29, Sol 6.1 medium 0 of 8) |
| Product code changes during `test` | 6% of steps (a median 21 lines where it does) |
| Product code changes during `document` | 5% of steps (a median 2 lines) |
| The step review changes product code | 23% of steps (a median 5 lines; round 1 found 22%) |

The model runs its tests a median twice in the `test` stage, the first time 16 seconds in. Per step the median
times are `implement` 34 s, `test` 55 s, `document` 27 s and the step review 31 s.

**R23. What the test stage does iterate on is the tests.** ShipLoop refused the `test` result in 43% of steps
(0.52 refusals a step). By the refused command's own output: 203 refusals because a seeded fault survived the
step's tests, 35 because a new test already passed on the old code, 11 because a recorded command failed, 11 for
a record rule. From the first refusal to acceptance is 25% of all test-stage seconds (a median 36 s where
refused), 9 to 14% of a step's build time on terra. At the 202 refusals that give a count, 447 of 1,453 sampled
faults had survived (a median 2 of 8). In the accepted results 1,932 sampled faults are caught and 97 are left
uncaught with a written reason, in 10% of steps; 72 of the 97 are a changed number constant.

**R24. The stage Until Loop does not repeat.** Of 2,433 stage loops with a receipt (`implement` 507, `test` 460,
`document` 428, `test-spec` 377, `step-plan` 377, `carry-forward` 282, `validate-existing` 2), 2,432 ended on
their first iteration; one `step-plan` loop took two. The Improve review's own loop is a different loop and does
repeat (its passes); it is not counted here.

**R25. Where the model's time goes, by kind of command** (`evidence/turn-census.txt`). Only runs whose stream
lists file edits are unbiased (41 terra runs, 3 Sol 6.1 medium, 4 Grok 4.6): in the others the time spent
writing a file is charged to the next visible command.

| Driver (runs) | Until Loop commands | ShipLoop callbacks | Packet fetches | Run records | Guides | Review notes | Knowledge home | Tests | Product |
|---|---|---|---|---|---|---|---|---|---|
| Codex terra xhigh (25) | 13% | 48% | 6% | 6% | 3% | 2% | 1% | 7% | 16% |
| Codex terra high (16) | 16% | 49% | 6% | 4% | 2% | 1% | 0% | 6% | 14% |
| Codex Sol 6.1 medium (3) | 20% | 6% | 4% | 26% | 4% | 13% | 4% | 11% | 11% |
| Grok 4.6 xhigh (4) | 6% | 4% | 2% | 18% | 8% | 5% | 9% | 4% | 44% |

On Codex terra a callback command usually also writes the result file it submits, so "callbacks" there holds
the result writing that shows as "run records" on the other two. Reading and running the product and its tests
is 20 to 23% of the model's time on Codex and 48% on Grok. Of the Until Loop commands, the `done` report is 7.4
to 9.2% of the model's time on terra, 6.5 to 8.0% on Sol medium and 2.3% on Grok; `start` is 4.4 to 5.0% on
terra, 11.6 to 18.5% on Sol medium and 1.6% on Grok, and includes reading the packet that says to start it.

**R26. The first complete implementation already passes every hidden check** (`snapshot_acceptance.py`,
`evidence/snapshot-acceptance.txt`, `.json`; exploratory). 84 of the 92 runs with held-out acceptance could be
graded at every snapshot (the other 8 are two cases whose acceptance block is no longer in `cases.json`). All 84
are terra (high 53, xhigh 31), on 12 cases with 6 to 23 checks each.

| Snapshot | Runs passing every hidden check | Checks passed |
|---|---|---|
| The last step's base | 5 of 83 | 800 of 1,261 (63%) |
| `implement` accepted | 83 of 84 | 1,266 of 1,267 |
| `test` accepted | 83 of 84 | 1,266 of 1,267 |
| Before the step review | 83 of 84 | 1,266 of 1,267 |
| The step commit, after the review | 83 of 84 | 1,266 of 1,267 |
| Before the end-of-work review | 84 of 84 | 1,267 of 1,267 |
| Delivered | 84 of 84 | 1,267 of 1,267 |

The one exception is a four-step run whose last step left no `implement` snapshot, so its third step was graded,
before the command-line change the fourth step made. No hidden check that passed at `implement` failed at a
later snapshot. So in these runs the `test` stage, the `document` stage, the step review, the end-of-work review,
the system tests and product acceptance changed no hidden verdict.

**R27. Outside evidence** (`research/`; the agents' readings, not checked again).

- Executable tests that the coder can see before writing raise first-attempt correctness on single-function
  benchmarks (9 to 13 points for GPT-4, 13 to 30 for a 70B model) and the ceiling is the tests' own quality; no
  study measures prose test cases written first, which is what `test-spec` produces. Agent-run test-first on
  real work measured no quality gain at 3 to 8.5 times the tokens in two practitioner studies, one of them on
  GPT-5.6 Sol at medium and xhigh with hidden tests.
- Repair is front-loaded: the first one or two rounds give 76 to 95% of the gain, logic failures repair at about
  45%, and a fresh start after two failed rounds helped small models by 4 to 10 points and strong ones not at all.
- Tests written in the same conversation as the code were far less accurate than tests written apart from it
  (52 to 61% against 88 to 90% in one study), which matches R23.
- Harnesses that publish their history removed per-task reviewers and plan-review loops for speed and kept one
  final review; one vendor dropped per-sprint evaluation for a stronger model and kept the planner and one final
  evaluator; several add a light path for small work.
- Vendors agree on a script-checkable signal to end a loop, a separate fresh evaluator, context resets instead
  of repeated correction, and removing scaffolding as models improve.

### Results from the live slices (run 2026-11-20 after d2a1466783f069ff4455ee0c2c2abe5cd10a36e5; arm L0 after c8f638b66c7209369c22b3520949135f416fbab8)

**R28. The runs** (`evidence/slices.txt`). 16 slices: 9 baseline, 6 of arm L0 and the L0 rehearsal. Every one
completed its inner loop by the harness's own verdict. Codex and Claude ran on subscriptions and report no dollar
figure; the Grok slice reports $10.57. No slice was rerun.

| Driver | Case | Minutes | Steps |
|---|---|---|---|
| Sol 6.2 medium | `tickets-assign` | 6.6, 10.7 | 2, 3 |
| Sol 6.2 medium | `shared-expenses-w1` | 11.3, 9.9 | 3, 3 |
| Sonnet 5.5 high | `tickets-assign` | 17.3 | 3 |
| Sonnet 5.5 high | `shared-expenses-w1` | 23.8 | 4 |
| Sol 6.2 xhigh (reference) | `tickets-assign` | 15.1 | 3 |
| Sol 6.2 xhigh (reference) | `shared-expenses-w1` | 15.8 | 3 |
| Grok 4.6 xhigh | `tickets-assign` | 99.2 | 3 |

**R29. Hidden checks (M6).** Two of the 14 registered `tickets-assign` checks (`assignee-persists`,
`old-tickets-unassigned`) fail at the end of every slice through the listing filter the one-step request leaves
out; by the registered rule they are reported apart and 12 are scored. In all 9 baseline slices and all 6 L0
slices the last step's `implement` snapshot passes every scored check (12 of 12 or 6 of 6), and so does the end
of the slice (`evidence/slices-snapshots.txt`). Earlier steps pass fewer because the feature is not built yet,
not because a built part is wrong. One snapshot dips: a Sonnet step commit in arm L0 failed the `unit` check,
which reruns the product's own tests, and passed again at the next step; it was not investigated.

**R30. Inside the stages (M3, M4, M5)** (`evidence/slices-iteration.txt`; 49 steps, both arms). The model's own
test runs never failed inside `test`: 0 of 47 steps. Product code changed during `test` in 11% of steps (a median
5 lines). The step review changed product code in 3 of 6 Sonnet steps and in none of 20 on Sol 6.2 or Grok
(baseline slices). ShipLoop refused the `test` result in 38% of steps; all 20 refusals that state a reason are
seeded faults that survived (39 of 139 sampled, a median 2 of 8), 8 of the 11 left uncaught at acceptance being
number constants. All 109 stage Until Loops with a receipt ended on their first iteration.

**R31. Where the inner loop's time goes (M1), baseline slices.**

| Driver | step-plan | its review | test-spec | implement | test | document | step review | carry-forward and its review | Before the first product edit |
|---|---|---|---|---|---|---|---|---|---|
| Sol 6.2 medium (4) | 17% | 8% | 4% | 21% | 25% | 10% | 9% | 6% | 30% |
| Sonnet 5.5 high (2) | 16% | 13% | 5% | 14% | 22% | 9% | 14% | 7% | 34% |
| Sol 6.2 xhigh (2) | 16% | 14% | 3% | 15% | 25% | 12% | 8% | 6% | 34% |
| Grok 4.6 xhigh (1) | 20% | 12% | 8% | 8% | 19% | 9% | 13% | 11% | 40% |

A build step costs a median 131 seconds on Sol 6.2 medium, 191 on Sonnet, 194 on Sol 6.2 xhigh and 971 on Grok,
of which 91, 152, 145 and 838 come after `implement` is accepted (`test`, `document`, the step review). Every
driver planned the one-endpoint case as 2 or 3 steps.

**R32. The model's time by kind of command (M2)** (`evidence/slices-turns.txt`). Baseline slices whose stream
lists edits: Sol 6.2 medium (3) loop 37%, callbacks 10%, packets 2%, records 12%, guides 6%, review notes 8%,
tests 6%, product 17%; Sonnet (2) loop 24%, callbacks 35%, packets 7%, records 4%, tests 15%, product 13%; Grok
(1) loop 10%, callbacks 4%, packets 2%, records 15%, guides 16%, review notes 4%, tests 6%, product 40%. In arm
L0 the loop column falls to 1% on Sol 6.2 medium and product and tests rise from 23% to 55%, while the slices
take as long or longer (R33): the time charged to the loop's `start` is the model's thinking about the stage,
which it does either way.

**R33. Arm L0, the stage Until Loop switched off.**

| Driver and case | Baseline minutes | L0 minutes | Change | Hidden checks at the end | Refusals, baseline / L0 |
|---|---|---|---|---|---|
| Sol 6.2 medium, `tickets-assign` | 6.6, 10.7 | 8.7, 8.7 | 0% | 12, 12 / 12, 12 | 2, 4 / 2, 7 |
| Sol 6.2 medium, `shared-expenses-w1` | 11.3, 9.9 | 13.4, 13.1 | +25% | 6, 6 / 6, 6 | 6, 3 / 4, 2 |
| Sonnet 5.5 high, `tickets-assign` | 17.3 | 23.5 | +36% | 12 / 12 | 5 / 8 |
| Sonnet 5.5 high, `shared-expenses-w1` | 23.8 | 34.0 | +43% | 6 / 6 | 5 / 6 |

### Registered readings

- **The first implementation is not what iterates.** On every driver the last step's `implement` snapshot passes
  every scored hidden check, so no later stage had a hidden failure to fix. The registered consequence: the
  first implementation is not where these runs lose time, and a tests-first comparison is not called for by this
  data.
- **Ceremony is the cost, by the registered sum, but the sum overstates it.** Loop, callbacks, packet fetches,
  records, guides and review notes are 75% of the model's time on Sol 6.2 medium, 72% on Sonnet and 51% on Grok.
  R32 shows the loop column is mostly thinking charged to the stage's first command. Without it the sum is 38%,
  48% and 41%.
- **The stage Until Loop does not iterate** on these drivers: 109 of 109 loops ended on their first iteration.
- **L0 completes** (6 of 6). **No time saving is seen**: no cell is 15% faster, one is level and three are 25 to
  43% slower (the two Sonnet cells are one slice each). **No quality loss is seen** in hidden checks.

### Findings

- **F18 (firm on Codex terra, consistent on four drivers in 15 slices).** The first complete implementation is
  already right by checks the model never saw (R26, R29). The loop the owner describes, moderately correct code
  that real tests then correct, is not what a ShipLoop step does: the step's own tests fail in 5% of recorded
  steps and in none of 47 slice steps, and product code changes during `test` in 6 to 11% of steps.
- **F19 (firm).** What the `test` stage repeats is the strength of its tests. About four steps in ten are
  refused once because a seeded fault survives, usually two of eight, mostly a number in the code that no test
  pins (R23, R30). The step criteria state the limit; the test cases written from them do not test both sides
  of it. This is the test-side face of F14.
- **F20 (firm that it does not repeat; interim, small sample, that removing it saves nothing).** The stage
  Until Loop took a second iteration once in 2,542 loops, and switching it off made no slice faster (R33). It
  is neither where the time goes nor a loop that loops: what a stage gets from it is its list of exit
  conditions, and the enforced exit is ShipLoop's own `check`.
- **F21 (firm for these slices).** `implement` is 8 to 21% of the inner loop on the owner's drivers. 30 to 40%
  passes before the first product edit (the step plan, its review, the test spec), 19 to 25% in `test`, 9 to 12%
  in `document`, and 20 to 31% in the three reviews.
- **F22 (interim).** Step count multiplies the fixed cost. Each step pays `test`, `document`, a review and a
  commit: 1.5 minutes on Sol 6.2 medium, 2.5 on Sonnet, 14 on Grok, before any of it depends on the step's size.
  Every driver cut a one-endpoint change into 2 or 3 steps, and the hidden checks show nothing the cut bought:
  the intermediate steps are unfinished, not wrong, and the last step's first implementation passes everything.
- **F23 (firm for 84 recorded runs and 15 slices).** No stage after `implement` changed a hidden verdict. What
  those stages add is tests that guard later changes, documents, and hardening beyond the request (F14); they do
  not make this request's behaviour right, because it already is.
- **F24 (firm).** The driver matters more than any stage: the same slice took 7 to 11 minutes on Sol 6.2 medium,
  17 on Sonnet 5.5 high, 15 on Sol 6.2 xhigh and 99 on Grok 4.6 xhigh, with the same hidden result.
- **F25 (outside evidence, R27).** It agrees where it can be compared: repair returns are front-loaded, tests
  written beside the code are weak, per-step reviews are what other harnesses cut first, and agent-run
  tests-first measured no gain in the two studies on real work.

### Recommendation (owner's decisions; nothing built)

What to leave alone:

1. **Do not move test writing before the code.** The first implementation already passes (F18), an executable
   target already exists before the code (the step's Proof), and the outside measurements on real work found no
   gain (R27).
2. **Do not spend effort on the stage Until Loop.** It does not repeat, and removing it saved nothing (F20). By
   the owner's rule of changing only for a material difference it stays as it is.

What to optimize, largest measured share first, each needing its own registered comparison before any default:

3. **The number of steps per item (F22).** A step plan that keeps a small item to one step unless a criterion
   cannot be proved without an earlier one would remove one or two rounds of `test`, `document`, review and
   commit from slices like these: about a quarter to a third of their build time. Risk to measure: a larger step
   whose first implementation is no longer right.
4. **Review placement on these drivers (F21, F23).** The three reviews are 20 to 31% of the inner loop and
   changed no hidden verdict. Round 1 found the step-plan review the one whose edits are substantive; the step
   review's product edits are hardening beyond the request. Reviewing the build once, at the end of the item,
   instead of at every step is the trade-off to price: it is a product decision, and rounds 1 and 3 left the
   owner's answer on review defaults open.
5. **Boundary cases in the test spec (F19).** For every number a criterion states, a case on each side of it,
   checked by a script at `test-spec`. That is aimed at the commonest refusal in the loop (seeded faults on
   number constants) and at the limits that later reviews argue about (F14). It moves a refusal after the fact
   to a requirement before it.
6. **The driver (F24).** For speed, Sol 6.2 medium and Sonnet 5.5 high are the drivers these slices support.
   Grok 4.6 at xhigh took ten times as long for the same result, 40 minutes of it before any product edit.

Not shown to be reducible, so not recommended: the packets' and records' weight. It is a large share of the
model's time (R25, R32), but nothing here separates the part that carries the run across a cleared context from
the part that does not.

### Limits

- The hidden checks are at their ceiling on these cases for every driver. They show that the first
  implementation is right here; they cannot show what happens on a request hard enough for a first
  implementation to be wrong. `node-chess-engine` is the step case to try for that.
- One or two slices a cell, two small cases, a seeded start with no planning stages, and up to six slices at
  once on one machine and shared provider capacity. Minutes differ by 60% between two baseline slices of one
  cell (6.6 and 10.7), mostly through the number of steps.
- Arm L0 is short work in one context. It says the loop is not a time cost; it cannot say what the loop does
  for long work or after a cleared context.
- The turn census charges thinking to the next command, so its loop and callback columns are upper bounds.
- The `tickets-assign` yardstick is 12 of the full case's 18 checks.
- Three recommendations (3, 4, 5) are designs read off measurements, not tested arms.

### Queued by the owner (2026-11-20, after the results): do progressive learnings pay?

The owner's words: "Also identify if there are progressive learnings shiploop should track in any way to benefit
implementations as it iterates that could be included to aide the overall runs, or if that is a waste with no
materially added value." Status: taken up the same day at the owner's word; see round 5. Consumer: the owner's
decision whether ShipLoop should track more, less or the same.

What frames it. Round 4 found the first implementation already right by hidden checks, so on requests like
these a tracked learning can pay only through speed (a refusal not met twice, a fact not rediscovered) or
through hardening, not by making the behaviour right. ShipLoop already writes learnings in at least four
places: a `learned` list in stage results, `learned_from` with the packet's look-back at earlier commits, the
knowledge home `docs/shiploop/`, and the carry-forward skill decision. So the first question is whether those
are read back and change anything, before any new one is proposed.

How it would be answered, cheapest first: from the recorded runs, how often `learned` holds more than "none",
how often `learned_from` names a commit, and whether a refusal reason met at one step is met again at a later
step of the same run; then the follow-on cases (a second feature in an earlier run's checkout), which are where a
first run's record can help a second. A live comparison would be registered only if those leave it open. A
research plan is being prepared outside the repository (the owner's todo queue, task `1795195223742-52ff23db`).

## Round 5 (2026-11-20): do progressive learnings pay, or are they paperwork?

### Question

The owner's words are in round 4's last block. Consumer: the owner's decision whether ShipLoop should track more,
less or the same as it iterates. Round 4 frames it: the first implementation is already right by hidden checks,
so on requests like these a tracked learning can pay only through speed (a refusal not met twice, a fact not
found twice) or through hardening.

### What ShipLoop already records (read in `skills/shiploop/scripts/`)

| Channel | Written | Read back | Reach |
|---|---|---|---|
| `learned` and `decisions` lines (`STEP_NOTES`), required of every `implement` result | into the step commit as its key learnings and decisions | by `look_back_lines`: the `implement` packet quotes the last `LOOK_BACK_COMMITS` (2) step commits, one line each; no other stage's packet does | later steps of the run |
| `learned_from`, optional | the commits a step says it used | the step commit's related commits | a citation |
| the knowledge home `docs/shiploop/` (`KNOWLEDGE_RECORD`: spec, architecture, environment) | at the planning stages, `document` and `carry-forward` | by every later stage, and by the next run in that repository | steps, items and runs |
| release-verify lessons (`LESSON_FIELDS`) | the body of the run's knowledge commit | quoted as "Inherited learnings" at the next run's `intake` and `discovery` (`lessons_lines`) | the next run |
| the carry-forward skill decision (`_SKILL_DECISIONS`: none, reuse, update, create) | a skill file in the repository | whoever loads that skill | later items and runs |
| an Improve review's key learnings (`shiploop_lessons.LESSON_LABELS`) | the review's commit | the next review packet | later review passes |

Refusal reasons are carried into no later packet. `test/shiploop_e2e/LEARNINGS.md` and `learning-records.jsonl`
are for the people developing ShipLoop, not for a product run.

### Method

Offline first (`learning_census.py`, no model): on round 1's 273 finished runs (460 build steps) and round 4's 16
slices, how often each field is filled and cited; whether steps that cite an earlier learning are refused less or
are faster than steps that were shown one and did not cite it, pooled and within the same case and model (a
Mantel-Haenszel difference); whether the seeded-fault refusal fades as an item's steps go on; and how many
refusals repeat a refusal of the same class met earlier in the run at another action, classed by ShipLoop's own
refusal text, with the seconds they cost. A background agent's research plan (the owner's todo queue, task
`1795195223742-52ff23db`) proposed these measures; its own counts are not used here. Then two independent Claude
Opus 5.5 judges label a fixed-seed sample of 160 recorded `learned` lines (`judge-learned/`, brief in
`evidence/learned-judge-brief.txt`): forward (a fact a later step or change could act on that the request does
not already say), restates (what this step did), process (about the harness), unclear. Then one live arm,
registered below.

### Results from the records

**R34. The fields are filled because they are required, and cited about a quarter of the time**
(`evidence/learning-census.txt`). All 460 `implement` results hold a `learned` list and 458 hold a real line: a
median of one line, 69 characters. Every `implement` packet has the look-back; it showed an earlier step's
learning in 305 (66%). `learned_from` names a commit in 84 of those 305 (28%) and in 1 of the other 155. The
carry-forward skill decision is `none` in 282 of 282 results and in all 16 slices.

**R35. Citing an earlier learning shows no benefit.** Among the 297 steps that were shown one and have a `test`
stage, `test` was refused at least once in 44% of the 80 that cited it and 45% of the 217 that did not; for the
seeded-fault refusal 42% and 41%. Within the same case and model the citing steps are refused more, by 15 and 16
points over 16 strata. Their `implement` plus `test` time is a median 121 seconds against 84, and 1.05 times the
other within case and model. On the slices (33 such steps) the differences have the other sign and two strata.

**R36. The one refusal that repeats does not fade from the first step to the second.** In the 71 recorded items
of two or more steps, `test` was refused for a seeded fault at step 1 in 56%, at step 2 in 56%, at step 3 in 44%
and at step 4 or later in 15%. After a refused step the next is refused in 56%, after a step that was not in 26%;
within case and model the gap is 16 points over 10 strata. On the slices' 16 items it is 56%, 31% and 20% by
step, and a refused step is followed by fewer refusals, not more (15% against 33%, 31 pairs).

**R37. Repeated refusals are a small cost.** Of 591 refused `check` or `complete` commands with a text, 63 (11%)
repeat a class met earlier in the same run at another action, and 60 of the 63 are the seeded-fault refusal.
From a refusal to the next accepted check of its action is 4.1% of run time for all refusals and 0.8% for the
repeats. On the slices: 2 of 49, 6.6% and 0.3%.

**R38. Runs that inherit a knowledge home are not quicker to start** (Codex terra, from round 1's census; one to
21 runs a case, different features, so only a direction). Seconds before `step-plan`, medians: `ticket-assignment`
162, then its follow-ons `ticket-escalation` 171, `ticket-comments` 196, `ticket-sla` 260; `user-listing` 153,
then `user-roles` 224, `user-team-listing` 204, `user-page-size` 325. Discovery and research alone are 27 to 31
seconds in the first runs and 26 to 45 in the follow-ons. No recorded run withholds the home, so what the home is
worth to a follow-on's correctness is not measured by any record.

### Registered design: arm K0, the look-back switched off (written and committed before any counted K0 slice ran)

**Why.** R35 is a correlation: a model chooses when to cite. An arm that removes the look-back prices it, as arm
L0 priced the Until Loop.

**The arm** (`overlays/k0-no-look-back.json`, one edit applied to a build copy by `slice.py --overlay`): the
`implement` packet no longer shows the last two step commits with their key learnings. The `learned`, `decisions`
and optional `learned_from` fields, the step commits that carry them, the knowledge home and every gate are
unchanged.

**Runs.** Round 4's two cases. Codex `gpt-6.2-sol` at medium: two K0 slices and one new baseline slice per case,
the arms alternating inside each lane; round 4's two baseline slices per case are reported beside them, not
pooled into the time comparison. Claude Sonnet 5.5 at high: one K0 slice per case beside round 4's baseline
slice. Yardstick and measures as in round 4.

**Readings.** One to three slices a cell read only large effects.

- *The look-back pays* on a driver and case if every K0 slice passes fewer hidden checks at its end than the
  least of its baseline slices, or K0's mean minutes are at least 15% above the baseline's in both cases of a
  driver with refusals at least as many.
- *The look-back is not what these slices run on* if every K0 slice completes, passes as many hidden checks at
  its end as the least baseline slice of its case, and K0's mean minutes are within 15% of, or below, the
  baseline's in at least three of the four cells.
- Otherwise no reading.

**Limits known before the run.** Two or three steps an item: the look-back has one or two earlier steps to show.
It cannot show what a learning is worth across many steps, a cleared context, or a later run. The knowledge home
stays, so this prices the look-back alone.

## Evidence (all rounds)

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
| `evidence/overlap-ceiling.txt` | stage reads and edit classes, neighbouring stages that could overlap, step-overlap ceiling by host (R12, R13) |
| `evidence/write-set-fidelity.txt`, `evidence/shared-files.txt` | declared against committed files per step; files every step of an item writes (R14) |
| `evidence/task-sizes.txt` | seconds per read-mostly piece by host (R15) |
| `judge/diffs-1.txt`, `judge/diffs-2.txt`, `judge/diff-key.json` | the 136 diffs as the judges saw them, and which run each came from |
| `judge/out-A-*.jsonl`, `judge/out-B-*.jsonl` | each judge's verdict and reason per diff |
| `evidence/replay-cases.txt`, `judge-replay/cases.json` | round 3: how the 18 cases were chosen, and which run each is |
| `evidence/replay-briefs.txt`, `evidence/replay-judge-brief.txt` | round 3: the plain and lens briefs, and the judges' brief |
| `judge-replay/packet-*.txt`, `judge-replay/key.json` | round 3: each fix and the six reports as the judges saw them, and which letter was which reader |
| `judge-replay/out-A-*.jsonl`, `judge-replay/out-B-*.jsonl` | round 3: each judge's verdict and reason per report |
| `judge-replay/reviewers.json` | round 3: seconds, turns, dollars, tokens, findings and the path audit per reader |
| `evidence/replay-results.txt` | round 3: the registered measures, the per-case table, the exploratory cuts, cost (R16 to R20) |
| `evidence/replay-conduct.txt` | round 3: kills by name, shared ports and other conduct outside the shared folder (R21) |
| `evidence/iteration-census.txt` | round 4: per build step, own test runs, refusals and reasons, loop iterations, product lines changed after implement (R22 to R24) |
| `evidence/turn-census.txt` | round 4: the model's time by kind of command, and the Until Loop's start and done shares (R25) |
| `evidence/snapshot-acceptance.txt`, `.json` | round 4: held-out checks passed at each snapshot of 84 recorded runs (R26) |
| `research/*.md` | round 4: the three research agents' reports and the briefs they were given (R27) |
| `overlays/l0-no-stage-loop.json` | round 4: the seven edits of arm L0, applied to a build copy only |
| `evidence/learning-census.txt`, `evidence/learning-census-slices.txt` | round 5: learning fields filled and cited, the effect of citing, refusals by step, repeated refusals (R34 to R37) |
| `judge-learned/lines.jsonl`, `out-A.jsonl`, `out-B.jsonl`, `evidence/learned-judge-brief.txt` | round 5: the 160 sampled `learned` lines, each judge's label, and the brief |
| `overlays/k0-no-look-back.json` | round 5: the one edit of arm K0, applied to a build copy only |
| `evidence/slices.txt`, `evidence/slices-iteration.txt`, `evidence/slices-turns.txt`, `evidence/slices-snapshots.txt`, `slices/*.json` | round 4: the live slices' registered measures, per-step detail, time by kind of command, hidden checks at each snapshot, and the three files they are computed from |

To rerun: `python3 -I stage_census.py <work>/census.json` writes the run list the other scripts read
(`passes_census.py <work>/census.json <work>/samples.jsonl`, `review_edits.py <work>/census.json
<work>/review_edits.json`, `deps_census.py`, `extras_census.py`, `more_cuts.py <work>`, `build_diffs.py <work>`,
`score_judges.py judge`; round 2: `overlap_ceiling.py`, `write_set_fidelity.py`, `shared_files.py`,
`task_sizes.py`, each `<work>/census.json`). The run folders are outside the repository and may be pruned; the outputs above are the
record.

Round 4, from the recorded runs: `iteration_census.py <work>/census.json <work>/iteration.json`,
`turn_census.py <work>/census.json`, `python3.13 snapshot_acceptance.py <work>/iteration.json <work>/snap.json`
(about 25 minutes, no model), `snapshot_score.py evidence/snapshot-acceptance.json` (from the repository alone).
The slices: `test/shiploop_e2e/slice.py --case <case> --host <host> --model <model> --effort <effort> --output
<root>/<name>` (add `--overlay overlays/l0-no-stage-loop.json` for arm L0), then `stage_census.py slices/census.json
<root>`, `iteration_census.py slices/census.json slices/iteration.json --all`, `turn_census.py slices/census.json
--all`, `python3.13 slice_snapshots.py slices/iteration.json slices/snapshots.json` and `slice_report.py
slices/census.json slices/iteration.json slices/snapshots.json`.

Round 3: `python3 -I replay_score.py judge-replay` rescores from the repository alone. To run it again from the
recorded runs: `replay_cases.py <work>` (needs `<work>/census.json` and `<work>/review_edits.json`),
`replay_build.py <work>`, `replay_run.py <work>` (108 headless Claude Code sessions; about $21),
`replay_judge_packets.py <work> judge-replay 3`, two judges per packet with `evidence/replay-judge-brief.txt`,
then `replay_score.py judge-replay` and `replay_conduct.py <work>`. The reviewers' full streams (about 25 MB) stay
in the working folder and are not in the repository.
