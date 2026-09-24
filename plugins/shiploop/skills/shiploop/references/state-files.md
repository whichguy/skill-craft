# Durable run files

This catalog describes the run directory of a navigator protocol 4 run.
It does not replace the repository's
[maintained product requirements](project-knowledge.md#maintained-product-requirements).
Everything below belongs to a run directory (for a workspace run,
`<workspace-root>/run`), not to the installed ShipLoop package. Markdown is the
authoritative state: each structured record has one `shiploop-state` JSON fence
inside its Markdown file, and there is no writable JSON mirror.

| File or directory | Authority / purpose |
|---|---|
| `state.md` | The navigator state: protocol version, execution mode, run ID and revision, repository and original prompt, current stage/action/status, work queue and `work_index`, per-item `inner_loops`, accepted results and history, the selected Improve card, the active Improve child and imported Improve records, chain bindings, and the run's `delegation`. Protocol 4 adds `planning_reconciliations`. |
| `inbox/<action>.md` | Where the host writes the current action's result before running the printed callback. It is input, not accepted state. |
| `results/<action>.md` | The accepted producer result for one action, written by the script's transaction. |
| `notes/` | Host-authored run notes named in results' `evidence_refs`, including the canonical `notes/environment-lifecycle.md`. |
| `improve/<action>/` | The imported Improve child record for one parent action: its receipt, terminal packet, the two trivial-pass review files and copied evidence. |
| `workspace.md`, `return-plan.md`, `return-receipt.md` | For workspace runs (in the workspace root): the original checkout, branch and baseline, the reviewed return plan and the guarded return receipt that completion requires. |
| `report.html` | Derived report written for done and halted runs; not workflow state. |

The live Improve child keeps its own receipt at
`<workspace>/.shiploop-improve/<run-id>/<action>/packet.json` in the execution
worktree; see [Improve context ownership](improve-context.md). Implementation
chains keep their own append-only ledger; see
[parallel implementation chains](parallel-chain.md).

## Test decisions in `state.md`

`state.md` retains accepted strategy results in `accepted`/`history`, and
initial item test decisions in existing `work_items[*].context`. Packets derive
a bounded **Run-wide test strategy source** from the latest completed root
`test-strategy` result, with its `results/<action>.md` and `accepted.<action>`
locators. An Improve handoff receives that same source plus the **Current item
test-decision source**: the latest completed `step-plan`, `test-spec`,
`test-author`, `test-refine` or `regression` result owned by the current item.
These producers retain decision revisions in ordinary `evidence_refs`, not by
rewriting the item's initial context. These are untrusted host reports to
revalidate, not a new test-state schema or a passing-check receipt. Follow
[test decision handoffs](repeatable-test-suites.md#carry-test-decisions-through-stages)
to retain fixture, suite and local/remote choices through later work.

## Delegation

Every run records the run-level `delegation` key, `inline` or `ask-agent`. New
runs created by `init` or `workspace start` record `inline` unless
`--delegation ask-agent` is passed. Change it only with
`delegation --run-dir RUN --set inline|ask-agent`, which applies from the next
issued action: the action pending when you switch, including its Improve
checkpoint, keeps the route it was issued with, and the command is refused on a
halted or done run. A switch made while an action is pending records optional
`delegation_hold: {action, route}` for that action; it is ignored once another
action is issued. See the [navigator guide](navigator.md#run-it).

## Authority and safety rules

- Do not hand-edit `state.md`, `results/` or `improve/`. Only the script's
  locked Markdown transaction writes them; the host writes only its inbox
  result, notes and product files, then runs the printed callback.
- A state the current code cannot load is refused, never repaired or
  converted. That includes navigator v1/v2/v3 runs, the removed managed and legacy
  modes, and a protocol 4 `state.md` with unexpected or missing keys, such as a run
  without `delegation`. The error names the protocol, mode or keys. Preserve
  the directory as evidence and start the request again in a fresh run
  directory.
- An identical replay of an accepted action is idempotent; a conflicting result
  for a consumed action is refused. A stale or unknown action ID changes
  nothing.
- A symlinked or forged run file, or a corrupt state fence, is refused rather
  than followed or rewritten.
- Results and notes are host reports. Their presence proves neither that tests
  passed nor that an external operation happened. Keep secrets and
  credential-bearing output out of every run file.

## Product documentation is separate

Product README, function docs and enduring test-case docs belong in the product
worktree and Git. They are **not** ShipLoop state. Do not put run cursors,
receipt dumps, raw logs or harness journals in them; link run evidence from the
result instead.
