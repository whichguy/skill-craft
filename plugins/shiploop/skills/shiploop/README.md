# ShipLoop

**Ship the project.** One session harness: spec once, sequence-plan once, then
walk ready steps until the work is landed.

This is **not** DevLoop. `/devloop` still means skill `devloop`. ShipLoop never
invokes it, never captures `devloop-run`, never auto-merges, and never claims
engine `COMPLETE`.

Package leaf: `skills/shiploop`. Invoke: `/shiploop`.

## What it does

1. **Intake → validate-spec → plan** — validate-spec runs a **survey first**
   (session kind/handles/MCP/initiation/UI, written to `environment.md`),
   then freezes a checkable `done_sentence` (`spec.md`). `plan` calls
   backchain once for the sequence DAG (requires sibling skill `backchain`),
   including a README create/revise as a late DAG successor.
2. **Implement** — claim each ready step, print its **stored** `prompt`
   verbatim (paste-ready; the script does not compose it) whose cwd is that
   step’s git worktree and branch (`shiploop/<run_id>/<id>`).
3. **Close each increment** — you commit on the worktree, merge the kept branch
   into the session checkout, then `/shiploop complete`. The next worktree
   forks `HEAD`.
4. **Residual** — after `steps_drained`, review-coverage Phase B under `/goal`.
   Stop when the packet says stop.

State lives in the bound repo’s `.shiploop/` (walked from cwd). Not inside this
package. File-by-file map: [references/state-files.md](references/state-files.md).

## Session A vs Session B

| | Session A — greenfield | Session B — brownfield |
|---|---|---|
| `environment.md` | `kind: greenfield`, `augment: false`, no product `README.md` to cite yet | `kind: brownfield`; cites the existing `README.md` (and other read paths) in `references` |
| Product `README.md` | created as the **last** product DAG step | revised as the **last** product DAG step — survey read it but never rewrote it |
| `initiation` | often `needed` (one-time project creation, needs a `create` handle) | often `none` or `done` |
| Everything else | same state machine, same hashes, same per-step worktrees | same |

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
