# ShipLoop Improve value journal

Status: **interim**, 2026-10-28. Nothing in ShipLoop was changed; the owner decides whether Improve changes.

Evidence, scripts and raw labels: [docs/shiploop-improve-value-evidence/](shiploop-improve-value-evidence/).
Every table below is copied from `tables.md` there, which `analyze.py` writes from the extracted rows.

## Question

The phase A E2E round showed Improve reviews take a large share of a run's time, and on `hello` (one line of
program) their findings were in the run's own records and none in `hello.py`. The owner asked to measure what Improve changes
before scaling it to request size. This journal answers two things:

1. For every Improve review finding in recent E2E runs: did it change the product or its tests, or only the run's own
   records (spec, test strategy, plan, release plan, stage results)? By stage and by plan size (work items and steps).
2. Could the planning-stage reviews (spec, test-strategy, plan, release-plan) be skipped on one-item plans while the
   implement and test reviews stay?

## Short answer

- **The data neither support nor refute skipping the planning reviews on one-item plans. Keep them until a paired
  on/off run decides.** The data price the cost of a skip, not its benefit. Cost: on the 17 one-item plans the four
  planning reviews took 161.9 minutes, a median 3.5 minutes per run (14% of active time), for about 10 record fixes per
  run. Benefit: those fixes are substantive (a third are contradictions or checks that cannot be replayed), but no run
  has the reviews switched off, so what a missed fix costs later is unmeasured (F5, F6).
- **What the data do establish:** 62% of Improve minutes (490 of 793) went to planning and step-level reviews that changed
  no product file at any plan size; the other 38% (303.5 minutes) made all 50 product edits, 40 of them behaviour changes,
  one per 7.6 minutes. Same shape on ShipLoop 1.16 and later: 184 record-only minutes against 138 build minutes with 16
  behaviour passes (F1, F2, F10).
- **Improve's output grows with plan size on both sides.** Per run, planning fixes are 5.1, 13.0 and 35.3 and behaviour
  passes on the build side are 0, 1.5 and 3.6, for one item/one step, one item/2+ steps and 2+ items. On the 7
  one-step runs (all hello) Improve took 14.8 minutes per run (26% of active time) for 7.4 findings, 5.1 of them in
  planning, and no behaviour change (F3, F11).
- **Two cut candidates are hypotheses for that experiment, not findings:** the `plan` review (0.51 findings per minute
  against 1.1 to 1.3 for the others) and, at the thin end, Improve as a whole on one-step plans. The larger pool of
  record-only minutes is on multi-item plans (284 of 490), where the one-item skip would not apply.
- **Why Improve changed no product, mostly by design:** planning reviews are scoped to records, hello's code was one
  already-proven line, and every review stops at its first trivial pass. The template part is the schedule: all 25 runs
  used the default `planning_review: stage`, so none tried the existing `--planning-review none` (F12).
- **The "about half of active time" figure is not reproduced.** Improve pass time is a median of 28% of a completed
  run's stage time (9% to 43% over 22 runs) (F4).

## Data and method

### Runs

All 25 full runs with Improve children under `/Users/dadleet/e2e-runs/20261020` to `20261028` and
`/Users/dadleet/e2e-runs-owner-note/20261028`: the two named runs
(`pa-ds-battleship-4ed4e3`, `pc-ds-hello-note-b45e87`) and 23 earlier ones, ShipLoop 1.8.0 to 1.17.0, hosts and models
as listed in `runs.json` (Claude Sonnet 5.5, DeepSeek flash, Grok 4.7, GPT-6 Luna, Haiku 5.5). Cases: hello,
battleship, battleship-scoring, seat-reservations, csv-report, chess on Salesforce. Slice runs (`seed`) and audit
copies are excluded because they are not full runs. Three runs did not finish: `chess-sf-full-9e52e8`
stopped at release-plan, `chess-sf-full-ed3292` in the inner loop, and `haiku55-max-battleship-d521a8` at spec, where one
spec review ran 13 passes without exiting. Every run is a greenfield build from a short request; no brownfield run is in
the data.

### Units

- **Child**: one Improve review of one stage result (`.shiploop-improve/<stage>-<8 hex>/`). 275 children.
- **Pass**: one `reviews/pass-<n>.json` with its `review-<n>.md`. 520 passes; 247 labelled non-trivial by the reviewer.
- **Finding**: one distinct defect, contradiction or gap that a review reports in its `Found:` paragraph and acts on
  (or reports and leaves). 681 findings in the 273 passes that were non-trivial or edited something.

### What a pass changed (git, not the reviewer's words)

Each pass records the git tree hash of the worktree after it (`tree`). The first pass of a child is diffed against the
tree in `run/improve/<nav-id>-bind.md` (taken when the child started), each later pass against the previous pass.
`git diff-tree` names the files; the `commit` field in `pass-<n>.json` is null for many edited passes and is not used.
`result_changed` says the stage's accepted result, a file outside the tree, was edited. Files are bucketed:

- `record`: `docs/shiploop/**`
- `test`: a `test`, `tests`, `test-support`, `__tests__` or `spec` directory, or a `test_*`, `*_test.*`, `*.test.*`,
  `*.spec.*`, `*Test.cls` file
- `doc`: other markdown and `docs/`
- `code`: everything else, configuration included (this also holds test harness files outside a test directory, such
  as `system-check/system.js`; for the product-or-tests question they count with `test`)

A pass is **product** when it touched a `code` or `test` file; **records** when it edited only `record`, `doc` or the
stage result; **none** when it edited nothing. 223 of the 520 passes are in the old format (no `edited` or `result_changed` field); for 9 of them a stage-result
edit is inferred from the `Changed:` text. Eleven non-trivial passes (6 old format, 5 new; 8 of them step-plan or test-spec
reviews) left no trace in the tree or the recorded result; their `Changed:` text names run scratch scripts or the stage
result, and they are counted with records.

