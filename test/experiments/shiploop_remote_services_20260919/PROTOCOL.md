# Remote-service discovery pilot

This is a two-case paired cold-reader prompt study, not an end-to-end ShipLoop
run, Until Loop convergence study, executable application test or live remote
probe. It evaluates the usefulness of a conditional decision cue while preparing
an architecture proposal. No candidate is automatically promoted by this study.

Freeze current v3 discovery/research duties, shared recursive-discovery guidance,
behavioral actor/state/async guidance and platform discovery guidance as baseline.
Candidate adds only candidate-cue.md. Supply each fresh agent just its neutral
arm input and report path, without parent history. Run each case once per arm,
with the same host-default model/settings and 1100-word limit. Retain all results,
including incomplete or unfavorable ones. No reruns to select a favorable answer.

Before dispatch, hash inputs and source files and freeze this protocol and rubric.
Each case also contains the same local-only negative control. Agent outputs are
independent draft artifacts; workers do not inspect other arms or the rubric.

An independent fresh reviewer receives each fact sheet, the rubric and reports
with neutral labels and reversed candidate position between cases. It receives
neither cue nor variant map. Require passage-level support for findings and
critical omissions. Assess correctness and grounded decisions before concision.
No statistical/general superiority claim is supportable from two cases and one
sample per variant. Source character counts may describe added context; they are
not measured model token usage. No performance winner is inferred from timing.

Rubric (applicable case facts govern; omitted unneeded machinery is good):
1. Distinguish provision/development MCP from app runtime; map schema and data
   operation capabilities and authorization separately without guessing coverage.
2. Preserve remote source of truth; justify facade/cache/projection using unknown
   measurements; clarify copies and avoid declaring cache automatically required.
3. Separate freshness and authorization: tenant/user key alone is insufficient;
   current allow/deny on reads, independent permission invalidation/revocation,
   account switching, safe behavior on authority failure.
4. Cover invalidation races, data/schema/permission changes and read-after-write;
   schema case must address event gaps and late fills specifically.
5. Choose usable async mechanism: reuse record/polling when adequate; acceptance
   versus completion, idempotency/revision, stale completions, restart/dispatch
   gap, authorized result reads; notifications are not durable completion proof.
6. Reconcile prior intent/local/remote/requested delta without overwriting unrelated
   metadata or computed fields; recheck drift, capability and authority at write.
7. Handoff explicit affected files/roles, evidence locators, ordered prerequisites,
   independent acceptance checks and unresolved gating conditions to development.
8. Local control needs no remote discovery or new service prerequisite.

Report per criterion: supported / partial / missing / incorrect, with reasons.
Flag material regressions even if the longer candidate covers more topics.
Possible recommendation: refine, retain baseline, or continue a focused pilot.
Production changes require broader packet integration/regression and cold handoff
evidence; this study cannot establish real Salesforce permissions or cache safety.
