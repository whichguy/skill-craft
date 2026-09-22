# Consumer-owned workspace route

Use this complete route only when an invoking consumer deliberately delegates
inside its already-bound candidate workspace. It is separate from Ask Agent's
helper-managed default: `workspace_route: consumer-owned` pairs only with
`delivery_mode: in-place`, never with `patch`, `commits`, or `report-only`.
Read this reference in full before route selection, launch, recovery, acceptance,
or cleanup.

The currently declared consumer binding is ShipLoop navigator-v3's bound,
whole-skill Improve child. Its worker receives `execution_role: improve-executor`
and `delegation_owner: parent`; it runs the complete selected Improve invocation
without dispatching another whole Improve run. Standalone Improve dispatch keeps
its existing owner-managed behavior and does not select this route. The binding
is a Codex native pilot with evidence from bounded native fixtures. Managed-workspace host
evidence does not establish this composition on Codex, Claude, Grok, or another
host.

## Select only with a complete consumer contract

The selected Ask Agent card must declare
`ask-agent/consumer-owned-workspace/v1`. The invoking consumer must explicitly
provide all of the following before a native launch:

- `workspace_route: consumer-owned` and `delivery_mode: in-place`, the consumer
  identity, and the route reference it selected.
- The canonical absolute candidate workspace and its canonical Git root; the
  current candidate/base and HEAD; the consumer binding marker; and the exact
  allowed-write scope and exclusions.
- The inherited staged, unstaged, and untracked inventory to preserve; the
  current candidate/target relationship; and any actual contribution SHA policy
  or explicit no-commit authority.
- The current task's scoped approvals, declines and pending decisions with their
  conditions and authorization sources, using the card's decision handoff rule.
- The selected Ask Agent, Improve, and runtime identities; a fresh native-context
  requirement; the executor role, delegation owner, one-candidate-writer rule,
  and delegate ownership/collection requirements.
- Required reviews/checks, the evidence root, the exact child terminal-receipt
  and completion-evidence locators, and the durable `host-owner.md` locator.
- The exact parent-only acceptance and continuation instruction, including the
  consumer's later original-caller delivery boundary; the final-delivery owner;
  and the consumer-owned cleanup owner.

An ordinary Ask Agent request that does not select this route uses the
helper-managed default. If a consumer explicitly selects this route but its
contract, capability, required fresh context, canonical workspace, or ownership
evidence is missing, fail closed: retain the available locators, report the
concrete gap, and leave the action pending. Do not prepare a helper workspace,
fall back to the default route, create shared writes, invent a receipt, or infer
the contract from an existing worktree.

## Bind the existing candidate without the helper

`identity --skill-card` remains available only as a read-only selected-package
identity check. It proves the card/helper package selected by the host; it does
not select a route, create a workspace, create a receipt, or validate a consumer
binding.

For this route, never call the helper's `prepare`, `inspect`, `check-context`,
or `close` on the consumer candidate. Do not create a worktree or branch, replay
a snapshot, make a helper patch/commit transfer, cherry-pick, or perform a
second transfer. This does not prohibit commits required by the consumer inside
its bound candidate; report those SHAs as evidence for parent acceptance. The `patch`, `commits`, and `report-only` enum and its helper evidence
belong only to the helper-managed default.

