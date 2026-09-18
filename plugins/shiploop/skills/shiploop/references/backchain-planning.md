# Backchain planning in ShipLoop

## Navigator planning

In navigator v3 this is an incorporated reasoning guide, not a standalone
Backchain invocation or a compatibility result schema. Read the selected
product clauses using [reference handoffs and destinations](project-knowledge.md#reference-handoffs-and-destinations)
alongside the new request and current-run spec. Preserve unaffected conditions
and map each required outcome to its own expected observation/test locator.

At `spec`, check outcomes and missing prerequisites without authoring future
receipts. At `plan`, apply [the dependency audit](#dependency-audit) to order
producers before consumers. At `step-plan`, apply it to the scoped local
microplan and its suppliers. At `carry-forward` and `product-acceptance`, use it
only for affected pending/corrective work and newly exposed dependencies.
The same stage's assigned Improve reviews those mappings and gaps.

Retain the audit in ordinary plan notes, result `evidence_refs` and work-item
`context`. Use v3's current callback and allowed result fields; do not import
legacy result fields, frozen-plan certificates, a Backchain JSON schema, or
another counter/dispatcher. The sections below describe the shared five lenses
and retained compatibility bindings; legacy field names apply only to those
recorded modes. A source path, matched label, or completed supplier declaration
is not independent evidence that the needed state exists.

## Owner binding

This is the native ShipLoop adaptation of the inspected Backchain planning
method, not a call to its standalone skill, generator, elaborator, or harness.
Read only the sections selected by the current packet. Perform that one action
and submit its exact callback; a planning review never authorizes implementation,
deployment, a new credential, or a different writer.

**Retained managed/legacy only:** ShipLoop owns the Markdown DAG, accepted spec, step contracts, review findings,
checks, audit commits, two-trivial-pass gates, and pending-only replans. Keep its
existing result shape. Do not add Backchain's `goal_needs`, `parallel_groups`,
`match`, or `artifact` fields to it. Concrete carriers and review conclusions
belong in existing output descriptions, evidence references and Markdown bodies.
No second scheduler, per-row cursor, state file, or model dependency is needed.
**Navigator v3:** ShipLoop owns traversal; actual Improve owns its independent
review cycle. Use ordinary notes, `evidence_refs` and work-item `context` as
described in [Navigator planning](#navigator-planning), not the legacy fields.

## Outcomes

Before drafting work, read the original request and the approved spec (or the
current spec candidate while authoring it). Enumerate each independent required
outcome, including negative constraints and conditional obligations. Reconcile
with applicable [maintained product requirements](project-knowledge.md#maintained-product-requirements)
and retain their section/test locators in the existing planning evidence. Reconcile
against that source again during review: a plan cannot prove completeness by
checking only the requirements it chose to list. A missing required outcome is
material, even when every listed test passes.

Give every independently checkable outcome a distinct criterion/case and a
sufficient planned observation: input/fixture, expected state or side effects,
named artifact or behavior, target and relevant revision when known. In v3,
keep these criteria in the current spec/plan notes and carry their locators in
`evidence_refs` and work-item `context`; future test paths remain planned.
Do not invent future receipts or observed revisions.

**Retained managed/legacy only:** At spec stages, author acceptance cases in the
spec/lifecycle candidate; do not invent future step IDs or contracts. During sequence,
map those cases to the work that establishes them and the later checks that
inspect them, using the step contracts and system-test requirements being
authored there. Later step plans retain the accepted mappings.
"The suite passes" alone is not per-outcome evidence. Use the existing
spec/lifecycle acceptance, `contract.done`, `contract.tests`, case IDs and
system-test requirements appropriate to that stage; do not duplicate them in
a new goal catalog. Share test infrastructure when useful, but retain each
outcome's trace. A planned check is not a passing result.

Keep subjective requests such as readability visible as scoped work and review
criteria. Do not silently drop them, invent an objective test for taste, or turn
them into unsupported claims of verified quality. An unmet measurable condition
stays open. A complete blocker report does not complete the original outcome.

## Sequence

After identifying outcomes, assess relevant environment prerequisites once at
the overall-plan level: repository/branch state, existing users or data needing
migration, release gates, required documentation, and systems that must exist.
Only a requirement-triggered probe creates a need; an irrelevant category adds
nothing. Record a baseline fact only when the request or an actual inspection
establishes it (`initial_state` in retained managed/legacy plans; cited ordinary
notes in v3). A tool's presence, an unanswered question or an
assumption is not evidence of access, runtime readiness, or populated data.

Draft coherent postcondition steps from these outcomes. In retained
managed/legacy plans, `statement` and `produces` describe what will be true;
`prompt` holds the authorized work. In v3, put the scoped outcome, prerequisites
and source/test locators in each ordered work item's `title`/`context` and linked
plan notes; do not add the legacy fields to a navigator result.
Split independently schedulable work when prerequisites or deliverables diverge;
do not require a separate DAG node for every assertion or cosmetic improvement.
ShipLoop's per-step verification gates already provide local checks. Plan a
separate system/integration producer only when a check genuinely needs multiple
steps, another environment, or a later lifecycle boundary.

Apply the dependency audit below to every draft step and new or widened supplier.
Record the outcome/case mapping, evidence sources, missing producers and final
forward-order check in existing plan notes and evidence. Retained managed/legacy
results use `plan` and `dependency_review`; v3 uses `evidence_refs` and work-item
`context`. Ask a clarifying question
when its answer could change an edge, supplier, scope or unresolved obligation.
Answer from current evidence where possible. Asking or answering does not itself
complete the action; unresolved required authority stays blocked.

## Dependency audit

For each step or local microplan row, use all five lenses:

1. **CLAIM:** identify the precise postcondition. Distinguish a capability,
   a concrete record/instance, an authored artifact, applied/runtime state,
   and the receipt that verifies that state.
2. **NEEDS:** infer what must exist to implement and verify that claim, including
   conditions missing from draft inputs. A nonempty input list is not proof
   that all needs were found. Include relevant recovery and downstream effects.
3. **SUPPLY:** inspect candidate suppliers across the relevant graph, not just
   adjacent rows. Ask what executing each supplier as written would leave that
   establishes this exact need. Revisit an under-supplied producer and its
   prerequisites; do not stop at the first matching claim.
4. **PULL:** inspect the committed consumers of this output. Does it establish
   the precise state and carrier they need? Recheck the producer's own inputs
   if downstream demand exposes a gap. This is not permission to redesign
   consumers or change an approved contract inside the current step.
5. **RESOLVE:** reuse an evidenced supplier or exact established initial fact;
   clarify the true owner's under-described output; add necessary in-scope
   evidence-producing work; otherwise retain the need as unresolved. Clarifying
   an owner must not hide additional unrelated work in a god-step. Investigate
   uncertain impact; there is no "assumed true" disposition.

Name concrete carriers in existing output/evidence text when ambiguous: a
migration file is not the applied database state; a mock provider is not a
matching user record; a deployment is not a same-build smoke receipt. A path
through a related producer does not supply the missing layer. Retained
managed/legacy DAGs require exact need-to-producer strings; v3 retains the
mapping in ordinary plan/context prose. Matching strings are not proof of truth.
Metadata existence also does not prove intended-consumer access: an assignment
for another user does not supply the intended user's prerequisite, existing
effective access may suffice, and the deployment operator need not be that
consumer.

Share one supplier among actual consumers of the same state and layer. Do not
hoist it above its genuine prerequisites or introduce a global barrier for
unrelated branches. Draft order, related labels and correlation do not establish
dependencies. Keep immediate real prerequisites and explicit cycles/unresolved
needs; do not create edges solely to make a diagram look sequential.

Account for every examined need with one disposition, including unresolved ones.
Re-audit added/widened producers until no necessary dependency is left hidden,
then walk forward once from established facts through outputs to the required
observations. If investigation cannot close a gap, retain it rather than
declaring a fixed point. A later plan revision receives a new audit in the
existing improvement loop, not another recursive dispatcher.

For a real cutover/retirement/compatibility window, distinguish evidenced entry
conditions, the full continuously-valid interval, and permission for the gated
change. Bind the clock to the qualifying state—not nominal deployment time—and
record rollback/invalidation/restart conditions. When old/new formats coexist,
check whether invalid new-format input could improperly fall back to legacy
handling. These are conditional risk checks, not mandatory extra migration work.

## Step plans

In v3, read the current work item's `context`, linked requirement and plan sections,
and supplier/test evidence. Keep the local microplan, audit and unresolved gaps
in ordinary notes and the result's `evidence_refs`; Improve reads those same
locators through its existing contract. No `step-context` command, frozen-plan
certificate, or legacy dependency fields are implied.

**Retained managed/legacy only:** Use the existing execution microplan and its output/case rows. Read the selected
step, direct suppliers/consumers and accepted criteria through `step-context`;
read `backchain/plan.md` for an exact cited `initial_state` fact when needed.
Recheck relevant current environment/knowledge evidence: an initial declaration
or completed supplier receipt can be stale. Follow transitive references when
the five lenses reveal a concrete dependency, without repeating the entire
global environment survey for every row.

In those retained modes, record the audit and unresolved gaps in `body`, `coverage_review.dependencies`
and `context_evidence.dependencies`; preserve every enclosing `PARENT-*` finding
and existing contract/test mapping. Apply the full audit during initial and
Improve planning and after plan revisions. During implementation, follow the
certified plan and route new gaps through review/recovery, not unapproved edits
to its frozen inputs. Per-row checks do not create per-row callbacks.

## Replanning

Post-inner and outer review reconcile newly observed facts with the original
outcomes and every affected pending consumer. Reuse known suppliers rather
than duplicating work, but do not erase unfulfilled outcomes when documenting
an external blocker. A local constructible fixture may have an authorized
producer; an unavailable external approval cannot be manufactured by one.

In v3, use the current `carry-forward`/outer correction result for permitted
future or corrective work; do not edit accepted state or declare a missing
prerequisite satisfied. In retained managed/legacy modes, use carry-forward and
the existing pending-only revision path for compatible
future work. A prerequisite that blocks the active step needs resolution or a
pause now, not a journal entry that permits premature completion. Preserve
running/completed definitions, accepted receipts, exact goal and initial-state
baseline; incompatible changes need explicit replanning authority. No Backchain
rule permits silently repairing or deleting frozen edges outside that path.

## Provenance

Inspected Backchain checkout: `8278e27a84aa3a28c8986f798e14a3cd9436be67`.
Sources: `prompts/generator.v1.md`, `prompts/dependency-review.prompt.md`,
`prompts/elaborator.v1.md`, and their regression/experiment controls. This
reference selectively incorporates outcome-first drafting, per-outcome checks,
evidence-only closes, five lenses, carrier/layer distinctions, shared suppliers
and conditional transition clocks. The upstream card's older blanket orphan
rule is not imported: a required terminal deliverable is a legitimate outcome.

Experimental replacement prompts, alternate model backends, NBQ/EVSI machinery,
benchmark scoring and standalone JSON packaging are not adopted. ShipLoop's
current gates validate shapes, identities, links and receipts—not the semantic
truth or exhaustiveness of this reasoning. Review against independent request
criteria and meaningful checks remains necessary. This is an incorporated
adaptation, not execution or a byte-identical snapshot of the external skill.
