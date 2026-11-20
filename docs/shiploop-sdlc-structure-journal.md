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

To rerun: `python3 -I stage_census.py <work>/census.json` writes the run list the other scripts read
(`passes_census.py <work>/census.json <work>/samples.jsonl`, `review_edits.py <work>/census.json
<work>/review_edits.json`, `deps_census.py`, `extras_census.py`, `more_cuts.py <work>`, `build_diffs.py <work>`,
`score_judges.py judge`; round 2: `overlap_ceiling.py`, `write_set_fidelity.py`, `shared_files.py`,
`task_sizes.py`, each `<work>/census.json`). The run folders are outside the repository and may be pruned; the outputs above are the
record.

Round 3: `python3 -I replay_score.py judge-replay` rescores from the repository alone. To run it again from the
recorded runs: `replay_cases.py <work>` (needs `<work>/census.json` and `<work>/review_edits.json`),
`replay_build.py <work>`, `replay_run.py <work>` (108 headless Claude Code sessions; about $21),
`replay_judge_packets.py <work> judge-replay 3`, two judges per packet with `evidence/replay-judge-brief.txt`,
then `replay_score.py judge-replay` and `replay_conduct.py <work>`. The reviewers' full streams (about 25 MB) stay
in the working folder and are not in the repository.
