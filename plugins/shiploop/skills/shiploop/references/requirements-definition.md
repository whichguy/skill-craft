# Existing specs and non-functional requirements

Treat requirements definition as an explicit activity within existing discovery,
research, and spec stages. It defines the requested product, not ShipLoop's own
workflow. Use the current protocol's notes, result/evidence fields, planning and
review routes; no new graph stage, state schema, or parallel spec is needed.

## Establish the applicable baseline

Before drafting a spec, locate relevant existing specs/PRDs, maintained
requirements, API contracts, architecture decisions, and quality/security/test
policies through README/AGENTS, the project index, and targeted repository
searches. Follow relevant links even when the document is not named `spec.md`.
An absent index or a first ShipLoop run does not make an existing product blank.
Record which sources/sections were inspected and their scope/status: accepted,
draft/proposed, superseded/historical, or unresolved. A filename, modification
date, old run prompt, or passing implementation alone does not prove authority.
If an expected source is unavailable, retain the gap before dependent work.

Reuse the [maintained requirements home](project-knowledge.md#maintained-product-requirements)
and its IDs/headings. Multiple documents can own different contract areas;
identify their applicable sections instead of flattening them into a new copy.
Follow [reference handoffs and destinations](project-knowledge.md#reference-handoffs-and-destinations)
when passing these sections to planning, test authors and Improve; a guide path
alone does not identify the selected product requirements.
If no suitable home exists, follow that policy's small-repository fallback.
Recover only affected requirements and cross-cutting conditions, not an
unrelated whole-system specification.

## Reconcile current context with existing intent

The current user request and explicit later clarifications of that same request
win where they conflict with older product requirements. Record each actual user
instruction's source and decision basis in the active protocol's durable
notes/results before relying on it after context loss. An unverified host summary
is not a user instruction. Current agent assumptions, proposals, code, or research
findings do not acquire authority merely by being newer. Use the active protocol's
correction/revision route for changes affecting a frozen contract; separately
requested new work follows the [new-run policy](project-knowledge.md#new-work-versus-recovery).

For each affected requirement, record **preserve, add, modify, or retire**, its
source/section, and the current-request or accepted-decision basis. Keep compatible
old and new conditions together. Supersede only the conflicting clause; preserve
unmentioned requirements, bounds, exceptions, negative cases, and cross-cutting
rules. Silence in the new request is not retirement. An explicit replacement
needs no redundant approval. If wording or conflicting sources leave a material
policy choice unresolved, identify it and obtain the missing decision before
dependent work; do not guess, choose the newest file, or quietly weaken the rule.

Edit the authoritative home narrowly when the active step permits product edits,
preserving unrelated text, IDs, links, and concurrent changes. Until then retain
the proposed delta in the assigned spec/result. Record supersession rationale
next to the changed clause. Keep historical records and frozen run baselines
intact; use the active protocol's correction/revision route when they must change.

## State and data change assessment

For an affected change, inventory only the relevant carriers: files, runtime
memory, applied configuration, access assignments, domain records, and derived
data. Identify the actual target, entity, or user; say whether it is changed,
observed, or intentionally out of scope. A local-only interaction does not
acquire fictional persistence, database, or migration work merely to complete an
inventory.

For each consequential read or mutation, retain its owner, before/after
invariant, authorized actor and effect, partial-failure/recovery rule, and an
observable check. Reuse the existing requirement/case IDs and applicable
[behavior model and transition ledger](behavioral-requirements.md#states-and-transitions),
sequence, context, and evidence locators; do not add a schema, phase, or mandatory
ledger.

Treat transition correctness and safety separately from workload quality goals.
Authorization, invariants, conflicts, partial effects, and recovery describe the
required transition; scale, latency, throughput, capacity, and cost are
non-functional criteria. When relevant, distinguish shared or hot-record
contention from independent-user load rather than treating either as proof of
the other. For an applicable staged release, migration, or access activation,
choose only containment the actual platform supports and retain an observable
promotion/stop condition and the rollback or compensation limit.

Material identity, authority, recovery, workload, or release criteria that remain
unresolved block the affected contract. Do not invent persistence, a target,
platform capability, or numeric bounds to close the assessment.

## Define non-functional requirements

During discovery, screen the requested change and preserved contract for relevant
quality attributes. During research, resolve consequential unknowns using local
contracts, primary platform/version documentation, or bounded authorized probes.
External research is unnecessary when local evidence suffices. Platform limits
and measured baselines inform feasibility; they do not choose user policy or
silently relax an existing target. At spec, complete this assessment before
dependent planning, even when the original request only describes features.

Consider proportionately:

- Performance, latency/freshness, throughput, capacity, resource and cost limits.
- Reliability, availability, durability, recovery, and data integrity.
- Security, privacy, access control, retention, and applicable compliance constraints.
- Accessibility, usability, and relevant user/device conditions.
- Compatibility, supported runtimes/interfaces, interoperability, and portability.
- Operability, observability, support, deployment and rollback constraints.
- Maintainability, testability, and constraints on dependencies or future changes.

For applicable requirements, retain an existing ID/section (or a stable new
reference), source/decision basis, affected behavior/component, relevant operating
conditions or workload, required response, measurable bound or observable
pass/fail criterion, and a verification method/surface. Record priority/tradeoffs
when they affect the design. Separate accepted requirements from proposed targets,
measured baseline, and current verification status. Qualitative goals such as
"fast", "secure", or "accessible" need concrete criteria; do not invent an SLA,
load figure, accessibility level, retention period, or budget to fill a template.

Record relevant exclusions with reasons and material unresolved targets with
their missing evidence/decision. Missing data or test access is not N/A. Material
unknowns prevent declaring the affected spec ready; unrelated work may proceed
through the existing route. A small local tool does not automatically need a
service availability target, load-test system, or new dependency. A short paragraph
can suffice; no mandatory table, category quota, or exhaustive NFR catalog.

## Initial-plan reconciliation

At initial planning, map every applicable architecture constraint, new and
preserved requirement, non-functional criterion, and state/data mutation to an
owner and work item, its prerequisite or evidenced supplier, and its planned
test/check. Retain an applicable release/recovery condition, or a reasoned
`N/A` or unresolved disposition, for each mapping. Keep compact source, decision,
and test locators in existing plan/work-item context and `evidence_refs`; normal
standalone Improve reviews use those same materials.

For an additive change, compare the actual consumer surface before and after the
planned outcome against the original request and baseline. Retaining a helper,
data shape, or unit assertion alone does not establish compatibility; earlier
agent acceptance does not authorize superseding a preserved condition.

If research, implementation, integration, or release reveals a new effect, use
the existing correction/recovery route and reconcile affected pending consumers.
Do not silently revise accepted intent or create another ledger, phase, or review
campaign.

## Carry the reconciled contract forward

Definition is ready to begin when the original request, applicable source
sections, intended consumer and material unknowns have been located. Definition
is done for dependent work when affected intent is reconciled into independently
verifiable clauses with observable outcomes and the required verification surface.
Retain material unresolved criteria explicitly; completing their investigation
does not make the affected definition or dependent implementation ready.
Neither definition completion nor a proposed test proves the product works.

Split a bundled requirement where its clauses need different observations; keep
the existing requirement ID and useful subclause/case locators. For example,
"open the deployed board and verify capture and winner detection" cannot be
closed by observing the board alone plus local rules tests. Distinguish a
required surface from an implementation choice: a local check may support a
required deployed interaction without satisfying it. Do not invent browser,
branding or deployment requirements for a local library or an embedded feature.

Test planning adds each clause's case or other existing verification record,
expected observation, required surface/target, due phase, owner and prerequisites
to the existing [case record](testing-and-documentation.md#test-cases).
Equivalent clauses may share a check when it actually observes them all; a
justified N/A needs a requirement-based reason, not unavailable access. Keep
actual status/evidence separate from these planned fields. Use the
[stage readiness and completion map](testing-and-documentation.md#stage-readiness-and-completion)
to distinguish definition done, tests authored, tests passed and delivery verified.

Test strategy and global/step plans must map applicable new **and preserved**
quality criteria to checks, prerequisites, and work-item requirement/test
locators. Assigned Improve reviews challenge silent loss, unjustified changes,
unmeasurable criteria, and feasibility/verification gaps within their scope.
Acceptance and handoff distinguish planned checks from actual evidence; a unit
pass cannot prove an untested latency, accessibility, recovery, or runtime claim.
Keep accepted intent in the maintained repository home with pending verification
explicit, so the next run does not need transient notes to recover the contract.

Hypothetical example: an existing search spec requires p95 latency at most 300 ms
for its documented workload, keyboard access, and no raw-query logging. The user
explicitly changes the latency limit to 200 ms and adds filtering. Discovery
retains the three source sections; spec modifies only the latency clause, adds
filter behavior, and preserves keyboard/privacy conditions. Test strategy keeps
the workload-bound timing check, keyboard flow, and logging assertion. A request
merely to "make it faster" would leave the existing bound intact and any proposed
new target unresolved; a lower measurement alone would not rewrite the contract.

The [arc42 quality guidance](https://docs.arc42.org/section-10/) supports concrete,
measurable quality scenarios and referencing existing goals instead of duplicating
them. Adopt that proportional technique, not an additional framework or runtime.
