Walk ready steps via `/goal`. The spec is **frozen** — do not refine, expand,
or rewrite it. **Diagnosis** (in You are here) shows completed steps, what is
now running/ready, and what is still waiting — against that frozen
`done_sentence`.

`/shiploop next` already claimed newly ready ids `running`. The packet's
**Next prompt** section prints each running id's **stored** `prompt` verbatim
— paste it as-is; the script does not compose or rewrite it. Each running
step's worktree and branch are named in **Look here** / **Diagnosis**, not
spliced into the prompt — `cd` there before pasting; do not edit the session
checkout or reuse a prior worktree.

Do not nest a second `/goal` inside the first.
If a `/goal` for an id is already open, do not open a second one. When the
`/goal` is done, invoke **`/shiploop complete`** — that command commits,
merges the kept branch into the session checkout, and prints the next
packet. Do not skip that merge; the next worktree forks `HEAD`. ShipLoop
does not auto-merge.

## Discovered work mid-implement: `inject-step`

If a running `/goal` surfaces intermediate work the frozen DAG did not
anticipate, add it with `scripts/shiploop inject-step --statement <label>
--prompt <text> --produces <text> [--id Sn] [--need <n> --from <id>]
[--before <id>...]`. Legal only in phase `implement` (including drained).
It refuses on plan-hash drift (a hand-edit is not an inject), refuses
`--before` a step that is not `todo`/`ready`, and rebinds `plan_sha256` only
— it never re-runs `dest plan` or clears existing receipts. Unlike a seed
step's `prompt`, a discovered step's `--prompt` does **not** need to cite
`{{ENV_MD}}`'s practice references — it is an ad-hoc fix, not researched
practice work. See `commands/shiploop-inject.md`.

After a `/goal` succeeds: invoke `/shiploop complete`.
After a `/goal` fails and the session can continue: invoke `/shiploop complete --clear`.
Hard stop: invoke `/shiploop complete --blocked --reason …`.
