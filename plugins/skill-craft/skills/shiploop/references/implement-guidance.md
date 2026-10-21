# Implement guidance

How one implementation step settles its design before building. The implement packet cites this guide; its duty items
stay the step's directive (scope, check, hand-off, send-back), and Code craft stays the code rubric. Nothing here adds a
result field or a gate.

## Considerations

Before building, settle each consideration the step touches, from its anchor: the anchor settles a point, follow it;
the anchors are silent, decide within the step and write the decision back (KNOWLEDGE/architecture.md ## Decisions);
a point that conflicts with an R-n or AD-n, or needs work outside the step, is a send-back. Keep a short line per
consideration the step touches in RUN/notes/<action>.md, so a context that starts fresh rebuilds it from the notes and
the packet. A consideration the step does not touch needs no line.

1. **Whole step** (the criteria; architecture.md ## Structure): everything the assigned criteria need at the step's
   boundary, meaning the change and its connections (entry points, registration, wiring, configuration, permissions,
   content, the documentation a criterion requires), placed per ## Structure. Note changed usage or operations for the
   document stage.
2. **Interactions** (the criteria; ## Interfaces and boundaries; interaction AD-n). People: what they see and do;
   waiting, error and empty states; accessible use. Systems: contracts, untrusted input and its validation, who may do
   what, sensitive output, slow, failed or repeated messages, compatibility with existing consumers.
3. **Building** (## Stack; environment.md ## Commands): a valid artifact, built or validated the project's way; no tool
   or dependency without a present need, and any added one recorded.
4. **Deploying** (## Targets and runtimes; ## Access and accounts; ## Platform facts; ## Real-boundary checks): target,
   order, per-environment settings, staged or reversible activation where the risk warrants, the check after, the undo.
   Only effects the run's recorded authority covers; preparing or recording a release action does not authorize
   running it.
5. **State** (## Structure; storage AD-n; spec.md ## Non-functional requirements): what the step reads, creates or
   changes, with its owner and shape before and after; compatibility with stored state; ordering, atomicity, concurrent
   updates. A transition it needs is prepared, applied only where authorized, safe to rerun and recoverable from a
   partial failure. Invent no storage.
6. **Operating** (## Non-functional requirements; ## Conventions; ## Platform facts): what an operator can see and
   diagnose; cost, limits, capacity; independent work in parallel where the platform allows it and it pays; secrets and
   permissions over time; retention, cleanup, owner.
7. **What exists** (## Structure; ## Conventions; ## Skills; ## Platform facts): reuse unchanged, combine or extend
   before creating, in the repository and in the environment's services (identity, storage, queues, scheduling,
   caching, logging, search, notification); duplicate none; keep current behaviour working; follow the example.
8. **Proof** (## Commands; ## Harnesses and suites): what demonstrates each assigned criterion now. The step's Proof is
   the check ShipLoop runs; never weaken or replace it to pass, and a passing Proof does not show a criterion it does
   not exercise.

## Evidence

What the summary claims for a criterion is something run or inspected, with what it showed and where its output is. A
description of the change or a check still to come is not evidence; for a document, an inspected passage and a
consistency check are. A check a later stage owns stays with that stage, never reported as done here. Temporary probes
go in RUN/scratch; permanent tests are the test stage's.