Launch a fresh general-purpose native executor when the host supports the
consumer's requirement. Do not replace it with inherited conversation context,
a shell-launched model, an external scheduler, or a new runtime schema. The
consumer leads that fresh assignment with the parent's current context and
[inline current learnings](../SKILL.md#carry-current-learnings-inline), then asks
the worker to invoke the selected Improve skill. It preserves the task's normal
tool, MCP, skill and authorized deployment capabilities and supplies these literal
assignment markers after that opening:

```text
workspace_route: consumer-owned
delivery_mode: in-place
execution_role: improve-executor
delegation_owner: parent
```

Only one worker owns candidate writes at a time. It may use scoped native
delegation only when its delegates cannot concurrently write the candidate; the
owner collects those delegates before returning. The parent and other workers
do not run edits or input-mutating checks in that candidate while the owner or a
delegate may still be active.

Before task work, verify the process `pwd` and `git rev-parse --show-toplevel`
against the canonical workspace and Git root. Set the exact consumer workspace
as the operation directory for every subsequent shell call. Recheck the cwd and
Git root after a directory change, retry, or unexpected tool routing. `git -C`
does not establish the shell directory. Use absolute paths for other file tools.
A mismatch stops work and is returned as a blocker; a prompt echo or
worker-reported path is not enough.

## Parent-owned launch and recovery record

The consumer derives `host-owner.md` beside its child `packet.json` in the same
action directory. It is a durable, append-only parent coordination record, not a
new scheduler, runtime state schema, or terminal success receipt. Only the
parent writes it; the worker may read it for orientation but cannot use it to
select or execute a parent transition.

Before native dispatch, the parent appends a launch-intent entry with the route,
consumer and selected-package identities, binding marker, canonical candidate
workspace/Git root, current base/HEAD and dirty inventory, allowed scope,
evidence and child-receipt locators, executor assignment, and parent recovery
command. Launch intent means **possibly launched**. An interruption between a
launch request and returned native handle leaves ownership unknown.

When available, the parent appends the returned native handle, each
host-exposed delegate identity, collection evidence, and confirmed stop evidence
without replacing earlier events. The parent later appends acceptance and caller
delivery outcomes with locators to bulky evidence. Native handles stay private
where the host requires it.
For a later user decision, append its source, scope/target, conditions and native
forwarding/receipt status here, and send it to the existing worker. This record
preserves decision provenance; it does not authorize a parent transition.

On recovery, read the child receipt and its sibling `host-owner.md` before any
new assignment. An intent, a partial record, a missing handle, an uncollected
return, a running owner, or unknown delegate status blocks replacement,
acceptance, and cleanup. Collect the old worker or obtain host evidence that it
never launched or has stopped before another writer can start. An absent record
on recovery is unknown ownership, not proof that nothing launched. Preserve all
prior intent, handles, collection, and stop evidence when appending the result.

## Return, acceptance, and separate delivery

The worker leaves candidate edits and all review/check evidence in place. Its
compact native return names the task outcome or blocker, observed workspace and
Git root, binding marker, changed paths and scoped diff/evidence locators, and
the exact child terminal receipt/completion-evidence paths. It also includes:

- Improve's cumulative key implemented changes and lessons learned inline,
  with actual validation and remaining work. Preserve this substantive summary
  in the parent's result after acceptance, updating delivery state to match the
  parent's observed outcome.
- Initial and final HEAD; inherited staged, unstaged, and untracked inventory
  with the preservation result; actual contribution SHAs or the explicit
  no-commit reason.
- Actual checks and qualifying review evidence, including gaps; stopped worker
  and delegate status/evidence; and the next owner with retained paths.
- The canonical candidate and original caller/target relationship; the unchanged
  parent-only continuation locator; and a statement that no parent callback,
  workspace return, final delivery, or cleanup was executed by the worker.

The parent collects the actual native return, verifies current candidate edits,
scope, Git identity, dirty-state preservation, checks/reviews, exact terminal
receipt, and stopped worker/delegate evidence, then appends its acceptance or
blocker to `host-owner.md`. In-place acceptance means the worker's edits already
reside in the bound candidate; it is not a patch or commit transfer.

The consumer separately owns final delivery to its original caller and executes
only its exact parent continuation after acceptance. A successful worker or
accepted candidate does not prove caller delivery. If the consumer's final
return is blocked, retain the candidate and evidence, mark the overall action
incomplete, and name the next owner. Only the parent writes the owner record,
executes the continuation, and performs any consumer cleanup; Ask Agent never
removes the consumer workspace.