A **behaviour** pass is a product pass in which a labelled finding fixed in code or tests is a behaviour defect. This
needs the labels; the other product passes are comment, docstring or wrapping edits. The hello run's one product pass
is of that kind (a docstring in `test_hello.py`; commit message: "No executable statement, assertion, case or expected
value changed").

### Findings and labels

The regex split of `Found:` paragraphs is unreliable (309 of 520 paragraphs list findings in prose without numbering, and 117 state none), so findings were split
and labelled by four Sonnet 5.5 workers (default effort) from [classification-prompt.md](shiploop-improve-value-evidence/classification-prompt.md),
68 or 69 passes each, given the review text and the git facts above. For each finding: what the fix touched
(`code`, `test`, `doc`, `record`, `run-result`, `nothing`) and its nature (`behaviour-defect`,
`contradiction-or-unverifiable`, `stale-or-wrong-reference`, `missing-content`, `polish`). The prompt did not mention
the question under test. Raw outputs are in `labels/out-*.json`.

Checks: all 273 passes labelled exactly once; no label claims a `code` or `test` fix in a pass whose git diff shows none.
32 labels name a record or run-result kind that the pass's recorded changes do not show (23 of them in the 11 passes with
no recorded edit, 9 where the labeller named the stage result or a run note although `result_changed` was false); none
affects the product-or-records split.
I read the review text of all 14 passes that edited product and records together and of 8 seeded random passes against
their labels: the product-versus-record attribution agreed in all 22; finer calls (splitting one paragraph into
findings, the nature of a polish-versus-stale item) are judgement and several are arguable. No second labeller ran, so
the nature counts carry unmeasured label noise.

### Plan size

From each run's `run/state.md`: work items planned (the accepted `plan` result) and steps (the first accepted
`step-plan` result per item). Three classes: **1 item, 1 step** (7 runs, all hello), **1 item, 2+ steps** (10 runs:
battleship, battleship-scoring, seat-reservations, csv-report, one DeepSeek hello), **2+ items** (7 runs: three chess,
one Grok battleship, three DeepSeek battleships). The haiku run never reached a plan and is in no size class.

### Time

`seconds` per pass from `run/improve/<nav-id>/passes.md`. Active time is the sum of stage seconds in the run's
`metrics.json` (within 2% of the wall time of every run). Pass seconds agree with `review_seconds` in `metrics.json` within 3%
for the 145 children that have both; two children (the haiku spec review and one release-plan review in `chess-sf-full-9e52e8`) have no seconds.

### Stage groups

planning = spec, test-strategy, plan, release-plan (the stages in the proposal); step-level planning = step-plan,
test-spec (`test-spec` no longer exists from ShipLoop 1.16); build = implement, system-test-author; carry-forward.

## Results

### Named run: battleship (DeepSeek flash, ShipLoop 1.17.0)

Model `deepseek-v4.1-flash:1017-cloud`, ShipLoop 1.17.0, plan: 3 planned items (1 added later), 8 steps; active 372.5 min, Improve 102.3 min.

| stage | item | passes | passes (N non-trivial / T trivial; what the pass edited) | findings | product / records / unacted | min | files changed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spec | - | 4 | 1 N records; 2 N records; 3 N records; 4 T records | 27 | 0 / 27 / 0 | 15.8 | `docs/shiploop/spec.md` x4, stage result |
| test-strategy | - | 4 | 1 N records; 2 N records; 3 N records; 4 T records | 14 | 0 / 14 / 0 | 14.4 | `docs/shiploop/architecture.md` x4, `docs/shiploop/environment.md` x4 |
| plan | - | 5 | 1 N records; 2 N records; 3 N records; 4 N records; 5 T none | 8 | 0 / 8 / 0 | 13.7 | `docs/shiploop/architecture.md` x2, `docs/shiploop/environment.md` x2 |
| release-plan | - | 3 | 1 N records; 2 N records; 3 T none | 8 | 0 / 8 / 0 | 7.7 | `docs/shiploop/environment.md` x2, stage result |
| release-plan | - | 2 | 1 N records; 2 T none | 3 | 0 / 3 / 0 | 3.8 | `docs/shiploop/environment.md`, stage result |
| step-plan | W1 | 3 | 1 N records; 2 N records; 3 T none | 6 | 0 / 6 / 0 | 8.0 | stage result |
| step-plan | W4 | 1 | 1 T none | 0 | 0 / 0 / 0 | 2.5 | - |
| implement | W1 | 2 | 1 N product-behaviour; 2 T records | 4 | 2 / 0 / 2 | 4.8 | `rules.js`, `test-support/random.js`, stage result |
| implement | W2 | 2 | 1 N product-behaviour; 2 T none | 5 | 5 / 0 / 0 | 10.2 | `page.js`, `server.js` |
| implement | W3 | 2 | 1 N product-behaviour; 2 T none | 1 | 1 / 0 / 0 | 5.7 | `test-support/browser.js` |
| implement | W4 | 1 | 1 T none | 0 | 0 / 0 / 0 | 0.9 | - |
| system-test-author | - | 3 | 1 N records; 2 N product-behaviour; 3 T none | 5 | 1 / 4 / 0 | 5.2 | `docs/shiploop/environment.md` x2, `docs/shiploop/system-tests.md`, `test/system.test.js`, stage result |
| system-test-author | - | 2 | 1 N records; 2 T product-comments | 5 | 1 / 4 / 0 | 2.2 | `docs/shiploop/environment.md`, `docs/shiploop/spec.md`, `docs/shiploop/system-tests.md`, `test/system.test.js` |
| carry-forward | W3 | 2 | 1 N product-behaviour; 2 T none | 3 | 2 / 0 / 1 | 5.8 | `docs/shiploop/environment.md`, `docs/shiploop/spec.md`, `rules.js`, `test-support/browser.js`, +2 more files |
| carry-forward | W4 | 1 | 1 T none | 0 | 0 / 0 / 0 | 1.5 | - |

The R-5.1 versus R-5.4 contradiction in the spec is finding 1 of spec pass 1 (27 findings over four spec passes).
The six product passes: `createGame` accepted an array and silently built a random fleet, `seeded` accepted a seed that
replayed seed 0, the page re-enabled a fired cell and applied a stale reply after New game (W2), `withPage` ignored
`Page.navigate` errors (W3), a symbol coordinate threw a `TypeError` in a refusal message and a launch timeout leaked
Chrome (carry-forward), a system-test assertion that could never fail (system-test-author), plus one line-wrap edit.

### Named run: hello (DeepSeek flash, ShipLoop 1.17.0)

Model `deepseek-v4.1-flash:1017-cloud`, ShipLoop 1.17.0, plan: 1 planned items (0 added later), 1 steps; active 152.3 min, Improve 42.0 min.

