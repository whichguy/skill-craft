# Spec retire and feature list: evidence (batch 1012 task R, 2026-10-10)

Journal: `docs/shiploop-spec-retire-journal-2026-10-10.md`. Design and audits: `docs/experiments/commit-spec-design-20261010/retire-design-and-audits.json`.

| File | What it is |
|---|---|
| `survey.py` | Runs the engine's own `_missing_ids` (named `_unmerged` when the survey ran), `_planned_record`, `retire`, `retired_by`, `is_retire_subject` and `feature_list` over the saved runs under `/Users/dadleet/e2e-runs` (read-only; the retire runs on clones in a scratch directory): `python3 survey.py <scratch-dir>` |
| `survey-summary.json`, `survey-rows.json` | Its output on 2026-10-10: 33 feature specs in 32 work repositories, one row each |
| `fail-first.txt` | What each new test failed with before its code, and the 14 of 17 `test/shiploop-retire.test.py` tests that fail against the navigator of `b8c1680e` |
| `mutants.json`, `mutation-record.jsonl`, `mutate.py` | The mutants (62 definitions, 60 distinct: two were re-run with a corrected pattern or a stronger test), their results (59 red, 1 equivalent), and the runner that applies one replacement, runs the suite and restores the file |
