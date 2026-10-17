# Starting a run

Split from the ShipLoop skill card (`../SKILL.md`). Read before the first `workspace start` or `init` of a run, and before a workspace return.

## Progress view

The CLI starts a read-only observer after a successful run initialization or
packet command. Open the packet's `progress.html` to follow the plan, recorded
activity, and embedded spec/architecture previews. The ordinary HTML file
refreshes itself without a server. This observer only publishes display files;
it never owns or backgrounds workflow execution. See
[live progress view](status-display.md#live-html-progress-view) for
start/stop controls, draft-versus-accepted labels, and freshness limits.

After the first successful `workspace start` or `init`, show the user the
packet's absolute progress-view link in your startup message: "You can use this
HTML file to track changes during this ShipLoop run." Make "HTML file" the link
by copying the packet's Markdown link verbatim, preserving its encoded target
and angle brackets. Show it once per run; keep following the current action afterward. If
the observer is unavailable or disabled and the file has not been created,
report that status instead of presenting a working tracking link.

## Workspace return

The returned packet binds its repository locator to the execution worktree and
its run directory to `WORKSPACE_ROOT/run`. `WORKSPACE_ROOT/workspace.md` retains
the original checkout/branch and baseline. Do all product work in that worktree;
do not silently fall back to editing the source. At the final planned integration
boundary, follow the packet's plan-return, review-return and guarded return commands. Completion
requires a verified return receipt. A dirty starting checkout receives only the
new delta and keeps its original index; this is not a Git merge/commit.
The return happens at release or handoff, after the end-of-work Improve
child, once no child is active. A product fix committed after that return (for
example one found by a post-deploy check) goes back as a follow-up return: run
the same plan-return, review-return and return commands again.
If source return must itself trigger a required delivery check, retain that
ordering conflict as incomplete; use the workspace policy's reconciliation rule.

## Existing-implementation baseline

For each new request changing an existing implementation, follow the
[initial repository baseline](execution-planning.md#initial-repository-baseline).
After minimal instruction, command and environment inspection, run the existing
smoke suite or practical full suite as discovery's first verification activity
in the packet's repository (execution worktree, or the explicitly selected
in-place/non-Git starting directory), before product/test/config/dependency edits. Record
the actual command, starting content, target, outcome, limits and evidence
locator. Carry failures or missing tests into planning as explicit prerequisites;
they are not passes. Discovery and baseline reviews do not repair the product or
its tests. A planned repair or test-bootstrap may establish its own starting
failure/missing-coverage evidence before its scoped edits; dependent feature work
waits for the required passing checks. Reuse only applicable same-run evidence;
a new follow-up request runs a fresh baseline.

## Recorded Improve card

New workspace and direct runs use navigator **protocol 4**; there is no protocol
selector. A saved run the current code cannot load, including any navigator
v1/v2/v3, managed or legacy run, is refused with an error that names its protocol
or mode; start a fresh `--run-dir` (or workspace root) for that request. If
new-run initialization did not select an Improve skill with `--improve-skill`, it records the
card installed beside ShipLoop (found by file location in this plugin install and
validated; no name or PATH search). ShipLoop binds that recorded card to the first Improve stage
itself. Only when the recorded card no longer resolves does the Improve packet print
`improve-bind --action <improve id> --skill-card ...` (a `--planning-review none` run has no planning
child to bind it, so it is still refused without `--improve-skill`). Where no installed card
validates, nothing is recorded and the packet prints a marked blank and says where ShipLoop looked.
Use the packet's exact command and absolute selected-card path; never substitute a same-named skill.

## Consumer-delivery pilot

For a new run explicitly piloting consumer-delivery declaration checks, add
`--delivery-contract` to `workspace start` (or direct `init`). Read
[consumer delivery](consumer-delivery.md) before starting a
deploy-and-interact pilot so its declared behavior obligations are enabled from
initialization. That reference defines the result contract, source-only cases,
and recovery boundaries. The option
does not grant publication authority or retrofit an existing run. Use the
packet's generated assessment template; the script supplies its binding.