| stage | item | passes | passes (N non-trivial / T trivial; what the pass edited) | findings | product / records / unacted | min | files changed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spec | - | 3 | 1 N records; 2 N records; 3 T none | 5 | 0 / 5 / 0 | 5.0 | `docs/shiploop/spec.md` x2 |
| test-strategy | - | 2 | 1 N records; 2 T none | 6 | 0 / 6 / 0 | 7.4 | `docs/shiploop/architecture.md`, `docs/shiploop/environment.md`, stage result |
| plan | - | 2 | 1 N records; 2 T none | 4 | 0 / 4 / 0 | 6.2 | `docs/shiploop/architecture.md`, stage result |
| release-plan | - | 2 | 1 N records; 2 T records | 3 | 0 / 3 / 0 | 2.7 | `docs/shiploop/environment.md` x2, stage result |
| step-plan | W1 | 1 | 1 T none | 0 | 0 / 0 / 0 | 0.8 | - |
| implement | W1 | 1 | 1 T none | 0 | 0 / 0 / 0 | 2.4 | - |
| system-test-author | - | 4 | 1 N records; 2 N records; 3 N records; 4 T records | 8 | 0 / 8 / 0 | 12.6 | `docs/shiploop/environment.md` x3, `docs/shiploop/architecture.md` x2, stage result |
| carry-forward | W1 | 2 | 1 N product-comments; 2 T records | 2 | 1 / 1 / 0 | 4.9 | `test_hello.py`, `docs/shiploop/architecture.md` |

Nine non-trivial passes (probably the "9 things" in the brief), 28 findings, 27 of them in records. The one product edit
is the docstring.

### Improve minutes and product edits, by stage group

| runs | stage group | passes | min | share of Improve min | passes editing product | behaviour passes | findings | f: product | f: records | min per behaviour pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all 25 runs | planning | 250 | 369.3 | 47% | 0 | 0 | 471 | 0 | 469 | - |
| all 25 runs | step-level planning | 81 | 120.5 | 15% | 0 | 0 | 49 | 0 | 47 | - |
| all 25 runs | build + carry-forward | 189 | 303.5 | 38% | 50 | 40 | 161 | 89 | 65 | 7.6 |
| ShipLoop 1.16 and later (5 runs) | planning | 72 | 162.8 | 51% | 0 | 0 | 179 | 0 | 179 | - |
| ShipLoop 1.16 and later (5 runs) | step-level planning | 10 | 21.4 | 7% | 0 | 0 | 9 | 0 | 9 | - |
| ShipLoop 1.16 and later (5 runs) | build + carry-forward | 48 | 137.6 | 43% | 19 | 16 | 81 | 41 | 36 | 8.6 |

### How Improve scales with plan size, per run

| plan size | runs | active min | Improve min | Improve share | planning min | planning fixes | build behaviour passes | behaviour passes / build passes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 item, 1 step | 7 | 57.5 | 14.8 | 26% | 7.7 | 5.1 | 0.0 | 0 / 27 |
| 1 item, 2+ steps | 10 | 62.0 | 21.9 | 35% | 10.8 | 13.0 | 1.5 | 15 / 72 |
| 2+ items | 7 | 310.2 | 67.2 | 22% | 29.6 | 35.3 | 3.6 | 25 / 90 |

### What each review was given, and when it stopped

Scope is the `context.scope` text in each child's `start.json`; it names product files only when it lists "Files this item changed" or "Files the executed items changed". Every run used `planning_review: stage`.

| stage | reviews | scope names product files | stop rule: 1 trivial pass | reviews that edited nothing | passes | passes that edited nothing | of which the review's last pass |
| --- | --- | --- | --- | --- | --- | --- | --- |
| spec | 25 | 0 | 25 | 2 | 94 | 19 | 19 |
| test-strategy | 24 | 0 | 24 | 3 | 67 | 21 | 21 |
| plan | 24 | 0 | 24 | 8 | 47 | 24 | 24 |
| release-plan | 24 | 0 | 24 | 11 | 42 | 20 | 20 |
| step-plan | 31 | 0 | 31 | 16 | 48 | 30 | 30 |
| test-spec | 25 | 0 | 25 | 17 | 33 | 24 | 24 |
| implement | 73 | 73 | 73 | 38 | 105 | 64 | 64 |
| system-test-author | 25 | 0 | 25 | 15 | 42 | 23 | 23 |
| carry-forward | 24 | 24 | 24 | 10 | 42 | 22 | 22 |

### All runs, by stage

| stage | group | children | passes | non-trivial | passes editing product | of which behaviour | passes editing records only | passes editing nothing | findings | product | records | unacted | min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spec | planning | 25 | 94 | 70 | 0 | 0 | 75 | 19 | 231 | 0 | 231 | 0 | 139.6 |
| test-strategy | planning | 24 | 67 | 43 | 0 | 0 | 46 | 21 | 141 | 0 | 139 | 2 | 108.0 |
| plan | planning | 24 | 47 | 23 | 0 | 0 | 23 | 24 | 47 | 0 | 47 | 0 | 73.8 |
| release-plan | planning | 24 | 42 | 19 | 0 | 0 | 22 | 20 | 52 | 0 | 52 | 0 | 47.9 |
| step-plan | step-level planning | 31 | 48 | 17 | 0 | 0 | 18 | 30 | 34 | 0 | 33 | 1 | 83.5 |
| test-spec | step-level planning | 25 | 33 | 8 | 0 | 0 | 9 | 24 | 15 | 0 | 14 | 1 | 37.0 |
| implement | build | 73 | 105 | 32 | 35 | 27 | 6 | 64 | 75 | 65 | 6 | 4 | 144.3 |
| system-test-author | build | 25 | 42 | 17 | 8 | 7 | 11 | 23 | 46 | 11 | 34 | 1 | 78.8 |
| carry-forward | carry-forward | 24 | 42 | 18 | 7 | 6 | 13 | 22 | 40 | 13 | 25 | 2 | 80.4 |

### By plan size and stage group

Plan size is the planned work items and the steps of the first accepted step plans.

