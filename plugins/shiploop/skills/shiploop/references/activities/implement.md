Walk ready steps via `/goal`. The spec is **frozen** — do not refine, expand, or rewrite it. **Diagnosis** (in You are here) shows completed steps, what is now running/ready, and what is still waiting — against that frozen `done_sentence`.

`/shiploop next` already claimed newly ready ids `running` and printed one `/goal` line per running id (inner-loop: write tests, run them, fix until they pass; or prep / deploy / cleanup when that step names it). Each `/goal` names that step's worktree and branch — `cwd` there; do not edit the session checkout or reuse a prior worktree.

Do **not** invoke `/devloop`. Do not nest a second `/goal` inside the first. If a `/goal` for an id is already open, do not open a second one. When the `/goal` is done, invoke **`/shiploop complete`** — that command commits, merges the kept branch into the session checkout, and prints the next packet. Do not skip that merge; the next worktree forks `HEAD`. ShipLoop does not auto-merge.

After a `/goal` succeeds: invoke `/shiploop complete`.
After a `/goal` fails and the session can continue: invoke `/shiploop complete --clear`.
Hard stop: invoke `/shiploop complete --blocked --reason …`.
