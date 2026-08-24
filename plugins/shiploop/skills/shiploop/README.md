# ShipLoop

**Ship the project.** One session harness: spec once, sequence-plan once, then
walk ready steps until the work is landed.

This is **not** DevLoop. `/devloop` still means skill `devloop`. ShipLoop never
invokes it, never captures `devloop-run`, never auto-merges, and never claims
engine `COMPLETE`.

Package leaf: `skills/shiploop`. Invoke: `/shiploop`.

## What it does

1. **Intake → validate-spec → plan** — freeze a checkable `done_sentence`, then
   one backchain DAG (requires sibling skill `backchain`).
2. **Implement** — claim each ready step, emit a paste-ready `/goal` whose cwd
   is that step’s git worktree and branch (`shiploop/<run_id>/<id>`).
3. **Close each increment** — you commit on the worktree, merge the kept branch
   into the session checkout, then `/shiploop complete`. The next worktree
   forks `HEAD`.
4. **Residual** — after `steps_drained`, review-coverage Phase B under `/goal`.
   Stop when the packet says stop.

State lives in the bound repo’s `.shiploop/` (walked from cwd). Not inside this
package.

## Commands (same leaf)

| Invoke | Meaning |
|--------|---------|
| `/shiploop` | Start or resume (`init` if needed), then follow the packet |
| `/shiploop next` | Reprint / claim only. Lost context, nothing to close |
| `/shiploop complete` | Closer: commit+merge if needed, then next packet |

There are no sibling marketplace skills for `next` or `complete`.

```sh
CLI="$SKILL_ROOT/scripts/shiploop"
python3 "$CLI" init --prompt "…" --repo PATH
python3 "$CLI" next
python3 "$CLI" complete
```

`--clear` and `--blocked --reason` are closer overrides. `--id` only when two
or more steps are running and cwd is not that worktree.

## Not this product

| You want | Use |
|----------|-----|
| DEFINE → PROVE → BUILD engine | skill `devloop` / `/devloop` |
| Offline freeze / prove / stop | `evidence-gates` |
| Residual×2 engine alone | `review-coverage` / `review-converge` |

## Install

From the skill-craft repo root:

```sh
./install.sh --skill shiploop
./scripts/sync-plugin-views.sh shiploop
```

If a host still has old `steer`, `steer-next`, or `steer-complete-next` skill
dirs, uninstall those and install `shiploop`. Old `.steer/` run dirs are not
adopted — start a new run (or rename the directory to `.shiploop` yourself).

## Tests

```sh
bash test/shiploop.test.sh
```
