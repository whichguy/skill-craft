---
bump: minor
---
The document, verify and carry-forward packets give the model the inputs their duties name, and carry-forward is shorter for
the common one-item run.
- Document prints `Changed since the item base (script-derived): <paths>` (or `not computed: <reason>`), and its duty 1
  lists behaviours from those paths; it named a change inventory that exists only at verify.
- Verify's duty 1 runs the Callback command with `--check-only` after the last edit, which reruns every recorded command into
  `RUN/tests/<action>-check-only.md`, in place of rerunning each command by hand and copying exit codes into notes; duty 11
  no longer asks for exit codes. The ask-agent route keeps item 8 (assembly).
- A run of one work item with one step and no pending item (proved from state) gets a short carry-forward: duty 2 says no
  item follows and how to add a corrective one, duty 3 records `none` or `reuse` unless an R-<n> says the procedure will
  recur, the queue rule prints only its path line and the Until Loop Work drops the trial clause (about 4.3 KB less in the
  printed head). Every other run keeps the text byte for byte.
- Carry-forward names the commands that passed at the item's verify and `environment.md` does not name under `## Commands`,
  and an accepted carry-forward prints one counted `ShipLoop knowledge notice:` line for them; it never refuses.
- The item commit raises when the item's changes cannot be read (no base snapshot) instead of reporting nothing to commit,
  and the `<item> verify item commit` reference is printed only when the worktree log holds a `feat: <item> ` commit.
