# Spec retire and feature list: evidence (batch 1012 task R, 2026-10-10)

Journal: `docs/shiploop-spec-retire-journal-2026-10-10.md`. Design and audits: `docs/experiments/commit-spec-design-20261010/retire-design-and-audits.json`.

| File | What it is |
|---|---|
| `survey.py` | Runs the engine's own `_missing_ids` (named `_unmerged` when the survey ran), `_planned_record`, `retire`, `retired_by`, `is_retire_subject` and `feature_list` over the saved runs under `/Users/dadleet/e2e-runs` (read-only; the retire runs on clones in a scratch directory): `python3 survey.py <scratch-dir>`. It ran with the first retire subject ("its requirement IDs are in the living spec"); its counts do not depend on the wording |
| `survey-summary.json`, `survey-rows.json` | Its output on 2026-10-10: 33 feature specs in 32 work repositories, one row each (the 32 of the first commit message is the repository count, the 33 the spec count) |
| `fail-first.txt` | What each new test failed with before its code, in the first series and in the fix round after the reviews |
| `mutants.json`, `mutation-record.jsonl`, `mutate.py` | The mutants, their results and the runner that applies one replacement, runs the suite and restores the file. A row may carry `args` (a `-k` filter) |

Mutation record. The record was re-run on the final tree of the fix round (the first series' record, 63 rows, is in commit `19c25538`): 85 mutants,
one row each, 85 distinct (suite, mutant) pairs, 84 red and 1 survivor, which is equivalent ("list rewritten when text equal" rewrites identical text).
Five rows were re-run and carry `first_run` with the reason: one mutant whose first definition was a syntax error (red for the wrong reason), two
that ran in the wrong suite (their tests are in `shiploop-retire`), one that survived a test gap (closed in `0ccb9233`) and one that ran in the wrong
suite and then survived because the test's path had the wrong depth (closed in `0ccb9233`). Recompute the counts with:

    python3 -c "import json,collections;r=[json.loads(l) for l in open('mutation-record.jsonl')];print(len(r),len({(x['suite'],x['mutant']) for x in r}),collections.Counter(x['result'] for x in r),sum('first_run' in x for x in r))"

which prints `85 85 Counter({'RED': 84, 'GREEN (survived)': 1}) 5`. The runner was started once per chunk of at most 12 mutants, in the foreground.