| plan size | runs | group | children | passes | non-trivial | product | behaviour | records only | nothing | findings | f: product | f: records | f: unacted | min total | min per run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 item, 1 step | 7 | planning | 28 | 45 | 17 | 0 | 0 | 19 | 26 | 36 | 0 | 36 | 0 | 53.9 | 7.7 |
| 1 item, 1 step | 7 | step-level planning | 15 | 18 | 3 | 0 | 0 | 3 | 15 | 3 | 0 | 3 | 0 | 17.4 | 2.5 |
| 1 item, 1 step | 7 | build | 14 | 17 | 3 | 1 | 0 | 4 | 12 | 9 | 1 | 8 | 0 | 22.9 | 3.3 |
| 1 item, 1 step | 7 | carry-forward | 7 | 10 | 3 | 1 | 0 | 3 | 6 | 4 | 1 | 3 | 0 | 9.5 | 1.4 |
| 1 item, 2+ steps | 10 | planning | 40 | 90 | 50 | 0 | 0 | 51 | 39 | 132 | 0 | 130 | 2 | 108.0 | 10.8 |
| 1 item, 2+ steps | 10 | step-level planning | 18 | 28 | 10 | 0 | 0 | 10 | 18 | 14 | 0 | 13 | 1 | 26.5 | 2.6 |
| 1 item, 2+ steps | 10 | build | 33 | 55 | 22 | 17 | 14 | 6 | 32 | 32 | 21 | 10 | 1 | 55.9 | 5.6 |
| 1 item, 2+ steps | 10 | carry-forward | 10 | 17 | 7 | 1 | 1 | 7 | 9 | 15 | 3 | 12 | 0 | 28.6 | 2.9 |
| 2+ items | 7 | planning | 28 | 102 | 75 | 0 | 0 | 83 | 19 | 247 | 0 | 247 | 0 | 207.3 | 29.6 |
| 2+ items | 7 | step-level planning | 23 | 35 | 12 | 0 | 0 | 14 | 21 | 32 | 0 | 31 | 1 | 76.5 | 10.9 |
| 2+ items | 7 | build | 51 | 75 | 24 | 25 | 20 | 7 | 43 | 80 | 54 | 22 | 4 | 144.2 | 20.6 |
| 2+ items | 7 | carry-forward | 7 | 15 | 8 | 5 | 5 | 3 | 7 | 21 | 9 | 10 | 2 | 42.3 | 6.0 |

### By plan size and stage

| plan size | stage | children | passes | product | behaviour | records only | nothing | children edited in pass 1 | findings | f: product | f: records | min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 item, 1 step | spec | 7 | 13 | 0 | 0 | 7 | 6 | 5 | 14 | 0 | 14 | 15.5 |
| 1 item, 1 step | test-strategy | 7 | 11 | 0 | 0 | 4 | 7 | 4 | 9 | 0 | 9 | 12.0 |
| 1 item, 1 step | plan | 7 | 11 | 0 | 0 | 4 | 7 | 4 | 7 | 0 | 7 | 17.1 |
| 1 item, 1 step | release-plan | 7 | 10 | 0 | 0 | 4 | 6 | 3 | 6 | 0 | 6 | 9.3 |
| 1 item, 1 step | step-plan | 8 | 11 | 0 | 0 | 3 | 8 | 3 | 3 | 0 | 3 | 9.1 |
| 1 item, 1 step | test-spec | 7 | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 8.3 |
| 1 item, 1 step | implement | 7 | 7 | 1 | 0 | 0 | 6 | 1 | 1 | 1 | 0 | 6.2 |
| 1 item, 1 step | system-test-author | 7 | 10 | 0 | 0 | 4 | 6 | 1 | 8 | 0 | 8 | 16.7 |
| 1 item, 1 step | carry-forward | 7 | 10 | 1 | 0 | 3 | 6 | 3 | 4 | 1 | 3 | 9.5 |
| 1 item, 2+ steps | spec | 10 | 29 | 0 | 0 | 19 | 10 | 10 | 56 | 0 | 56 | 39.0 |
| 1 item, 2+ steps | test-strategy | 10 | 27 | 0 | 0 | 17 | 10 | 10 | 48 | 0 | 46 | 38.3 |
| 1 item, 2+ steps | plan | 10 | 18 | 0 | 0 | 8 | 10 | 6 | 12 | 0 | 12 | 20.2 |
| 1 item, 2+ steps | release-plan | 10 | 16 | 0 | 0 | 7 | 9 | 4 | 16 | 0 | 16 | 10.4 |
| 1 item, 2+ steps | step-plan | 10 | 16 | 0 | 0 | 6 | 10 | 5 | 10 | 0 | 9 | 21.4 |
| 1 item, 2+ steps | test-spec | 8 | 12 | 0 | 0 | 4 | 8 | 4 | 4 | 0 | 4 | 5.1 |
| 1 item, 2+ steps | implement | 23 | 39 | 15 | 12 | 2 | 22 | 15 | 22 | 19 | 2 | 33.1 |
| 1 item, 2+ steps | system-test-author | 10 | 16 | 2 | 2 | 4 | 10 | 4 | 10 | 2 | 8 | 22.8 |
| 1 item, 2+ steps | carry-forward | 10 | 17 | 1 | 1 | 7 | 9 | 7 | 15 | 3 | 12 | 28.6 |
| 2+ items | spec | 7 | 39 | 0 | 0 | 36 | 3 | 7 | 105 | 0 | 105 | 85.1 |
| 2+ items | test-strategy | 7 | 29 | 0 | 0 | 25 | 4 | 7 | 84 | 0 | 84 | 57.6 |
| 2+ items | plan | 7 | 18 | 0 | 0 | 11 | 7 | 6 | 28 | 0 | 28 | 36.4 |
| 2+ items | release-plan | 7 | 16 | 0 | 0 | 11 | 5 | 6 | 30 | 0 | 30 | 28.2 |
| 2+ items | step-plan | 13 | 21 | 0 | 0 | 9 | 12 | 7 | 21 | 0 | 21 | 53.0 |
| 2+ items | test-spec | 10 | 14 | 0 | 0 | 5 | 9 | 4 | 11 | 0 | 10 | 23.5 |
| 2+ items | implement | 43 | 59 | 19 | 15 | 4 | 36 | 19 | 52 | 45 | 4 | 105.0 |
| 2+ items | system-test-author | 8 | 16 | 6 | 5 | 3 | 7 | 5 | 28 | 9 | 18 | 39.2 |
| 2+ items | carry-forward | 7 | 15 | 5 | 5 | 3 | 7 | 4 | 21 | 9 | 10 | 42.3 |

### Planning stages on one-item plans

