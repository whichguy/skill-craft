# ShipLoop SDLC structure journal

Living journal for one question from the owner (2026-11-19): is ShipLoop's stage structure right, in particular the
planning sequence, how the dependency graph is made, and how the inner loop executes it, and should any of it change?

Evidence folder: `docs/experiments/sdlc-structure-20261119/` (scripts, their outputs under `evidence/`, the judges'
inputs and verdicts under `judge/`, and round 3's under `judge-replay/`). No round's own commits change `skills/`. The
changes that came out of the rounds are commits of their own: the fewest-steps wording (ShipLoop 2.4.0), three text
corrections (2.4.1), and round 15's two changes to the engine, merged from their branch on 2026-11-22.

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

### Results from the judges and the live arm (run 2026-11-20 after 1e86444f573427c3400986690a0d3082c19e4f34)

**R39. What the recorded learnings say** (`evidence/learned-judged.txt`, `judge-learned/`). The two judges gave
the same label to 97% of the 160 sampled lines (kappa 0.94). By both judges: 86 lines (54%) state a fact a later
step or change could act on, 54 (34%) restate what the step did, 14 (9%) are about the harness, 1 is unclear. A
forward fact is commoner after the first step (41 of 59 lines) than at it (45 of 101). Examples of forward
lines: "Weekly report depends on raw column positions"; "The outbox retains sent and dead events, not just
pending ones."

**R40. Arm K0, the look-back switched off** (`evidence/slices-k0.txt`, `slices-k0/`). Eight new slices, all
completed; no look-back was printed in any of K0's 16 build steps and it was printed in all 23 baseline steps.

| Driver and case | Baseline minutes | K0 minutes | Change | Hidden checks at the end | Refusals, baseline / K0 |
|---|---|---|---|---|---|
| Sol 6.2 medium, `tickets-assign` | 8.9 (round 4: 6.6, 10.7) | 8.3, 8.9 | -3% (-2% with round 4's) | 12 / 12, 12 | 5 (2, 4) / 5, 3 |
| Sol 6.2 medium, `shared-expenses-w1` | 10.6 (round 4: 11.3, 9.9) | 11.8, 11.3 | +9% (+9%) | 6 / 6, 6 | 3 (6, 3) / 3, 4 |
| Sonnet 5.5 high, `tickets-assign` | round 4: 17.3 | 22.2 | +28% | 12 / 12 | 5 / 2 |
| Sonnet 5.5 high, `shared-expenses-w1` | round 4: 23.8 | 20.4 | -14% | 6 / 6 | 5 / 3 |

In every slice of both arms the last step's `implement` snapshot passes every scored hidden check where the
snapshot exists (one K0 slice lacks it and passes at its end).

### Registered reading

**The look-back is not what these slices run on.** Every K0 slice completes and passes as many hidden checks as
its baseline, and K0's minutes are within 15% of the baseline's, or below, in three of the four cells. The
fourth, one Sonnet slice against one, is 28% slower with fewer refusals. The condition for "the look-back pays"
(hidden checks lost, or 15% slower in both cases of a driver) is not met on either driver.

### Findings

- **F26 (firm for these records and slices).** ShipLoop already records a learning at every build step and
  shows it to the next two, and nothing measurable comes of it: the field is filled because it is required
  (R34), a step that cites an earlier learning is refused no less and is no faster (R35), and removing the
  look-back changed no hidden check and no time beyond run-to-run noise (R40).
- **F27 (firm for the sample).** The notes are not empty. About half hold a real fact about the code base
  (R39). In an item of two or three steps done in one conversation the next step already has that fact in its
  context, so the look-back repeats it. Where such a fact could matter, after a cleared context or in a later
  run, the look-back does not reach: a later run sees the knowledge home and the last three commit messages.
- **F28 (firm).** A memory of refusals has almost nothing to save. Refusals that repeat an earlier one cost
  0.8% of recorded run time and 0.3% of slice time, and nearly all are the seeded-fault refusal, which round 4's
  boundary cases address at the source instead (F19).
- **F29 (firm).** The carry-forward skill decision has been `none` in every one of 306 results (282 recorded
  runs, 24 slices): a required
  answer that has never been anything else.
- **F30 (not measured).** What the knowledge home is worth to a later run. Follow-on runs are not quicker to
  start (R38), but no run withholds the home, so its worth for keeping earlier decisions is unpriced.

### Recommendation (owner's decisions; nothing built)

1. **Track nothing more as a run iterates.** No refusal memory, no lessons store, no new field for the model to
   fill. The measured ceiling is under 1% of run time (F28), the channel that already exists shows no effect
   (F26), and each new required field adds a refusal class of its own (R23 counts 11 record-rule refusals at
   `test` alone).
2. **Leave `learned` and the look-back as they are.** They cost a line of about 70 characters a step and feed
   the step commits' messages; taking the look-back out saved nothing either (R40), so by the owner's rule of
   changing only for a material difference there is no case to change it in either direction.
3. **One candidate to drop, small and the owner's call:** the carry-forward skill decision (F29).
4. **If any learning is to be priced further, price the cross-run one (F30)**, since it is the only channel
   whose worth is unknown: one follow-on case run with the earlier run's knowledge home present and with it
   withheld, graded by the follow-on's held-out checks, which include the ones that test whether earlier
   decisions were kept. That is a full-run comparison, registered first.

### Limits

- Items of two or three steps in one conversation: nothing here tests a learning across many steps, across a
  cleared context or across runs, which is where a recorded fact has the best chance to matter.
- The hidden checks are at their ceiling in both arms, so K0 could only have shown a loss or a time change.
- One to three slices a cell; the two Sonnet cells are one slice against one and point in opposite directions.
- R35 and R36 are correlations over recorded runs, 96% of them one model. R38 compares different features.
- The judges label what a line says, not whether anyone used it.

## Round 6 (2026-11-20): does an item cut into fewer steps finish sooner, and what does a larger step risk?

### Question

Owner, 2026-11-20, choosing among round 5's next steps: "Fewer-steps test". Round 4 found that each build step
pays its own `test`, `document`, review and commit round whatever its size, that every driver cut a one-endpoint
change into two or three steps, and that the hidden checks showed nothing the cut bought (F22). Its third
recommendation was to compare a step plan of fewer steps, with the risk named: a larger step whose first
implementation is no longer right. This round runs that comparison.

### What sets the step count today (read in `skills/shiploop/scripts/` and in the history)

- **The text.** The step-plan duty's sizing bullet (`DUTIES["step-plan"]`, item 4, in `shiploop_prompts.py`):
  one behaviour-level change a step, "at most 4 criteria and 3 product files", and "two separately confirmable
  behaviours or two outcomes joined with 'and' make another step". No gate counts either number:
  `_check_step_sizing` in `shiploop_navigator.py` refuses a step with no criteria or no proof, a criterion no
  step serves, and a step that only changes tests.
- **Why the bound is there** (`docs/shiploop-plan-sizing-journal.md`, experiment E-SIZE1). It was added on
  2026-10-25 (f23cdb20e977a56e0a2025d6003fd80b06c3ad39) because Grok 4.7 at medium put a whole chess engine in
  one or two steps under the earlier words "too large for one review"; a countable bound moved it to three or
  more in 6 of 8 plans against 3 of 8 (a57a93248382b48deb3e2222365679faa2b51414). The commit carried an open
  item: "the downstream cost of extra steps is unmeasured".
- **What was measured downstream** (that journal's entry 12, F43 to F46, DeepSeek flash, 3 items an arm). With
  the bound against the same ShipLoop without it, delivery tied at 12 of 12 and the median item finished sooner
  (63 against 124 minutes on the chess engine, 96 against 124 on a battleship server). The reason was not more
  steps: without the bound the plans ranged from 4 to 10 steps, with it from 5 to 6. Owner, 2026-10-28: "No,
  keep as is."
- **What was never measured.** Whether an item in three or more steps is built better than the same item in
  one. E-SIZE1's own F8: "No evidence yet that big steps produce worse results". The "three or more steps" it
  scored the engine against was a planned shape, not a measured benefit.

So this round does not reopen "bound or no bound": taking the bound out widened the plans. It asks the direction
E-SIZE1 left open: a larger countable bound with one step as the default.

### Method

1. **The records, free.** `step_size_census.py` over round 4's iteration census (273 finished runs, 460 build
   steps, 96% Codex gpt-6.1-terra) and over round 4's 16 slices: the shape of every accepted step plan, a step's
   seconds against the product-code lines it built, and runs of one case, model and effort that happen to
   differ in step count, with the hidden checks of what each delivered.
2. **A live arm** on the owner's drivers, registered below before any counted slice.

### Results from the records

**R41. What sets the step count** (`evidence/step-size-census.txt`, `evidence/step-size-census-slices.txt`).

- In the recorded runs 213 of 282 items (76%) are one step, 21 two, 29 three, 15 four and 4 more. An item has a
  median 2 criteria. No planned step holds more than 4 (0 of 435), so the bound is obeyed to the letter, and 9
  of 428 steps that list their files name more than 3 product files.
- Of the 69 items of two or more steps, the bound alone forces the cut (more than 4 criteria) in 14. The other
  55 are cut by the planner's reading of "separately confirmable behaviours".
- In round 4's slices on the owner's drivers an item has 4 to 11 criteria (a median 6: Sol 6.2 at medium writes 4 to 7,
  Sonnet 10 or 11) and 15 of 16 are three steps; there the bound alone forces two or more in 15 of 16. The
  planners that write more criteria for the same request get more steps.

**R42. A step's cost is mostly the same whatever its size.**

| Product-code lines built at `implement` | Steps | implement s | test s | document s | step review s | `test` refused | Review changed product code |
|---|---|---|---|---|---|---|---|
| 1 to 25 | 240 | 30 | 44 | 26 | 26 | 27% | 12% |
| 26 to 75 | 88 | 35 | 63 | 27 | 42 | 76% | 33% |
| 76 to 200 | 93 | 48 | 94 | 35 | 51 | 57% | 43% |
| 201 and more | 3 | 57 | 135 | 60 | 67 | 2 of 3 | 1 of 3 |

Recorded runs, medians. Within one case and model, 100 more product lines go with 16 more seconds of
`implement` and 60 more of `test`, `document` and the step review; of the mean step's 183 seconds after
`implement`, 159 do not depend on its size. In the slices the same line gives 102 of 183 seconds. A larger step
is refused at `test` more often and its review changes product code more often, so a merged step carries both
of those with it.

**R43. The same request in more or fewer steps.** 16 cells of one case, model and effort (135 runs) hold runs
that differ in step count. One more step goes with 105 more seconds of build (implement, test, document, step
review), 25 more in the plan stages, 131 more over the whole inner loop, 0.4 more `test` refusals, and 5 more
product lines: the same product, built in more rounds. Two cells:

| Case (gpt-6.1-terra high) | Steps | Runs | Build seconds (median) | Product lines (median) |
|---|---|---|---|---|
| `shared-expenses` | 1 | 16 | 218 | 124 |
| | 2 | 2 | 355 | 126 |
| | 3 | 2 | 548 | 134 |
| `ticket-assignment` | 1 | 3 | 197 | 47 |
| | 4 | 6 | 507 | 44 |

**R44. Hidden checks do not move with the step count.** The delivered product passes every held-out check in
41 of 41 graded one-step runs (603 of 603 checks) and in 50 of 50 runs of two or more steps (793 of 793). Seven
cells hold both shapes; every run in them passes. Round 4's R26 already had the first implementation passing
every check in 40 of 40 one-step runs and 43 of 44 others.

R42 to R44 are correlations: the planner chose each step count, and the model is terra, not one of the owner's
drivers. They predict what an arm should show; they do not show it.

### Registered design: arm F1, the fewest steps (written and committed before any counted F1 slice ran)

**Why.** R43 says the same request costs about two minutes more for each extra step with nothing to show for it
in the hidden checks, but on another model and by the planner's own choice. An arm that asks the planner for
the fewest steps prices it on the owner's drivers, and a larger item tests the named risk.

**The arm** (`overlays/f1-fewest-steps.json`, one edit applied to a build copy by `slice.py --overlay`, never to
the checkout). The sizing bullet of the step-plan duty becomes: "Use the fewest steps the item allows; one step
is the default. Every step pays its own test, document, review and commit round, so separately confirmable
behaviours share a step and its proof shows each of them. Size: at most 12 criteria and 6 product files a step
[...] Cut a larger item at a module or layer boundary (interface first, then each side) into the fewest steps
of that size." The fold rule and the one-step rule for a bug fix or rename are kept. The criteria, each step's
proof, every gate, the `test` stage with its seeded-fault check, and the reviews are the shipped ones. 12 and 6
are three times and twice the shipped numbers; 242 of the 282 recorded items fit inside them.

**Rehearsal** (five F1 runs stopped after `step-plan`, not counted). All five planned one step, and the step-plan
review left each at one. Sol 6.2 medium: `tickets-assign` 6 criteria and 5 product files, `shared-expenses-w1` 7
criteria, `node-chess-engine` 6 criteria. Sonnet: `tickets-assign` 10 criteria and 7 product files (one file over
the arm's number, which nothing enforces), `node-chess-engine` 11 criteria. Each plan took one refused command,
as baseline plans do. Rounds 4 and 5 planned the two small cases as two or three steps in 24 of 24 slices.

**Cases.** Round 4's two (`tickets-assign`, about 50 product lines in an existing service; `shared-expenses-w1`,
a small service from an empty repository) and one larger item for the risk: `node-chess-engine`, a chess rules
engine in one file built from an empty repository (E-SIZE1's case K2, the item the bound was written to split).

**Yardstick the model never sees.** As round 4 for the two small cases (12 scored checks; 6). For the chess
engine, ten checks through the module's public interface (`chess_hidden.js`): six published counts of move
sequences two to four moves deep from six standard positions (the item's own spec asks for the one-move counts
only), two replayed games compared as whole positions, four statuses, four illegal moves, and sorting.
Calibration: the six engines delivered in E-SIZE1's downstream round pass all ten; a wrapper that drops two
castling moves and reports stalemate as ongoing fails four.

**Runs.** The arms alternate inside each lane; up to seven slices run at once.

- Codex `gpt-6.2-sol` at medium: all three cases, two baseline and two F1 slices each.
- Claude Sonnet 5.5 at high: the two small cases, two F1 slices and one baseline slice each (F1, baseline, F1);
  the chess engine once per arm, both at the same time.
- Grok 4.6 at xhigh: one F1 slice of `tickets-assign`, read beside round 4's one baseline slice (99.2 minutes,
  three steps). Descriptive only: one against one, hours apart.

**Measures**, each per slice: steps planned; minutes, and seconds by part; hidden checks at the last step's
`implement` snapshot and at the end; `test` refusals and the seeded faults that survived; product-code lines
changed after `implement`; seconds after `implement` per step.

**Prediction from the records** (stated so the result can miss it). The saving is the steps removed times the
part of a step that does not depend on its size: about 100 seconds a step on Sol 6.2 medium and 150 on Sonnet
(round 4's slices). Three steps to one is then about 3 of 10 minutes on Sol 6.2 medium and 5 of 20 on Sonnet, a
quarter to a third.

**Readings.** A cell is one driver and case; the six Sol 6.2 and Sonnet cells are read, Grok is reported.

- *The arm takes* in a cell if its F1 slices plan at least one step fewer on average than its baseline slices.
- *Time*, as for arms L0 and K0: F1 saves time in a cell if its mean minutes are at least 15% below the
  baseline's; within 15% either way no difference is readable.
- *Quality*: no loss is seen in a cell if every F1 slice passes at least as many hidden checks at its end as the
  least of that cell's baseline slices. *The named risk shows* in a cell if an F1 slice's last `implement`
  snapshot fails a hidden check that every baseline slice's last `implement` snapshot passes.
- *Fewer steps pays on these drivers* if the arm takes and saves time in at least four of the six cells and no
  cell shows a quality loss. *It does not pay* if it saves time in at most one cell, or two or more cells show
  a quality loss. Anything else is reported cell by cell with no overall reading.
- Refusals, surviving seeded faults and the reviews' product edits are reported without a bar. R42 expects more
  of each per step in F1 and fewer steps to meet them.

**Limits known before the run.** One or two slices a cell read only large effects. A slice is one item in one
conversation with a seeded start. The wording is one of several possible, and its two numbers are not tuned.
The small cases' hidden checks are at their ceiling, so on them F1 can show a time change or a loss, not a gain;
the chess engine may be at its ceiling too, as the six calibration engines suggest. The engine's own tests
include time budgets, which seven slices at once on one machine can disturb. Nothing here says what a larger
step does to a review's findings beyond the product lines it changes.

**Budget and failures.** At most $20 for a Claude slice; the Grok slice about $10. A slice that ends without its
`carry-forward` accepted is reported as it ended and run once more if time allows.

### Results from the live slices (run 2026-11-20 after f9b110856b43ecd4d8587fcae979a473e9ed485f)

**R45. The runs** (`evidence/slices-f1.txt`). 21 counted slices, 10 baseline and 11 F1. Every one completed its
inner loop by the harness's own verdict and none was rerun. Codex and Claude ran on subscriptions and report no
dollar figure; the Grok slice reports $6.78 (round 4's baseline slice, $10.57).

**R46. The arm takes, and the baseline's own step count is not stable.**

| Driver | Case | Baseline: steps planned | F1: steps planned |
|---|---|---|---|
| Sol 6.2 medium | `tickets-assign` | 3, 3 | 1, 1 |
| Sol 6.2 medium | `shared-expenses-w1` | 1, 3 | 1, 1 |
| Sol 6.2 medium | `node-chess-engine` | 1, 1 | 1, 1 |
| Sonnet 5.5 high | `tickets-assign` | 4 | 1, 1 |
| Sonnet 5.5 high | `shared-expenses-w1` | 3 | 1, 1 |
| Sonnet 5.5 high | `node-chess-engine` | 2 | 1 |
| Grok 4.6 xhigh | `tickets-assign` | 3 (round 4) | 1 |

All 11 F1 slices planned one step (16 of 16 with the rehearsal). Three of the six Sol 6.2 baseline slices also
planned one step, each by writing exactly 4 criteria, the shipped bound's number; rounds 4 and 5 never saw that
in 6 Sol 6.2 medium baseline slices, which wrote 4 to 7 criteria in two or three steps. Under the shipped text
the same driver cuts the same item into one step or three from run to run.

**R47. Time.**

| Driver | Case | Baseline minutes | F1 minutes | Change |
|---|---|---|---|---|
| Sol 6.2 medium | `tickets-assign` | 8.4, 9.4 | 10.1, 8.4 | +4% |
| Sol 6.2 medium | `shared-expenses-w1` | 6.7 (one step), 13.0 (three) | 8.2, 8.6 | −15% |
| Sol 6.2 medium | `node-chess-engine` | 10.4, 7.7 | 10.6, 7.4 | 0% |
| Sonnet 5.5 high | `tickets-assign` | 19.6 | 14.7, 17.0 | −19% |
| Sonnet 5.5 high | `shared-expenses-w1` | 29.7 | 19.3, 14.0 | −44% |
| Sonnet 5.5 high | `node-chess-engine` | 16.4 | 10.8 | −34% |
| Grok 4.6 xhigh | `tickets-assign` | 99.2 (round 4) | 69.8 | −30% |

The Sol 6.2 expenses cell is −15.2% unrounded, and its baseline is one slice of each shape.

**R48. Hidden checks (`evidence/slices-f1-snapshots.txt`).** At the end of the slice every F1 slice passes what
its baseline passes: 12 of 12 scored ticket checks, 6 of 6 expense checks, 10 of 10 chess checks. At the last
step's `implement` snapshot:

- `tickets-assign`: 12 of 12 in all 9 slices.
- `node-chess-engine`: 10 of 10 in all 6, five of them a whole engine of 318 to 404 lines written as one step.
- `shared-expenses-w1`: 6 of 6 in the two baseline slices of three steps, and 5 of 6 in all five one-step
  slices (one baseline, four F1). The sixth is `unit`, which reruns the product's own tests and requires at
  least one; a one-step item has none until its `test` stage writes them, and `unit` passes from the `test`
  snapshot on. The five checks of behaviour pass at `implement` in every slice.

**R49. Refusals, send-backs and what the reviews changed.**

- `test` refused, per slice: Sonnet baseline 3, 3, 1 against F1 1, 0, 0, 0, 0; Sol 6.2 baseline 2, 1, 0, 2, 1,
  0 against F1 1, 1, 1, 0, 1, 0; Grok 1 against 1.
- Seconds after `implement` per step rise in the larger step, as R42 expects (Sonnet: 128 to 198 on the engine,
  273 to 383 and 305 on expenses; Grok 813 to 1,406), and there is one such step instead of three or four.
- Product-code lines changed after `implement`, baseline against F1: Sonnet 12 against 6 and 2 (tickets), 30
  against 2 and 27 (expenses), 5 against 0 (engine); Sol 6.2 5 and 5 against 23 and 0 (tickets), none on the
  other two cases but 4 in one F1 engine; Grok 9 against 2.
- Send-backs: 2 of 11 F1 slices and 3 of 10 baseline slices. All five are a command in the step plan that
  ShipLoop could not run or read (a proof ordered before its tests, a search recorded as a test suite, a command
  that prints nothing when it fails). None is a wrong product.

**R50. Pooled by the steps planned (exploratory, `evidence/steps-pooled.txt`).** Because the baseline chose one
step by itself in three slices, the arm comparison has cells with little or no contrast. Pooling the 32 baseline
and F1 slices of rounds 4 to 6 by the steps their plan held, whichever arm planned it:

| Driver | Case | One step: minutes (slices) | Two or more: minutes (slices) | Change |
|---|---|---|---|---|
| Sol 6.2 medium | `tickets-assign` | 9.2 (2) | 8.8 (5) | +5% |
| Sol 6.2 medium | `shared-expenses-w1` | 7.8 (3) | 11.2 (4) | −30% |
| Sonnet 5.5 high | `tickets-assign` | 15.8 (2) | 18.5 (2) | −14% |
| Sonnet 5.5 high | `shared-expenses-w1` | 16.7 (2) | 26.8 (2) | −38% |
| Sonnet 5.5 high | `node-chess-engine` | 10.8 (1) | 16.4 (1) | −34% |
| Grok 4.6 xhigh | `tickets-assign` | 69.8 (1) | 99.2 (1) | −30% |

One step is faster in 5 of 6 cells, by 15% or more in 4, a median 30%. The seconds come out of `test`,
`document`, the step review and, on Sonnet and Grok, `implement`; the step plan, its review and the test spec do
not shrink. In the one cell that does not gain, the single step's documents and review took longer than the
three steps' together (90 against 59 seconds, 71 against 51) and its plan longer (155 against 117). This cut is
not a registered reading: in a baseline slice the planner chose the count, and the rounds ran hours apart.

**The prediction.** A quarter to a third was predicted. Sonnet: 19%, 44% and 34%. Grok: 30%. Sol 6.2 medium:
15% on expenses (30% by step count) and nothing on the ticket change, where the prediction missed: on that
driver a step's `test`, `document` and review time followed its content, not the number of steps.

### Registered readings

- **The arm takes** in five of the six cells. In the sixth, Sol 6.2 medium on the engine, the baseline already
  plans one step.
- **Time.** F1 saves time in four cells: Sonnet on all three cases, and Sol 6.2 medium on expenses at the
  threshold (15.2%). No difference is readable on Sol 6.2 medium's ticket change (+4%) or its engine (0%, no
  contrast).
- **Quality.** No loss is seen in any cell.
- **The named risk**, by the letter of the rule, shows in one cell: Sonnet on expenses, where both F1 `implement`
  snapshots pass 5 of 6 and the baseline's passes 6. The check is `unit` (R48), which a one-step item cannot
  pass before its `test` stage. The rule did not foresee that; it is reported as it fell and not rescored. On
  the checks of behaviour no one-step implementation failed anything.
- **Fewer steps pays on these drivers**, by the registered rule: the arm takes and saves time in four of six
  cells and no cell shows a quality loss. The fourth cell is at the threshold, so the firm part is narrower
  than the rule's words: it pays on Sonnet in every case, and on Sol 6.2 medium it depends on the case.

### Findings

- **F31 (firm on Sonnet 5.5 high in three cases; one slice on Grok; consistent with 135 recorded terra runs,
  R43).** The same item planned as one step instead of two to four finishes sooner and passes the same hidden
  checks: 19 to 44% sooner on Sonnet (4 to 13 minutes a slice), 30% on Grok (29 minutes), with fewer `test`
  refusals in total.
- **F32 (firm for these items).** The larger step's first implementation is right. In 14 one-step slices,
  five of them a whole chess engine, every check of behaviour passes at the `implement` snapshot. The risk
  round 4 named did not appear, on any driver, on items up to about 400 product lines in one file or 60 lines
  across six.
- **F33 (interim, two cases).** On Sol 6.2 medium the gain depends on the case: 15% by arm and 30% by step
  count on the service built from nothing, none on the one-endpoint change. That driver's per-step overhead is small (round 4: 91 seconds), so
  when a merged step's documents and review grow with its content there is little left to save.
- **F34 (firm, new).** The shipped bound does not fix the step count. It caps criteria per step, so a planner
  that writes 4 criteria gets one step and one that writes 6 gets three, for the same item on the same driver
  (R46). E-SIZE1's F29 saw the same from the other side: the bound caps the count of criteria, not their text.
  The F1 wording gave one step in 16 of 16 plans.
- **F35 (firm).** Every send-back in these 21 slices, in either arm, was a faulty command in the step plan,
  never a wrong product (R49). One step does not remove them, and they cost a one-step item one redo.
- **F36 (not measured).** An item that needs cutting (more than 12 criteria, several layers), what per-step
  reviews and step commits are worth on harder or longer work, and a run with a cleared context. The engine
  was meant as the hard case and was not hard for these drivers.

### Recommendation (owner's decisions; nothing built)

1. **A candidate change, the owner's call: the F1 wording for the step-plan duty's sizing bullet** (one step
   the default, at most 12 criteria and 6 product files a step, a larger item cut at a module or layer
   boundary). It is a product-behaviour change and it turns the direction of the bound the owner kept on
   2026-10-28, so it is not made here. For it: F31, F32 and F34. Against it: the gain is not shown on Sol 6.2
   medium's small change (F33), and nothing here tests an item that should still be cut (F36).
2. **If the owner wants it firmer before deciding, one guard round, registered first:** an item past the new
   numbers or across two layers (E-SIZE1's battleship server, case K4, is the ready one), F1 against the shipped
   text on Sonnet, to see that F1 still cuts where it should and what its larger steps cost there.
3. **Leave the rest as round 4 left it.** One step also removes all but one step review, which is most of what
   round 4's "one build review per item" would have saved; that candidate needs no separate test if this one
   is adopted.

### Limits

- One or two slices a cell. The overall registered reading turns on a cell at 15.2% whose baseline mixes one
  slice of each shape; the pooled cut that makes the picture clearer is exploratory.
- The hidden checks are at their ceiling in every cell, the engine included, so F1 could show a loss or a time
  change, not a gain in quality, and "the first implementation is right" is shown only for items these drivers
  find easy.
- Nothing larger than one file of about 400 lines or six files of about 60. Sonnet's ticket plans list 7
  product files, one over the arm's number, with no visible effect.
- The registered risk rule counted a check (`unit`) that a one-step item cannot pass at `implement`.
- A slice ends at `carry-forward`: the end-of-work review, the system tests and the release stages are not in
  it. One step also means one step commit, so the history is coarser; nothing here prices that.
- Up to seven slices ran at once. The Grok comparison is one slice against one from round 4, hours apart.

### Guard round: an item large enough to need cutting (registered before any counted guard slice)

**Question.** Owner, 2026-11-20, asked "Should I run the guard round on a larger item before you decide on the
wording?": "Run guard round". Recommendation 2 above named it: an item past F1's numbers or across layers, F1
against the shipped text, to see that F1 still cuts where it should and what its larger steps cost there.

**The item, and why not the one named.** Recommendation 2 named E-SIZE1's battleship server
(`node-battleship-server`). Read again, that item is one product file with one held-out check: under F1 it would
be one step by design, as the engine was, and `tickets-assign` already built a change across six files and three
layers as one step. The guard needs an item past the numbers. The largest recorded item is the `ticket-due-times`
request (`cases.json`, the planning-points probe of 2026-11-14), on the same ticket service as `tickets-assign`:
a due time stored on every ticket, a data-file migration for the tickets already in production, a setting for
the response hours, a listing filter, a staged switch-on (nothing changes until `DUE_TIMES=on`) and a way back
(release 1.4.0 must still start on the data file the new release wrote). Grok 4.6 xhigh planned it with 15, 20
and 27 criteria in 8, 9 and 11 steps and spent 207 to 222 minutes in its inner loop; no other driver has run it.

**Apparatus.** A step case, `tickets-due-times` (`guard-step-cases.json`): the whole request as one work item on
the `node-tickets` fixture, its only visible check `npm test`. `guard_apply.py` merges it into `step_cases.json`
of a throwaway worktree, never the checkout, because several hermetic suites walk every committed step case;
`slice.py` runs from that worktree, at ddf922c4e3c43e7106e13dca3c2963831dadb959 (the same ShipLoop 2.3.0 build).

**Yardstick the model never sees.** The eight checks of the full case: `suite` and `pristine` (the service's
own tests still pass, with new ones beside them, and unchanged) and the six modes of `checks/due_times_probe.py`
(`migrate`, `restart`, `switch`, `rollback`, `off`, `cli`). The case was calibrated when it was made against its
base, a reference and six planted defects. Through this round's grader (`slice_snapshots.due_times`) the base
passes 4 of 8 (not `suite`, `migrate`, `restart`, `switch`), the reference 7 of 8 (it adds no tests, so not
`suite`), and the planted defect `version-two` fails `rollback`, `pristine` and `suite`. Unlike the yardsticks of
rounds 4 to 6, this one has a known way for a plausible first implementation to be wrong: raise the data file's
format version and 1.4.0 no longer starts on it.

**Rehearsal** (four runs stopped after `step-plan`, not counted).

| Driver | Shipped text | F1 |
|---|---|---|
| Sol 6.2 medium | 5 criteria, 4 steps (1, 1, 2, 1), 9 product files | 7 criteria, 1 step of 6 product files |
| Sonnet 5.5 high | 10 criteria, 5 steps (2, 4, 2, 1, 1) | 14 criteria, 2 steps (7, 7): the due-time model and its storage first, then the API, the command line and the documents |

The step-plan reviews left all four plans as submitted. The item exercises both of F1's behaviours: Sonnet's
plan is past 12 criteria and is cut at a layer boundary, and Sol 6.2's fits inside the numbers and stays one
step.

**Runs.** Sonnet 5.5 high, two slices an arm, the four at once. Sol 6.2 medium, two slices an arm, the four at
once. Grok 4.6 xhigh, the plan only: one run an arm stopped after `step-plan`, because a full Grok slice of this
item does not fit in the two hours a background task gets here.

**Measures**, each per slice: criteria, steps planned, criteria and product files per step and which files each
step holds; minutes, and seconds by part; hidden checks at the last step's `implement` snapshot and at the end;
`test` refusals and send-backs.

**Readings.** A cell is one driver; two slices a cell read only large effects.

- *F1 cuts where it should*: an F1 plan that holds more than 12 criteria or more than 6 product files has two
  or more steps, none over either number. An F1 plan that fits inside the numbers as one step does not exercise
  the cut and is reported as such.
- *Quality at the end*: no loss is seen in a cell if every F1 slice passes at least as many of the eight checks
  at its end as the least of that cell's baseline slices.
- *The first implementation*, with round 6's lesson applied before the run: at the last step's `implement`
  snapshot the seven checks other than `suite` are read, since `suite` counts the new tests the `test` stage
  writes. The named risk shows in a cell if an F1 slice fails one of the seven there that every baseline slice
  of the cell passes there. A failure there that a later stage repairs is reported with the stage that repaired
  it.
- *Time*: as before, F1 saves time at 15% or more below the baseline's mean minutes and is slower at 15% or
  more above.
- *The guard holds* if F1 cuts wherever its plan is past the numbers, no cell shows a quality loss at the end
  and F1 is not slower in any cell. *The guard fails* if an F1 plan past the numbers stays one step, or a cell
  shows a quality loss at the end.
- Registered fallback (round 6's lesson): if the two arms' plans overlap in step count within a cell, the
  slices are also read by the steps planned, labelled exploratory.

**Limits known before the run.** One item, two slices a cell. The item is a brownfield change of a few hundred
lines, larger than anything in rounds 4 to 6 and still not a large build. Planners fit their criteria to the
bound (F34), so whether a plan is "past the numbers" depends on how many criteria the planner writes: in the
rehearsal only Sonnet's was. Grok is read by its plan alone. A slice ends at `carry-forward`.

**Budget and failures.** At most $25 for a Claude slice; each Grok plan about $3. A slice that ends without its
`carry-forward` accepted is reported as it ended and run once more if time allows.

### Guard round: results (run 2026-11-20 after 6bd1a372109cba27525a12d63e9f2f97e6af69cd)

**R51. The runs** (`evidence/slices-guard.txt`). Eight full slices (Sonnet 5.5 high and Sol 6.2 medium, two an
arm) and two Grok 4.6 xhigh runs stopped after `step-plan`. Every full slice completed its inner loop and none
was rerun. The two Grok plans cost $5.27 and $5.07 and took 31 and 41 minutes to an accepted plan.

**R52. The plans.**

| Driver | Shipped text | F1 |
|---|---|---|
| Sol 6.2 medium | 7 criteria in 4 steps; 6 in 3 | 7 criteria in 1 step; 5 in 1 |
| Sonnet 5.5 high | 12 criteria in 5 steps; 13 in 4 | 12 in 2 (7, 5); 12 in 2 (9, 4) |
| Grok 4.6 xhigh (plan only) | 10 in 3 (3, 3, 4) | 12 in 2 (5, 7) |

- Sonnet's two F1 plans and Grok's declare 10, 11 and 8 product files, past F1's 6, and all three cut the item
  in two at the same place: the due-time rule, the setting and the storage first, then the listing, the API,
  the command line and the release files. Each of Sonnet's built steps changed 5 product files, one slice's
  copy of release 1.4.0 kept as test data aside.
- Sol 6.2's two F1 plans stay one step. They declare 6 and 5 source files and `package.json`; the one step
  built changed 7 and 6 product files with `package.json` counted. The planner wrote 5 to 7 criteria and listed
  as many files as the number allows.

**R53. Time.**

| Driver | Baseline minutes (steps) | F1 minutes (steps) | Change |
|---|---|---|---|
| Sol 6.2 medium | 11.3 (4), 12.1 (3) | 9.5 (1), 9.4 (1) | −19% |
| Sonnet 5.5 high | 30.0 (5), 27.1 (4) | 25.6 (2), 25.7 (2) | −10% |

One Sonnet F1 slice spent about six of its minutes on two send-backs, both for a command or record in the step
plan that ShipLoop could not use (the accepted plan lacked the review's corrections; a recorded command that is
not a test runner). Neither is a wrong product (F35).

**R54. Hidden checks**, after the correction in R55. At the end of the slice: 8 of 8 in all eight slices,
`rollback` included (release 1.4.0 starts on the file the new release wrote). At the last step's `implement`
snapshot: 7 of 7 in all eight, both arms, so no later stage had anything to repair in the checks the model
never saw. `test` refused, per slice: Sonnet baseline 4 and 6 against F1 1 and 1; Sol 6.2 baseline 3 and 2
against F1 1 and 2.

**R55. A known apparatus exposure, met again and corrected for: a check built on the ticket fixture's own
tests sometimes loses its verdict.**
In the first grading three checks ended at `base_tests.py`'s 120-second ceiling with no test result: `pristine`
at a Sol 6.2 baseline's last `implement` snapshot, `pristine` at a Sonnet baseline's step commit, and `suite`
at the end of one Sonnet F1 slice, which made that slice read 7 of 8 at its end
(`evidence/slices-guard-snapshots.txt`, kept as it fell). Repeating the `suite` check on that slice's final copy
passed 5 of 5, 29 of 30 and 78 of 80 times, and one of the two failures kept is the untouched base's own tests
not ending in the base; plain `node --test` there passed 60 of 60 (`evidence/base-suite-flake.txt`). So the hang
is in the fixture's test run, about one run in forty on this machine, and says nothing about the tree graded.
`regrade_timeouts.py` runs again any check whose note is that timeout, up to three times, and keeps the first
note beside the rerun (`reran` in `slices-guard/snapshots.json`): all three pass at the first rerun
(`evidence/slices-guard-regrade.txt`). Both arms were hit, two baseline marks and one F1 mark of 98 graded.

Corrected the same day, after the first write-up called this a new fault: it is not new.
`docs/experiments/brownfield-flake-20261101/README.md` measured it on 2026-11-01 (32 of 928 concurrent runs of
the base's tests failed). The base's tests listen on the IPv6 wildcard and connect to 127.0.0.1, where another
project's server on this machine can hold the same port number, so a test reaches the wrong server. The
calibration suite was hardened then (26728eddd587930f5da3f6600e5d7ab4017d8acc,
8c5b4d4ec776dc9a06445c1054e9d4802558a649); the live check `base_tests.py` was left unchanged, because a retry
there could hide a delivery whose own server resets, and the choice was left with the owner. That study's rule
for a lost verdict is the one followed here: run the check again on the saved work, keep the first result,
report both. What this round adds is the form it took (three runs that never ended, where that study saw
resets and wrong answers) and the rerun applied to graded snapshots.

### Guard round: registered readings

- **F1 cuts where it should: on Sonnet and Grok yes, on Sol 6.2 medium no.** Sonnet's two F1 plans and Grok's
  are past the numbers and are cut in two, with 5 product files a step. By the instrument's count one Sonnet
  step is over the file number, because that slice kept a 25-file copy of release 1.4.0 as test data under
  `testdata/`, which the path classifier counts as product files. One of Sol 6.2's two F1 plans is past the
  number by the same count (6 source files and `package.json`) and is not cut; the other is inside the numbers
  and does not exercise the cut.
- **Quality at the end:** no loss is seen in either cell, after R55's reruns. By the first grading alone one F1
  slice read 7 of 8.
- **The first implementation:** the named risk does not show in either cell.
- **Time:** F1 saves time on Sol 6.2 medium (19%). On Sonnet no difference is readable (10%). F1 is slower
  nowhere.
- **The guard, by its letter, does not hold:** an F1 plan past the numbers stayed one step (Sol 6.2, one file
  over, the file being `package.json`). On what the cut was there to protect it holds: nothing was lost at the
  end or at the first implementation on any driver, and no cell is slower.

### Guard round: findings

- **F37 (firm for this item on Sonnet; plan only on Grok).** On the largest recorded item F1 still splits the
  work where the planner's own count passes the numbers, into two steps at the boundary between storage and the
  surfaces that show it, against four or five steps with the shipped text. Those larger steps passed every
  hidden check at their first implementation and at the end.
- **F38 (firm, and the reason the letter failed).** F1's numbers are a budget the planner fits, as the shipped
  bound's are (F34): Sol 6.2 wrote 5 to 7 criteria, listed as many files as the number allows, and built the
  whole item as one step. The numbers are not what kept the result right. The one-step version passed all seven
  applicable checks at its first implementation and all eight at the end, the way back to 1.4.0 included, in
  9.5 minutes against 11 to 12.
- **F39 (interim, two slices a cell).** The saving shrinks as the item grows: 10% on Sonnet here against 19 to
  44% on the small items, because two steps of five files are each larger than the five steps they replace.
  `test` refusals still fall, from 4 and 6 to 1 and 1.
- **F40 (apparatus; known since 2026-11-01, met again).** A hidden check built on the ticket fixture's own
  tests (`suite` and `pristine` of every ticket case, through `checks/base_tests.py`) can lose its verdict to
  another project's server on the same port (R55). Here it took the form of a test run that did not end, three
  times in 98 graded marks and twice in 80 repeats, and `base_tests.py` reports that as a failed check. One of
  the three would have failed this guard had it not been run again. Rounds 4 to 6 used the acceptance module
  for their ticket yardstick and saw no such failure.
- **F41 (not measured).** A full Grok run of a large item under F1; an item of thousands of lines; long runs
  and a cleared context; what a coarser step history costs later.

### Guard round: recommendation (owner's decisions; nothing built)

1. **The F1 wording stays the candidate, with one thing said plainly: its numbers do not guard anything.** The
   guard found no quality lost on the largest recorded item on Sol 6.2 medium or Sonnet, fewer `test` refusals,
   and equal or less time. But where a planner writes few criteria, F1 means one step for the whole item (F38).
   If the owner adopts the wording, it is adopted as "one step unless the planner sees a layer boundary worth
   cutting at", not as a size limit. A script-checked limit is not recommended: E-SIZE1's gate never fired in
   40 samples, and nothing here shows the one-step versions doing worse.
2. **The harness exposure is the owner's standing call, not a new proposal (F40).** The two options recorded
   on 2026-11-01 are still open: a retry in `base_tests.py`, or binding the base's tests to 127.0.0.1 in the
   pinned fixture. This round is one more reason to choose: a graded verdict was lost three times in 98, and
   once it would have failed a registered reading. Until then the rule stands: run a lost base-test verdict
   again before reading a bar, keep the first result, report both (`regrade_timeouts.py` does it for graded
   snapshots).
3. **Still unmeasured where it matters most for Grok:** a full Grok run of a large item under F1 (F41). The
   plan alone says two steps against three; the slice-length limit here kept the build out of reach.

### Guard round: limits

- One item, two slices a cell; the Sonnet time difference is inside the registered noise band.
- The guard's letter failed on a count of one file, and the count is the instrument's (declared paths by path
  class), which counts `package.json` and a test-data folder as product files where the wording would not.
- The yardstick had a known trap (the data file's version) and no slice fell into it in either arm, so it is at
  its ceiling here too: the guard shows no loss, not a gain.
- Three graded checks were run again after a harness timeout; the first grading is kept beside the reruns.
- Grok is read by two plans, one an arm. A slice ends at `carry-forward`.

### Owner decision, 2026-11-20: adopt the wording

Asked "Should I make the fewest-steps wording ShipLoop's step-plan rule?", the owner answered "Adopt the
wording". The step-plan duty's sizing bullet (`shiploop_prompts.DUTIES["step-plan"]`, item 4) is now arm F1's
text, byte for byte, so `overlays/f1-fewest-steps.json` applies only to commits before the adoption.
Recommendation 1 of round 6 and of its guard round is closed.

What it changes for later evidence: step counts and inner-loop times of runs from this version on do not compare
directly with earlier ones. The E-SIZE1 journal carries the matching entry
(`docs/shiploop-plan-sizing-journal.md`, entry 13), and the whole delivery that vouches for the release is in
`test/shiploop_e2e/LEARNINGS.md`. Still open from the guard round: a full Grok build of a large item under the
new text (F41), and the owner's standing choice on the ticket fixture's lost verdicts (F40).

## Round 7 (2026-11-20): which reviews earn their time on the owner's drivers?

### Question

Owner, 2026-11-20, asked "based on learnings, what next?" and then chose "Start review round". With steps now
fewer, reviews are the largest block left: a third of a Sonnet delivery. Two decisions are open. Round 1's
recommendation 4 (stop reviewing `plan` and `system-test-author`) was read on Codex terra only. And the
planning-review default was kept at `stage` by the owner on 2026-11-04 on four cases, with "a larger same-case
sample" named as what would reopen it (53d8d04f8dcf736a648dad1add62f3d6a1af715d).

### What exists (read in `skills/shiploop/scripts/` and in the history)

- **Eight review points.** An Improve review can follow `spec`, `test-strategy`, `plan`, `step-plan` (for the
  first item, or one sent back), each step's `document`, the last `carry-forward`, `system-test-author` and
  `release-plan` (`shiploop_stage_spec.reviewed_stages`, `shiploop_navigator._improve_checkpoint`).
- **One option.** `--planning-review stage|none`, recorded at the run's start. `none` removes the first four
  and needs the Improve card named at the start (`references/run-options.md`, which calls it the highest-risk
  combination).
- **The 2026-11-04 decision** (53d8d04f8dcf736a648dad1add62f3d6a1af715d). Same case and host, `stage` against
  `none`: planning 5.3 to 3.2 minutes, Improve children 8 to 4. What planning reviews had caught by then: a spec
  with no replayable move sequence and malformed API boundaries, a test strategy that assumed a browser
  connector that did not exist, two docstring edits, and nothing on the smallest case. "The evidence supports
  'review sometimes catches something real' and not how often."
- **Never run.** The three-arm comparison of planning reviews that the owner approved on 2026-10-28
  (`docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md`, Q2). The 2026-11-13 lifecycle assessment defers
  review-default changes "until a registered comparison shows a gain without a regression".

### Results from the records (free, before the registration)

**R56. Who runs without planning reviews** (`evidence/review-option-census.txt`; 1,251 run directories, 297
finished whole deliveries). 294 recorded `stage`. Of the three that recorded `none`, the harness asked for one.
The other two chose it themselves: a Codex terra xhigh run on 2026-11-01, and the Sol 6.2 medium delivery of
the fewest-steps round, whose own start command carried `--planning-review none --improve-skill=<card>` with
nothing in the harness's prompt asking for it. That delivery passed 18 of 18 held-out checks in 13 minutes, and
it is the only Sol 6.2 medium whole delivery on record. So nothing on record prices the option on the owner's
drivers, and a driver can turn planning reviews off unasked.

**R57. What reviews cost, by driver** (the same file, whole deliveries with `stage`).

| Driver | Runs | All reviews | spec | test-strategy | plan | step-plan | steps | carry-forward | system-test-author | release-plan |
|---|---|---|---|---|---|---|---|---|---|---|
| Codex terra high | 150 | 34% | 4.2% | 3.4% | 3.1% | 6.2% | 6.6% | 3.9% | 3.0% | 3.6% |
| Codex terra xhigh | 117 | 30% | 3.8% | 2.7% | 2.8% | 5.5% | 6.5% | 3.5% | 2.6% | 2.7% |
| Claude Sonnet 5.5, October builds | 8 | 43% | 7.6% | 8.5% | 3.9% | 2.8% | 0.9% | 6.0% | 4.2% | 1.2% |
| Codex Sol 6.1 medium | 4 | 27% | 3.3% | 2.2% | 2.6% | 5.5% | 7.3% | 2.4% | 2.1% | 2.0% |
| Grok 4.6 xhigh | 3 | 35% | 3.4% | 3.5% | 3.9% | 5.0% | 12.6% | 2.1% | 1.6% | 2.8% |

The fewest-steps round's one Sonnet 5.5 high delivery spent 33% of its 48 minutes in reviews, 11% of it in three
rounds of the `system-test-author` review and 11% in the four planning reviews. Its Sol 6.2 medium delivery,
with planning reviews off, spent 17%.

**R58. What reviews changed, by driver** (`evidence/review-yield-drivers.txt`: 255 reviews in this study's 54
slices and 2 whole deliveries, from each review's own pass log).

| Driver | Reviewed stage | Reviews | Edited anything | Lines in an edit (median) | Seconds (median) |
|---|---|---|---|---|---|
| Sonnet 5.5 high | step-plan | 28 | 17 (61%) | 12 | 86 |
| | a step | 47 | 24 (51%) | 22 | 40 |
| | carry-forward | 20 | 18 (90%) | 19 | 65 |
| Sol 6.2 medium | step-plan | 33 | 8 (24%), the result only | 4 | 34 |
| | a step | 68 | 4 (6%) | 40 | 15 |
| | carry-forward | 31 | 0 | | 14 |
| Grok 4.6 xhigh | step-plan | 4 | 4 | 28 | 642 |
| | a step | 4 | 1 | 10 | 283 |

The same review is a different thing on the two drivers. On Sol 6.2 medium it is short and almost never changes
anything; on Sonnet it edits half the time or more. Round 1's yield table, read on terra, transfers to neither.
An edit is not a defect caught (F6), so what Sonnet's edits are is still to be judged.

### Registered design (written and committed before any counted run)

**Why.** R57 is accounting and round 4 showed accounting can mislead: the cost of a part is priced by an arm
that removes it. R58 says the reviews edit, not whether the edits matter.

**Arms**, whole deliveries from intake to handoff with `test/shiploop_e2e/run.py`, each from a plugin build of
this checkout with one overlay applied to the copy (`build_arm.py`; the checkout is never changed).

- **S, as shipped, pinned** (`overlays/r7-s-planning-reviews-pinned.json`): a new run records `stage` whatever
  its start command asked for, because of R56. All eight review points run.
- **L, lean** (`overlays/r7-l-lean-reviews.json`, with the harness's `--planning-review none`): no review
  follows `spec`, `test-strategy`, `plan`, `step-plan` or `system-test-author`. The step reviews, the last
  carry-forward's review and the `release-plan` review still run, and every gate is unchanged.

Two arms, the widest contrast both open decisions allow, instead of three: L removes everything round 1's
candidate and the `none` option would. If L loses something, which review mattered is the follow-up.

**Rehearsal** (not counted; Sol 6.2 medium, the `hello` case). Both passed every verdict. S recorded `stage` and
ran reviews of spec, test-strategy, plan, step-plan, the step, carry-forward, system-test-author and
release-plan, in 6.5 minutes. L recorded `none` and ran reviews of the step, carry-forward and release-plan, in
6.6 minutes.

**Cases.** `ticket-due-times` on both drivers: the planning-heavy request of the guard round (a migration, a
switch-on flag, a way back to 1.4.0), eight held-out checks with a known trap, no port lease. `shared-expenses`
on Sol 6.2 medium as a second case (six checks).

**Runs.** Sonnet 5.5 high: two S and two L of `ticket-due-times`, the four at once. Sol 6.2 medium: two S and two
L of each case. A run whose recorded option is not its arm's is set aside and run once more.

**Measures**, each per run: minutes from start to end; seconds by stage and by reviewed stage; the harness
verdicts; held-out checks at the end (a base-test verdict lost to a timeout or a reset is run again and both
results kept, R55); reviews run; refusals, send-backs and work items added.

**What the removed reviews changed** (the second instrument). For every review of the five removed stages in
the S runs of this round and in the fewest-steps round's two deliveries, the tree and the result before the
review against after it, cut at 12,000 characters. Two Opus 5.5 judges, each blind to the other, label each:
`substantive` (it changes what is built, a rule the product must meet, or what a test or check would catch),
`wording` (documents, names, comments, restating, format), or `records` (ShipLoop's own bookkeeping).

**Readings.** A cell is one driver and case; two runs an arm read only large effects.

- *Time*: L saves time in a cell at 15% or more below S's mean minutes; within 15% no difference is readable.
- *Quality*: no loss is seen in a cell if every L run passes every harness verdict and at least as many
  held-out checks as the least of the cell's S runs.
- *The removed reviews earn their place* on a driver if both judges call the edit substantive in at least 30%
  of that driver's removed reviews; *they do not* if it is 10% or fewer; between, no reading. (Round 1 called
  31% earning it and 2 to 4% not.)
- *Lean pays* on a driver if L saves time in each of its cells, no cell shows a quality loss, and the removed
  reviews do not earn their place there. *Lean does not pay* if a cell shows a quality loss or the removed
  reviews earn their place. Anything else is reported with no overall reading.
- Registered fallback: if a run's recorded option or reviews are not its arm's and the rerun's are not either,
  the runs are read by the reviews they ran, labelled exploratory.

**Limits known before the run.** Two runs a cell, one or two cases. Held-out checks have been at their ceiling
in every round, so a quality loss is unlikely to show there; the judged edits are the instrument for what is
lost, and an edit is not an escape. The judges are one model. Reviews run inline, in the builder's own
conversation, so "a review" means a second look by the same model. Up to eight ticket-service runs at once can
meet the port collision of R55.

**Budget and failures.** At most $40 for a Claude run, about $100 for the four. A run that ends without every
verdict is reported as it ended and run once more if time allows.

### Results (run 2026-11-20 after b1b90f373c19130f67bf28d2b7a6d90430552b15)

**R59. The runs** (`evidence/review-arms.txt`). Twelve whole deliveries: Sol 6.2 medium, two S and two L of
`shared-expenses` and of `ticket-due-times`; Sonnet 5.5 high, two S and two L of `ticket-due-times`. Every run
recorded its arm's option, so none was set aside and the registered fallback was not needed. Every S run ran
reviews of all eight points; every L run ran only the step, carry-forward and `release-plan` reviews. Eleven
ended. One Sonnet L run was still working when this was written (R62); it has ended since (see the update
after Limits).

**R60. One run's process kill reached five others.** At 20:35:19, 31.7 minutes into the four Sonnet runs,
`sonnet-high-due-S-2` stopped its own test server with `pkill -f "src/server.js" -P $(cat $S/pid)` and then
`pkill -f "node src/server.js"`. macOS `pkill` reads everything after the first pattern as more patterns, and a
host's command line holds the request, which names `src/server.js`. The other three Sonnet hosts ended with
SIGTERM, at `system-test`, `release-plan` and `release-check`. Two Sol hosts received it too: one in the review
of `release-plan`, which `run.py` resumed 0.1 seconds later, and one 12 seconds after its delivery was done,
which lost only its process verdict (`runs-reviews/interrupted.json`). The three Sonnet runs were resumed by
hand with `run.py --resume-run` 14.0 minutes later.

What it does to the measures. Minutes from start to end, the registered measure, cannot be compared in the two
`ticket-due-times` cells. Every run had by then finished planning, its build items and the writing of its system
tests, so those parts are clean in all twelve, and the cells are also read at a milestone that was not
registered: the first entry into `system-test`. The time no host was running is taken out of the seconds by
part (`down` in `runs-reviews/census.json`).

**R61. Time**, in minutes, the two runs of each arm.

| Cell | Arm | Start to end | To the first step plan | Build | Writing the system tests | To `system-test` | In reviews |
|---|---|---|---|---|---|---|---|
| Sol 6.2 medium, shared-expenses | S | 10.9, 9.0 | 2.9, 2.5 | 5.1, 4.4 | 0.4, 0.3 | 8.4, 7.3 | 1.4, 1.2 |
| | L | 14.2, 12.9 | 2.6, 2.6 | 7.2, 7.2 | 0.3, 0.3 | 10.2, 10.2 | 2.3, 1.3 |
| Sol 6.2 medium, ticket-due-times | S | 20.8 (resumed), 16.5 | 4.6, 3.7 | 9.3, 7.5 | 1.2, 1.7 | 15.2, 13.0 | 4.4, 2.2 |
| | L | 15.2, 16.8 | 2.2, 3.0 | 9.2, 9.2 | 0.7, 1.3 | 12.1, 13.5 | 1.5, 1.8 |
| Sonnet 5.5 high, ticket-due-times | S | 53.1 (39.1 with a host running), 45.3 | 9.4, 10.3 | 20.3, 28.5 | 1.6, 1.7 | 31.3, 40.5 | 10.2, 8.4 |
| | L | 110.0 (96.0), 48.3 (34.2) | 5.3, 6.4 | 21.6, 20.2 | 1.2, 0.9 | 28.1, 27.4 | 7.4, 3.3 |

- **Sol 6.2 medium, shared-expenses.** L is 36% slower from start to end (mean 13.5 against 9.9). The five
  removed reviews took 55 seconds of an S delivery, and planning took the same time in both arms. The
  difference is in the build (7.2 against 4.8 minutes), in each part of it: implement 102 against 64 seconds,
  test 129 against 109, the step review 64 against 9.
- **A review's seconds on Sol 6.2 medium.** The first review a run meets takes 23 to 41 seconds; most later ones
  take 6 to 22, and every one ends with nothing to change. With the planning reviews removed, the first review
  is the step's, and it takes 35 to 92 seconds. So total review time did not fall on `shared-expenses` (1.8 minutes in
  three reviews against 1.3 in eight) and fell by half on `ticket-due-times` (1.7 against 3.3).
- **Sol 6.2 medium, ticket-due-times.** The removed reviews took 95 seconds. Planning is 1.6 minutes shorter in
  L (2.6 against 4.2) and the build 0.8 longer. To `system-test`: 12.8 against 14.1, 9% less. Start to end: 16.0
  against 18.6 with the resumed run (14% less), against 16.5 without it.
- **Sonnet 5.5 high.** The removed reviews took 5.0 minutes of an S delivery (the four planning reviews 4.3,
  the `system-test-author` review 0.7). Planning is 4.0 minutes shorter in L (5.8 against 9.9, 41% less). To
  `system-test`: 27.8 against 35.9, 23% less; part of that is the plans' shape, not the reviews: the S runs
  planned 2 and 3 work items, the L runs 2 and 1.
- **Where an S delivery's time goes on Sonnet** (mean 41.8 minutes with a host running): the step plan and
  test spec 17%, the planning stages 15%, test 14%, acceptance to handoff with the release plan's review 13%,
  implement 12%, the four planning reviews 10%, the step reviews 5%, document 5%, carry-forward and its review
  4%, the system tests 3%, their review 2%.
- **Cost.** The one Sonnet run that was not interrupted cost $15.60. A killed session reports no cost, so the
  other three have none to compare.

**R62. Verdicts and held-out checks.**

| Cell | S | L |
|---|---|---|
| Sol 6.2 medium, shared-expenses | 6 of 6, 6 of 6; every verdict | 6 of 6, 6 of 6; every verdict |
| Sol 6.2 medium, ticket-due-times | 3 of 8, 8 of 8 | 3 of 8, 8 of 8 (this one's process verdict lost to the kill) |
| Sonnet 5.5 high, ticket-due-times | 8 of 8, 8 of 8; every verdict | 8 of 8, every verdict (and 8 of 8 at its last commit before the kill); 8 of 8 after a rerun |

- **The two 3 of 8, one in each arm, are one design choice.** The delivery adds a migration script, and its
  server refuses to start with `DUE_TIMES=on` until an operator has run it ("tickets are missing due times; run
  scripts/backfill-due-times.js first"). The five probes that start the new release switched on against the old
  data file fail at that start; `suite`, `pristine` and `off` pass. The request says due times "are switched on
  in production only once the data file holds them" and does not say what fills the file, so the words allow
  this reading and the probes do not. The other two Sol deliveries and all four Sonnet ones fill the file when
  the service starts. These are the first failed held-out checks of this study. The guard round's four Sol
  slices of the same request passed 8 of 8; four against four, that difference can be chance.
- **One lost verdict, run again** (R55's rule). `sonnet-high-due-L-2` was first graded 7 of 8: `pristine` failed
  with a connection reset in the untouched base's own tests. Run again on the saved work it passed 5 of 5; both
  are kept (`runs-reviews/reruns.json`).
- **The run that was unfinished at the first write-up** (its end is in the update after Limits). After its resume, `sonnet-high-due-L-1`'s release check ran the delivery's `npm test`
  46 times, saw about 4 abnormal runs against 0 in 40 on the base, and opened a third work item so that the
  service registers its signal handlers before it reports that it listens. Its later step plan records 0 red in
  200 runs before the fix. At 84 minutes it was still building that item. Its product at its last commit before the
  kill (28.3 minutes, system tests written) passes 8 of 8 (`runs-reviews/l1-at-kill.json`).

**R63. Refusals and send-backs.** Refused commands are alike in both arms: Sonnet 9 and 8 against 8 and 8; Sol
6.2 `ticket-due-times` 3 and 8 against 4 and 5; `shared-expenses` 6 and 7 against 7 and 5. No build stage sent
an item back, and no stage after the build opened new work, in the eleven runs that had ended at the first
write-up. The twelfth is the exception (see the update after Limits).

**R64. What the removed reviews changed** (`evidence/removed-review-judged.txt`; each packet is the review's own
tree before and after, and its result as submitted and as accepted). 37 reviews of the five removed stages, in
this round's six S runs and the fewest-steps round's two deliveries. 13 changed a file or a result, every one
of them on Sonnet. The two judges gave the same label to 13 of 13 (kappa 1.00): 11 substantive, 2 wording.

| Driver | Reviewed stage | Reviews | Changed anything | Substantive, both judges |
|---|---|---|---|---|
| Sonnet 5.5 high | spec | 3 | 3 | 3 |
| | test-strategy | 3 | 3 | 3 |
| | plan | 3 | 3 | 3 |
| | step-plan | 3 | 1 | 0 |
| | system-test-author | 4 | 3 | 2 |
| | all five | 16 | 13 | 11 (69%) |
| Sol 6.2 medium | all five | 21 | 0 | 0 |

The substantive ones, in the judges' words: a process test that starts the server with an invalid setting and
checks its exit code; rollback tests that "gain a replayable procedure and a guard assertion"; module contracts
with signatures and error behaviour; a missing due time defined as "an absent key only"; a system test that
kills the server in the middle of a burst of requests and checks that the data file still loads with every
acknowledged expense. Ten of the
eleven correct or complete something the request or the reviewed text already required; one adds requirements
the request did not state.

### Registered readings

- **Time.** Sol 6.2 medium, `shared-expenses`: L is slower (36%). Sol 6.2 medium, `ticket-due-times`: not
  readable as registered, because one S run was resumed; read any other way it shows no readable difference
  (14% less with that run, 3% less without it, 9% less to `system-test`). Sonnet 5.5 high: not readable as
  registered (three runs interrupted, one unfinished); at the milestone that was not registered L saves time
  (23%).
- **Quality.** `shared-expenses`: no loss seen. Sol 6.2 `ticket-due-times`: by the letter a loss, because one L
  run lacks a harness verdict. That verdict was lost to the kill 12 seconds after the delivery was complete, so
  the cell is read here as no loss seen, and this is a departure from the letter: held-out checks are 3 and 8
  of 8 in both arms. Sonnet: no loss seen in the finished L run after its rerun (7 of 8 as first graded); the
  other L run was unfinished at the first write-up. It has since ended with every verdict and 8 of 8, so the
  cell reads no loss seen.
- **The removed reviews earn their place on Sonnet 5.5 high** (69% substantive by both judges; the bar was
  30%). **They do not on Sol 6.2 medium** (0%; the bar was 10%).
- **Lean does not pay on Sonnet 5.5 high,** by the registered rule: the removed reviews earn their place.
- **On Sol 6.2 medium there is no overall reading.** The removed reviews do not earn their place and no quality
  loss is seen, but L did not save time in each cell: in one it was 36% slower.

### Findings

- **F42 (firm for these two requests; 21 reviews).** On Sol 6.2 medium the five removed reviews are a
  formality, and removing them buys nothing. (Corrected 2026-11-21 after review: what is shown is that no saving
  appeared in this round; it does not bound what removing them could save.) None changed a file or a result. They cost about a minute to a
  minute and a half of a delivery (9%), and the run pays the first review's reading time whichever review comes
  first (R61). The saving the option can reach is under the 15% this study can read, and in one cell L was
  slower for reasons the removed reviews do not explain.
- **F43 (firm for the three planning reviews on these requests; interim for the other two. "Earn their place"
  in this round is the registered edit-yield rule, not a measured benefit to a delivery: F45).** On Sonnet 5.5 high
  the reviews of `spec`, `test-strategy` and `plan` are real editing: 9 of 9 changed content that both judges
  call substantive, and nearly all of it completes what was already required. The `step-plan` review made one
  wording edit in 3. The `system-test-author` review is 2 of 4. Round 1's recommendation 4 was read on terra,
  where the `plan` review was 2 to 3% substantive and the `system-test-author` review edited anything in 4%
  (R8); it does not transfer to Sonnet.
- **F44 (interim; the registered measure was lost. Qualified 2026-11-21 after review: this is an accounting
  estimate, not a measured saving, and the plans' different work-item counts may themselves be an effect of the
  reviews).** What lean would buy on Sonnet is 4 to 5 minutes of a
  40-minute delivery, 10 to 12%: the planning window is 4.0 minutes shorter and the removed reviews' own
  seconds are 5.0 minutes. The 23% at the milestone overstates it, because the S runs also planned more work
  items.
- **F45 (firm, and a limit of F43).** A substantive edit is not a defect caught (F6). All four Sonnet products
  pass 8 of 8 with the reviews and without them, one of them graded before it finished. The reading that the
  reviews earn their place rests on the judges alone; nothing here shows what the edits bought.
- **F46 (new; interim, four runs).** On Sol 6.2 medium the held-out result of the planning-heavy request was
  decided in planning, and no review touched it. Two of four whole deliveries chose an operator-run migration
  and a service that will not start switched on before it, one in each arm; in the S run the reviews of the
  spec, the test strategy and the plan each ended without a change. The request allows the choice and the
  probes do not (R62), so this is also a question about the yardstick.
- **F47 (apparatus and product; second time).** A builder stopped its test server by name pattern and ended
  five other hosts (R60). Round 3 saw the same class in 7 of 108 reader sessions (R21). ShipLoop's text says
  nothing about how a run stops a process it started, and the same command can reach processes that are not
  ShipLoop's.
- **F48 (apparatus; likely, not shown. Qualified 2026-11-21 after review: four at once is a precaution, not a
  measured threshold).** Eight runs of one fixture at once is too many. Besides the kill, one
  run's own release check measured its tests as unstable while the others were running and found nothing to
  reproduce later (R62), and one base-test verdict was lost to a reset (the exposure of R55). Fewer at once
  lowers the exposure; it does not remove it.
- **F49 (exploratory).** On Sonnet the step plan and test spec of a work item now take more time than
  implementing it: 7.0 against 5.1 minutes of an S delivery, over two or three work items. With steps fewer
  and reviews priced, that pair is the largest single part left (R61).

### Recommendation (owner's decisions; nothing built)

1. **Keep the planning-review default at `stage`; the 2026-11-04 decision stands.** This round is the larger
   same-case sample that decision named, and it is still small. On Sonnet the planning reviews are where content changes, at a price
   of about a tenth of a delivery. On Sol 6.2 medium they change nothing, cost a minute, and removing them
   saved nothing readable. Neither driver gives a reason to change the default.
2. **Withdraw round 1's recommendation 4 for these drivers.** Stopping the `plan` review is not supported on
   Sonnet (3 of 3 substantive). The `step-plan` review is the one removed review with no substantive edit on
   either driver, 0 of 7, but three judged Sonnet reviews are too few to drop it on, and R58 shows it editing
   in 17 of 28 Sonnet slices.
3. **Decide whether a run may switch planning reviews off by itself** (R56: two of 297 did, one of them on Sol
   6.2 medium). Arm S's one-line pin is the candidate if the answer is no. On Sol 6.2 medium the choice costs
   nothing measurable either way; on Sonnet it would drop the edits of F43 without anyone asking.
4. **Tell builders how to stop what they start** (F47): by the process id they recorded, never by name or
   pattern. One sentence in ShipLoop's text; not written here.
5. **For Sol 6.2 medium, reviews are not the lever on a planning-heavy request** (F46). A second look by the
   same model passed the choice that failed the probes. Two things could move it, neither tested here: the
   spec stage saying outright how existing data gets its new field (the side experiment in
   `docs/experiments/spec-elaboration-20261120/`, another session's, is aimed at gaps of this kind), or a
   review by a different model.
6. **Decide what the `ticket-due-times` yardstick should accept.** Either the request says the release fills
   the file itself, or the probes follow the delivery's documented switch-on steps. Changing either breaks
   comparison with this round and the guard round.
7. **Run at most four deliveries of one fixture at once** (F48). A harness habit, adopted for this study from
   here on.

### Limits

- Two runs a cell, one of them unfinished at the first write-up (ended since). The registered time measure was lost in two of
  three cells to the kill; the milestone and the time split that replace it were not registered.
- The judges are one model, and 13 packets is a small base for a kappa. Packets are cut at 12,000 characters.
- An edit is not an escape (F45). The held-out checks are at their ceiling on Sonnet and cannot show what the
  judged edits bought.
- The two failed Sol deliveries fail on one reading of the request (F46); the count of five failed probes is
  that one choice five times.
- Reviews are inline: "a review" here is a second look by the same model in the same conversation.
- Only one Sonnet run reported its whole cost.
- Whether an S run asked for `none` and was held to `stage` by the pin was not established.
- R61's time split charges a review to the stage it reviews and leaves out the time no host ran; a resumed
  session re-reads its run, and that reading is charged to the stage it resumed in.

### Update, 2026-11-20, after the first write-up (6c4fcfdbe14bde845eb9bb110eb737dd732e63d6): the twelfth run ended

`sonnet-high-due-L-1` ended 110.0 minutes after its start, 96.0 of them with a host running: every harness
verdict and 8 of 8 held-out checks. The work item its release check opened took 52 minutes, from 52.3 to 104.6,
with two send-backs from `implement` to the step plan (at 68.1 and 85.7 minutes). The product had passed 8 of 8
at 28.3 minutes, before that item (`runs-reviews/l1-at-kill.json`). The resumed session cost $7.44; the session
the kill ended reported none.

What it changes above. R59: all twelve ended. R61: the L row of the table now holds 110.0 minutes and 7.4
minutes in reviews. R62: 8 of 8 at the end. R63: this run is the one with send-backs and with work opened after
the build. The quality reading for the Sonnet cell is now no loss seen. No time reading changes: start to end
was already not comparable in this cell. `runs-reviews/unfinished.json` is removed; the report no longer needs
it.

- **F50 (new; interim, two cases on the current Sonnet).** A work item opened after the build is what makes a
  Sonnet delivery long. Here it more than doubled the run (52 minutes on top of 44 with a host running) for a
  product that already passed every held-out check. On record it is rare (`evidence/late-work-census.txt`): 8
  of 311 finished whole deliveries, 5 of 269 on terra, none on Sol 6.2 medium (11), Sol 6.1 medium (4) or Grok
  (6), but 2 of 5 on Sonnet 5.5 high: this one, opened by `release-check`, and the fewest-steps round's
  `shared-expenses` delivery, opened by `product-acceptance`, which added 13 minutes. Whether either was needed
  is not established. This one followed a stability measurement taken while other runs shared the machine
  (F48).
- **Also read for the next round (exploratory; quick cuts of this round's runs and of the records, not
  registered; `evidence/next-round-cuts.txt`).** On Sonnet the step plan alone takes 11% of a delivery, against
  6 to 8% on Sol 6.2 medium, and Sonnet's plans hold 20 to 26 criteria for the request where Sol 6.2's hold 2 to
  6. The seconds after a refused command are 7 to 12% of a run, most of them after the mutation check in `test`. The
  three recorded Grok 4.6 xhigh deliveries of `ticket-due-times` (2026-11-14, before the fewest-steps release)
  took 339 to 364 active minutes, 112 to 134 of them in reviews: the step reviews 38 to 53, the four planning
  reviews 46 to 56. Their review records are still on disk and have not been judged.

## Round 8 (2026-11-20): Grok's reviews and a Sol 6.2 high baseline, on the latest ShipLoop

### Question

Asked "what should we do to continue?", the owner chose "Start Grok scan": a Grok 4.6 xhigh delivery of the
ticket request takes about six hours on record, a third of it in reviews, and round 7 showed that what a review
is worth depends on the driver. Two instructions arrived while the scan ran, and both change the round.

### Owner decisions, 2026-11-20

1. **"lets switch to sol 6.2 high instead of medium".** Read here as: the study's drivers are now Sonnet 5.5
   high, Grok 4.6 xhigh and Sol 6.2 high. The Sol 6.2 medium results of rounds 4 to 7 stay as measured and are
   never pooled with high. No whole delivery on Sol 6.2 high is on record, so a baseline is registered below.
2. **"alwasy use the absolute latest version of shiploop".** It came right after a status note said the three
   recorded Grok deliveries ran ShipLoop 1.34.3. Read here as: every run of this study is built from the newest
   commit of `skills/shiploop` on `main` at its launch, with no overlay unless an overlay is the arm; the commit
   is recorded with the run; runs on different ShipLoop commits are not pooled; and records made on an older
   ShipLoop are context and carry no reading. Today the newest is ShipLoop 2.4.0
   (4693c1a307984a71dda367d98568337e663d6e53).

### Context from the records (ShipLoop 1.34.3 and 2.3.0, so no reading)

The scan the owner asked for, kept as background because of decision 2.

**R65. Time and cost of a Grok 4.6 xhigh delivery on ShipLoop 1.34.3** (`evidence/next-round-cuts.txt`, part C;
the planning-points probe of 2026-11-14, 909adf228e00254d293ddfcd76b8011ef296fd6c: three finished deliveries of
`ticket-due-times`, all passing). 339, 348 and 364 active minutes; $89 to $96 each. In minutes: planning 36 to
40, step plan and test spec 26 to 28, implement 25 to 35, test 38 to 61, document 28 to 37, system tests 12 to
14, acceptance to handoff 26 to 36, reviews 112 to 134 (33 to 39%). Their plans held 8 to 11 steps, under the
step text of that version.

**R66. What Grok's reviews changed, from their pass logs** (`evidence/grok-review-scan.txt`: 76 reviews in 10
runs; the whole deliveries are the three above, a fourth that did not finish, and a `hello` delivery stopped
after its spec review).

| Reviewed stage | Reviews | Changed anything | Lines changed when it did | Minutes a review (median) |
|---|---|---|---|---|
| spec | 5 | 5 | 21 to 210 | 9.8 |
| test-strategy | 4 | 4 | 32 to 104 | 11.6 |
| plan | 4 | 4 | 26 to 81 | 12.1 |
| step-plan | 4 | 4 | 12 to 37 | 15.7 |
| a step | 33 | 8 (24%) | 1 to 8 | 3.9 |
| carry-forward | 4 | 0 | | 7.2 |
| system-test-author | 4 | 1 | 17 | 2.5 |
| release-plan | 3 | 2 | 6 and 25 | 10.3 |

In the five slices (ShipLoop 2.3.0, one on 1.36.0): step-plan 5 of 5, a step 1 of 5, carry-forward 0 of 3.

What it suggests, and no more than that. On these records Grok looks like Sonnet, more so: the four reviews
before the build changed something every time, by tens to hundreds of lines, at 10 to 16 minutes each. Step
reviews seldom changed anything and then by a few lines, and their 32 to 45 minutes a delivery follow the step
count, which the current step text has cut (Grok planned this request as 2 steps under it, R52). The
end-of-item review never changed anything. None of it was judged, and none of it is today's ShipLoop.

### Registered design (written and committed before any counted run)

**Builds.** A clean detached worktree of `main` at this registration's commit (ShipLoop 2.4.0), its plugin built
with `build_arm.py` and no overlay, and `run.py --source checkout --plugin-dir` from that worktree. Before each
batch the newest ShipLoop commit on `main` and `origin/main` is checked again; if it has moved, the batch is
built from the newer one and is not pooled with earlier runs.

**Sol 6.2 high baseline** (starts with this commit). `ticket-due-times` four times and `shared-expenses` twice
on Codex `gpt-6.2-sol` at `--effort high`; at most four runs of one fixture at once. The base it is read
against is round 7's Sol 6.2 medium runs of the same two requests in arm S (two a request; ShipLoop 2.4.0 with
planning reviews pinned on). Round 7's two medium L runs of `ticket-due-times` count for the planning choice
only.

- *Measures*, each per run: minutes from start to end and to two milestones (the first step plan, the first
  entry into `system-test`); seconds by stage; the harness verdicts; held-out checks; reviews run and which
  changed anything; refusals; work items; the planning choice (the service fills the data file when it starts,
  or refuses to start until an operator has run a script), read from the probes.
- *Time*: high is slower in a cell at 15% or more above medium's mean minutes, faster at 15% or more below;
  within 15% no difference is readable. If a run is interrupted, the cell is read at the milestones.
- *Quality*: held-out checks and verdicts are reported per run. The planning choice is counted, four high
  against four medium. Four against four cannot show a difference in a rate, even none against two, so no
  reading is registered on it; the count is kept for pooling with later runs.
- A run that records `none` by itself (R56) is reported apart from the cell.

**Grok 4.6 xhigh on the latest ShipLoop: registered, not started.** A recorded delivery cost $89 to $96 and took
about six hours, so no Grok run starts without the owner's word. If it is given: one or two deliveries of
`ticket-due-times` from the same build.

- *Measures*: minutes by part with a host running; steps and work items; every review's passes, seconds and
  whether it changed anything; held-out checks.
- *Judges*: every review that changed anything, at all eight review points, as packets built like round 7's
  (`removed_review_diffs.py --all-stages`), two Opus judges blind to each other, round 7's labels. Six of round
  7's packets are mixed in as anchors: if a judge labels fewer than five of the six as round 7's judges did,
  the shares are reported without a reading.
- *Readings*, by group (the five reviews round 7 removed; the step reviews; the two end reviews): a group earns
  its place at 30% or more substantive by both judges and does not at 10% or fewer.
- R65's minutes are not a baseline for it: the version differs, so a difference is described and not read.

**Amended before the Grok run, 2026-11-21.** The owner said "Run one". The Grok command-line tool (1.0.92) now
lists `grok-4.7` as its newest and default model; the harness default is still `grok-4.6` at extra-high, an owner
setting of 2026-11-10 (db47982bcd9faf553041c26958abecd402002963). Asked which to use, the owner declined the question, so the
standing rule decides: the run uses the newest model in the host's own catalog, `grok-4.7`, at `xhigh`, passed on
the command line. Both models accept `xhigh` (a one-word prompt each). The harness default is not changed here:
that is the owner's decision. What it changes: R65 and R66 are `grok-4.6` on an older ShipLoop, so they are
context twice over, and the estimate of four hours and $60 to $90 comes from them and may not hold. One
delivery of `ticket-due-times`; no time or spend limit is set, as the harness's default is none (owner,
2026-10-24). The measures, the judges and the readings above stand, with one run a group.

**Superseded minutes later by the owner, 2026-11-21: "Use 4.6 extra high".** The `grok-4.7` run was stopped 1.5
minutes after its start, at `intake`; its folder is kept and not counted. The delivery runs on `grok-4.6` at
`xhigh`, as first registered and as the harness defaults. So the owner's named model stands over the catalog's
newest, and R65 and R66 are the same model on an older ShipLoop: still context, because the ShipLoop version
differs. Everything else in the amendment above stands: one delivery, no time or spend limit, one run a group.

**Limits known before the run.** Two to four runs a cell. The medium runs ran hours earlier and with the pin.
Sol 6.2 high has no earlier whole delivery, so nothing checks this baseline against another day. One model as
both judges.

**Budget.** Six Codex deliveries, about 20 to 40 minutes each. No Grok spend without the owner's word.

### Results: the Sol 6.2 high baseline (run 2026-11-20 after ff8e63fab93a592dda80fe600d088d16173d5c68)

**R67. The runs** (`evidence/effort-sol-high.txt`). Six whole deliveries on Codex `gpt-6.2-sol` at high effort,
from a clean checkout of the registration commit (ShipLoop 2.4.0, no overlay): `ticket-due-times` four at once,
then `shared-expenses` two at once. The newest ShipLoop commit was checked before each batch and had not moved.
Every run ended in one session with every harness verdict. Two of the six recorded `none` by themselves and are
reported apart (R70).

**R68. Time**, in minutes.

| Request | Measure | Medium, arm S | High | Change |
|---|---|---|---|---|
| ticket-due-times | start to end | 20.8 (resumed), 16.5 | 19.7, 20.0, 25.3 | +16% |
| | to the first step plan | 4.6, 3.7 | 4.5, 4.1, 4.6 | +5% |
| | to `system-test` | 15.2, 13.0 | 16.1, 16.3, 20.7 | +26% |
| shared-expenses | start to end | 10.9, 9.0 | 16.5 | +66% |
| | to the first step plan | 2.9, 2.5 | 3.4 | +23% |
| | to `system-test` | 8.4, 7.3 | 12.6 | +61% |

The two runs apart, with planning reviews off by their own choice, took 20.4 minutes (`ticket-due-times`) and
15.2 (`shared-expenses`). Round 7's medium runs with them off at the harness's request took 15.2 and 16.8, and
14.2 and 12.9.

**R69. Held-out checks and the planning choice.** `shared-expenses`: 6 of 6 in both high runs.
`ticket-due-times`: 8 of 8, 8 of 8, 3 of 8 and 3 of 8. The two 3 of 8 are R62's choice again: a script an
operator must run, and a service that will not start switched on before it ("ticket T-0001 has no due time; run
scripts/backfill-due.js before ..."; "tickets are missing due times; run npm run backfill:due before setting
DUE_TIMES=on"). That is 2 of 4 on high, 2 of 4 on medium (R62) and 4 of 8 on Sol 6.2 in all, against 0 of 4 on
Sonnet (R62).

**R70. Two runs switched planning reviews off by themselves.** `sol-high-due-2` and `sol-high-expenses-1`. Each
one's first ShipLoop command was `workspace start --repo "$PWD" --planning-review none --improve-skill=<the
plugin's Improve card>`, sent right after it read the skill card. Nothing in the request or the harness asked
for it. The card's start section names the option twice, in a comment ("Optional (required with
--planning-review none): select the exact actual Improve skill at initialization") and in its list of run
options, and does not say that `stage` is the default or when `none` is meant. With R56's two that is four on
record: 3 of the 7 Sol 6.2 whole deliveries that were free to choose, and one terra run.

**R71. Reviews, plans and refusals.** One high run's reviews changed something (2 of 8); the other five's
changed nothing. Medium arm S: 1 of 8 and 0 of 8 on `ticket-due-times`, 0 of 8 twice on `shared-expenses`. First
step plans hold 3 to 7 criteria in one or two steps on high and 2 to 7 on medium. Refused commands: 2 to 8 a
run on high, 3 to 8 on medium. One work item in every run and no work opened after the build.

**R72. A known exposure in the Codex host**, found by the spec-elaboration session
(6c9055f1672a61ec43fc9776ba7728486bf66546): Codex 0.171.0 lists the owner's own skills to every session, the
harness's throwaway profile included. Every Sol run of this study ran that way, the medium base and this
baseline alike. None of round 8's six runs names a file under those skill folders in its events; of 43 Sol run
folders of rounds 4 to 7, one rehearsal does.

### Registered readings: the Sol 6.2 high baseline

- **Time.** `ticket-due-times`: high is slower, 16% above medium's mean from start to end. The medium cell holds
  a resumed run; at the first entry into `system-test`, which no run of either cell reached interrupted, high is
  26% slower. `shared-expenses`: high is slower (66%), on one high run against two, the other having recorded
  `none`.
- **Quality.** Held-out checks are the same on `shared-expenses` (6 of 6). On `ticket-due-times` they are 8, 8,
  3 and 3 of 8 on high against 3, 8, 3 and 8 on medium.
- **The planning choice**: 2 of 4 against 2 of 4. Counted; no reading was registered and none is taken.
- **Apart**: two of six runs recorded `none` by themselves.

### Findings

- **F51 (interim; four against four).** Sol 6.2 high made the planning choice that fails the held-out probes as
  often as medium did: half the time. Higher effort is not what moves it. (Corrected 2026-11-21 after review: no
  improvement was shown; three or four in six cannot show that effort has no effect.)
- **F52 (firm in direction; two requests).** High costs minutes for the same held-out results: about a sixth
  more on the planning-heavy request and two thirds more on the small one. On the ticket request planning takes
  the same time at both efforts and the extra is in the build.
- **F53 (firm as a count; the cause is inferred. Corrected 2026-11-21: this read "the cause is read in the runs",
  but the runs record no reasoning before the command, only that the card is all they had read).** Sol 6.2 switches planning reviews off by itself in 3 of the 7
  deliveries that were free to. It does it in its first command, straight from the skill card, whose start
  section names `--planning-review none` without saying which value is the default. Round 7's recommendation 3
  asked whether a run may do this; this is how often it does and why.
- **F54 (context only; ShipLoop 1.34.3).** On record Grok's four reviews before the build always changed
  something and by a lot, its step reviews seldom and by little, its end-of-item review never (R66). Nothing on
  today's ShipLoop says whether that still holds, or what a Grok delivery takes now (F41).

### Recommendation (owner's decisions; nothing built)

1. **Sol 6.2 high stays the owner's call; this is what it bought here.** No change in the planning choice, the
   same held-out results, and 16 to 66% more minutes. If that failure was the reason for the switch, effort is
   not the lever. The two that could be are unchanged from round 7: the spec stage saying how existing data gets
   its new field (the spec-elaboration session's work), and what the yardstick accepts.
2. **One sentence in the skill card would stop the unasked `none`** (corrected 2026-11-21 after review: a candidate
   remedy to be tested in round 9; the cause is not shown) (F53): say in the start section that
   `stage` is the default and that `none` is for a user who asks for it. It is smaller than round 7's pin and it
   treats the cause. It is a ShipLoop text change: the owner's go-ahead, a change note, the packet tests and an
   E2E round.
3. **Grok on the latest ShipLoop: one delivery, on the owner's word.** By the records about four hours and $60
   to $90. It gives the end-to-end time under the current step text and a full set of reviews to judge by the
   registered design above.
4. **The yardstick** (round 7, recommendation 6) now rests on eight Sol 6.2 deliveries: four take the
   operator-step reading.
5. **The Codex skills exposure** (R72) is with the owner through the spec-elaboration session. Every Sol result
   of this study is in the exposed condition.

### Limits

- One to four runs a cell. `shared-expenses` on high has one run in its cell, because the other chose `none`.
- The medium base ran hours earlier, with planning reviews pinned on, and one of its runs was resumed.
- All Sol runs, base and baseline, ran with the owner's own skills listed to the session (R72).
- The held-out checks of `ticket-due-times` count one planning choice five times (F46).
- No Grok run on the latest ShipLoop exists yet; R65 and R66 are an older version and were not judged.

### Correction, 2026-11-21: the baseline's time readings are withdrawn

The session running the Ratchet pilot reports ten stray test processes of its own at full CPU on this machine
from about 22:00 to 02:02 (recorded by the spec-elaboration session in
6a9731322ba8aecbe308f625570aa8370452d3b6; the fix is ffe1c68d6fe6299173b21cf47bc9304a3a0d1cf2). The
six Sol 6.2 high runs ran from 22:13 to 22:55, inside that window. Their medium base ran from 20:03 to 20:39,
before it, beside this study's own other runs. So R68 compared minutes taken under different loads. The minutes
stay as measured. The readings "high is slower" and finding F52 are withdrawn until the paired redo below.
Nothing else in the round rests on minutes: the held-out checks, the planning choice (F51) and the runs that
switched planning reviews off (F53) stand.

Related, from that session's pilot (7c4631e31913a02454367f79ff187cd4a2da0901): a different build loop on Sol 6.2
high read the same request the operator-step way and failed the same five probes from its first build to its
last, with its own tests green throughout. That is F46's reading again, on a third apparatus.

### Registered design: a paired redo of the timing (written and committed before any counted run)

- **Runs.** The baseline's build (ShipLoop 2.4.0, no overlay). Medium and high start together, so each pair runs
  under the same load: `shared-expenses` two medium and two high at once; `ticket-due-times` one medium and one
  high at once, twice. This round's Grok delivery runs beside them.
- **Time.** Per request, high against medium in mean minutes from start to end: slower at 15% or more above,
  faster at 15% or more below, otherwise no readable difference. The two milestones are reported. A run that
  records `none` by itself is compared only with runs of the same option.
- **Counts.** Held-out checks, the planning choice and the option each run records are added to R69 and R70.
- **Limits known before the run.** Two runs a cell, two requests, one evening.

### Results: the paired redo (run 2026-11-21 after 98ee2e64527a2445a60d1e155d49628c374bb00d)

**R73. The runs** (`evidence/effort-sol-paired.txt`). Eight whole deliveries on ShipLoop 2.4.0, medium and high
started together: `shared-expenses` two and two at 03:29, `ticket-due-times` one and one at 03:29 and again at
03:54. This round's Grok delivery ran beside them. Every run ended in one session with every harness verdict.
Two of the four medium runs recorded `none` by themselves, so each medium cell holds one run.

**R74. Time**, in minutes.

| Request | Measure | Medium | High | Change |
|---|---|---|---|---|
| shared-expenses | start to end | 11.1 (and 11.9 with reviews off by its own choice) | 17.1, 13.7 | +38% |
| | to the first step plan | 3.0 | 4.0, 3.8 | +32% |
| | to `system-test` | 8.3 | 13.3, 10.4 | +43% |
| ticket-due-times | start to end | 15.0 (and 13.7 with reviews off by its own choice) | 24.6, 25.2 | +66% |
| | to the first step plan | 3.7 | 5.0, 5.4 | +40% |
| | to `system-test` | 12.2 | 19.3, 19.7 | +60% |

**R75. Held-out checks and the planning choice.** `shared-expenses`: 6 of 6 in all four. `ticket-due-times`: both
high runs 3 of 8, the operator-step choice again; medium 3 of 8 for the same reason, and 8 of 8 in the run with
reviews off. That run was first graded 7 of 8: `suite` ended at the harness's time limit with no test result,
the lost verdict of R55, and passed 5 of 5 on the returned work (`runs-effort-paired/reruns.json`). The count on
ShipLoop 2.4.0 is now: Sol 6.2 medium 3 of 6, Sol 6.2 high 4 of 6, 7 of 12 in all; Sonnet 0 of 4.

**R76. Runs that switched planning reviews off by themselves**: two of the four medium runs, neither high run.
With R70 that is 5 of the 15 Sol 6.2 deliveries that were free to choose: 3 of 5 on medium, 2 of 10 on high.

**R77. The exposure of R72, seen.** Two of the eight runs' events name a file under the owner's own skill
folders, twice each (`sol-high-expenses-p1`, `sol-medium-expenses-p1`).

### Registered readings: the paired redo

- **Time.** High is slower on both requests: 38% on `shared-expenses` and 66% on `ticket-due-times`, each
  against the one medium run that kept planning reviews on. The medium runs with reviews off were faster still.
- **Quality.** The same on `shared-expenses`. On `ticket-due-times` high passed 3 and 3 of 8 against medium's 3
  and 8.
- This replaces the withdrawn readings of R68. F52 stands again, restated: **high costs about 40% more minutes
  on the small request and two thirds more on the planning-heavy one, for held-out results that are no better.**
  Unlike the withdrawn figures, planning is slower too (32% and 40% to the first step plan). Interim: one evening
  and one medium run a cell.
- F51 is stronger for it: the failing planning choice came in 4 of 6 high deliveries and 3 of 6 medium ones.
- F53's count is now 5 of 15.

Recommendation 1 of this round, restated on these numbers: on this evidence Sol 6.2 medium is the better
driver for these two requests, faster by a third or more (corrected 2026-11-21 after review: medium takes 28% and
40% less time than high; it is high that takes 38% and 66% more) and no worse on the held-out checks. The switch to
high is the owner's to keep or reverse.

### Results: the Grok delivery (run 2026-11-21 after 195fbf1d760dae26c0b65fa5a99b5cfa777f1ef5)

**R80. The run** (`runs-grok/census.json`). One whole delivery of `ticket-due-times` on Grok `grok-4.6` at
`xhigh`, ShipLoop 2.4.0 with no overlay: every harness verdict, 8 of 8 held-out checks, 240.6 minutes, $67.90,
732 turns. The session ended once, at `system-test`, and the harness resumed it at once. The paired Sol runs of
R73 ran beside its first hour. The plan held 12 criteria in one step; two commands were refused, both in `test`.

**R81. Where the four hours went.**

| Part | Minutes | Share |
|---|---|---|
| planning stages (intake to prepare) | 28.0 | 12% |
| the four planning reviews | 51.8 | 22% |
| step plan and test spec | 26.6 | 11% |
| implement | 7.8 | 3% |
| test | 14.6 | 6% |
| document | 7.6 | 3% |
| the step review | 11.2 | 5% |
| carry-forward, and its review | 6.4, 18.5 | 3%, 8% |
| system tests, and their review | 13.9, 9.6 | 6%, 4% |
| acceptance to handoff, and the release-plan review | 27.8, 15.7 | 12%, 7% |

All eight reviews: 106.8 minutes, 45% of the run. Building the item (implement, test, document) took 30 minutes.

**R82. What the reviews changed, from their pass logs.** Seven of the eight changed something: spec (193 lines),
test-strategy (71), step-plan (51), the step (8), carry-forward (108), system-test-author (73) and release-plan
(15). The plan review changed nothing. Not yet judged; the registered judges read them next.

**For context only (R65, another ShipLoop version):** the three recorded deliveries of the same request on the
same model took 339 to 364 minutes and $89 to $96, in plans of 8 to 11 steps. This one took about a third less
time and a quarter less money, in one step. One run, and the version is not the only thing that differs.

**R83. What the changed reviews were, by two judges** (`evidence/grok-reviews-judged.txt`; `judge-grok/`). Seven
packets from this run and six of round 7's as anchors, thirteen in a shuffled order. The judges gave the same
label to 12 of 13. On the anchors judge A repeated round 7's label on 6 of 6 and judge B on 5 of 6, so the scale
held and the reading below stands.

| Review of | Both judges | What it changed, in a judge's words |
|---|---|---|
| spec | substantive | "A large spec rewrite ... adds a request map and refines requirement clauses" |
| test-strategy | substantive | keeps `overdue=maybe` from being "rejected with 400 when the switch is off" |
| plan | no change | |
| step-plan | substantive | "the overdue filter must run before paging" and a setting "must reach createService" |
| the step | wording | comments reworded, an unused export dropped |
| carry-forward | substantive | "New tests cover per-priority backfill, the CLI omitting due and DUE_HOURS=0 being rejected" |
| system-test-author | substantive | a new system test that "the process backfills missing due times" |
| release-plan | records | standing facts about the checkout updated |

### Registered reading: the Grok delivery's reviews

- **The five reviews round 7 removed earn their place on Grok 4.6 xhigh**: 4 of 5 substantive by both judges
  (80%; the bar was 30%). Sonnet was 69% and Sol 6.2 medium 0% (R64).
- **The step reviews do not**: 0 of 1. **The two end reviews do**: 1 of 2, the end-of-item review.
- One run a group. As in round 7 this is the edit-yield rule: it says the reviews made substantive edits, not
  what a delivery would have lost without them (F45).

- **F55 (interim; one run).** On today's ShipLoop Grok behaves like Sonnet and not like Sol: the reviews before
  the build and of the system tests change what is built or checked, at 61 of the run's 240 minutes. With the
  whole item in one step, the end-of-item review is where tests were added (108 lines), which on the older
  version, with 8 to 11 steps, it never did (R66).
- **F56 (interim; one run).** After the fewest-steps change, a Grok delivery spends an eighth of its time
  building (30 minutes) and nearly half in reviews. Anything further on Grok's time is a question about reviews
  or about the 55 minutes of planning and step planning, not about the build.

## Round 9 (2026-11-21): from findings to changes: what is settled, and small tests first

### Question

Owner, 2026-11-21: "What should we improve?", then "Yes, plan small experiments before doing larger ones to see
if you can get fast iteration. Do we have sufficient evidence to conclude early?", and, with a review of the plan
by another model already running, "Do the review here in this context".

### Settled on the evidence in hand (no new run needed)

- Review defaults stay (round 7; today's Grok delivery had seven of its eight reviews change something).
- Sol 6.2 runs at medium, not high (R74: the paired redo).
- The planning choice that fails `ticket-due-times` is made in the spec stage, and four things do not move it:
  higher effort (F51), a second look by the same model (F46), a longer elaboration form and more test cycles
  (the Ratchet pilot's F20 and F24).
- The stale sentence in `references/behavioral-requirements.md` ("Store the proposed product behavior in the
  result `body`", while spec duty 2 writes requirements to `KNOWLEDGE/spec.md`) is fixed without a test.

### Two free cuts read for the plan (`evidence/plan-review-cuts.txt`)

**R78. Who stops processes by name.** In 88 run folders of rounds 4 to 8, a `pkill` or `killall` command is in
7 of 25 Sonnet runs, 0 of 57 Sol runs and 0 of 6 Grok runs. Sonnet also stops by process id in 16 runs, Sol in
9. So R60 was not a rare slip: it is a habit of one driver, in more than a quarter of its runs.

**R79. The spec decides the reading.** Of the twelve Sol 6.2 deliveries of `ticket-due-times` on ShipLoop 2.4.0,
eleven specs state how tickets already on file get their due times, and each one's held-out result follows it:
"an offline migration", "the operator's exclusive-writer maintenance window", "with the service stopped" in the
seven that pass 3 of 8; "when the new release starts", "before serving HTTP", "on startup", "before accepting
requests" in four that pass 8 of 8. The twelfth, which passes, prints no such line. So a spec read at the moment
it is accepted predicts the delivery, and a run can be ended there.

### The plan as first drawn

- A1: the skill card states that planning reviews default to `stage` and that `none` is passed only when the
  user asks (R70, R76: 5 of 15 Sol 6.2 deliveries passed it unasked).
- A2: one sentence telling builders to stop a process by its recorded process id, never by name.
- A3: the stale sentence.
- B: a spec-stage wording about refusals and manual steps the request does not state, the one the
  spec-elaboration session is drafting for duty 4.
- E1, for A1: the real case ended with the harness's stop file right after the run's first command, where the
  option is recorded: a minute or two a sample.
- E2, for B: the real case ended when its spec is accepted, read against the twelve specs of R79: three or four
  minutes a sample.

### Review of the plan, done in this session at the owner's word

Not an independent review: the reviewer wrote the plan. A max-effort review by Sol was started before the
owner's instruction (the runner's `sol` target calls `gpt-6.1-sol`, not 6.2) and was still running when this was
written; its report is added when it returns.

- **P0. B cannot be judged until the owner says which reading of the request is wanted.** The words allow both
  (R62). If an operator-run migration is acceptable, the seven deliveries are not wrong and the held-out checks
  are; then B is not a ShipLoop change at all. This is the first question to put.
- **P0. A2 as a sentence is the wrong tool.** R78 says it is a habit, and the Ratchet pilot's F22 says a duty in
  a prompt did not do what a script-run check did. ShipLoop's hooks already read the commands a session runs
  (`shiploop_keepalive.py`). A refusal there of `pkill` and `killall` by pattern, with the sentence as its
  message, holds every time; its test is a unit test on the seven recorded commands and needs no model. It
  changes what ShipLoop refuses, so it is the owner's decision; the sentence alone is the fallback.
- **P1. A1's cause is inferred** (corrected in F53 above). The card's "Read before choosing `--delegation`,
  `--lint` or `--planning-review`" makes choosing the model's job, so the wording should say whose choice it
  is: a run option is passed only when the user's request asks for it, and otherwise the defaults apply. If
  text does not stop it, the next step is the script: `workspace start` refusing a `none` the request does not
  name.
- **P1. E1 at ten samples shows too little.** 0 of 10 against the 5 of 15 on file is p = 0.06, and 1 of 10 is
  0.20. Fifteen samples over both requests, on medium, where the rate on file is 3 of 5.
- **P1. E2 holds only because of R79**, and its reading of each spec must be made blind to the wording that
  produced it. 0 of 8 against 7 of 12 is p = 0.01; 1 of 8 is 0.05; eight samples a wording, twelve if the first
  eight are mixed.
- **P2.** A3 needs no test. A1 and A3 go into one ShipLoop change with one E2E round; B stays apart.

### Revised plan

1. Ask the owner which reading of `ticket-due-times` is wanted (gates B and the yardstick).
2. E1 on a reworded card, fifteen start-only samples; registered before its first run.
3. A2 put to the owner as a hook refusal, with its unit test, or as the sentence.
4. B after 1: E2 with the duty-4 wording the spec-elaboration session's own review asked a trial of
   (`docs/spec-elaboration-journal.md`, section 24), eight samples a wording, read blind.
5. Whole deliveries only for what survives 2 and 4.

### Owner decision, 2026-11-21: the release fills the data file when it starts

Asked "For the ticket request, should the release fill the data file itself when it starts?", the owner
answered "Yes, fill at start". So the held-out probes of `ticket-due-times` stand as they are, and the seven
Sol 6.2 deliveries that make an operator run a migration first were wrong, not merely different. R62's and F46's
"the request allows it" is settled against that reading, round 7's recommendation 6 is closed, and the first P0
of the review above is answered: B is a ShipLoop question.

### The max-effort review, received

`review-r9/sol-max-review.md`, word for word; the brief is `review-r9/sol-max-brief.txt`. Sol at maximum effort,
read-only, 17 minutes; the runner's `sol` target calls `gpt-6.1-sol`. Its verdict: "Ship A1, A2 and A3. Pilot B
after narrowing its wording." Each pointer below was checked against the code it cites.

- **A1 is text only.** Not round 7's pin, which would also override a user who asks for `none`, and not a
  navigator refusal: nothing `new_state` receives says who asked. Its sentence is the one used.
- **A2 goes in `STAGE_RULES`** (`shiploop_prompts.py`), beside the scratch-folder rule, because every producer
  packet prints it. A hook is a separate decision (host coverage, quoting, indirect commands), and stopping by
  process id is not cleanup of a process's children. So this session's second P0 is withdrawn: the text now, the
  hook as its own question.
- **B needs its own wording.** The spec-elaboration session's arm G is about limits and "does not clearly
  address" a manual step. A wording must name it and must not become "never add a refusal". Arm N is narrowed
  to that.
- **E1** uses the harness's own `run.py --stop-after-start`, keeps the first attempted start command, and runs a
  fresh control beside the candidate.
- **E2** stops after the spec's review, keeps the spec as written and as accepted, runs a fresh control, sorts
  each spec into four classes with a quoted clause, and looks for a safeguard given up. The counts and the rule
  for going further are fixed before the first sample.
- **Eight statements of rounds 7 and 8 claimed more than their evidence.** Each is corrected or qualified in
  place: F42, F43's "earn their place", F44, F48, F51, F53, round 8's recommendation 2 and the closing
  recommendation of the paired redo, whose "a third or more" had the wrong denominator.

### Registered design: two small tests (written and committed before any counted sample)

**Builds.** ShipLoop 2.4.0 from a clean detached worktree of `main`, three copies: plain; arm C, with
`overlays/r9-card-run-options.json` applied to its `SKILL.md` by `card_patch.py`; and arms N and G, each with its
overlay on the spec duty (`overlays/r9-n-no-added-manual-step.json`, `overlays/r9-g-duty4-bounds.json`).

**E1: does the card wording change the first command?** Codex `gpt-6.2-sol` at medium, where the behaviour is
frequent enough to read (3 of 5 on file; 2 of 10 at high). Twelve fresh sessions on the plain build and twelve on
arm C, six of each request (`shared-expenses`, `ticket-due-times`), started in mixed batches with `run.py
--stop-after-start`. Read from each: the option of the first start command it attempted and the option the run
recorded. A session that starts no run is counted apart.
- *Reading*: arm C stops it if at most 1 of its 12 pass `none` and at least 4 of the 12 plain ones do. If the
  plain arm shows 1 or fewer, the test cannot read. Anything else: no effect shown. No extension.

**E2: does a duty-4 wording change what the spec decides?** `ticket-due-times` on Codex `gpt-6.2-sol` at high,
the owner's chosen effort. Eight fresh sessions an arm: plain, N and G, started in mixed batches and ended by
`stage_stop_samples.py` when the navigator enters `test-strategy`, so the spec's review has run where the run
has one. Kept from each: the spec as written and as accepted.
- *Classes*, by a reader who is not told the arm, each with the clause quoted: (1) the release prepares the
  file itself and starts; (2) a person must run something first and the release refuses to start until then;
  (3) unresolved or contradictory; (4) no accepted spec. An optional offline tool beside a working start is
  class 1. The same reader notes any safeguard given up, such as serving on a file that could not be saved.
- *Reading*: a wording changes the decision if at most 1 of its 8 is class 2 and at least 4 of the 8 plain ones
  are. Anything else: no effect shown. No extension. A wording that gives up a safeguard is not put forward
  whatever its count.
- G is the other session's arm, read here on the real case because its own trial is 36 deliveries; its
  result is reported to that session's journal by git, not acted on.

**Limits known before the run.** One request for E2 and two for E1; one model; a spec is a stand-in for the
delivery, good for this decision by R79 and for nothing else; small counts read only large effects; all Sol
sessions are shown the owner's own skills (R72).

### Results: the two small tests (run 2026-11-21 after 3d9fa01fcde71293e33d1c7e180d7274064fe96a)

**R84. E1, the card** (`evidence/e1-card-starts.txt`). Twenty-four fresh Sol 6.2 medium sessions, each ended by
the harness at its first start; all started a run. As shipped, 2 of 12 passed `--planning-review none` with
`--improve-skill` in their first start command, one on each request. With the patched card, 0 of 12, and none
passed any run option. Twenty-four samples took eight minutes.

**R85. E2, the spec wording** (`evidence/e2-spec-read.txt`, `spec-read/`). Twenty-four fresh Sol 6.2 high
sessions of `ticket-due-times`, eight an arm, each ended when the navigator entered `test-strategy`: 2.6 to 4.7
minutes a sample, all reached. The spec's review left the spec as written in 20 of the 21 runs that had one. Two
readers not told the arm gave the same class to 24 of 24, and neither flagged a safeguard given up.

| Arm | The release fills the file itself | A person acts first and the release refuses until then | Unresolved |
|---|---|---|---|
| as shipped | 7 | 1 | 0 |
| N (an added manual step or refusal) | 4 | 3 | 1 |
| G (the other session's seven sentences on limits) | 5 | 3 | 0 |

**R86. Why a writer chooses the operator step, read in the seven specs that did.** None cites safety and none
treats the refusal as something it is adding. Each ties the migration to the service's existing rule that one
process writes the data file: "With the sole writer stopped", "Only the existing file owner or its offline
replacement writes", "Production remains owned by the service operator". The specs that fill the file at start
keep the same rule the other way round: the service is that one writer, so it does the filling.

### Registered readings: the two small tests

- **E1: no effect shown.** The card arm had 0 of 12, but the as-shipped arm had to show at least 4 of 12 and
  showed 2. As a count, 0 of 12 against 2 of 12 is p = 0.48; against every as-shipped Sol 6.2 start on record
  (7 of 27) it is p = 0.08, a comparison that was not registered.
- **E2: no effect shown, for N and for G.** Neither wording lowered the count; both hold more operator-step
  specs than the as-shipped arm, and 3 against 1 of 8 cannot be read either (p = 0.57).

### Findings

- **F57 (firm for these two wordings on this request).** A sentence in spec duty 4 about limits, or about added
  manual steps and refusals, does not change what Sol 6.2 decides here. The writer does not see the operator
  step as added: it reads it out of the repository's own rule about who writes the data file (R86). A wording
  aimed at added refusals misses that.
- **F58 (interim).** The rate of the operator-step reading is not stable: 1 of 8 as shipped here against 7 of
  12 in the whole deliveries, on the same build, model and effort (p = 0.07). Pooled it is 8 of 20. So "7 of 12"
  was never a base to measure a wording against, and F51's counts by effort are weaker than they looked.
- **F59 (method; firm).** Ending a real run at the stage that decides cost 3 to 5 minutes a sample against 20
  for a delivery: 48 samples and both readings inside an hour. For this endpoint it answered in eight samples
  what the other session had planned 36 deliveries to ask of arm G.
- **F60 (interim).** The reworded card points the right way and is not shown to work. The rate of an unasked
  `none` on Sol 6.2 medium is 5 of 17 with these twelve, not the 3 of 5 of R76.

### Recommendation (owner's decisions; nothing built)

1. **Ship the three text corrections** (the card's default and whose choice a run option is; the
   stop-by-recorded-process-id rule in `STAGE_RULES`; the stale sentence), in one ShipLoop change with one E2E
   round, on the review's grounds. Say of the card change exactly what R84 shows: right direction, not shown.
2. **Put no spec wording forward.** Two were tried and neither moved the decision. What the specs say points
   elsewhere: the request, which does not say who fills the file, and the repository's own writer rule. A third
   wording would have to speak to that, and this round gives no evidence one would work.
3. **For the spec-elaboration session**, by this journal: on this endpoint arm G shows no effect in eight
   samples; its own endpoints are a different question.

### Limits

- Eight and twelve samples an arm read only large effects, and both as-shipped arms came in low.
- One request for E2, two for E1, Sol 6.2 only; a spec stands in for a delivery here and for nothing else.
- Both readers are one model; they agreed on every file.
- All sessions were shown the owner's own skills (R72).

### Owner decision, 2026-11-21: ship the three text corrections

On the recommendation above the owner answered "Ship the fixes". Recommendation 1 is carried out here.
Recommendations 2 and 3 stand as written: no spec wording is put forward.

**R87. The change** (commit `c138c061c9e7eb236a374198645362450e6f94aa`). One ShipLoop commit with a patch-level change note.

- The skill card and `references/run-options.md` say a run option is the user's to set, to pass one only when the
  user asks, and that planning reviews default to on (`stage`).
- `STAGE_RULES`, printed in every producer packet, gains the rule to record the PID of a background process and to
  stop it by that PID once it is confirmed to be the run's still, never by name or pattern. The long form in `COMMON`
  gives the reason: other work on the machine can match the same name. The rules block grew from 537 to 766
  characters.
- One sentence of `references/behavioral-requirements.md` sends the spec to `KNOWLEDGE/spec.md`; it had said the
  result `body`.

Four new assertions pin the texts: two in `test/shiploop-navigator-v4.test.py` and two test methods in
`test/shiploop-navigator-contract.test.py`. On the change: navigator-v4 18 tests, e2e-packet-anatomy 30,
packet-completeness 66, navigator-contract 127, and the quick tier with the changed files' suites, 33 suites, all
passing.

**R88. The E2E round** (`test/shiploop_e2e/LEARNINGS.md`, entry of 2026-11-21; `evidence/ship-round-readings.txt`).
Two whole deliveries from a clean checkout of the commit, started together, with no run option asked for.

| Delivery | Result | Case checks | Held-out | Minutes | Cost | Reviews (changed something) | Refusals, all recovered |
|---|---|---|---|---|---|---|---|
| `ticket-assignment`, Sol 6.2 high | pass | 3 of 3 | 18 of 18 | 16.5 | not reported | 9 (0) | 5 |
| `shared-expenses`, Sonnet 5.5 high | pass | 6 of 6 | none declared | 83.0 | $20.48 | 9 (6) | 9 |

**R89. What the round shows of the three texts.** Each session's one start command passed no run option and each
run records `stage`. Neither session used `pkill` or `killall`. The Sol session ran no shell `kill`. The Sonnet
session stopped a server four times, each time by a PID it had recorded, and twice ran `pgrep -f` only to look; one
match was a server outside the run, and nothing was stopped. The rule is in every producer packet (25 of 35 files and
28 of 38; the rest are Improve hand-offs and the `done` packet). None of the 14 refusals names a changed text.
Neither session opened the requirements guide or the options reference, so only the card and the packet rule were in
front of a builder.

**R90. The same case on the earlier text, one run each.** The Sonnet run of `shared-expenses` in the round of
2026-11-20 (same subject and effort, before the rule) against this round's, parsed the same way:

| Run | Stops by name | Stops by a recorded id | Background starts with no id recorded |
|---|---|---|---|
| 2026-11-20, without the rule | 3 | 1 | 5 of 6 |
| 2026-11-21, with the rule | 0 | 4 | 2 of 6 |

The spec-elaboration session found the pair first, with its own script; these counts are from a separate parse and
agree with its three and one.

### Findings: the shipped corrections

- **F61 (firm, for function).** The corrected texts break nothing on a whole delivery on two hosts: every verdict
  and every case check pass, and the held-out set where the case has one (18 of 18).
- **F62 (not shown; one lead).** Nothing in the round shows that a text changes what a session does. A `stage` start
  is what 20 of 27 earlier Sol starts already did, and a run with no stop by name is what 18 of 25 earlier Sonnet
  runs and all 57 earlier Sol runs did. The card's wording, tested alone, showed no effect (R84). The one pair in R90
  points the way the PID rule intends (3 stops by name before, none after, on the same case and subject), and one
  pair cannot carry more than that. Two of the three texts were not read by either builder (R89). The corrections
  ship on the review's grounds, that the texts were wrong or missing, and not on a measured effect.
- **F63 (observation, one run).** Looking by name still reaches other work. The Sonnet session's
  `pgrep -f "node.*server.js"` listed a server that was not the run's; the rule forbids choosing what to stop by
  name, and the session stopped nothing. None of its four stops shows a check that the PID was still the run's, the
  rule's second half, and nothing measures that. Two of its six background starts recorded no id, the rule's first
  half; both were a mutation script that ends by itself.

### Limits of the round

- One run a host on two small cases; no Grok run; not a comparison with the release before.
- The Sonnet delivery took 83.0 minutes where the same case and subject took 48.8 in the round of 2026-11-20. One
  run each on different days is not a comparison, and this journal times arms only in pairs started together.
- The readings in R89 were made from the events by a Sonnet worker and checked here by a second parse of the Claude
  events and by counting, in both event streams, the lines that hold `pkill` or `killall` outside the rule's text
  (none). The Sol events were parsed once; the spec-elaboration session's own reading of that run gives the same
  count of commands (279) and no stop.

### Publication

The fix was committed on the shared checkout's `main` at 08:02, and four commits of the spec-elaboration session were
then made above it. At 08:25 the Ratchet session's merge moved the remote `main`. So the fix was published from a
worktree cut from the remote `main` that merges the fix alone (merge `dc9922c4e9f2db0fa213408536e9909082710cca`): only this
session's commits are in the pushed range, and the other session's entries stay its own to publish. The release that
carries the fix, and the refresh of the hosts, are in the next section.

### Release: skill-craft 4.2.1, ShipLoop 2.4.1 (2026-11-21)

- **Before the push**, on the entry's commit: the quick tier pinned to the remote base, 37 suites in 202 seconds, all
  passing; the release boundary check; the release script's preflight (the entry comes after the fix).
- **One guarded push** published the fix, its merge, the journal entry and the release commit
  `62af08c43b0240f5c1ab20b4835634617951c03d` together, so no pending change note ever sat on the remote `main`. Six
  checks ran on the release tree inside the guard: plugin views in sync, marketplace packages, the release
  boundary against the base, the test catalogue, and the two changed suites (navigator-v4 18 tests,
  navigator-contract 127).
- **Hosts.** Claude Code and Grok each reported 4.2.0 to 4.2.1, and Codex lists 4.2.1 after its upgrade. On all
  three the installed `skills/shiploop` has no file that differs from the published tree (123 files).
- **A slip in the Codex refresh.** Codex's upgrade deletes every other version folder, and the loop that was to put
  them back did not run: zsh does not split an unquoted variable into words, so the three versions were read as
  one name. `3.3.0`, `4.1.0` and `4.2.0` were missing for about a minute and were then restored from their release
  commits (425, 309 and 309 files, each the commit's own count). The documented process check had printed nothing
  just before the upgrade, so no running process lost its folder; a run that was only paused would not show in a
  process list.
- **The published plugin, installed fresh** (`test/published-install-smoke.py`, no model): "PASS required published
  clean-install checks". No live session from the marketplace was run; R88 ran the same source from the checkout.
- **CI** on the release commit was still running when this was written: three of seven jobs done, all passing.
  Its result is not part of this record.
- **Still local.** The spec-elaboration session's five commits on the shared checkout's `main`. A message telling
  that session what was published was held by it and not delivered, so this section and the merge of the remote
  `main` into the shared checkout are how it will learn of it.

## Round 10 (2026-11-21): cheaper drivers: Sol back to medium, and Sonnet at medium against high

### Owner decisions, 2026-11-21

The owner asked what the study had improved and said: "One of the things I'd like to do is use a less expensive
model. If I could go down to medium for Sonnet, that would be great, and obviously use Sol at medium as well, as long
as the quality comes out the same." Offered the two steps, the owner answered: "Yes, switch Sol to medium and run the
Sonnet pairs".

- **Sol 6.2 runs at medium again** from this entry on, reversing the switch to high of 2026-11-20. The ground is the
  paired redo of round 8: high took 38% and 66% more time than medium and its held-out results were no better; the
  operator-step planning choice appeared at both efforts (3 of 6 at medium, 4 of 6 at high). The effort is passed on
  the command line (`--effort medium`); `test/shiploop_e2e/hosts.py` is unchanged. Sol high and Sol medium results
  stay separate cells.
- **Sonnet 5.5 at medium has never been run in this study.** Every Sonnet run so far was at high, so nothing yet says
  whether its quality holds.

### Registered design: Sonnet medium against high, two pairs (written and committed before any counted run)

- **Question.** Does a whole delivery on Sonnet 5.5 at medium pass the checks its partner at high passes, and what
  does it take in time and dollars?
- **Runs.** Four whole deliveries from a clean worktree of this commit (`run.py --source checkout`, the newest
  ShipLoop on `main`), all started together: `ticket-due-times` and `shared-expenses`, each at `--effort medium` and at
  `--effort high`, on `claude-sonnet-5-5`. No run option, no turn, time or resume cap; `--max-budget-usd 40` each. These
  are the two cases of round 8's Sol pairs.
- **Quality reading, fixed now.** For each pair: the harness's overall pass and the case checks passed (8 for
  `ticket-due-times`, 6 for `shared-expenses`), as recorded; nothing is regraded. "No drop shown" needs each medium
  run to pass every check its partner passes. A medium run that fails a check its partner passes is "a drop seen" and
  is reported with what failed. A failure with a cause outside the run that the records show (a lost port, another
  session's kill) makes that pair inconclusive; the first result is kept.
- **Time and cost.** Minutes start to end and dollars for each run, and medium as a share of high within each pair.
  Also read: planning reviews that changed something, refusals, and steps planned.
- **What two pairs can show.** Only a large drop or a large saving. "No drop shown" here does not make medium the
  default; it earns a larger round. The machine's load at the start is recorded, and other sessions share it.
- **Spend.** Earlier Sonnet high deliveries of these cases cost $2 to $20 and took 45 to 110 minutes.

### Results: Sonnet medium against high (run 2026-11-21 after 54e7476e128036efa1139a6bc6766f030f80d128)

**R91. The four deliveries.** All four started together at 19:10Z from a clean worktree of the registration, one
session each, no resume, planning-review option `stage` in all. Load was 25 on 18 processors at the start (another
session's work) and 15 when the last run ended. Run folders: `/Users/dadleet/e2e-runs-sdlc12/20261121/`.

| Case | Effort | Harness result | Case checks | Minutes | Cost | Turns | Plan | Reviews (changed) | Refusals |
|---|---|---|---|---|---|---|---|---|---|
| `shared-expenses` | medium | pass | 6 of 6 | 16.9 | $5.77 | 249 | 1 item, 11 criteria, 1 step | 8 (7) | 4 |
| `shared-expenses` | high | pass | 6 of 6 | 32.0 | $10.79 | 341 | 1 item, 14 criteria, 2 steps | 9 (6) | 7 |
| `ticket-due-times` | medium | pass | 8 of 8 | 23.9 | $6.24 | 242 | 1 item, 11 criteria, 1 step | 9 (2) | 3 |
| `ticket-due-times` | high | fail | 7 of 8 | 49.4 | $18.14 | 498 | 2 items, 11 and 12 criteria, 1 step each | 9 (7) | 16 |

Medium as a share of high: 53% of the time and 53% of the cost on `shared-expenses`; 48% of the time and 34% of the
cost on `ticket-due-times`.

**R92. The one failed check is the high run's, and it is the delivery's own fault.** The high `ticket-due-times`
delivery failed `suite`: its own tests, run by the harness from a copy of the tree, 155 pass and 9 fail ("its command
line runs from the extracted tree"). Run in place in the saved work folder the same tests pass 164 of 164; the
harness check rerun on the saved work fails the same way three times of three. So it is not load or a lost port: nine
of the tests that run added depend on the repository around them (they extract release 1.4.0 with git) and fail once
the tree is copied elsewhere. All six probes of the feature itself (migrate, restart, switch, rollback, off, cli)
pass in both runs, and both specs fill the data file at start, the reading the owner ruled right.

### Registered reading: Sonnet medium against high

- **No drop shown.** Each medium run passes every check its partner passes. The only failed check in the round is at
  high.
- **A large saving in both pairs**: about half the time, and a half to a third of the cost.
- Where the high runs spent more: more planning (the high ticket run planned a second work item; the high expenses
  run two steps), more refusals to work through (16 against 3; 7 against 4) and more review passes.

### Findings

- **F64 (interim, two pairs).** On these two cases Sonnet 5.5 at medium delivered the same passing checks as high in
  about half the time for half the cost or less. The registration set the bar for what this can carry: it earns a
  larger round and does not by itself make medium the default.
- **F65 (observation, one run).** More effort produced more product, not a better one: the high ticket run's second
  work item and its extra tests are where its one failure came from. This is the same direction as Sol in round 8,
  where high was slower and passed no more.
- **F66 (apparatus).** A delivery whose tests need the surrounding git repository passes in place and fails the
  `suite` check, which copies the tree. That check is right to fail it; a reader of a failed `suite` should rerun it
  on the saved work before blaming load.

### Limits

- Two pairs, one run a cell, two small cases, one day, a loaded machine. Sonnet's spread at high on these cases was
  45 to 110 minutes in round 7, so the time ratios are weak; cost and turns point the same way.
- Case checks are the yardstick. Nothing here reads code quality, and `shared-expenses` has no held-out set.
- Reviews changed more at medium on one case (7 of 8) and less on the other (2 of 9); not judged for substance.

### Owner decision, 2026-11-21: "Run larger round"

Offered a larger round or an immediate switch of Sonnet to medium, the owner chose the larger round.

### Registered design: Sonnet medium against high, six more pairs (written and committed before any counted run)

- **Runs.** Twelve whole deliveries on `claude-sonnet-5-5` from a clean worktree of this commit (`--source checkout`),
  no run option, no turn, time or resume cap, `--max-budget-usd 40` each: two more pairs each of `ticket-due-times`,
  `shared-expenses` and `ticket-assignment` (3 case checks and 18 held-out checks).
- **Starts.** `ticket-due-times` and `shared-expenses` run as two waves of four, each pair started together, the
  second wave when the first has ended. `ticket-assignment` leases a fixed port for its whole run, so two of its runs
  cannot overlap: its four runs go one after another, in the order medium, high, high, medium, beside the waves. Its
  pairs are therefore pairs for quality and cost only; their minutes are reported and not read as a ratio.
- **Quality reading, fixed now, over all eight pairs (these six and R91's two).** As recorded by the harness: overall
  pass, case checks and held-out checks; nothing regraded. A failed check is rerun on the saved work before it is
  counted, and a failure with an outside cause the records show makes that pair inconclusive (first result kept).
  - *Holds*: no medium run fails a check its partner passes.
  - *One such failure*: reported with its cause; the reading is "not settled".
  - *Two or more*: "a drop seen"; Sonnet stays at high.
- **Cost and time.** Dollars and turns for every pair; minutes as a ratio only for the pairs started together.
- **What it can carry.** Eight pairs on three small cases read a drop that happens in roughly a quarter of runs or
  more. If the reading is "holds", the recommendation to the owner will be to make medium the Sonnet profile and
  keep watching the checks on real runs; the default itself is the owner's.

### Owner decision, 2026-11-21, 14:27: Sonnet goes to medium and the round is stopped early

With five of the twelve runs finished, the owner asked "Do we really need to finish or can we conclude? Is there any
chance we would change our minds?" Told that the chance was small, that most of the cost was spent and that an early
stop on a favourable look weakens the record, the owner answered: "Yes, switch to medium and stop remaining runs".

- **Sonnet 5.5 runs at medium from this entry on** (`--effort medium`), with Sol 6.2 at medium (above). It is a
  command-line value; nothing in the harness changes. Results at high stay a separate cell.
- **The round registered in 2b349c22bb8fed6ffc6726111b6b5bdf517ce7b0 was not completed**, so its registered reading
  ("holds", "not settled", "a drop seen" over eight pairs) cannot be given and is not claimed.

### Results: what ran before the stop

**R93.** Five runs finished; five were ended on purpose through their stop files at 14:28 (the harness records them
STOPPED: high `ticket-assignment` at 47 minutes in `system-test-author`, and the four runs of the second wave at 15
to 16 minutes); two were never started. Stopped runs are not counted. Run folders:
`/Users/dadleet/e2e-runs-sdlc13/20261121/`.

| Case | Effort | Result | Case checks | Held-out | Minutes | Cost |
|---|---|---|---|---|---|---|
| `shared-expenses` | medium | pass | 6 of 6 | none | 12 | $4.21 |
| `shared-expenses` | high | pass | 6 of 6 | none | 42 | $15.10 |
| `ticket-due-times` | medium | pass | 8 of 8 | none | 27 | $9.32 |
| `ticket-due-times` | high | pass | 8 of 8 | none | 46 | $15.03 |
| `ticket-assignment` | medium | pass | 3 of 3 | 18 of 18 | 15 | $4.55 |
| `ticket-assignment` | high | stopped at 47 minutes | not graded | not graded | | |

**R94. Pooled with R91: four complete pairs and one medium run alone.** All five medium runs pass every check. Of
the four high partners, three pass every check and one fails one (R92). Medium's cost is 28% to 62% of its
partner's and its time 29% to 59%, in pairs started together.

### Findings

- **F67 (interim; the registered round was cut short).** In four pairs on two cases, and one more medium run on a
  third case with a held-out set, Sonnet 5.5 at medium passed everything, at a third to three fifths of the cost.
  No drop was seen. This is less than the registered eight pairs, and the stop came after a look at the results.
- **F68 (decision record).** The switch to medium is the owner's, taken on F67 with the limits stated. The check on
  it is the checks of real runs from here on; a medium run that fails where high would not is the signal to revisit.

### Limits

- Four pairs and a single; three small cases; case checks and one held-out set as the yardstick; code quality unread.
- The high `ticket-assignment` partner never finished, so that case has no pair.
- Stopping: my first command to end the launcher did nothing (a shell variable that zsh does not split into words,
  the second such slip today); the second ended it a minute later. Stray child shells of one stopped run were then
  ended by process id. `lifecycle.py cleanup` found nothing left in any folder.

## Round 11 (2026-11-21): do recurring refusals cost enough to fix their instructions?

### Owner decision, 2026-11-21

Asked "Based on learnings, is there anything else we should change", I named three candidates and proposed to start
with a free count of refused commands across the runs already on disk; the owner answered "Yes".

### Question and method (a reading of existing records; no run was launched)

Do the same refusals recur often enough, and cost enough time, to justify changing the instructions that precede
them? `refusal_census.py` reads `trace.jsonl` of every run folder of rounds 4 to 10 (`e2e-runs-sdlc4` to
`e2e-runs-sdlc13`): 160 runs with at least one command, 5,353 commands, on ShipLoop 2.3.0, 2.4.0 and 2.4.1, drivers
Sonnet 5.5 (high, medium), Sol 6.2 (medium, high, xhigh) and Grok 4.6 xhigh. A refusal is a command record with a
non-zero exit and an error text. Each goes into a named class by its text. Cost is the time from the refusal to the
next accepted check, complete or review command. That is an upper bound: real work done in between counts too.
42 of the 160 runs are whole deliveries (they reached the operations stage); the rest are stopped early, most of
them on purpose (the stop-early tests of round 9, the runs stopped in round 10).

### Results

- **R95.** 482 refusals, 9% of commands. Summed over all runs, the time after a refusal is 3.0 of 40.8 traced hours
  (7%).
- **R96.** The largest class is the mutation check (a seeded fault in a changed line survived the tests): 125
  refusals in 80 of the 97 runs that reached the test stage, median 30 s, 80 minutes in all. Failed test runs add 19
  minutes. Together they are 55% of the time after refusals. These are the product's check at work and not a
  misread instruction.
- **R97.** The instruction-shaped classes, by total time: a step proof naming a file that the base lacks and no
  earlier step declares (37 of 109 runs that reached step planning, once each, median 24 s, 18 minutes in all;
  29 of 51 on Sol medium against 5 of 33 on Sonnet high); the requirements file edited beyond the step's own lines
  at the document stage (33 refusals in 31 of 97 runs, median 12 s, 13 minutes); every other class is 4 minutes
  or less in all across the 160 runs.
- **R98.** The two I had named from memory: the test strategy without a unit or component row is in 15 of 47 runs
  that reached that stage, median 6 s, 2 minutes in all (Sonnet high 8 of 13, Sonnet medium 0 of 7). The step
  proof class is R97's first.
- **R99.** Per whole delivery, the median time after refusals that are not a failed test, a surviving mutant or a
  failed proof is 0.5 minutes on Sonnet medium (of 16.6, n=5), 0.5 on Sol medium (of 12.6, n=15), 0.3 on Sol high
  (of 19.2, n=11) and 1.4 on Sonnet high (of 48.2, n=10; maximum 8.1).
- **R100.** One class is commoner on the newest version: a plan concern whose `owner_stage` is not an allowed stage,
  in 8 of 14 runs on 2.4.1 against 3 of 31 on 2.4.0 (Sonnet 9 of 20, Sol 2 of 26). Each costs a median 5 s. The
  versions were run on different cases and drivers, so this is a description and not an effect of the version.

### Findings

- **F69 (firm as a count, for these cases and drivers).** Instruction-shaped refusals cost about half a minute of a
  13 to 17 minute delivery on the two drivers now in use, 3 to 4% at most, and the figure is an upper bound.
  Removing all of them could not save more than that.
- **F70 (decision, mine, routine).** No packet wording is proposed. A ShipLoop text change needs tests, a change
  note and an E2E round (about $10 to $20 and an hour); three wording attempts in round 9 showed no effect; the
  most this one could return is half a minute a run. The candidate "fix the instructions behind recurring
  refusals", which I gave the owner as second of three, is withdrawn on this count.
- **F71 (exploratory).** Most of the time after refusals is the mutation check doing its work. Whether its cost can
  fall without losing what it catches is a product trade-off for the owner and was not examined here.

### Limits

- Text classes are mine; 75 refusals at step planning fall in a mixed "other" class (18 minutes in all, median
  10 s), which no single wording would remove.
- The cost is elapsed time only; the tokens a refusal costs were not measured.
- The Grok row has one whole delivery. Small cases only (three services, one small app).
- Evidence: `evidence/refusal-census.txt`.

## Round 12 (2026-11-21): where a medium delivery's time and money go now, and what is left to try

### Owner decision, 2026-11-21

To round 11's result and my offer of a Grok effort test: "No, skip grok. Think deeply if there are any other
optimizations or experiments that would make this more complete or efficient". The Grok effort test is dropped.

### Question and method (readings of existing records; no run was launched)

On the drivers now in use (Sonnet 5.5 medium, Sol 6.2 medium), where do a whole delivery's minutes and tokens go,
and which part is still large enough to be worth an experiment? Three scripts read the run folders of rounds 7 to 10:

- `where_it_goes.py`: per driver, over whole deliveries (ShipLoop status done): stage time by phase, model calls,
  context size, token counts, what the tool results put in the context. From `metrics.json` and `result.json`.
- `context_origin.py` (Claude only): the context size at each model call, from `events.jsonl`, and what each step
  of growth came from. Its re-read total agrees with the bill's own count to 1% (36.48 against 36.11 million
  tokens on one run, 24.69 against 24.39 on another).
- `reset_ceiling.py` (Claude only): the same context series with the context set back to its starting size at
  chosen boundaries. It leaves out what a fresh session would have to read again, so it is an upper bound.

Prices are the ones the recorded bills imply: a least-squares fit over the 14 Sonnet 5.5 sessions with a bill gives
$0.10 per million tokens re-read from cache, $4.00 per million newly written, $10.00 per million output, with a
misfit under one cent on bills from $0.67 to $20.48.

### Results

- **R101 (time).** Sonnet medium, 5 whole deliveries on ShipLoop 2.4.1: median 16.7 minutes in stages, 141 model
  calls, 26 stage records, one build step. Planning (intake to test spec) 41%, the build 34%, after the build 21%.
  `implement` is 7.0% (70 s); `test` 15.4%; `step-plan` 11.3%; `document` 8.2%; each other stage is less. Reviews are 18%
  (153 s) and edited 18 of 44 reviewed results. Sol medium, 14 whole deliveries on 2.4.0: 13.0 minutes, 66 model
  calls, 23 stage records; planning 34%, build 40%, after 25%; `implement` 12.5%, `test` 13.1%; reviews 11% and
  edited 3 of 82.
- **R102 (context).** A session is one context from start to end. Of the Claude runs with a metrics file, 11 have
  one context window and no compaction; the 3 with two windows are round 7's runs that were continued after an
  interruption. Sonnet medium starts at a median 58,735 tokens and ends at 358,216; Sol medium 40,971 and 158,206.
  Each model call reads the whole context again: a median 32.2 million tokens re-read per Sonnet medium delivery
  (228,516 a call), 6.7 million on Sol medium (99,009 a call).
- **R103 (the bill, Sonnet medium, n=5, median $5.77).** Re-reading the session so far is 56% of it, text entering
  the session 24%, output 20%.
- **R104 (what is re-read, Sonnet medium, medians).** By share of re-read tokens: the model's own commands, which
  hold the files and results it writes, 25%; the start of the session (system text, tools, skill list, first
  prompt) 21%; stage instructions printed by ShipLoop 16%; shell reads 14%; skill cards loaded for reviews 7%;
  files read with the Read tool 6%; other ShipLoop output 3%; test output 1%. The skill descriptions of the whole
  plugin are 10,185 characters, about 2,600 tokens of the 58,735 at the start: not a lever.
- **R105 (ceiling of a fresh session).** With the context set back at two boundaries (before the build, after the
  build): at most 51% fewer re-read tokens and at most 29% off the bill (27 to 34% over the five runs). At every
  stage change: at most 75% and 42% (39 to 50%).
- **R106 (context only).** Round 7's three Sonnet high runs that were continued in a new session: two passed every
  check; `sonnet-high-due-L-2` is the run whose verdict was lost and run again (round 7's note). They show that
  a delivery can go on in a new session; they are not a test of it.
- **R107 (correction to what I told the owner on 2026-11-21).** I said a run's effort and review option are not in
  its result file. `result.json` has `effort`; the review option is in `invocation.json` as `planning_review`.
  The gap I named is one file's distance and needs no harness change.

### Findings

- **F72 (firm for these runs).** On a small change, writing the product code is 7% of a Sonnet medium delivery and
  12.5% of a Sol medium one. The rest is spread over 23 to 26 stage records, the largest 15%. No single stage is a
  large prize, which is F1 again on today's drivers.
- **F73 (firm as arithmetic, Sonnet).** More than half the bill is the session reading its own history again. The
  stage instructions are written to stand without that history (the main tenet: context clears between stages),
  but in these runs nothing ever clears it, so a run pays for the restated instructions and for the history too.
- **F74 (estimate; an upper bound, not a measurement).** A fresh session at two phase boundaries could take at most
  about 29% off a Sonnet medium bill, and one at every stage at most about 42%. What the fresh session must read
  again comes off that. The effect on time and on the checks is unknown: no run has tried it.
- **F75 (the gaps in this study's evidence, listed).** (a) Medium effort is supported on three small cases with
  one build step, by checks alone; nobody has read the code of a medium delivery beside a high one. (b) Every
  yardstick is one delivery: no run of this study changed a product that an earlier run delivered, though the
  harness has chains of such cases (`ticket-assignment` to `ticket-sla`, `user-listing` to `user-page-size`).
  (c) Nothing larger than one work item (F2, F7). (d) The main tenet is unexercised (F73).

### Candidates (the owner's decisions; nothing was run)

1. A blind reading of the code of the four medium and high pairs already on disk, by a judge that does not know
   which is which. It answers the owner's own condition for medium ("as long as the quality comes out the same")
   beyond the checks. A few dollars.
2. Medium on harder work: the four-change ticket chain on both drivers, and one larger request (`roundtable`).
   About $25 to $40 on Sonnet. It tests (a) and (b).
3. A fresh session at the two phase boundaries, Sonnet medium, paired with an untouched run, two pairs: about $20.
   The harness can end a run on purpose and continue it (`stop` file, `--resume-run`), so no ShipLoop change is
   needed to test it. It prices F74 and tests the tenet.
4. Planning reviews off on Sonnet medium, two pairs, about $20. F44's estimate at high was 10 to 12% of the time;
   at medium all reviews together are 18%.
5. Low effort, the rung below medium, two pairs a driver. Effort is the only lever that produced a large saving
   in this study; the risk to quality is larger than it was for medium.

Left alone, with the reason: the seeded-fault check (the ratchet pilot found it is what ShipLoop's extra time
buys); the stages after the build (21 to 25% of the time, an audit trail whose removal is a product trade-off, and
F23 says they changed no held-out verdict); the stage structure and the packet wording (rounds 1 to 11).

### Limits

- Small cases only; five Sonnet medium deliveries; the Sol rows are ShipLoop 2.4.0 and have no bill.
- The growth classes rest on text marks in commands and results; the split between a command and its result is by
  text length.
- The bill is the figure the host reports; whether it is what the owner pays depends on the owner's plan.
- Evidence: `evidence/where-it-goes.txt`, `evidence/context-origin.txt`, `evidence/reset-ceiling.txt`.

## Round 13 (2026-11-21): a blind reading of the code of medium and high deliveries

### Owner decision, 2026-11-21

Of round 12's five candidates the owner chose the first ("1"): a blind reading of the code of the medium and high
pairs already on disk.

### Registered design (written and committed before any judge ran)

**Question.** The owner's condition for the cheaper drivers was "as long as the quality comes out the same".
Rounds 8 and 10 answered it with checks (case checks, held-out probes). Does a reader who does not know which is
which find the medium product worse than the high one?

**Material (existing deliveries; no delivery is run).** The four complete Sonnet 5.5 pairs of round 10: in
`e2e-runs-sdlc12/20261121`, `sonnet-medium-due` with `sonnet-high-due` and `sonnet-medium-expenses` with
`sonnet-high-expenses`; in `e2e-runs-sdlc13/20261121`, `due-medium-2` with `due-high-2` and `expenses-medium-2`
with `expenses-high-2`. Two cases: `ticket-due-times` (a change to an existing service) and `shared-expenses` (a
product built from nothing).

**Packets.** `quality_packets.py <out> 20261121 <pairs>` writes, for each pair and each of two judges, a folder
with the request, the base tree when there was one, the two delivered trees as `X` and `Y`, and each one's diff
against the base. Which run is `X` is drawn from the seeded generator for judge A and reversed for judge B.
ShipLoop's own knowledge files (`docs/shiploop`) and git data are left out; any path naming a run folder is
replaced. The key stays outside the packets.

**Judges.** Two independent Claude Opus agents per pair (the Agent tool's `opus`), each given only its packet and
`evidence/quality-judge-brief.txt`. They read only: no command is run by a judge, so no judge can start or stop a
process (F47). Each returns, per side, a list of defects with file, line, kind (functional, test, maintainability,
scope), severity and a way to confirm it; four ratings from 1 to 5; and an overall choice of `X`, `Y` or no
material difference.

**Verification (mine, in the main session).** A judge's defect is a claim. I mark every claim from the blind
labels before opening the key:
- functional: I run the stated check against a fresh clone of that delivery. Reproduced, not reproduced, or cannot
  be checked.
- test, maintainability, scope: I read the cited lines (and for a test claim, break the code where that is cheap
  and see whether the test still passes). Confirmed or not confirmed.
The same defect from both judges counts once.

**Registered reading.**
- Primary measure: confirmed functional defects per delivery.
- A drop at medium is shown if medium has more confirmed functional defects than its high partner in at least 3
  of the 4 pairs, or if a confirmed functional defect of high severity is in at least two medium deliveries and
  in no high delivery. Otherwise: no drop seen by reading. Four pairs can show only a large difference, and the
  result will be stated that way.
- Described, not tested: the eight overall choices and whether the two judges of a pair agree; the ratings; the
  confirmed test, maintainability and scope findings; lines of source and tests.

**Known weaknesses, stated in advance.** The high deliveries are larger (round 10, F65), so a judge may tell the
sides apart by size; the brief says that more code is not better. Readers find what reading can find: a defect
that only shows under load or over time is out of reach. Opus judges share a model family with the builder.

**Extension, decided at the milestone.** The four Sol 6.2 pairs of round 8's paired redo
(`e2e-runs-sdlc10/20261121-paired`) can be read the same way with the same script, brief and reading. Whether to
run them is decided when the Sonnet pairs are read and their cost is known.

### Changes to the apparatus after registration and before any judge ran

- **A wrong citation in the registration commit.** The message of 00677819118968c3d885782a6bcdf9345e06383b cites
  f6f1489789fd41a284c9c5f6c01df3598cb58e97 as round 12. That is another session's merge, the tip of the remote
  when I resolved the hash from a moving name. Round 12 is eeb31fdca0058aad2b85b526a2256b79c4209c15.
- **The packet builder** stopped on the product built from nothing, which has no start commit. It now compares
  such a product with the empty tree. No packet had been read.
- **The brief** gained one sentence: comments may cite files under `docs/shiploop/`, which the packets leave out
  on purpose, and such a citation is not a defect. Without it a judge would have reported the citations.
- **The key and the clones** were moved out of the folder that holds the packets.

### Results (2026-11-21; eight judges, then my checks; `evidence/quality-reading.txt`)

- **R108 (the judges' choice).** Medium 3, high 3, no material difference 2. The two judges of a pair named the
  same side in one pair of four (`expenses-2`, high). Mean ratings, medium against high: correctness 4.25 and
  4.88, fidelity to the request 4.38 and 3.50, clarity 4.25 and 4.00, tests 3.62 and 4.62.
- **R109 (functional claims, each run against all four deliveries of its case).** Confirmed by the marking rule
  (`judge-quality/marking-rule.txt`, written before the key was opened): medium 5, in two of four deliveries;
  high 2, in two of four. By pair: `due-1` 0 and 0; `due-2` 1 and 0; `expenses-1` 0 and 1; `expenses-2` 4 and 1.
  Every one was rated low by the judge who found it.
  - Medium, `expenses-2` (four): a group id that is not valid percent-encoding is answered 500; `__proto__` as a
    group id is answered 201, then 404, then 201 again where the request says 409; a tie goes to a member whose
    name is a number and not to the member listed first; a member named `__proto__` is dropped and the balances
    no longer add up to 0. All four come from keeping groups and balances in plain objects.
  - Medium, `due-2` (one): for a ticket that a 1.4.0 file holds without a due time, the command line shows the
    default hours (24) where the service, given `DUE_HOURS_HIGH=10`, gives 10.
  - High, both `shared-expenses` deliveries (one each): a member name of two spaces is refused, where the request
    asks for "at least two distinct non-empty names". Both medium deliveries accept it. This is the letter of the
    request; without this item high has none.
  - Reproduced and not counted, by the rule: 400 for a malformed id (one medium delivery); no start on an empty
    data file (both medium `shared-expenses` deliveries; both high ones start).
- **R110 (test claims confirmed).** Medium: with the configured hours no longer passed to the store, all 148 tests
  of `due-2` medium still pass, while the other three ticket deliveries fail tests; a test whose title and input
  disagree; a test of the docs' wording and system tests that take the caller's environment (`due-1`); a test
  that runs the whole suite again (`expenses-1`). High: 9 of 164 tests of `due-1` high fail in a tree without the
  repository's history (round 10's F66, found again by both judges); an assertion on a constant and a count of
  files (`expenses-1`).
- **R111 (scope).** Before checking, the judges made 13 scope claims on high and 2 on medium. Confirmed on all four
  high deliveries: a second listing `overdue=false`; defaults, 413 and 405 answers, a versioned and audited data
  file; tests of test helpers and of release metadata. On medium: a 1,614-line copy of the old release kept as a
  test oracle, and a service that runs in memory without a word when `DATA_FILE` is not set.
- **R112 (size).** High has 1.1 to 4.4 times the tests of its medium partner (164 to 151, 175 to 148, 116 to 34,
  62 to 14) and 1.0 to 1.8 times the product lines.
- **R113 (what the earlier checks saw).** All eight deliveries passed every case check of round 10 except the one
  suite failure already known. None of the seven confirmed functional defects was caught by a case check or by
  the delivery's own tests.

### Registered reading

No drop at medium is shown: medium has more confirmed functional defects than its high partner in 2 of 4 pairs,
where the rule needs 3, and no confirmed defect is of high severity. Four pairs can show only a large difference.

### Findings

- **F76 (registered; interim).** By the rule set in advance, reading does not show that medium is worse.
- **F77 (description; interim, four pairs).** The two are not the same at the edges. Medium's products carry more
  small faults on unusual input (5 against 2, or 5 against 0 without the name check), most of them in the one
  leanest delivery, and their tests are fewer and rated a point lower. Where a judge scored the two sides differently for
  correctness (4 of 8 times), high was the higher each time.
- **F78 (description; agrees with F65).** High pays for it in scope: more product and tests than were asked for
  in every pair, and the lower rating for fidelity. Readers split evenly on which they would rather have.
- **F79 (about the yardstick).** The checks that carried rounds 8 and 10 cannot see this difference (R113). "The
  same passing checks" was true and was a weaker statement than "the same quality".
- **F80 (decision record).** Nothing is changed. Whether small faults on unusual input are worth two to three
  times the cost is the owner's call; F67's signal to revisit (a medium run failing a check on real work) has not
  occurred.

### Limits and conduct

- Four pairs, two small cases, one model family as builder and judge. A size difference is visible to a judge.
- I was not fully blind while marking: when the first packet build failed I saw file counts for `due-1`, and I
  knew round 10's suite failure, which the git claim matches. Functional marks are from commands.
- The judge of packet `due-1-A` reported running one read-only shell command inside its packet against the brief.
- The first suite runner did not end on one changed tree and I stopped it and its children by process id. The
  script now starts each run in its own process group with a 90 s limit, and every run was repeated with it.
- One plain run of `due-2` high failed 1 of 175 while the machine's load average was 39; six runs alone passed.
- The Sol 6.2 extension was run afterwards and is the next section.

### Extension: the four Sol 6.2 pairs (2026-11-21; decided at the milestone, as registered)

**Decision to run it (mine).** The Sonnet reading cost about 170,000 to 220,000 tokens and two minutes a judge and
found a lean that the earlier checks could not see, so the same question was worth asking of the other driver the
owner moved to medium. Same script, brief, marking rule and reading. Packets: seed 20261122, the four pairs of
`e2e-runs-sdlc10/20261121-paired` (`sol-medium-due-p1` with `sol-high-due-p1`, and so on). The brief's prompt
added "not even ls or diff" after the Sonnet judge that ran a shell command.

- **R114 (the judges' choice).** High 3, medium 2, no material difference 3. Mean ratings, medium against high:
  correctness 4.25 and 4.50, fidelity 3.75 and 3.75, clarity 4.25 and 4.00, tests 4.00 and 4.38.
- **R115 (functional claims, each run against all four deliveries of its case; `evidence/quality-reading-sol.txt`).**
  Confirmed: medium 5, in three of four deliveries; high 2, in two of four. By pair: `due-1` 2 and 1; `due-2` 2 and
  1; `expenses-1` 0 and 0; `expenses-2` 1 and 0.
  - All four ticket deliveries: a huge hours setting (`DUE_HOURS_LOW=2400000000`) is accepted at start and every
    ticket of that priority is then answered 500. One each; it does not separate the efforts.
  - Both medium ticket deliveries, neither high one: a due time does not survive a rollback and return. An urgent
    ticket (due in 4 hours) is made low under release 1.4.0, which drops the due time when it saves; back on the
    new release the ticket is due in 168 hours. Both high deliveries built a backfill option that takes the copy
    saved before the rollback and gives the 4 hours back; neither medium delivery has a way.
  - One medium `shared-expenses` delivery: a valid expense is refused with 400 once a member's total passes the
    largest safe integer. Its high partner, and both deliveries of the other pair, keep exact sums.
- **R116 (tests, scope, size).** Unlike Sonnet, Sol's two efforts are the same size (product lines within 5%,
  tests 122 to 125 and 123 to 123 on the ticket case, 5 to 8 on the other) and the judges made as many scope
  claims on one as on the other (5 and 5). Confirmed test faults are on both sides: a medium test started by a
  relative path (1 of 122 fails from another folder), a high suite that needs npm on PATH (3 of 123 fail without
  it). One medium delivery rewrote `docs/api.md` to say that two filters match either, which is what the base
  code does and not what its documentation said; its high partner left the sentence.
- **R117 (each round's checks on the other driver's products; described).** Sol's four `shared-expenses` products
  have none of the faults found in Sonnet's medium one. Sonnet's four ticket products, medium and high alike,
  move the due time after a rollback and return and have no way to keep it; all four refuse the huge hours
  setting at start.

**Registered reading, Sol.** A drop at medium is shown by the rule: medium has more confirmed functional defects
than its high partner in 3 of 4 pairs. The count turns on two readings, both made before the key was opened:
that losing a due time across a rollback is against "a later change of the hours or of the ticket's priority
does not move it", and that refusing a valid expense is a defect (one judge filed it as functional, the other as
scope). Without the second it is 2 of 4 and not shown.

### Findings of the extension, and of the round as a whole

- **F81 (registered; interim, four pairs).** On Sol 6.2 the rule shows a drop at medium. What separates the
  efforts is one thing found twice: at high, both deliveries foresaw that the old release drops the new field and
  built a way back; at medium, neither did. That is planning foresight and not coding care.
- **F82 (both drivers; description).** Over the eight pairs medium has 10 confirmed functional defects and high 4;
  medium has more in 5 pairs, fewer in 1, the same in 2. None is rated high. On Sonnet the difference is
  robustness on unusual input and the depth of tests; on Sol it is the rollback path. Neither is the kind of
  fault a case check or the delivery's own tests caught (F79).
- **F83 (contrary evidence).** Round 8's held-out probes graded these same four ticket deliveries on another
  point, whether the release works without an operator step first. The medium delivery that fills due times by
  itself at start passed 8 of 8 once its lost verdict was run again; the other three, both high ones among them,
  got 3 of 8 (R75). The readers preferred the high delivery of that pair, 2 of 2. The two yardsticks disagree
  about which design is right, and the probes do not look at the return after a rollback.
- **F84 (decision record).** Nothing is changed by me. The owner's condition was "as long as the quality comes
  out the same"; read closely, it does not come out the same, by a small margin in faults of low severity. The
  choice between the cheaper driver and the more careful one is the owner's.

### Limits of the extension

- Four pairs, the same two cases, the same judges' model family. The Sol runs are ShipLoop 2.4.0.
- I knew from the round's first half what kinds of fault to expect, and I chose to count the rollback item only
  where no way to keep the due time exists; that choice was made before the key was opened and is what gives
  3 of 4.
- In both first Sol pairs the medium run had also switched planning reviews off by itself (R76), so in those two
  pairs effort is not the only difference between the sides.
- In every Sol pair the seeded draw put the medium run as X for judge A. Judge B saw the reverse, so position is
  still balanced across judges, not within a judge.

## Round 14 (2026-11-21): what round 13's faults say about ShipLoop's own stages

### Owner decision, 2026-11-21

To round 13: "Keep med for both ; help me understand what we learned or what we could do to improve the prompts ,
sequence, stages, etc". Sonnet 5.5 and Sol 6.2 stay at medium, with round 13's result known.

### Question and method (a reading of run records and of the skill's source; no run was launched)

For each kind of fault confirmed in round 13: which ShipLoop stage could have caught it, and does that stage's
record say why it did not? Read: the step-plan criteria and the release-plan `consumer_checks` of the sixteen
deliveries, the plan's concern catalog (`shiploop_concerns.py`), the release instructions
(`shiploop_prompts.py`) and the fault check's operators (`shiploop_mutation.py`).

### Results

- **R118 (tests that pass only where they were written).** ShipLoop already has the gate: at release-verify it
  runs the `consumer_checks` in a clean copy of the returned tree with no Git history. The model writes those
  commands at release-plan. 15 of the 16 deliveries named the whole suite. One, `sonnet-high-due`, wrote
  `SKIP_ROLLBACK_TEST=1 npm test`: a switch its own tests read to skip the 9 that need the repository's history.
  The gate passed. The harness's `suite` check, which runs the suite as it is, failed that delivery (F66).
- **R119.** The clean copy is run from the project folder with the caller's PATH. Started from another folder, the
  suites of two Sol ticket deliveries fail 1 and 3 tests, and one of them fails 3 with no npm on PATH (R116).
- **R120 (the way back after a rollback).** The plan fills a row for each of fifteen concerns (`ui`, `api`,
  `messaging`, `state`, `migrate-before`, `migrate-after`, `switchover`, `concurrency`, `platform-services`,
  `scale`, `security`, `observability`, `config`, `performance`, `accessibility`). None asks what the previous
  release does with data the new one writes, or how the new one is entered again after going back. The rollback
  procedure is written at release-plan, after the build. Six of the eight ticket deliveries lose the due time on
  the return (all four of Sonnet, both of Sol medium); the two that keep it are Sol high (R115, R117).
- **R121 (tests of things that are not the product).** The tests the judges called brittle or out of scope trace
  to ShipLoop's own records. `TC_26`, which runs the whole suite again, confirms a step-plan criterion marked
  `executed`: "the suite runs under node --test, prints every TC ID". The count of test files confirms "the suite
  is discoverable by node --test". The test of the wording of `docs/operations.md` confirms "The rollout and
  rollback order is documented". The test of `package.json` against the changelog confirms a criterion on the
  version. The tests of the test helpers are the `prepare` stage's proof of its harness. Six of the eight Sonnet
  deliveries carry at least one such test; the judges reported none in Sol's eight.
- **R122 (odd input).** The four faults on unusual names and ids are in one delivery of sixteen. No stage record
  asks about such input. Not traced further.
- **R123 (wiring).** The fault check changes single lines by text (comparisons, literals and the like). Leaving an
  argument out is not among its changes, so the setting that never reached the service (R110) was outside it.
  One delivery.

### Findings

- **F85 (firm for these sixteen).** A gate whose command the model writes can be met by weakening the command. It
  happened once in sixteen, and the weakened run was accepted without a word.
- **F86 (interim).** Planning asks nothing about going back. The fault is in six of eight deliveries, and what made
  up for the missing question was effort on one driver (Sol high, twice).
- **F87 (firm as a trace; Sonnet).** Part of what readers called unasked scope and brittle tests is ShipLoop's own
  doing: criteria about the suite, the documents and the release, marked `executed`, become permanent tests in
  the product's suite.
- **F88 (decision record).** Nothing is changed. The candidates below are the owner's; each ShipLoop change needs
  tests, a change note and an E2E round.

### Candidates (the owner's decisions; nothing was run)

1. **The clean-copy gate.** Have release-verify run the recorded regression command itself in the clean copy, and
   refuse when more tests are skipped there than in the work area. Optionally start it from another folder.
   Script-run, no wording. Catches R118; from another folder also R119.
2. **A concern row for the way back.** A sixteenth row in the plan's catalog: what the previous release does with
   what this one writes, and how this one is entered again. A row to fill, which is the form the ratchet
   session's amendments found to work, not a sentence. Test: the ticket case with and without the row, read with
   `quality_checks/rollback.js`.
3. **Where the proof of a non-behaviour criterion lives.** A criterion about the suite, a document or the release
   is confirmed by a check row in the run's records, not by a test added to the product; the `prepare` stage's
   proof of a harness stays out of the product's suite. Three wording attempts in round 9 showed no effect, so
   this needs a field or a refusal, and a count at step-plan (F59's method) before and after.
4. **The yardstick.** Add round 13's checks to the E2E cases as observations (the return after a rollback, odd
   names and ids, the suite from another folder), so that the next comparison sees what rounds 8 and 10 could
   not (F79).
5. From round 12, unchanged: a fresh session at the two phase boundaries (at most 29% of a Sonnet bill);
   planning reviews off on Sol (3 of 82 reviewed results edited).

Not proposed: a question about odd input (one delivery of sixteen, and wording has not moved behaviour here); a new
kind of change for the fault check (one delivery).

## Round 15 (2026-11-21): building round 14's candidates: the review, what is built, what is tried first, what is not built

### Owner decision, 2026-11-21

To round 14's four candidates: "Yes, do these".

### Review before building (Sol 6.2 at max effort; `review-r15/`)

The owner's order for a ShipLoop change is a max-effort review of the intention and the design, then weighing it,
then building. The brief and the verbatim review are in `review-r15/` (served model gpt-6.2-sol, effort max, no
fallback; a read-only export with no personal names). Its verdict: "C1–C4 should all be built differently." What
it said, what I checked in the code, and what I decided:

- **C1, the clean-copy gate.** *Review:* equality of commands is a hint, not a proof: a setting in front can
  select a legitimate smaller profile; the return plan may exclude tests; a wrapper escapes; an unreadable count
  must not pass once a count is bound; both exits must be named. *Checked:* `verify` gives the outer stages no
  floor (`held = {}`), by the decision of 53ab8b788de56feb3d28c598146331cd51e006b3 (its audit: no revise
  there, and a union across items dead-ends on a consolidation; "open, needs an owner decision"); `judge` reads a
  count on a `check` row and Node's reader leaves skipped tests out of `ran`; `send-back` from release-verify
  reruns release-plan (`OUTER_SEND_BACK_TO`) and `add-work` queues a corrective item. *Decision:* build the floor
  with four corrections: the latest accepted work-area count and not the most; an unreadable count is refused
  where a count is bound; the refusal names `add-work` and `send-back`; the release-verify packet prints each
  bound count and the release-plan duty states the rule. Not adopted: a new field that declares a full replay. One
  live run in sixteen does not earn a new field (the owner's rule on guards), and the two exits cover the cases
  the review names. The limits (a wrapper, a different spelling, an equal count hiding a changed selection) are
  documented and pinned by a test.
- **C2, the way back.** *Review:* do not add a concern; a sixteenth id rejects saved plans on load, `rollback`
  already names release-plan's undo of the source return, every plan pays one more answer, and a row can be filled
  while the product stays as it is; use the existing `state` row. *Checked:* the result normaliser calls
  `shiploop_concerns.canonical_plan` on each accepted plan and it refuses a plan missing any current id, so saved
  runs would stop loading; the plan duty prints only the ids (the one-line questions in `CONCERNS`, from
  fff7fa13fd537d7152e9d71a476b716e4f5e6839, are never shown to the model), so a row's meaning has to be said in
  the duty. *Decision:* no new row. One sentence in plan duty 3 on the `state` row, as a candidate on its own
  branch (44d8dea03f571f54e0a6c5f232573f47a6d58100), tried before it ships (below).
- **C3, tests of things that are not the product.** *Review:* wording alone is unlikely to move it; the step-plan
  template seeds every open assumption as an `executed` criterion on the focused row and shows no `searched`
  one; a `check` row can run before the document stage writes the wording it expects; relabelling behaviour as a
  search would lower rigour. *Checked:* the template does so on purpose, by measured decisions of 2026-10-31
  recorded in its comments (a `check` row naming a criterion "taught 22 of 445 executed criteria to rest on one";
  10 of 11 open items were met with a check that settled nothing). The census below puts the strict class at one
  criterion in 2 of 5 Sonnet medium runs and none on Sol. *Decision:* **not built.** The prize is one brittle test
  in under half of one driver's deliveries; no trial of affordable size can show a move from 2 in 5; the earlier
  measured decisions pull the other way; and the risk is to rigour. It stays a described finding (F87).
- **C4, the yardstick.** *Review:* the probes need the harness's own server handling, a check that the old
  release's writes survive a restore, like-for-like suite runs, and calibration on the saved deliveries; and an
  edit to `cases.json`, `checks/` or the harness's top-level code changes the digests that make runs comparable.
  *Checked:* `boundary.evaluator_files` is the top-level `*.py` and `*.cjs`, `oracle_files` is `checks/` and
  `fixtures/`, and the SPEC says "a harness or oracle change is an experiment of its own". *Decision:* build the
  observers as an opt-in tool outside that boundary, calibrated on the sixteen saved deliveries, changing no
  verdict and no digest. Wiring them into every run is left as the owner's later decision.

Also taken from the review: qualify each change on its own before the batch round; C1's trigger cannot be waited
for in live runs (1 in 16), so it is seeded through the real gate in a test; one correction to round 13's wording
(the nine tests that need Git history were caught by the harness's own suite check; the fourteen are the faults in
behaviour).

### Baselines from existing records (no run)

- **Plan rows** (`plan_rows.py`, six saved plans of the ticket case on the released text). Both Sol high plans
  decide to keep due times across a rollback ("Keep due-bearing snapshot to recover through old binary writes";
  "For re-upgrade after 1.4.0 rewrites, merge retained due values from a stopped-service backup"), in their
  `migrate-after` rows. Neither Sol medium plan nor either Sonnet medium plan does; one Sonnet medium plan
  records the loss as documented.
- **Criteria** (`criteria_census.py`, 13 runs). By a broad word pattern 8 of 13 runs have an `executed`
  criterion about a document, the suite or the release; read by hand the strict class (a search inside a test)
  is 2 of 5 Sonnet medium runs and 4 of 9 Sonnet runs, one criterion each, and 0 of 4 Sol medium runs. Several
  hits are a real requirement of the request ("no npm dependencies").
- **Delivered tests** (`meta_test_census.py`, the sixteen deliveries): marks in 6 of 16, all Sonnet; the pattern
  misses one test the judges confirmed (it reads its document through a helper), so it is a list to confirm.

### Registered trial for C2 (written and committed before any run)

**Question.** Does the sentence on the `state` row change what a plan decides about data that must survive going
back to the previous release and returning?

**Arms.** Control: the plugin built from the remote main as it is. Candidate: the same with only the sentence
(44d8dea03f571f54e0a6c5f232573f47a6d58100). Each built with `build_arm.py` from a clean worktree.

**Samples.** The ticket case (`ticket-due-times`), ended when the run enters `prepare` (the plan and its review
are then accepted), with `stop_at_stage.py`. Two samples an arm on each driver now in use: Claude Code
`claude-sonnet-5-5` at medium and Codex `gpt-6.2-sol` at medium; eight samples. `--planning-review stage` is
passed to all eight, because two of four Sol medium runs on file switched the reviews off by themselves (R76).
Control and candidate samples start together.

**Reading.** `plan_rows.py --blind` prints each plan's `state`, `migrate-before`, `migrate-after` and
`switchover` rows under shuffled labels. I label each plan before opening the key:
- **keeps**: the plan decides a way for a due time to survive going back and returning (a saved copy that is
  merged or restored, or another mechanism);
- **accepts**: the plan says due times are recomputed or lost on the return, documented or not;
- **silent**: no row says what happens on the return.

**Rule.** The sentence goes on to whole deliveries if at least 3 of 4 candidate plans are *keeps* and at most 1 of
4 control plans is. Otherwise it is not shipped and its branch is deleted. A plan that only *accepts* is not what
the sentence is for: it changes no product.

**If it goes on.** The batch round's ticket deliveries are its product test: shown if at least 3 of 4 keep the
due time across a rollback and return and keep what the old release wrote, where 0 of 4 medium deliveries on file
do. That round is registered separately, when the build is final.

**Limits, stated in advance.** Two samples a cell. The request does not say a due time must survive a return, so
"keeps" is the stricter reading of "set once" and "keep them from then on", and a plan that accepts the loss in
writing is not wrong by the request. A stopped Claude sample records no cost.

### Results of the trial for C2 (2026-11-21; `evidence/state-row-trial.txt`)

- **R124.** Eight samples reached the plan in 3.6 to 5.3 minutes each, but for one (see the apparatus note). The
  four Sonnet samples cost about $6 by the fitted prices (a stopped Claude run records no cost).
- **R125 (labels written before the key was opened).** Control: silent 4 of 4. Candidate: keeps 2 of 4, accepts
  2 of 4, silent 0. By driver: both Sol 6.2 medium candidate plans keep ("keep an enriched snapshot to recover
  fixed deadlines during roll-forward"; "Restore preserved due from pre-rollback snapshot keyed by stable ticket
  identity, keeping newer state"); both Sonnet 5.5 medium candidate plans accept ("1.4.0 ... its next save drops
  it; returning to 1.5.0 backfills again").
- **Registered reading.** Not met: keeps in 2 of 4 candidate plans, where the rule needs 3. By the rule the
  sentence does not go on to whole deliveries on this evidence.
- **F89 (described, not the registered reading).** The sentence is answered every time: 4 of 4 candidate plans
  say what happens on the return and 0 of 4 control plans do. What they decide differs by driver. On Sol the
  answer is the one the two high-effort plans gave unasked (R120's baseline); on Sonnet it is an explicit
  acceptance of the loss, which changes no product.
- **Apparatus note.** The session of `candidate-sonnet-1` halted its first ShipLoop run, which it had started
  with a reworded request, and started another with the request as given. `stop_at_stage.py` watched the first
  run folder only, so that sample ran on for 14.3 minutes, past the build, until I ended it by its stop file. Its
  accepted plan is read like the others. The sampler and `plan_rows.py` now look at every run folder of a sample;
  the second wave used the corrected sampler. My first launch started nothing: a zsh slip in the sample names
  (`$n:t` is a modifier), seen at once and corrected before any run.

### C1 as built, and the observers (C4)

- **C1** is one commit on a candidate branch (5fc4a220ae797cbcdf4ae7d1104720b50ebae1d1): the code, 12 tests (10
  unit, 2 through the real gate, one for each exit), the packet and duty lines, the reference text and the change
  note. Its own test file passes whole (234), with the suites that pin packet text. It is not on main until the
  batch round below.
- **C4** is `test/shiploop_e2e/observers/`: `ticket_return.py` (the return after a rollback, the ordinary way
  and with the delivery's own restore option, with a check that what 1.4.0 wrote survives),
  `expense_inputs.py` (odd names, ids and sums), `suite_elsewhere.py` (the suite without npm and from another
  folder, the same files each time) and `observe.py`. They use the cases' own server handling from `checks/`,
  change no check and sit outside the files a run's `boundary` digests. Calibration on the sixteen deliveries of
  round 13 (`evidence/observers-calibration.txt`) gives round 13's findings again: both Sol high ticket deliveries
  keep every due time with their restore option and the other six move one of eight; one delivery has the four
  faults on unusual input; the two suites that lean on npm or the working folder show it. A name of two spaces,
  400 against 404 for a malformed id, and a total past the largest exact integer are recorded and not judged.

### Registered batch round (written and committed before any run)

**Two builds.** A: main with C1 (5fc4a220ae797cbcdf4ae7d1104720b50ebae1d1). B: A with the sentence
(b6287b09bbb55df20e7729d15fc90de630550031).

**Why B is run at all.** The first rule was not met, and I am not rescoring it. The split by driver is a question
the rule did not ask: on the one driver whose plans changed to *keeps*, does the product follow? This is a second
test of the same sentence, chosen after seeing the first, and should be weighed as that.

**Runs.** Eight whole deliveries at medium effort, no run option, no turn or time cap (Claude runs with
`--max-budget-usd 40`), from clean worktrees of the two commits, in two waves of four started together.
- Wave 1: `ticket-due-times` on Codex `gpt-6.2-sol`, builds A and B, twice each (the paired test).
- Wave 2: `ticket-due-times` on Claude `claude-sonnet-5-5`, builds A and B, once each; `shared-expenses` on
  build B, once on each driver.

**Reading 1, the release's E2E round (C1).** Every harness verdict and case check of each run. C1 is accepted if no
ordinary delivery is refused wrongly by the count rule: each release-verify record is read, and a refusal by the
rule is judged by hand (right, or a false refusal). The rule's own trigger is seeded in its tests, not waited for.

**Reading 2, the sentence (C2).** `ticket_return.py` on the four Sol ticket deliveries. The sentence is merged if
both B deliveries keep every due time across the rollback and return, with what 1.4.0 wrote (by themselves or with
their own restore option), and neither A delivery does. Otherwise it is not merged and its branches are deleted.

**Described.** The observers on all eight deliveries; each run's recorded planning-review option; the Sonnet A and
B ticket deliveries' return behaviour.

**What is released.** Build B if reading 2 holds, else build A. Each has whole deliveries on both hosts in this
round (A: three; B: five).

**Limits, stated in advance.** Two deliveries a cell. Runs side by side, so no time is read. The yardstick for
reading 2 is the stricter reading of "set once" (round 15's registration). Sol at medium may switch planning reviews
off by itself; it is recorded, not pinned, because the release's round uses the defaults.

### Results of the batch round (2026-11-21; `evidence/batch-r15.txt`)

Eight whole deliveries at medium effort, defaults, in two waves of four started together; the machine's load
average was 15 to 31 throughout (another session's work), so no time is read.

| Run | Build | Driver, case | Verdicts | Case checks | Final check as release-plan recorded it | In the clean copy |
|---|---|---|---|---|---|---|
| `sol-A-due-1` | A | Sol, ticket | all pass | 7 of 8 | `[regression] npm test` | ran 122, floor 122 |
| `sol-A-due-2` | A | Sol, ticket | all pass | 8 of 8 | `[regression] npm test` | ran 121, floor 121 |
| `sol-B-due-1` | B | Sol, ticket | all pass | 3 of 8 | `[regression] npm test` | ran 121, floor 121 |
| `sol-B-due-2` | B | Sol, ticket | all pass | 8 of 8 | `[regression] npm test -- --test-reporter=spec` | ran 120, floor 120 |
| `sonnet-A-due` | A | Sonnet, ticket | all pass | 8 of 8 | `[check] npm test` | ran 163, floor 161 |
| `sonnet-B-due` | B | Sonnet, ticket | all pass | 7 of 8 | `[check] node --test` of three test files | ran 26, no floor |
| `sonnet-B-expenses` | B | Sonnet, expenses | all pass | 6 of 6 | `[check] node --test` | ran 26, floor 26 |
| `sol-B-expenses` | B | Sol, expenses | all pass | 6 of 6 | `[regression] node --test` | ran 6, floor 6 |

Each run kept planning reviews on. The three Sonnet runs cost $8.01, $8.50 and $5.72.

- **R126 (reading 1, as registered).** No delivery was refused by the count rule, rightly or wrongly. The rule bound
  a floor in seven of eight deliveries and each met it, twice on a row recorded as an exit-code `check`.
- **R127 (what the rule did not see).** `sonnet-B-due` passed release-verify and fails the harness's own suite check:
  in a copy of the tree its tests are 144 passing and 3 failing. Its system test takes release 1.4.0 from the
  repository's history (`git archive 2db433e src`), which a copy does not hold (run again alone: "fatal: not a git
  repository"). release-plan recorded as its one consumer check `node --test` of three unit-test files, 26 tests,
  where the work area's regression command `npm test` had run 145. That is another command, so the rule held it
  to nothing. It is the fault of round 14's R118 by another route: a subset of the files in place of a setting
  that skips. Two of the six Sonnet deliveries of this case on file now have a suite that cannot pass in a copy, and
  each time the consumer check was written to go round it.
- **R128 (what my own text did).** Build A's release-plan duty ended "Record a check that is meant to run less by
  its own command". This delivery did exactly that. One run, so not shown, but the sentence pointed at the way
  round.
- **R129 (reading 2, as registered).** The sentence is not merged. Of the two Sol deliveries with it, one keeps
  every due time across a rollback and return (with its own restore option, and with what 1.4.0 wrote), and one
  moves it; neither delivery without it keeps it. The rule needs both.
- **R130 (described).** The one delivery that keeps the due times is also the one that fails five case checks: its
  service will not start with `DUE_TIMES=on` until an operator has run its backfill command. On file, every Sol
  delivery that keeps due times across a return has that start-up behaviour (three of three: round 13's two at high
  effort and this one). Both Sonnet plans with the sentence accept the loss in writing and both products move the
  due time, as do both Sonnet products without it.
- **R131 (one failed check that is not the product's).** `sol-A-due-1`: `pristine`, the base's own tests run in the
  base, lost a connection in one test ("socket hang up", 1.7 ms in). That is this fixture's port collision with
  other projects' servers on this machine (R55). Run again alone five times on the saved work the check passes
  each time, 117 of 117. The recorded FAILED stands and both are reported.
- **R132 (the observers, on all eight).** No delivery has a fault on unusual input. Suites: `sol-A-due-2` fails one
  more test from another folder; `sonnet-B-due` fails the three above everywhere outside its work area.

### Findings of the batch

- **F90 (firm for these 24 deliveries).** The model decides what release-verify runs, and when it knows its suite
  cannot pass in a clean copy it writes a check that can: a setting once, a subset once. Comparing the written
  check with the recorded command cannot close that; only running the recorded command can. This is what the owner
  approved in the first place.
- **F91 (registered; two tests).** The sentence on the `state` row is answered every time and does not, by either
  rule, do what it was for. Where it changes a product it brings a start-up design the case's checks reject (R130).
  Not merged. Its two branches are deleted (2026-11-21), so the commits this journal cites for it,
  44d8dea03f571f54e0a6c5f232573f47a6d58100 and b6287b09bbb55df20e7729d15fc90de630550031, are no longer reachable;
  its text is kept in `evidence/state-row-sentence.patch`.
- **F92 (about my first build).** A rule with a named way round is read as a way round (R128). A packet should
  state what will be run, not how to record something that will not be.

### C1 rebuilt: ShipLoop itself runs the step plan's regression command in the clean copy

The rebuild is one more commit on the candidate branch, 62676fc0e0dacb0ca8febd7f6f2424684c707b47, on top of the
first build (5fc4a220ae797cbcdf4ae7d1104720b50ebae1d1). Neither is on main until the confirmation round below
is read.

- **What is run.** Where release-verify's commands run in a clean copy of the returned result and release-plan
  recorded at least one consumer check, ShipLoop runs the checks as recorded and then each regression command of the
  last work item whose step plan records one that runs on the checkout, where no check already is that command (the
  same text). The packet's list and a refusal mark each as "the step plan's regression command, added by ShipLoop".
- **The count.** Each of those commands, added or written as a check, is held to the count of its latest passed run
  in the work area under an accepted stage, with the record named, and its count must be readable. Any other
  consumer check is the model's own and is held to nothing. Settings in front of a command are no longer stripped:
  the suite behind a setting is the model's own check, and the added command holds the suite.
- **Two exits, by what is wrong.** `send-back` reruns release-plan when the release plan lacks a step the suite
  needs in the copy (an install, a build) or a check removes what a later command needs. `add-work` queues a
  corrective item when the delivery must change. The refused-run remedy stays `add-work`, as
  c4fc5608e7818902a6d3654f0012bc9987f5b042 decided.
- **Why the last work item's commands and not every item's.** Work items are built in list order and a corrective
  item is added at the end. An earlier item's command can name a file a later item moved, and no stage can retire
  it; with every item's commands such a command would refuse the stage for good. With the last item's, the
  corrective item's own step plan records what is added next, so `add-work` can always be taken. The cost: a later
  item that records a narrower regression command leaves an earlier item's suite out. Three of the 24 deliveries on
  file have more than one work item and every item in them records the same command, so the two readings agree on
  all 24.
- **Words.** "Added", not "replay": "replay" already means a resubmitted result in the navigator and a re-derived
  example in the reviews. The sentence of R128 is gone; release-plan's duty says what will be run and that a step
  the suite needs there is a check recorded before it.
- **Not built, written down as limits in the reference.** Nothing is added where release-plan recorded no consumer
  check, where the checks run in the work area or in place, or for a regression command that tests a hosted runtime.
  A suite that runs fewer tests in a clean copy by design is refused all the same. A check that is the regression
  command keeps the row release-plan recorded, so the step plan's test IDs and minimum are not carried to it.

### The rebuilt rule on the 24 deliveries on file (no live run)

- **R133 (the gate itself; `gate_on_file.py`, `evidence/gate-on-file.txt`).** ShipLoop's own release-verify gate was
  run on each saved run's state: the consumer checks, then the added commands, in one clean copy made the way the gate
  makes it, with nothing written into a saved run. On the final code, with the machine quiet: 22 pass and 2 are
  refused, `sonnet-high-due` and `sonnet-B-due`, each on the added `npm test` (exit 1; 164 tests run against a floor
  of 164, 147 against 145). Five commands are added in all. 25 command runs are held to a floor and every one is at or
  above it, so both refusals are by exit code. No saved run's scratch folder changed. A first run of the same, made
  while 23 test suites were running beside it (`evidence/gate-on-file-run1.txt`), refused a third delivery:
  `sol-A-due-2`'s own consumer check `npm test` exited 1 once. Run again alone five times the gate passes it each
  time. It is not a command the rule adds; the failing run's output was not kept; the likely cause is the port
  collision of R55, which is not established.
- **R134 (the added commands alone; `replay_on_file.py`, `evidence/replay-on-file.txt`).** The rule adds a command
  in 5 of 24 deliveries. Two are refused, the same two (`npm test` exits 1 with 164 and 147 tests run). Three pass:
  a regression command recorded as three test files beside a `node --test` check, a second regression command of
  one file, and `node --test` beside a check spelled with a reporter flag. Each added command took 0 to 6 seconds.
  In the other 19 a check already is the command.
- **R135 (one run that did not end).** The first version of that script ran `npm test` in a copy of
  `sonnet-high-due` without a process group, and the run had not ended after 300 seconds; I stopped its two
  processes by process id. Every later run of the same command there ended in 1 to 2 seconds with exit 1. The
  likely cause is the fixture's port collision (R55), which is not established. ShipLoop's own guard is 600 seconds
  a command and reports such a run as could-not-run, which does not count as a refused run.

### Second review before the confirmation (Sol 6.2 at max effort; `review-r15/sol-max-review-2.md`)

Served by `gpt-6.2-sol` at max effort with no fallback, read-only, on a neutral export of the candidate with the
question in `review-r15/sol-max-brief-2.txt`. Verdict: change first. Eight findings; each was checked in the code.

| # | Finding | Disposition |
|---|---|---|
| 1 | After a timeout the shared runner drains a command's output with no deadline, so a child that left its group and holds the pipe can hold the run | True of the runner for every stage, and not new here. Not changed in this commit; put to the owner as a separate fix |
| 2 | A corrective item that records no regression command leaves the first command in force; missing setup has a direct `send-back` edge | Taken: the reply names both exits and says the corrective item's step plan records the replacement. A return that reuses its receipt when only the return plan changed is reported, not verified here, and not on the route the reply names (a corrective item commits) |
| 3 | A sound delivery can be refused for setup, for authority or for a count that differs by design | Setup: taken (`send-back`, driven through the real gate). A count that differs by design: refused on purpose, as the owner approved; written down. A hosted runtime behind a wrapper no platform card lists: the existing classification's limit; written down |
| 4 | Reading commands as shell words drops a command `shlex` cannot split and treats two different spellings as one; a check that is the command does not inherit its test IDs and minimum | First part taken: the exact text. Second part not taken; written down |
| 5 | Choosing the last item before leaving out hosted commands can add nothing; a later item's narrower command leaves an earlier suite out; no consumer check, nothing added | First taken. The other two written down as limits |
| 6 | The floor could come from an older spelling, from an action that ended in send-back, or from an older run when the latest is uncounted; an unreadable record raised | All taken: the floor is only for the last item's commands, from the latest passed run of a done action, with its record named; an unreadable record sets none |
| 7 | The texts overpromise and misroute: the rule's sentence, the reply's stated cause, the advice to relabel an added command as a check, the copy described as untouched | Taken, except showing the selected commands in the release-plan packet, which needs packet plumbing no run has asked for |
| 8 | No test finishes the corrective return | Taken: one test drives refusal, `add-work`, a corrective item with a replacement command, a second return and an accepted release-verify; another drives `send-back` for a missing install step |

### What was checked before any live run

- **Fail-first.** Against the first build (5fc4a220ae797cbcdf4ae7d1104720b50ebae1d1) 23 of the 24 tests for the rule
  fail or error; one pins what both builds share (system-test and the end-of-work review stay without a floor).
- **Both exits, through the real gate with a real return.** One test: refused, `add-work`, a corrective item whose
  step plan records a replacement command, a second return, release-verify accepted with the replacement added at the
  corrective item's own count and the first command no longer run. Another: refused for a missing install step,
  `send-back`, release-plan records the step, the same returned tree, accepted. A third: the ordinary delivery passes
  with the added command in its record.
- **Mutants (`mutate_c1.py`, `evidence/mutants-c1.txt`).** Fifteen decisions of the rule broken one at a time; the
  unit tests fail on each. One first survived: a second filter on release-verify records that the history row's stage
  had already made redundant. It is removed.
- **Suites (`evidence/suites-c1.txt`).** The 23 related suites, 1,162 tests, pass on the final code, one after
  another. In the first of three batches, on the rule as first rebuilt and under a load of 15 to 31, one test of
  `shiploop-navigator-contract` failed: a run folder's listing changed across a refused command in the progress page's
  data, which a run's observer rewrites every two seconds. Alone it passed three of three, and it passed in both later
  batches.
- **Lint.** ruff's error and unused-name rules are clean on the changed files but for two unused locals in the
  navigator that the base has too.

### Registered confirmation round (written and committed before any run)

**Build C.** The candidate branch at 62676fc0e0dacb0ca8febd7f6f2424684c707b47: the rebuilt rule, without the
sentence.

**Runs.** Three whole deliveries at medium, defaults, started together: `ticket-due-times` on Claude
`claude-sonnet-5-5` twice (the driver and case of both live faults: 2 of 6 on file) and on Codex `gpt-6.2-sol`
once. No run option, no turn or time cap; the Claude runs carry `--max-budget-usd 40`.

**Reading.** Every verdict and case check. For each release-verify attempt of each run: the returned tree, the
consumer checks and the added commands in order, each floor with its record, each count and exit, and what the run
did next. Every refusal by the rule is read by hand as right or wrong, and reproduced on a fresh copy of that
attempt's tree. The rule is accepted if (a) no delivery is refused wrongly, and (b) every delivery ShipLoop accepts
passes the harness's suite check, the delivery's own tests in a copy. A right refusal that the run recovers from
counts for the rule and is reported in full. If (a) or (b) fails the rule is not released as built.

**Not conclusive, stated in advance.** A run that ends on an unresolved timeout says nothing either way. A driver
with no accepted delivery leaves that driver unconfirmed. A check lost to the fixture's port collision (R55) is run
again alone five times on the saved work, the first result is kept and both are reported.

**Limits, stated in advance.** Three deliveries; the trigger may not occur (about one Sonnet delivery in three on
file), and its mechanics are in the tests and in R133, not this round. The cases have no installed dependencies, so
the `send-back` exit for a missing install step is shown by its test alone. A refusal costs the run another pass of
the outer stages, which this round can time only once or not at all.

### Results of the confirmation round (2026-11-21, 21:23 to 21:57; `evidence/confirm-r15.txt`)

Three whole deliveries of the ticket case at medium effort, defaults, started together on build C
(62676fc0e0dacb0ca8febd7f6f2424684c707b47). The load average was 4 to 6.

| Run | Minutes, cost | Verdicts | Case checks | release-verify in the clean copy |
|---|---|---|---|---|
| `sol-C-due-1` | 15.4, no dollar figure | all pass | 8 of 8 | accepted: its own check `npm test` ran 122 against a floor of 122; ShipLoop added the plan's second regression command, 13 against 13 |
| `sonnet-C-due-2` | 27.1, $7.73 | all pass | 8 of 8 | accepted: its own check was one system-test file, 3 tests; ShipLoop added `npm test`, 159 against a floor of 156 |
| `sonnet-C-due-1` | 33.9, $12.67 | `committed` fails | 8 of 8 | refused: its own check `npm test` ran 148 against a floor of 152; `add-work`; a second return; accepted at 150 against 150 |

- **R136 (the rule acted in all three).** A command was added in two deliveries and a floor bound in all three.
  `sonnet-C-due-2` is the form of R127 again, a consumer check of one file where the suite is 159 tests, and this
  time the suite was run in the copy and passes there.
- **R137 (a wrong refusal).** `sonnet-C-due-1` was refused with nothing wrong in the copy. Its `npm test` ran 148
  tests there, all passing, against a floor of 152 taken from the end-of-work review's run at 21:44. Four minutes
  after that run, at release-plan, the builder moved six verbatim 1.4.0 source files out of `test/`, where node's
  runner had been counting each as a test, and it had added two system tests: 152 - 6 + 2 = 148. Run again by hand:
  the returned tree with no history runs 148; the returned head with its history and the working tree as returned
  runs 148; the commit the end-of-work review ran on runs 152. The work area, as returned, ran what the copy ran.
  The floor was the count of an earlier tree.
- **R138 (what the wrong refusal cost).** The builder did what the reply says: `add-work`, with a corrective item
  whose own run would set a new count. That item is a checksum file for the fixture and a test of it, which nobody
  asked for. From the refusal to the end of the run: 6.4 of 33.9 minutes and about a quarter of the run's spend
  (26% of its token cost at fitted prices, about $3 of $12.67).
- **R139 (the reading, as registered).** (a) fails: one delivery of three was refused wrongly. (b) holds: all three
  deliveries ShipLoop accepted pass the harness's suite check. The rule is not released as built.
- **R140 (described, one run: told what would be run, the builder fixed it first).** The same builder, at
  release-plan, wrote the whole 1.4.0 tree into a fixture from the repository's history, so that its system test no
  longer needs the history in a copy. Release-plan's duty now says the suite will be run in the clean copy. In
  round 15's batch a Sonnet delivery of this case left such a test reading the history (R127). The edits were made
  at release-plan, outside the item stages, and no accepted run covered them before the return.
- **R141 (a failed verdict the rule did not cause, and the ShipLoop fault behind it).** `sonnet-C-due-1`'s returned
  checkout holds the whole delivery uncommitted on the case's base commit, so the harness's `committed` verdict
  fails. Both of its returns were of the kind that applies a working-tree delta, because the candidate still had
  six staged deletions, the old paths of the moved files; the return policy fast-forwards only a candidate with no
  tracked changes. The first return came before release-verify ran. The deletions were never committed because
  the commit before the return lists changed paths with `git diff --name-only HEAD`, which names only the new path
  of a staged move; the path-limited commit then leaves the old path's deletion staged. Reproduced in an empty
  repository (git 2.54.0); `--no-renames` lists both paths.
- **R142 (the observers).** All three delivered trees move one of eight due times on a rollback and return, as
  most deliveries on file do. Each suite passes from the project folder, without npm and from another folder.

### Findings of the confirmation round

- **F93 (the mechanism is reproduced; one case).** A count taken from the run's history is only as true as the tree
  it was run on. Stages after the last counted run change the tree: here release-plan did, and in four of the 27
  deliveries the copy ran more tests than its floor because tests were added after it. The 24 saved deliveries
  could not show the fault, because in each the later stages only added tests. The first outside review had said to
  tie the count to the candidate or call it unmeasured; I tied it to the latest accepted run instead.
- **F94 (described, one run).** A sentence that says what will be run can do the gate's work before the gate
  (R140). It also moved product edits to a stage that has no test or review of its own.
- **F95 (a ShipLoop fault, met once in 27 deliveries).** The commit before the return drops the deletion half of
  a staged move, and the return then leaves the user's checkout uncommitted (R141). It is not part of the four
  approved changes.

### Decisions before a second confirmation round

1. **The count is measured, not looked up.** At release-verify ShipLoop runs each of the last work item's
   regression commands in the work area and then in the clean copy, at the same moment and on the same tree, and
   refuses when the copy runs fewer tests or its count cannot be read. No count is taken from the run's history,
   so the code that read it, and the limits that came with it, go. This is the owner's rule as approved ("refuse
   if fewer tests run"), with the comparison made on one tree.
2. **The move's deletion is committed.** The commit before the return lists changed paths with renames off. It is
   a separate commit with its own test, outside the four approved changes, made because the next round would meet
   the same fault whenever a builder moves a file late; the owner is told.
3. **Nothing else changes.** Release-plan's duty still says what will be run. One run is not a reason to add a
   sentence that sends such a fix through `add-work`; with 1 and 2 in place that run would have been accepted with
   every verdict passing.
4. The rebuilt code is checked on the saved deliveries again, now 27 and with this refusal among them, before a
   second confirmation round is registered.

### Owner decision, 2026-11-21: no count

Asked whether to keep a test-count comparison at release-verify or drop it for the plain rule, with the pro and con
of each, the owner answered "Go for the simpler". So release-verify compares no test count. ShipLoop adds the last
work item's regression command to the clean copy's commands and it must pass there.

What the owner was shown. For keeping: it is the one thing that would catch a suite that passes in the clean copy while its
tests skip themselves there, and one builder of two that knew its suite could not run in a copy reached for a skip
switch (R118). For dropping: on the 27 deliveries on file the count caught no fault (both real faults fail by exit
code), one build of it refused a sound delivery (R137), and it had taken three builds. I recommended keeping it with
the second round as its test. The owner chose the plain rule, and the record supports that choice: nothing measured
speaks for the count.

### The count's three builds, and the moved file

- **Build 1, read from the run's records** (62676fc0e0dacb0ca8febd7f6f2424684c707b47): refused a sound delivery
  (R137).
- **Build 2, measured in the work area at the moment of the check** (decision 1 above; built, not committed). The
  third outside review said to change it first, and it was right: that run comes after the return has recorded the
  candidate, so a suite that rewrites a tracked file or leaves a new one changes the candidate. A test through the
  real gate showed it: a suite that writes a report on every run left `report-23837.txt` in the work area after the
  non-counting check.
- **Build 3, measured on the returned tree in a temporary checkout that has the repository's history** (built, not
  committed): the checkout the test stage's base run already makes, at the receipt's tree. It passed its 36 unit
  tests and 10 tests through the real gate, 16 mutants, and the replay of the refused attempt (148 in both places);
  on the two faulty deliveries the suite passed with the history and failed in the copy. It still meant a second run
  of the suite and a refusal for any suite whose count differs between two runs.
- **What is committed** (two commits on the candidate branch, in this order):
  1f5bb5ca8a3cc3ec1d8806133df9452049225fa8, the moved file, and 5c48bcc84ac3999cb9dce5484a1da0aeb059f2e2, which
  removes every count from release-verify. Neither is on main until the second confirmation round below is read.
- **The moved file (F95).** The one commit helper lists what it staged with renames off, passes to `git add` only
  paths that are in the checkout or the index, and keeps a path that is in HEAD alone (a deletion already staged).
  The commit before the return and one other listing do the same. With the engine files of the commit before it, a
  test of both forms of a move (left as it is, staged first) through the real workspace calls fails; with them it
  passes and the return is a fast-forward. It is outside the four approved changes (decision 2 above).
- **What the rule is now.** In the clean copy ShipLoop runs the consumer checks and then each regression command of
  the last work item that records one that runs on the checkout, where no check is that command (the same text). The
  added command is judged as the step plan recorded it and marked in the packet and in a refusal. A command that
  fails has two exits: `send-back` when the release plan lacks a step it needs, `add-work` when the delivery must
  change.
- **The limit accepted**, written into the reference and pinned by a test: a suite that passes in the clean copy
  while some of its tests skip themselves there is accepted. If a delivery shows it, build 3 is the starting point.

### The committed code on saved release checks (no live run; `evidence/gate-on-file.txt`)

- **R143.** ShipLoop's own release-verify gate, on the committed code, on 28 saved release checks: the 24 deliveries
  of rounds 13 and 15, the confirmation round's three, and its refused attempt replayed on the tree it returned. 26
  pass and 2 are refused, `sonnet-high-due` and `sonnet-B-due`, each on the `npm test` ShipLoop added. Seven commands
  are added in all and none is held to a count. The attempt the round refused wrongly passes (148 tests, all passing).
  In that run `sonnet-high-due`'s added command did not end within the script's 120 seconds and was recorded
  could-not-run; run again alone three times it fails each time in 2 seconds with exit 1. Both results are kept.
- **R144 (leftover test servers, found while this ran).** A check on build 3 stood still for eight minutes on an
  `npm test` that did not end in a clean copy. Looking for the cause:
  - Five `node` processes from two of this study's earlier runs, `sonnet-medium-due` (finished 11:34) and
    `due-medium-3` (finished 14:28), were still alive after 11 and 8 hours: hung test commands of ShipLoop's base
    run in its temporary checkouts, parentless, two of them holding a listening port on the wildcard address. Both
    runs' `left_behind` verdicts report nothing left. I stopped the five by process id.
  - Twenty-nine more parentless `node` processes (corrected 2026-11-21: 27 of the 29 listeners were the check's;
    see R145) hold wildcard ports from temporary folders named `base-tests-*`,
    `pristine-*` and `suite-*`, the oldest six days old. Those are the prefixes of the harness's own base check,
    `checks/base_tests.py`, which runs `node --test` with a 120-second limit and, when the limit passes, stops that
    one process: the test-file runners and the servers they started live on. I did not stop them: they are not
    provably this study's, and the check is inside the evaluator boundary. Both the clean-up and the fix are put to
    the owner.
  Listeners like these are what the ticket fixture loses verdicts to (R55), and each one left behind makes the next
  loss more likely. That this is the source of this study's lost verdicts is likely and not established: no reading
  here depends on it.

### Third review (Sol 6.2 at max effort; `review-r15/sol-max-review-3.md`)

Served by `gpt-6.2-sol` at max effort with no fallback, read-only, on a neutral export, with the question in
`review-r15/sol-max-brief-3.txt`. It was asked about build 2 of the count and about the moved file. Verdict: change
first. Seven findings; each was checked in the code. The owner's decision came after it.

| # | Finding | Disposition |
|---|---|---|
| 1 | A run in the work area after the return can change the candidate the return recorded | True, and reproduced. Answered first by build 3, then by the owner's decision: nothing is run outside the clean copy. The test stays as the pin of that |
| 2 | That run is one more place to meet the shared runner's unbounded wait after a timeout, with the run lock held | The wait is the runner's, for every stage, and is not changed here; put to the owner as a separate fix |
| 3 | The work area can be ahead of the return or hold uncommitted edits; a count can differ between two runs | No longer applies: no count |
| 4 | A reference that fails leaves the copy with no floor; a check that is the command does not carry the step plan's test IDs | First part no longer applies. Second part declined as after the second review; written down |
| 5 | The moved-file fix is right for a plain move, a staged move, a directory, a move with an edit, a deletion alone and the empty commit; two edges older than the fix remain (an ignored destination staged by hand, a dangling link) | Nothing to change in the fix. The two edges are recorded and left |
| 6 | The texts should say what sets a floor and what happens when nothing does | The texts now say what is run and that no count is compared |
| 7 | Add a test through the real gate for a suite that writes a file after the return | Taken; it now pins that the added command runs in the clean copy alone |

### What was checked before the second round

- **Fail-first.** With the engine files of 62676fc0e0dacb0ca8febd7f6f2424684c707b47 the moved-file test fails for both
  forms of a move, and 4 of the 19 tests for the release-verify rule fail (no count is compared, the packet's list has
  no floor, an added command is judged by the step plan's minimum, the corrective route for a failing suite); 15 pin
  what both builds share.
- **Both exits, through the real gate with a real return (10 tests).** A suite that fails in the returned copy is
  refused, `add-work` is accepted, the corrective item's step plan records a replacement command, release returns
  again and release-verify passes with the replacement added and the first command no longer run. A suite that lacks
  an install step is refused, `send-back` is accepted, release-plan records the step and on the same returned tree the
  stage passes. The added command runs in the clean copy alone: the work area's status and the return are unchanged
  after the check and after done.
- **Mutants (`mutate_c1.py`, `evidence/mutants-final.txt`).** Twelve decisions of the rule broken one at a time; the
  unit tests fail on each.
- **Suites (`evidence/suites-final.txt`).** The 24 related suites, 1,321 tests, pass on the committed code, one after
  another.
- **Lint.** ruff's error and unused-name rules are clean on the changed files. (Corrected 2026-11-22: they report
  nothing new there. Two unused-variable findings in `shiploop_navigator.py`, where one sentence changed, are older
  than this work, are in the 2.4.1 release, and remain.)

### Registered second confirmation round (written and committed before any run)

**Build D.** The candidate branch at 5c48bcc84ac3999cb9dce5484a1da0aeb059f2e2.

**Runs.** Three whole deliveries at medium, defaults, started together: `ticket-due-times` on Claude
`claude-sonnet-5-5` twice and on Codex `gpt-6.2-sol` once. No run option, no turn or time cap; the Claude runs carry
`--max-budget-usd 40`. Before the launch, and after the round, processes left by this study's runs are looked for
by working folder and stopped by process id.

**Reading.** Every verdict and case check. For each release-verify attempt of each run: the returned head and tree,
the consumer checks and the added commands in order, each status, count and exit in the clean copy, and what the run
did next. Every refusal is read by hand as right or wrong and reproduced on a fresh copy of that attempt's tree. A
failed verdict is explained. Where a file was moved, both paths and the kind of the return are read. The rule is
accepted if (a) no delivery is refused wrongly, and (b) every delivery ShipLoop accepts passes the harness's suite
check. A right refusal that the run recovers from counts for the rule and is reported in full. If (a) or (b) fails
the rule is not released as built.

**Not conclusive, stated in advance.** A run that ends on an unresolved timeout says nothing either way. A driver
with no accepted delivery leaves that driver unconfirmed. A check lost to the fixture's port collision (R55) is run
again alone five times on the saved work, the first result is kept and both are reported.

**Limits, stated in advance.** Three deliveries of one case. Neither of the first round's two faults may recur: the
replay of the refused attempt (R143) and the moved-file test carry them. The cases have no installed dependencies,
so the `send-back` exit is shown by its test alone. A suite whose tests skip themselves in the copy is accepted by
design and this round does not look for one.

### Owner decision, 2026-11-21: stop the leaked test servers and fix the check

Asked whether to stop the leaked test servers of R144 and to fix the harness check that leaks them, the owner
answered "Yes, stop and fix" (23:38 local). Both were done while the second confirmation round was running. The round
runs the harness of the candidate's own tree, which this does not touch.

- **R145 (the stop; `evidence/leaked-servers-stopped.txt`).** Listed again just before stopping (`list_leaked.py`):
  70 `node` processes on the machine, 31 of them parentless, 27 of those in a temporary folder named `base-tests-*`
  (12), `suite-*` (11) or `pristine-*` (4). Every one of the 27 is a test-file process of `node --test` holding one
  listening port, and none has a living runner. Twenty started on 2026-11-15, five on 2026-11-20 and two on
  2026-11-21. They were stopped by process id at 23:41 (`stop_leaked.py`), each one checked again just before its
  signal: still `node`, still parentless, the same start time, the same folder. All 27 ended on SIGTERM and a listing
  afterwards shows none.
  - **Correction to R144 (2026-11-21).** Its "twenty-nine" was the count of every `node` process listening on the
    wildcard address. Twenty-seven of those were the check's. The other two are not: one is in a run folder of
    another study (`e2e-runs/fixrate-pilot2-20261115`) and one is a server in another session's scratch folder. Both
    were left alone, with two more parentless `node` processes that hold no port.
  - **A change inside the round, not in its registration.** The stop came six minutes after the round's launch, with
    all three runs in planning. It removes listeners that a run's own tests or the harness's checks could have
    reached. It cannot make ShipLoop accept or refuse a delivery, so the round's rule is read as registered.
  - **One more, and what it says about the cause.** The sweep after the round found a 28th: a `pristine-*` process
    started at 23:55 by another session's run of the ticket case (`e2e-runs/r-20261121-2c3d50/w2/d4`), whose
    pristine check "did not end within 120 s" on that session's own copy of the unfixed check. Its folder was
    gone and it was the last of its group; it was stopped the same way at 00:25. That run lost its verdict to a hang
    14 minutes after the 27 were stopped, so the 27 were not the cause of that hang.
- **R146 (the fix).** `node_test` in `test/shiploop_e2e/checks/base_tests.py` ran `node --test` with a 120-second
  limit and, when the limit passed, stopped the one process it had started, the runner. The runner has one process
  for each test file, and a test file that leaves a server listening never ends. Those processes lived on with no
  parent, each with its port, in a folder the check had already deleted. Now each run has a session of its own and,
  at the limit, the check ends the run's whole process group with `listeners.end_group`, the harness's one group
  kill, which its other checks already use.
  - **Earlier fix and what it left.** e74097b10c2e165d8e25a919059b9ad7b2958602 (2026-11-15) put the check inside an
    owned process group in the hermetic tests' wrapper (`test/fixture_process.py`) and left the check file as it was,
    to keep the oracle digest. A check started by a live run, or by a test without the wrapper, kept leaking:
    eleven of the 27 started after that commit was written (four later that day, five on 2026-11-20, two on
    2026-11-21).
  - **Working with that wrapper.** A session of its own takes the run out of the group the wrapper owns, so the
    check, when it is itself stopped (SIGTERM), now stops its run on the way out.
  - **Fail-first.** A new test gives `node_test` a test file that leaves a server listening and a limit of five
    seconds. With the old check the test file's process is still alive ten seconds after the limit (the test then
    stops it itself); with the fix it is gone. A second test runs the real check under the wrapper and stops it while
    its run hangs: it passes with the old check (one group), fails with the fix less its SIGTERM line (the run
    outlives the check), and passes with the fix.
  - **Suites, one after another.** `shiploop-e2e-brownfield` 31 tests, `shiploop-e2e-environment` 140 and
    `shiploop-e2e-user-directory` 45 pass. `shiploop-e2e-brownfield-tickets` passed 51 of 52 and then, run again
    alone, 52 of 52: on the first run the base's own tests did not end within 120 seconds once, in the base copy, for
    one of the calibration's 159 results. That is the fixture's hang on a shared machine, not the fix; nothing was
    left behind by it. Both results are kept.
  - **What it changes for comparisons.** The oracle digest goes from `dba32b3f6860` to `b32933f70500`; the evaluator
    digest (`cc221376b337`) is unchanged. `promotion.py` compares a case only across equal digests, so attempts graded
    before and after are separate experiments for it. What the check reports is unchanged: the same verdict lines,
    and the same diagnostic for a run that does not end.
  - **Not covered, written down.** The harness gives one check 180 seconds, less than the check's own worst case of
    two runs of 120. When that limit passes, `run.py` stops the shell it started and the check can die before it
    stops its run. None of the 27 was left that way: that would leave a runner alive, and none had one. A test file
    that starts a process in a session of its own is outside the group. A process that a run leaves behind after its
    runner has ended by itself is not stopped either: none is on record.
  - **Still open.** ShipLoop's own base run leaves the same kind of process behind when a test command hangs (the
    five of R144). That is the engine's runner, not this check, and is not changed here.
  Whether these servers are what the ticket fixture loses verdicts to (R55) is not established, and the 28th speaks
  against their being the only cause. 26728eddd587930f5da3f6600e5d7ab4017d8acc measured that fixture's wrong
  answers as another server on the same port number and noted that some "could in principle come from another
  tickets server". A leaked base-test server is one such server; live runs of the same case on the machine are
  others.

### Results of the second confirmation round (2026-11-21 23:35 to 2026-11-22 00:20; `evidence/confirm-r15d.txt`)

Three whole deliveries of the ticket case at medium effort, defaults, started together on build D
(5c48bcc84ac3999cb9dce5484a1da0aeb059f2e2). The load average was 6 at the start and 25 to 34 when the two Sonnet runs
ended: other sessions' runs and suites were on the machine.

| Run | Minutes, cost | Verdicts | Case checks | release-verify in the clean copy |
|---|---|---|---|---|
| `sol-D-due-1` | 13.9, no dollar figure | all pass | 8 of 8 | accepted at its one attempt: the release plan recorded `npm test` itself, 123 tests pass; nothing was added |
| `sonnet-D-due-1` | 44.8, $7.40 | all pass | 8 of 8 | accepted at its one attempt: its own check was one system-test file, 1 test; ShipLoop added `npm test`, 144 tests pass |
| `sonnet-D-due-2` | 42.3, $10.26 | all pass | 8 of 8 | accepted at its one attempt: its own checks were one system-test file, 2 tests, and `node bin/tickets.js --help`; ShipLoop added `npm test`, 158 tests pass |

- **R147 (the rule acted in two deliveries and was already met in the third).** Both Sonnet release plans recorded a
  consumer check that runs one test file. ShipLoop added the last work item's `npm test`, and the whole suite ran in
  the copy and passed: 144 and 158 tests, none failing, none skipped. This is the form of R127 twice more. The Sol
  release plan recorded `npm test` itself, so the copy already ran the suite.
- **R148 (nothing was refused at release-verify).** Each delivery had one attempt there, in the returned copy, and it
  was accepted. The runs' other refusals (3, 13 and 13 commands) are at other stages and were recovered in the
  session. So this round did not meet a right refusal, and neither exit was taken live: the tests through the real
  gate carry both.
- **R149 (the reading, as registered).** (a) holds: no delivery was refused wrongly. (b) holds: all three deliveries
  ShipLoop accepted pass the harness's suite check, and its other seven checks. No verdict failed. The rule is
  accepted as built.
- **R150 (the counts, read because the first round's fault was a count).** In both Sonnet runs the copy ran more
  tests than the last run recorded in the work area, 144 against 143 and 158 against 156: system tests were written
  after that run. A count taken from the run's history would have been stale again, this time in the harmless
  direction. Run again by hand on each delivered tree, the suites report 123, 144 and 158 tests, all passing, none
  skipped.
- **R151 (the moved-file fix was not met).** No delivery renamed or deleted a file. Every return is a fast-forward
  merge, every returned checkout is clean and committed, and all three `committed` verdicts pass. The fix is carried
  by its test.
- **R152 (the observers).** All three delivered trees move one of eight due times on a rollback and return, as most
  deliveries on file do (round 14's second hole, which this build does not address). Each suite passes from the
  project folder, without npm and from another folder. The observer counts 122, 143 and 156 where `npm test` counts
  123, 144 and 158: it names the `*.test.*` files, and `node --test` with no file names also runs the helper files
  under `test/`, one passing test each.
- **R153 (a hang the gate did not meet, described, one run).** `sonnet-D-due-2` spent 6.7 minutes at release-verify
  for its one accepted attempt. Before calling the gate, the builder made its own copy of the returned head and ran
  `npm test` there; that run did not end, the builder found a test process spinning, stopped its own task and wrote
  that it suspected "a port collision with other sessions on this shared machine". Run again under a 90-second limit
  it passed in a second, and ShipLoop's own run of the added command took 1.1 seconds. The rule adds one more run
  of the suite to a delivery, so it adds one more chance to meet such a hang; the registration calls a run that ends
  on an unresolved timeout inconclusive, and none did.
- **R154 (time, not a comparison).** The two Sonnet runs took 44.8 and 42.3 minutes against 27.1 and 33.9 in the
  first round. Their plans differ (two steps an item here, and two work items in one run), each spent about 14
  minutes at `test`, one lost 6.7 minutes to R153, and the machine was loaded. No command ShipLoop ran took over a
  minute.

### Findings of the second confirmation round

- **F96 (firm for what was built; six deliveries of one case over two rounds).** Left to the builder, the check of
  the delivery where a consumer gets it is often one file: three of the four Sonnet deliveries of the two
  confirmation rounds recorded a consumer check of 1 to 3 tests where the suite has 144 to 159, and both Sol
  deliveries recorded `npm test`. With the rule the suite is run in the copy either way. In all six it passes there;
  the two deliveries on file where it does not (R118, R127) are refused by the committed gate (R143).
- **F97 (two rounds, one direction each).** A count from the run's history was stale in both rounds: once too high
  (R137, a wrong refusal) and twice too low (R150, harmless). Nothing in the second round speaks for comparing a
  count.
- **F98 (a limit, described).** Every run of the suite on a shared machine can meet the fixture's hang (R153, and
  another session's lost verdict in R145). The rule's added run is one more of them. On the 28 saved release checks
  one added command of 7 did not end within the script's limit and failed in 2 seconds when run alone (R143).

### Decision: release (routine, AGENTS.md "Decisions")

The owner approved the change ("Yes, do these") and chose its form ("Go for the simpler"); the registered round
accepts it. The candidate branch is merged into main with its four commits kept, the round is journaled in
`test/shiploop_e2e/LEARNINGS.md` after the merge, and the release is published once `scripts/release.py`'s preflight
and CI pass. The two change notes make it a minor release of ShipLoop.

Left open, each the owner's to decide: proof of non-product criteria kept out of product tests (candidate 3, not
built); the observers wired into every run; the engine's two faults the reviews found (the shared runner's unbounded
wait after a timeout, and a return that reuses its receipt when only the return plan changed); ShipLoop's own base
run leaving test processes behind (R144); and the return after a rollback that moves a due time (R152).

**Released, 2026-11-22.** ShipLoop 2.5.0 in skill-craft 4.3.0 (eb4fad3023f10011b5117cbee1f5f9edafe743e5), cut by
`scripts/release.py` at the commit of the E2E entry. The guarded push passed its four checks and CI passed on both
pushes, the merge's and the release's. Claude and Grok went from 4.2.1 to 4.3.0. Codex was refreshed while no
process ran from an installed plugin folder; its refresh removed the older version folders 3.3.0, 4.1.0 and 4.2.1,
and they were put back from their release commits within a minute (425, 309 and 309 files, each its release commit's
count). The first lookup of those commits found nothing (`\b` in an extended regular expression), which is why it
took a second command. The published-install smoke test passes against the release commit.

- **R155 (the last sweep, 2026-11-22 01:25).** By working folder, over this study's run roots and scratch folder:
  one process of this study was left, a `python server.py` on port 18765 that a headless reader of round 3's replay
  had started on 2026-11-20; stopped by process id. No parentless `node` process is in a folder of the base check.
  Four parentless processes that are not this study's are left as they were and put to the owner: two in run folders
  of another study of 2026-11-15 (one of them has used a whole processor for six days), one in an unnamed temporary
  folder, and one server in another session's scratch folder.
- **R156 (the fixture's hang, described; three in an hour).** After the 27 were stopped: another session's pristine
  check at 23:55, one builder's own `npm test` in its own copy at 00:10 (R153), and the base's own tests in the
  calibration suite at about 00:50 (R146). The base's tests listen on the wildcard address with port 0, connect to
  `127.0.0.1` and send requests with no time limit (`fixtures/node-tickets/test/helpers.js`), so a request that
  reaches another program holding the same port number can wait for ever; 13 programs held an IPv4 loopback port in
  that range at about 00:50, 10 of them Claude sessions. 26728eddd587930f5da3f6600e5d7ab4017d8acc measured the same
  mechanism for wrong answers and left the fixture to the owner, because it is pinned by its digest and is the E2E
  subject. Binding the fixture's tests to `127.0.0.1` is put to the owner again with these three hangs.

### Owner question, 2026-11-22: what binding the fixture's tests to `127.0.0.1` means (`evidence/port-mixup.txt`)

The owner, of the question R156 put: "I do not understand 1 technically". Answered by watching the mix-up on this
machine and counting it, on scratch copies of the fixture, 05:44 to 06:10. Nothing under
`test/shiploop_e2e/fixtures/` is changed, and the decision stays the owner's. Status: firm for this machine and
this morning; one machine, one node version.

The two lines it is about: the service listens with a port and no address, which is every address of the machine
(`src/server.js`, `server.listen(config.port, ...)`), and the test's client calls `127.0.0.1` at that port
(`test/helpers.js`, `withService`), the port being 0, "any free one".

- **R157 (the mix-up, watched; `port_mixup_demo.js`).** 26728eddd587930f5da3f6600e5d7ab4017d8acc inferred the
  mechanism and "did not watch the two sockets". On one fixed port number, 23117: another program listens on
  `127.0.0.1:23117`; a server then listens on 23117 with no address and the system accepts it (IPv6 `::`); a client
  that asks `127.0.0.1:23117` is answered by the other program, and by the test's own server only once the other
  program is gone. The order in which the two start does not matter. A server told to listen on `127.0.0.1:23117`
  itself is refused (`EADDRINUSE`).
- **R158 (how often the system hands out a held number).** Other programs held 12 numbers on `127.0.0.1` in the
  range the system hands out (49152 to 65535): 10 Claude sessions, OrbStack and Ollama. Asked for "any free port"
  40,000 times with no address, the system gave one of those 12 numbers 29 times, each of the 12 at least once: 12
  in 16,552, where a held number counted as free would be 12 in 16,384. Asked on `127.0.0.1`: 0 times in 40,000.
- **R159 (the base's suite, 1,600 runs each way; `port_mixup_suite_probe.py`, `evidence/port-mixup-probe.json`).**
  One run of the suite has 117 tests and starts 21 servers, as it is and with a two-line change (the service passes
  `config.host` to `listen`; the test settings name `127.0.0.1`). As it is, 1,580 of 1,600 runs pass, 2 fail and 18
  do not end within 30 seconds. With the change, 1,600 of 1,600 pass. Of the runs as it is, 19 were given a number
  another program held on `127.0.0.1` (15 a Claude session, 2 Ollama, 2 OrbStack): all 19 are among the 20 that did
  not pass, and none passed. None of the changed copy's 33,600 servers was given one. The twentieth run did not end
  and shared no number in the list read at the start of its round; its cause is not shown.
- **R160 (what the test does, by what the other program does; `port_mixup_outcomes.py`).** One test through the
  fixture's own `withService`, another program already on `127.0.0.1` at its port number. The other program hangs
  up: the test fails with `ECONNRESET` and the run ends. It answers in JSON: the answer is taken for the service's (a
  test that checks only the status passes on it). It answers in anything else: the test is reported failed and the
  run never ends. It never answers: nothing is reported and the run never ends. The helper parses the body inside
  the response's `end` handler, so a body that is not JSON throws there, the request is never settled, `withService`
  never reaches its `finally`, the test's server stays up and the test file's process cannot exit. 17 of R159's 18
  runs that did not end had reported a test failed first, which is this path; the two outright failures were
  dropped connections, both at OrbStack.
- **R161 (a stuck run of this session's own, found and stopped).** A `node --test` of the base's tests in the
  system's temporary folder (`tmp749rmb4l/prior`), started at 00:44:45 by a case check's command in this session's
  own test tier: `test/api.test.js`, 0.35 seconds of processor time in 5 hours 22 minutes, waiting, its server still
  listening on every address at port 57236 and no connection open, which is the state R160 describes. Who held 57236
  on `127.0.0.1` at 00:44 is not known. The sweep of 01:25 (R155) looked in this study's run roots and scratch
  folder and not in the system's temporary folder, so it missed it. Its six processes were stopped by process id,
  each checked to have started at 00:44:45. The check's own shell was among them and had no parent left: whatever
  ran the check ended without stopping it. Which path that was is not shown (R146 names one: a check that outlives
  the harness's 180-second limit).

Findings.

- **F99. The mix-up is observed, and its rate follows from two counts.** With `h` numbers held on `127.0.0.1` by
  other programs and 21 servers a run, a run of the base's suite shares a number about `21 × h / 16,384` of the
  time: 1.5 percent at 12, against 1.25 percent measured (20 of 1,600). The 25 node and Python servers on
  `127.0.0.1` that 26728eddd587930f5da3f6600e5d7ab4017d8acc counted give 3.2 percent if all were in the range
  handed out, against the 3.4 percent it measured (32 of 928). The rate rises with every program that listens on
  `127.0.0.1`, and each open Claude session is one.
- **F100. What it looks like depends on who holds the number.** On 2026-11-01 the holders were other projects'
  servers and it showed as resets and wrong answers. Today 10 of the 12 are Claude sessions and it shows as a run
  that never ends (18 of 20). So the runs that never ended since 2026-11-20 (R55, R146, R153, R156) are of the same
  kind as the flake of 2026-11-01; no single one of them is shown to be it, and R153's, where the builder found a
  test process spinning, is not explained by a wait.
- **F101. Listening on `127.0.0.1` removes it where it starts.** 0 of 1,600 runs, 0 of 33,600 servers and 0 of
  40,000 askings were given a held number. A time limit or a caught parse error in the helper's client would turn a
  run that never ends into a failed test and leave the mix-up in place.

What the change would touch, for the owner's decision (nothing of it is done).

- Two lines in `fixtures/node-tickets` and the same two in `fixtures/node-tickets-assigned`; the service's line is
  also in `stage_cases/step-plan/replay-ticket-comments-late-send-back/repo`.
- The pins of four cases in `cases.json`: `ticket-assignment`, `ticket-import` and `ticket-due-times` at
  `5652a97375d0`, `ticket-assignment-tests` at `f0e486c77413`. `brownfield.resolve` refuses a case whose fixture
  does not digest to its pin.
- The oracle digest of every case, because it is taken over `checks/` and `fixtures/` (`boundary.oracle_files`):
  promotion reads attempts graded under different digests as different experiments. It is `b32933f70500` since
  fb0f834d90ff8a27b4a2eaec75ed45462a913e95 changed the base check on 2026-11-21, so the series already began again
  a day ago; a fixture change now begins it once more, and little has been recorded on the new digest yet.
- Not reached by it: a saved delivery keeps the old lines, so grading one again can still meet the mix-up, and a
  test server of a changed base is one more number on `127.0.0.1` an unchanged one can be handed; a builder's own
  test that starts the product on every address and calls `127.0.0.1`; any run that does not end for another reason.
  The harness's own acceptance checks take their number on `127.0.0.1` first (`quality.free_port`), so no other
  program holds it there when the product starts.

Conduct, a slip of mine. The probe ran 16 suites at once and each suite runs its 18 files at once: the load
average reached about 190 for most of 17 minutes. No E2E run was live when it began, but another session's quick
tier (scratch folder `defaults/merge-a5ac04`) started three minutes in, at 05:51, and ran beside it until 06:04.
During the changed arm's rounds the probe's ticket servers also held numbers on `127.0.0.1` that the tier's ticket
suites could have been handed. A heads-up to that session was held by it and not delivered. A failure or timeout of
that tier between 05:51 and 06:04 should be run again alone before it is read. Four copies at once would have done.

### Owner decision, 2026-11-22: the ticket fixtures' tests listen on `127.0.0.1`

Asked "Change the ticket fixtures so their tests listen on `127.0.0.1`?", the owner: "Yes do all changes". It is the
choice 26728eddd587930f5da3f6600e5d7ab4017d8acc left with the owner on 2026-11-01 and
238bb13ebcc63a8ebdc0fac74037568491a4bcde called the owner's standing call.

- **R162 (the change).** In `fixtures/node-tickets` and `fixtures/node-tickets-assigned`, the two lines R159
  measured: `createService(...).start()` passes `config.host` to `listen`, and `TEST_SETTINGS` in `test/helpers.js`
  names `127.0.0.1`, the address the helper's client calls. A comment at each says why, in the base's own words (the
  base never names the harness). The service started the operator's way has no `host` and listens on every address
  as before: seen on IPv6 `::`, answering on `127.0.0.1` and on `::1`. Not added: a `HOST` environment variable. The
  base's README says every setting is an environment variable, so a `HOST` would be a new documented setting with
  its config test and changelog line, more of the subject changed than was measured or approved; `config.host` is
  set by a caller, and the comment at `start()` says so. The user-directory references' tests already listen on
  `127.0.0.1`.
- **R163 (pins and digests).** `node-tickets` goes from `5652a97375d0` to `6d6f3563c459` (ticket-assignment,
  ticket-import, ticket-due-times) and `node-tickets-assigned` from `f0e486c77413` to `d88f22750bc6`
  (ticket-assignment-tests, asserted in `test/shiploop-e2e-test-adequacy.test.py`). The oracle digest of every case
  goes from `b32933f70500` to `95a78b4ccfa1`, and the four cases' own digests change with their pins (for
  ticket-due-times, `1f9bbcdded4d` to `22063c685377`). Attempts graded before and after are separate experiments for
  `promotion.py`. Nothing is rescored; earlier results stand as records of the old base.
- **R164 (checked without a model).** Each fixture's suite: 117 tests pass and 21 servers start, all on `127.0.0.1`.
  A new test, `FixtureAddressTest` in `test/shiploop-e2e-brownfield-tickets.test.py`, runs each fixture's own tests
  with a preload that records the address of every server and asks for `127.0.0.1` alone: it fails on both fixtures
  as they were (`IPv6 ::`) and passes now. All 92 variants of the five ticket reference modules build on the changed
  base, so every patch still applies, and the adequacy suite's case contract passes (10 tests). The quick tier
  selected by the change (70 suites) is not run in this commit: three live runs of another session were on the
  machine, and a tier is not run beside live runs. Its result is in the results below.
- **R165 (left as it is).** The stage case `stage_cases/step-plan/replay-ticket-comments-late-send-back` keeps its
  repo: it is the recorded state of a run of 2026-11-01, and like any saved delivery it has the old lines. The
  calibration's regrading (`settle` and `agreed`, from 26728eddd587930f5da3f6600e5d7ab4017d8acc and
  8c5b4d4ec776dc9a06445c1054e9d4802558a649) stays: it costs nothing when grades agree, and whether first grades
  still disagree with the new base is not measured here. `checks/base_tests.py` keeps its 120-second limit and its
  whole-group stop.
- **What other sessions meet.** A checkout or apparatus copy taken before this commit keeps the old fixtures and
  pins and goes on as before. One taken after it grades every case under a new oracle digest. While both kinds run
  on one machine, a test server of the new base is one more number on `127.0.0.1` that a run of the old base can be
  handed.

### Registered confirmation runs for the changed base (written and committed before any run)

**Build.** The commit that carries this section, from a clean checkout.

**Runs.** Two whole deliveries of `ticket-due-times` at medium, defaults, started together: Codex `gpt-6.2-sol` once
and Claude `claude-sonnet-5-5` once (`--max-budget-usd 40`). No run option, no turn or time cap. No test tier is on
the machine at the launch. Three live runs of another session, on the old base, are (`e2e-runs/r-20261122-ffb3fb`);
they and these two do not share a base. After the runs, processes left by these two are looked for by working
folder and by environment and stopped by process id. The quick tier selected by the change runs once no live run
is left on the machine, and the push to main waits for it and for these runs.

**Reading.** For each run: the base record (the fixture and the digest it started from), every verdict and case
check, and any check that did not end. On each delivered tree, the delivered suite is run once with the preload of
`FixtureAddressTest`, and every server it starts is counted by address.

**What it is asked.** (a) The harness starts each run from the new base (the recorded digest is `6d6f3563c459`) and
grades it: no refusal over the pin, verdicts and checks recorded. (b) Every server the delivered suite starts through
the base's helper listens on `127.0.0.1`. A server on another address is reported with the test that started it: it
is the builder's own doing and not a failure of the change. (c) No base, pristine or suite check ends on "did not
end". If (a) fails the change is not pushed as it is. A failed verdict or case check is read and explained: two
deliveries cannot show a rate, and a delivery that fails for a reason of its own says nothing about the base.

**Limits, stated in advance.** Two deliveries of one case on two drivers; nothing about how often a builder is led
astray by `config.host`; nothing about `ticket-assignment-tests`, whose fixture is covered by the suites alone.

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
| `evidence/learned-judged.txt` | round 5: the judges' agreement and label shares (R39) |
| `evidence/slices-k0.txt`, `evidence/learning-census-slices-k0.txt`, `slices-k0/*.json` | round 5: arm K0 beside the baseline slices, and the files it is computed from (R40) |
| `evidence/step-size-census.txt`, `evidence/step-size-census-slices.txt` | round 6: step plans' shape, a step's seconds by its size, the same request in more or fewer steps, hidden checks by step count, over the recorded runs and over round 4's slices (R41 to R44) |
| `overlays/f1-fewest-steps.json` | round 6: the one edit of arm F1, applied to a build copy only |
| `evidence/slices-f1.txt`, `evidence/slices-f1-iteration.txt`, `evidence/slices-f1-snapshots.txt`, `evidence/step-size-census-slices-f1.txt`, `slices-f1/*.json` | round 6: arm F1 beside its baseline slices, per-step detail, hidden checks at each snapshot, the step plans' shape, and the three files they are computed from (R45 to R49) |
| `evidence/review-option-census.txt`, `review_option_census.py` | round 7: the planning-review option every recorded run used and who asked for it, and review seconds by reviewed stage and driver (R56, R57) |
| `evidence/review-yield-drivers.txt`, `review_yield_drivers.py` | round 7: what each review changed, by driver and reviewed stage, from the pass logs of this study's runs (R58) |
| `overlays/r7-s-planning-reviews-pinned.json`, `overlays/r7-l-lean-reviews.json`, `build_arm.py` | round 7: the two arms' edits, applied to plugin build copies only, and the script that builds an arm's plugin for `run.py --plugin-dir` |
| `evidence/review-arms.txt`, `review_arms_report.py`, `runs-reviews/census.json` | round 7: the twelve deliveries' rows, the registered readings by driver and case, the time split, and the file they are computed from (R59 to R63) |
| `runs-reviews/interrupted.json`, `runs-reviews/reruns.json`, `runs-reviews/l1-at-kill.json` | round 7: which runs the kill reached and how each went on, the one check run again, and the grading of the run that was unfinished at the first write-up at its last commit before the kill (R60, R62) |
| `evidence/late-work-census.txt`, `late_work_census.py` | round 7 update: how often a stage after the build opened a new work item, by driver, in 311 finished whole deliveries, and the minutes it added (F50) |
| `evidence/next-round-cuts.txt`, `next_round_cuts.py` | round 7 update, exploratory: seconds by stage and after refused commands in this round's deliveries, criteria per work item, and the recorded Grok deliveries by part |
| `evidence/grok-review-scan.txt`, `grok_review_scan.py` | round 8, context only: every recorded Grok 4.6 review's passes, seconds and whether it changed anything, on ShipLoop 1.34.3 to 2.3.0 (R66) |
| `evidence/effort-sol-high.txt`, `effort_report.py`, `runs-effort/census.json` | round 8: the six Sol 6.2 high deliveries beside round 7's Sol 6.2 medium runs, the registered readings, and the file they are computed from (R67 to R71) |
| `evidence/effort-sol-paired.txt`, `runs-effort-paired/census.json`, `runs-effort-paired/reruns.json` | round 8: the paired redo, medium and high started together, its readings, the file they are computed from, and the one check run again (R73 to R77) |
| `evidence/plan-review-cuts.txt`, `plan_review_cuts.py` | round 9: how builders stop processes, by driver, and what each Sol spec of `ticket-due-times` says about tickets already on file (R78, R79) |
| `review-r9/sol-max-brief.txt`, `review-r9/sol-max-review.md` | round 9: the brief sent for the max-effort review of the change plan, and the review word for word |
| `overlays/r9-card-run-options.json`, `card_patch.py`, `overlays/r9-n-no-added-manual-step.json`, `overlays/r9-g-duty4-bounds.json`, `stage_stop_samples.py` | round 9: the three candidate wordings as patches to build copies, the applier for the card patch, and the driver that ends a real run once it is past the spec stage |
| `runs-grok/census.json` | round 8: the Grok delivery's seconds by stage (R80 to R82) |
| `evidence/e1-card-starts.txt`, `start_option_read.py` | round 9: the card test's 24 start-only samples, what each passed and recorded, and the registered reading (R84) |
| `evidence/e2-spec-read.txt`, `spec_read_score.py`, `spec-read/` | round 9: the spec test's 24 accepted specs under shuffled names, the readers' brief, which is which, both readers' classes with quotes, the one spec its review changed as written, the sample list, and the score (R85, R86) |
| `evidence/ship-round-readings.txt` | round 9: the E2E round on the shipped corrections: every value of the `LEARNINGS.md` entry with the file it was read from, the three readings of the change, and the same case's run on the earlier text (R88 to R90) |
| `judge-grok/packet-*.txt`, `judge-grok/key.json`, `judge-grok/out-A.jsonl`, `judge-grok/out-B.jsonl`, `judge-grok/source/`, `evidence/grok-review-judge-brief.txt`, `evidence/grok-reviews-judged.txt`, `grok_review_score.py` | round 8: the Grok delivery's seven changed reviews and six round-7 anchors as the judges saw them, which is which, each judge's labels, the brief, the score and the script that makes it (R83) |
| `removed_review_diffs.py`, `judge-reviews/packet-*.txt`, `judge-reviews/key.json` | round 7: each review of a removed stage that changed anything, as the judges saw it, and which run and driver each is |
| `judge-reviews/out-A.jsonl`, `judge-reviews/out-B.jsonl`, `evidence/removed-review-judge-brief.txt` | round 7: each judge's label, scope and reason per packet, and the brief |
| `evidence/removed-review-judged.txt`, `removed_review_score.py` | round 7: the judges' agreement and the substantive share by driver and reviewed stage (R64) |
| `guard-step-cases.json`, `guard_apply.py` | round 6 guard round: the step case `tickets-due-times`, and the script that merges it into a throwaway worktree's case list |
| `evidence/slices-guard.txt`, `evidence/slices-guard-iteration.txt`, `slices-guard/*.json` | round 6 guard round: each plan with its steps and the files each built step changed, the slices' measures, the registered readings, and the files they are computed from (R51 to R54) |
| `evidence/slices-guard-snapshots.txt`, `evidence/slices-guard-regrade.txt`, `evidence/base-suite-flake.txt` | round 6 guard round: hidden checks at each snapshot as first graded, the three checks run again after a harness timeout, and the repeat runs that showed the ticket fixture's test run sometimes does not end (R55) |
| `evidence/steps-pooled.txt`, `slice-plans.json` | round 6: slice minutes and seconds by part against the steps planned, baseline and F1 slices of rounds 4 to 6 pooled (R50, exploratory), and each slice's planned steps and criteria as read from its run folder |
| `chess_hidden.js` | round 6: the ten hidden checks of the chess engine case |
| `evidence/slices.txt`, `evidence/slices-iteration.txt`, `evidence/slices-turns.txt`, `evidence/slices-snapshots.txt`, `slices/*.json` | round 4: the live slices' registered measures, per-step detail, time by kind of command, hidden checks at each snapshot, and the three files they are computed from |
| `evidence/batch-r15.txt` | round 15: the eight deliveries of the batch round: verdicts, case checks, each release-verify record with counts and floors, the observers (R126 to R132) |
| `gate_on_file.py`, `evidence/gate-on-file.txt`, `evidence/gate-on-file-run1.txt` | round 15: ShipLoop's own release-verify gate, with the rebuilt rule, on the 24 saved deliveries: each command, its count, its floor and each refusal; the quiet run and the first run (R133) |
| `replay_on_file.py`, `evidence/replay-on-file.txt` | round 15: the commands the rebuilt rule adds, each run alone in a fresh copy of the delivered tree (R134) |
| `mutate_c1.py`, `evidence/mutants-c1.txt`, `evidence/suites-c1.txt` | round 15: the fifteen mutants of the rebuilt rule and the test that catches each; the three batches of related suites, with the one failure under load and its reruns |
| `review-r15/sol-max-brief-2.txt`, `review-r15/sol-max-review-2.md` | round 15: the question put to Sol 6.2 at max effort about the rebuilt rule, and its verbatim answer |
| `confirm_read.py`, `evidence/confirm-r15.txt` | round 15: the confirmation round: each delivery's verdicts, checks, work items, every release-verify attempt with its counts and floors; the wrong refusal and the uncommitted return reproduced by hand (R136 to R142) |
| `evidence/gate-on-file-final.txt`, `evidence/mutants-final.txt`, `evidence/suites-final.txt` | round 15: the committed rule (no count) on 28 saved release checks, with the refused attempt replayed (R143); its twelve mutants; the 24 suites and the fail-first results |
| `review-r15/sol-max-brief-3.txt`, `review-r15/sol-max-review-3.md` | round 15: the question put to Sol 6.2 at max effort about the count measured in the work area and the moved-file fix, and its verbatim answer |
| `list_leaked.py`, `stop_leaked.py`, `evidence/leaked-servers-stopped.txt` | round 15: the leaked test servers of the harness's base check: the listing, each process stopped with its start time, port and folder, and what was left alone (R145) |
| `evidence/confirm-r15d.txt` | round 15: the second confirmation round: each delivery's verdicts, checks, work items and its one release-verify attempt with the added command; the suites run again by hand; refusals, returns, the hang in one builder's own copy (R147 to R154) |
| `port_mixup_demo.js`, `port_mixup_outcomes.py`, `port_mixup_stranger.js`, `port_mixup_suite_probe.py`, `port_mixup_count_listens.js`, `evidence/port-mixup.txt`, `evidence/port-mixup-probe.json` | 2026-11-22: the ticket fixture's port mix-up watched and counted: one number held by two programs, how often the system hands out a held number, the base's suite 1,600 times as it is and with the service on `127.0.0.1`, what one test does by what the other program does, and a stuck run found and stopped (R157 to R161) |

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

Round 5: `learning_census.py <work>/iteration.json [--sample 160 judge-learned/lines.jsonl]` (after
`iteration_census.py`), `learned_score.py judge-learned`, and for the arm `slice.py ... --overlay
overlays/k0-no-look-back.json` followed by round 4's slice scripts; `slice_report.py slices-k0/census.json
slices-k0/iteration.json slices-k0/snapshots.json` reproduces `evidence/slices-k0.txt`.

Round 6: `python3 -I step_size_census.py <work>/iteration.json <work>/census.json` (after round 4's
`iteration_census.py`; with `slices/iteration.json slices/census.json` it reproduces
`evidence/step-size-census-slices.txt` from the repository alone), `node chess_hidden.js <product root> <check>`
(`--list` names the checks), and for the arm `slice.py ... --overlay overlays/f1-fewest-steps.json` followed by
round 4's slice scripts into `slices-f1/`; `slice_report.py slices-f1/census.json slices-f1/iteration.json
slices-f1/snapshots.json` reproduces `evidence/slices-f1.txt`, and `steps_pooled.py slices slices-k0 slices-f1`
reproduces `evidence/steps-pooled.txt`, both from the repository alone.

Round 6, guard round: `git worktree add --detach <path> HEAD`, `guard_apply.py <path>`, then from that worktree
`slice.py --case tickets-due-times ...` (with `--overlay <checkout>/.../overlays/f1-fewest-steps.json` for F1,
`--stop-after step-plan` for a plan-only run); `stage_census.py slices-guard/census.json <root>`,
`iteration_census.py slices-guard/census.json slices-guard/iteration.json --all`, `python3.13 slice_snapshots.py
slices-guard/iteration.json slices-guard/snapshots.json`, `python3.13 regrade_timeouts.py slices-guard/iteration.json
slices-guard/snapshots.json`, and `guard_report.py slices-guard`, which reproduces `evidence/slices-guard.txt` from
the repository alone.

Round 7: `python3 -I review_option_census.py <work>/census.json <run roots>` (R56, R57) and `review_yield_drivers.py
<run roots>` (R58). The arms: `python3 build_arm.py <folder> overlays/r7-s-planning-reviews-pinned.json` (or the L
overlay) prints a plugin folder; `test/shiploop_e2e/run.py --case <case> --host <host> --model <model> --effort
<effort> --plugin-dir <that folder> --output <root>/<name>-S-1` runs a delivery (for arm L add `--planning-review
none` and name the folder `-L-1`). Then `review_option_census.py runs-reviews/census.json <root>` and
`review_arms_report.py runs-reviews/census.json`, which reads the run folders and reproduces
`evidence/review-arms.txt`. The judges: `removed_review_diffs.py judge-reviews <run folders>` writes the packets, two
judges label them with `evidence/removed-review-judge-brief.txt`, and `removed_review_score.py judge-reviews`
rescores from the repository alone. `late_work_census.py <work>/census.json runs-reviews/census.json` reads the
runs' traces and reproduces `evidence/late-work-census.txt`; `next_round_cuts.py runs-reviews/census.json
<work>/census.json` does the same for `evidence/next-round-cuts.txt`.

Round 15: `python3 stop_at_stage.py --plugin-dir <plugin> --root <out> --until prepare --planning-review stage
<name>:ticket-due-times:<host>:<model>:medium ...` ends each sample at the plan; `python3 -I plan_rows.py [--blind
<key file>] state,migrate-before,migrate-after,switchover <name>=<run folder> ...` prints the rows;
`criteria_census.py` and `meta_test_census.py` take `<name>=<run folder or tree>` and print the two baselines.
The port mix-up (R157 to R161): copy `test/shiploop_e2e/fixtures/node-tickets` twice and apply the two-line change of
`evidence/port-mixup.txt` to the second copy; `node port_mixup_demo.js`;
`python3 -I port_mixup_outcomes.py <copy> <changed copy>`;
`python3 -I port_mixup_suite_probe.py <copy> <changed copy> port_mixup_count_listens.js <out.json> 16 100 30`
reproduces `evidence/port-mixup-probe.json` in kind (heavy: about 17 minutes and a load average near 190 at 16
copies; use 4 beside any other work).

Leaked test servers: `python3 -I list_leaked.py` prints one JSON line for each `node` process (it stops nothing);
`python3 -I stop_leaked.py <that listing> [<minimum age in seconds>]` stops, by process id, the parentless ones in
a folder of the base check.
The observers: `python3 test/shiploop_e2e/observers/observe.py <case> <delivered tree> [--out <file>]`; run on the
sixteen trees of round 13 it reproduces `evidence/observers-calibration.txt`.
The rebuilt rule on saved deliveries: `python3 -I gate_on_file.py <candidate>/skills/shiploop/scripts 600
<name>=<run folder>[@<release-verify action>] ...` runs the gate (with the scripts of 62676fc0e0da it reproduces
`evidence/gate-on-file.txt`; with those of 5c48bcc84ac3 and a limit of 120, `evidence/gate-on-file-final.txt`);
`replay_on_file.py` takes the same
arguments and reproduces `evidence/replay-on-file.txt`; `python3 mutate_c1.py <a copy of the candidate tree>`
reproduces `evidence/mutants-c1.txt`. The 24 run folders are the sixteen of round 13 (`e2e-runs-sdlc12/20261121`,
`e2e-runs-sdlc13/20261121`, `e2e-runs-sdlc10/20261121-paired`) and the eight of `e2e-runs-sdlc14/r15b/20261121`.

Round 13: `python3 -I quality_packets.py <out> 20261121 <name>=<medium run>,<high run> ...` builds the packets; two
judges per pair with `evidence/quality-judge-brief.txt`; their answers are `judge-quality/verdicts.json` and the key
`judge-quality/key.json`. The checks: `node quality_checks/expenses.js <tree>`, `node quality_checks/due.js <base tree>
<tree>` and `python3 -I quality_checks/suites.py <folder of trees>`, on copies of judge A's packets; their output is
in `evidence/quality-reading.txt`. The Sol extension: the same builder with seed 20261122 on the pairs of
`e2e-runs-sdlc10/20261121-paired`; `judge-quality/verdicts-sol.json` and `key-sol.json`; `node
quality_checks/rollback.js <base tree> <tree> [backfill script] [restore]`, `node quality_checks/bigsum.js <tree>` and
`python3 -I quality_checks/suites_sol.py <folder of trees>`; output in `evidence/quality-reading-sol.txt`.

Round 12: `python3 -I where_it_goes.py <run roots>` reproduces `evidence/where-it-goes.txt`;
`python3 -I context_origin.py <the five Sonnet medium run folders>` reproduces `evidence/context-origin.txt` and
`python3 -I reset_ceiling.py <the same folders>` reproduces `evidence/reset-ceiling.txt`. The five folders are
`sonnet-medium-due` and `sonnet-medium-expenses` of `e2e-runs-sdlc12/20261121`, and `assign-medium-1`,
`due-medium-2` and `expenses-medium-2` of `e2e-runs-sdlc13/20261121`.

Round 11: `python3 -I refusal_census.py <run roots>` reads the runs' traces and reproduces
`evidence/refusal-census.txt`.

Round 8: `python3 -I grok_review_scan.py grok-4.6 <run roots>` reads the runs' pass logs and reproduces
`evidence/grok-review-scan.txt`. `removed_review_diffs.py OUT <run folders> --all-stages --slices --model <model>`
builds packets for every review point of one model's runs, seeded slices included. The baseline: a detached worktree of
the registration commit, `build_arm.py <folder>` with no overlay, `run.py --case <case> --host codex --model
gpt-6.2-sol --effort high --source checkout --plugin-dir <plugin> --output <root>/<name>` from that worktree, then
`review_option_census.py runs-effort/census.json <root>` and `effort_report.py runs-reviews/census.json
runs-effort/census.json`, which reads the run folders and reproduces `evidence/effort-sol-high.txt`. The paired redo:
the same launches with medium and high started together, `review_option_census.py runs-effort-paired/census.json
<root>`, then `effort_report.py - runs-effort-paired/census.json` reproduces `evidence/effort-sol-paired.txt`.

Round 3: `python3 -I replay_score.py judge-replay` rescores from the repository alone. To run it again from the
recorded runs: `replay_cases.py <work>` (needs `<work>/census.json` and `<work>/review_edits.json`),
`replay_build.py <work>`, `replay_run.py <work>` (108 headless Claude Code sessions; about $21),
`replay_judge_packets.py <work> judge-replay 3`, two judges per packet with `evidence/replay-judge-brief.txt`,
then `replay_score.py judge-replay` and `replay_conduct.py <work>`. The reviewers' full streams (about 25 MB) stay
in the working folder and are not in the repository.
