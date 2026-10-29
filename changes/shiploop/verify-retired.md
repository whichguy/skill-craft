---
bump: minor
---
The `verify` stage is retired (design T section 9.1, 2b-4). Each work item now runs 7 inner stages: step-plan,
test-spec, validate-existing, then implement, test and document once per step, then carry-forward.
- Verify's gates run inside each step: document's done lints its own lines and reruns what its edits could affect,
  and the step review's import lints the review's lines and reruns the step's commands.
- Verify's entry-point trace, where every finding it made came from, is each step review's: one valid, one boundary
  and one invalid input per new or changed public entry point. The test stage writes those three cases.
- Later-phase checks are document's open items, due at the stage that makes them.
- Verify's item commit is gone: each step's commit stage commits the step. On the ask-agent route the item is
  committed whole when its document stage and review are accepted, and Git refusing that commit refuses the callback.
  The commit names the changed files it leaves.
- Carry-forward follows the last step and reads the item's test and document results.
- Removed with verify: the change inventory, the advisory lint pass at its entry, its Code craft rubric file
  (`RUN/quality/`) and its single trivial-review loop. Send-back is accepted from test-spec through document.
- A step's review commits nothing: its handoff no longer prints the improve-commit command or the commit-message rules
  (it told the review to commit since 2b-2, against its own focus), and `improve-commit` refuses at a step review,
  naming improve-pass.
