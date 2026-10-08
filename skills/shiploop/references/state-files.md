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
| `state.md` | The navigator state: protocol version, execution mode, run ID and revision, repository and original prompt, current stage/action/status, work queue and `work_index`, per-item `inner_loops`, accepted results and history, the selected Improve card, the active Improve child and imported Improve records, chain bindings, the run's `delegation`, the required run-level `lint` option (`fix`, `report` or `off`; a saved run without it is refused) and the required run-level `backchain_passes` option (`one`, `converge` or `none`; a saved run without it is refused) and the required run-level `planning_review` option (`stage` or `none`; a saved run without it is refused). Protocol 4 adds `planning_reconciliations`, and state version 4 adds `revisions` (how many times each work item went back to `step-plan`, at most 2). |
| `notes/` | Host-written run notes. ShipLoop creates the empty directory whenever it prints a packet, so a model never needs `mkdir`; the notes and the pass log stay the host's to write. Notes named in results' `evidence_refs` include the canonical `notes/environment-lifecycle.md`. `notes/<action>.md` is the optional pass log: the host creates it when a pass starts and appends what each pass checked and what is left. Every packet names this action's pass log with the same conditional rule (open it first after a reset if it exists; if it does not, nothing was logged) and the context index lists it under "In progress"; neither reads the file, so neither can say whether it exists. It is a recovery aid, never a completion gate and never evidence: ShipLoop's own test-run records are the evidence, and a test-loop or quality-loop stage keeps its iteration state in the Until Loop receipt. |
| `inbox/<action>.md` | Where the host writes the current action's result before running the printed callback. It is input, not accepted state. It stays after acceptance for two uses: replay (a repeated `complete` of the same action is compared with `accepted`) and the pending draft after a kill. It is refused as a planning dependency because it is mutable. |
| `results/<action>.md` | The accepted result for one action, written by the script in the same transaction as `state.md`, and the "Read first" copy a packet points at. `state.md` `accepted[<action>]` stays the authority: on a planning-return path `planning_context.collect` fails when the file's parsed content differs from state (parsed equality, not bytes; an ordinary run does not check it). |
| `improve/<action>/` | The imported Improve child record for one parent action: its receipt, terminal packet, the trivial-pass review files (two, or one for an unchanged first pass) and copied evidence. |
| `workspace.md`, `return-plan.md`, `return-receipt.md` | For workspace runs (in the workspace root): the original checkout, branch and baseline, the return plan whose dispositions `review-return` records, and the guarded return receipt that completion requires. |
| `report.html` | Derived report written for done and halted runs; not workflow state. For a worktree run it lists, read live from Git, the branches and worktrees the run left in the source repository with the command to remove each; ShipLoop never removes them itself. |
| `progress.html` | Self-contained live plan, activity and key-file previews, published by a read-only observer. Browser refresh reads the whole file; no web server is needed. |
| `progress-observer.json`, `.progress.lock`, `.progress-stop`, `.progress-disabled` | Display process status, singleton lock, cooperative stop request and restart preference. None owns workflow state or proves the workflow is running. See [live progress view](status-display.md#live-html-progress-view). |
| `status.md` | Derived copy of the user-facing [status block](status-display.md), rewritten by every saved transition in the same transaction as `state.md`; not workflow state. |
| `decisions/<action>.md` | The user's own reply to a question (or a person's report after steps) a blocked result was `awaiting`, recorded by `resume --answer`/`--observed`. |
| `improve/<action>-bind.md` | The candidate's tree when that Improve child was bound; the import compares against it to find the review's own uncommitted edits. |
| `lint/` | Script-owned lint output, never exit-criteria evidence: per-item base snapshots (`items/`), per-action records and patches, byte-exact tool logs (`logs/`, mode 0600), scratch space (`tmp/`) and pending fix journals. See the [lint catalog](lint-catalog.md). |

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

Test commands have two homes with different jobs, and no script compares them.
The strategy file the `test-strategy` stage names owns the repository's suite
entry points and is the durable catalog later runs inherit (committed under
`docs/shiploop`); plans point at it rather than restating them. The accepted
`step-plan` result's `test_commands` (with `system_commands` and
`consumer_checks` where recorded) is the per-item run list ShipLoop itself
executes (`test_loop.stage_commands`). A command in one and not the other is not
detected, and neither is a strategy file that keeps its commands outside a
fenced block, as its duty asks.

The planning basis travels the same way. Prelude planning packets (discovery
through plan) name the current accepted intake-through-test-strategy results as
**Current planning sources**. The stages that turn the accepted plan into work
(`step-plan`, `test-spec`, `system-test-author`, `release-plan`) name the
accepted `spec` and `plan` results there, beside the test strategy source, so
the steps, tests and release steps are planned from the accepted plan rather
than from memory. `test/shiploop-planning-handoff.test.py` pins which results
each stage's packet names.

## Run context index

Every save regenerates `context-index.md` in the run directory from `state.md`:
the request, each current accepted planning result (result file, summary,
registered notes, Improve receipt and lessons, and the plan's assumptions), the
work-item queue with each item's accepted results, the outer loop, and
superseded results. It is a derived view with pointers and short summaries, not
another record; `state.md` stays the authority, and nothing writes the index
but the script.

Every packet prints the index path right after its callback line, so no stage is
limited to the result of the stage before it. Active packets also print **Read
first**: the accepted results this stage builds on, resolved to their result
files from the script-owned `STAGE_READS` map in `shiploop_context_index.py`
(for example `verify` reads the spec, test strategy and the item's step-plan and
test-spec). A stage reads those before acting and reports a conflict with them
rather than choosing silently.

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

## Backchain passes

Every run records the run-level `backchain_passes` key: `one` (the default for new
runs), `converge` or `none`. It is set once, by `--backchain-passes` on `init` or
`workspace start`, and no verb changes it: an `init` or `workspace start` retry that
names another value is refused, and a saved run without the key is refused with the
fresh-run hint like any other missing key. See the
[skill guide](../SKILL.md#backchain-passes-option).

## Planning review

Every run records the run-level `planning_review` key: `stage` or `none` (`stage` is the
default for new runs). `stage` starts an Improve child after each of `spec`, `test-strategy`,
`plan`, `step-plan` and `test-spec`; `none` starts none, so a `none` run's `improve_results` holds
only the records at `system-test-author`, `release-plan` and the last `carry-forward`. It is
set once, by `--planning-review` on `init`
or `workspace start`, and no verb changes it: an `init` or `workspace start` retry that
names another value is refused, and a saved run without the key is refused with the
fresh-run hint like any other missing key. See the
[skill guide](../SKILL.md#planning-review-option).

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
