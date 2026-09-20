# Compact completion-driven dispatch

## Outcome

At initialization and after every event, process the exact returned attempt,
accept only verified completion, and fill all safely available execution slots.
A slow sibling never becomes a wave barrier. New invocations select current
published source instead of historical release worktrees.

## Smallest implementation

1. Reuse the existing claim/start/report/verify/settle loop and its durable state.
   Order eligible starts and claims before potentially waiting observations.
   Keep parent recovery, resource conflicts, planning prerequisites and capacity
   reservations authoritative. Serial mode retains capacity one.
2. Make branch identity visible without a new event schema: retain Dispatcher
   report/receipt envelopes and detailed settlement attempt records; add the
   settlement's authoritative `step`. Add `step` beside every ShipLoop navigation
   `attempt`, including cleanup and recovery. Derive identities from durable
   records; never trust arrival order or a caller-supplied branch label.
3. Keep one scheduler and no additional queue, ledger, polling service or mutable
   completion cache. `next` derives the frontier from accepted dependencies;
   existing exact continuations, owner fences, receipts and append-only history
   support cold recovery, duplicate delivery and out-of-order results.
4. Merge into current remote main, verify the combined code, push, then activate
   from a clean rolling main checkout with the existing installers. Preserve
   unrelated dirty checkouts. Refresh copied installs when main is updated.
   Recorded identities/hashes inside an active run are recovery evidence, not
   installation release pins, and remain enforced.

## Alternatives rejected

A new scheduler or shared cross-repository library would duplicate durable state
and weaken portable packages. Renaming the existing settlement `attempt` object
to a scalar would break consumers for no scheduling benefit. A new required
capability gate is unnecessary for additive labels derived by each package.
Future capacity and host adapters can use the existing claim/start boundary;
unknown future requirements do not justify new persistent machinery today.

## Verification and delivery

Baseline: existing Dispatcher CLI 24 groups pass before the additive identity
change; the earlier implementation audit records the original lifecycle baseline.
Verify copied Dispatcher CLI accepted/rejected/replay/cascade identities; ShipLoop
navigation identities across parallel, serial, recovery and cleanup paths; eager
refill and join gating; current Dispatcher cross-package real-Git integration;
bounded packets and generated package parity. Run the required Backchain hygiene
gate and independent review. Native workers in these tests are deterministic
fixtures, not a claim of live model compliance.

Commit only task files from isolated branches, integrate current main without
discarding concurrent work, push both repositories, and read back remote SHAs and
installed paths. Installation freshness is distinct from durable run identity.