| stage | children | passes | product | records only | nothing | children edited in pass 1 | findings acted on | contradiction / unverifiable | behaviour defect | stale / wrong reference | missing content | polish | min | min in passes that edited nothing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spec | 17 | 42 | 0 | 26 | 16 | 15 | 70 | 26 | 3 | 2 | 36 | 3 | 54.5 | 6.6 |
| test-strategy | 17 | 38 | 0 | 21 | 17 | 14 | 57 | 18 | 2 | 12 | 22 | 1 | 50.4 | 7.8 |
| plan | 17 | 29 | 0 | 12 | 17 | 10 | 19 | 4 | 0 | 3 | 10 | 2 | 37.3 | 19.8 |
| release-plan | 17 | 26 | 0 | 11 | 15 | 7 | 22 | 7 | 3 | 6 | 4 | 2 | 19.7 | 7.9 |

### Planning stages on one-item plans, by pass number

| pass | passes | passes that edited | findings acted on | min |
| --- | --- | --- | --- | --- |
| 1 | 68 | 46 | 123 | 115.4 |
| 2 | 45 | 19 | 36 | 36.5 |
| 3 | 18 | 4 | 6 | 7.9 |
| 4+ | 4 | 1 | 1 | 2.1 |

### Record fixes by stage, one-item plans

| stage group | record-only findings | contradiction / unverifiable | stale / wrong reference | missing content | behaviour defect | polish |
| --- | --- | --- | --- | --- | --- | --- |
| planning | 166 | 55 | 23 | 72 | 8 | 8 |
| step-level planning | 16 | 8 | 0 | 2 | 6 | 0 |
| build | 18 | 8 | 5 | 2 | 1 | 2 |
| carry-forward | 15 | 4 | 10 | 1 | 0 | 0 |

### Nature of acted-on findings, all runs

| group | findings | behaviour defect | contradiction / unverifiable | stale / wrong reference | missing content | polish |
| --- | --- | --- | --- | --- | --- | --- |
| planning | 469 | 45 | 139 | 65 | 199 | 21 |
| step-level planning | 47 | 9 | 24 | 5 | 9 | 0 |
| build | 116 | 56 | 14 | 10 | 15 | 21 |
| carry-forward | 38 | 12 | 5 | 18 | 3 | 0 |

### Planning-stage Improve cost, one-item runs

| run | model | ShipLoop | plan size | planning passes | planning min | share of active | all Improve min | active min |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261028/pc-ds-hello-note-b45e87 | deepseek-v4.1-flash: | 1.17.0 | 1 item, 1 step | 9 | 21.4 | 14% | 42.0 | 152.3 |
| 20261024/gate-290-b60ed7-claude-batch/battle | claude-sonnet-5-5 | 1.9.0 | 1 item, 2+ steps | 10 | 3.5 | 18% | 6.3 | 19.4 |
| 20261024/gate-290-b60ed7-claude-batch/hello | claude-sonnet-5-5 | 1.9.0 | 1 item, 1 step | 4 | 1.0 | 10% | 2.5 | 10.2 |
| 20261024/gate-290-b60ed7-claude-batch/seat-r | claude-sonnet-5-5 | 1.9.0 | 1 item, 2+ steps | 7 | 2.1 | 10% | 5.4 | 20.7 |
| 20261024/gate-290-b60ed7-claude-csv-report | claude-sonnet-5-5 | 1.9.0 | 1 item, 2+ steps | 10 | 4.6 | 15% | 10.9 | 30.0 |
| 20261024/gate-290-b60ed7-codex-hello | gpt-6-luna | 1.9.0 | 1 item, 1 step | 5 | 19.3 | 15% | 32.7 | 124.6 |
| 20261025/gate-2100-96810d-claude-web/battles | claude-sonnet-5-5 | 1.10.0 | 1 item, 2+ steps | 8 | 2.5 | 11% | 6.0 | 22.9 |
| 20261025/gate-2100-96810d-claude-web/battles | claude-sonnet-5-5 | 1.10.1 | 1 item, 2+ steps | 8 | 3.3 | 14% | 7.0 | 23.3 |
| 20261025/gate-2132-f7ba78-grok-hello | grok-4.7 | 1.13.1 | 1 item, 1 step | 5 | 4.4 | 6% | 12.2 | 68.1 |
| 20261025/gate-2132-f7ba78-grok-web/battleshi | grok-4.7 | 1.13.1 | 1 item, 2+ steps | 8 | 15.0 | 13% | 32.5 | 113.7 |
| 20261025/trace-verify-1131-b096ae/hello | claude-sonnet-5-5 | 1.13.1 | 1 item, 1 step | 9 | 2.8 | 21% | 4.7 | 13.1 |
| 20261025/trace-verify-4fd9f1/hello | claude-sonnet-5-5 | 1.12.0 | 1 item, 1 step | 7 | 2.9 | 13% | 6.0 | 22.8 |
| 20261026/live-sonnet-battleship-01b9b3 | claude-sonnet-5-5 | 1.15.0 | 1 item, 2+ steps | 7 | 3.1 | 9% | 8.0 | 36.6 |
| 20261026/live-sonnet-hello-b01d1c | claude-sonnet-5-5 | 1.15.0 | 1 item, 1 step | 6 | 2.1 | 18% | 3.7 | 11.6 |
| 20261026/pilot-ollama-dsflash-993a9d-hello | deepseek-v4.1-flash: | 1.15.0 | 1 item, 2+ steps | 13 | 15.7 | 27% | 25.0 | 58.0 |
| 20261027/v2170-sonnet-battleship-491d9a | claude-sonnet-5-5 | 1.16.0 | 1 item, 2+ steps | 8 | 53.3 | 20% | 108.3 | 262.5 |
| 20261027/v2180-sonnet-battleship-36036c | claude-sonnet-5-5 | 1.17.0 | 1 item, 2+ steps | 11 | 4.9 | 15% | 9.7 | 32.5 |

### Per run

