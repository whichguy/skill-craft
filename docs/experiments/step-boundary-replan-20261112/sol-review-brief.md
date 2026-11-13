# Sol brief: adversarial review of fix forward and two refusals (2026-11-12)

Read-only. Review the diff `git diff 7ceaecf441448c1c394340ec2c98f848cd685b27..HEAD` in this checkout (branch
`feat/fix-forward-5308ed`, three commits: 636a02e2, be98fb8e, 34937ec7). Read the commit messages and
`docs/shiploop-fix-forward-design-2026-11-12.md` for intent. Find real defects; verify each claim against the code
before reporting it, and say how you verified it.

Intent in one paragraph: in ShipLoop's inner loop, a send-back from test-spec through document used to return the item
to step-plan and re-run every step already done. Now a step whose document was accepted stays done. The amended step
plan must start with those rows, byte-identical except `"done": true`, and only later steps change. Test cases due at a
done step stay frozen. All step cursors read one projection (`planning_revision._StepLists`). Separately, a step
Proof's failure refusal gains a line about repeat-safety (`test_loop.REPEAT_LINE`). Step-plan also refuses a `focused`
test command that only searches text (`layers.check_confirms`).

Look hardest at:
1. `planning_revision._StepLists` and its readers: `current_actions`, `step_actions`, `built_steps` and `done_steps`,
   then `implement_progress`, `test_loop.step_number`, `loops.current_step`, `step_view` and `_previous_step_results`.
   Can any history (a send-back from a step review, a document send-back, several items, an Improve import, a
   not-applicable document, a send-back before any step, recovery after a crash) give a cursor that points at the wrong
   step, or keep or drop the wrong actions? Do old saved runs, whose plans carry no marks, read exactly as before?
2. The gates `_fix_forward_refusal` and `_frozen_case_refusal`: can a valid amendment be refused, or a reopening slip
   through? Consider two amendments in a row, steps whose criteria span steps, a done step with no criteria, an
   amendment that reorders unfinished steps, and the ask-agent delegation route.
3. Anything the change breaks that its tests do not cover: commit attribution, the iteration ledger, RED and base runs at
   the resumed step, open items, test-count floors, the progress and trace views.
4. The focused-search refusal: false refusals of legitimate focused commands (pipelines, `grep` inside a test runner's
   output, `cd` prefixes).

Return findings ranked by severity, each with file:symbol, a concrete failing history or input, and your verification.
Say plainly if you find nothing material.
