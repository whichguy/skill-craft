"""Prompt catalog for ShipLoop's lightweight navigator execution mode.

The navigator owns no execution, evidence interpretation, or loop counter.  It
only exposes stable, host-neutral instructions for the runtime's current node.
"""

PRELUDE = (
    "intake",
    "discovery",
    "research",
    "research-improve",
    "spec",
    "spec-improve",
    "test-strategy",
    "plan",
    "plan-improve",
)

INNER = (
    "step-plan",
    "step-plan-improve",
    "implement",
    "test-refine",
    "test-author",
    "document",
    "skill-validate",
    "verify",
    "product-improve",
    "integrate",
    "carry-forward",
)

OUTER = (
    "system-test",
    "outer-improve",
    "release-plan",
    "release",
    "release-verify",
    "handoff",
)

IMPROVE_STAGES = {
    "discovery",
    "research-improve",
    "spec-improve",
    "test-strategy",
    "plan-improve",
    "step-plan-improve",
    "product-improve",
    "outer-improve",
    "release-plan",
}

# These stages can cross an environment boundary before, during, or after the
# ordinary research pass.  The navigator only renders the pointer; the shared
# policy and its generic-result adaptation remain in the linked references.
ENVIRONMENT_DISCOVERY_REQUIREMENTS = {
    "discovery": "Mandatory for this stage's relevant environment reads.",
    "research": (
        "Mandatory while resolving relevant environment unknowns in this stage."
    ),
    "research-improve": (
        "Mandatory while rechecking relevant environment conclusions in this campaign."
    ),
    "product-improve": (
        "Mandatory if this campaign encounters a consequential new environment unknown."
    ),
    "outer-improve": (
        "Mandatory if this campaign encounters a consequential new environment unknown."
    ),
}

COMMON = """\
The script owns only this cursor, action identity, durable state, and graph
routing. You own repository review, judgment, planning, edits, test design,
commands, evidence, and whether work has converged. Follow the user’s scope
and permissions; do not infer permission to release, push, install, delete, or
change unrelated work.

For work that may affect a user, retain the original requested outcome and
identify the actual or likely consumer and entry point. A repository or Git
history is a source of context, not automatically the consumer boundary.
Keep separate: whether a consumer update or check is necessary, whether its
exact target and operation are authorized, and evidence of operation/effect,
artifact identity, and consumer behavior. An applicable user-approved
repository policy can grant a scoped operation; an agent-authored plan, a
visible connection, or a prior operation cannot. Absence of an explicit publish
wording does not silently make work source-only. A necessary operation or check
without authority or current evidence is unresolved or blocked, not
non-applicable; do not perform it merely to resolve the uncertainty.

Use this packet's Current node and Action for your assignment and callback;
the Last accepted transition describes earlier work, not the current action.

Inspect current repository and run context before relying on prior notes. Keep
the candidate and adjacent context explicitly scoped, preserve unrelated user
work, and treat a missing prerequisite, access, decision, or trustworthy check
as incomplete rather than success. Choose proportionate ways to carry out this
prompt; no exact prose layout, check-manifest schema, byte comparison, or
generic evidence string proves quality.

Return a concise result with `outcome` (`done`, `repeat`, or `blocked`) and a
`summary`; add `evidence_refs` when they help locate real evidence. Do not
supply a next stage. `repeat` asks for a new action at this same node; `blocked`
keeps this work incomplete until the host resumes it. Only `plan` may include
ordered `work_items` for all approved work. `plan-improve` may update that
ordered queue before execution begins. Only `carry-forward` may include ordered
future-only `work_items`.
"""

