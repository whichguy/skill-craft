Walk ready steps via `/goal`. The spec is **frozen** — do not refine, expand,
or rewrite it. **Diagnosis** and the implement walk rail (in You are here)
use the same glyphs as the session rail: `●` hash-matching complete,
`▶` running or ready, `○` waiting (`todo`), still with `S1: running` /
waiting-on — against that frozen `done_sentence`. No `✗` on steps.

`/shiploop next` already claimed newly ready ids `running`. The packet's
**Next prompt** section prints worktree / branch / HOST FLAG, then a
**Frozen session environment** block, then each running id's **stored**
`prompt` verbatim. Paste the Frozen session environment block together
with the stored prompt into `/goal`. Do not paste worktree, branch, or
HOST FLAG. The script does not compose or rewrite the stored prompt.
Each running step's worktree and branch are named in **Look here** /
**Diagnosis** — work there (do not re-root the host chat); do not edit
the session checkout or reuse a prior worktree.

Do not nest a second `/goal` inside the first.
If a `/goal` for an id is already open, do not open a second one. When the
`/goal` is done, invoke **`/shiploop complete`** — that command commits
on the worktree, merges into the session checkout
(`git -C <session-checkout> merge --no-ff --no-edit <branch>`), and
prints the next packet. Do not skip that merge; do not run a bare
`git merge` from the worktree cwd. The next worktree forks `HEAD`.
ShipLoop does not auto-merge.

## Discovered work mid-implement: `inject-step`

If a running `/goal` surfaces intermediate work the frozen DAG did not
anticipate, add it with `inject-step`. **Look here** lists the harness CLI
and the inject-step card as absolute paths. Pass `--statement`, `--prompt`,
`--produces`, optional `--id Sn`, `--need`/`--from`, `--before`. Legal only
in phase `implement` (including drained). It refuses on plan-hash drift (a
hand-edit is not an inject), refuses `--before` a step that is not
`todo`/`ready`, and rebinds `plan_sha256` only — it never re-runs `dest
plan` or clears existing receipts. Unlike a seed step's `prompt`, a
discovered step's `--prompt` does **not** need to cite `{{ENV_MD}}`'s
practice references or carry a `Tools:` block — it is an ad-hoc fix, not
researched practice work. The Next envelope still reprints frozen
tools/MCP above that stored prompt; paste that Frozen block with the
discovered prompt.

After a `/goal` succeeds: invoke `/shiploop complete`.
After a `/goal` fails and the session can continue: invoke `/shiploop complete --clear`.
Hard stop: invoke `/shiploop complete --blocked --reason …`.
