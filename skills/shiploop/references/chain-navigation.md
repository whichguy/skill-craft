# Implementation chains: navigation and settlement

Split from the ShipLoop skill card (`../SKILL.md`). Read once a chain is bound: its navigation packet, capacity, serial mode, ledger and settlement.

## Navigation and settlement

Use the selected Plan Dispatcher and Ask-Agent packages, external sibling
`.work-trees` checkouts, and the bridge's claim/start/import/prepare/done/finish flow.
For per-step chains, the script's `navigation` packet owns navigation. Perform
its returned actions, submit the requested observations or verification through
the named `operation`, then follow its exact `next_argv` to refresh. For every
claim action, claim and start every listed candidate that is actually ready and
safe up to `max_steps`; do not leave a safe native slot idle. Defer only a candidate with a
concrete recorded host-capacity, resource, readiness, or recovery blocker, then
refresh after every returned event. Never compute successors, select an unlisted
step, infer a launch from a recovered packet, or finish from an empty ready list.
`navigation.complete` marks chain completion; the top-level `complete` field
describes graph acceptance only. Supply actual readiness, capacity and
verification facts; if they prevent an offered action, retain that blocker rather
than inventing a transition.
Every new chain requires the selected Ask-Agent to declare the full current
managed-workspace capability set and a matching helper identity; a version number
alone does not qualify. Both parallel and serial preparation use that selected
helper; caller-prepared worktrees are not supported. Each step starts from the invoking branch's current integrated HEAD.
The parent imports and archives worker-local results, prepares and checks the
combination, merges it into the invoking checkout and accepts the exact attempt.
It refills safe ready capacity before asking the receipt owner to close accepted
workspaces. A higher package version alone does not establish compatibility.
Choose `chain bind --mode serial` to execute one dependency-ready step at a time
in the main context with no agent dispatch; default parallel mode uses native
Ask-Agent. Without `--mode`, a new binding is parallel and a replay keeps its
recorded mode. Serial start atomically records local ownership before issuing an
execute packet. Continue through all required steps and the verified return,
or retain an explicit incomplete blocker; an empty ready list alone is not done.
Only a fresh parallel launch packet permits native dispatch. Workers report; the parent
owns acceptance and the exact initiating-checkout return. The append-only,
timestamped ledger records bridge events without replacing Markdown traversal
or the child dispatcher's state. An unfinished chain blocks the normal producer
callback; after verified integration, continue with the step's Improve child and `test`.
The planning artifact reference is context, not graph navigation or execution
authority. Workers verify required local files before using them and report a
blocker when unavailable. Missing or drifted required inputs block fresh starts
or positive acceptance, but preserve observation, report capture, negative
settlement, retry, cleanup, and recovery. Do not copy runtime state, worker
status, or a whole mutable `state.md` into the manifest. Register every generated
planning file in the producer result's existing `evidence_refs`; explicitly
registered external local specifications are valid, while URLs remain
reference-only until materialized locally.
Accepted is the only persisted step-done state. The derived `completion` view
lists done/not-done; `chain done` is the one verified settlement transition.
Use read-only `chain history` for timestamped audit events and `chain pending`
for unfinished steps, unmet dependencies, capacity and cleanup recovery; neither dispatches
work nor repairs state. Both take `--run-dir` and `--action` without an input file.
Keep combined main-conversation status from actual execution observations and
dispatcher state; progress reports never accept work or release dependencies.
This does not parallelize whole work-item lifecycles.
Only binding schema v6 is supported; every chain operation, including history
and pending, refuses an earlier binding. Preserve its workspaces and ledger and
bind a newly reviewed chain rather than rebinding it. A cleanup failure
leaves the step accepted and must be resolved without executing its work again.
Final completion requires all contributions integrated and owned worker cleanup
complete. Keep dirty targets, conflicts and unknown files as explicit blockers.
