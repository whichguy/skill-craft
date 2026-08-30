The current ShipLoop increment is finished. This command **is** the closer, not a reprint.

**Success (default):** if this was an implement `/goal`, commit on that worktree if needed, then merge the kept branch into the session checkout (`git -C <session-checkout> merge --no-ff --no-edit <branch>`). Do not skip the merge; the next worktree forks `HEAD`. ShipLoop does not auto-merge. Full sequence: [README.md — Git sequence (harness vs host)](../README.md#git-sequence-harness-vs-host).

Then exec `python3 "$SKILL_ROOT/scripts/shiploop" complete` (or the leaf wrapper `scripts/shiploop-complete`) so the harness prints the next packet.

- `/goal` failed, session continues: `--clear`
- Hard stop: `--blocked --reason <text>`
- `--id` only when several steps are running and cwd is not that worktree

Follow the whole packet that prints. Echo `## You are here` and Diagnosis now/pending. Not `/shiploop next`.
