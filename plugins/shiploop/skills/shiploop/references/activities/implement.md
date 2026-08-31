Walk ready steps via `/goal`. The spec is **frozen** — do not refine, expand,
or rewrite it.

Follow the printed Next envelope; do not nest Improve `/goal` B inside A.
Each running step's worktree and branch are named in **Look here** /
**Diagnosis** — work there (do not re-root the host chat); do not edit
the session checkout or reuse a prior worktree.

Do not nest Improve `/goal` B inside `/goal` A.
If `/goal` A for an id is already open, do not open a second functional
`/goal` for that id. Inner `/goal` A iterates and pathspec-commits **on
the worktree**. Never `git add -A`. Never merge from that cwd. Then invoke
**`/shiploop complete`** — the harness merges
(`git -C <session-checkout> merge --no-ff --no-edit <branch>`), prints
Git ran, dests residual when this was the last step, and prints the next
packet. Do not run a bare `git merge` from the worktree cwd. The next
worktree forks `HEAD`. Complete does not resolve conflicts; read Git ran
and retry.

### Discovered work mid-implement: `inject-step`

If a running `/goal` surfaces intermediate work the frozen DAG did not
anticipate, add it with `inject-step`. **Look here** lists the harness CLI
and the inject-step card as absolute paths. Pass `--statement`, `--prompt`,
`--produces`, optional `--id Sn`, `--need`/`--from`, `--before`. Legal only
in phase `implement` (including drained). It refuses on plan-hash drift (a
hand-edit is not an inject), refuses `--before` a step that is not
`todo`/`ready`, and rebinds `plan_sha256` only — it never re-runs `dest
plan` or clears existing receipts. Unlike a seed step's `prompt`, a
discovered step's `--prompt` still needs `/goal` plus until-`produces`
and does **not** need to cite `{{ENV_MD}}`'s practice references or the
frozen `mcp_considered` token. That exemption does **not** cover the writer
prohibition: when `exclusive` is nonempty, the discovered `--prompt` still
carries a `Tools:` block, a `Use:` line whose entries include the designated
`exclusive[].use`, and a parsed `Don't use:` line (`Don't use: none`
if the token union is empty; a token under `Use:` does not count; overlap
with `Don't use:` is a gap). The envelope wraps a discovered prompt exactly
as it wraps a seed prompt.
If the writer above fails, stop and invoke /shiploop complete --blocked --reason … — do not switch writers.

After `/goal` A produces and Improve `/goal` B finishes: invoke `/shiploop complete`.
After a `/goal` fails and the session can continue: invoke `/shiploop complete --clear`.
Hard stop: invoke `/shiploop complete --blocked --reason …`.