| run | case | model | ShipLoop | items | steps | children | passes | product passes | planning product passes | planning min | Improve min | active min | Improve share | final stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20261028/pc-ds-hello-note-b45e87 | hello | deepseek-v4.1-flash:10 | 1.17.0 | 1 | 1 | 8 | 17 | 1 | 0 | 21.4 | 42.0 | 152.3 | 28% | done |
| 20261020/chess-sf-full-9e52e8 | chess-salesforce | grok-4.7 | 1.8.0 | 3 | 3 | 14 | 26 | 2 | 0 | 30.3 | 70.4 | 239.6 | 29% | release-plan |
| 20261024/chess-sf-full-12a23d | chess-salesforce | grok-4.7 | 1.9.0 | 3 | 10 | 27 | 41 | 5 | 0 | 22.1 | 75.6 | 873.1 | 9% | done |
| 20261024/chess-sf-full-ed3292 | chess-salesforce | grok-4.7 | 1.9.0 | 3 | 1 | 5 | 14 | 0 | 0 | 23.9 | 34.2 | 92.8 | 37% | inner-loop |
| 20261024/gate-290-b60ed7-claude-batch/battleship | battleship | claude-sonnet-5-5 | 1.9.0 | 1 | 3 | 11 | 19 | 1 | 0 | 3.5 | 6.3 | 19.4 | 32% | done |
| 20261024/gate-290-b60ed7-claude-batch/hello | hello | claude-sonnet-5-5 | 1.9.0 | 1 | 1 | 9 | 9 | 0 | 0 | 1.0 | 2.5 | 10.2 | 24% | done |
| 20261024/gate-290-b60ed7-claude-batch/seat-reser | seat-reservations | claude-sonnet-5-5 | 1.9.0 | 1 | 2 | 10 | 15 | 0 | 0 | 2.1 | 5.4 | 20.7 | 26% | done |
| 20261024/gate-290-b60ed7-claude-csv-report | csv-report | claude-sonnet-5-5 | 1.9.0 | 1 | 4 | 12 | 23 | 2 | 0 | 4.6 | 10.9 | 30.0 | 36% | done |
| 20261024/gate-290-b60ed7-codex-hello | hello | gpt-6-luna | 1.9.0 | 1 | 1 | 9 | 11 | 0 | 0 | 19.3 | 32.7 | 124.6 | 26% | done |
| 20261025/gate-2100-96810d-claude-web/battleship | battleship | claude-sonnet-5-5 | 1.10.0 | 1 | 2 | 10 | 18 | 4 | 0 | 2.5 | 6.0 | 22.9 | 26% | done |
| 20261025/gate-2100-96810d-claude-web/battleship- | battleship-scoring | claude-sonnet-5-5 | 1.10.1 | 1 | 3 | 11 | 19 | 2 | 0 | 3.3 | 7.0 | 23.3 | 30% | done |
| 20261025/gate-2132-f7ba78-grok-hello | hello | grok-4.7 | 1.13.1 | 1 | 1 | 9 | 10 | 0 | 0 | 4.4 | 12.2 | 68.1 | 18% | done |
| 20261025/gate-2132-f7ba78-grok-web/battleship | battleship | grok-4.7 | 1.13.1 | 2 | 5 | 16 | 25 | 1 | 0 | 25.9 | 48.9 | 205.4 | 24% | done |
| 20261025/gate-2132-f7ba78-grok-web/battleship-sc | battleship-scoring | grok-4.7 | 1.13.1 | 1 | 2 | 10 | 17 | 2 | 0 | 15.0 | 32.5 | 113.7 | 29% | done |
| 20261025/haiku55-max-battleship-d521a8 | battleship | claude-haiku-5-5 | 1.11.0 | None | None | 1 | 13 | 0 | 0 | 0.0 | 0.0 | 34.6 | 0% | spec |
| 20261025/trace-verify-1131-b096ae/hello | hello | claude-sonnet-5-5 | 1.13.1 | 1 | 1 | 9 | 16 | 0 | 0 | 2.8 | 4.7 | 13.1 | 36% | done |
| 20261025/trace-verify-4fd9f1/hello | hello | claude-sonnet-5-5 | 1.12.0 | 1 | 1 | 11 | 15 | 1 | 0 | 2.9 | 6.0 | 22.8 | 26% | done |
| 20261026/ds-flash-978478-battleship | battleship | deepseek-v4.1-flash:10 | 1.15.0 | 3 | 12 | 22 | 43 | 8 | 0 | 22.0 | 79.6 | 222.1 | 36% | done |
| 20261026/live-sonnet-battleship-01b9b3 | battleship | claude-sonnet-5-5 | 1.15.0 | 1 | 3 | 11 | 20 | 3 | 0 | 3.1 | 8.0 | 36.6 | 22% | done |
| 20261026/live-sonnet-hello-b01d1c | hello | claude-sonnet-5-5 | 1.15.0 | 1 | 1 | 9 | 12 | 0 | 0 | 2.1 | 3.7 | 11.6 | 32% | done |
| 20261026/pilot-ollama-dsflash-993a9d-hello | hello | deepseek-v4.1-flash:10 | 1.15.0 | 1 | 2 | 10 | 24 | 0 | 0 | 15.7 | 25.0 | 58.0 | 43% | done |
| 20261027/v2170-ds-battleship-759a03 | battleship | deepseek-v4.1-flash:10 | 1.16.0 | 3 | 9 | 10 | 41 | 8 | 0 | 27.8 | 59.5 | 165.7 | 36% | done |
| 20261027/v2170-sonnet-battleship-491d9a | battleship | claude-sonnet-5-5 | 1.16.0 | 1 | 3 | 8 | 14 | 1 | 0 | 53.3 | 108.3 | 262.5 | 41% | done |
| 20261027/v2180-sonnet-battleship-36036c | battleship | claude-sonnet-5-5 | 1.17.0 | 1 | 3 | 8 | 21 | 3 | 0 | 4.9 | 9.7 | 32.5 | 30% | done |
| 20261028/pa-ds-battleship-4ed4e3 | battleship | deepseek-v4.1-flash:10 | 1.17.0 | 3 | 8 | 15 | 37 | 6 | 0 | 55.4 | 102.3 | 372.5 | 27% | done |

## Findings

Status: firm = counted from git and the run records; interim = rests on the labels or on a small n;
exploratory = a pattern worth testing, not a result.

**F1 (firm). Planning reviews edit records only.** 0 of 250 planning passes touched a product file (spec 94, test-strategy
67, plan 47, release-plan 42); 166 edited records or the stage result. Release-plan runs after the code exists and
its 42 passes still touched no product file. Evidence: `passes.json` (`stage`, `outcome`), "All runs, by stage".
Not an argument either way: the artifact under review is a record.

