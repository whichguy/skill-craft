Walk ready steps via the printed parent until-loop. The spec is **frozen** —
do not refine, expand, or rewrite it.

Follow the printed Next envelope; do not nest Improve inside Implement.
Each running step's worktree and branch are named in **Look here** /
**Diagnosis** — work there (do not re-root the host chat); do not edit
the session checkout or reuse a prior worktree.

Do not nest Improve inside Implement.
If Implement for an id is already in this parent chat, do not start a
second functional until-loop for that id. Implement iterates and
pathspec-commits **on the worktree**. After produces is true:
lint-after-write then tests-until-green. `LINT_PATHS` is the NUL-safe union
of `git -C <worktree> diff -z --name-only <receipt.base_sha>` (including
the working tree) and `git -C <worktree> ls-files -z --others
--exclude-standard` (untracked, not ignored). Anchor on that step's
immutable `receipt.base_sha`, never moving session HEAD. Recompute after
every production-file edit; the lint run that counts is the one after the
last production edit. If tests force production edits, re-lint those paths
before claiming green. Residual Improve B / review-converge use that
round's `CHANGED_PATHS`, not the step receipt baseline. Writer
lint/validate on dest/source in `LINT_PATHS` is dest-syntax SoT for
file-local syntax; dest-identity findings (order/position/name/presence)
are provisional until live dest list/status/push-preflight agrees;
disagreement is a P2 learning, not a rewrite of reserved runtime;
docs-only: none(<reason>). Then author and run checkable tests for this
produces until they pass. Then `/shiploop complete`. Never `git add -A`. Never merge from
that cwd. Then follow the printed Improve (one cycle; lint-after-write
then re-run recorded checks). Then invoke the printed When done —
**`/shiploop complete`** (add `--trivial` if this Improve cycle was
only-trivial). Do not
pass `--inner-loop parent --improve` unless When done named that override.
When When done is the merge, the harness
merges
(`git -C <session-checkout> merge --no-ff --no-edit <branch>`), keeps the
step branch, removes the worktree, and does not squash; inner Key learnings
stay reachable from session HEAD. It prints Git ran, dests residual when this
was the last step, and prints the next stdout. Use `--inner-loop goal` only
if this host actually ran `/goal`. Parent still includes Implement then
Improve. Do not run
a bare `git merge` from the worktree cwd. The next worktree forks `HEAD`.
Complete does not resolve conflicts; read Git ran and retry.

### Discovered work mid-implement: `inject-step`

If a running until-loop surfaces intermediate work the frozen DAG did not
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

After Implement produces and Improve finishes: invoke `/shiploop complete`
as printed under When done.
After an until-loop fails and the session can continue: invoke `/shiploop complete --clear`.
Hard stop: invoke `/shiploop complete --blocked --reason …`.