IMPROVE = """\
This one action owns the entire reusable Improve review cycle. Read
`references/improve-review-policy.md` and perform its ordered review, plan,
apply, checks, record, and assessment work internally. Do not start standalone
Improve or until-loop, create child phases or ambient state, or add another
loop wrapper around this action.

For every distinct cycle, inspect the seven latest full Git commit messages;
when fewer exist inspect all available messages, and when none exist disclose
that no history was available. Review the in-scope current candidate and
affected consumers against the stated baseline, then plan only authorized
worthwhile changes and establish their expected behavior and checks before
applying them. Classify materiality
semantically: a one-line defect can be material, and cosmetic changes are not
automatically material. Investigate uncertainty. Any material finding or edit
resets the clean-review condition.

Where engineering choices are in scope, assess the applicable implementation
conventions and justified departures. Review only the relevant subset; investigate
named changed assumptions. Challenge stale or unsafe precedents; recorded practice
is evidence to evaluate, not automatic authority.

In every cycle, compare the plan to the original request, not only the generated
specification: if all planned steps succeed, will the intended user receive the
requested behavior at the intended entry point? Identify a missing update
operation, authorization decision, consumer check, or consequential second-
order effect. Preserve source/effect, artifact identity, and consumer-behavior
observations separately. This is a review question inside this existing
campaign; do not create another stage, wrapper, counter, or standalone loop.

After every affected plan, code, test, documentation, or skill change, refresh
the checks it can affect. Keep a durable human-readable record under the run
directory, for example `notes/<actionID>.md`, with scope, candidate/source/
baseline identity as a host-recorded descriptor, findings and classification,
plan or no-change reason, checks, evidence, learnings, review limitation, and
clean-review streak before and after. That descriptor is not a scripted hash
gate. Use a fresh independent reviewer when available; otherwise record the
self-review limitation. Commit authorized changes only after their checks;
never manufacture an empty commit, and honor an explicit user request not to
commit.

Schedule available independent review against the final candidate before
declaring convergence. Record what it actually reviewed; later material edits
invalidate affected review evidence and require reconsideration of that scope,
including another independent look when available. Reviewer agreement alone
does not establish correct behavior.

For persistent failures or recurring findings, state a testable diagnosis and
the smallest observation that distinguishes plausible causes. Use the result
to choose the next action; repeated failure without new evidence calls for a
different experiment or a revised plan. Keep this diagnosis in ordinary notes,
without inventing another loop, counter, or result field.

Repeat complete, distinct cycles internally until you assess two consecutive
trivial-only completed reviews with current checks and no unresolved material
findings. The action boundary is the whole cycle campaign: submit one `done`
only after that assessment. A blocker, stop, stale check, missing evidence, or
unfinished convergence prevents `done`. If you cannot continue, report `blocked`.
Ordinary review iterations continue inside this action. If an attempt must be
restarted, the generic `repeat` outcome requests a fresh attempt at this node;
it is not a completed review, a clean pass, or a successful completion.
"""


IMPLEMENTATION_QUALITY = """\
Implementation quality: error checking + token-efficient code documentation
- Project conventions: read the retained implementation conventions and source
  examples relevant to this assignment. Check product purpose, runtime/dependency
  versions, interface/tool contracts and selected skills. Prefer applicable,
  supported patterns; do not copy stale or unsafe code. Record justified departures
  and required checks, and refresh affected decisions when assumptions change.
  Tool or skill availability does not require adding a product dependency.
- Error checking: validate changed input/state boundaries; handle relevant
  dependency failures and cleanup/recovery proportionately. Preserve actionable
  errors; do not silently turn failures into success or add speculative defenses.
- Debug diagnostics: reuse existing logger/debug controls for opt-in debug
  diagnostics at selected major actions. Emit bounded, redacted before/after
  summaries and failure outcomes, correlated by operation/request ID as relevant.
  Choose useful IDs, counts, decisions, state changes and timings; avoid whole-state
  dumps and expensive diagnostic construction when debug is off.
- Exception context: snapshot safe relevant values before cleanup or mutation,
  including expected versus observed conditions and the operation/phase. Use
  stable copies, not mutable references. Retain essential error context even when
  debug is off. Expose only safe, concise audience-appropriate messages; keep
  bounded structured context internal. Redact sensitive fields and emitted
  exception details, including causes and stacks. Preserve the original type,
  cause and traceback for propagation;
  diagnostics must not mask the original error. Record at the owning handling
  boundary without duplicate stacks on rethrow; expected control-flow exceptions
  are not automatically incidents.
- Token-efficient code documentation: make changed public interfaces and
  non-obvious logic understandable to a fresh LLM or human with concise
  colocated contracts: purpose, preconditions, outputs/errors, material side
  effects/invariants, and rationale. Prefer clear names and one authoritative
  explanation over narration, repeated signatures, or boilerplate. Preserve
  material caveats and required API/user documentation.
Apply these criteria to this stage's assignment. Reuse adequate existing
checks/docs; when a criterion has no relevant change, explain why in ordinary
notes rather than adding unnecessary code or documentation.
"""


