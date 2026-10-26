# Implementation chains: route and binding

Split from the ShipLoop skill card (`../SKILL.md`). Read on a `delegation: ask-agent` run at `implement`, and before any `chain` command.

## Ask-agent context boundary

For an
`implement` producer, select the packet's chain route first. During that producer, its bound mode and executor take precedence: parallel chains
retain their capacity and bypass this serial context boundary; explicit serial
chains execute in the main context without workers. Do not wrap a chain in an
extra worker or restart an existing attempt. Follow the
[chain mode contract](parallel-chain.md#serial-execution-in-the-main-context);
serial chains execute in this conversation.
Chain precedence ends at producer completion. Improve follows its own selected
context and ownership policy even when the historical chain binding remains.
For other serial work where delegation is permitted, save these locators
and prefer one native fresh worker at a time, without inherited conversation.
It must have the required tools, the existing workspace and a return route to
the live parent. Give it the current packet, selected skill locators and necessary
durable references. The parent waits, verifies the result and alone submits the
ShipLoop callback; only one owner writes to the candidate. Recover or collect an
existing owner before replacement. An already-fresh assignment is not delegated
again when the prefix repeats. Serial execution means waiting before
the next assignment; it does not require reusing the same conversation.
For Improve, the fresh context belongs to the one executor running the whole
invocation, not to the parent; it retains context between its review iterations
and respects its existing owner/recovery rules. When no fresh worker is usable
for a producer, execute it in this conversation.

## Parallel implementation chains

Implementation chains are the opt-in `delegation: ask-agent` route. Under
`delegation: inline`, `step-plan` records its `steps` in order, without a Plan
Dispatcher execution graph; its actual Improve loop (`stage` runs) reviews them. ShipLoop then
issues one `implement` packet per step, in that order, in the execution checkout
in this conversation: each packet names its step, its helper `skills`, the steps
already accepted and the ones still to come. An Improve stage reviews each
accepted step, and the callback after the last step's review moves to `test`. No chain binding, Ask Agent or native workers, and no Plan Dispatcher.
Which steps are done is read from the run's history, so recovery reprints the
current step. `chain bind` refuses a fresh binding on an inline run before any
side effect; a replay of an existing binding keeps its recorded mode. To use a
chain, first switch the run with `delegation --set ask-agent`.

On an ask-agent run, after creating initial steps, require their plan and execution graph to complete
the selected actual Improve loop before execution (in a `stage` run; a `none` run has no such
loop, so only ShipLoop's checks at `complete` and the structural `backchain-check` have seen the graph). The normal `plan`/`step-plan`
handoff owns that review; follow the linked guide for late graph creation or
material revisions. Retain the completed review's graph identity and evidence.
For a reviewed graph within the current `implement` action that has safe
dependency-independent steps, the main owner uses [the parallel implementation
chain](parallel-chain.md) by default when the selected Plan Dispatcher
and Ask-Agent contracts are compatible and observed native slots are available.
Record a concrete compatibility, capacity, resource, or
readiness blocker when that route cannot start; choose serial execution only for
an explicit user or host limit. Bind `--capacity` to the observed user/host
native-slot limit for this run; the parallel default is not evidence that only
two safe slots exist.
Before binding, use the bridge's read-only `chain planning-inputs` view for that
exact run, action, and reviewed graph. Resolve every current-required planning
reference through its printed resolution contract, then bind the immutable
planning-artifact manifest. Its deterministic `planning-brief.md` consolidates
key reference statements, decisions, constraints, acceptance context, and
reference locators from the accepted planning pass. It is supporting material,
not the user prompt and not a replacement task directive. The dispatcher's
step `contract.task`, `contract.ready`, and `contract.done` remain the worker's
sole assignment. The reviewed graph stays unchanged; the manifest is a separate
input reference for Plan Orchestrator and every worker packet.
Use the complete worker packet, including its engineering-guidance locators.
For parallel execution, follow the returned launch action: pass the packet
unchanged through the selected Ask Agent launch contract to a fresh context with
a compact Current learnings block. Preserve available host capabilities within
existing task authorization. Carry applicable approvals, declines, pending and
revoked decisions with scope, conditions and actual source through its existing
authority contract, separately from advisory learnings. Retain the effective
assignment in the existing parent record or retained handoff, durably outside the
worker workspace. For serial
mode, execute it in the current main conversation. Each bounded executor applies
relevant planning and engineering guidance, returns discoveries, rationale, checks
and uncertainty through the existing summary and declared files, and reports
conflicting premises before affected work. The parent reads and retains those
findings for verification, recovery and later assignments.
