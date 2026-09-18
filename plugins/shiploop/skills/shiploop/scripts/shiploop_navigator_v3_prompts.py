"""Prompt catalog for navigator v3's script-owned SDLC traversal.

The navigator selects one producer step at a time.  After that producer has a
result, the runtime renders :func:`improve_prompt` and parks the parent action
while the selected Improve skill follows its own bound Until Loop runtime.
Neither prompt contains a copied Improve algorithm or a second review counter.
"""

from __future__ import annotations


PRELUDE = (
    "intake",
    "discovery",
    "research",
    "spec",
    "test-strategy",
    "plan",
    "prepare",
)

INNER = (
    "select-work",
    "step-plan",
    "test-spec",
    "baseline",
    "test-author",
    "test-red",
    "implement",
    "test-green",
    "test-refine",
    "regression",
    "document",
    "skill-assess",
    "skill-validate",
    "static-checks",
    "verify",
    "integrate",
    "integration-verify",
    "carry-forward",
)

OUTER = (
    "system-test-author",
    "system-test",
    "product-acceptance",
    "release-plan",
    "release-check",
    "release",
    "release-verify",
    "operations",
    "handoff",
)

STAGES = PRELUDE + INNER + OUTER


# Keep stage routing declarative and package-relative.  The navigator renders
# these selected locators with the package reference directory; this catalog
# does not persist a second graph, decision ledger, or prompt copy.
STAGE_REFERENCES: dict[str, tuple[tuple[str, str], ...]] = {
    "intake": (
        ("Prior-run and recovery guidance", "project-knowledge.md#new-work-versus-recovery"),
        ("Delivery authority guidance", "delivery-authority.md#ask-at-the-first-concrete-boundary"),
    ),
    "discovery": (
        ("Persistent project-context guidance", "project-knowledge.md#discover-persistent-context-before-planning"),
        ("Environment and source-return discovery", "environment-lifecycle.md#discover-before-planning-code"),
    ),
    "research": (
        ("Bounded research guidance", "research-loop.md#recursive-discovery-and-experiments"),
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
    ),
    "spec": (
        ("Behavior-model guidance", "behavioral-requirements.md#behavior-model"),
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
    ),
    "test-strategy": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("System-test catalog guidance", "system-tests.md#catalog-shape"),
    ),
    "plan": (
        ("Dependency-planning guidance", "backchain-planning.md#dependency-audit"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
    ),
    "prepare": (
        ("Environment preparation guidance", "environment-lifecycle.md#plan-preparation-before-its-first-consumer"),
        ("Workspace and return guidance", "workspace-lifecycle.md#entry-identity-and-storage"),
    ),
    "select-work": (
        ("Cold-start evidence guidance", "execution-planning.md#cold-start-evidence"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
    ),
    "step-plan": (
        ("Implementation constitution", "testing-and-documentation.md#implementation-constitution"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
    ),
    "test-spec": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "baseline": (
        ("Baseline-test guidance", "execution-planning.md#baseline-tests-and-migrations"),
    ),
    "test-author": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "test-red": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "implement": (
        ("Implementation constitution", "testing-and-documentation.md#implementation-constitution"),
    ),
    "test-green": (
        ("Iteration and verification guidance", "testing-and-documentation.md#iteration"),
    ),
    "test-refine": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "regression": (
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "document": (
        ("Documentation guidance", "testing-and-documentation.md#documentation"),
        ("Documentation and reuse guidance", "testing-and-documentation.md#iteration-documentation-and-reuse"),
    ),
    "skill-assess": (
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
    ),
    "skill-validate": (
        ("Documentation and reuse guidance", "testing-and-documentation.md#iteration-documentation-and-reuse"),
    ),
    "static-checks": (
        ("Iteration and verification guidance", "testing-and-documentation.md#iteration"),
    ),
    "verify": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "integrate": (
        ("Workspace integration guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
    "integration-verify": (
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "carry-forward": (
        ("Carry-forward mapping guidance", "carry-forward.md#mandatory-post-inner-mapping"),
        ("Persistent project-knowledge guidance", "project-knowledge.md#retain-learnings-for-the-next-invocation"),
    ),
    "system-test-author": (
        ("System-test catalog guidance", "system-tests.md#catalog-shape"),
    ),
    "system-test": (
        ("System-test placement guidance", "system-tests.md#placement-and-dependency-rules"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "product-acceptance": (
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
        ("Consumer delivery guidance", "consumer-delivery.md#what-to-establish"),
    ),
    "release-plan": (
        ("Environment promotion guidance", "environment-lifecycle.md#carry-the-route-into-final-delivery"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
    "release-check": (
        ("Delivery completion guidance", "consumer-delivery.md#where-completion-is-enforced"),
    ),
    "release": (
        ("Delivery authority mapping", "consumer-delivery.md#map-authority-readiness-to-existing-fields"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
    "release-verify": (
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
        ("Consumer delivery evidence guidance", "consumer-delivery.md#evidence-and-limits"),
    ),
    "operations": (
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
    ),
    "handoff": (
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
}


PROGRESS_REPORTING = """\
Progress: report the saved Done / Current / Pending / Blocked snapshot at
start/recovery and material milestones.  Only the current owner reports overall
progress.  State labels say which action is assigned, not that work, tests, or
Improve iterations have occurred.  Describe Improve activity only from its own
observed records; do not infer a review count, completion percentage, or ETA.
"""


COMMON = """\
This packet assigns one script-selected SDLC producer step.  The script owns the
durable graph, action identity, and legal successor; you own the engineering
judgment, repository work, evidence, and result.  Perform only the current
step.  Preserve unrelated work and do not choose a successor, advance parent
state, or treat a previous packet as the current assignment.

Read the current repository, run state, applicable instructions, and relevant
durable lessons before relying on earlier notes.  Treat Git history, plans, tool
descriptions, and prior results as context to recheck, not authority or proof.
Use actual observations for test, build, integration, release, and consumer
claims.  Keep scope, target authority, artifact identity, operation effects, and
consumer behavior distinct.  A missing prerequisite, permission, access, or
trustworthy check is unresolved or blocked; it is not a successful N/A.

During discovery, spec development, global planning and step planning, use the
packet's Interaction design guide to identify relevant actors, interaction
directions, channels, and state ownership. Choose the simplest suitable mechanism,
preferring existing capabilities for this request and environment; a hosted UI
does not imply server state for each action. Where a plan creates or revises work
items, retain only the relevant compact locator, decision, rationale, scope, and
revalidation condition in existing plan notes and that item's `context`; retain
the supporting source locator in the ordinary `evidence_refs`. Do not copy source
transcripts, invent a decision ledger, or treat a context summary as proof.

Return the packet's concise producer result with a truthful outcome, summary,
and useful evidence locators.  A justified N/A is still an output that states
what was assessed and why it does not apply.  Do not embed an Improve review
campaign in this result: every producer attempt result is followed by a separate
actual Improve-skill handoff before this graph can advance.
"""


IMPLEMENTATION_CONSTITUTION = """\
Implementation constitution for this step:
- Derive practices from the product purpose, current runtime/dependency and
  interface contracts, repository conventions, applicable skills/MCP tools, and
  supported library examples.  Record a justified departure; do not add a
  dependency or integration merely because it is available.
- Validate changed input and state boundaries.  Preserve actionable failures,
  proportional cleanup/recovery, and the original error type/cause/traceback;
  diagnostics must never mask the original failure.
- Reuse the existing debug control where available.  With debug enabled, emit
  bounded, redacted before/after state summaries at major actions, including the
  operation ID, important decisions, counts, state changes and failure outcome.
  Avoid whole-state dumps and expensive diagnostic work while debug is disabled.
- Before mutation or cleanup, capture safe stable context needed to explain an
  exception: operation/phase, expected versus observed conditions, relevant IDs
  and bounded state.  Keep sensitive values and duplicate stack traces out of
  user-facing messages; retain concise internal context and causal detail.
- Make public interfaces and non-obvious logic understandable with concise,
  colocated documentation of purpose, preconditions, outputs/errors, material
  effects/invariants, and rationale.  Prefer clear names and one authoritative
  explanation over boilerplate or repeated narration.
"""


DUTIES = {
    "intake": """\
Establish the requested outcome, repository and run boundaries, explicit user
constraints, authority limits, consumers/entry points, known risks, and open
questions.  Distinguish facts from assumptions and identify what discovery must
establish before planning, testing, implementation, or release work is trusted.
Do not implement or silently broaden scope here.
""",
    "discovery": """\
Inspect the current repository, Git/worktree state, instructions, relevant code,
tests, documentation, environment, consumers, and project knowledge.  Identify
the actual development, test, integration, and delivery boundaries.  Locate
current conventions, supported runtime/dependency versions, canonical code/test
examples, relevant MCP/API contracts, and reusable skills/libraries.  Separate
binding requirements, observed practices, and proposals; record source-backed
facts, conflicts, and consequential gaps without installing or provisioning
anything. Before planning, determine whether returning to the original source
branch triggers CI, deployment, publication, or another material effect, and
whether that return is a prerequisite for any required consumer check. Record the
actual route and uncertainty in existing environment/deployment notes; inspecting
it does not authorize a return, deployment, or early final-handoff action.
""",
    "research": """\
Resolve material unknowns with repository, primary-interface, or otherwise
appropriate evidence.  Connect each conclusion to its source, uncertainty,
affected requirement, consumer, prerequisite, reuse choice, and verification
need.  Assess relevant skills, MCP servers, libraries, and environment patterns
for actual fit and support; discovery alone is not successful use or authority to
install a dependency.  Leave unsupported questions open.
""",
    "spec": """\
Define the required behavior, boundaries, acceptance criteria, nonfunctional
expectations, error behavior, and user/consumer outcomes.  State independent
positive, failure, and boundary expectations before coding.  Preserve approved
scope and mark unresolved prerequisites or user decisions explicitly rather than
hiding them in implementation detail.
""",
    "test-strategy": """\
Create a risk-based test and verification strategy from the specification before
code.  Name independent expected outcomes, local/unit/integration/system checks,
negative cases, fixtures/data, environment and authorization needs, and the
owner/boundary for each required check.  Distinguish planned checks from executed
evidence and identify meaningful expected-RED controls where test-first work is
applicable.
""",
    "plan": """\
Create a dependency-aware delivery plan from desired outcomes back to required
producers.  Order readiness, test, implementation, integration, documentation,
and release work so consumers do not run before their prerequisites.  Define
ready/done conditions, candidate scope, check evidence, authority boundaries,
and correction routes.  Do not use the plan to imply unrun tests or authorized
external operations. Where this plan creates work items, retain each applicable
convention, canonical test/example, verified skill/MCP/library contract,
environment or delivery decision, and approved exception as a short source
locator plus decision, rationale, and revalidation condition in existing plan
evidence. Put only the item-specific compact summary in the existing work-item
`context` and preserve the source locators in ordinary `evidence_refs`.
""",
    "prepare": """\
Prepare or verify the approved development/test environment and prerequisites.
Confirm isolation, runtime/configuration/data safety, access, fixture readiness,
and baseline identity using safe observations.  Record a justified N/A only when
no preparation is needed for this candidate; missing required access or setup is
blocked. Recheck any discovered source-return trigger and an authorized
execution-checkout delivery/verification route before its first dependent work.
If source return must precede a required consumer check, record the ordering
conflict and keep it unresolved for reconciliation; do not return early, deploy,
or bypass the final-handoff return guard merely to make local work possible.
""",
    "select-work": """\
Select the next ready work item from the script-owned queue.  Confirm its
dependencies, scope, owner, relevant lessons, expected outcomes, and prerequisites
are current.  If no item is ready, return the concrete missing producer or
correction need; do not invent a new queue transition. Reopen the item's compact
`context` and relevant plan/evidence locators, then revalidate their stated
conditions before relying on an earlier convention or environment decision.
""",
    "step-plan": """\
Turn the selected item into a bounded implementation plan.  Name target files
and interfaces, behavior and failure cases, tests/fixtures/commands, existing
conventions and reusable capabilities, diagnostic/error-handling obligations,
documentation changes, integration impact, and required checks.  Revalidate
environment, skill/MCP/library, and project-practice choices for this exact item.
Reopen only the relevant item `context`, plan/evidence locators, and packet-selected
reference sections; verify that their scope and revalidation conditions still
apply. Record a changed decision or exception with its short locator and reason in
the existing plan/result evidence rather than relying on copied chat context.
""",
    "test-spec": """\
Specify executable tests before production edits when applicable.  Map the item
to independent positive, boundary, and failure assertions, fixtures, and command
paths.  Define what the baseline/expected RED should prove, what focused GREEN
will prove after implementation, and how regression coverage prevents weakening
the oracle.  A test specification is not execution evidence.
""",
    "baseline": """\
Run and record the relevant pre-change baseline checks.  Separate known existing
failures from failures introduced by the candidate, retain commands and observed
results, and establish the baseline needed to interpret RED/GREEN and later
regressions.  A blocked or invalid baseline remains incomplete.
""",
    "test-author": """\
Author or refine executable tests and fixtures from the independent test
specification before production implementation.  Preserve adequate coverage and
keep experiments isolated.  Do not weaken or delete an assertion merely to make
the eventual candidate pass; record a justified N/A only where test-first work
cannot apply and name the alternative evidence.
""",
    "test-red": """\
Execute the selected pre-implementation tests and establish a meaningful expected
RED for the intended missing behavior.  Confirm that the failure is caused by the
specified behavior rather than syntax, setup, fixture, or environment error.
Do not edit production code to make the test green at this stage.  A valid RED is
successful control evidence for this stage, not a product failure to hide.
""",
    "implement": """\
Implement the authorized bounded change.  Preserve unrelated work, inspect the
actual code as it changes, and carry discoveries into later test refinement.
Apply the planned behavior, error handling, opt-in diagnostics, exception context,
and concise code contracts.  Do not claim verification from an edit alone.
""",
    "test-green": """\
Run focused checks against the implemented candidate and establish meaningful
GREEN evidence for the specified behavior.  Diagnose failures before changing
code or tests, preserve the test oracle, and rerun affected checks after a
justified repair.  A passing command only supports the outcomes it actually
exercises.
""",
    "test-refine": """\
Refine cases and executable tests using the code that now exists while preserving
independent specification-based expectations.  Cover changed failure behavior,
debug on/off behavior and safe diagnostic context where relevant.  Correct an
oracle only with an independent reason; do not retrofit tests to the implementation
solely to obtain green.
""",
    "regression": """\
Execute relevant regression, negative, compatibility, and boundary checks on the
current candidate.  Include selected error and recovery behavior.  Distinguish a
product defect, invalid test, and environment issue with a small discriminating
observation; repeated unchanged failure is not progress.
""",
    "document": """\
Update necessary code, API, user, operator, design, and decision documentation
from observed implementation and test results.  Keep public/error/debug behavior
accurate, concise, and discoverable.  Promote durable facts and lessons into the
appropriate repository documentation rather than leaving them only in transient
run notes; preserve uncertainty and material caveats.
""",
    "skill-assess": """\
Assess whether an existing skill, helper, MCP capability, library pattern, or
repo-local skill change is warranted for this work.  Check actual task fit,
maintenance/portability implications, available examples, and expected consumer
value.  Record a clear reuse, update, or justified N/A disposition.  Presence or
installation does not prove execution, and this step does not authorize a new
dependency or publication.
""",
    "skill-validate": """\
Validate the selected reusable skill/helper or skill-related change against its
real examples, inputs, failure behavior, and consumer documentation.  If the
prior assessment found no applicable skill work, emit and verify the justified N/A
result instead of silently skipping this graph step.  Record the tested scope and
limitations; discovery or installation alone is not validation.
""",
    "static-checks": """\
Run the selected formatting, lint, type, build, packaging, and static analysis
checks for the current candidate.  Inspect failures, make only justified repairs,
and rerun affected checks.  State any required unrun check, why it is unavailable,
and the condition for completing it rather than treating partial green as done.
""",
    "verify": """\
Verify the complete work item against its acceptance criteria and current evidence.
Reconcile tests, static checks, documentation, error behavior, diagnostics,
dependencies, and known limitations.  Refresh checks affected by material changes
and retain failures or blocked boundaries honestly.  This is work-item acceptance,
not an assertion that integration or release has happened.
""",
    "integrate": """\
Perform only authorized Git/worktree integration for the candidate.  Inspect
actual diffs, branches, conflicts, identities, and combined interfaces.  Preserve
user work and keep run-time state, raw logs, credentials, and generated artifacts
out of product commits and returns.  Do not infer a merge, commit, push, or
deployment from a plan or command attempt.
""",
    "integration-verify": """\
Verify the assembled integrated candidate with the affected shared interfaces,
tests, and consumer-facing behavior.  Recheck evidence invalidated by merge or
conflict-resolution edits.  Separate a local integrated result from remote
delivery, and route a concrete integration failure to correction rather than
claiming that individual passing components establish the combination.
""",
    "carry-forward": """\
Record reusable learning, unresolved dependencies, newly discovered risks,
future work, system-test obligations, release prerequisites, and ownership.  Keep
current completed evidence separate from future plans.  Update appropriate project
knowledge and preserve concrete revalidation conditions; do not silently expand
scope or convert tentative ideas into adopted policy. When creating a future
work item, carry only its applicable compact decision/convention locator, rationale,
and revalidation condition in its existing `context`, with supporting source
locators in ordinary `evidence_refs`; do not duplicate transcripts or invent a
second decision store.
""",
    "system-test-author": """\
Author or refine whole-product/system test cases and fixtures from the assembled
candidate and global test strategy.  Cover real integration, consumer, runtime,
security, accessibility, migration, compatibility, and operational boundaries as
applicable.  A justified N/A records why that boundary does not apply; it does not
erase a required external check with missing access.
""",
    "system-test": """\
Execute authorized end-to-end, runtime, integration, or system tests against the
actual intended candidate and boundary.  Verify prerequisites, fixtures, target,
identity, authorization, and observed behavior.  Do not substitute a planned case
or local mock for a required system observation, deploy to unblock a test, or use
production without authority.
""",
    "product-acceptance": """\
Assess the assembled product against the original outcome, acceptance criteria,
cross-cutting requirements, consumer impact, test evidence, and known limits.
Identify missing product work, stale evidence, or delivery prerequisites and route
them honestly.  Acceptance does not itself execute a release or prove a remote
consumer boundary.
""",
    "release-plan": """\
Create an authorized release/recovery plan: target and candidate identity,
permission, prerequisites, user impact, rollback, monitoring, pre/post-release
checks, and stop conditions.  Distinguish source return, artifact publication,
deployment, promotion, and consumer verification.  A plan does not authorize or
perform an external operation; a required target or authority gap is blocked.
For isolated runs, source return occurs only after the final handoff Improve
child. Use an authorized delivery route from the execution checkout if available.
If source return itself is required before consumer checks can run, record the
ordering conflict for reconciliation and retain an incomplete disposition; never
claim earlier checks observed a future return-triggered effect.
""",
    "release-check": """\
Verify final release-candidate readiness without performing the release.  Check
candidate identity, current evidence, target/prerequisite status, required
approvals, rollback readiness, and pre-release validation.  Preserve any stale or
failed evidence and do not replay or promote merely to obtain a new observation.
""",
    "release": """\
Perform the planned release only when the exact target, operation, authority, and
conditions are current.  Record operation/effect and artifact identity separately.
If release is genuinely non-applicable, record the concrete reason.  Reconcile an
uncertain external outcome before retrying; never replay a merge, push, deployment,
or promotion simply to complete the graph.
""",
    "release-verify": """\
Verify the actual release and required deployed consumer/runtime behavior using
current target evidence.  Distinguish source synchronization, artifact identity,
operation receipt, and real consumer behavior.  A blocked or unknown post-release
check remains incomplete; preserve prior receipts and do not re-release blindly.
""",
    "operations": """\
Verify applicable operational readiness: monitoring, alerting, logging/diagnostic
access, recovery ownership, support documentation, cleanup, and revalidation
needs.  Record a justified N/A only after assessing the actual operational
boundary.  Do not represent a plan or configuration file as evidence the service
is observed and supported in operation.
""",
    "handoff": """\
Prepare an honest final handoff with source, test, integration, release, consumer,
and operational status; evidence locators; limits; blockers; follow-up work; and
revalidation needs.  Reconcile durable project documentation and product-return
receipts where applicable.  Do not transform an intent, stale green result, or
conversational summary into completion evidence.
""",
}


IMPROVE_SCOPES = {
    "intake": "the scope, authority, consumer, and unanswered-question record",
    "discovery": "repository/environment facts, conventions, reuse findings, and material gaps",
    "research": "source-backed conclusions, uncertainty, and reuse recommendations",
    "spec": "behavior, acceptance, failure boundaries, and consumer outcomes",
    "test-strategy": "independent test/risk strategy and required test boundaries",
    "plan": "dependency plan, readiness/done conditions, and correction routes",
    "prepare": "environment readiness evidence or its justified N/A disposition",
    "select-work": "the ready-item selection and prerequisite assessment",
    "step-plan": "the bounded item plan, conventions, checks, and diagnostic obligations",
    "test-spec": "test-first cases, independent oracles, and RED/GREEN definitions",
    "baseline": "baseline commands, observations, and pre-existing failure classification",
    "test-author": "new or refined executable tests and fixtures",
    "test-red": "the expected-RED control and its observed failure reason",
    "implement": "the scoped implementation, code contracts, diagnostics, and error behavior",
    "test-green": "focused GREEN evidence and any scoped repair",
    "test-refine": "post-implementation test refinement and oracle integrity",
    "regression": "regression, negative, compatibility, and recovery evidence",
    "document": "code and user/operator/project documentation updates",
    "skill-assess": "the reuse or skill-update decision, including a justified N/A",
    "skill-validate": "skill/helper execution evidence or its justified N/A",
    "static-checks": "lint, type, format, build, packaging, and static-check evidence",
    "verify": "work-item acceptance evidence and remaining limitations",
    "integrate": "authorized integration result and combined candidate scope",
    "integration-verify": "integrated-candidate evidence and cross-interface behavior",
    "carry-forward": "durable learning, pending obligations, and revalidation conditions",
    "system-test-author": "whole-product/system test cases and fixtures",
    "system-test": "executed system-boundary evidence and its prerequisites",
    "product-acceptance": "whole-product acceptance assessment and correction needs",
    "release-plan": "target/authority/recovery/check plan without executing release",
    "release-check": "final candidate readiness and pre-release evidence",
    "release": "the authorized release outcome or justified N/A disposition",
    "release-verify": "post-release target and consumer/runtime evidence",
    "operations": "operational-readiness evidence or justified N/A disposition",
    "handoff": "final evidence, limits, durable knowledge, and remaining obligations",
}


IMPLEMENTATION_STAGES = frozenset(
    {
        "step-plan",
        "test-spec",
        "test-author",
        "test-red",
        "implement",
        "test-green",
        "test-refine",
        "regression",
        "document",
        "static-checks",
        "verify",
        "integrate",
        "integration-verify",
    }
)


def _require_stage(stage: str) -> None:
    if stage not in DUTIES:
        raise ValueError(f"unknown navigator-v3 stage: {stage!r}")


def prompt(stage: str) -> str:
    """Return the single current producer instruction for a v3 graph stage."""
    _require_stage(stage)
    parts = [COMMON, DUTIES[stage]]
    if stage in IMPLEMENTATION_STAGES:
        parts.append(IMPLEMENTATION_CONSTITUTION)
    parts.append(PROGRESS_REPORTING)
    return "\n\n".join(parts)


def improve_prompt(stage: str) -> str:
    """Return the actual Improve-skill handoff for a completed producer stage."""
    _require_stage(stage)
    return f"""\
This producer attempt has returned a result; its parent action now awaits Improve.
Invoke the selected actual Improve skill for {IMPROVE_SCOPES[stage]}.  Read the
selected skill card and follow the Until Loop runtime bound by that card.  Use the
parent-provided candidate scope, prior producer result, relevant lessons, expected
check state, allowed edits, authority, and evidence/return locators.

When the candidate concerns actor interactions, channels, or state ownership,
read the packet's Interaction design guide and relevant decision/evidence notes.
Carry those locators into the child contract for cold recovery; revalidate the
choice against this request, environment, and affected tests without inventing
distributed infrastructure or expanding the assigned scope.

Treat the relevant work-item `context`, parent `evidence_refs`, plan notes, and
packet-selected reference locators as parent-supplied cold-context inputs. Reopen
and revalidate only the sources relevant to this candidate, then retain a compact
current locator, decision, rationale, and revalidation result in the child review
notebook. Do not replace those source locators with copied transcripts, a new child
ledger, or an unverified summary.

Improve owns its own review iterations, evidence notebook, continuation, and
completion judgment.  Do not replace it with an inline review algorithm, copied
policy, ShipLoop review counter, child phase graph, or guessed runtime command.
The parent action remains pending while the child is active or blocked.  Resume a
recorded child through its authoritative state; do not initialize a replacement.
On accepted child completion, use the packet's parent return route to import the
bound evidence and lessons once.  Do not advance the SDLC graph yourself.

Children have no commit authority by default: preserve the parent no-commit
constraint unless the packet explicitly supplies a user- or repository-authorized
exception.  Keep Until Loop state and child evidence out of product commits and
integration returns.  Refresh affected checks after child edits.  For a RED-stage
handoff, do not make production edits merely to turn the expected RED green.  For
release/verification handoffs, reconcile an uncertain external outcome rather
than replaying it.
"""


if len(STAGES) != 34 or len(set(STAGES)) != len(STAGES):
    raise RuntimeError("navigator-v3 stage catalog must contain 34 unique stages")
if set(DUTIES) != set(STAGES) or set(IMPROVE_SCOPES) != set(STAGES):
    raise RuntimeError("navigator-v3 prompts do not cover the complete graph")


PROMPTS = {stage: prompt(stage) for stage in STAGES}
IMPROVE_PROMPTS = {stage: improve_prompt(stage) for stage in STAGES}


__all__ = (
    "COMMON",
    "DUTIES",
    "IMPLEMENTATION_CONSTITUTION",
    "IMPLEMENTATION_STAGES",
    "IMPROVE_PROMPTS",
    "IMPROVE_SCOPES",
    "INNER",
    "OUTER",
    "PRELUDE",
    "PROGRESS_REPORTING",
    "PROMPTS",
    "STAGE_REFERENCES",
    "STAGES",
    "improve_prompt",
    "prompt",
)
