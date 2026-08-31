Walk ready steps via `/goal`. The spec is **frozen** — do not refine, expand,
or rewrite it. **Diagnosis** and the implement walk rail (in You are here)
use the same glyphs as the session rail: `●` hash-matching complete,
`▶` running or ready, `○` waiting (`todo`), still with `S1: running` /
waiting-on — against that frozen `done_sentence`. No `✗` on steps.

`/shiploop next` already claimed newly ready ids `running`. The packet's
**Next prompt** section prints worktree / branch / HOST FLAG, then a
**Frozen session environment** block, then **Implement git**, **Goal until**,
each running id's **stored** `prompt` verbatim, then **Improve**. That stored
prompt **is** `/goal` A until this step's `produces`. Paste Frozen,
Implement git, and Goal until above it; do not wrap a second `/goal`; do
not work in the parent chat without until. When produces is true, close A
and open `/goal` B = Frozen + Implement git + Improve (do not nest).
Improve: last 7 git commits, two consecutive only-trivial, max 12, then
leftover + `/shiploop complete`. Do not paste HOST FLAG. Implement git
names the worktree and branch and the commit schema (`git log -10`,
verbose body, `Key learnings:`, `See: <sha>`). The script does not compose
or rewrite the stored prompt from the original ask.
Each running step's worktree and branch are named in **Look here** /
**Diagnosis** — work there (do not re-root the host chat); do not edit
the session checkout or reuse a prior worktree.

Do not nest Improve `/goal` B inside `/goal` A.
If `/goal` A for an id is already open, do not open a second functional
`/goal` for that id. Inner `/goal` A iterates and pathspec-commits **on
the worktree** (read `git log -10` before planning each iteration; verbose
message with `Key learnings:` and `See: <full sha> <subject>`). Never
`git add -A`. Never merge from that cwd. When produces is true, close A,
open Improve `/goal` B, leftover uncommitted work gets the same commit
schema, then invoke **`/shiploop complete`** — the harness merges
(`git -C <session-checkout> merge --no-ff --no-edit <branch>`), prints
Git ran, dests residual when this was the last step, and prints the next
packet. Do not run a bare `git merge` from the worktree cwd. The next
worktree forks `HEAD`. Complete does not resolve conflicts; read Git ran
and retry.

## Discovered work mid-implement: `inject-step`

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
with `Don't use:` is a gap). The Next envelope still reprints Frozen
(Exclusive / dest-blocked / See) and Implement git above that stored prompt;
paste Frozen, Implement git, Goal until, and Improve with the discovered prompt (do not paste HOST
FLAG). If the writer above fails, stop and invoke /shiploop complete --blocked --reason … — do not switch writers.

After `/goal` A produces and Improve `/goal` B finishes: invoke `/shiploop complete`.
After a `/goal` fails and the session can continue: invoke `/shiploop complete --clear`.
Hard stop: invoke `/shiploop complete --blocked --reason …`.
