The current ShipLoop increment is finished. This command **is** the closer, not a reprint.

**Success (default):** if this was an implement `/goal` A + Improve `/goal` B:

1. If the worktree still has uncommitted work: `git -C <worktree> log -10
   --format=full` (treat bodies as key learnings; follow every `See: <sha>`),
   then pathspec add (never `git add -A`) and commit:
   - Subject: one line
   - Body: verbose description of the change
   - `Key learnings:` bullets
   - `See: <full sha> <subject>` for prior commits that taught this lesson
   If `/goal` already committed, do **not** invent a second finish commit.
2. Then exec the harness `complete`. It merges
   (`git -C <session-checkout> merge --no-ff --no-edit <branch>`), prints
   `Git ran:` (argv + exit + output), dests residual when this was the last
   step, and prints the next packet. Session checkout = `repo_root` main
   working tree. Do not merge from the worktree cwd. Dirty, empty, or
   conflicted complete is exit 2 with that transcript — fix and retry.

Complete runs the merge; it does not resolve conflicts. Full sequence: [README.md — Git sequence (harness vs host)](../README.md#git-sequence-harness-vs-host).

Then exec `python3 "$SKILL_ROOT/scripts/shiploop" complete` (or the leaf wrapper `scripts/shiploop-complete`) so the harness prints the next packet.

- `/goal` failed, session continues: `--clear`
- Hard stop: `--blocked --reason <text>`
- `--id` only when several steps are running and cwd is not that worktree

Follow the whole packet that prints. Echo `## You are here` and Diagnosis now/pending. Not `/shiploop next`.
