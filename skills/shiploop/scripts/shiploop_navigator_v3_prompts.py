"""Prompt catalog for the navigator's script-owned SDLC traversal (protocol 4).

The navigator selects one producer step at a time.  After that producer has a
result, the runtime renders :func:`improve_prompt` and parks the parent action
while the selected Improve skill follows its own bound Until Loop runtime.
Neither prompt contains a copied Improve algorithm or a second review counter.
"""

from __future__ import annotations


SERIAL_INNER_CONTEXT = """\
Clear and then execute the prompt.

For an implement producer, select the chain route before choosing a context route.
While executing that producer, its bound mode and executor take precedence: parallel
chains retain their capacity and bypass this serial context boundary; serial
chains execute in the main context without spawning workers. Do not wrap a chain
in an extra worker. Both modes recover the existing attempt, never rerun start.
Serial chains may use only the callable-reset or manual-handoff route below.
Chain precedence ends at producer completion. Improve follows its own selected
context and ownership policy even when the historical chain binding remains.
For other serial INNER assignments where delegation is permitted, begin
in a fresh context. Retain the
CLI, repository, run-directory locators and exact Recovery command below in
durable host handoff material. Prefer a native fresh worker with no inherited
conversation, the required tools, and a return route to the live parent. Give it
this packet, selected skill locators and necessary durable references in the
existing workspace. Run one assignment worker at a time; the parent waits for
its result, verifies it and alone submits the ShipLoop callback. Keep one writer;
collect or confirm an existing owner stopped before replacement. Once fresh for
this assignment, do not clear again or delegate it again when this prefix repeats.
Use a same-conversation clear only if the host exposes an actual callable reset
and continuation route; then recover this same run. Printing `/clear` in a packet
does not invoke it. If neither route is usable, use the printed pause command and
give the user a durable handoff: clear through the host or open a fresh context,
run the Recovery command, then follow the printed Resume command. Do not claim
a clear or execute the pending assignment before that boundary is satisfied.
ShipLoop emits this instruction; the host performs the context clear.
"""


IMPROVE_INNER_CONTEXT = """\
Keep the invoking parent alive and follow Improve's selected context ownership.

Chain precedence ends at producer completion, even when the historical chain
binding remains. The fresh-context boundary belongs to the whole Improve
executor invocation, not the invoking parent and not individual review iterations.
Prefer the selected fresh native executor route; the parent retains collection,
verification and the exact parent-only continuation. Do not clear, replace or
wrap the live parent to satisfy the executor's freshness requirement. A generic
parent reset or manual handoff is not that fresh executor boundary.
Recover an existing child from its receipt and ownership record; collect or
confirm its owner stopped before any replacement. Once fresh for this invocation,
do not clear again or delegate the whole invocation again. If the selected route
is unavailable, use same-context execution only when its ownership policy allows
it and separate context was not explicitly required; otherwise keep this action
pending and report the missing capability. Retain the exact Recovery command
and child receipt locators for interruption recovery.
"""


# Run-level delegation (state key ``delegation``).  ``inline`` is the default
# for new CLI-created runs; ``ask-agent`` is the opt-in delegated route
# rendered by SERIAL_INNER_CONTEXT/IMPROVE_INNER_CONTEXT above and by the
# unmodified DUTIES text.  A run without the key keeps its recorded ask-agent
# behaviour, so catalog calls default to it.
INLINE = "inline"
ASK_AGENT = "ask-agent"
DELEGATIONS = (INLINE, ASK_AGENT)

# Improve runs after every result of a planning/contract stage and once after
# the carry-forward that leaves no work item pending (the navigator's pending-queue
# check).  Planning stages write the contracts later work is built on: a sentence,
# example or expected result there can look done and still be wrong.
PLANNING_REVIEW_STAGES = frozenset({
    "spec", "test-strategy", "plan", "step-plan", "test-spec",
    "system-test-author", "release-plan",
})

INLINE_ITEM_CONTEXT = """\
Clear and then execute the prompt.

Delegation: inline. This select-work packet opens a work item and is its only
INNER context boundary. Clear once here, then execute this packet and every
later INNER stage and Improve checkpoint of this work item in this conversation.
If the host exposes an actual callable context reset with continuation, use it,
then run the Recovery command below. Otherwise run the printed pause command and
give the user this handoff: clear through the host (for example `/clear`) or
open a fresh conversation, run the Recovery command, then the printed Resume
command. Printing `/clear` does not clear. A conversation that began with that
reset or recovery for this work item is already fresh: when this prefix repeats,
execute without clearing or pausing again. Do not hand this assignment to Ask
Agent or a native worker; this conversation is the only writer and alone submits
ShipLoop callbacks. Retain the CLI, repository, run-directory locators and exact Recovery
command in durable host handoff material.
"""

INLINE_STAGE_CONTEXT = """\
Continue in this context and execute the prompt.

Delegation: inline. This work item's context boundary was its select-work
packet. Execute this INNER stage in this conversation without clearing, pausing
for a clear, or handing it to Ask Agent or a native worker. This conversation is
the only writer and alone submits ShipLoop callbacks. After an unplanned reset
or lost context, run the Recovery command and continue from the reprinted packet.
"""

INLINE_IMPROVE_CONTEXT = """\
Keep the invoking parent alive and run this Improve invocation inline.

Delegation: inline. Run the selected Improve skill's whole invocation in this
conversation, in the exact Child workspace; its review iterations share this
context. Do not clear, hand off, or hand the invocation to Ask Agent or a native
worker. Run its reviews and checks in this conversation too; start no reviewer,
test-runner or executor agent unless the user asked for independent review.
This conversation is both executor and parent: the only candidate
writer until the runtime returns a terminal packet, then the sole submitter of
ShipLoop callbacks. Recover an existing child through its runtime's recovery route
(for the ephemeral runtime, the saved receipt's exact next_argv); start another
runtime only through the packet's stopped-child restart route. Retain the exact
Recovery command and child receipt locator for interruption recovery.
"""


def inner_context(delegation: str, stage: str, *, improve: bool) -> str:
    """Return the context prefix for an active INNER producer or Improve packet."""
    _require_delegation(delegation)
    if delegation == ASK_AGENT:
        return IMPROVE_INNER_CONTEXT if improve else SERIAL_INNER_CONTEXT
    if improve:
        return INLINE_IMPROVE_CONTEXT
    return INLINE_ITEM_CONTEXT if stage == INNER[0] else INLINE_STAGE_CONTEXT


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

# User-facing status display only: one plain purpose per stage and the INNER
# stages grouped for the item map.  Neither is a prompt, graph, or state.
STAGE_PURPOSE = {
    "intake": "confirm the request, boundaries and open questions",
    "discovery": "inspect the current repository, environment and baseline tests",
    "research": "resolve the unknowns that matter with evidence",
    "spec": "define required behavior and acceptance criteria",
    "test-strategy": "map requirements to the checks that will prove them",
    "plan": "build the dependency plan and the work-item queue",
    "prepare": "ready the development and test environment",
    "select-work": "confirm this work item is still the right next item",
    "step-plan": "plan this item's concrete changes and checks",
    "test-spec": "specify the tests this item needs before code changes",
    "baseline": "record the relevant checks before any change",
    "test-author": "write the tests the item's test spec calls for",
    "test-red": "run the new tests and confirm they fail for the right reason",
    "implement": "make the planned change",
    "test-green": "run the focused tests and confirm they pass",
    "test-refine": "tighten the tests against the actual implementation",
    "regression": "rerun the retained suites for regressions",
    "document": "update the documentation this change affects",
    "skill-assess": "decide whether a reusable skill or helper change is warranted",
    "skill-validate": "validate any skill or helper change against real inputs",
    "static-checks": "run formatting, lint, type and build checks",
    "verify": "verify the item against its acceptance criteria",
    "integrate": "integrate the candidate into the working branch",
    "integration-verify": "verify the integrated result and shared interfaces",
    "carry-forward": "record lessons and revise the remaining queue",
    "system-test-author": "prepare end-to-end and system tests",
    "system-test": "run end-to-end and system tests on the real candidate",
    "product-acceptance": "assess the product against the original outcome",
    "release-plan": "plan the release, rollback and checks",
    "release-check": "confirm release readiness without releasing",
    "release": "perform the planned release",
    "release-verify": "verify the release where consumers use it",
    "operations": "confirm monitoring, recovery and support readiness",
    "handoff": "write the final handoff with status and evidence",
}

