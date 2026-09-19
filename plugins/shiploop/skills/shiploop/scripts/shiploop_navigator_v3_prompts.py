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

TEST_FACILITY_STAGES = frozenset({
    "test-strategy", "plan", "step-plan", "test-spec", "test-author", "test-red",
    "test-refine", "regression", "carry-forward", "system-test-author", "release-plan",
})


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
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
        ("Environment and source-return discovery", "environment-lifecycle.md#discover-before-planning-code"),
        ("UI planning ownership when applicable", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
    ),
    "research": (
        ("Bounded research guidance", "research-loop.md#recursive-discovery-and-experiments"),
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
    ),
    "spec": (
        ("Behavior-model guidance", "behavioral-requirements.md#behavior-model"),
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "test-strategy": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("System-test catalog guidance", "system-tests.md#catalog-shape"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "plan": (
        ("Dependency-planning guidance", "backchain-planning.md#dependency-audit"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("Initial-plan reconciliation", "requirements-definition.md#initial-plan-reconciliation"),
        ("UI planning ownership when applicable", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
    ),
    "prepare": (
        ("Environment preparation guidance", "environment-lifecycle.md#plan-preparation-before-its-first-consumer"),
        ("UI planning ownership when applicable", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
        ("Workspace and return guidance", "workspace-lifecycle.md#entry-identity-and-storage"),
    ),
    "select-work": (
        ("Cold-start evidence guidance", "execution-planning.md#cold-start-evidence"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
    ),
    "step-plan": (
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
        ("Implementation constitution", "testing-and-documentation.md#implementation-constitution"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("UI planning ownership when applicable", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
    ),
    "test-spec": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "baseline": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Baseline-test guidance", "execution-planning.md#baseline-tests-and-migrations"),
    ),
    "test-author": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "test-red": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "implement": (
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Implementation constitution", "testing-and-documentation.md#implementation-constitution"),
    ),
    "test-green": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Iteration and verification guidance", "testing-and-documentation.md#iteration"),
    ),
    "test-refine": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "regression": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "document": (
        ("Documentation guidance", "testing-and-documentation.md#documentation"),
        ("Documentation and reuse guidance", "testing-and-documentation.md#iteration-documentation-and-reuse"),
    ),
    "skill-assess": (
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
    ),
    "skill-validate": (
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
    ),
    "static-checks": (
        ("Iteration and verification guidance", "testing-and-documentation.md#iteration"),
    ),
    "verify": (
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "integrate": (
        ("Workspace integration guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
    "integration-verify": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "carry-forward": (
        ("Carry-forward mapping guidance", "carry-forward.md#mandatory-post-inner-mapping"),
        ("Persistent project-knowledge guidance", "project-knowledge.md#retain-learnings-for-the-next-invocation"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "system-test-author": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("System-test catalog guidance", "system-tests.md#catalog-shape"),
    ),
    "system-test": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("System-test placement guidance", "system-tests.md#placement-and-dependency-rules"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "product-acceptance": (
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
        ("Consumer delivery guidance", "consumer-delivery.md#what-to-establish"),
    ),
    "release-plan": (
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Environment promotion guidance", "environment-lifecycle.md#carry-the-route-into-final-delivery"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "release-check": (
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Delivery completion guidance", "consumer-delivery.md#where-completion-is-enforced"),
    ),
    "release": (
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Delivery authority mapping", "consumer-delivery.md#map-authority-readiness-to-existing-fields"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
    "release-verify": (
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
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


for _outer_stage in OUTER:
    STAGE_REFERENCES[_outer_stage] += (
        ("OUTER test-planning handshake", "repeatable-test-suites.md#outer-test-planning-handshake"),
    )

for _facility_stage in TEST_FACILITY_STAGES:
    STAGE_REFERENCES[_facility_stage] += (
        ("Reusable test facilities", "repeatable-test-suites.md#reuse-and-define-test-facilities"),
    )


PROGRESS_REPORTING = """\
Progress: report the saved Done / Current / Pending / Blocked snapshot at
start/recovery and after each major completed step. Only the current owner reports
overall progress. State labels say which action is assigned, not that work, tests, or
Improve iterations have occurred.  Describe Improve activity only from its own
observed records; do not infer a review count, completion percentage, or ETA.
Run to completion by default within scope and authority. Emit progress as an
intermediate update, then immediately continue the active packet's current owner
while authorized runnable work remains. Do not wait for acknowledgement, ask
whether to continue, or end the turn merely to deliver a report. Follow the exact
callback and its returned packet, including a bound Improve child; a producer's
done or a child's completion is not run completion. Respect explicit user stops
and paused/blocked/halted/done states; resolve recoverable conditions through the
printed route and ask only for an actually missing decision, authority, or access.
"""


COMMON = """\
This packet assigns one script-selected SDLC producer step.  The script owns the
durable graph, action identity, and legal successor; you own the engineering
judgment, repository work, evidence, and result. Perform only the current step
before its callback, then immediately follow the newly returned packet.
Preserve unrelated work and do not choose a successor, advance parent state
yourself, or treat a previous packet as the current assignment.

Read the current repository, run state, applicable instructions, and relevant
durable lessons before relying on earlier notes.  Treat Git history, plans, tool
descriptions, and prior results as context to recheck, not authority or proof.
Use actual observations for test, build, integration, release, and consumer
claims.  Keep scope, target authority, artifact identity, operation effects, and
consumer behavior distinct.  A missing prerequisite, permission, access, or
trustworthy check is unresolved or blocked; it is not a successful N/A.

Requested runtime / entry point / material dependency: preserve each original
user requirement, and distinguish it from a verified contract, observed practice,
or assumption in the existing notes/results. Record local-test-route evidence
separately from target compatibility. A local fixture or preview cannot supply a
target capability absent from the requested runtime. Delivery outside the present
scope does not by itself make requested-runtime compatibility N/A. Establish
compatibility with target-compatible source or local evidence where possible;
otherwise keep the gap unresolved.

Follow the packet's Maintained requirements policy. Read the applicable accepted
product requirements, including preserved and cross-cutting conditions, from
their repository-owned home; a new request changes scope without erasing
unaffected rules. Carry requirement and test locators into work-item context.
Do not infer approved intent from code/tests or silently relax a condition to
match them. Keep proposals and verification gaps distinct from accepted intent.
Follow the packet's Reference handoff policy: distinguish package guidance,
repository-owned requirements/tests and run-local evidence. Resolve and verify
the selected file/section against its named root; retain exact applicable
locators for downstream work, not merely a link to this policy.
Use the packet's Requirements definition guide to reconcile existing specs and
define applicable non-functional requirements. Current explicit user instructions
supersede conflicting older clauses; preserve unaffected conditions and retain
clarification, requirement, and verification locators for cold recovery.
Later clarifications must be actual user instructions for this same request with
their durable user-source/decision basis; an unverified host summary is not an
instruction. Use the active correction/revision route for affected frozen contracts.

During discovery, research, spec development, global planning and step planning,
use the packet's Interaction design guide and its incoming-events, UI-specific planning
and review sections as applicable. Identify actors, channels, incoming/outgoing events,
connection lifecycle and state ownership; retain the existing baseline/delta.
For affected UI, read and apply suitable available design guidance before consequential
decisions; record its identity/version or digest, or the repository-guidance fallback.
Establish or preserve component, interaction and skin premises, truthful async feedback
and deployment fit. Prefer existing capabilities; no UI does not skip applicable
machine interactions. Put exact relevant source/section locators and short decisions
in each affected work-item context and evidence_refs, including planned check locators,
for cold recovery and the normal Improve handoff; do not start a nested review.

Where a plan creates or revises work
items, retain only the relevant compact locator, decision, rationale, scope, and
revalidation condition in existing plan notes and that item's `context`; retain
the supporting source locator in the ordinary `evidence_refs`. Do not copy source
transcripts, invent a decision ledger, or treat a context summary as proof.

Return the packet's concise producer result with a truthful outcome, summary,
and useful evidence locators. For relevant product work, include the selected
maintained requirement sections and test/evidence locators in the result's
existing evidence_refs so the next Improve packet can recover them. If a required
source is missing, report the gap rather than inventing a locator or omitting it.
A justified N/A is still an output that states
what was assessed and why it does not apply.  Do not embed an Improve review
campaign in this result: every producer attempt result is followed by a separate
actual Improve-skill handoff before this graph can advance.
"""


SELECTED_CASE_RECONCILIATION = """\
Selected-case reconciliation: in the existing plan/results, classify every
selected case as passed, failed, blocked, not-run, or justified N/A, preserving
required gaps. Source, HTTP, or DOM structure alone cannot close a selected
rendered interaction; retain the observed rendered action/outcome or leave it
incomplete.
"""


RECONCILIATION_STAGES = frozenset(
    {
        "verify",
        "integration-verify",
        "system-test",
        "product-acceptance",
        "release-verify",
        "handoff",
    }
)


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
Locate existing specs and quality policies, establish their scope/status, and
screen applicable non-functional requirements using the Requirements definition guide.
Use the Repository-local skill guidance to inspect existing repo index/README/AGENTS
skill links and plausible skill contracts before proposing implementation. Record
fit or no fit with source locators; for a selection retain its entrypoint, effective
input/default sources, applicable product contract and revalidation conditions in
ordinary evidence_refs and linked notes. Inspect skill packages without editing
them here; preserve the existing project-knowledge recording/index policy.
Use the packet's Initial repository baseline guide. For every new change to an
existing implementation, after only the minimum inspection needed to identify
the packet's designated starting repository directory, instructions, and safe
existing command. Then run the established full suite when practical or
established smoke suite otherwise on
the unchanged starting content there. This is discovery's first verification activity:
actual execution, rather than selecting a command or citing an old pass, is
required. Record command/cwd, checked content and target, result, coverage
limits, and an evidence locator in ordinary evidence_refs. Classify a failure,
missing coverage, setup/access block, uncertainty, or expected repair RED before
planning; it is not healthy. Preserve the observation for prerequisite planning;
do not edit product source, tests, dependency definitions, or configuration to
turn it green. Discovery may finish its investigation with a failed baseline,
but that does not make dependent feature work ready.
""",
    "research": """\
Resolve material unknowns with repository, primary-interface, or otherwise
appropriate evidence.  Connect each conclusion to its source, uncertainty,
affected requirement, consumer, prerequisite, reuse choice, and verification
need.  Assess relevant skills, MCP servers, libraries, and environment patterns
for actual fit and support; discovery alone is not successful use or authority to
install a dependency.  Leave unsupported questions open.
Research consequential quality-target and feasibility unknowns from existing
contracts and appropriate evidence; measured baselines do not choose user policy.
""",
    "spec": """\
Define the required behavior, boundaries, acceptance criteria, nonfunctional
expectations, error behavior, and user/consumer outcomes.  State independent
positive, failure, and boundary expectations before coding.  Preserve approved
scope and mark unresolved prerequisites or user decisions explicitly rather than
hiding them in implementation detail.
Reconcile the delta with maintained product requirements: preserve, add, modify,
or retire affected conditions with their request/decision basis. Retain accepted
intent outside transient run notes, with pending implementation/checks explicit.
Complete the Requirements definition guide's non-functional assessment: record
operating conditions, measurable bounds or observable criteria, verification
methods, justified exclusions, and material unresolved targets. Do not invent
targets or declare dependent work ready with material requirement conflicts open.
Use the State and data assessment to identify affected resources, target identities,
before/after invariants and recovery; retain applicable checks and unknowns.
""",
    "test-strategy": """\
Create a risk-based test and verification strategy from the specification before
code.  Name independent expected outcomes, local/unit/integration/system checks,
negative cases, fixtures/data, environment and authorization needs, and the
owner/boundary for each required check.  Distinguish planned checks from executed
evidence and identify meaningful expected-RED controls where test-first work is
applicable.
Map applicable new and preserved non-functional criteria to checks and their
environment/workload prerequisites; missing evidence or access is not N/A.
Read the Repeatable test-suite guide. Select the major harnesses and suite entry
points now; reuse a prior-run harness only after revalidating its current fit.
Consider supported platform/library testing systems and available browser tools
by required capability rather than product name. Record their roles, fit,
availability and prerequisites; distinguish inspection from retained assertions.
Link the durable strategy note in ordinary evidence_refs, with the selection
rationale, fixture lifecycle, suite entry points and revalidation conditions.
Retain exact focused, smoke, and full-suite commands, inclusion rules, expected
cost and environment/fixture prerequisites. Plan durable regression tests, not
one-off probes; smoke is a bounded subset, never evidence for the full suite.
Plan execution location separately from target location: local, client checks
against a deployed target, or remote-resident tests. Discover the remote framework,
availability, access and deployment prerequisites; retain the authorized route to
define/register, install and invoke remote tests. A local pass is not a remote pass.
Use the packet's Initial repository baseline guide and consume the observed
initial baseline rather than treating suite selection as proof. Retain its
coverage and limits; distinguish a passing subset from a failed, blocked,
intermittent, missing-test, or expected-RED observation. Name the setup, repair,
or test-bootstrap prerequisite and its required evidence before dependent feature
checks, using ordinary evidence_refs and planned work-item context.
""",
    "plan": """\
Create a dependency-aware delivery plan from desired outcomes back to required
producers.  Order readiness, test, implementation, integration, documentation,
and release work so consumers do not run before their prerequisites.  Define
ready/done conditions, candidate scope, check evidence, authority boundaries,
and correction routes.  Do not use the plan to imply unrun tests or authorized
external operations.
Apply Initial-plan reconciliation to the architecture, reconciled spec, NFRs and
State and data assessment. Map each applicable obligation to its responsible work
item, prerequisites, observing test and relevant release/recovery conditions, or
retain a reasoned exclusion or unresolved need. Preserve the mapping in existing
plan notes, item context and evidence_refs; a completed template is not proof.
For affected interactions, recheck the guide's relevant subsections instead of
copying the prior plan unchecked. Retain a compact Design basis paragraph or
exact section links: baseline/delta; state/event/connection agreements and planned
recovery checks (including a crash after acknowledgment but before processing
accepted work where applicable); and source/check locators. For UI, include component/interaction/skin
premises, selected design guidance locator plus identity/version or digest (or
named fallback), and meaningful async cues with their purpose and reduced-motion
alternative, or an explicit static choice. For consequential UI choices, include
the guide's ambition, reuse/evolve/upgrade decision, rough effort/benefit and
compatibility check; reuse accepted choices for unaffected scope and the existing
design/test facilities. The next review is the packet's automatic Improve handoff immediately after this producer result, before
implementation. Do not schedule a review stage or claim it ran. Link this plan in
evidence_refs; keep these as ordinary notes, not new result fields.
Use the packet's Initial repository baseline guide. Carry initial-baseline
evidence and classification through ordinary evidence_refs and affected work-item
context. Put an affected foundation repair, setup prerequisite, or missing-test
bootstrap in the earliest feasible work item before its dependent feature, with
the original check's passing rerun when available, or a separately recorded
passing post-bootstrap characterization against unchanged application behavior,
as feature readiness. Preserve the original no-suite observation. An expected-RED
repair may start its own work. A bootstrap may make the smallest justified
test-only harness, dependency, or configuration edits while testing unchanged
application behavior; its producer completion alone does not make the repository
healthy or unblock dependent features without the required passing evidence.
Unknown relatedness stays blocking; do not
silently waive or expand unrelated failures.
Where this plan creates work items, retain each applicable
convention, canonical test/example, verified skill/MCP/library contract,
environment or delivery decision, and approved exception as a short source
locator plus decision, rationale, and revalidation condition in existing plan
evidence. Put only the item-specific compact summary in the existing work-item
`context` and preserve the source locators in ordinary `evidence_refs`.
For a selected local skill, include the repo index/selection-note locator and what
must be revalidated for that item's inputs. Treat no fit as a current observation;
later items must reread the index for skills learned during this run.
Use the packet's Run-wide test strategy source. Carry its locator and the
applicable compact test decisions into each work item's existing `context`;
include execution/target location, fixture and suite choices, and what to recheck.
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
Use the packet's Initial repository baseline guide. When setup or access blocked
the initial baseline, prepare only the approved prerequisite, retain the original
observation, then rerun the original initial check against unchanged product and
tests before dependent feature edits. Do not replace it with an easier route or
describe the blocked baseline as passed.
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
Use the Coding decision guide to retain a compact decision record in the linked
plan note: outcome and preserved invariants, changed responsibilities/contracts,
applicable engineering decisions, ordered edits, independent checks, readiness,
completion and revalidation conditions. Identify the actual runtime/version,
artifact and boundary; read only matching practice/platform sections. Link the
accepted plan and selected sections in evidence_refs; do not copy every card or
create boilerplate for inapplicable concerns. Planning does not authorize edits.
Use the Repository-local skill guidance. Reopen the repo's current skill index or
README/AGENTS links, even if earlier context reported no fit: a preceding item may
have created or evolved a skill. Prefer unchanged reuse with supported inputs and
defaults. Record the selection or no-fit rationale in the linked plan/evidence
note; retain the entrypoint, effective inputs/default sources, product contract,
validation locators and revalidation condition in ordinary evidence_refs. Keep
later decision changes in these notes, not edits to the script-owned work queue.

Keep the interaction delta within the selected work item; available APIs and
other features in the original request do not expand it. Apply UI planning
ownership where relevant. An unresolved prerequisite outside this item's
authorized scope needs its supplier/correction route and the packet's blocked
disposition, not just a future implementation bullet.
For affected interactions, recheck the guide's relevant subsections instead of
copying the prior plan unchecked. Retain a compact Design basis paragraph or
exact section links: baseline/delta; state/event/connection agreements and planned
recovery checks (including a crash after acknowledgment but before processing
accepted work where applicable); and source/check locators. For UI, include component/interaction/skin
premises, selected design guidance locator plus identity/version or digest (or
named fallback), and meaningful async cues with their purpose and reduced-motion
alternative, or an explicit static choice. For consequential UI choices, include
the guide's ambition, reuse/evolve/upgrade decision, rough effort/benefit and
compatibility check; reuse accepted choices for unaffected scope and the existing
design/test facilities. The next review is the packet's automatic Improve handoff immediately after this producer result, before
implementation. Do not schedule a review stage or claim it ran. Link this plan in
evidence_refs; keep these as ordinary notes, not new result fields.
Use the packet's Initial repository baseline guide. Revalidate the initial
baseline evidence for this item's starting content, command, runtime/configuration,
target, and fixture assumptions; reuse only when they still apply, otherwise rerun
the relevant existing check. Retain its locator and readiness condition in the
item context. A named repair or test-bootstrap item may carry expected RED or
missing coverage into its owned edits; a dependent feature waits for the required
passing rerun.
Reopen only the relevant item `context`, plan/evidence locators, and packet-selected
reference sections; verify that their scope and revalidation conditions still
apply. Record a changed decision or exception with its short locator and reason in
the existing plan/result evidence rather than relying on copied chat context.
For every INNER change, use the Repeatable test-suite guide to reassess setup,
the test and independent oracle, teardown, and focused/smoke/full-suite placement.
Reopen the Run-wide test strategy source and this item's test context. Retain
any justified changed decision and its evidence in the current plan/evidence_refs.
Revalidate platform/library testing systems and available browser tools for the
changed surfaces; reuse supported choices or record a justified revision. Turn
useful inspection findings into retained tests or explicit manual procedures.
Retain the harness and case locators in the existing plan and work-item context.
For remote-resident cases, revalidate framework availability and the authorized
setup, test-definition/invocation, result retrieval and teardown route.
""",
    "test-spec": """\
Specify executable tests before production edits when applicable.  Map the item
to independent positive, boundary, and failure assertions, fixtures, and command
paths.  Define what the baseline/expected RED should prove, what focused GREEN
will prove after implementation, and how regression coverage prevents weakening
the oracle.  A test specification is not execution evidence.
Specify setup, test/assertions, and teardown together, or state why a stateless
case needs no setup or teardown. Reuse fixture code without assuming mutable
state is shareable. Share expensive setup only with demonstrated noninterference;
if in doubt, use per-test isolation. Plan failure cleanup and suite registration.
""",
    "baseline": """\
Run and record the relevant pre-change baseline checks.  Separate known existing
failures from failures introduced by the candidate, retain commands and observed
results, and establish the baseline needed to interpret RED/GREEN and later
regressions. A blocked or invalid baseline remains incomplete for dependent
feature readiness.
Use the packet's Initial repository baseline guide. Check whether the initial
evidence still applies to this item's current starting state and reuse it only
when it does; otherwise execute the relevant existing check before edits. Keep
failure classification and evidence locators in ordinary results/context. A named
repair or test-bootstrap producer may retain an expected RED or missing coverage
as its baseline classification so it can perform its assigned work. That result
does not certify health or unblock a dependent feature without its required
passing rerun.
""",
    "test-author": """\
Use the Run-wide test strategy source and current item context to select the
applicable harness and test boundaries; revalidate the choice before authoring.
Author or refine executable tests and fixtures from the independent test
specification before production implementation.  Preserve adequate coverage and
keep experiments isolated.  Do not weaken or delete an assertion merely to make
the eventual candidate pass; record a justified N/A only where test-first work
cannot apply and name the alternative evidence.
Retain tests and fixtures in the repository. Register each case in the full
regression route and applicable focused entry points; decide smoke membership
independently without duplicating tests. Follow the Repeatable
test-suite guide for setup/teardown, safe fixture sharing, and rerun instructions;
verify discovery selects the cases rather than merely recording their paths.
For remote-resident cases, retain/version the remote definitions and registration
with their authorized installation/invocation prerequisites.
""",
    "test-red": """\
Execute the selected pre-implementation tests and establish a meaningful expected
RED for the intended missing behavior.  Confirm that the failure is caused by the
specified behavior rather than syntax, setup, fixture, or environment error.
A missing test facility is a prerequisite gap, not meaningful RED. Facility
readiness must not require future product behavior to pass.
Do not edit production code to make the test green at this stage.  A valid RED is
successful control evidence for this stage, not a product failure to hide.
""",
    "implement": """\
Implement the authorized bounded change.  Preserve unrelated work, inspect the
actual code as it changes, and carry discoveries into later test refinement.
Apply the planned behavior, error handling, opt-in diagnostics, exception context,
and concise code contracts.  Do not claim verification from an edit alone.
Use the Coding decision guide to reopen the accepted plan and only its relevant
practice/platform sections. Check current code, versions and consumers before
reuse or augmentation. Retain justified revisions in the linked note; a new
prerequisite or authority boundary uses the existing correction route.
""",
    "test-green": """\
Run focused checks against the implemented candidate and establish meaningful
GREEN evidence for the specified behavior.  Diagnose failures before changing
code or tests, preserve the test oracle, and rerun affected checks after a
justified repair.  A passing command only supports the outcomes it actually
exercises.
""",
    "test-refine": """\
Recheck the Run-wide test strategy source against the current item context and
observed implementation; record revised test decisions in ordinary evidence_refs.
Refine cases and executable tests using the code that now exists while preserving
independent specification-based expectations.  Cover changed failure behavior,
debug on/off behavior and safe diagnostic context where relevant.  Correct an
oracle only with an independent reason; do not retrofit tests to the implementation
solely to obtain green.
Reassess setup/teardown and safe sharing from actual behavior; preserve stateless
cases without boilerplate. Keep refined tests registered in the repeatable suites
and refresh their case, fixture, command, and cost notes when those change.
""",
    "regression": """\
Use the Run-wide test strategy source and current item context to recover the
applicable retained suites, target prerequisites and justified decision changes.
Revalidate retained facility definitions and readiness for this regression target;
reuse the existing route when it still fits and retain any required correction.
Execute relevant regression, negative, compatibility, and boundary checks on the
current candidate.  Include selected error and recovery behavior.  Distinguish a
product defect, invalid test, and environment issue with a small discriminating
observation; repeated unchanged failure is not progress.
Use the retained suite commands and report the selected scope. Check rerun and
cleanup isolation when state or fixture sharing changed; exercise relevant order
and parallel hazards. A smoke pass cannot stand for the required full suite.
""",
    "document": """\
Update necessary code, API, user, operator, design, and decision documentation
from observed implementation and test results.  Keep public/error/debug behavior
accurate, concise, and discoverable.  Promote durable facts and lessons into the
appropriate repository documentation rather than leaving them only in transient
run notes; preserve uncertainty and material caveats.
Reconcile maintained requirements with accepted changes, not merely observed code:
preserve unaffected conditions and link tests/evidence or unresolved gaps. Update
README/index links to the authoritative home without duplicating its contract.
""",
    "skill-assess": """\
Assess whether an existing skill, helper, MCP capability, library pattern, or
repo-local skill change is warranted for this work.  Check actual task fit,
maintenance/portability implications, available examples, and expected consumer
value. Record a clear reuse, update, create, or justified N/A disposition. Presence or
installation does not prove execution, and this step does not authorize a new
dependency or publication.
Read any existing skill index, README or AGENTS skill links and the linked
local-skill guidance; absence of an index is not a blocker. Prefer unchanged
reuse with existing inputs/defaults, then a compatible local update; create a
separate local skill only for an evidenced gap or incompatible contract. Perform
the warranted skill/index edits within this item's scope, preserving supported
older uses. Keep generated skills in the product repository, never install them
globally. Link the disposition note and applicable repo index, selected entrypoint,
effective input/default sources, product contract and validation evidence in
ordinary evidence_refs so Improve and the next context can recover them. Do not
invent entrypoints or validation for a no-fit disposition.
""",
    "skill-validate": """\
Validate the selected reusable skill/helper or skill-related change against its
real examples, inputs, failure behavior, and consumer documentation.  If the
prior assessment found no applicable skill work, emit and verify the justified N/A
result instead of silently skipping this graph step.  Record the tested scope and
limitations; discovery or installation alone is not validation.
For a changed skill, exercise the triggering case and a retained older use; check
applicable defaults/overrides and a relevant failure boundary. A cross-context
reuse claim needs a fresh-reader trial using only the repo index, skill and new
task; otherwise record that cold-context reuse remains untested.
""",
    "static-checks": """\
Run the selected formatting, lint, type, build, packaging, and static analysis
checks for the current candidate.  Inspect failures, make only justified repairs,
and rerun affected checks.  State any required unrun check, why it is unavailable,
and the condition for completing it rather than treating partial green as done.
""",
    "verify": """\
Verify the complete work item against its acceptance criteria and current evidence.
Use the Coding decision guide to compare the actual diff and affected consumers
with the accepted plan, justified revisions and selected practice/platform checks.
Preserve any required real-boundary gap; a pattern name or tool pass is not proof
of the behavior it did not exercise.
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
Preserve repeatable tests, fixture lifecycle decisions, harness/case locators and
focused/smoke/full-suite commands in repository test documentation and work-item
context. Link pending full-suite or real-boundary checks with their owner; do not
leave the only rerun procedure in transient run notes.
Retain the originating strategy locator alongside current item-specific test
decisions so later items and whole-system tests can revalidate their basis.
For selected local skills, retain the repo index/entrypoint, applicable inputs or
overrides, validation evidence and revalidation trigger; keep the reusable
procedure outside disposable run storage.
Maintain the existing skill index/README links and their short SHIPLOOP.md locator
so the next item or run can find newly created or evolved local skills. Keep
task-specific values in evidence and revalidate prior selections for each new task.
""",
    "system-test-author": """\
Reopen the Run-wide test strategy source. From accepted history, select the
latest done test-decision record for every relevant completed item: step-plan,
test-spec, test-author, test-refine or regression, with its retained prior locators.
Keep selected action/result and durable test-note locators in evidence_refs.
Do not infer whole-product coverage from the last transition or final item.
Reconcile their suite membership and prerequisites before adding cases.
Author or refine whole-product/system test cases and fixtures from the assembled
candidate and global test strategy.  Cover real integration, consumer, runtime,
security, accessibility, migration, compatibility, and operational boundaries as
applicable.  A justified N/A records why that boundary does not apply; it does not
erase a required external check with missing access.
Integrate retained INNER cases with the repeatable full-suite entry point; retain
the smoke selection and new system cases without copying tests into another suite.
Review shared setup cost, independent assertions, isolation and failure teardown
using the Repeatable test-suite guide. Verify actual discovery and rerun commands.
Author/version remote-resident definitions and registration when the remote
framework requires them, with repeatable authorized installation and invocation.
Retain an integrated test plan in ordinary evidence_refs using the OUTER
test-planning handshake: current candidate/boundaries, selected cases and oracles,
commands, lifecycle/sharing decisions, cost, prerequisites and execution owners.
Identify which checks run now and which require the authorized release first;
required post-release checks stay assigned to release-verify, not silently waived.
""",
    "system-test": """\
Execute authorized end-to-end, runtime, integration, or system tests against the
actual intended candidate and boundary.  Verify prerequisites, fixtures, target,
identity, authorization, and observed behavior.  Do not substitute a planned case
or local mock for a required system observation, deploy to unblock a test, or use
production without authority.
Before execution, acknowledge the applicable integrated test plan and revalidate
its candidate, case selection, target and fixture assumptions. Record reuse or
the concrete mismatch in ordinary evidence_refs; resolve a required planning gap
through this stage's supported repeat, blocked or corrective replan outcome.
Run the planned retained suite, reconcile selected cases and cleanup outcomes,
and record command, candidate/target, scope and unrun checks. When fixtures changed,
check relevant repeatability; never blindly replay an uncertain external effect.
Verify execution location, remote framework availability and deployed/test revision
identity. A local pass cannot replace a blocked/unrun required remote check or
establish a combined full-suite pass; preserve its assigned owner and boundary.
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
Revalidate the integrated test plan for the release target. Retain the pre/post
check owners, commands/case selectors, independent expected outcomes, prerequisites,
execution versus target locations, remote test-definition revision where relevant,
setup/test/teardown, fixture isolation/sharing and cost, cleanup and stop conditions.
Reuse applicable tests; define additional checks only for changed boundaries or
coverage gaps. Retain this release test plan in ordinary evidence_refs, including
what release-check must establish before release and release-verify after it.

Use Release operation guidance to order remaining schema/data/service/cutover
work and establish its durable execution owner, observations, and recovery limits.
If earlier deployment/test prerequisites are still unmet, return an outer replan
with corrective work and retained evidence; let the script rerun the outer stages.
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
Check applicable execution-owner readiness and target-enforced concurrency
conditions. External release N/A does not waive current local candidate checks.
""",
    "release": """\
Perform the planned release only when the exact target, operation, authority, and
conditions are current.  Record operation/effect and artifact identity separately.
If release is genuinely non-applicable, record the concrete reason.  Reconcile an
uncertain external outcome before retrying; never replay a merge, push, deployment,
or promotion simply to complete the graph.
Use Release operation guidance: distinguish accepted/running from terminal and
verified; retain partial receipts and reconcile with supported provider lookup,
retry, parameter-binding, and conditional-mutation semantics before proceeding.
Check operation postconditions here, then return through this stage's Improve.
The script-selected release-verify owns final consumer behavior checks afterward.
""",
    "release-verify": """\
Verify the actual release and required deployed consumer/runtime behavior using
current target evidence.  Distinguish source synchronization, artifact identity,
operation receipt, and real consumer behavior.  A blocked or unknown post-release
check remains incomplete; preserve prior receipts and do not re-release blindly.
For local-only work, verify the current local candidate and consumer behavior;
external activation N/A does not make these checks N/A.
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
    "discovery": "repository/environment facts, initial-baseline evidence and classification, conventions, reuse findings, and material gaps",
    "research": "source-backed conclusions, uncertainty, and reuse recommendations",
    "spec": "behavior, acceptance, non-functional criteria, existing-spec reconciliation, failure boundaries, and consumer outcomes",
    "test-strategy": "independent test/risk strategy and required test boundaries",
    "plan": "dependency plan, readiness/done conditions, and correction routes",
    "prepare": "environment readiness evidence or its justified N/A disposition",
    "select-work": "the ready-item selection and prerequisite assessment",
    "step-plan": "the bounded item plan, conventions, checks, and diagnostic obligations",
    "test-spec": "test-first cases, independent oracles, and RED/GREEN definitions",
    "baseline": "baseline commands, observations, initial-baseline applicability, and pre-existing failure classification",
    "test-author": "new or refined executable tests and fixtures",
    "test-red": "the expected-RED control and its observed failure reason",
    "implement": "the scoped implementation, code contracts, diagnostics, and error behavior",
    "test-green": "focused GREEN evidence and any scoped repair",
    "test-refine": "post-implementation test refinement and oracle integrity",
    "regression": "regression, negative, compatibility, and recovery evidence",
    "document": "code and user/operator/project documentation updates",
    "skill-assess": "the reuse, update or creation decision, including a justified N/A",
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


BACKCHAIN_STAGES = frozenset({"spec", "plan", "step-plan", "carry-forward", "product-acceptance"})
TEST_DECISION_STAGES = frozenset({"step-plan", "test-spec", "test-author", "test-refine", "regression"})
TEST_FACILITY_HANDOFF = """\
Use the packet's Reusable test facilities guide. Read applicable selected skill
and MCP capability references; reuse, configure or extend existing frameworks,
helpers and supported facilities before defining the smallest missing facility.
Retain its definition locator, supported interface, readiness evidence or gap,
owner/prerequisites and revalidation conditions in ordinary evidence_refs and
repository test documentation. Carry relevant locators into item context and the
Improve child's context/notes. Planning names missing prerequisite work; the owning
authoring/configuration work implements and validates it before dependent checks,
within the assigned scope and expected check state. Discovery or readiness is not
test execution. Reopen the durable definition for later tests instead of inventing
another facility or assuming a named skill/MCP is available or authorized.
"""
TEST_DECISION_HANDOFF = """\
Reopen the packet's Current item test-decision source when present, alongside
the Run-wide test strategy source and initial item context. Keep applicable
prior decision locators and any justified revision in this result's ordinary
evidence_refs and durable test notes, so later stages can recover their basis.
Retain the accepted step-plan note/result locator and applicable coding-guidance
sections even when this later test decision becomes the packet's latest source.
State which decisions are retained, refined or superseded and why; replacing the
test strategy does not silently replace unrelated engineering decisions.
Missing decisions require scoped reassessment; recorded completion is not proof
that a selected harness, fixture or target remains usable.
"""
OUTER_TEST_HANDOFF = """\
Use the packet's OUTER test-planning handshake guide. Recover the latest done
system-test-author and release-plan records from root-owned accepted history
after the most recent accepted replan, when those producers have completed.
Earlier OUTER records are historical inputs to revalidate, not current plan or
pass authority; pending, repeat, and blocked results are not plan authority.
Review a pending producer proposal separately during its Improve handoff.
Read the selected results and relevant evidence_refs; retain their action/result
and durable plan locators in this result and the Improve child's context/notes.
At system-test-author or release-plan, create/reconcile the plan owned by that
stage; do not require a future producer's plan. At consumers, acknowledge which
plan applies and revalidate it for the current candidate and boundary before
relying on its tests. Recover a missing plan or use the supported incomplete or
correction outcome; never guess commands, erase required coverage, or deploy to
make a check available. A plan is not execution evidence. Material changes to
code, tests, fixtures, configuration or target invalidate affected observations;
retain prior receipts, identify and rerun affected checks through the authorized
route. Reuse unaffected evidence only with its identity and relevance established.
"""
BACKCHAIN_NATIVE_CALLS = {
    "plan": ("plan", "draft"),
}
BACKCHAIN_AUDIT_STAGES = frozenset(
    {"spec", "step-plan", "carry-forward", "product-acceptance"}
)


def _backchain_guidance(stage: str, *, improve_owner: bool = False) -> str:
    """Return host-mediated caller guidance without adding navigator state."""
    selection = """\
Follow the packet's Backchain planning guide for this stage's scoped outcome,
prerequisite and consumer review. Carry selected requirement sections and test
locators through the plan and existing result/context fields. Existing runs retain
their recorded mode. For a new v3 plan, current embedded adaptation remains the
compatibility default until an explicit run-note selection chooses
`source-aware-native`.

A `source-aware-native` call is allowed only when run notes identify an observed
selected Backchain `SKILL.md`, `backchain-caller/v1` resource for this action/stage,
`references/convergence.md`, and `prompts/convergence-review.prompt.md`, plus a selected
physical Until Loop root with its `SKILL.md`,
`references/runtime-ephemeral.md`, and `scripts/until_loop_ephemeral.py` capability.
Read the Backchain convergence resources and verify each selected identity and capability
before use. They must support the direct natural-language handoff under
`Backchain standalone Until Loop binding: <binding-id>` for a plan-only child where the
actual loaded Until Loop card starts its adapter, is the sole CLI caller, and returns the
exact terminal packet. Caller/v1 alone is insufficient; an observed old custom Backchain
loop is incompatible even when an Until Loop package is installed. Do not guess a sibling,
cache, or ambient Until Loop. A missing, stale, ambiguous, or incompatible selected resource
leaves the request incomplete/blocked with its recovery locator; there is no silent fallback.
This is host-judged semantic compatibility; the navigator does not machine-enforce it.

Preserve selected Backchain/Until Loop identities, original source/candidate identities,
resolved bases/locators, protected bounds, action ID/owner, exact
`Backchain standalone Until Loop binding: <binding-id>`, and receipt locations in
ordinary run notes, `evidence_refs`, and necessary work-item `context`. Backchain passes
dependency-specific review/fix/check work, plan candidate files, source/lens context,
and protected bounds to Until Loop. ShipLoop records opaque actual Until Loop terminal
evidence and Backchain domain evidence:
binding_id, owner, candidate input/output digests, resolved resources, opaque
`terminal_receipt`, domain_evidence, planning_gaps, execution_blockers, and
next_action. It does not interpret child runtime progress, own a counter, schedule
retries, or claim completion from an intermediate candidate. A structural plan, planned check,
or experiment that merely ran is not execution evidence or a passed experiment.
Material findings remain visible and cannot clear ordinary Improve.

The Until Loop child is plan-only: it may change the candidate plan and permitted planning
companions, but may not commit, push, merge, execute the project, or broaden scope.
"""
    if improve_owner:
        return selection + """\
Improve remains an independent broader review. It may inspect Backchain findings
and the returned candidate as ordinary parent inputs, but it does not request
Backchain passes, count them, or make a Backchain completion claim. Do not create
an `active_backchain` child, a nested Until Loop, a retry dispatcher, or a new
callback; a protected/out-of-scope change follows the existing blocked or
recovery route. If a dependency diagnostic is relevant, use a one-pass Backchain
primitive; do not start a whole Backchain→Until Loop child.
"""
    if stage in BACKCHAIN_NATIVE_CALLS:
        action, operation = BACKCHAIN_NATIVE_CALLS[stage]
        return selection + f"""\
When `source-aware-native` is selected for this stage, the current stage host may
request exactly one action `{action}` / stage `{operation}` within the packet's
scope. Backchain invokes the selected actual Until Loop for its dependency-specific
review/fix/check cycle using `Backchain standalone Until Loop binding: <binding-id>`.
Until Loop owns the callback handle, progress, its `required_trivial_reviews: 2` gate for
two consecutive distinct complete trivial/no-change dependency reviews, recovery, and
terminal transition; Backchain and ShipLoop do not copy that runtime or create another
controller.
Backchain returns opaque actual Until Loop terminal evidence only after the child reports
`complete` and its exact receipt is saved. A nonterminal, unresolved, or incompatible
child leaves this parent action incomplete and must not be submitted as a completed parent
action. Only that exact `complete` receipt plus final candidate identity and domain evidence
permits Backchain planning convergence. The draft is a proposed candidate; ShipLoop still owns
acceptance and lifecycle state.
"""
    if stage in BACKCHAIN_AUDIT_STAGES:
        return selection + """\
At this stage, request action `review` / stage `audit` only for a material
prerequisite ambiguity, pending/corrective dependency, or acceptance gap. Audit
is a read-only, one-pass diagnostic: it does not mutate a candidate, converge a
plan, replace consumer verification, or complete the parent action. If it reports
a material finding, route that finding to the current stage owner. Within explicit
authorized edit bounds, that owner may request exactly one action `repair` / stage
`revise`; it is another whole native Backchain operation with a dependency-specific
review/fix/check cycle in the selected actual Until Loop. Audit itself remains read-only
and does not start that child. A forbidden revision, nonterminal child, unresolved finding, or
incompatible selected package remains incomplete and must not be submitted as a
completed parent action.
"""
    return selection + """\
This stage has no native Backchain action. Keep relevant findings in ordinary
notes and route a material planning gap through its authorized owner.
"""


BACKCHAIN_GUIDANCE = _backchain_guidance("plan")


def _require_stage(stage: str) -> None:
    if stage not in DUTIES:
        raise ValueError(f"unknown navigator-v3 stage: {stage!r}")


def prompt(stage: str) -> str:
    """Return the single current producer instruction for a v3 graph stage."""
    _require_stage(stage)
    parts = [COMMON, DUTIES[stage]]
    if stage in TEST_FACILITY_STAGES:
        parts.append(TEST_FACILITY_HANDOFF)
    if stage in TEST_DECISION_STAGES:
        parts.append(TEST_DECISION_HANDOFF)
    if stage in OUTER:
        parts.append(OUTER_TEST_HANDOFF)
    if stage in BACKCHAIN_STAGES:
        parts.append(_backchain_guidance(stage))
    if stage in RECONCILIATION_STAGES:
        parts.append(SELECTED_CASE_RECONCILIATION)
    if stage in IMPLEMENTATION_STAGES:
        parts.append(IMPLEMENTATION_CONSTITUTION)
    parts.append(PROGRESS_REPORTING)
    return "\n\n".join(parts)


def improve_prompt(stage: str) -> str:
    """Return the actual Improve-skill handoff for a completed producer stage."""
    _require_stage(stage)
    backchain = _backchain_guidance(stage, improve_owner=True) if stage in BACKCHAIN_STAGES else ""
    coding_review = ""
    if stage in {"step-plan", "implement", "verify"}:
        coding_review = """\
Use the packet's Coding decision guide. Carry the accepted plan, proposed revisions
and selected practice/platform locators into the child's existing contract/review
notes. Read only applicable sections and compare decisions with independent
requirements and checks. Planning review concerns decisions and proposed checks;
implementation/verification review needs actual evidence. Keep the assigned edit
scope and expected check state; this guide adds no review loop or authority.
"""
    outer_handshake = OUTER_TEST_HANDOFF if stage in OUTER else ""
    test_facilities = TEST_FACILITY_HANDOFF if stage in TEST_FACILITY_STAGES else ""

    release_guard = ""
    if any(label == "Release operation guidance" for label, _ in STAGE_REFERENCES[stage]):
        release_guard = """\
Read and retain Release operation guidance and the current operation/evidence
locators. Review this stage's plan, readiness checks, or observed outcome within
its authority; Improve does not initiate or replay release effects for convergence.
Reconcile uncertain or partial outcomes without inventing provider guarantees.
Material candidate changes require corrective planning and affected revalidation.
External release N/A still requires applicable local candidate and consumer checks.
"""
    assessment = ""
    if any(label == "State and data assessment" for label, _ in STAGE_REFERENCES[stage]):
        assessment = """\
Review the packet's State and data assessment for the affected slice. Check actual
resource/consumer identity, transition correctness, workload criteria and applicable
release/recovery conditions against the proposed work and tests. At initial plan,
apply Initial-plan reconciliation; carry its selected source/test locators into
this child's contract and notes. Keep unknowns visible and use existing correction
routes for newly discovered effects. This is part of this Improve call.
"""
    baseline_guard = ""
    if stage in {"discovery", "baseline"}:
        baseline_guard = """\
For this discovery/baseline handoff, use the packet's Initial repository baseline
guide to review evidence, commands, and classification only. You may improve
run notes and repeat authorized checks, but may not edit product source, tests,
dependency definitions, or product configuration, install dependencies, provision
targets, or perform a repair/bootstrap to make the observation green. Keep an
expected-RED repair or missing-coverage bootstrap as evidence for its named
producer; a completed evidence review does not certify repository health.
"""
    return f"""\
This producer attempt has returned a result; its parent action now awaits Improve.
Invoke the selected actual Improve skill for {IMPROVE_SCOPES[stage]}.  Read the
selected skill card and follow the Until Loop runtime bound by that card.  Use the
parent-provided candidate scope, prior producer result, relevant lessons, expected
check state, allowed edits, authority, and evidence/return locators.

Follow the packet's Maintained requirements policy for the candidate's applicable
accepted product requirements. Read and retain requirement and test locators in
the child contract/review notes for cold recovery; preserve unaffected conditions
and relevant cross-cutting rules. Review material subclauses and intentional
supersession, not just feature names. Do not let code, a passing test or a draft
proposal silently redefine accepted intent; keep verification gaps visible.
Follow the packet's Reference handoff policy. Before the first review, carry
the actual selected requirement, test and relevant run-note locators into the
child's existing contract prose and review notes. Keep their package/repository/run
bases explicit; a parent packet alone does not populate the child's contract.
Use the packet's Requirements definition guide for affected quality criteria and
existing-spec reconciliation. Retain source and current-decision locators; check
measurability, preserved conditions, and unresolved targets within this scope.
Use the packet's Initial repository baseline guide when baseline evidence is
relevant. Retain its locator, command/result evidence, classification, and
readiness conditions in the child contract/review notes for cold recovery.

{baseline_guard}

{backchain}

{coding_review}

{assessment}

{outer_handshake}

{test_facilities}

{release_guard}

When the candidate concerns actor interactions, channels, incoming/outgoing events,
connection lifecycle, state ownership or UI, read the applicable Interaction design
guide sections, including UI-specific planning when relevant, and the current
baseline/delta, contract and UI-premise locators. Review acknowledgment/recovery and
deployment assumptions, plus component/interaction/skin, motion and design guidance
where a UI is affected. Keep planning reviews scoped to decisions and proposed
checks; later reviews require actual consumer evidence. Revalidate reused choices.
Apply UI planning ownership at the candidate's stage: check the selected-item
boundary and prerequisite supplier/disposition without demanding later-stage work.
Check UI ambition, credible reuse/upgrade estimates and existing-facility reuse
where a consequential UI choice is affected.
Carry reviewed replacement locators and their precedence through the existing
handoff when these decisions change.
Carry those locators into the child contract for cold recovery. This is conditional
review scope within the existing handoff, not another Improve run; do not invent
infrastructure or expand the assigned scope.

Treat the relevant work-item `context`, parent `evidence_refs`, plan notes, and
packet-selected reference locators as parent-supplied cold-context inputs. Reopen
and revalidate only the sources relevant to this candidate, then retain a compact
current locator, decision, rationale, and revalidation result in the child review
notebook. Do not replace those source locators with copied transcripts, a new child
ledger, or an unverified summary.

When this candidate selects, uses or changes a repository-local skill, carry its
repo index, selected entrypoint, effective input/default sources, applicable
product contract and validation locators from the parent's evidence/selection
note into this child's existing contract/review notes before the first review.
Review task fit, supported overrides, current defaults and preserved older uses;
for a split, check distinct triggers and retained consumers. Reuse of an unchanged
skill does not require an edit. A no-fit decision needs its inspected sources and
rationale. Missing execution or fresh-reader evidence stays untested. The host
authors this handoff; a successful runtime receipt alone cannot prove skill use.

For test plans, authored/refined tests, fixtures, suite wiring or test evidence,
read the packet's Repeatable test-suite guide. Carry the harness, case and suite
locators, the Run-wide test strategy source and Current item test-decision source
when present, with the pending producer's proposed changes,
into this child's contract/review notes. Review independent assertions,
setup/test/teardown (including justified stateless cases), sharing noninterference,
failure cleanup, repeatability, and focused/smoke/full-suite inclusion and cost.
Improve the tests themselves and rerun affected checks after edits within the
assigned stage's expected check state; authoring and expected RED do not require
future production behavior to pass. Keep unresolved coverage visible.
Include remote-resident definitions, framework availability, authorized invocation,
execution location and deployed/test revision evidence; a local pass does not
satisfy a required remote check.
Review selected facility definitions and skill/MCP references for actual reuse,
supported interfaces and readiness limits. Preserve their durable locators for
later tests; verify an owned new/changed facility before its dependent checks
without treating facility readiness as a passing product test.

Improve owns its own review iterations, evidence notebook, continuation, and
completion judgment.  Do not replace it with an inline review algorithm, copied
policy, ShipLoop review counter, child phase graph, or guessed runtime command.
The parent action remains pending while the child is active or blocked.  Resume a
recorded child through its authoritative state; do not initialize a replacement.
On accepted child completion, use the packet's parent return route to import the
bound evidence and lessons once.  Do not advance the SDLC graph yourself.

Ordinary child review notes retain candidate and scope identity; independent
reviewer availability, use, or permitted fallback; whether reused evidence still
applies; findings, current checks, and limits; and short decision and reference
locators for cold recovery. This is review-note guidance, not a synthetic receipt
schema or a new parent validation rule.

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
