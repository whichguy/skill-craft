`/shiploop complete` execs the printed When done.
The script updates `.shiploop/` and prints the next stdout — that is the next prompt to issue.
This command can advance Implement to Improve, record one Improve cycle,
or merge a step. Calling it does not by itself mean the increment is finished.

Run the command printed under **When done invoke**.

For an implement step, flagless `complete` is the happy path. The script
infers the action from the receipt. If When done named `--trivial`,
`--improve cap-exceed(<why>)`, `--reason`, or `--id`, pass those.

If When done is the merge and the worktree still has uncommitted work:
`git -C <worktree> log -10 --format=full` (treat bodies as key learnings;
follow every `See: <sha>`), then pathspec add (never `git add -A`) and commit:
- Subject: one line
- Body: verbose description of the change
- `Key learnings:` bullets
- `See: <full sha> <subject>` for prior commits that taught this lesson
If Improve already committed, do **not** invent a second finish commit.

Use `--inner-loop goal` only if this host actually ran `/goal` (override).
`--advance B` / `--improve-cycle` / `--inner-loop parent` are overrides.
A merge complete merges (`git -C <session-checkout> merge --no-ff --no-edit <branch>`), keeps the
step branch, removes the worktree, and does not squash, so inner Key
learnings stay reachable from session HEAD. It prints `Git ran:` (argv +
exit + output), dests residual when this was the last step, and prints the
next stdout. Session checkout = `repo_root` main working tree. Do not merge
from the worktree cwd. Dirty, empty, or conflicted **merge** is exit 2 with
that transcript — fix and retry. Uncertain whether complete landed →
`/shiploop next` (do not retry complete).

Complete runs the merge when that is the inferred action; it does not resolve conflicts. Full sequence: [README.md — Git sequence (harness vs host)](../README.md#git-sequence-harness-vs-host).

Then exec `python3 "$SKILL_ROOT/scripts/shiploop" complete` plus any flags When done printed.

- Until-loop failed, session continues: `--clear`
- Hard stop: `--blocked --reason <text>`
- `--id` only when several steps are running and cwd is not that worktree

Then SKILL.md Host loop: issue this prompt; satisfy any printed precondition; exec When done exactly. Not `/shiploop next` unless reprinting. Do not end the turn if When done is another `complete`.
