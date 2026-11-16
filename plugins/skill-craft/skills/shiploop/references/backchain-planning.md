# Backchain planning in ShipLoop

## Navigator planning

This guide is ShipLoop's planning checklist, not a call to another skill or a
result schema. (The standalone Backchain skill was retired on 2026-11-16; its
backward-planning method is this guide's.) Read the selected
product clauses using [reference handoffs and destinations](project-knowledge.md#reference-handoffs-and-destinations)
alongside the new request and current-run spec. Preserve unaffected conditions
and map each required outcome to its own expected observation/test locator.

At `spec`, check outcomes and missing prerequisites without authoring future
receipts. At `plan`, apply [the dependency audit](#dependency-audit) to order
producers before consumers. At `step-plan`, apply it to the scoped local
microplan and its suppliers. At `carry-forward` and `product-acceptance`, use it
only for affected pending/corrective work and newly exposed dependencies. The
ordinary Improve handoff, where the stage has one, is the separate broader review.

After the initial steps are created, both `plan` and `step-plan` must complete
their actual Improve handoff before consumers use the plan, when the run has one: in a
`planning_review: none` run neither stage has an Improve stage, so the graph's only checks before
consumers use it are ShipLoop's at `complete` and the structural `backchain-check`. Include any
execution graph in that review's candidate and evidence locators.

Use [question-driven history investigation](project-knowledge.md#investigate-git-history-for-planning)
when a decision depends on prior rationale. Continue relevant history as needed,
check later supersession against current evidence, and turn useful findings into
specific plan constraints, prerequisites or checks rather than a citation inventory.

Retain the audit in ordinary plan notes, result `evidence_refs` and work-item
`context`. Use the current callback and allowed result fields; do not import
legacy result fields, frozen-plan certificates, the plan graph format, or
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
chain manifest, not a new review machine or a substitute for the
unchanged reviewed execution graph.

## Owner binding

This guide is ShipLoop's own and calls no other skill. Read only the sections
selected by the current packet. Perform that one action and submit its exact
callback; a planning review never authorizes implementation, deployment, a new
credential, or a different writer.

ShipLoop owns traversal; actual Improve owns its independent review cycle. Use
ordinary notes, `evidence_refs` and work-item `context` as described in
[Navigator planning](#navigator-planning). Do not add the plan graph format's
`goal_needs`, `parallel_groups`, `match`, or `artifact` fields to a navigator
result. No second scheduler, per-row cursor, state file, or model dependency is
needed.

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
work step's `produces`/`contract.done`, not only sinks; a plan graph step's
`confirm` entry records the same confirmation in structured form.

"The suite passes" alone is not per-outcome evidence. Use the existing
acceptance lines, case IDs and system-test catalog appropriate to that stage;
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
each is confirmed as far as the environment allows, and the step's `document`
stage and its Improve review (or chain parent verification) rerun or inspect
them. A criterion without a
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

Use the current `carry-forward` or outer `add-work` result for permitted future or
corrective work; do not edit accepted state or declare a missing prerequisite
satisfied. A prerequisite that blocks the active step needs resolution or a
pause now, not a journal entry that permits premature completion. Preserve
running/completed definitions, accepted receipts, exact goal and initial-state
baseline; incompatible changes need explicit replanning authority. No planning
rule permits silently repairing or deleting accepted edges outside that path.

## Limits

ShipLoop's gates validate shapes, identities, links and receipts—not the
semantic truth or exhaustiveness of this reasoning. Review against independent
request criteria and meaningful checks remains necessary.

## Plan graph format

The record-only `backchain-check` reads a candidate graph in this shape, as a JSON
file. Write one only when the work needs a graph, never only to run the check; it
never replaces the navigator result's own fields.

**Top-level keys.** Required: `goal`, `initial_state`, `steps`, `parallel_groups`,
`unresolved`. Optional: `goal_needs`.

- `goal`: one sentence describing the end state, not a task title or a verb-first
  to-do ("User authentication works end-to-end", not "Add auth").
- `initial_state`: concrete facts already true and evidenced before any step runs
  (supplied by the request or found by inspection while planning), never guesses.
- `steps`: at least one step; every step's `produces` has at least one non-empty
  string.
- `parallel_groups`: the steps of each dependency depth, derived from the inputs.
  The check packages a copy, so `[]` is fine.
- `unresolved`: the open needs the plan cannot close (shape below); `[]` when none
  remain.
- `goal_needs`: the request's terminal needs. Each must appear in some step's
  `produces` or in `initial_state` for the graph to be complete. Never invent an
  entry; `[]` means no terminal constraint.

**Steps.** Every step has five required fields, `id`, `statement`, `produces`,
`inputs` and `origin` (`seed` or `discovered`), plus an optional `confirm`, and no
other field. `statement` and every `produces` entry are postconditions (a state or
conclusion), never actions or commands. A new graph's steps are `S1`, `S2`, … with
`origin: "seed"`; steps added to an inherited graph are `D1`, `D2`, … with
`origin: "discovered"`. A `confirm` entry is `{"produces": "<exact text of one of
this step's produces>", "by": "<command, observation or inspection>; pass when
<expected result>", "level": "execute" | "inspect" | "unconfirmable"}`, at most one
per produce: the [Outcomes](#outcomes) `Confirm by` clause in structured form.

**Inputs and open needs.** Each input is `{"need": ..., "from": ...}`: `from: null`
when the need is already true (it must then also appear, word for word, in
`initial_state`), or the id of the step whose `produces` supplies it; never a
placeholder such as `"initial"`. Optional: `artifact` (the concrete carrier) and
`match` (only for a wording difference that is not obvious). Each `unresolved`
entry is `{"step": ..., "need": ..., "reason": "residual-risk"}`, or `"reason":
"circular"` with a `cycle` array of at least two step ids naming the refused loop
(that edge stays out of `inputs`). Never drop a genuine need silently.

**Structural invariants.** A valid graph satisfies all seven:
1. only the fields above, and each `confirm` names the exact text of one of its
   step's produces, at most once, with a non-blank `by` and a valid `level`;
2. no cycle among committed edges;
3. every non-null `from` names an existing step;
4. every `discovered` step supplies another step's input or a `goal_needs` entry;
5. no need is both an input and an unresolved entry of the same step;
6. every step id in `unresolved` and `cycle` exists, and a non-empty
   `parallel_groups` matches the dependency depths;
7. every `from: null` need appears in `initial_state` (exact match after trimming
   and collapsing whitespace).

A valid graph with entries in `unresolved` is valid but incomplete; with
`goal_needs`, every entry must also be covered for the graph to be complete.

## Experiment-informed planning

In [experiment-informed planning](planning-experiments.md), the provisional delivery plan exposes
assumptions to its existing Plan Improve owner (a `planning_review: none` run has none). That child may run bounded
experiments and revise the candidate or return an upstream-reconciliation need.
Do not launch a separate planning loop inside Plan Improve. Bind the accepted graph to the dispatcher only after the
renewed planning suffix and preparation complete.
