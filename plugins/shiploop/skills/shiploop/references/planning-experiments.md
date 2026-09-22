# Experiments during planning

Navigator v4 is an explicit new-run pilot. Select `--protocol-version 4` on
`workspace start`, or `--navigator-version 4` on `init`. Existing runs keep their
saved protocol; the default remains v3. Follow the current packet rather than
retrofitting this guide onto an active older run.

Plan Improve screens the provisional plan for consequential uncertainty and
conducts worthwhile experiments through its existing Improve/Until Loop. Early
research still answers questions visible before a plan exists. No additional
experiment phase, nested loop, or dispatcher is introduced.

```mermaid
flowchart TD
    A[Draft plan] --> B[Existing Plan Improve]
    B --> C{Evidence sufficient?}
    C -->|No, bounded probe available| D[Run and evaluate experiment]
    D --> E{Upstream premise invalidated?}
    E -->|No| B
    E -->|Yes| F[Stop child and retain evidence]
    F --> G[Parent reconciles earliest affected stage]
    G --> A
    C -->|Yes| H[Normal qualifying reviews]
    C -->|Blocked or inconclusive| I[Retain gap and stay incomplete]
    H --> J[Accept coherent plan and prepare]
```

A finding can change the plan, confirm it, or leave a material question open.
Only the first two can support readiness; an experiment's mere completion cannot.

## One review cycle

Read the current plan, current planning sources, and prior observations. Ask:
**Which feasible experiment could materially change a decision or establish
whether its consumer may proceed?** A task can need zero experiments. Reuse
sufficient current evidence rather than repeat it to satisfy a quota. Baseline
checks and required acceptance checks remain due regardless.

Before an experiment, append a dated record to the packet's investigation
notebook. Name the decision and assumption, plausible alternatives, affected
consumer, representative source/configuration/target identity, discriminator and
outcome-to-decision mapping. Specify allowed effects, time/action bound, and
cleanup owner before running it. Use the smallest adequate fixture and record
why it exercises the intended boundary. For noisy results, predeclare controls
and repetitions.

Run the authorized probe, retain its exact command and output behind evidence
locators, and evaluate the apparatus as well as the outcome. A failed harness,
wrong target, timeout, missing access, or inconclusive result leaves the
assumption unresolved. A valid negative result may disprove it; a valid
confirmation may justify proceeding with no plan diff. Revise the candidate and
its checks, then reassess the remaining frontier before launching another probe.

This entire cycle belongs to one actual Until callback. Material findings or
repairs reset its normal convergence streak. Do not launch another Until or
Backchain convergence loop, invent a separate experiment counter, or compress
multiple reviews into one callback. The existing two qualifying trivial reviews
remain necessary, together with coherent current planning artifacts and no
worthwhile unresolved experiment due now. Required architecture choices cannot
be relabeled deferred merely to accept a graph.

## Scope, accounting, and recovery

The parent names the candidate plan, investigation notebook, evidence paths and
scratch-fixture scope in the existing Improve contract. Use its consumer-owned
workspace. Experimental code stays in the declared scratch area, normally below
`.shiploop-improve/<run-id>/`; exclude it from product integration. Preserve
sanitized observations before cleanup. The child may revise the candidate plan;
it may not promote prototypes, repair the baseline, mutate production, acquire
persistent infrastructure, or broaden authority merely to finish planning.

Use [research's shared allowance](research-loop.md#budget-stopping-and-convergence):
by default at most 15 active minutes, 64 observable host actions, two capability
candidates and three experiments, reserving two minutes/eight actions for
reconciliation and cleanup. The same investigation keeps its original allowance
through child iterations, action changes, reconciliation and context resets.
Record consumption, remaining allowance, limitations and pending cleanup in the
stable notebook printed by the packet. A new action ID grants no new allowance.
This is host-accounted guidance, not a protocol-enforced budget or watchdog:
ShipLoop cannot observe every native tool invocation. If accounting is uncertain,
use a conservative available bound and retain that limitation. Exhaustion is an
incomplete outcome, never a trivial review.

Keep large logs and the full generated review prompt behind locators. Use compact
Until continuity context with explicit resource references; copying the entire
parent packet into the child contract can exceed its bounded state limit. A fresh context reads the original request,
current source/action identities, candidate, dated observations, remaining
allowance, pending cleanup and next useful uncertainty from the notebook and
packet. The rolling Until handoff is continuity context, not the experiment audit
history. User-approved scope changes remain user decisions.

## When a finding changes an earlier premise

A plan-local finding stays in the current Improve child. If the finding
invalidates discovery, research, specification or test strategy, identify the
**earliest** affected stage. Retain the premise and evidence in the reconciliation
summary and local evidence files; do not edit accepted upstream results in place.

The return path is available only for v4's initial `plan` Improve child before
any preparation, work-item execution, chain binding or workspace return. It
currently supports the bundled ephemeral Until runtime. Legacy durable children
remain incomplete rather than receive a fabricated settlement.

1. Finish the current bounded work and preserve observations/cleanup status.
   Report the unresolved or non-trivial review, unsatisfied or unknown exit, and
   cancelled continuation through the child's actual callback. Save its complete
   raw `stopped` packet at the exact parent-issued receipt location.
2. The parent collects the actual worker's return or confirms cancellation.
   An uncertain/live owner, missing terminal packet or usable child callback
   prevents settlement. The packet importer checks structural declarations and
   local file identities; it does not independently authenticate worker death.
3. Write the packet-issued reconciliation receipt with exactly `summary`,
   `target`, and nonempty `evidence_refs`. Target is `discovery`, `research`,
   `spec`, or `test-strategy`. Evidence references must be absolute regular,
   single-link, non-symlink files inside the child workspace. Use the printed
   `improve-reconcile` callback, never `improve-complete` for this stopped child.
4. ShipLoop archives the raw terminal packet, receipt and evidence, records a
   non-success `reconcile` result and timestamped event, then issues a fresh
   action at the target in one recoverable Markdown transaction. Event/history
   order determines causality; the local UTC timestamp is informational.
5. Rerun the fixed suffix through plan, with the normal Improve owner at each
   stage. Reuse still-applicable evidence explicitly. Superseded results remain
   audit history; only the governing source projection can authorize preparation
   or supply required dispatcher context. Exact callback replay has no second
   effect; conflicting/stale callbacks are rejected.

If the parent call was interrupted, recover using the same run's `next` packet.
Do not recreate the child or repeat its experiments merely because the parent
response was lost. Missing or changed archived evidence blocks recovery rather
than silently restoring stale authority.

After preparation begins, this pilot does not replace an active graph. Block
architecture-dependent consumers and use an already-supported corrective route,
or retain an explicit incomplete handoff. If a feasibility question requires
substantial product implementation, keep its dependent architecture unresolved
and scope the feasibility work separately. A generic “experiment completed” edge
cannot certify that the tested condition holds.
