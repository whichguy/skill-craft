# Survey, research, behavior, and spec actions

These are separate durable actions because a small context should not need to
hold discovery, source research, and a final product contract simultaneously.
For each planning baseline:

1. Survey and write environment.md.
2. Draft paired research report/evidence candidates, then converge the research
   loop before behavior.
3. Draft behavior.md and repeatedly review/improve it until the behavior loop
   converges; finalize only with fresh checks and no open findings.
4. Draft spec-draft.md and lifecycle-draft.md, run the separate spec improvement
   loop, then atomically freeze spec.md plus lifecycle.md at spec-finalize.

All three loops require two consecutive trivial-only passes with reviewed Git
history, complete rubric dispositions, applied fixes, lint/tests and one verbose
audit-only commit per pass. Research planning checks use the exact acceptance
`research evidence`; follow the stage-selected
[Planning loops](../planning-loops.md) contract. One initial answer is not
enough.

Use the exact action/result commands from the action protocol. If a user
decision or external prerequisite blocks progress, pause with a specific reason
instead of creating an uncheckable spec or inventing facts.
Use the canonical [test cases](../testing-and-documentation.md#test-cases),
[surface selection](../testing-and-documentation.md#surface-selection), and
[documentation](../testing-and-documentation.md#documentation) guidance for
field-level detail; it adds host duties, not result fields or a second schema.
Follow [Behavioral requirements](../behavioral-requirements.md) at the section
selected by the packet: discovery/research first, behavior-model convergence,
then spec improvement. Product states and flows are not ShipLoop's own stages.
Use [requirements definition](../requirements-definition.md) within these actions:
survey locates existing specs and applicable quality conditions; research resolves
consequential gaps; spec reconciles old and new intent and defines verifiable
non-functional requirements. Preserve unaffected accepted conditions, let explicit
current requirements supersede conflicting clauses, and keep material unknowns
open before dependent work. Review these duties in the existing behavior/spec
loops; no extra action or result fields are introduced.
For a cold start, begin with the minimal typed machine record in
[the survey guide](../survey.md#minimal-valid-local-greenfield-machine-record)
and adapt it rather than guessing booleans, lists, or conditional fields.

## Survey

The survey result body becomes environment.md. Write a concise prose brief,
then exactly one H2 named machine and one fenced JSON object. The JSON is
structured content within authoritative Markdown. It is not a separate
environment.json authority.

Inventory, with evidence:

- repository kind and augmentation status; current product tree and relevant
  README/AGENTS guidance when it exists;
- concrete repository, product, writer, platform, and official-doc references
  with a one-line constraint-oriented why;
- available in-scope tools and MCPs, one read-capable mcp_considered token,
  non-secret handles/initiation facts, and unresolved questions;
- human-facing surfaces, their existing design/convention constraints, and
  whether an early design-producing step will be needed;
- behavior risks, relevant local/browser/service/API views, intended test or
  deployment environment, and readiness dependencies; select only relevant
  views, with a reason when a view is inapplicable;
- prompt-linked actors, stateful entities/owners, initial and terminal outcomes,
  existing sequence flows, persistence/communication boundaries, and unresolved
  behavior rules; keep this inventory in prose, not new machine fields;
- destination writer, runtime/library conventions, safe product paths,
  reserved paths, syntax-lint oracle, live destination identity oracle,
  routing/entrypoint probe, and — when a client will call a service — both
  sides' invocation protocol (see
  [Client–service invocation](../survey.md#clientservice-invocation)).

When a destination artifact has more than one potential writer, designate
exactly one use and record overlapping mutation tools in dont_use. They are
conflicts, not backups. If the designated writer cannot operate, pause and
obtain direction; do not silently switch writers.

For a writer-backed product, research and preserve the following before plan:

1. Which writer operation owns read, create, mutate, validation, and publish;
   do not use a familiar tool merely because it exists.
2. Required runtime/module/wrapper mechanics and existing local/destination
   patterns. Reuse before adding another stack.
3. Reserved versus product paths. Product changes never go into a writer-owned
   or overwrite-prone tree.
4. The user-facing route or entrypoint, reserved routes, a routing-level
   confirmation probe, and the distinction between a cheap bound-call probe
   and live acceptance. This is routing, not the client–service invocation
   protocol.
5. Writer lint/validation for file-local syntax and writer list/status or
   preflight for live identity. Destination rules outrank a generic formatter
   when they conflict.

Never record credentials, API tokens, signed-in account addresses, or volatile
delivery URLs. Record expected account role, safe status probes, and source
pointers instead.

## Research

Research the uncertainties discovered by survey before authoring behavior or the
spec. Prefer primary documentation, existing repository conventions, and the
named writer's own descriptions. `research` and `research-apply` submit `body`
plus the complete typed `research_state`; the script alone imports the paired
`research.md` and `research-evidence.md` candidates. Use the
[draft schema](../research-loop.md#draft) rather than inventing a report shape.
A client–service API, when in scope, is a research uncertainty: resolve both
systems' invocation protocol from primary docs before the spec, and do not
author communication yet.

The printed research stages are `research → research-review → research-plan →
research-apply → research-verify → research-commit`, then either another review
or `research-finalize`. Finalization needs two consecutive trivial-only passes,
no open findings or open/blocked questions, and fresh candidate-bound checks;
it then issues `behavior` rather than an execution step.

Trace high-risk requirements through the actual end-to-end sequences and state
changes, including failure/recovery and relevant repeated, concurrent or stale
events. Retain source/revision pointers and what each establishes or contradicts.
Resolve important gaps before behavior/spec; external docs or current
implementation cannot decide missing user policy. A research review uses the
complete [research rubric](../research-loop.md#review), retains stable question
and source IDs, and treats changed conclusions/status/scope as material. See
[Discovery and research](../behavioral-requirements.md#discovery-and-research).

Research does not authorize product changes, destination mutations, a mandatory
provider, or re-surveying an already frozen environment. User-authorized
temporary acquisition and isolated discovery experiments follow the shared
[recursive discovery controls](../research-loop.md#recursive-discovery-and-experiments);
only authorized disposable setup and test data may change. Do not record secrets.
Research finalization is an as-of evidence certificate, not proof that
sources remain live. A material discovery after freeze follows the explicit
[later-discovery route](../research-loop.md#later-discoveries): revisit research
before execution, handle it in the active Improve loop, map a future producer,
or pause for incompatible authority.

## Behavioral convergence

After `research-finalize`, at `behavior`, draft the prompt-linked R/F/T model with state transitions and
edge conditions, including case expectations and explicit uncertainty. On every
`behavior-review`, search again for missing behavior, invalid events, boundary
conditions and important interactions. Record stable findings and all rubric
dimensions; at `behavior-plan` address every open ID, then apply corrections,
run artifact-bound planning checks, and commit the learnings.

Any material discovery/application resets the trivial streak. Omitted findings
remain open. Only after two fully completed trivial-only passes and no open
findings may `behavior-finalize` run fresh checks and freeze the exact model.
The next action is `spec`, not an execution step. The
[modeling guide](../behavioral-requirements.md#behavior-model) defines breadth;
the [loop contract](../planning-loops.md#loop-contract) defines progression.

## Spec

At `spec`, submit a draft body with exactly one line each, outside fences and
blockquotes; the script stores it as spec-draft.md, not frozen spec.md:

~~~text
done_sentence: <one checkable delivery sentence>
checkable: true
~~~

The spec result also supplies lifecycle:

~~~json
{
  "acceptance": ["observable acceptance criterion"],
  "preparation": "none | dag | outer-before",
  "publish": "none | dag | outer-loop",
  "quality": true,
  "reason": "why work belongs in these locations"
}
~~~

The spec states scope, exclusions, user-facing outcome, acceptance, risks, and
the placement rationale. It does not invent a testing framework, external
permission, writer, endpoint, or source fact.

Make every acceptance criterion observable. Propose stable generic test cases
and documentation work in the spec result body, then let planning map cases to
exact outputs and executable selectors. Expected results are not actual
evidence; keep them distinct in the existing durable results.

Include the [Behavior model](../behavioral-requirements.md#behavior-model): stable
requirement IDs from the incoming prompt, sequence diagrams, state definitions
and invariants, transition ledgers with triggers/guards/effects, invalid-event
behavior, and relevant failure/recovery paths. Link them to expected-outcome
cases. Explicitly audit breadth and record justified exclusions or stateless
applicability; a happy-path diagram alone is insufficient. Material unknown
behavior blocks freeze, not merely an optional future test.

- preparation outer-before means a named readiness action must complete before
  the DAG walk; dag means preparation is an early DAG step; none means no such
  work is implied.
- publish dag means a declared sequence step; outer-loop means an authorized
  delivery action after coverage/quality; none means no publication action.
- quality true means outer quality needs its quality review plus integration
  checks; quality false still requires mandatory acceptance/integration checks.
  The chosen integration check is implementation policy, not a fake user quote.
- when an acceptance requires a real deployment, name the authorized
  deployment/readiness and dependent checks as DAG work before outer quality.
  An outer-loop publication can add final delivery smoke evidence only.
- a relevant required check without a ready environment, tool, or authorization
  is blocked, not `N/A` or passed. Only an irrelevant surface is inapplicable,
  with its reason recorded.

Completing the draft enters `spec-review`, not sequence. Improve clarity,
consistency, feasibility and the full behavior rubric through review/plan/apply/
verify/commit passes. Two trivial-only passes and no open findings permit the
fresh-check `spec-finalize` action. It alone promotes the draft/lifecycle to
the frozen contract. A newly discovered upstream behavioral gap uses
`revisit --to behavior` and re-convergence before another spec.

After spec-finalize, a later plan revision cannot silently
change its done sentence or baseline. Product README and optional AGENTS.md
work are product DAG artifacts when needed, not survey writes or session state.
Product documentation never contains ShipLoop session state; propose concise
public/non-obvious contracts and README changes here, then create them only in
the appropriate product worktree.