INNER_GROUPS = (
    ("Plan", ("select-work", "step-plan")),
    ("Tests first", ("test-spec", "baseline", "test-author", "test-red")),
    ("Build", ("implement", "test-green", "test-refine")),
    ("Check", ("regression", "document", "skill-assess", "skill-validate",
               "static-checks", "verify")),
    ("Integrate", ("integrate", "integration-verify", "carry-forward")),
)

if set(STAGE_PURPOSE) != set(STAGES):
    raise RuntimeError("STAGE_PURPOSE must describe exactly the navigator stages")
if tuple(stage for _, group in INNER_GROUPS for stage in group) != INNER:
    raise RuntimeError("INNER_GROUPS must cover INNER exactly, in order")

# Rendered at these producer stages with the recursive-discovery locators.
ENVIRONMENT_DISCOVERY_REQUIREMENTS = {
    "discovery": "Mandatory for this stage's relevant environment reads.",
    "research": (
        "Mandatory while resolving relevant environment unknowns in this stage."
    ),
}

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
        ("Connected knowledge discovery", "project-knowledge.md#connected-knowledge-discovery"),
        ("Discovery evidence handoff", "project-knowledge.md#discovery-evidence-handoff"),
        ("Discovery investigation guidance", "research-loop.md#plan-the-investigation"),
        ("Service discovery guidance", "service-discovery.md#select-scope"),
        ("Current-system baseline guide", "current-system-baseline.md#establish-or-refresh"),
        ("Persistent project-context guidance", "project-knowledge.md#discover-persistent-context-before-planning"),
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
        ("Environment and source-return discovery", "environment-lifecycle.md#discover-before-planning-code"),
        ("UI planning ownership when applicable", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
    ),
    "research": (
        ("Connected knowledge discovery", "project-knowledge.md#connected-knowledge-discovery"),
        ("Discovery evidence handoff", "project-knowledge.md#discovery-evidence-handoff"),
        ("Discovery investigation guidance", "research-loop.md#plan-the-investigation"),
        ("Service discovery guidance", "service-discovery.md#select-scope"),
        ("Current-system baseline guide", "current-system-baseline.md#evidence-and-authority"),
        ("Bounded research guidance", "research-loop.md#recursive-discovery-and-experiments"),
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
    ),
    "spec": (
        ("Service discovery guidance", "service-discovery.md#verification"),
        ("Current-system baseline guide", "current-system-baseline.md#planning-and-review-handoff"),
        ("Behavior-model guidance", "behavioral-requirements.md#behavior-model"),
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "test-strategy": (
        ("Service discovery guidance", "service-discovery.md#verification"),
        ("Current-system baseline guide", "current-system-baseline.md#planning-and-review-handoff"),
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("System-test catalog guidance", "system-tests.md#catalog-shape"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "plan": (
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Current-system baseline guide", "current-system-baseline.md#planning-and-review-handoff"),
        ("Dependency-planning guidance", "backchain-planning.md#dependency-audit"),
        ("Git-history investigation guide", "project-knowledge.md#investigate-git-history-for-planning"),
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
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Current-system baseline guide", "current-system-baseline.md#planning-and-review-handoff"),
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("Git-history investigation guide", "project-knowledge.md#investigate-git-history-for-planning"),
        ("Parallel-chain guide", "parallel-chain.md#parallel-implementation-chains"),
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
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Parallel-chain guide", "parallel-chain.md#parallel-implementation-chains"),
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Implementation constitution", "testing-and-documentation.md#implementation-constitution"),
    ),
    "test-green": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Iteration and verification guidance", "testing-and-documentation.md#iteration"),
    ),
    "test-refine": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
    ),
    "regression": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "document": (
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
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
        ("Service discovery guidance", "service-discovery.md#verification"),
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
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
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
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
        ("Consumer delivery guidance", "consumer-delivery.md#what-to-establish"),
    ),
    "release-plan": (
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
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
        ("Service discovery guidance", "service-discovery.md#observability-coverage"),
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
    ),
    "handoff": (
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
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
Progress: show the user this packet's ShipLoop status block unchanged, from its
begin marker through its end marker, at start/recovery and after each callback. Skip it only
when a host status hook already showed this same block (it arrives as a system
reminder). Do not paraphrase, reorder or extend it; add at most one line of your
own. Only the current owner reports overall progress. State labels say which action is assigned, not that work, tests, or
Improve iterations have occurred.  Describe Improve activity only from its own
observed records; do not infer a review count, completion percentage, or ETA.
Run to completion by default within scope and authority. Emit progress as an
intermediate update, then immediately continue the active packet's current owner
while authorized runnable work remains. Do not wait for acknowledgement, ask
whether to continue, or end the turn merely to deliver a report. Follow the exact
callback and its returned packet, including a bound Improve child; a producer's
done or a child's completion is not run completion. Respect explicit user stops
and paused/blocked/halted/done states. A user message about this skill, the loop,
its cost, or saying not to implement is a stop for product work: answer it, run the
current packet's pause command, and resume only on an explicit continue; resolve recoverable conditions through the
printed route and ask only for an actually missing decision, authority, or access.
"""


COMMON = """\
This packet assigns one script-selected SDLC producer step.  The script owns the
durable graph, action identity, and legal successor; you own the engineering
judgment, repository work, evidence, and result. Perform only the current step
before its callback, then immediately follow the newly returned packet.
Preserve unrelated work and do not choose a successor, advance parent state
yourself, or treat a previous packet as the current assignment.

Use the Stage readiness and completion guide for this activity's Definition of
Ready (inputs and prerequisites) and Definition of Done (scoped output and due
evidence). Definition complete, tests planned, tests authored and tests passed
are different claims; retain later-phase verification without claiming it now.

Read the current repository, run state, applicable instructions, and relevant
durable lessons before relying on earlier notes.  Treat Git history, plans, tool
descriptions, and prior results as context to recheck, not authority or proof.
Use actual observations for test, build, integration, release, and consumer
claims.  Keep scope, target authority, artifact identity, operation effects, and
consumer behavior distinct.  A missing prerequisite, permission, access, or
trustworthy check is unresolved or blocked; it is not a successful N/A.
Blocked means work this stage cannot do: a missing target or account, a missing
approval, or a command with no replacement available inside the stage. A retained
command that does not run what it claims (for example a test path the runner does
not expand) is a documentation fix made in this stage, then rerun, not a blocker.

For identity or access discovery, use supported non-mutating probes and
sanitized evidence. Normal supported tool-managed authentication and tool
configuration metadata without session material remain allowed. Builders and
reviewers must not read, decode, retain, or report local authentication,
session, or credential-store contents.

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
campaign in this result. Only planning results (spec, test-strategy, plan,
step-plan, test-spec, system-test-author, release-plan) and the carry-forward that
leaves no work item pending get an actual Improve-skill handoff; every other result
is accepted on this step's own checks and the graph advances directly. Where this
guidance mentions this action's Improve checkpoint, handoff or review at another
stage, keep that evidence in evidence_refs for the single end-of-work Improve
instead. Run only the checks this step's change needs. When this step changes no
product file, its check is the named command, its exit code and its required output
substrings: record them, cite the earlier accepted stage that ran the same command,
and do not reread history to repeat it.
"""


SELECTED_CASE_RECONCILIATION = """\
Selected-case reconciliation: in the existing plan/results, classify every
selected case as passed, failed, blocked, not-run, or justified N/A, preserving
required gaps. Source, HTTP, or DOM structure alone cannot close a selected
rendered interaction; retain the observed rendered action/outcome or leave it
incomplete.
Reconcile each affected requirement clause with its case or existing verification
record, required surface and due phase, actual checked surface, current candidate,
status and evidence. A pass at a different surface is supporting evidence, not
closure. Preserve cases not yet due with their phase, owner and prerequisites;
they need not pass early, but missing already-due evidence remains incomplete.
Check the original selected inventory for dropped clauses/cases; do not claim
all requirements met while required observations remain unrun.
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


# One rubric for writing and reviewing code.  Implementation-stage packets,
# the static-checks quality loop and the end-of-work Improve focus all carry
# this exact text, so no packet names the rubric without also defining it.
CODE_CRAFT = """\
Code craft. Write for the next maintainer, a person or a model, who opens one
file cold with no run history. Every rule serves that reader.
1. Match the house. The repository's error types, validation helpers, docstring
   style and logging come first; record any justified departure. Add no
   dependency, option or fallback without a present need.
2. Fail at the door. A function reachable from outside its module (exported
   API, CLI handler, request or event handler, callback) checks its arguments
   before any effect: required values present, type and shape, range or allowed
   set, and consistency between arguments. Reject with the house error type,
   naming the argument, the constraint and the received value (redacted when
   sensitive). Code called only by validated code may trust its caller; say so
   once where that is not obvious. Never swallow an error or substitute a
   success default; keep the original cause when rethrowing.
3. State the contract where it lives. A new file opens with one or two lines on
   its purpose. A public function's docstring gives purpose, argument
   constraints, return, errors raised and side effects. In a body, comment only
   what the code cannot say: why this approach, an invariant, a workaround and
   its trigger, a removed approach that must not return.
4. Spend tokens on information. Delete comments that restate a name, signature
   or the next line. No banners, change history or commented-out code. Prefer a
   precise name to a comment and one authoritative explanation to several.
5. Small, not thin. KISS and YAGNI limit features and abstractions. They never
   remove an argument check, an error path or a contract docstring.
6. Make failure diagnosable. Check a response's contract, not only transport
   success. Before mutation or cleanup, keep the context that explains a
   failure: operation, relevant IDs, expected versus observed. Errors name the
   operation and that mismatch. Reuse the existing debug switch for short,
   redacted state summaries at major actions, with no diagnostic work while it
   is off. Keep secrets and duplicate stack traces out of user-facing messages.
7. Write text that can be translated. User-facing messages go through the
   repository's message catalog or i18n helper when one exists; otherwise keep
   each message one whole sentence with named placeholders, never assembled
   from fragments, so it can be externalized later. Format numbers, dates,
   currency and plurals through locale-aware APIs. Keep log text, error codes
   and machine identifiers stable and untranslated.
"""


# The static-checks quality loop runs on the Until Loop bound to the selected
# Improve card.  ShipLoop writes these three texts into the loop contract
# verbatim; the Until Loop script counts iterations and ends the loop, and
# ShipLoop checks the saved terminal packet against them before accepting.
QUALITY_LOOP_LIMIT = 3

QUALITY_ITERATION = """\
One quality iteration over this work item's change. Scope: the change
inventory in context, plus tests for those files.
1. Checks. On the first iteration, run the step plan's focused tests and the
   selected formatting, lint, type, build and static-analysis checks, recording
   each command and exit code. Later iterations start from the previous
   iteration's final check results in the handoff.
2. Inventory. List every new or changed public entry point in scope: exported
   function, CLI handler, request or event handler, callback.
3. Trace. For each entry point, walk one valid, one boundary and one invalid
   input through the code, branch by branch, to its return value, raised error
   or side effect. Compare each path with the accepted step plan and
   requirements, and record a one-line trace per path. A path that is wrong,
   unhandled or untested is a finding; add a test for an untested path.
4. Review against the Code craft rubric: each entry point's argument checks and
   contract docstring, then the rest of the change for missing error paths,
   silent failures, comments that restate code, stale comments, dead code, and
   user-facing text that is concatenated or bypasses the repository's catalog.
5. Classify. Material: wrong behavior on a traced path; a missing or wrong
   argument check, contract, error path or test; a failing check; a misleading
   comment. Trivial: wording, ordering, a sharper name. Do not reopen a finding
   an earlier iteration fixed unless its code changed again.
6. Fix every finding within scope, changing the work and never a check or its
   expected result. If anything changed, rerun the step 1 checks once and
   record the results in the handoff.
Classify this iteration trivial only when it found no material finding.
"""

QUALITY_EXIT_CONDITION = (
    "A complete iteration found only trivial findings or none, applied them, and "
    "the step's focused tests and static checks pass on the final candidate."
)

QUALITY_REPEAT_CONDITION = (
    "Repeat while the latest iteration fixed a material finding and its checks ran. "
    "Stop cancelled when iteration " + str(QUALITY_LOOP_LIMIT) + " still finds a "
    "material finding, naming it. Stop blocked when a finding cannot be fixed within "
    "the scope or authority in context, or a required check cannot run."
)


DUTIES = {
    "intake": """\
Establish the requested outcome, repository and run boundaries, explicit user
constraints, authority limits, consumers/entry points, known risks, and open
questions.  Distinguish facts from assumptions and identify what discovery must
establish before planning, testing, implementation, or release work is trusted.
Retain permitted source hints and ambiguous internal terms for discovery: relevant
team/workspace, channels, internal sites/docs, private repositories and owners.
Sanitize hints for their audience; sensitive locators belong only in an authorized
knowledge home, not automatically in ordinary or public project notes.
Hints are leads, not verified definitions or access; missing hints do not require
a separate questionnaire when available evidence can resolve the question.
State where the result will be visible and when. In an isolated run the opened
source checkout stays at its starting snapshot until the final return, and an
outcome that lives in a deployed target (an org, a site, a store) exists only
after release; say both in this result so a long INNER run is not read as idle,
and do not call a source-level check the user's requested outcome.
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
Use Discovery investigation guidance after the baseline: check its plan triggers
first and again when evidence conflicts or dependencies emerge. When one applies,
retain the plan and its outcome in the existing note: question, evidence route
and order, owner, permitted effects, shared time/attempt bound, and stop condition.
Otherwise take the direct path when inspection suffices.
Use Connected knowledge discovery for internal terms, background, requirements
and decisions beyond the checkout. Actively find relevant available MCP readers
and use scoped search/read/resource access, following hits to supporting content;
Slack/Teams, internal sites/design docs and private Git are examples. Resolve
terms and conflicting claims with provenance, preserve access/coverage gaps and
safe evidence locators, and keep private queries/content off public surfaces.
An information reader is not automatically a product runtime dependency.
Use the Current-system baseline guide after the initial repository baseline.
Read README first; reuse/revalidate an adequate current-system account or recover
one from relevant docs, code/tests and authorized read-only observations. Retain
its as-of identity, coverage/conflicts, exact source locators and durable home in
a run note or retrievable immutable revision; include the selected baseline in
evidence_refs. A missing ShipLoop index does not mean a new system. Keep incoming
changes separate and leave consequential gaps unready for dependent work.
Use Service discovery guidance to assess owned observability for affected local
or remote flows, reusing existing event owners and sinks. When service boundaries
matter, trace consumer needs through business services to actual MCP/API/runtime
capabilities, identities and current schema/state. Safe scoped authorized reads
may resolve gaps; unavailable or partial observations are not absence. Select
relevant cache/invalidation and async questions without inventing infrastructure.
For unproven access or caching, state the safe interim policy-enforced read route
or denial; privileged direct access is not a safe fallback. For a selected schema
or projection delta, name preserved state and the reconciliation/read-back check.
Turn unknown ownership or coverage into a scoped probe and conditional file/test
change; gate only the work that actually depends on the missing evidence.
If a selected flow depends on asynchronous work, identify or record as unknown
its processor/recovery owner and durable acceptance-versus-completion boundary;
a status poller alone does not establish them. Gate that dependent flow only.
For retained application state, follow Service discovery guidance's Runtime state
placement section. Establish the current target and effective identity, then pass
that resolved target to dependent remote reads. Distinguish discovery operator, deployed runtime and end
user; explicitly retain any unknown relevant role or authority and its affected
consumer.

Before handoff, use Discovery evidence handoff: ensure the index links to the exact
decision-note section, then reopen
that link and its actual observations or receipts as a fresh reader would.
Retain explicit evidence_refs for the consumer, with scoped prerequisites and
due revalidation.
""",
    "research": """\
Resolve material unknowns with repository, primary-interface, or otherwise
appropriate evidence.  Connect each conclusion to its source, uncertainty,
affected requirement, consumer, prerequisite, reuse choice, and verification
need.  Assess relevant skills, MCP servers, libraries, and environment patterns
for actual fit and support; discovery alone is not successful use or authority to
install a dependency.  Leave unsupported questions open.
Use Connected knowledge discovery to resolve internal vocabulary and material
context gaps through relevant available MCP/internal readers. Open supporting
content rather than trusting snippets; retain authority, scope and safe source
locators in the existing evidence handoff. Keep evidence readers distinct from
runtime dependencies and do not disclose private context through public searches.
Use Discovery investigation guidance to reuse or revise the current question
frontier. Check its plan triggers first and again as evidence conflicts or
dependencies emerge; retain any triggered plan and outcome. Use the direct path
only when no trigger applies and direct investigation suffices. Verify the
Discovery evidence handoff before passing conclusions onward.
Research consequential quality-target and feasibility unknowns from existing
contracts and appropriate evidence; measured baselines do not choose user policy.
Reopen the selected current-system baseline and resolve its consequential gaps.
Retain the prior as-of account and record corrections/new evidence separately;
observations or synthetic fixtures cannot choose approved product intent.
For affected service choices, use Service discovery guidance to resolve current
state, zero-copy/cache tradeoffs, permission-aware invalidation, async recovery,
and observability gaps with discriminating evidence. Reuse native facilities;
retain unknowns and their actual dependent work in the indexed decision note.
Exit criteria: this stage is finished only when every load-bearing assumption is
listed in that decision note with a disposition. An assumption is load-bearing
when a plan decision, consumer or acceptance check would change if it were false.
Each one is evidenced (its source locator), probed (the read or command and its
observed outcome) or open (the check that would settle it, why it was not run
here, and its first affected consumer). A recalled fact is not evidence, and an
inconclusive probe leaves its assumption open. An empty list is valid when stated.
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
Separate independently verifiable clauses and their required observation surfaces;
keep bundled behaviors visible even when they share one requirement ID. Definition
completion establishes criteria, not implementation or test success.
Read the selected prior current-system baseline as well as accepted requirements.
Define the incoming delta with concrete preserved/changed behavior and retain
both source-section locators and evidence limits for planning and Improve.
For selected service boundaries, specify current authority, freshness versus
revocation, incremental state preservation, async completion/recovery, and owned
event coverage. Use Service discovery guidance to make these contracts verifiable;
mark inapplicable concerns briefly instead of adding services to fill a template.
""",
    "test-strategy": """\
Create a risk-based test and verification strategy from the specification before
code.  Name independent expected outcomes, local/unit/integration/system checks,
negative cases, fixtures/data, environment and authorization needs, and the
owner/boundary for each required check.  Distinguish planned checks from executed
evidence and identify meaningful expected-RED controls where test-first work is
applicable.
Allocate each clause to a case or existing verification record with its required
surface and due phase, owner and prerequisites. Record local support separately
from required consumer observations; do not narrow a behavior list to a render smoke.
Map applicable new and preserved non-functional criteria to checks and their
environment/workload prerequisites; missing evidence or access is not N/A.
Read the Repeatable test-suite guide. Select the major harnesses and suite entry
points now; reuse a prior-run harness only after revalidating its current fit.
Use Target-native test selection to connect discovered remote code/test assets
and the actual deployment gate to evidence-backed suite selections or exclusions.
Consider supported platform/library testing systems and available browser tools
by required capability rather than product name. Record their roles, fit,
availability and prerequisites; distinguish inspection from retained assertions.
Where relevant, consider curl or an existing HTTP/API client, Chrome DevTools or
equivalent inspection, and Playwright or equivalent browser automation; these are
capability examples, not a mandatory tool checklist. For browser-based UI criteria,
plan browser actions and expected visible outcomes; HTTP success alone does not
validate them. Apply the Consumer testing guide and retain access gaps.
Link the durable strategy note in ordinary evidence_refs, with the selection
rationale, fixture lifecycle, suite entry points and revalidation conditions.
Retain exact focused, smoke, and full-suite commands, inclusion rules, expected
cost and environment/fixture prerequisites. After this stage one file owns the
suite commands (name it, e.g. the repository's testing doc); plans and later notes
point at it rather than restating commands, and a stale command sentence elsewhere
is a plan defect to fix, not a second source of truth. Store each command in a
fenced code block, never in a Markdown table cell: an escaped `\\|` in a cell becomes
a literal pipe, matches nothing and can still exit 0. A passing command names the
test IDs or cases it ran. Plan durable regression tests, not
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
Use the selected prior baseline and incoming-spec sections to plan checks for
new and preserved behavior. Unknown existing semantics need discovery before
asserting a preservation target; old passing evidence is not a current pass.
Use Service discovery guidance for affected cache authorization/invalidation,
remote reconciliation, async recovery and observability checks. Map each relevant
contract to independent outcomes and its real observation boundary; fixture
results do not prove live permissions, event delivery or operator log access.
""",
    "plan": """\
Create a dependency-aware delivery plan from desired outcomes back to required
producers.  Order readiness, test, implementation, integration, documentation,
and release work so consumers do not run before their prerequisites.  Define
ready/done conditions, candidate scope, check evidence, authority boundaries,
and correction routes.  Do not use the plan to imply unrun tests or authorized
external operations.
Reopen the discovery evidence handoff. Distinguish researchable unknown contracts,
owner/access gaps and known selected setup prerequisites. Name the first affected
consumer of each gap; retain independent research and conditional planning as
eligible under their own prerequisites when another boundary is blocked.
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
design/test facilities.

After creating the initial steps, submit this producer result to its mandatory
actual Improve handoff. The plan remains a draft until
that loop completes; dependent work waits. Link the created plan and any execution
graph in evidence_refs so Improve reviews their actual contents. Do not schedule
an extra review stage or claim the loop ran. Keep these as ordinary notes, not
new result fields.

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
Reopen the selected current-system baseline and incoming change spec. Demonstrate
use through before/after decisions and preservation checks. Carry their exact
sections, gaps and revalidation conditions in evidence_refs and affected item
context; plan durable documentation work when recovery exists only in run notes.
Reopen the Repository knowledge index and current service decision sections.
Use Service discovery guidance to map accepted choices to affected schema/config,
query/cache, worker/status, business/UI, logging, tests and operator files only as
needed. Order their actual prerequisites and checks. Retain exact current note
locators and revalidation conditions in evidence_refs and item context; earlier
stage references are not automatically replayed in every later packet.
Before finalizing work-item IDs, check the draft once for coherent implementation
increments. Split deliverables when they need different prerequisites, expose a
useful intermediate contract/artifact, or can be implemented and checked
independently. Merge fragments that share prerequisites and an implementation
boundary without yielding a useful independently checkable state. No minimum
task count, planning-time quota, or mandatory scaffolding item is needed.
Keep preservation and negative requirements as checks on affected work unless
they require their own change. The inner loop already plans, tests, documents,
reviews and integrates each item; do not duplicate these stages as work items.
Keep genuinely cross-item or later-environment checks at their required boundary.
For each dependency, name the supplier and the concrete output/state the consumer
needs. Distinguish authoring an artifact from applying it in a running environment;
a runtime integration check may need both while independent code authoring does
not. Shared topic, list order or a shared file alone is not a causal dependency.
Record independent branches and file/resource conflicts separately in ordinary
plan notes; isolated workspaces alone do not establish safe parallel execution.
ShipLoop executes the ordered queue one item at a time. Put actual prerequisites
before consumers and carry their readiness checks in each item's existing context.
Return the complete ordered `work_items` array using only `id`, `title` and optional
`context`, and link the plan note in `evidence_refs`. Cover every approved outcome,
including required independent work with no downstream consumer. A plan note
alone does not populate the execution queue. A small change may use one item.
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
Revalidate the current script-selected work item in queue order. Confirm its
dependencies, scope, owner, relevant lessons, expected outcomes, and prerequisites
are current. The script does not choose among dependency-ready items. If this
item lacks a prerequisite, return blocked with the concrete missing producer or
correction need; do not skip it or advance to carry-forward to repair the queue. Reopen the item's compact
`context` and relevant plan/evidence locators, then revalidate their stated
conditions before relying on an earlier convention or environment decision.
""",
    "step-plan": """\
Turn the selected item into a bounded implementation plan.  Open the result
summary with one sentence naming the concrete change and the checks that will
prove it; the status display shows that sentence.  Name target files
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
For a plan with dependency-independent implementation steps, create and review
its initial steps and graph here for the default parallel chain, even when an
initial serial prefix will release those branches later. A serial chain remains
an explicit user or host-limit selection. Give every graph direct dependencies,
readiness and completion criteria,
shared-resource exclusions and the integration node. Link the graph's exact path
and content digest in existing plan notes/evidence_refs. This producer's mandatory
actual Improve loop must review the created steps and graph before they are used
for execution. Use the Parallel-chain guide for late creation or revision;
planning never starts the dispatcher or expands this item's scope.
Give every completion criterion a confirmation: `<condition>. Confirm by:
<command, observation, or inspection>; pass when <expected result>.` It must pass
the two-people test: two people running it separately would be forced to agree.
State whether the condition must be exercised or whether inspection is
sufficient. Give content criteria (docs, changelogs, test coverage) a
command-checkable confirmation, such as a search for required terms, so they are
re-observed rather than recalled. Mark a criterion that no available check can
confirm as `Confirm by: unconfirmable here — <what would confirm it>` rather
than dropping it. When the item adds or changes a public entry point, include
this criterion: each such entry point checks its arguments and carries a contract
docstring (Code craft 2-3). Confirm by: inspecting the diff for each entry point
and running its rejection tests; pass when every entry point has both.
When a check relies on an external oracle (golden, fixture, or
snapshot), confirm that the oracle agrees with the task.
Use the Repository-local skill guidance. Reopen the repo's current skill index or
README/AGENTS links, even if earlier context reported no fit: a preceding item may
have created or evolved a skill. Prefer unchanged reuse with supported inputs and
defaults. Record the selection or no-fit rationale in the linked plan/evidence
note; retain the entrypoint, effective inputs/default sources, product contract,
validation locators and revalidation condition in ordinary evidence_refs. Keep
later decision changes in these notes, not edits to the script-owned work queue.
Label every pinned value that exists so a check can replay an exact path (fixed
dice, seed data, a sample click) as a source-check fixture, and name the runtime
control separately (for example, two die values the player can change, with the
pinned values as the documented first path). Implementation must not turn a test
fixture into the product's only behavior.

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
Reopen this item's selected prior-baseline and incoming-spec sections from context.
Revalidate scope/freshness, retain preserved behavior and checks, and surface any
missing consequential source before dependent implementation.
For affected service work, reopen the indexed current contract and item-specific
sections from Service discovery guidance. Reconcile changed remote/local state,
authority, cache invalidation, async recovery and owned logging before dependent
edits; retain file roles, revalidation conditions and checks in the accepted plan.
A superseded note or prior successful probe cannot replace current evidence.
""",
    "test-spec": """\
Specify executable tests before production edits when applicable.  Map the item
to independent positive, boundary, and failure assertions, fixtures, and command
paths.  Define what the baseline/expected RED should prove, what focused GREEN
will prove after implementation, and how regression coverage prevents weakening
the oracle.  A test specification is not execution evidence.
Preserve every assigned clause and its required surface and due phase. Specify
the action and expected observable outcome for each distinct behavior, not only
that its page loads. Link later-phase procedures without claiming they ran here.
For each new or changed public entry point, specify one rejection case per
constraint it checks (missing, wrong type or shape, out of range), asserting the
error type, the named argument and unchanged state.
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
Author the specified rejection cases for each public entry point; they are
executable tests, not comments.
Retain tests and fixtures in the repository. Register each case in the full
regression route and applicable focused entry points; decide smoke membership
independently without duplicating tests. Follow the Repeatable
test-suite guide for setup/teardown, safe fixture sharing, and rerun instructions;
verify discovery selects the cases rather than merely recording their paths.
For remote-resident cases, retain/version the remote definitions and registration
with their authorized installation/invocation prerequisites.
Authoring is complete only when selected clauses have executable check bindings
or justified reproducible manual procedures at their required surfaces. Keep
unavailable execution prerequisites and later-phase observations pending.
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
Write first: list the paths this step plan creates or changes, write those files,
then run the item's named focused tests once. Read history or earlier reviews only
when a test fails or a concrete open question needs a specific section; history
before the first edit belongs to plan review, not to implementing a listed file set.
Reopen Target-native test selection when actual local/remote code, configuration,
dependencies or delivery route changes invalidate the earlier test decision.
Apply the planned behavior and the Code craft rubric below.  Do not claim
verification from an edit alone.
Exit criteria: the accepted step plan's completion criteria are this action's
exit criteria. It is finished only when you have confirmed each one as far as
this environment allows.
(1) Before editing, record for each criterion the command or inspection that
confirms it and what counts as a pass. Use its `Confirm by:` method when it has
one. Existing tests, check scripts, golden or fixture files, and thresholds belong
to the checks: change them only when a criterion says to.
(2) Confirm with what is already present. Never download, install, or fetch a
tool, runtime, or dependency to confirm a criterion. Record the best available
evidence and recommend what would confirm it.
(3) Stay within the item. If satisfying a check would make the result do or claim
something the item does not ask for, leave that check failing and report the
discrepancy.
(4) After your last edit to any file, rerun every check in one pass; only that
pass counts. When a check fails, change the work, not the check, and rerun them all.
(5) Stop on exactly one: every criterion confirmed or inspected, or reported
`unconfirmable` when the accepted plan already marks it `Confirm by: unconfirmable
here`, and none failed → outcome done; a criterion proven unachievable → outcome
blocked, naming it for plan revision rather than a blind retry; the same check
still failing after 3 genuine fix attempts → outcome blocked with that criterion
failed. A criterion is proven unachievable only when (a) it contradicts another
criterion, the item, or a protected file, shown by a check after all compatible
work is done and with the existing behavior kept at the conflict point; (b)
confirming it needs a tool, runtime, access, or authority that is absent, for a
criterion the plan did not already mark `Confirm by: unconfirmable here`; or (c)
satisfying it would exceed the item.
Report each criterion's check, the observed output from the final pass, and its
level (`confirmed`, `inspected`, `failed`, `not_run`, or `unconfirmable`), plus
discrepancies and recommendations, in the result summary or a linked evidence note.
Use the Coding decision guide to reopen the accepted plan and only its relevant
practice/platform sections. Check current code, versions and consumers before
reuse or augmentation. Retain justified revisions in the linked note; a new
prerequisite or authority boundary uses the existing correction route.
When the accepted step plan says no parallel chain, or the work-item context says
its steps write the same tree, use one writer in the execution checkout and do not
search for or bind a parallel chain; cite that plan or context locator in the result.
For a reviewed graph with safe dependency-independent implementation steps, use
the parallel-chain guide and bind this action to the default parallel
mode when the selected Plan Dispatcher and Ask-Agent contracts are compatible
and observed native slots are available. Record a concrete
compatibility, capacity, resource, readiness, or recovery blocker if that route
cannot start; use serial mode only for an explicit user or host limit. Parallel
mode uses native Ask-Agent; serial mode executes one ready step in the main
context without spawning agents. Bind parallel capacity to the observed
user/host native-slot limit, not its fallback default; an independent branch may
become ready after an initial serial prefix. Both use external sibling worktrees and
the same verified acceptance transition. Ask-Agent creates parallel worker
worktrees; orchestration verifies and adopts them, imports worker-local results,
prepares and checks the combination, merges into the invoking branch, then
accepts the step and removes its worktree. Retain conflicts and cleanup blockers;
never repeat accepted work because removal failed. Keep observable combined status; only
accepted steps are done. Continue until every required step is accepted and the
combined return is verified, or retain an explicit incomplete blocker. Finish
before this action's normal completion callback and Improve checkpoint.
On the initial frontier and every returned event, claim and start every listed
candidate that is actually safe up to the packet's available capacity. Refresh
immediately after each callback. Do not wait on a native reconciliation,
preparation, verification, or collection while an independent safe worker can
start; defer only a candidate with a concrete recorded blocker.
For service changes, apply the accepted current contract and relevant Service
discovery guidance. Revalidate target state and authority before effects; preserve
unrelated remote fields and existing operational owners. Unresolved cache access
or async completion semantics require their recorded safe fallback or correction.
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
Use Target-native test selection to reassess affected native suites and prior
exclusions against the actual local/remote changes and remaining test gates.
Refine cases and executable tests using the code that now exists while preserving
independent specification-based expectations.  Cover changed failure behavior,
debug on/off behavior and safe diagnostic context where relevant.  Correct an
oracle only with an independent reason; do not retrofit tests to the implementation
solely to obtain green.
Reconcile the original clause/case inventory: explain every removed or narrowed
case, surface change or phase reassignment with an independent requirement or
correction basis. Preserve missing consumer coverage as pending, not a local pass.
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
Use the Current-system baseline guide to retain recovered observations and
accepted deltas in durable product docs, preserving their distinct evidence status
and the prior as-of baseline. Update README/index links to the selected homes.
Maintain the indexed service decision note with accepted contracts, affected
files, check evidence, operational owners and revalidation triggers. Follow Service
discovery guidance to keep current and superseded choices distinguishable; do not
leave the only usable handoff inside transient results or chat.
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
Purpose: run this work item's quality loop on the bound Until Loop. ShipLoop
wrote the loop contract; the Until Loop script counts iterations and decides
when the loop ends; you execute each iteration and report it honestly.
Inputs: the Quality loop lines below (Until Loop card, start command, contract,
packet paths), the change inventory, and the ShipLoop lint block if present.
Do:
1. Read the bound Until Loop card in full once per context and follow it. Start
   the run with the printed command. Do not edit, retype or extend the contract.
2. Execute each returned iteration exactly as its work says, then call its done
   command. Save every returned packet from stdout to the printed latest-packet
   path, so a reset can recover the run through its next_argv. Continue until
   the runtime returns complete or stopped.
3. Save the terminal packet, byte for byte from stdout, to the printed terminal
   path and list that path in evidence_refs.
Report: done when the loop completed; blocked when it stopped, naming the
unresolved findings for plan revision. Summarize the entry-point inventory, each
trace that found an issue, the fixes, and the final check commands with exit
codes. ShipLoop refuses this result unless the saved terminal packet matches the
contract and outcome. State any required unrun check and why it could not run.
A ShipLoop lint block is supporting output, not this step's evidence: read it,
keep or revert any auto-fix it names, and still run the step's own checks inside
the loop.
""",
    "verify": """\
Verify the complete work item against its acceptance criteria and current evidence.
Check evidence applies to the current candidate, command, configuration and target;
stale, missing or skipped required evidence is incomplete. Use the authoritative
acceptance criterion, keeping diagnostic scores separate from that decision.
Use the Coding decision guide to compare the actual diff and affected consumers
with the accepted plan, justified revisions and selected practice/platform checks.
Preserve any required real-boundary gap; a pattern name or tool pass is not proof
of the behavior it did not exercise.
Check the static-checks quality loop's entry-point inventory against the actual
diff; an entry point missing from it has not been traced or reviewed.
Check the implement result's per-criterion receipt against each completion
criterion of the accepted step plan, and independently rerun or inspect each
criterion's confirmation. Do not accept the item when a confirmable criterion
failed or was not confirmed; name those criteria. A criterion reported `inspected`
or `unconfirmable` whose `Confirm by:` required execution means the step contract
cannot be met here: treat it as blocked for planning, not as accepted. A blocked
result with a proven-unachievable criterion goes back to planning (plan revision
or replan), not to a blind retry.
Reconcile tests, static checks, documentation, error behavior, diagnostics,
dependencies, and known limitations.  Refresh checks affected by material changes
and retain failures or blocked boundaries honestly.  This is work-item acceptance,
not an assertion that integration or release has happened.
Use Service discovery guidance for the item's selected service and observability
contracts. Verify the due outcomes, including safe fallback and failure cases;
separate local simulation from required remote readback, permission enforcement,
completion and event retrieval. Keep later-phase checks explicitly pending.
""",
    "integrate": """\
Perform only authorized Git/worktree integration for the candidate.  Inspect
actual diffs, branches, conflicts, identities, and combined interfaces.  Preserve
user work and keep run-time state, raw logs, credentials, and generated artifacts
out of product commits and returns.  Do not infer a merge, commit, push, or
deployment from a plan or command attempt.  If implement used a bound chain,
confirm its finish commit is an ancestor of the execution checkout HEAD and
record it; otherwise assemble or commit this item's candidate in the execution
checkout under workspace and repository policy, or record a justified no-op.
The original branch is returned only at the final workspace return.
""",
    "integration-verify": """\
Verify the assembled integrated candidate with the affected shared interfaces,
tests, and consumer-facing behavior.  Recheck evidence invalidated by merge or
conflict-resolution edits.  Separate a local integrated result from remote
delivery, and route a concrete integration failure to correction rather than
claiming that individual passing components establish the combination.
""",
    "carry-forward": """\
Read the full ordered queue before revising future work. Preserve every
still-required pending outcome, including unrelated work with no consumer.
Explain removals, merges or supersession against approved scope in the linked
plan note. A completed prerequisite invalidated by new evidence needs corrective
work and revalidation before its consumer; do not rewrite past completion evidence.
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
Carry the selected prior baseline, incoming delta and updated durable knowledge
locators forward. Preserve historical snapshots and pending persistence work;
new observations do not silently replace approved intent or old evidence.
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
Each new test file names the requirement or test IDs it covers in its opening
lines, and shared test helpers check their arguments.
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
Distinguish verified product criteria from pending release verification. Cases
not yet due may remain pending with their owner and prerequisites so release can
proceed; failed or missing already-due checks require correction. Readiness for
release is not a claim that every requested consumer behavior has been observed.
Identify missing product work, stale evidence, or delivery prerequisites and route
them honestly.  Acceptance does not itself execute a release or prove a remote
consumer boundary.
Reconcile new and preserved behavior against the selected prior baseline and
incoming spec. Check durable knowledge and remaining gaps; a recovered description
or planned check alone does not establish product acceptance.
""",
    "release-plan": """\
Create an authorized release/recovery plan: target and candidate identity,
permission, prerequisites, user impact, rollback, monitoring, pre/post-release
checks, and stop conditions. List every operation the user-visible outcome needs as
a named step with its exact command and its authorization status: the deploy
itself, and each separate access or visibility change (for example assigning a
permission set, activating an app or tab) and each browser session a consumer
check needs, with the selected browser tool. A step that an existing approval does
not cover is a pending approval named now, not a gap found at release-check.  Distinguish source return, artifact publication,
deployment, promotion, and consumer verification.  A plan does not authorize or
perform an external operation; a required target or authority gap is blocked.
Revalidate the integrated test plan for the release target. Use Target-native
test selection for this actual payload and deployment/promotion operation,
including any revised gate. Retain the pre/post
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
For isolated runs, source return occurs at release or handoff once no Improve
child is active. Use an authorized delivery route from the execution checkout if available.
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
For a browser surface, identify the usable consumer entry after authentication,
account/target, visible feature and actual action/outcome for each required clause.
Retain non-secret routing state; require app chrome/branding only when specified.
An embedded feature can satisfy its accepted boundary. Source or local test passes
cannot discharge an unobserved required deployed interaction.
""",
    "operations": """\
Verify applicable operational readiness: monitoring, alerting, logging/diagnostic
access, recovery ownership, support documentation, cleanup, and revalidation
needs.  Record a justified N/A only after assessing the actual operational
boundary.  Do not represent a plan or configuration file as evidence the service
is observed and supported in operation.
Reopen the Repository knowledge index and current observability coverage note.
Use Service discovery guidance to check authoritative event owners, existing
sinks and operator retrieval, including successful/failed logins where applicable.
Close only evidenced owned gaps; do not duplicate provider logs or treat every
failure as an incident. Preserve required audit failure and recovery policy.
""",
    "handoff": """\
Prepare an honest final handoff with source, test, integration, release, consumer,
and operational status; evidence locators; limits; blockers; follow-up work; and
revalidation needs.  Reconcile durable project documentation and product-return
receipts where applicable.  Do not transform an intent, stale green result, or
conversational summary into completion evidence.
Verify that current system knowledge, accepted changes and unresolved limits
survive outside transient run notes. Preserve the prior baseline's as-of account
and verify durable README/index links from the returned project documentation home.
Use Service discovery guidance to retain current service decisions, source and
check locators, ownership, unresolved boundaries and revalidation conditions in
indexed project documents. Verify those locators are usable by a fresh reader;
work-item context and earlier result references alone are not a durable index.
""",
}


IMPROVE_SCOPES = {
    "intake": "the scope, authority, consumer, and unanswered-question record",
    "discovery": "repository/environment facts, initial-baseline evidence and classification, conventions, reuse findings, and material gaps",
    "research": "source-backed conclusions, uncertainty, and reuse recommendations",
    "spec": "behavior, acceptance, non-functional criteria, existing-spec reconciliation, failure boundaries, and consumer outcomes",
    "test-strategy": "independent test/risk strategy and required test boundaries",
    "plan": "the newly created steps and dependency graph, readiness/done conditions, and correction routes",
    "prepare": "environment readiness evidence or its justified N/A disposition",
    "select-work": "the ready-item selection and prerequisite assessment",
    "step-plan": "the newly created bounded steps and any parallel or serial execution graph, conventions, checks, and diagnostic obligations",
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
locators through the plan and existing result/context fields. The only Backchain
call route is `source-aware-native`; ShipLoop carries no embedded Backchain mode.

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

The Until Loop child is plan-only when invoked by Backchain for dependency analysis:
it may change the candidate plan and permitted planning companions, but may not
commit, push, merge, execute the project, or broaden scope. These restrictions
belong to that Backchain child, not the separate Improve executor's authority.
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
Through `source-aware-native`, the current stage host may
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
        raise ValueError(f"unknown navigator stage: {stage!r}")


def _require_delegation(delegation: str) -> None:
    if delegation not in DELEGATIONS:
        raise ValueError(f"unknown navigator delegation: {delegation!r}")


# Inline runs replace only the chain-specific paragraphs of these duties; the
# ask-agent text above stays the single source for the delegated route.
_INLINE_DUTY_PARAGRAPHS = {
    "step-plan": ("""\
For a plan with dependency-independent implementation steps, create and review
its initial steps and graph here for the default parallel chain, even when an
initial serial prefix will release those branches later. A serial chain remains
an explicit user or host-limit selection. Give every graph direct dependencies,
readiness and completion criteria,
shared-resource exclusions and the integration node. Link the graph's exact path
and content digest in existing plan notes/evidence_refs. This producer's mandatory
actual Improve loop must review the created steps and graph before they are used
for execution. Use the Parallel-chain guide for late creation or revision;
planning never starts the dispatcher or expands this item's scope.
""", """\
For a plan with more than one implementation step, record its ordered steps here
for linear execution in this conversation: each step's direct dependencies,
readiness and completion criteria, and the checks that show it is done. Link the
step list in existing plan notes/evidence_refs. This producer's mandatory actual
Improve loop must review the steps before they are used for execution.
Delegation is inline: do not create a Plan Dispatcher execution graph or plan
parallel worker branches; planning never expands this item's scope.
"""),
    "implement": ("""\
When the accepted step plan says no parallel chain, or the work-item context says
its steps write the same tree, use one writer in the execution checkout and do not
search for or bind a parallel chain; cite that plan or context locator in the result.
For a reviewed graph with safe dependency-independent implementation steps, use
the parallel-chain guide and bind this action to the default parallel
mode when the selected Plan Dispatcher and Ask-Agent contracts are compatible
and observed native slots are available. Record a concrete
compatibility, capacity, resource, readiness, or recovery blocker if that route
cannot start; use serial mode only for an explicit user or host limit. Parallel
mode uses native Ask-Agent; serial mode executes one ready step in the main
context without spawning agents. Bind parallel capacity to the observed
user/host native-slot limit, not its fallback default; an independent branch may
become ready after an initial serial prefix. Both use external sibling worktrees and
the same verified acceptance transition. Ask-Agent creates parallel worker
worktrees; orchestration verifies and adopts them, imports worker-local results,
prepares and checks the combination, merges into the invoking branch, then
accepts the step and removes its worktree. Retain conflicts and cleanup blockers;
never repeat accepted work because removal failed. Keep observable combined status; only
accepted steps are done. Continue until every required step is accepted and the
combined return is verified, or retain an explicit incomplete blocker. Finish
before this action's normal completion callback and Improve checkpoint.
On the initial frontier and every returned event, claim and start every listed
candidate that is actually safe up to the packet's available capacity. Refresh
immediately after each callback. Do not wait on a native reconciliation,
preparation, verification, or collection while an independent safe worker can
start; defer only a candidate with a concrete recorded blocker.
""", """\
Delegation is inline: execute a reviewed multi-step plan directly, one step at a
time in dependency order, in the execution checkout in this conversation. Do not
bind an implementation chain or dispatch Ask Agent or native workers; chains are
available only when the run's delegation is ask-agent. Confirm each step's
readiness before starting it and its completion checks before starting a
dependent step. Keep observable per-step status in the result; only verified
steps are done. Continue until every required step is done and verified, or
retain an explicit incomplete blocker, before this action's normal completion
callback and Improve checkpoint.
"""),
}
for _stage, (_delegated, _inline) in _INLINE_DUTY_PARAGRAPHS.items():
    if DUTIES[_stage].count(_delegated) != 1:
        raise RuntimeError(f"navigator {_stage} duty lost its delegated chain paragraph")

_PLANNING_HANDOFF = (
    "Preserve this planning pass's key reference statements, decisions, constraints and acceptance "
    "context in its summary and registered material. At plan and step-plan, consolidate applicable "
    "upstream material for a fresh execution context as supporting references, not a replacement "
    "assignment or a restatement of the user prompt. The dispatch step task/ready/done contract remains "
    "the sole worker directive. Register every produced planning file and required source as an absolute "
    "reference in evidence_refs; an unrecorded conversation is not a planning handoff."
)
_INLINE_PLANNING_DIRECTIVE = (
    "The dispatch step task/ready/done contract remains the sole worker directive.",
    "Each reviewed step's task/ready/done criteria remain its sole execution directive.",
)


def duty(stage: str, *, delegation: str = ASK_AGENT) -> str:
    """Return one stage duty with the run's implementation-route paragraph."""
    _require_stage(stage)
    _require_delegation(delegation)
    text = DUTIES[stage]
    if delegation == INLINE and stage in _INLINE_DUTY_PARAGRAPHS:
        delegated, inline = _INLINE_DUTY_PARAGRAPHS[stage]
        text = text.replace(delegated, inline)
    return text


def prompt(stage: str, *, delegation: str = ASK_AGENT) -> str:
    """Return the single current producer instruction for a navigator graph stage.

    The navigator always passes the run's delegation; the ask-agent default
    keeps catalog renders identical to runs recorded before the setting existed.
    """
    _require_stage(stage)
    _require_delegation(delegation)
    parts = [COMMON, duty(stage, delegation=delegation)]
    if stage in PRELUDE or stage in {"step-plan", "test-spec"}:
        parts.append(_PLANNING_HANDOFF if delegation == ASK_AGENT
                     else _PLANNING_HANDOFF.replace(*_INLINE_PLANNING_DIRECTIVE))
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
        parts.append(CODE_CRAFT)
    parts.append(PROGRESS_REPORTING)
    return "\n\n".join(parts)


# Inline runs have no dispatcher steps, execution graph or worker packets; the
# ask-agent wording above stays the single source for the delegated route.
_INLINE_IMPROVE_REPLACEMENTS = (
    ("the newly created bounded steps and any parallel or serial execution graph",
     "the newly created bounded steps and their ordered dependencies"),
    ("user prompt nor a second worker directive. The dispatch step's task/ready/done\n"
     "contract remains the sole assignment.",
     "user prompt nor a second directive. Each reviewed step's task/ready/done\n"
     "criteria remain its sole assignment."),
)


PLANNING_REVIEW_FOCUS = """\
Planning review focus. This planning result is
the contract that later stages build on and that no other review sees until the
end. Look for these conditions and fix them within scope:
- a step, example or expected result that cannot be replayed exactly: name the
  concrete inputs, values, identifiers and sample interactions;
- an expected result or check that a weaker stand-in would pass: a hardcoded
  value, a missing assertion, a title-only test, or an absent required name;
- a documented command that does not run what it claims on the target runtime:
  run it once and record the exit code and the cases it executes;
- a required requirement, test ID or case dropped or weakened compared with the
  prior accepted version;
- a missing prerequisite, wrong order or unowned verification in the steps.
Do not reread history or rerun a check already recorded green at this commit
unless a finding depends on it. A pass that finds none of these is trivial.
"""


END_REVIEW_FOCUS = """\
End-of-work code review focus. Across every executed work item's change, trace
each new or changed public entry point with a valid, a boundary and an invalid
input, then review the change against the rubric below. Fix violations within
scope. A pass that finds no material violation is trivial.

""" + CODE_CRAFT


def improve_prompt(stage: str, *, delegation: str = ASK_AGENT) -> str:
    """Return the actual Improve-skill handoff for a completed producer stage."""
    _require_delegation(delegation)
    text = _improve_prompt(stage)
    if delegation == INLINE:
        for delegated, inline in _INLINE_IMPROVE_REPLACEMENTS:
            text = text.replace(delegated, inline)
    return text


def _improve_prompt(stage: str) -> str:
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
    plan_guard = ""
    if stage in {"plan", "step-plan"}:
        plan_guard = """\
Review the actual steps after their creation, including any linked execution
graph. Carry the plan/graph locators and current content identities into this
child's existing contract and review notes. Check direct dependencies, missing
suppliers, ready/done criteria, independent paths, joins, resource exclusions,
and integration/verification ownership. Recheck affected relationships after
material repairs. Keep the plan pending until this actual Improve loop completes;
structural validation or a Backchain result alone does not complete this handoff.
"""

    release_guard = ""
    if any(label == "Release operation guidance" for label, _ in STAGE_REFERENCES[stage]):
        release_guard = """\
Read and retain Release operation guidance and the current operation/evidence
locators. Review this stage's plan, readiness checks, or observed outcome within
its authority. Improve may perform deployments, MCP interactions and other release
operations already authorized for the current task and stage, with their required
checks. Do not repeat unchanged release effects merely to advance the review streak.
Reconcile uncertain or partial outcomes before retrying, without inventing provider guarantees.
Retry only when the reconciled state warrants it and the operation remains
authorized under the release guidance; retain the prior operation/receipt identity
and follow the provider's supported retry or idempotency procedure.
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
The selected Improve card supplies execution capabilities and the review loop.
The stage requirements below qualify this candidate and its authority.
Freeze selected staged/unstaged/untracked candidate paths and excluded unrelated
work in the existing child scope, or retain the exact inventory locator when large.
An empty initial commit or unmoved HEAD does not replace named untracked candidate
files with the latest commit's diff. Git history supplies context, not scope.

For identity or access discovery, use supported non-mutating probes and
sanitized evidence. Normal supported tool-managed authentication and tool
configuration metadata without session material remain allowed. Builders and
reviewers must not read, decode, retain, or report local authentication,
session, or credential-store contents.

Follow the packet's Maintained requirements policy for the candidate's applicable
accepted product requirements. Read and retain requirement and test locators in
the child contract/review notes for cold recovery; preserve unaffected conditions
and relevant cross-cutting rules. Review material subclauses and intentional
supersession, not just feature names. Do not let code, a passing test or a draft
proposal silently redefine accepted intent; keep verification gaps visible.
Reconcile each relevant clause's required surface and due phase with its actual
evidence. Review the current stage's Ready/Done criteria: a planning or authoring
review does not require future product checks to pass. Later verification reviews
must inspect due observations, not merely the proposed procedures.
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

{plan_guard}

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

For current-system recovery or affected product work, carry selected prior-baseline
and incoming-spec sections into this child's existing contract before review.
Check preservation, evidence/intent separation, consequential gaps and durable
retention within this candidate's scope; a package-guide link alone is insufficient.

Treat the relevant work-item `context`, parent `evidence_refs`, plan notes, and
packet-selected reference locators as parent-supplied cold-context inputs. Reopen
and revalidate only the sources relevant to this candidate, then retain a compact
current locator, decision, rationale, and revalidation result in the child review
notebook. Do not replace those source locators with copied transcripts, a new child
ledger, or an unverified summary.

For every planning-producing candidate, author coherent supporting reference
material with key accepted statements, decisions, constraints, acceptance context,
and exact source locators. It supplies planning-pass context; it is neither the
user prompt nor a second worker directive. The dispatch step's task/ready/done
contract remains the sole assignment. Register every generated planning file in
the producer result's `evidence_refs`. If this Improve result supplies a revised
`final_result`, preserve the prior registered references and add its new planning
files; do not discard evidence just because the reference material was consolidated.
Explicit local project documents may remain absolute references. A URL is a
reference-only citation until its needed material is supplied as a local artifact.

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

Follow the selected Improve card's review, commit and completion policies under
this binding's authority; preserve explicit task overrides and an existing child's
frozen contract. The parent owns acceptance, callbacks and workspace return.
For a RED-stage handoff, do not make production edits merely to turn the expected
RED green. For release/verification handoffs, reconcile an uncertain external
outcome rather than replaying it.
"""


if len(STAGES) != 34 or len(set(STAGES)) != len(STAGES):
    raise RuntimeError("navigator stage catalog must contain 34 unique stages")
if set(DUTIES) != set(STAGES) or set(IMPROVE_SCOPES) != set(STAGES):
    raise RuntimeError("navigator prompts do not cover the complete graph")


PROMPTS = {stage: prompt(stage) for stage in STAGES}
IMPROVE_PROMPTS = {stage: improve_prompt(stage) for stage in STAGES}
for _delegated, _inline in _INLINE_IMPROVE_REPLACEMENTS:
    if not any(_delegated in text for text in IMPROVE_PROMPTS.values()):
        raise RuntimeError("navigator Improve prompts lost a delegated-route phrase")


__all__ = (
    "ASK_AGENT",
    "COMMON",
    "DELEGATIONS",
    "DUTIES",
    "END_REVIEW_FOCUS",
    "ENVIRONMENT_DISCOVERY_REQUIREMENTS",
    "CODE_CRAFT",
    "IMPLEMENTATION_STAGES",
    "IMPROVE_PROMPTS",
    "IMPROVE_SCOPES",
    "INLINE",
    "INNER",
    "INNER_GROUPS",
    "OUTER",
    "PLANNING_REVIEW_FOCUS",
    "PLANNING_REVIEW_STAGES",
    "QUALITY_EXIT_CONDITION",
    "QUALITY_ITERATION",
    "QUALITY_LOOP_LIMIT",
    "QUALITY_REPEAT_CONDITION",
    "PRELUDE",
    "PROGRESS_REPORTING",
    "PROMPTS",
    "STAGE_PURPOSE",
    "STAGE_REFERENCES",
    "STAGES",
    "duty",
    "improve_prompt",
    "inner_context",
    "prompt",
)