**F2 (firm). Product edits come from three stages.** implement 35 of 105 passes edited product (27 changed behaviour),
system-test-author 8 of 42 (7), carry-forward 7 of 42 (6). Total 50 product passes, 40 behaviour. 89 of the 681 findings
touched code or tests: 66 behaviour defects, 18 polish, 5 missing content. Evidence: `findings.json`, `summary.json`.

**F3 (interim). Product yield scales with plan size.** Behaviour passes among build and carry-forward passes: 0 of 27
(1 item, 1 step), 15 of 72 (1 item, 2+ steps), 25 of 90 (2+ items). The zero rests on seven hello runs, one of them
the DeepSeek named run. Evidence: "By plan size and stage group" (`behaviour` column), `summary.json`.

**F4 (firm). Improve is about 28% of a completed run, not half.** Pass seconds divided by stage seconds over the 22
completed runs: median 28.1%, range 8.7% to 43%. Improve passes total 793 minutes, of which planning stages 369 (47%).
The named runs: battleship 102.3 of 372.5 minutes (27%), hello 42.0 of 152.3 (28%). The owner's "half" may use another
denominator (for example model-active time); I did not find one that gives 50%.

**F5 (interim). The planning findings are substantive in kind.** Across all runs 469 planning findings were acted on:
139 contradictions or checks that cannot be replayed (30%), 199 missing content (42%), 65 stale or wrong references
(14%), 45 defects in what the record tells a later stage to do (10%), 21 polish (4%). On one-item plans: 166 fixes,
55 / 72 / 23 / 8 / 8 in the same order. Examples on one-item plans: a release-plan consumer check
(`node --test`) that passes on an empty copy or when zero tests run (battleship, v2170 and v2180 Sonnet runs), a rollback
using `git reset --hard` (battleship, hello), runnable commands containing a `<kept paths>` placeholder (grok hello,
pilot hello), a plan check `git diff --stat` that is vacuous for an untracked file (hello). These sit in records that
later stages execute or quote.

**F6 (firm for cost). Planning reviews cost a median 3.5 minutes per one-item run, with a wide spread by harness
version and model.** Across 17 one-item runs: 135 planning passes, 161.9 minutes, 50% of those runs' Improve time. Per run
median 210 s, range 62 s to 3,199 s, 14.2% of active time (6.4% to 27%). By model family (median planning seconds):
Claude 181 (12 runs), Grok 580 (2), DeepSeek 1,112 (2), GPT-6 Luna 1,159 (1). The same Sonnet battleship case cost 53.3
planning minutes on ShipLoop 1.16.0 and 4.9 on 1.17.0, so any mean saving carries that spread. Per stage, one-item plans:

| stage | minutes per run | findings | findings per minute | children edited in pass 1 | minutes in passes that edited nothing |
| --- | --- | --- | --- | --- | --- |
| spec | 3.2 | 70 | 1.28 | 15 of 17 | 6.6 of 54.5 |
| test-strategy | 3.0 | 57 | 1.13 | 14 of 17 | 7.8 of 50.4 |
| plan | 2.2 | 19 | 0.51 | 10 of 17 | 19.8 of 37.3 |
| release-plan | 1.2 | 22 | 1.12 | 7 of 17 | 7.9 of 19.7 |

**F7 (interim). Later stages still fix records on one-item plans.** Record-only fixes by stage group: planning 166,
step-level planning 16, build 18, carry-forward 15; contradictions or unreplayable checks among them 55, 8, 8, 4. So
23% of the record-only fixes (49 of 215) are made after planning, by step-plan, build and carry-forward reviews. The
stages look at overlapping records, but the data cannot say how many of the planning-stage defects those later reviews
would have caught.

**F8 (firm). The second and later passes of a planning review find 26% of the fixes in 29% of the time.**
Planning stages on one-item plans: pass 1 is 68 passes, 123 fixes, 115.4 minutes; passes 2 and later are 67 passes,
43 fixes, 46.5 minutes (29% of the time, 26% of the fixes). The owner asked to be consulted before any loop limit is
added or changed, so this is a measurement, not a recommendation.

**F9 (exploratory). The smallest plans show the lowest return from every stage, not only planning.** On the seven
one-item one-step runs all stages together: 90 passes, 103.7 minutes (14.8 per run), 52 findings, 2 product passes,
both docstring edits. Implement reviews there: 7 passes, 1 product edit (a docstring), 6.2 minutes; carry-forward:
10 passes, 1 product edit (a docstring), 9.5 minutes. Seven runs, one task family, so this is a pattern to test.

**F10 (firm). Where Improve's minutes go is not where its product edits come from.** Planning 369.3 min (47%) and
step-level planning 120.5 min (15%) changed no product file in 331 passes; build and carry-forward 303.5 min (38%) made
all 50 product edits. On ShipLoop 1.16 and later: planning 162.8 min and step-level 21.4 min, 0 product edits; build
137.6 min, 19 product passes, 16 behaviour. Evidence: "Improve minutes and product edits, by stage group".

**F11 (interim). Both sides of Improve grow with plan size.** Per run, planning fixes 5.1, 13.0, 35.3 and build
behaviour passes 0.0, 1.5, 3.6 across the three plan-size classes; Improve is 26%, 35% and 22% of active time.
Evidence: "How Improve scales with plan size, per run". The one-step class is seven hello runs.

**F12 (firm for the mechanics). Why most Improve passes change no product file, and which part is the template.**
1. *Planning reviews are scoped to records by design.* Each child's `context.scope` (`start.json`) names the stage result
   and "the knowledge files it worked from, under docs/shiploop"; it names product files for implement and carry-forward
   only (97 of 275 reviews). `skills/shiploop/references/improve-stages.md` gives the intent: these stages "write the
   contracts that later work is built on", and their handoffs focus on steps or examples that can't be replayed,
   expected results a weaker stand-in would pass, commands that don't run what they claim, and dropped IDs. The labelled
   findings match that focus (F5). The prompt does what it was written to do; product edits are the wrong yardstick here.
2. *Small, already-proven code leaves nothing to fix.* `hello.py` is `print("Hello, world!")`, checked by the step's
   proof before the review; the implement reviewer reported "nothing material" (`passes.json`, field `found`, hello
   `implement-d09d307c` pass 1). Half of all implement reviews (38 of 73) edited nothing.
3. *Every review stops at its first trivial pass* (`required_trivial_reviews: 1` in all 275 children; owner decision
   2026-10-20). All 247 passes that edited nothing are a review's last pass, and 120 reviews found nothing in their only pass.
