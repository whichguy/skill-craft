# Test loop and confirmation

Split from the ShipLoop skill card (`../SKILL.md`). Read at `step-plan`, `test-spec`, `test` and `document`, and when a test gate refuses.

## Test loop

`step-plan` records:
`"test_commands": [{"command": "<shell command>", "suite": "focused" | "regression" | "check", "ids": ["TC-9"], "min_tests": 1}]`
(`ids`/`min_tests` optional, never on `check`), `"paths"` (repo-relative globs/files),
and `"steps": [{"id": "S1", "task": "...", "deps": []}]` (real prerequisites only, `[]`
when independent). Missing fields require explicit `_na` reasons (`test_commands_na`,
`check_na`). Regression commands marked `"minimum": true` run at every step; unmarked
ones run at the item's last step only (`>= 2` steps require one or `minimum_na`;
[what each step runs](testing-and-documentation.md#what-each-step-runs)).

`test` follows `implement`, asserting each spec oracle. ShipLoop mutates changed product
lines and refuses unkilled mutants without a `mutant_dispositions` entry. Its
[Until Loop](inner-loop.md#stage-until-loops) writes a test per spec case (ID as its
own word), runs recorded/red-check/lint commands, and fixes code (recording test-edit
reasons) until green. On `done`, after lint, ShipLoop runs two gates
(`scripts/shiploop_test_loop.py`) with `/bin/sh -c` (10 min timeout):

1. **Base run** (`base_check`): runs focused/regression commands at item base (plus this
   item's test files). New IDs must fail on missing behaviour or missing added module
   (path guards are not RED). Earlier steps' cases are floor-counted, not judged
   (`earlier_steps`); Remote tests skip base. Intentional base-passing cases go in
   `red_na: [{"id", "reason"}]` (`tests/<action>-base<N>.md`).
2. **Candidate run** (`loop_run`): runs all recorded commands in WORKTREE (`<= 0` exit,
   every listed ID shown, count `>= floor`; `tests/<action>-verify<N>.md`).

A command's **floor** is `max(base_count, max_prior_run) - len(retired_tests_on_base)`
(`retired_tests: [{"id", "reason"}]`). Removing or skipping tests to pass fails.
Passing requires exit 0, counted tests, and every listed ID shown.

`shiploop red-check --run-dir <run> --action <test action> [--result <draft>]` runs
the uncounted base check (`red_na`/`retired_tests` apply): 0 clean, 1 failed, 3 error.

`document` reruns affected commands; outer stages run recorded commands. Unchanged
checks may reuse receipts; external and `release-verify` checks rerun. No count of
refused runs stops `done` (base, candidate, and mutation share one tally). Remedy wrong
plans/commands via `send-back` (INNER, or non-final `document` `done` with
`replan_remaining`) or `send-back` / `add-work` at `system-test` (`system-test-author`)
and `release-verify` (`release-plan`). Timeouts or unstartable runs refuse uncounted.

`test` is skipped when no test command exists and only docs/config change; `document`
is skipped when no code/test path changed
([command rules](testing-and-documentation.md#how-shiploop-runs-the-recorded-commands)).

ShipLoop runs recorded commands outside host permission prompts (empty lists accept with reason).

## Confirmation is a passing command

A passing test that ShipLoop runs is the only confirmation of a criterion. `step-plan`
links every criterion to a command; text/doc criteria use suite `check` (exit code),
while unconfirmable criteria become open items in summary. `system-test-author`
(`system_commands`) and `release-plan` (`consumer_checks`) gate `system-test` and
`release-verify` (running `release-verify` against clean exported `consumer-check` on
isolated returns, else WORKTREE; [reruns](testing-and-documentation.md#reruns-after-the-test-stage)).
Run records under `tests/` are the evidence, not summaries.

Unobserved outcomes: a done `product-acceptance` lists it in `unverified`
(`outcome, requirement, reason, lower_layer_check, settle, owner, due_stage`; `[]` if
none). Missing/placeholder lists, unknown IDs, or non-later due stages refuse;
`primary` needs a passed `lower_layer_check` or `add-work`. Acceptance/due stages/handoff
restate the list and settle removals via `settled` (`observed` or `user-correction` with
nonempty `evidence_refs`; missing restatements/unmatched settlements/unsettled due rows
refuse). Delivery-contract gates still apply.

## Tests pass or the step stops

Each inner stage's [Until Loop](inner-loop.md#stage-until-loops) prints its
repeat condition (`REPEAT` in `scripts/shiploop_loops.py`). At `test`, Beat 1
inspects `RUN/fields/<action>-product-diff.patch`, `KNOWLEDGE/architecture.md`,
`test_cases`, and `not_covered` to write focused tests and register new IDs in
`added_tests`; Beat 2 runs checks, fixes local product defects (re-verifying step
Proof at `done`), and triages into `test_findings` (`none`, `local`,
`amend-remaining`, `system-test`), `assumptions`, or `send-back`. Only a final
full pass after the last edit counts. It ends on `done`, `send-back`, or, at
`implement`, the same check still failing in the same way after a genuine fix
that taught nothing new about why (`send-back`). Missing tools, access or
authority end `blocked`. ShipLoop's gates at `complete` (lint, tests, Proof on
product edits, expectations) are script-enforced.