def _prompt(
    duty: str, *, improve: bool = False, implementation_quality: bool = False
) -> str:
    """Assemble a concrete prompt while keeping shared obligations in one place."""
    parts = [COMMON, duty]
    if implementation_quality:
        parts.append(IMPLEMENTATION_QUALITY)
    if improve:
        parts.append(IMPROVE)
    return "\n\n".join(parts)


PROMPTS = {
    "intake": _prompt(
        """\
Establish the requested outcome, repository and run boundaries, explicit user
constraints, authority limits, consumers and entry points, known risks, and
unanswered questions. For a likely existing consumer, distinguish whether a
usable update is necessary from whether a specific remote operation is
authorized. Distinguish facts from assumptions. Identify what discovery must
establish before research, specification, planning, pre/post-update tests, or
release work can be trusted; do not implement or silently expand scope yet."""
    ),
    "discovery": _prompt(
        """\
Inspect the current repository, Git/worktree state, instructions, relevant
code, tests, documentation, environment, consumers, and useful local skills.
Identify implementation conventions relevant to this product's purpose:
supported runtime/dependency versions, canonical code/test examples, relevant
MCP/API contracts and existing reusable skills. Distinguish binding requirements,
observed practices and proposals; resolve consequential gaps through research.
Ground binding constraints in current user/repository requirements and verified
runtime/interface contracts; tool or skill descriptions do not grant authority.
Record concise findings with source/version references in an appropriate existing
project document or durable discovery notes; avoid a generic coding manual.
Record current facts and gaps that shape the work. Review the candidate before
planning; neither old commits nor a visible file proves current behavior,
authorization, or a passing check.
For an existing system, locate the actual consumer/entry point and any
user-approved delivery policy or activation mechanism. A hosted consumer makes
delivery a material question, not automatic authority or an automatic
source-only conclusion. When its answer changes scope or authority, ask or
durably retain one high-value unresolved question while continuing independent
authorized work.
First produce the discovery record, then run the complete Improve campaign
below on that record before returning done. Challenge existing-versus-new
system assumptions, affected actors and flows, access claims, missing evidence,
and consequential second-order effects. Improve the investigation and its
durable findings, not product code. An unanswered downstream question may be
recorded with its owner and gating stage; an unresolved prerequisite for this
discovery remains incomplete. Reuse the shared investigation allowance across
reviews; exhaustion is not convergence.""",
        improve=True,
    ),
    "research": _prompt(
        """\
Resolve the material unknowns using appropriate primary repository or external
evidence. Relate each conclusion to its source, uncertainty, affected
requirement, consumer, prerequisite, and likely verification need. Keep
research bounded to the request and leave unsupported questions open rather
than inventing answers or implementation."""
    ),
    "research-improve": _prompt(
        """\
Improve the research record and its conclusions as the current candidate.
Check evidence quality, scope, assumptions, source relevance, and downstream
impact before accepting a change. Refresh any affected research-based plan,
expected outcome, or system-test need.""",
        improve=True,
    ),
    "spec": _prompt(
        """\
Define the approved behavior, boundaries, acceptance criteria, nonfunctional
expectations, failure cases, and consumer-facing outcomes. State independent
expected outcomes early, including local tests and plausible integration,
system-test, or outer-loop obligations. Mark unresolved prerequisites or user
decisions instead of burying them in implementation detail. For any consumer
update, record whether it is required, source-only, or unresolved and keep that
necessity separate from authority for a target operation. Preserve applicable
binding implementation constraints; observed practices or proposals do not become
requirements merely because they appear in discovery notes."""
    ),
    "spec-improve": _prompt(
        """\
Improve the specification as the current candidate. Review behavior,
acceptance criteria, failure paths, consumer impact, and early test/system-test
expectations. Refresh every planned outcome or check affected by a changed
requirement.""",
        improve=True,
    ),
    "test-strategy": _prompt(
        """\
Turn the specification into independent, observable expected outcomes before
coding. Cover normal, failure, boundary, and relevant consumer behavior;
separate executable local tests from integration, runtime, and system tests.
Name necessary fixtures, data, environments, authorization, and evidence
limits. Place pre-update candidate checks separately from post-update consumer
checks, and distinguish source/effect, artifact identity, and behavior
observations. A planned test is not a passed test.
First produce this test strategy, then run the complete Improve campaign below
on its cases, independent expected outcomes, coverage gaps, and prerequisite
placement before returning done. Check the plan's adequacy using relevant
source/specification evidence; do not claim unimplemented tests passed or
require future implementation merely to review the strategy.""",
        improve=True,
    ),
    "plan": _prompt(
        """\
Create a dependency-aware implementation plan by reverse-walking each required
outcome: required behavior, prerequisites, suppliers, affected consumers, and
verification. Use Backchain-style reasoning to expose missing inputs or cycles.
Select the applicable implementation conventions from discovery and current
sources. Retain their scope, rationale, source examples and useful checks in one
appropriate project document or durable plan note. Include its locator in plan
`evidence_refs` and each applicable work item's `context`; keep context to a short
locator and decision summary, not copied convention text. Preserve those references
when revising the queue. Reuse adequate documents rather than copying them.
Order approved work by actual dependencies and retain early test and outer/
system-test obligations. Carry the implementation quality criteria below into
each applicable work item's acceptance expectations. For a required consumer outcome, plan the exact update
operation, target, authority source, and pre/post-update checks; leave an
unknown authority unresolved rather than deleting the outcome. If useful,
return ordered `work_items` covering the whole approved plan; do not turn them
into a second scheduler.""",
        implementation_quality=True,
    ),
    "plan-improve": _prompt(
        """\
Improve the complete delivery plan. Recheck prerequisites, dependency order,
scope, expected outcomes, test strategy, system-test obligations, consumers,
release assumptions, required consumer updates, and their authority. Refresh
affected planned checks before deciding the plan is ready for local step
planning. If the approved work queue changes before execution, return ordered
`work_items` for the whole updated plan. Preserve applicable convention locators
and decision summaries in revised work-item context, or record why they changed.""",
        improve=True,
        implementation_quality=True,
    ),
    "step-plan": _prompt(
        """\
Plan the current authorized work item in enough detail to implement safely:
the bounded candidate, prerequisites, affected code and consumers, intended
behavior, independent expected outcomes, test cases, fixtures, documentation,
skill/reuse questions, and checks. Resolve or block missing inputs before code;
this is planning, not permission to skip directly to unverified edits.
Read the implementation conventions referenced by this work item's context;
if the locator is absent or inaccessible, recover it from accepted discovery/plan
records and canonical repository sources. Never infer binding rules from a summary.
Apply the relevant subset and revalidate changed assumptions rather than repeat
full discovery. Record any justified departure, its rationale and verification
needs. Resolve material conflicts with requirements or supported interfaces
through targeted discovery before dependent edits; block only unresolved
prerequisites. A historical pattern is not a mandate to copy a defect.
Name the relevant failure boundaries, expected error handling and negative
checks, and locations needing concise in-code contracts before implementation.
Select major actions needing diagnostics, safe snapshot fields, existing debug
controls, and expected before/after/failure observations. Reuse adequate coverage.
Where acceptance could have different meanings, state a positive example and
a nearby negative example. Select operational and security checks for changed
boundaries: authorization, data integrity, dependency provenance/compatibility,
migration recovery, or useful diagnostics as relevant. Keep the selection
proportionate; record a missing required prerequisite as incomplete.
Distinguish prerequisites for the current work item from downstream integration,
system-test, consumer-update, or release conditions. Record downstream-only
conditions, their owner and earliest gating stage without blocking independently
authorized work. Preserve a new delivery implication for carry-forward instead
of assuming a later stage will rediscover it.
If delegating, define bounded task/file ownership, shared interface contracts,
inputs, expected outputs and evidence, and the owner responsible for checking
the assembled result. Delegation remains within the current action.""",
        implementation_quality=True,
    ),
    "step-plan-improve": _prompt(
        """\
Improve the local step plan as the current candidate. Recheck the bounded
scope, prerequisite evidence, Backchain dependencies, expected outcomes,
tests, documentation, reuse/skill choice, and any system-test impact. Refresh
the affected plan and its planned checks before implementation. Challenge
ambiguous acceptance examples, selected risk checks, and any delegation
boundaries rather than assuming the draft plan resolved them. Check that planned
error coverage, diagnostic context and code contracts satisfy the quality criteria
below without speculative defenses or boilerplate.""",
        improve=True,
        implementation_quality=True,
    ),
    "implement": _prompt(
        """\
Implement the authorized bounded plan. Inspect the actual code as it changes,
preserve unrelated work, and record material discoveries. Do not treat a code
edit as verification: send the learned implementation context forward so cases
can be refined and executable tests authored before the final checks.
Implement the planned error behavior, diagnostics and concise colocated contracts
with the code; carry all implementation quality criteria into delegated prompts.
When delegating, give each worker bounded ownership, shared contracts, inputs,
and expected outputs/checks. Reconcile overlapping or conflicting work and
inspect actual changes and evidence; the owning agent remains responsible for
the assembled result and the one completion callback.""",
        implementation_quality=True,
    ),
    "test-refine": _prompt(
        """\
Refine the earlier test cases from the code that now exists. Correct stale
assumptions, retain meaningful coverage, and state current expected outcomes,
failure behavior, fixtures, and selectors. Do not weaken an oracle merely to
obtain a green result and do not claim a planned or edited test has run.
Challenge expected results independently against the specification, including
positive and nearby negative boundaries where useful. Check that mocks or
implementation-derived expectations do not hide the behavior being tested;
resolve a genuine specification ambiguity before treating disagreement as a
code defect. Include the planned error paths and observable diagnostics in the
negative cases, checking their expected behavior independently. Where diagnostics
change, check debug on/off behavior, context retained across cleanup, redaction,
causal preservation, and logging/serialization failures that must not mask the
original error. Keep checks proportionate to the changed boundaries.""",
        implementation_quality=True,
    ),
    "test-author": _prompt(
        """\
Author or refine executable tests and fixtures from the current case set.
Map important behavior and failure cases to meaningful checks, preserving
adequate existing tests where they already cover the outcome. Record any
blocked test need honestly; final linters and tests still run at verify.
For an important regression where practical, show that its check rejects the
known-bad baseline or an isolated deliberately broken variant and passes the
candidate. Reuse an adequate existing reproduction; avoid extra mutation
testing when it adds no meaningful coverage. Keep experiments isolated from
the deliverable and preserve caller/user data.""",
        implementation_quality=True,
    ),
    "document": _prompt(
        """\
Update necessary code, API, user, or operator documentation from the completed
implementation and test learning. Reconcile concise in-code contracts with the
actual error behavior and relevant tests; remove stale or duplicate explanations
while preserving material caveats. Explain relevant debug controls and diagnostic
fields where operators need them. Retain validated implementation conventions
and their rationale/source examples in existing appropriate project docs; create
a focused document only when needed for reuse and none fits. Keep proposals and
task-specific exceptions distinct from adopted defaults. Make an explicit reuse
decision: use an existing relevant skill, or create/update a repo-local skill when
repeated work demonstrates a concrete benefit. Otherwise explain why none is needed. Do not
install or publish a skill without authority. Set `choices.skill_required: true` when the next
`skill-validate` node is genuinely required; otherwise omit that choice. A
documentation or reuse change may require affected checks to be refreshed.
For a consequential learning, record whether it stays in this run, becomes a
repo-local regression/example, or warrants a shared improvement proposal.
Keep the evidence, intended scope, and cross-task validation need with that
decision; a one-off workaround is not sufficient grounds for a general rule.""",
        implementation_quality=True,
    ),
    "skill-validate": _prompt(
        """\
Validate the selected reusable skill or skill-related change against its real
executable examples, inputs, failure behavior, and consumer documentation;
check the claimed host portability when applicable. Do not claim
a skill is usable from its presence alone. Refresh all plan, code, test, or
documentation checks affected by this work before final verification.
For a proposed shared lesson or prompt change, check the triggering example,
a relevant failure case, and other representative tasks for regressions before
adoption. Record the tested scope and limits; one successful example does not
establish a broadly reusable rule."""
    ),
    "verify": _prompt(
        """\
Run the actual relevant linters, executable tests, and other checks for the
current candidate. Inspect failures, fix justified defects, and rerun affected
checks until they are current; explain an invalid test before changing it. Tie
results to expected outcomes and disclose any unrun, blocked, or environment-
limited check rather than treating a partial green run as completion.
Check important planned failure behavior and inspect that code documentation
matches the current candidate; test success alone does not establish doc quality.
For persistent or repeated failure, separate evidence of a product defect,
invalid test, and environment problem. State the current testable diagnosis,
choose a small discriminating check, and record its observation and the reason
for the next action. Revisit the approach when retries add no evidence; never
waive a required check because a retry budget or investigation allowance ended.""",
        implementation_quality=True,
    ),
    "product-improve": _prompt(
        """\
Improve the assembled product candidate as a whole, including the integrated
plan, code, tests, documentation, skill/reuse decision, and verification
evidence. Reconsider consumers, cross-step behavior, dependencies, and
system-test needs, including whether a required consumer update or post-update
check has changed. Any plan, code, test, documentation, or skill change made
inside this action refreshes every affected check before convergence. Revisit
the selected operational/security checks, test-oracle adequacy, actual combined
worker outputs, and final-candidate review coverage in proportion to this
candidate's risk.""",
        improve=True,
        implementation_quality=True,
    ),
    "integrate": _prompt(
        """\
Perform only authorized Git and worktree integration work. Inspect the actual
branches, diffs, conflicts, identities, and resulting candidate; preserve user
work and do not infer that a merge, commit, push, or deployment occurred from
a plan or command attempt. Recheck integration-affected tests and surface a
permission or conflict blocker rather than forcing an external operation.
Verify shared interfaces and consumer behavior on the assembled candidate;
separate workers' passing checks do not establish that their combination works.
A material merge or conflict-resolution edit invalidates affected prior review
evidence: review that changed scope and refresh its checks before completion,
using an independent reviewer when available. Keep broader unfinished review
obligations explicit for carry-forward and outer Improve.""",
        implementation_quality=True,
    ),
    "carry-forward": _prompt(
        """\
Review broad remaining scope, dependencies, discoveries, system-test needs,
consumer impacts, release prerequisites, and reusable-skill obligations. Keep
current work separate from honest future work. If needed, return ordered
future-only `work_items`; do not use them to claim a future test, integration,
or release has already occurred. Carry unresolved required delivery, exact
target/authority, and pre/post-update verification obligations forward with
their evidence and owner; do not let an ordinary summary erase them.
Carry the implementation-conventions locator into applicable future work-item
context. Retain validated changes for later items without expanding their scope.
For a consequential learning, decide whether to retain it in this run, add a
repo-local regression/example, or propose a shared skill/prompt improvement.
Record the supporting evidence and target; avoid promoting a one-off workaround
into a general rule. Carry pending cross-task validation into the outer review
before shared adoption, without silently editing unrelated global guidance."""
    ),
    "system-test": _prompt(
        """\
Run or honestly assess the actual authorized integration, end-to-end, runtime,
or system checks that were planned. Verify the real target, prerequisites,
fixtures, authorization, and observed behavior; distinguish a planned case or
local mock from an executed system boundary. A genuinely non-applicable check
needs a concrete reason, while unknown access or target state is blocked.
Complete due pre-update checks here; leave required post-update consumer checks
explicitly pending for their assigned release-verification boundary rather than
calling them passed."""
    ),
    "outer-improve": _prompt(
        """\
Improve the entire product and delivery candidate, not a single local file.
Review cross-cutting requirements, integration and system evidence, release
readiness, consumer impact, documentation, skills, and handoff facts. Refresh
all checks affected by any plan, code, test, documentation, or skill change
made during the complete improvement campaign. Resolve pending learning
promotion proposals against representative regression evidence and existing
authority; retain, revise, or decline them explicitly. Unvalidated proposals
may remain documented future work but cannot be reported as adopted. Recheck
that required consumer updates and post-update checks remain carried forward
with their necessity, authority, and distinct evidence needs.""",
        improve=True,
        implementation_quality=True,
    ),
    "release-plan": _prompt(
        """\
Plan a release only within granted authority. Identify the intended target,
identity and version checks, permissions, prerequisites, user impact,
rollback/recovery path, monitoring, and pre/post-release verification. A plan
does not authorize the release or prove target access; leave unsupported
decisions blocked for direction.
First determine whether a consumer update is necessary; then separately
determine its exact target, operation, and scoped authority. A required but
unauthorized or unverified update is blocked, not non-applicable. Source
synchronization, artifact identity, consumer behavior, versioned deployment,
promotion, and access changes are distinct operations or observations.
This current action's deliverable is a non-executing release plan. After its
Improve campaign and planning-level prerequisite review, `done` means that plan
is complete, not that an update or consumer check has occurred. The existing
`release` action owns an authorized synchronization or update; `release-verify`
owns post-update consumer behavior. Do not block this plan merely because those
future actions have not run. Block only when a fact needed to scope the plan
safely, such as required authority, target, operation, or necessary current
pre-update condition, remains unresolved.
First produce the release plan or a justified non-applicable assessment, then
run the complete Improve campaign below on that candidate before returning
done. Challenge target identity, authority, ordering, recovery, and consumer
checks without performing the release. A non-applicable release still needs
review of that conclusion; it is valid only when no necessary in-scope
activation remains and does not require invented deployment work.""",
        improve=True,
    ),
    "release": _prompt(
        """\
Execute a release only when it is explicitly authorized and the planned target,
checks, and rollback conditions are satisfied. Inspect the real result before
claiming an external effect. When no release applies, report an honest,
concrete non-applicable reason; do not invent a deployment, commit, push, or
consumer change to advance the graph. Record operation/effect and artifact
identity separately. If an outcome is uncertain, reconcile it before retrying;
do not blindly repeat an update merely to obtain a new observation."""
    ),
    "release-verify": _prompt(
        """\
Verify the actual relevant release and consumer/runtime boundary using current
target evidence. Confirm the observed behavior, version or identity where
available, and release-specific checks; distinguish unavailable evidence from
a passed check. If release was genuinely non-applicable, verify the applicable
final consumer boundary and retain that reason. Source synchronization, an
artifact string, a URL, or a successful GET cannot replace a required consumer
interaction. If an update succeeded but consumer access is blocked, preserve the
update evidence and report behavior as blocked or unverified; do not re-upload
without evidence that retrying is appropriate."""
    ),
    "handoff": _prompt(
        """\
Produce an honest handoff of actual source, test, integration, release, and
consumer status. Name completed evidence, current limitations, unresolved
blockers, follow-up work, operational/revalidation needs, and the exact scope
of any non-applicable release. Do not convert a planned action, stale check,
or conversational summary into completion evidence. Report separately what was
implemented, what update was performed or already current, what artifact
identity was checked, what consumer behavior was verified, and what remains
blocked or unverified."""
    ),
}


if set(PROMPTS) != set(PRELUDE + INNER + OUTER):
    raise RuntimeError("navigator prompt catalog does not cover its graph")


__all__ = (
    "COMMON",
    "ENVIRONMENT_DISCOVERY_REQUIREMENTS",
    "IMPROVE",
    "IMPROVE_STAGES",
    "IMPLEMENTATION_QUALITY",
    "INNER",
    "OUTER",
    "PRELUDE",
    "PROMPTS",
)
