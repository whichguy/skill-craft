# Backchain planning in ShipLoop

## Navigator planning

This guide is ShipLoop's planning checklist, not a standalone Backchain
invocation or a result schema. A Backchain call uses only the caller contract in
[Source-aware native caller](#source-aware-native-caller) below; there is no
embedded Backchain mode. Read the selected
product clauses using [reference handoffs and destinations](project-knowledge.md#reference-handoffs-and-destinations)
alongside the new request and current-run spec. Preserve unaffected conditions
and map each required outcome to its own expected observation/test locator.

At `spec`, check outcomes and missing prerequisites without authoring future
receipts. At `plan`, apply [the dependency audit](#dependency-audit) to order
producers before consumers. At `step-plan`, apply it to the scoped local
microplan and its suppliers. At `carry-forward` and `product-acceptance`, use it
only for affected pending/corrective work and newly exposed dependencies. In a
native call, a whole `plan`/`draft` or authorized `repair`/`revise`
operation owns its internal convergence; the ordinary Improve handoff remains a
separate broader review.

After the initial steps are created, both `plan` and `step-plan` must complete
their actual Improve handoff before consumers use the plan. Include any serial
or parallel execution graph in that review's candidate and evidence locators;
Backchain's result does not bypass this broader planning review. Follow the
[chain review requirement](parallel-chain.md#required-review-after-step-creation)
when a graph is first created or materially changed after the checkpoint.

Use [question-driven history investigation](project-knowledge.md#investigate-git-history-for-planning)
when a decision depends on prior rationale. Continue relevant history as needed,
check later supersession against current evidence, and turn useful findings into
specific plan constraints, prerequisites or checks rather than a citation inventory.

Retain the audit in ordinary plan notes, result `evidence_refs` and work-item
`context`. Use the current callback and allowed result fields; do not import
legacy result fields, frozen-plan certificates, a Backchain JSON schema, or
another counter/dispatcher. The sections below describe the shared five lenses.
A saved run from a retired protocol or mode is refused rather than read with
older field names. A source path, matched label, or completed supplier declaration
is not independent evidence that the needed state exists.

For a context-capable implementation chain, author coherent supporting planning
reference material before binding: key statements, decisions, constraints,
acceptance context, and exact locators from the accepted planning pass. It does
not replace the dispatch step's `task`/`ready`/`done` assignment or restate the
user prompt. Register every generated planning file in that producer's ordinary
`evidence_refs`.
Keep external local documents as explicit references and URLs as citations until
their material is supplied locally. This is planning context for the immutable
chain manifest, not a new Backchain review machine or a substitute for the
unchanged reviewed execution graph.

## Owner binding

This guide is not a call to Backchain's standalone skill, generator, elaborator,
or harness. Only a `source-aware-native` call binds the current host to the
observed standalone skill and caller resources below.
Read only the sections selected by the current packet. Perform that one action
and submit its exact callback; a planning review never authorizes implementation,
deployment, a new credential, or a different writer.

ShipLoop owns traversal; actual Improve owns its independent review cycle. Use
ordinary notes, `evidence_refs` and work-item `context` as described in
[Navigator planning](#navigator-planning). Do not add Backchain's `goal_needs`,
`parallel_groups`, `match`, or `artifact` fields to a navigator result. No second
scheduler, per-row cursor, state file, or model dependency is needed.

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
named artifact or behavior, target and relevant revision when known. Keep
these criteria in the current spec/plan notes and carry their locators in
`evidence_refs` and work-item `context`; future test paths remain planned.
Do not invent future receipts or observed revisions.

Give every completion criterion a confirmation: `<condition>. Confirm by:
<command, observation, or inspection>; pass when <expected result>.` It must pass
the two-people test: two people running it separately would be forced to agree.
State whether the condition must be exercised or whether inspection is
sufficient. Give content criteria (docs, changelogs, test coverage) a
command-checkable confirmation, such as a search for required terms, so they are
re-observed rather than recalled. Mark a criterion that no available check can
confirm as `Confirm by: unconfirmable here — <what would confirm it>` rather
than dropping it. When a check relies on an external oracle (golden, fixture, or
snapshot), confirm that the oracle agrees with the task. This applies to every
work step's `produces`/`contract.done`, not only sinks; a Backchain step
`confirm` entry records the same confirmation in structured form.

"The suite passes" alone is not per-outcome evidence. Use the existing
acceptance criteria, case IDs and system-test catalog appropriate to that stage;
do not duplicate them in a new goal catalog. Share test infrastructure when useful, but retain each
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
establishes it, with a cited run note. A tool's presence, an unanswered question or an
assumption is not evidence of access, runtime readiness, or populated data.

Draft coherent postcondition steps from these outcomes. Put the scoped outcome,
prerequisites and source/test locators in each ordered work item's
`title`/`context` and linked plan notes.
Split independently schedulable work when prerequisites or deliverables diverge;
do not require a separate work item for every assertion or cosmetic
improvement. Local checks come from each step's own completion criteria and
their `Confirm by:` confirmations: `implement` (or a chain worker) loops until
each is confirmed as far as the environment allows, and `verify` (or chain
parent verification) reruns or inspects them. A criterion without a
confirmation has no local check. Plan a
separate system/integration producer only when a check genuinely needs multiple
steps, another environment, or a later lifecycle boundary.

Apply the dependency audit below to every draft step and new or widened supplier.
Record the outcome/case mapping, evidence sources, missing producers and final
forward-order check in existing plan notes, `evidence_refs` and work-item
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
through a related producer does not supply the missing layer. Retain the
need-to-producer mapping in ordinary plan/context prose; matching strings are
not proof of truth.
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

Read the current work item's `context`, linked requirement and plan sections,
and supplier/test evidence. Keep the local microplan, audit and unresolved gaps
in ordinary notes and the result's `evidence_refs`; Improve reads those same
locators through its existing contract. Recheck relevant current environment
evidence: an initial declaration or completed supplier result can be stale.
Follow transitive references when the five lenses reveal a concrete dependency,
without repeating the entire global environment survey for every row. During
implementation, follow the accepted plan and route new gaps through the current
stage's result, not unapproved edits to its inputs. Per-row checks do not create
per-row callbacks.

## Replanning

`carry-forward` and the outer stages reconcile newly observed facts with the original
outcomes and every affected pending consumer. Reuse known suppliers rather
than duplicating work, but do not erase unfulfilled outcomes when documenting
an external blocker. A local constructible fixture may have an authorized
producer; an unavailable external approval cannot be manufactured by one.

Use the current `carry-forward` or outer `replan` result for permitted future or
corrective work; do not edit accepted state or declare a missing prerequisite
satisfied. A prerequisite that blocks the active step needs resolution or a
pause now, not a journal entry that permits premature completion. Preserve
running/completed definitions, accepted receipts, exact goal and initial-state
baseline; incompatible changes need explicit replanning authority. No Backchain
rule permits silently repairing or deleting accepted edges outside that path.

## Limits

ShipLoop's gates validate shapes, identities, links and receipts—not the
semantic truth or exhaustiveness of this reasoning. Review against independent
request criteria and meaningful checks remains necessary.

## Source-aware native caller

`source-aware-native` is the only Backchain route. A planning host may call it,
recording the selection in ordinary run notes, when the host has observed the
selected Backchain `SKILL.md`, its `backchain-caller/v1` action/stage resource,
`references/convergence.md`, and `prompts/convergence-review.prompt.md`, plus a selected
physical Until Loop root with its `SKILL.md`, `references/runtime-ephemeral.md`, and
`scripts/until_loop_ephemeral.py` capability. Read the Backchain convergence resources:
they must support the direct natural-language handoff under
`Backchain standalone Until Loop binding: <binding-id>` for a plan-only child where the
actual loaded Until Loop card starts its adapter, is the sole CLI caller, and returns the
exact terminal packet. This is host-mediated prompt guidance, not navigator state, a
callback, a controller, or a scheduler. Caller/v1 alone does not establish this
capability; an observed old custom Backchain loop is incompatible even when an Until
Loop package is installed.

The durable selection record names mode, interface, action/stage, action ID and
owner; selected Backchain and Until Loop card/resource locators and digests, including
the Backchain convergence reference and review prompt; original request; candidate ID,
locator, base, resolved locator and input/output digests;
each source's locator, base, resolved locator, authority, provenance, currentness,
revision, digest and supersession; protected bounds; and receipt locators. Backchain
passes dependency-specific review/fix/check work, plan candidate files, source/lens
context, and protected bounds to its child under
`Backchain standalone Until Loop binding: <binding-id>`. ShipLoop preserves the full
opaque actual Until Loop terminal evidence and Backchain domain evidence in ordinary
run notes, `evidence_refs`, and compact work-item `context`: binding_id; owner; candidate
input/output digests; resolved resources; opaque `terminal_receipt`; domain_evidence;
planning_gaps; execution_blockers; and next_action. It does not interpret runtime
progress, own a counter, schedule a retry, or make completion from an intermediate
plan. Cold recovery rereads these records; it never infers either selected root from
CWD or a neighboring package.

The Until Loop child is plan-only: it may change the candidate plan and permitted planning
companions, but may not commit, push, merge, execute the project, or broaden scope.

The plan-stage owner may request one whole `plan`/`draft` operation. A material
audit finding may be routed to the authorized current stage owner for one bounded
whole `repair`/`revise` operation. Each whole operation lets Backchain invoke the
selected actual Until Loop for its dependency-specific review/fix/check cycle. Until
Loop alone owns callback progress, its `required_trivial_reviews: 2` gate for two
consecutive distinct complete trivial/no-change dependency reviews, recovery, and terminal
state. Backchain returns only after the child reports `complete`
and the exact terminal evidence is saved; a blocked, stopped, unresolved, or
incompatible child leaves the parent action incomplete and must not be submitted as
completed. Only that exact `complete` receipt plus final candidate identity and domain
evidence permits planning convergence. `review`/`audit` remains a read-only one-pass diagnostic: it neither
mutates a candidate nor starts an Until Loop child. Improve's ordinary ShipLoop review
remains independent. It must not launch a nested whole Backchain→Until Loop subcall;
use a one-pass Backchain primitive for any relevant diagnostic.


An unavailable, stale, ambiguous, superseded-without-inspection, or incompatible
material source/card/contract/resource is incomplete or blocked; there is no
fallback route. Host reasoning evaluates capability and packet compatibility:
the direct-handoff compatibility judgment remains host-judged and the script does not
claim to enforce those semantic facts. A native output with invalid identity is
unchanged/rejected/unresolved; no digest is invented. A revised plan starts with
structural status unknown and empty `parallel_groups` until its exact output digest and
structural check are independently recorded.

## Experiment-informed planning

In [experiment-informed planning](planning-experiments.md), the provisional delivery plan exposes
assumptions to its existing Plan Improve owner. That child may run bounded
experiments and revise the candidate or return an upstream-reconciliation need.
Native Backchain remains plan-only; do not launch another Backchain/Until loop
inside Plan Improve. Bind the accepted graph to the dispatcher only after the
renewed planning suffix and preparation complete.
