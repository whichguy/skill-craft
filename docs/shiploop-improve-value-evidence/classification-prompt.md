# Labelling rubric: findings reported by ShipLoop Improve review passes

You label review passes. Each input line is one JSON object (one review pass):

- `id`: unique pass id, copy it back unchanged
- `stage`: the ShipLoop stage that was reviewed (spec, test-strategy, plan, step-plan, test-spec, implement, system-test-author, carry-forward, release-plan)
- `label`: the reviewer's own class, `trivial` or `non-trivial`
- `files`: files the pass changed in the product worktree, from git (authoritative)
- `buckets`: the kinds of those files, from git (authoritative): `code` (product source and config), `test` (test files), `doc` (README and docs outside docs/shiploop), `record` (the run's own records under docs/shiploop/)
- `result_changed`: true when the pass also edited the stage's accepted result, a run record that lives outside the repository
- `found`: the reviewer's `Found:` paragraph
- `changed`: the reviewer's `Changed:` paragraph
- `class`: the reviewer's `Class:` line

## Task

For every input line, list the distinct findings the reviewer reports in `found`, and say what the fix for each one touched.

A finding is a defect, contradiction, gap or wrong statement the reviewer reports and acts on, including a minor polish edit it made. Split a long paragraph into its separate findings, whatever the numbering style. Do not list as findings: confirmations that something was correct ("replayed, not findings", "all other cases match"), restatements of what was read, or the reviewer's summary sentence. If `found` reports nothing to change, give an empty list.

For each finding give:

- `summary`: at most 20 words, in your own words
- `touched`: a list drawn from `code`, `test`, `doc`, `record`, `run-result`, `nothing`.
  - `code`, `test`, `doc`, `record` mean the fix edited a file of that kind; use `changed` and `files` to decide which. `run-result` means the fix edited the stage's result record outside the repository (or the run's notes).
  - If one fix edited several kinds (for example product code and the record that describes it), list all of them.
  - `nothing` means the reviewer reports the item but did not act on it (left for a later stage, accepted as is).
  - Every kind you list other than `nothing` must be among the pass's `buckets` (or `run-result` when `result_changed` is true, or when `changed` says the stage result was rewritten). If the text does not let you attribute a finding, choose the best fit among the pass's actual kinds and set `attribution` to `uncertain`; otherwise set it to `clear`.
- `nature`: exactly one of
  - `behaviour-defect`: product code or a test behaves wrongly, a test cannot fail, an assertion is wrong, an error path is missing
  - `contradiction-or-unverifiable`: a record contradicts itself or another record, or states a check that cannot be replayed or falsified as written
  - `stale-or-wrong-reference`: wrong count, ID, path, name, command or stale statement; naming collision
  - `missing-content`: a required statement, case or coverage is absent
  - `polish`: wording, formatting, clarity or tidying with no behavioural consequence
- `attribution`: `clear` or `uncertain`, as above

## Output

Write a JSON array to the output file you were given, one object per input line, in any order:

```json
[{"id": "<id>", "findings": [{"summary": "...", "touched": ["record"], "nature": "contradiction-or-unverifiable", "attribution": "clear"}]}]
```

Then check it with `python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d))" <output file>` and confirm that the number of objects equals the number of input lines and every input `id` appears exactly once.

Your final message is only: the output path, the number of passes, the number of findings, and anything you could not label. Do not paste the labels into the message.