4. *The template part is the schedule.* All 25 runs used the default `planning_review: stage` (`runs.json`), which starts
   the same planning reviews whatever the request size: hello got 8 reviews, 17 passes and 42 minutes for one line.
   `--planning-review none` already exists (`references/run-options.md`, "Planning review option"): it drops the reviews
   after spec, test-strategy, plan and step-plan and keeps implement, system-test-author, release-plan and the last
   carry-forward. No run used it, which is why the planning reviews' benefit is unmeasured.
5. *Ordering limits a plan-size rule.* In every run spec and test-strategy finish before the plan exists, so a rule keyed
   on the plan's item count can only govern the reviews from the plan onward; spec and test-strategy would need a guess
   from the request.
6. *A small scope gap.* system-test-author's scope names no files although that stage writes tests; 8 of its 42 passes
   edited test or test-harness files anyway.

Open: recall. Whether the reviews miss defects that exist is unmeasured; a seeded-defect check would answer it.

## Recommendation (interim)

Marked interim: 17 one-item runs, 3 of them on the current harness (1.16.0 and later), one labelling pass, no
counterfactual, one task family for the one-step class.

**1. Keep the planning reviews on one-item plans for now.** A skip is a bet that the record fixes are worth less than the
minutes. The minutes are known (median 3.5 per run, 14% of active time). The fixes are real but unpriced: 166 on one-item
plans, 55 of them contradictions or unreplayable checks, several in records later stages act on (a release check that
passes with zero tests, a rollback using `git reset --hard`). Later stages already fix some records (23% of record-only
fixes, F7), so there is overlap, but how much is unknown. The saving is small against that uncertainty.

**2. Run the paired experiment before cutting anything, with the existing flag.** Hello and battleship, three runs each per
arm, one model and one harness version, `--planning-review stage` versus `--planning-review none`; no ShipLoop change is
needed. `none` keeps the release-plan review and drops the step-plan review, so it differs from the proposal there (F12). Compare (a) record defects the implement and system-test
reviews then find, (b) their behaviour changes, (c) the release stage's own failures and send-backs, (d) minutes.
`extract.py` and `analyze.py` already produce (a), (b) and (d) from any run folder.

**3. Hypotheses to put in that experiment.** (a) The `plan` review: lowest yield (19 findings in 17 children, 0.51 per
minute, 4 contradictions), saves 2.2 minutes per run. A finding is not a fixed price, so this is a candidate, not a
conclusion. (b) Improve as a whole on one-step plans: 0 behaviour changes in 27 build-side passes, 14.8 minutes per run in
total; the proposal keeps exactly those build reviews, and the cell is seven hello runs. (c) Multi-item plans hold the
larger record-only pool (planning and step-level 284 of 490 minutes) and the most record fixes (35 per run).

**4. If `none` is no worse on one-item plans,** choose `planning_review` per run instead of defaulting to `stage`. Spec and
test-strategy run before the plan exists, so that choice has to come from the request (for example the intake
classification), not from the plan's item count (F12). This is a ShipLoop change and the owner's call.

**5. Not recommended without the owner's go:** any change to pass limits or to the confirming pass (F8); the owner asked
to be consulted before a loop limit is added or changed.

## Revisions

**2026-10-28, later the same day.** The owner found the conclusion unclear. I re-derived the headline numbers from the
rows (they reproduce) and reworked the recommendation. Superseded, with reason:
- "Do not adopt the blanket skip", then "the cut the numbers support first is the `plan` review", then "key it on steps":
  three recommendations of unequal strength. The `plan` review ranking rests on findings per minute, which does not price a
  fix; "key it on steps" rests on seven hello runs. Both are now hypotheses (Recommendation 3). The short answer now says
  the data neither support nor refute the skip.
- Added F10, F11 and two tables ("Improve minutes and product edits, by stage group"; "How Improve scales with plan size,
  per run"). No count changed.

**2026-10-28, later.** The owner asked why Improve changed nothing and whether that is intended or a byproduct of the
prompts and templates. Added F12 and the table "What each review was given, and when it stopped" (from each child's
`start.json` and the run's `planning_review`); Recommendation 2 now names the existing `--planning-review none` flag, and
a new Recommendation 4 notes that spec and test-strategy run before the plan's item count exists. No earlier count changed.

## Limits

- No counterfactual. The data show where fixes land and what they cost, not what happens without them.
- Greenfield only. In brownfield work a spec or plan review might find product defects; no run here is brownfield.
- Confounds: model, host and ShipLoop version vary across runs (1.8.0 to 1.17.0); the Improve loop changed over that period
  (`test-spec` is gone from 1.16). Plan size is confounded with task family (the one-step class is hello). Medians and
  per-run tables are given for that reason.
- Labels come from one Sonnet pass per paragraph, spot-checked by me on 22 passes. The product-versus-record split rests
  on git and holds; the nature split is judgement.
- Time: `seconds` is the pass duration; waiting between passes and the parent's stage work are not in it.

## Round log

**Round 1, 2026-10-28.** Question: what do Improve reviews change, by stage and plan size? Cases: the 25 runs above.
Subjects: the models in `runs.json`. Tools: `extract.py` (git tree diffs, run records, `passes.md`, `metrics.json`),
four Sonnet 5.5 labelling workers, `analyze.py`. Conditions: run folders read-only; no ShipLoop code changed; the
canonical checkout was clean at `3d7b83a3` when the task began; other sessions have committed on `main` since. Code under test in the named
runs: `337b09c5` (battleship) and `4e1c8df0` (hello), plugin 2.18.0, ShipLoop 1.17.0. Result: findings F1 to F9 and the interim recommendation above.

Harness and test-case changes: none. Supersedes: none.

## Reproduce

```bash
python3 -I docs/shiploop-improve-value-evidence/extract.py   # reads the run folders, writes runs/reviews/passes/review-text.json
python3 -I docs/shiploop-improve-value-evidence/analyze.py   # joins labels/out-*.json, writes findings.json, tables.md, summary.json
```

Evidence index: `runs.json` (one row per run), `reviews.json` (per child), `passes.json` (per pass, with files changed
and bucket), `review-text.json` (the Found, Changed and Class text that was labelled), `labels/out-*.json` (raw
labels), `findings.json` (labelled findings joined to their pass), `summary.json` (every figure quoted above that is not
in a table), `tables.md`.
