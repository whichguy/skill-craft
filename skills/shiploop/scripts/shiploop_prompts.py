"""Prompt catalog for the navigator's script-owned SDLC traversal (protocol 4).

The navigator selects one producer step at a time.  After that producer has a
result, the runtime renders :func:`improve_prompt` and parks the parent action
while the selected Improve skill follows its own bound Until Loop runtime.
Neither prompt contains a copied Improve algorithm or a second review counter.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import shiploop_stage_spec as stage_spec


SERIAL_INNER_CONTEXT = """\
Execute the prompt in a fresh context.

For an implement producer, select the chain route before choosing a context route.
While executing that producer, its bound mode and executor take precedence: parallel
chains retain their capacity and bypass this serial context boundary; serial
chains execute in the main context without spawning workers. Do not wrap a chain
in an extra worker. Both modes recover the existing attempt, never rerun start.
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
this assignment, do not delegate it again when this prefix repeats. If no fresh
worker is usable, execute the assignment in this conversation. Never pause for a
context clear: no packet, script or hook output can clear a host conversation,
and the host's own compaction manages its context.
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
# example or expected result there can look done and still be wrong.  Each accepted
# implement step has its own rule ("step"), whatever the planning review option says.
PLANNING_REVIEW_STAGES = stage_spec.with_improve("always")

INLINE_STAGE_CONTEXT = """\
Continue in this context and execute the prompt. Delegation: inline: do this stage here and submit its callback
yourself; never clear or hand it off. After lost context, run the Recovery command.
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


def inner_context(delegation: str, *, improve: bool) -> str:
    """Return the context prefix for an active INNER producer or Improve packet."""
    _require_delegation(delegation)
    if delegation == ASK_AGENT:
        return IMPROVE_INNER_CONTEXT if improve else SERIAL_INNER_CONTEXT
    return INLINE_IMPROVE_CONTEXT if improve else INLINE_STAGE_CONTEXT


# The two lines under every packet's first line, Improve packets included (owner, 2026-10-16: "the first line of each
# packet should say something like: read this file if you don't have context about prior paths and what you're doing,
# or if you're uncertain in any way ... point to the file and let the model inspect it and open subfiles from there").
# Each text is defined here once; the navigator prints them in render, packet_head and improve_packet, and nothing else
# in a packet says either again.  A model that lost its context reads the index first, so the pointer carries the
# absolute path of the run's context-index.md (a derived master index: shiploop_context_index).
OWNER_RULE = "Owner rule: concise and exact; no restating. Keep every command, path, ID and expected value."
INDEX_POINTER_PREFIX = "Lost context, or unsure of anything about this run? Read "
INDEX_POINTER_SUFFIX = (" first: it maps every file of this run and what it holds; open the file you need from there.")


def index_pointer(index_path: object) -> str:
    """The pointer line: the absolute path of the run's context-index.md, which maps every other file."""
    return INDEX_POINTER_PREFIX + str(index_path) + INDEX_POINTER_SUFFIX


# The graph and each stage's fixed considerations live in shiploop_stage_spec.
PRELUDE = stage_spec.PRELUDE
INNER = stage_spec.INNER
OUTER = stage_spec.OUTER

STAGES = PRELUDE + INNER + OUTER

# User-facing status display only: one plain purpose per stage and the INNER
# stages grouped for the item map.  Neither is a prompt, graph, or state.
# The status and narrative lines show the short goal; the packet's GOAL line prints the full one once (re-cut, 2026-10-11).
STAGE_PURPOSE = {name: row.short_goal for name, row in stage_spec.STAGE_SPEC.items()}

INNER_GROUPS = (
    ("Plan", ("step-plan", "test-spec")),
    ("Validate existing", ("validate-existing",)),
    ("Build", ("implement", "test", "document")),
    ("Verify", ("verify",)),
    ("Carry forward", ("carry-forward",)),
)

if set(STAGE_PURPOSE) != set(STAGES):
    raise RuntimeError("STAGE_PURPOSE must describe exactly the navigator stages")
if tuple(stage for _, group in INNER_GROUPS for stage in group) != INNER:
    raise RuntimeError("INNER_GROUPS must cover INNER exactly, in order")

# Rendered at these producer stages with the recursive-discovery locators.
ENVIRONMENT_DISCOVERY_REQUIREMENTS = {
    "discovery": "Mandatory for this stage's relevant environment reads.",
    "research": "Mandatory while resolving relevant environment unknowns in this stage.",
}
if set(ENVIRONMENT_DISCOVERY_REQUIREMENTS) != stage_spec.with_block("environment-discovery"):
    raise RuntimeError("ENVIRONMENT_DISCOVERY_REQUIREMENTS must match the stage table")

TEST_FACILITY_STAGES = stage_spec.with_block("test-facility")


# Keep stage routing declarative and package-relative.  The navigator renders
# these selected locators with the package reference directory; this catalog
# does not persist a second graph, decision ledger, or prompt copy.
STAGE_REFERENCES: dict[str, tuple[tuple[str, str], ...]] = {
    "intake": (
        ("Prior-run and recovery guidance", "project-knowledge.md#new-work-versus-recovery"),
        ("Delivery authority guidance", "delivery-authority.md#ask-at-the-first-concrete-boundary"),
    ),
    "discovery": (
        ("Discovery investigation guidance", "research-loop.md#plan-the-investigation"),
        ("Connected knowledge discovery", "project-knowledge.md#connected-knowledge-discovery"),
        ("Current-system baseline guide", "current-system-baseline.md#establish-or-refresh"),
        ("Service discovery guidance", "service-discovery.md#select-scope"),
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
        ("Discovery evidence handoff", "project-knowledge.md#discovery-evidence-handoff"),
        ("Environment and source-return discovery", "environment-lifecycle.md#discover-before-planning-code"),
        ("Delivery authority guidance", "delivery-authority.md#ask-at-the-first-concrete-boundary"),
        ("House-style guidance", "house-style.md#extract-the-house-style"),
    ),
    "research": (
        ("Access-readiness policy", "research-loop.md#early-access-readiness"),
        ("Connected knowledge discovery", "project-knowledge.md#connected-knowledge-discovery"),
        ("Discovery evidence handoff", "project-knowledge.md#discovery-evidence-handoff"),
        ("Discovery investigation guidance", "research-loop.md#plan-the-investigation"),
        ("Service discovery guidance", "service-discovery.md#select-scope"),
        ("Current-system baseline guide", "current-system-baseline.md#evidence-and-authority"),
        ("Bounded research guidance", "research-loop.md#recursive-discovery-and-experiments"),
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
    ),
    "spec": (
        ("Current-system baseline guide", "current-system-baseline.md#planning-and-review-handoff"),
        ("Behavior-model guidance", "behavioral-requirements.md#behavior-model"),
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("Service discovery guidance", "service-discovery.md#verification"),
    ),
    "test-strategy": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Service discovery guidance", "service-discovery.md#verification"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
    ),
    "plan": (
        ("Git-history investigation guide", "project-knowledge.md#investigate-git-history-for-planning"),
        ("Dependency-planning guidance", "backchain-planning.md#dependency-audit"),
        ("Initial-plan reconciliation", "requirements-definition.md#initial-plan-reconciliation"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("Delivery authority guidance", "delivery-authority.md#ask-at-the-first-concrete-boundary"),
        ("Namespace and placement guidance", "coding-practices.md#namespaces-and-placement"),
        ("Schema and storage guidance", "coding-practices.md#schema-and-storage"),
        ("Decision carry-forward guidance", "project-knowledge.md#carry-context-into-the-new-plan"),
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("UI planning ownership guide", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
    ),
    "prepare": (
        ("Environment preparation guidance", "environment-lifecycle.md#plan-preparation-before-its-first-consumer"),
        ("Workspace and return guidance", "workspace-lifecycle.md#entry-identity-and-storage"),
    ),
    "step-plan": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("House-style guidance", "house-style.md#write-the-match-contract"),
        ("Plan record guide", "plan-record.md#topics-the-item-touches"),
        ("Namespace and placement guidance", "coding-practices.md#namespaces-and-placement"),
        ("Schema and storage guidance", "coding-practices.md#schema-and-storage"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Parallel-chain guide", "parallel-chain.md#parallel-implementation-chains"),
        ("UI planning ownership guide", "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner"),
    ),
    "test-spec": (
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "validate-existing": (
        ("Baseline-test guidance", "execution-planning.md#baseline-tests-and-migrations"),
        ("Current-system baseline guide", "current-system-baseline.md#evidence-and-authority"),
    ),
    "implement": (
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("House-style guidance", "house-style.md#match-while-building"),
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Parallel-chain guide", "parallel-chain.md#parallel-implementation-chains"),
    ),
    "test": (
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "document": (
        ("Documentation guidance", "testing-and-documentation.md#documentation"),
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
    ),
    "verify": (
        ("Coding decision guide", "coding-guidance.md#select-guidance"),
        ("Test-case planning guidance", "testing-and-documentation.md#test-cases"),
        ("Service discovery guidance", "service-discovery.md#verification"),
        ("Workspace integration guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "carry-forward": (
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
        ("House-style guidance", "house-style.md#retain-the-house-style"),
        ("Persistent project-knowledge guidance", "project-knowledge.md#retain-learnings-for-the-next-invocation"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("Carry-forward mapping guidance", "carry-forward.md#mandatory-post-inner-mapping"),
        ("Reuse-before-build guidance", "research-loop.md#reuse-before-a-new-mechanism"),
        ("Repository-local skill guidance", "testing-and-documentation.md#reusable-product-skills"),
    ),
    "system-test-author": (
        ("System-test catalog guidance", "system-tests.md#catalog-shape"),
        ("Repeatable test-suite guide", "repeatable-test-suites.md#select-or-revalidate-the-harness"),
    ),
    "system-test": (
        ("System-test placement guidance", "system-tests.md#placement-and-dependency-rules"),
        ("Real-boundary test guidance", "testing-and-documentation.md#layers-and-real-boundaries"),
    ),
    "product-acceptance": (
        ("Consumer delivery guidance", "consumer-delivery.md#what-to-establish"),
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
        ("Behavior traceability guidance", "behavioral-requirements.md#traceability-and-review"),
    ),
    "release-plan": (
        ("Target-native test selection", "repeatable-test-suites.md#select-target-native-tests"),
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("State and data assessment", "requirements-definition.md#state-and-data-change-assessment"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
        ("Environment promotion guidance", "environment-lifecycle.md#carry-the-route-into-final-delivery"),
    ),
    "release-check": (
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Delivery completion guidance", "consumer-delivery.md#where-completion-is-enforced"),
    ),
    "release": (
        ("Delivery authority mapping", "consumer-delivery.md#map-authority-readiness-to-existing-fields"),
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
    ),
    "release-verify": (
        ("Consumer delivery evidence guidance", "consumer-delivery.md#evidence-and-limits"),
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
        ("Release operation guidance", "environment-lifecycle.md#release-operation-ownership"),
        ("Which checkout release-verify observes", "workspace-lifecycle.md#which-checkout-release-verify-observes"),
    ),
    "operations": (
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
        ("Service discovery guidance", "service-discovery.md#observability-coverage"),
        ("Service handoff guidance", "service-discovery.md#development-handoff"),
    ),
    "handoff": (
        ("Deployment and handoff guidance", "testing-and-documentation.md#deployment-and-handoff"),
        ("Workspace return guidance", "workspace-lifecycle.md#inner-assembly-and-final-return"),
        ("Current-system baseline guide", "current-system-baseline.md#retain-across-runs"),
        ("Service discovery guidance", "service-discovery.md#development-handoff"),
    ),
}


# Every OUTER duty names the plans it relies on (the OUTER test-planning handshake), and every stage that reuses or
# defines a test facility cites the facility guide; carry-forward records facility locators but defines none.
for _outer_stage in OUTER:
    STAGE_REFERENCES[_outer_stage] += (
        ("OUTER test-planning handshake", "repeatable-test-suites.md#outer-test-planning-handshake"),
    )

for _facility_stage in sorted(TEST_FACILITY_STAGES - {"carry-forward"}):
    STAGE_REFERENCES[_facility_stage] += (
        ("Reusable test facilities", "repeatable-test-suites.md#reuse-and-define-test-facilities"),
    )


PROGRESS_REPORTING = """\
Progress: do not reprint this packet's ShipLoop status block; it orients you.
The user sees the run's status through a host status hook where one exists. At
start/recovery and after each callback, tell the user at most one line of your
own: the item, the stage just finished and the stage now starting. Show the whole
block unchanged only when the user asks for the full status. At milestones a packet
also carries a ShipLoop narrative section; follow its first line, which says whether
you paste the narrative to the user as written or the host already showed it. Only the current owner reports overall progress. State labels say which action is assigned, not that work, tests, or
Improve iterations have occurred.  Describe Improve activity only from its own
observed records; do not infer a review count, completion percentage, or ETA.
Run to completion by default within scope and authority. Emit progress as an
intermediate update, then immediately continue the active packet's current owner
while authorized runnable work remains. Do not wait for acknowledgement, ask
whether to continue, or end the turn merely to deliver a report. Follow the exact
callback and its returned packet, including a bound Improve child; a producer's
done or a child's completion is not run completion. Respect explicit user stops
and paused/blocked/halted/done states. A user message that asks to stop or pause,
or says not to implement, is a stop for product work: run the current packet's pause
command, answer it, and resume only on an explicit continue. A question or comment
about this skill, the loop, its progress or its cost is not a stop: answer it
briefly and keep following the current packet. Do not pause on your own to ask
whether the run is worth continuing or to confirm the process for a small task;
the user's request already authorizes the run. Never end the turn while a ShipLoop
command is still running: keep each one in the foreground until it returns, and if
the host moves it to a background task, wait for that task in this same turn before
anything else. A `complete` that reruns tests can take minutes, and a headless host
ends the whole session when the turn ends, losing the callback. If a host keepalive
hook refuses to end the turn, its reason names this run's next command: run it and
follow the packet. Resolve recoverable conditions through the
printed route and ask only for an actually missing decision, authority, or access.
"""


# The requirement and reference-handoff rules: COMMON carries them, and the run reference file (shiploop_reference,
# section "requirements") carries them for every stage.
REQUIREMENTS_RULES = """\
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
Write temporary files (command output, a report you pipe into a tool) in the
packet's Scratch directory, not /tmp: /tmp is shared with other runs and
sessions, and a fixed /tmp name can read another run's file.
ShipLoop runs unattended: no one is watching and nothing arrives on standard
input. When a decision is open, take the default that best fits the request and
the recorded knowledge, record it as an assumption (the alternatives and why
this one) in the result's summary (only plan's result has an assumptions list),
and continue. When a step can only be done by a person (a sign-in, a
grant, an observation in a signed-in browser), record it as an open item in the
result, with who must do what and what they should report, and continue with
everything that does not depend on it. Only when nothing further can proceed
without the person, report blocked with `blocked_by` user (or access, for a
sign-in) and `awaiting`: `{"kind": "answer", "question": "...", "options": [...], "no_default": "..."}`
for a decision, or `{"kind": "present", "steps": [...], "report": "...", "no_default": "..."}`
for something only a person can do; `no_default` says why no recorded default
would do, and ShipLoop refuses a wait without it. Ask one decision per question,
in words the user can answer in one reply. The run then stops until the user's
own reply resumes it.

For identity or access discovery, use supported non-mutating probes and
sanitized evidence. Normal supported tool-managed authentication and tool
configuration metadata without session material remain allowed. Builders and
reviewers must not read, decode, retain, or report local authentication,
session, or credential-store contents.

""" + REQUIREMENTS_RULES + """\
Return the packet's concise producer result with a truthful outcome, summary,
and useful evidence locators. For relevant product work, include the selected
maintained requirement sections and test/evidence locators in the result's
existing evidence_refs so a later reader can recover them. If a required
source is missing, report the gap rather than inventing a locator or omitting it.
A justified N/A is still an output that states
what was assessed and why it does not apply. ShipLoop starts an Improve child
after planning results (spec, test-strategy, plan, step-plan, test-spec,
system-test-author, release-plan), after each accepted implement step, and after
the carry-forward that leaves no work item pending. Run only the checks this step's change needs. When this step changes no
product file, its check is the named command, its exit code and its required output
substrings: record them, cite the earlier accepted stage that ran the same command,
and do not reread history to repeat it.
"""


# What a producer packet prints instead of COMMON, REQUIREMENTS_RULES and PROGRESS_REPORTING (owner, 2026-10-11: "the
# full packet file looks far too verbose ... consolidate the language and deduplicate"). One line per rule a step can
# hit; the long texts stay whole in the run reference file (reference#rules, #requirements, #progress), so nothing is
# lost, and the blocked shapes are printed once, with the stage's outcomes.
STAGE_RULES = """\
RULES (each one fixes a failure live runs showed; the long form is reference#rules):
- Do only this stage, then run its callback; ShipLoop picks the next stage.
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.
- Run ShipLoop commands in the foreground, unpiped, and never end the turn while one runs.
- Temporary files go in RUN/scratch, never /tmp.
- Never read, keep or report credential-store or session contents.
"""

# Every INNER stage runs its work as one Until Loop that ShipLoop starts from a contract it wrote (shiploop_loops).  The
# renderer prints the /until-loop block and this one rule beside it, once per packet (packet re-cut, 2026-10-11), so no
# duty repeats it and a duty never names the loop's paths.

# Non-producer packets (Improve parent, paused, blocked) print this instead of PROGRESS_REPORTING.
PROGRESS_RULE = """\
Progress: tell the user one line per stage; describe Improve activity only from its own records. Keep each ShipLoop
command in the foreground and never end the turn while one runs. A question about the run is not a stop; a request
to stop or pause runs Pause. Long form: reference#progress.
"""


# An inline step-plan or carry-forward builds no execution graph, so it carries one optional audit line instead of the
# Backchain caller guidance (owner, 2026-10-11); the guide and the audit resource are printed with the packet's
# locators.
INLINE_AUDIT_STAGES = ("step-plan", "carry-forward")
INLINE_BACKCHAIN_AUDIT = """\
Optional: for a material prerequisite ambiguity or acceptance gap, request one
read-only Backchain review/audit (Backchain planning guide), then run the printed
`backchain-check` on your candidate and cite its receipt in evidence_refs.
"""


# How big a step is (owner, 2026-10-10: "do we ever want to scope down the size of a step so that we don't cram too much
# or too little in one step?"). The six live step plans of 2026-10-10 split an item by file type (product change, then
# "add the test"), and the test step was a no-op at implement every time because the tests were already written.
STEP_SIZING = """\
Size each step as one behaviour-level change that a named check proves. Give
every step the criteria IDs it satisfies (criteria) and the files it changes
(paths, a subset of the item's paths); each criterion is satisfied by some step.
Split a step when it holds two behaviours that can each be confirmed on their
own, when it crosses a module or layer boundary (the interface first, then each
side), when its task needs "and" between two outcomes, or when it is too large
to review and recheck in one pass. Merge a step that no check can confirm on its
own (half a rename, scaffolding nothing uses yet) into the step it serves. Tests
are not a step: the test stage writes them from the test spec after the last
implement step, so a step that only changes test files is refused unless the
whole item is tests. One change, such as a single bug fix or a mechanical rename,
is one step.
"""


# Stage-specific paragraphs, carried only by the stages the stage table names
# (blocks "interaction-design" and "work-items").
INTERACTION_DESIGN = """\
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
for cold recovery; do not start a nested review.
State and information lifecycle. For each piece of state the request involves,
decide and state, in proportion to the request: its authoritative owner and where
it lives; who may read it (information one user must not see, such as an opponent's
hidden game state or another person's record, stays off that user's client;
information a lone user could only misuse against themselves may stay on their
client); how simultaneous changes are resolved; what ends it (finished, abandoned,
expired) and what removes it; and which runtime quotas or limits it meets. For
personal or secret data, state where it is shown, stored and logged, how long it is
kept, and how it is removed. Map each to what the runtime and the project's own
layers already offer, from their documentation, configuration and code. Do not add
identity, sharing or persistence the request does not call for; when the request
leaves them open, take the default you would choose, record it as an assumption
in the result's summary, and continue.
Choose the simplest placement that meets the request: a single-user game or tool
with no shared or lasting state runs entirely in the client. Add server state,
identity, a store or a live channel only for a requirement that needs it, and use
the runtime's native storage, identity, cache, workflow and notification services
before building your own.
Simplicity removes machinery, never safeguards: at every placement, keep the
personal-data handling above, a server-side check on every action by a caller the
product does not control, validation and abuse limits on anonymous input, and a
record of every background or asynchronous failure that reaches whoever must act. For each hop, pick the lightest channel that meets the
freshness the request states: request/response; polling at a stated interval;
email or platform notification for changes hours apart; server-sent events,
WebSockets or platform push only when seconds matter. After a push, poll gap or
reconnect, read the authoritative state back. Cache only derived data, in the
runtime's cache, with an expiry that matches the staleness the request allows.
State each channel's and cache's cost against the runtime's quotas.
"""

WORK_ITEM_CONTEXT = """\
Where a plan creates or revises work
items, retain only the relevant compact locator, decision, rationale, scope, and
revalidation condition in existing plan notes and that item's `context`; retain
the supporting source locator in the ordinary `evidence_refs`. Do not copy source
transcripts, invent a decision ledger, or treat a context summary as proof.
"""


SELECTED_CASE_RECONCILIATION = """\
Selected-case reconciliation: classify every selected case in `summary` as passed, failed, blocked, not-run, or
justified N/A. Reconcile each affected requirement clause with its case, its required surface and due phase, the
surface checked, the candidate, the status and the evidence. A pass on a different surface only supports; Source,
HTTP, or DOM structure alone cannot close a rendered interaction. A case not yet due keeps its phase, owner and
prerequisites; missing evidence for a case already due stays incomplete. Check the selected inventory for dropped
clauses or cases. Never claim every requirement met while a required observation is unrun.
"""


RECONCILIATION_STAGES = stage_spec.with_block("reconciliation")


# One rubric for writing and reviewing code.  The code-craft stages' packets
# (implement, test, document, verify), the per-step Improve focus and the
# end-of-work Improve focus all carry this exact text, so no packet names the
# rubric without also defining it.
CODE_CRAFT = """\
Code craft. Write for the next maintainer, a person or a model, who opens one
file cold with no run history. Every rule serves that reader.
1. Match the house. The repository's error types, validation helpers, docstring
   style and logging come first; record any justified departure. Add no
   dependency, option or fallback without a present need. An argument that
   lets an existing unit serve this change instead of a copy is a present need.
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
5. Small, not thin. KISS and YAGNI limit features and speculative
   abstractions. They never remove an argument check, an error path, a
   contract docstring, or the rich UI interaction the plan calls for.
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
8. Put it where it belongs. New code lives in the namespace the step plan
   chose, with the narrowest visibility a present consumer needs. A new name
   must not collide with or shadow one in the shared space of any runtime it
   runs in (such as globals, an import path, a shell or a platform org) or in a
   library the code uses. No new generic bucket such as `utils`. Stored data
   follows the planned schema and storage policy.
9. Compose before you build. Before writing a new unit, evaluate reusing an
   existing one unchanged, composing existing ones, or augmenting one (a new
   argument, an extension point, or a shared piece extracted from existing
   code) while its current callers keep working. Augment only when the units
   share one meaning, not merely similar code: a near-copy of existing logic
   is a defect, and so is a parameter that fuses two different rules. State
   the option chosen and why in one line.
"""


# What a producer packet prints instead of CODE_CRAFT: one line per rule; the full rubric stays in the reference.


# The step exit criteria's stopping rule; test/shiploop-stage-spec.test.py pins every prose copy to this value.
_FIX_ATTEMPTS = str(stage_spec.GENUINE_FIX_ATTEMPTS)

# Delegation-specific paragraphs: the ask-agent text is in DUTIES; _INLINE_DUTY_PARAGRAPHS swaps in the inline one.
_STEP_PLAN_GRAPH = """\
11. **Execution graph.** Give each change that needs no other its own step (`deps` []), joined by a later step that
    needs both, so the parallel chain can run them together (serial only on an explicit user or host limit). For
    independent steps write the graph now, even behind a serial prefix: direct dependencies, readiness and completion
    criteria, shared-resource exclusions, integration node. Its path and content digest go in the summary and
    evidence_refs. Late creation or revision: Parallel-chain guide. Planning never starts the dispatcher.
"""
_STEP_PLAN_INLINE = """\
11. **Execution graph.** Record none: an inline run issues the steps one at a time.
"""
_IMPLEMENT_CHAIN = """\
7. **Chain.**
   - The step plan says no parallel chain, or the item context says its steps write the same tree: one writer in the
     execution checkout, no chain bound; cite that locator in the result.
   - Otherwise, for a reviewed graph with safe independent steps, bind the default parallel mode (Parallel-chain
     guide) when the Plan Dispatcher and Ask-Agent contracts are compatible and native slots are observed free
     (capacity is the observed user or host slot limit, not the fallback default). If it cannot start, record the
     concrete blocker (compatibility, capacity, resource, readiness or recovery). Serial mode only for an explicit
     user or host limit: one ready step in the main context, no agents.
   - Both modes use external sibling worktrees and one acceptance route: Ask-Agent creates each worker worktree; you
     verify and adopt it, import its results, check the combination, merge into the invoking branch, accept the step,
     remove the worktree. Keep conflicts and cleanup blockers; never repeat accepted work because removal failed.
     Keep the combined status observable. Only accepted steps are done.
   - On the first frontier and after every callback, refresh and start every safe listed candidate up to capacity (a
     branch may become ready after a serial prefix). Never wait on a reconciliation, preparation, verification or
     collection while an independent safe worker can start; defer only a candidate with a recorded blocker.
   - Before this stage's callback: every required step accepted and the combined return verified, or a recorded
     incomplete blocker.
"""
_IMPLEMENT_INLINE = """\
7. **Inline.** Do the one step on the packet's Step lines (task, paths, skills, check commands, lint command) in this
   conversation. Bind no chain and dispatch no worker.
"""
_VERIFY_ASSEMBLY = """\
8. **Assembly.** If implement bound a chain, confirm its finish commit is an ancestor of the execution checkout HEAD,
   record it, and inspect the combined diff, conflicts and shared interfaces between steps (Workspace integration
   guidance). Otherwise confirm the candidate is assembled in the execution checkout under workspace and repository
   policy. The original branch returns only at the final workspace return.
"""
_VERIFY_ASSEMBLY_INLINE = """\
8. **Assembly.** Confirm the item's candidate is assembled in the execution checkout under workspace and repository
   policy (Workspace integration guidance). The original branch returns only at the final workspace return.
"""


# The conditions the Improve child applies to a planning result (PLANNING_REVIEW_FOCUS, further down).  The spec and
# test-strategy duties hold the ones that apply to them, so a producer reads in its own packet what its result must
# meet (SPEC S-6).  One source: the child's list is the producers' list plus the condition on steps, which a spec or
# test strategy does not hold.
_REVIEW_FOCUS_ITEMS = (
    "a step, example or expected result that cannot be replayed exactly: name the\n"
    "  concrete inputs, values, identifiers and sample interactions",
    "an expected result or check that a weaker stand-in would pass: a hardcoded\n"
    "  value, a missing assertion, a title-only test, or an absent required name",
    "a documented command that does not run what it claims on the target runtime:\n"
    "  run it once and record the exit code and the cases it executes",
    "a required requirement, test ID or case dropped or weakened compared with the\n"
    "  prior accepted version",
    "a claim about what the runtime, platform or a library can do that a decision\n"
    "  depends on, with no primary-documentation source or probe result: check it,\n"
    "  and correct the plan where it is wrong",
)
_REVIEW_FOCUS_STEPS = "a missing prerequisite, wrong order or unowned verification in the steps"


def _focus_list(items: tuple) -> str:
    return "".join("- " + item + (";" if index < len(items) - 1 else ".") + "\n" for index, item in enumerate(items))


REVIEW_FOCUS_CONDITIONS = _focus_list(_REVIEW_FOCUS_ITEMS + (_REVIEW_FOCUS_STEPS,))

# The producers whose duty carries the review focus conditions; the navigator's Improve line says so for exactly these.
REVIEW_FOCUS_DUTY_STAGES = ("spec", "test-strategy")


def _duty_focus(number: int, where: str, product: str) -> str:
    """The numbered duty item that holds the planning review focus conditions, worded for this stage's own files."""
    rows = [" ".join(item.split()).replace("correct the plan", "correct the " + product)
            for item in _REVIEW_FOCUS_ITEMS]
    lines = [f"{number}. Before you submit, fix any of these in {where}:"]
    for index, row in enumerate(rows):
        lines.append(textwrap.fill(row + (";" if index < len(rows) - 1 else "."), width=117,
                                   initial_indent="    - ", subsequent_indent="      "))
    return "\n".join(lines) + "\n"


# How ShipLoop matches a listed test ID against the runner's output (``shiploop_test_counts.named``).  One sentence,
# restated by every duty and packet line that says a listed ID must be shown, so the rule is worded once.
ID_WORD_RULE = ("A listed ID counts only as its own word in a test's printed name (for example, a test titled `TC-4a` "
                "does not show `TC-4`: title it `TC-4 (a)`).")

# Placeholders duty() fills from the run: the Backchain item of spec and plan (by the run's Backchain passes option)
# and the item commit rule of document and verify (by the run's execution mode).
_BACKCHAIN_ITEM = "<<backchain item>>"
_ITEM_COMMIT = "<<item commit rule>>"

DUTIES = {
    "intake": """\
1. Map each sentence of the request to an outcome, boundary or open question in `summary`. Boundaries: repository and
   run scope, user constraints, authority limits, consumers and entry points, risks. Mark each fact or assumption.
2. Each open question: who answers it (discovery or a recorded default), what it blocks, what discovery must
   establish first.
3. List discovery's source hints in `summary` (team or workspace, channels, internal sites and docs, private
   repositories, owners, ambiguous terms). A hint is a lead, not a verified fact. Put a sensitive locator only in an
   authorized knowledge home. Ask no questionnaire for what evidence can resolve.
4. Name where the result must become usable; a request that names the target is the grant (Delivery authority
   guidance).
5. Say where and when the outcome is visible: an isolated run's source checkout stays at its snapshot until the
   final return, and an outcome in a deployed target exists only after release.
6. For an interactive product, list the open interaction and state questions: actors and how the runtime identifies
   them; shared state across people, devices or sessions; its lifetime and what ends it; what stays hidden from
   whom; what the runtime already provides. Answer from the request, else record the default and what it rules out.
7. A request that continues an earlier run follows Prior-run and recovery guidance.
8. Implement nothing; add no scope. `evidence_refs`: each source used.
""",
    "discovery": """\
1. Baseline first (Initial repository baseline guide): find the starting directory, its instructions and a safe
   command, then run the full suite on the unchanged checkout (the smoke suite if the full one is impractical).
   Choosing a command or citing an old pass does not count. `evidence_refs`: command, cwd, target, result, coverage
   limits, output file. No suite: record missing coverage.
2. Classify the baseline in `summary`: passed, failed, missing coverage, setup or access block, uncertain, or
   expected repair RED. Only a pass is healthy. Change no product file to turn it green. A failed baseline lets
   discovery finish and leaves dependent feature work unready.
3. Inspect Git and worktree state, instructions, code, tests, docs, consumers and project knowledge. Record in
   HOME/environment.md, each with a source locator and marked binding requirement, observed practice or proposal:
   - ## Targets and runtimes: development, test, integration and delivery boundaries; runtime and dependency
     versions;
   - ## Commands: linters, formatters, type checkers, test runners;
   - ## Platform facts: conventions, canonical code and test examples, MCP and API contracts, reusable libraries,
     house style (House-style guidance).
   Install and provision nothing.
4. Find how a change reaches its consumer (Environment and source-return discovery): whether the source-branch
   return triggers CI, a deploy or a publication, and whether it must precede a consumer check. Record route and
   uncertainty under ## Targets and runtimes. Inspecting a route authorizes no return, deploy or early handoff.
5. Locate existing specs and quality policies (scope, status in `summary`); screen the applicable non-functional
   requirements (Requirements definition guide).
6. Check the repository index, README and AGENTS for skill links before proposing an implementation
   (Repository-local skill guidance). Record fit or no fit under ## Skills with a locator; for a chosen skill, its
   entrypoint, inputs and defaults, contract and revalidation condition. Edit no skill package.
7. After the baseline, and again when evidence conflicts or a dependency emerges, check the Discovery investigation
   guidance triggers. If one applies, write the plan and outcome to RUN/notes/discovery.md (question, evidence route
   and order, owner, permitted effects, bound, stop condition); otherwise inspect directly.
8. Every environment read follows the Recursive discovery policy. One allowance covers discovery and research;
   reaching it stops exploration, not the run: record open gaps as assumptions or open items in `summary`.
9. Resolve internal terms and background beyond the checkout with Connected knowledge discovery: find the MCP readers
   (Slack or Teams, internal sites, design docs, private Git), search, and follow hits to the content. Record terms
   and conflicting claims with provenance, access and coverage gaps, and safe locators in RUN/notes/discovery.md.
   Keep private queries and content off public surfaces; a reader is no runtime dependency.
10. Establish the current-system account (Current-system baseline guide): read README first, reuse and revalidate an
    adequate account or recover one from docs, code, tests and authorized read-only observation. Write
    RUN/notes/current-system-baseline.md with as-of identity, coverage, conflicts, locators and durable home; cite it
    in `evidence_refs`. A repository without ShipLoop knowledge is not a new system. Keep the incoming change
    separate; consequential gaps leave dependent work unready.
11. For affected flows apply Service discovery guidance; record in RUN/notes/discovery.md:
    - observability: event owners and sinks to reuse;
    - service boundaries: consumer needs traced through business services to the real MCP, API and runtime
      capabilities, identities, schema and state;
    - cache, invalidation and async questions, inventing no infrastructure;
    - unproven access or caching: a safe policy-enforced read route, or a denial (privileged direct access is no
      fallback);
    - schema or projection delta: preserved state and its read-back check;
    - async flow: processor and recovery owner and the acceptance/completion boundary, else unknown (a status poller
      establishes neither); gate only that flow;
    - retained application state: the Runtime state placement section.
    Safe authorized reads may resolve a gap; an unavailable or partial observation is not absence. Turn unknown
    ownership into a scoped probe and a conditional change, gating only dependent work.
12. Establish the current target and effective identity; use it for dependent remote reads. Distinguish discovery
    operator, deployed runtime and end user. Record each unknown role or authority and its consumer under
    ## Access and accounts.
13. Record the interaction baseline (Interaction design guide) in RUN/notes/current-system-baseline.md: actors,
    channels, events, connection lifecycle, state ownership, what the runtime and project layers offer. Affected UI:
    the design guidance and its identity, version or digest, or the repository fallback. No UI still has machine
    interactions.
14. Answer each intake open question in `summary` with a source, or keep it unknown with an owner.
15. Before submitting, apply Discovery evidence handoff: list each consequential decision in `evidence_refs` with its
    section locator, and reopen each locator as a fresh reader. Also list every file written and source used, with
    scoped prerequisites and due revalidation.
""",
    "research": """\
1. Start from the open unknowns in the intake and discovery results and RUN/notes/discovery.md. Revise that frontier
   with Discovery investigation guidance (check its triggers first, and again when evidence conflicts); write a
   triggered plan and outcome to RUN/notes/research.md. Investigate directly only when no trigger applies.
2. Resolve each consequential unknown with repository, primary-interface or other fit evidence. In
   RUN/notes/research.md record the conclusion, source, uncertainty, affected requirement, consumer, prerequisite,
   reuse choice and verification need; leave an unsupported question open there with owner and the gate it blocks. A
   recalled fact is not evidence.
3. Environment reads follow the Recursive discovery policy, with bounded experiments (Bounded research guidance).
   The allowance is shared with discovery; reaching it stops exploration, not the run: record open gaps as
   assumptions or open items in `summary`.
4. Confirm access to each delivery target with a safe non-mutating probe (Access-readiness policy). Record each
   proven access need under HOME/environment.md ## Access and accounts as an open item: who can grant it, the gate
   it blocks.
5. For each need, in order: reuse unchanged, compose, augment, build new (Reuse-before-build guidance). Record the
   choice in RUN/notes/research.md, and why earlier options fail for augment or new. Assess skills, MCP servers,
   libraries and patterns for fit; a discovered capability is no authority to install it.
6. Resolve internal vocabulary gaps with Connected knowledge discovery: open the content, not snippets. Record
   authority, scope and safe locators in RUN/notes/research.md; evidence readers are not runtime dependencies; keep
   private context out of public searches.
7. Research quality-target and feasibility unknowns from existing contracts and evidence; a measured baseline does
   not choose user policy.
8. Reopen RUN/notes/current-system-baseline.md and resolve its consequential gaps (Current-system baseline guide):
   keep the prior as-of account, append corrections as a dated section. An observation or synthetic fixture cannot
   choose product intent.
9. For affected service choices, resolve with discriminating evidence (Service discovery guidance): current state,
   zero-copy and cache tradeoffs, permission-aware invalidation, async recovery, observability. Reuse native
   facilities. Record each unknown and its dependent work in RUN/notes/research.md.
10. Resolve the open interaction and state questions (Interaction design guide): actors, channels, events, connection
    lifecycle, state ownership, runtime and layer offers. Answers in RUN/notes/research.md; runtime facts under
    HOME/environment.md ## Platform facts.
11. RUN/notes/research.md ## Assumptions: each load-bearing assumption (its failure would change a plan decision,
    consumer or acceptance check), marked evidenced (locator), probed (command and saved output) or open (the check
    that would settle it, why not run). Plan builds its `assumptions` from it.
12. Before submitting, apply Discovery evidence handoff: list each consequential decision in `evidence_refs` with its
    section locator, reopen it as a fresh reader; also every file written and source used.
""",
    "spec": """\
1. Start from HOME/spec.md (quoted below), the research and discovery results and RUN/notes/current-system-baseline.md
   (Current-system baseline guide). Keep every R-<n>: change one in place, move a dropped one under ## Retired with
   its reason. Current explicit user instructions supersede older clauses; never relax a requirement to fit the code
   or tests.
2. Write each requirement under HOME/spec.md ## Requirements as R-<n> with its acceptance criteria inside
   (Behavior-model guidance): behaviour, boundaries, error behaviour, consumer outcome. Each criterion: positive,
   failure and boundary expectations, the consumer surface where it is observed, how it is confirmed. Split
   independently verifiable clauses; keep bundled behaviours visible under one ID.
3. Number requirements R-<n> only. A structure or technology choice is an AD-<n> decision in
   HOME/architecture.md ## Decisions, never in HOME/spec.md; a product decision never takes the AD- prefix.
4. Map every request outcome to at least one criterion (Behavior traceability guidance); keep approved scope. Mark
   each unresolved prerequisite or user decision as an open gap under its R-<n> in HOME/spec.md.
5. In each R-<n> this run adds or changes, state its request or decision basis, preserved and changed behaviour,
   source-section locators, evidence limits, and pending implementation and checks. ShipLoop derives the added,
   changed and retired IDs from the spec diff; list none by hand.
6. Assess non-functional requirements under HOME/spec.md ## Non-functional requirements (Requirements definition
   guide): operating conditions, measurable bound or observable criterion, verification method, justified
   exclusion, or unresolved target. Invent no target. A material requirement conflict goes in `summary` as open and
   keeps dependent work unready.
7. State and data assessment: under the R-<n> it affects in HOME/spec.md, write the affected resources, target
   identities, before and after invariants, recovery, applicable checks and unknowns.
8. For each service boundary specify verifiable contracts (Service discovery guidance): current authority, freshness
   versus revocation, incremental state, async completion and recovery, owned event coverage. Mark an inapplicable
   concern in one line; add no service to fill a template.
9. Decide the state and information lifecycle (Interaction design guide), in proportion to the request, as
   requirements in HOME/spec.md. Per piece of state: owner and location; who may read it (information one user must
   not see, such as an opponent's hidden game state or another person's record, stays off that client; what a lone
   user could only misuse against themselves may stay); how simultaneous changes resolve; what ends and removes it;
   the runtime quotas it meets. Personal or secret data: where shown, stored, logged, how long kept, how removed.
   Map each to what the runtime offers. Add no identity, sharing or persistence the request does not need; record a
   default for an open choice as an assumption in `summary`. Affected UI: component, interaction and skin premises
   and truthful async feedback as consumer-visible behaviour.
""" + _duty_focus(10, "HOME/spec.md", "spec") + """\
11. """ + _BACKCHAIN_ITEM + """
12. A complete spec establishes criteria, not implementation or test success. `evidence_refs`: HOME/spec.md, each
    requirement section and source used.
""",
    "test-strategy": """\
1. Build a risk-based strategy from HOME/spec.md and the spec changes since the run began (quoted below) before any
   code. Under HOME/environment.md
   ## Harnesses and suites plan, per requirement: layers (unit, integration, system, consumer), negative cases,
   fixtures and data, environment and authorization needs, required surface, due stage, owner, prerequisites; for a
   state or data change, its before and after checks (State and data assessment). Mark every check planned (planned
   is not a pass). Name an expected-RED control where test-first applies.
2. Plan checks for new and preserved behaviour from the spec changes since the run began and RUN/notes/current-system-baseline.md. An
   unknown existing behaviour needs discovery before a preservation target; an old pass is not a current pass.
3. Map each applicable non-functional criterion to a check with its environment and workload prerequisites. Missing
   evidence or access is not N/A.
4. Select or revalidate harnesses and suite entry points (Repeatable test-suite guide); reuse a prior harness only
   after revalidating fit. Choose target-native tests from the discovered remote code, test assets and deployment
   gate, or record the exclusion (Target-native test selection). Choose test systems and browser tools by
   capability, not product name. Under ## Harnesses and suites record each choice's role, fit, availability,
   prerequisites, setup and isolation, fixture lifecycle, runner and coverage tool, rationale and revalidation
   condition. Keep inspection separate from retained assertions.
5. Reuse, configure or extend existing frameworks and helpers before defining the smallest missing facility
   (Reusable test facilities); never assume a named skill or MCP is available. Record each facility's locator,
   interface, readiness or gap, owner and revalidation condition under ## Harnesses and suites. A missing facility
   goes in `summary` as plan's prerequisite work; its owning stage builds and validates it first.
6. Under HOME/architecture.md ## Real-boundary checks record, per check, where it runs and its target: local, client
   against a deployed target, or remote-resident. For remote tests: framework, availability, access, deployment
   prerequisites, and the authorized route to define or register, install and invoke them. A local pass is not a
   remote pass; do not narrow a behaviour list to a render smoke.
7. Affected service contracts (Service discovery guidance): map cache authorization and invalidation, remote
   reconciliation, async recovery and observability to independent outcomes at their real boundary under
   ## Real-boundary checks. A fixture does not prove live permissions, event delivery or operator log access.
8. Consume discovery's baseline (Initial repository baseline guide): record its coverage and limits, telling a
   passing subset from failed, blocked, intermittent, missing-test or expected-RED. In `summary` name each setup,
   repair or bootstrap prerequisite and the evidence it needs before dependent feature checks.
9. Write the focused, smoke and full-suite commands under HOME/environment.md ## Commands, each in a fenced code
   block, never in a Markdown table cell (an escaped `\\|` becomes a literal pipe, matches nothing and can exit 0).
   Per command: inclusion rule, expected cost, environment and fixture prerequisites, the test IDs it may print.
   A passing command names the IDs or cases it ran. This section owns the suite commands; fix any stale copy. Plan
   durable regression tests, not one-off probes. Smoke is a bounded subset, never evidence for the full suite.
10. Under HOME/environment.md ## ID convention declare each ID as tests will be titled. """ + ID_WORD_RULE + """
11. A case needing a host tool (browser, device, account, service): name it and probe it now by doing the case's
    first step, not reading a version. Before the product exists, probe a stand-in: a one-line page in RUN/scratch
    opened by `file:` URL or a throwaway static server you stop, its title read back; for an account or service, a
    harmless read. Cite the output in `evidence_refs`. Record only a failed probe as an access gap under
    ## Real-boundary checks with the requirement left unobserved. Give the case its own opt-in command or flag so the
    default test command passes without the tool.
12. A request naming a page or screen people use: plan a case driving it through its interface (browser or device)
    with its actions, expected visible outcomes, and tool named and probed as in item 11 (Consumer testing guide).
    Otherwise record the outcome unverified with owner and due stage (handoff, or the stage whose external effect it
    gates). An HTTP response alone is neither.
""" + _duty_focus(13, "HOME/environment.md or HOME/architecture.md", "strategy") + """\
14. `evidence_refs`: HOME/environment.md, HOME/architecture.md, each probe output and source used.
""",
    "plan": """\
1. Reopen the accepted intake, discovery, research, spec and test-strategy results, RUN/notes/{discovery,research,
   current-system-baseline}.md, the spec changes since the run began, HOME/environment.md ## Harnesses and suites, HOME/architecture.md
   and the relevant Git history (Git-history investigation guide). Sort open gaps into researchable unknown
   contracts, owner or access gaps and known setup prerequisites, each with its first affected consumer. With one
   boundary blocked, keep independent research and conditional planning eligible on their own prerequisites.
2. Plan backward from desired outcomes to their producers (Dependency-planning guidance); return `work_items`
   (item 17). Order readiness, implementation, integration and release so no consumer runs before its
   prerequisites. Each item's `context` gives ready and done conditions, candidate scope, proving check, authority
   boundaries, correction route. The plan implies no unrun test and no authorized external operation.
3. Apply Initial-plan reconciliation to HOME/architecture.md, HOME/spec.md, the non-functional requirements and the
   State and data assessment: map each applicable obligation and every acceptance criterion to its work item,
   prerequisites, observing test and release or recovery conditions, or to a reasoned exclusion (`summary`) or open
   need (`assumptions`). The mapping goes in each item's `context`. A filled template is not proof.
4. Carry the initial baseline's evidence and classification into `evidence_refs` and each affected item's `context`
   (Initial repository baseline guide). A foundation repair, setup prerequisite or missing-test bootstrap goes in the
   earliest feasible item before the feature that depends on it; its readiness evidence is the original check's
   passing rerun or, when none can rerun, a separately recorded passing characterization of unchanged application
   behaviour. Keep the original no-suite observation. An expected-RED repair may start its own work. A bootstrap
   makes only the smallest test-only harness, dependency or configuration edits and tests unchanged behaviour;
   alone it neither makes the repository healthy nor unblocks features. A failure of unknown relatedness stays
   blocking; waive or absorb no unrelated failure.
5. Reuse, configure or extend an existing test facility before planning a new one (Reusable test facilities); plan
   each missing one as its own prerequisite item and record in the consuming item's `context` its definition
   locator, readiness gap and owner. Readiness is not test execution.
6. Include environment preparation and delivery work as items; ask for delivery authority at the first concrete
   boundary that needs it (Delivery authority guidance).
7. Code or stored data added: write the namespace and data entries in HOME/architecture.md ## Structure with an AD-<n> per
   decision; each item's entries go in its `context`:
   - every execution environment the code runs in or reaches (local checkout, remote runtime behind an MCP server,
     API or CLI, hosted platform, each service);
   - per environment: current library structure (packages, modules, prefixes, exported surfaces, where similar
     responsibilities live), name resolution, and what new code imports, is called by or shares names with
     (Namespace and placement guidance); inspect a remote environment through its interface;
   - a home namespace and visibility per new responsibility across all items, and how new names, shared ones
     included, avoid collisions;
   - data storage per environment (Schema and storage guidance): existing and destination schema, owner and change
     mechanism; for a new schema its store, keys, field types, constraints, relationships, version, migration and
     storage policy (authority, retention, sensitive fields, quotas).
   Plan no empty package or directory for a hypothetical future.
8. Decide the interaction structure (Interaction design guide); record each decision as an AD-<n> in
   HOME/architecture.md:
   - placement: the simplest that meets HOME/spec.md. A single-user game or tool with no shared or lasting state
     runs entirely in the client. Add server state, identity, a store or live channel only for a requirement that
     needs it, and use the runtime's native storage, identity, cache, workflow and notification services first;
   - safeguards at every placement: HOME/spec.md's personal-data handling, a server-side check on every action by a
     caller the product does not control, validation and abuse limits on anonymous input, a record of every
     background or async failure that reaches whoever must act;
   - channels: per hop the lightest that meets the stated freshness (request/response; polling at a stated interval;
     email or platform notification for changes hours apart; server-sent events, WebSockets or push only when
     seconds matter). After a push, poll gap or reconnect, read authoritative state back. Cache only derived data,
     in the runtime's cache, expiring with the allowed staleness. State each channel's and cache's quota cost.
   Then write a Design basis in `summary`, rechecking the guide rather than copying a prior plan: baseline and delta;
   state, event and connection agreements with planned recovery checks (including a crash after acknowledgment but
   before processing); deployment fit; source and check locators. UI: component, interaction and skin premises, the
   design guidance locator with identity, version or digest (or the named fallback), each async cue with purpose and
   reduced-motion alternative or an explicit static choice. A human-facing UI defaults to an ambitious, highly
   interactive design: name the rich interactions planned (direct manipulation, inline editing, live preview,
   keyboard paths, animated transitions) and any scaled back, with the reason. A consequential UI choice gives the
   guide's ambition, the reuse, evolve or upgrade decision, effort and benefit, and the compatibility check.
   Allocate each UI decision to the item that owns it (UI planning ownership guide) and put it, with planned check
   locators, in that item's `context` and `evidence_refs`. Reuse accepted choices for unaffected scope. Start no
   nested review.
9. HOME/architecture.md: each structure or technology decision as AD-<n> (choice, why, alternatives, status) under
   ## Decisions; a decision that no longer holds under ## Superseded; update ## Stack, ## Structure, ## Conventions
   and ## Interfaces and boundaries where this plan changes them.
10. Give each work item a compact `context` a fresh reader can act on, full locators in `evidence_refs`, longer notes
    in `summary` (Decision carry-forward guidance). Per applicable entry: locator, decision, rationale, scope,
    revalidation condition:
    - each convention, canonical test or example, verified skill, MCP or library contract, environment or delivery
      decision, approved exception;
    - a selected local skill: the index or selection-note locator and what to revalidate (no fit is a current
      observation; later items reread the index);
    - test strategy: the ## Harnesses and suites locator and the item's compact test decisions (execution and target
      location, fixture and suite choices, what to recheck);
    - baseline and spec: exact sections, gaps and revalidation conditions of RUN/notes/current-system-baseline.md and
      HOME/spec.md;
    - service decisions: note locators and revalidation conditions;
    - readiness checks of the item's prerequisites.
    A later packet replays no earlier stage's references, so the item carries them. Copy no transcript, invent no
    decision ledger; a context summary is not proof.
11. Plan the before and after decisions and preservation checks from the baseline and the spec changes since the run began, and durable
    documentation work for knowledge that exists only in run notes.
12. Map accepted service choices to the affected schema and config, query and cache, worker and status, business and
    UI, logging, test and operator files, as needed (Service discovery guidance), ordering prerequisites and checks.
13. Each item's `context` states the module format its files use (CommonJS or ESM, with or without package.json) and
    the loadable seam its tests import, so a test loads before the implementation exists.
14. Before fixing item IDs, check the draft once for coherent increments. Split a deliverable with different
    prerequisites, a useful intermediate contract or artifact, or independent implementation and check; merge
    fragments sharing prerequisites and an implementation boundary with no checkable state of their own. A small
    change may be one item; no minimum, quota or scaffolding item. Preservation and negative requirements are checks
    on the affected item unless they need their own change. Add no item for step planning, validation, build, test,
    documentation, verification, commit or review (each item already gets them). Keep a cross-item or
    later-environment check at the boundary where it is due.
15. Per dependency name the supplier and the concrete output or state the consumer needs. Authoring an artifact
    differs from applying it in a running environment. A shared topic, list order or shared file is no dependency.
    Record independent branches and file or resource conflicts in `summary` (an isolated workspace does not make
    parallel work safe). ShipLoop runs the queue one item at a time, so put each prerequisite before its consumers.
16. Return the load-bearing `assumptions`, starting from RUN/notes/research.md ## Assumptions and the discovery
    notes, with exactly the template's fields per disposition (evidenced: `evidence`; probed: `check`, `evidence`;
    open: `check`, `consumer`, `reason`). An open assumption's `consumer` is the `work_items` ID that settles it.
17. Return the complete ordered `work_items`, each with only `id`, `title` and optional `context`, covering every
    approved outcome, including required independent work with no downstream consumer.
18. `summary` keeps this pass's key reference statements, decisions, constraints and acceptance context, as
    supporting references, not a replacement assignment or a restatement of the request; each item's ready and done
    conditions stay its only execution directive. `evidence_refs`: HOME/architecture.md, any execution graph, every
    source used. An unrecorded conversation is not a handoff.
19. """ + _BACKCHAIN_ITEM + """
""",
    "prepare": """\
1. Prepare or verify the development and test environments the plan's items and HOME/environment.md name
   (Environment preparation guidance), using what the repository declares. Install nothing without authority.
2. Confirm by safe observation: isolation, runtime, configuration and data safety, access, fixture readiness,
   baseline identity (Workspace and return guidance).
3. Start each planned check's runner, the linters and the fixtures; save the output and list each file in
   `evidence_refs`.
4. Baseline blocked by setup or access (Initial repository baseline guide): prepare only the approved prerequisite,
   keep the original observation, and rerun the original initial check on the unchanged product and tests before any
   dependent feature edit. Never replace it with an easier route or call the blocked baseline passed.
5. Recheck discovery's source-return trigger and the authorized delivery and verification route from the execution
   checkout before the first dependent work. If the return must precede a consumer check, record the ordering
   conflict in `summary` as unresolved. Never return early, deploy, or bypass the final-handoff return guard.
6. Record readiness under HOME/environment.md ## Targets and runtimes and ## Commands: what was prepared, the
   commands that start each runner, the observations. Record not-applicable only when this candidate needs no
   preparation, with what you assessed. Missing required access or setup is blocked, not not-applicable.
""",
    "step-plan": """\
Change no product file in this stage.

1. **Recheck the item.** Reopen its `context` and recheck each condition. If the plan no longer requires it, report
   blocked (blocked_by user, `awaiting` an answer: drop or keep) citing the superseding result; never skip the item
   or repair the queue here. Keep the change inside the item: available APIs and other parts of the request do not
   widen it. A prerequisite outside the item gets its supplier route in the summary and the blocked outcome.
2. **Test decisions.** Reopen the item's test decision and HOME/environment.md's harness and suite decisions. In the
   summary say which you retain, refine or supersede and why; locators in evidence_refs. Revalidate harness, suite
   and browser tools for the changed surfaces (Repeatable test-suite guide); reuse supported choices or record a
   justified revision. A remote-resident case needs its framework and an authorized setup, invocation, result
   retrieval and teardown route. Reuse an existing facility before the smallest missing one (Reusable test
   facilities); record its locator and readiness gap in the summary.
3. **`criteria`** (`[{"id": "C1", "text": "..."}]`). Each: `<condition>. Confirm by: <command, observation or
   inspection>; pass when <expected result>`; say whether it must be exercised or inspection suffices, and name the
   R-<n> served.
   - A docs or coverage criterion gets a command check (a search for the required terms).
   - A condition no command can confirm is not a criterion: list it in the summary as an open item (who does what,
     what they report back) with `Confirm by: unconfirmable here — <what would confirm it>`.
   - A new or changed public entry point: add a criterion that it checks its arguments and carries a contract
     docstring (Code craft 2-3), confirmed by its rejection tests and by inspecting the diff.
4. **`steps`**: every implementation step in order (one is fine); ShipLoop issues one implement packet per step.
   - Size each as one behaviour-level change a named check proves. Split a step with two separately confirmable
     behaviours, one crossing a module or layer boundary (interface first, then each side), joining two outcomes with
     "and", or too large for one review. Merge a step no check confirms alone (half a rename, unused scaffolding)
     into the step it serves. A single bug fix or mechanical rename is one step.
   - Tests are not a step (the test stage writes them after the last implement step); a step changing only test
     files is refused unless the whole item is tests.
   - Each step declares `deps` (earlier step IDs it truly needs, else []; list order is no dependency), the
     `criteria` it satisfies and the `paths` it changes (inside the item's `paths`). Every criterion is satisfied by
     some step.
   - `skills`: reread the host's skills and the repository's skill index (an earlier item may have added one). List
     `{"name", "why", "locator"}` for each with a concrete use in the step, else []. Prefer a repository-local skill
     reused unchanged. `locator`, when given, is an existing SKILL.md or card path.
5. **`test_commands`** (`[{"command", "suite", "ids", "criteria"}]`), run from the repository root; the test and
   verify stages run exactly these.
   - focused: this item's cases with the IDs they carry and a runner flag that prints test names (Jest `--verbose`,
     pytest `-v`, `node --test` default spec or tap reporter; never dot or junit). """ + ID_WORD_RULE + """ `min_tests`
     where a command must run at least that many. ShipLoop refuses a run that executed no test, so check the filter.
   - regression: the retained suites the changed paths affect.
   - check: the lint, type and build commands HOME/environment.md records for these files, judged by exit code, no
     `ids` or `min_tests`. None: `check_na` with the reason; no command at all: `test_commands_na`.
   - Every criterion is named in some command's `criteria`, and a command names only listed criteria. A list too
     large for the loop contract is refused: shorten IDs, drop duplicates or split the item.
6. **`expectations`**: each fact the steps build on, `{"id", "state", "statement", "steps", "paths", "check",
   "from"}`; ShipLoop runs every check on the unchanged item base at validate-existing.
   - Every existing path a step changes or relies on is `works` or `broken` (the request says it is broken); every
     new path is `absent` (its place is free).
   - `check`: one read-only command from the repository root that exits 0 while the state holds. For `broken`, the
     reported failure still reproduces: `! npm test -- -t TC-3` or `node cli.js 2>&1 | grep -q 'TypeError'`.
   - An open plan assumption this item consumes becomes an expectation whose `from` names it.
7. **`paths`**: every file the item changes (repository-relative files or globs), including the test files the test
   stage writes. The item commit takes these, the changed documentation and HOME/. No test command and only non-code
   paths skips the test stage; a diff touching no code or test path skips document.
8. **`follows`**: each R-<n> and AD-<n> followed; each must exist in HOME/spec.md or HOME/architecture.md.
9. **Plan record** in the item's `context` or the summary:
   - outcome and invariants kept; contracts and responsibilities that change;
   - target files, interfaces and conventions, matched to the house style (House-style guidance);
   - each step's failure cases and the diagnostics and errors it must produce;
   - documentation to change; integration impact and release prerequisites; readiness, completion and revalidation
     conditions;
   - the Coding decision guide's selection: runtime and version, artifact and boundary, links to only the matching
     sections;
   - when the item adds or moves code or stored data, replays a pinned value (fixed dice, seed data), or changes
     interactions, UI or service state: also record what the Plan record guide (GUIDES/plan-record.md) lists for that
     topic, opening only its matching section.
   This record is supporting reference; each step's task and criteria stay its only directive.
10. **Knowledge.** A structural choice HOME/architecture.md lacks: next AD-<n> under ## Decisions, cited in the
    step. A newly working command: HOME/environment.md ## Commands. Keep every R-<n> and AD-<n>; write nothing else
    in HOME/.
""" + _STEP_PLAN_GRAPH + """\
12. **evidence_refs**: absolute paths of every planning file written, and the requirement sections and test locators
    used.
""",
    "test-spec": """\
Write no test code in this stage.

1. One `test_cases` row per ID the step plan's focused commands list; no other ID. A criterion that needs an
   unlisted ID: report revise naming it.
2. Each row (Test-case planning guidance): `criterion`, `requirement` (R-<n>), `oracle`, `red`, `green`. Put surface
   (unit, public interface, real boundary, rendered UI; Real-boundary test guidance) and due phase, setup and
   fixture, action, teardown (or "stateless"), command row, registering suite and smoke membership in those fields
   or the summary.
3. Oracle from the requirement's text, never the code; check any golden, fixture or snapshot against it. It is an
   observation, never only that a page loads. RED: how it fails on the item's base, or "characterisation" if it
   already passes.
4. Cover positive, failure and boundary. Each new or changed public entry point: one rejection case per constraint
   (missing, wrong type or shape, out of range), asserting the error type, the argument named and unchanged state.
5. Isolate each test: no shared mutable state, each with its failure cleanup. Name the harness, helper or fixture
   it uses (Reusable test facilities); for a missing one, the smallest facility the test stage must build.
6. Due at a later stage (system test, release): an `assumptions` open item (case ID, criterion, R-<n> and oracle in
   `assumption`; `check`; `consumer` = that outer stage; owner). Confirmed only by a check command or inspection: no
   case; list it with its command in the summary. Untestable as written: report revise naming it.
7. Summary: which harness and suite decisions in HOME/environment.md this item keeps, refines or supersedes, and
   why. evidence_refs: their locators, the step plan's, the requirement sections used.
""",
    "validate-existing": """\
1. ShipLoop ran each expectation's check, and each open plan assumption this item settles, on the unchanged item
   base; results are below. For each mismatch read the step plan's steps and paths, and with one small
   discriminating observation find whether the fact or the check is wrong (Baseline-test guidance, Current-system
   baseline guide).
2. Route each mismatch:
   - check wrong, fact holds: report revise. Never edit or weaken a check here.
   - `works` expectation broken, fix known and small: fix it in the working tree, touching only that expectation's
     paths, and commit nothing (ShipLoop commits it on accept as a separate preparatory commit).
   - environment lacks a tool, service or setting: fix it and record it in HOME/environment.md ## Commands or
     ## Targets and runtimes.
   - `absent` finds something, `broken` does not reproduce, or the fix is unknown: report revise with what is true
     (the step plan reshapes the steps; a needed repair becomes an earlier step).
   - fix lies outside this run (another system, a person's access): report blocked, blocked_by external or access,
     naming the need.
3. Start none of the item's own change.
4. Revise names each mismatch in `failed_expectations`: `[{"id": "E1", "actual": "<what is true>", "route":
   "check" | "steps"}]`; `check` when the check is wrong (`actual` gives the corrected check), `steps` when the
   plan must change.

On re-entry after implement, ShipLoop runs the checks in a temporary worktree at the item base (after any
preparatory commit); a mismatch there is a revise.
""",
    "implement": """\
1. **Scope.** Do only this step: edit its paths to meet its criteria, nothing no criterion asks for. Earlier steps are
   accepted. Write no tests, start no later step, and leave everything outside the step's paths as is (no
   reformatting, no reverting). Existing tests, check scripts, golden or fixture files and thresholds are checks:
   change one only when a criterion says to.
2. **Build.** Each iteration edits first. Follow the step plan's Coding decision selection (Coding decision guide),
   reading only its matching sections; check current code, versions and consumers before reusing or augmenting a
   unit. Read history or earlier reviews only when a check fails or a question needs one section. Apply Code craft
   and House-style guidance. Use each listed step skill for its purpose (invoke it, or read its SKILL.md and follow
   it); the summary says per skill whether you used it, and why not.
3. **Check.** After each edit run every recorded check command and `shiploop lint --action`; write each exit code in
   RUN/notes/<action>.md. Fix a failure by changing the work, never the check, its expected result or the command.
   A lint finding that must stay goes in `lint_waivers` as `{"id": "<printed ID>", "reason": "<why>"}`. Use only
   what is present: download, install or fetch nothing. Record the best evidence available and what would confirm
   more.
4. **Hand off.** `not_covered`: each behaviour the change added that no test-spec case covers, else empty. Record a
   departure from HOME/architecture.md as a new AD-<n> under ## Decisions, and a newly working command in
   HOME/environment.md ## Commands.
5. **Services.** Apply the accepted contract and Service discovery guidance; revalidate target state and authority
   before any effect; keep unrelated remote fields and existing operational owners. Unresolved cache access or async
   completion uses its recorded safe fallback or correction.
6. **Unachievable as planned.** Stop the loop blocked and report revise, naming the criterion or command and the
   case, when:
   - a criterion contradicts another, the item or a protected file, shown by a check after all compatible work is
     done, with existing behaviour kept at the conflict point;
   - confirming it needs an absent tool, runtime, access or authority, and the criterion text does not say
     `Confirm by: unconfirmable here`;
   - satisfying it would exceed the item;
   - the same check still fails after """ + _FIX_ATTEMPTS + """ genuine fix attempts;
   - the change invalidates a recorded command (moved module, new dependency or runtime; Target-native test
     selection) or needs a new prerequisite or authority boundary.
   Report blocked, with blocked_by, only when the user, an access grant or an outside dependency must resolve it.
""" + _IMPLEMENT_CHAIN,
    "test": """\
1. **Write the cases.** Each quoted test case becomes a test titled with its ID as its own word, in the suite and
   command its case names (Repeatable test-suite guide, Target-native test selection), asserting the spec's oracle,
   never the code's behaviour. Reuse existing harness, helpers and fixtures first (Reusable test facilities); never
   assume a named skill or MCP is available. Build a missing facility within this item and validate it before the
   tests that use it; record it in HOME/environment.md ## Harnesses and suites (locator, interface, readiness,
   owner, revalidation condition). Write no case due at a later stage.
2. **Test decisions.** Reopen the item's test decision and HOME/environment.md's harness and suite decisions. Record a
   harness or suite decision the implementation changed in ## Harnesses and suites, and a real-boundary decision in
   HOME/architecture.md ## Real-boundary checks. Summary: which decisions you retain, refine or supersede and why;
   locators and the step plan's in evidence_refs. A recorded completion does not prove a harness, fixture or target
   still works.
3. **Gaps.** Read the implement results' `not_covered`. A behaviour or rejection case the spec lacks becomes a
   sub-case of the closest quoted case with its oracle from the spec (Test-case planning guidance), titled
   `<ID> (<letter>)`; none fits: report revise. Each new or changed public entry point gets rejection cases. Test a
   new error path or debug output, on and off, with safe diagnostic context.
4. **Run and fix.** After each change run every recorded command, the red-check command and the lint command. Find
   each failure's cause with one small observation (product defect, invalid test, environment) and fix the product.
   Change a test, fixture, golden file or threshold only for an independent reason written in RUN/notes/<action>.md.
   Never weaken, delete or skip a test to get green. A repeated unchanged failure is not progress: change approach.
5. **End states.** Each case ends as:
   - validated: run, and the observation matches the oracle;
   - validated another way: the first method could not observe it, another ran and passed, still titled with the ID;
     the summary says what changed and why;
   - unachievable: a named reason and the requirement left unverified; report revise.
   A case written but not run has no end state.
6. **Result fields.** `red_na`: each new test passing on the item base without this change, `[{"id", "reason"}]`.
   `retired_tests`: each test this item deliberately retires, `[{"id", "reason": "<the R-<n> or AD-<n> that retires
   it>"}]` (any other drop below a command's floor is refused). `lint_waivers`: `{"id": "<printed ID>", "reason":
   "<why>"}` per lint finding that must stay.
7. **Proof limits.** A passing command proves only the cases it runs; a smoke or subset run never stands for a
   recorded command; a local pass does not replace a required remote or real-boundary check (Real-boundary test
   guidance). Probes and experiments go in RUN/scratch. Install, download or fetch nothing. Never commit or push.
8. **Revise** (naming the case or command, why, the requirement left unverified, and every required command that
   could not run) when: a failure is proven unachievable (contradicts the spec or another requirement, needs an
   absent tool, access or authority, or would exceed the item); a recorded command is wrong or cannot run here; an
   existing suite the changed paths now affect must join the regression command; the step plan recorded no test
   command for code this item changes. Report blocked, with blocked_by, only when the user, an access grant or an
   outside dependency must unblock it.
""",
    "document": """\
1. **List** the changed public behaviours from the change inventory, the step plan, the implement results and the
   item's diff.
2. **Observe and write.** Run each changed behaviour, then update the README, API, user, operator, error and design
   docs from what you observe: visible errors, how to turn on diagnostics, known limits and caveats. Link to the
   authoritative home rather than copying a contract (Documentation guidance). Document nothing you did not observe
   working. Durable facts go in the repository's docs, never only in run notes.
3. **Decisions.** A design or service decision implement did not record: an AD-<n> under HOME/architecture.md
   ## Decisions (a service choice with contract, owner and revalidation trigger).
4. **Baseline.** Recovered existing behaviour: keep recovered observations and accepted deltas apart from the prior
   as-of baseline (Current-system baseline guide).
5. **Reread** every changed document and run its commands and examples. In RUN/notes/<action>.md record why a
   behaviour needs no documentation, why the README did not change, or why an example cannot run here.
6. **Commit nothing yourself.** """ + _ITEM_COMMIT + """
7. Plan or criterion wrong as observed: report revise naming it. Report blocked only when a behaviour cannot be
   observed here, naming it.
""",
    "verify": """\
This is item acceptance, not a claim that integration or release has happened. Each review iteration does items 1-7
in order.

1. **Run** every recorded command (the Test rerun list); write each exit code and test count in RUN/notes/<action>.md.
2. **Confirm.** Per criterion name the passing command or inspection that confirms it now. Stale, skipped, missing or
   other-candidate, command, configuration or target evidence confirms nothing; diagnostic scores are apart from
   this. A criterion reported `inspected` or `unconfirmable` whose `Confirm by:` needs execution: report revise.
3. **Reconcile cases** (Test-case planning guidance). Classify each test-spec case passed, failed, blocked, not-run
   or justified N/A, and reconcile each affected requirement clause with its case, required surface and due phase,
   checked surface, candidate, status and evidence. A pass on another surface only supports; source, HTTP or DOM
   structure alone cannot close a rendered interaction. A case not yet due keeps its phase, owner and prerequisites;
   missing evidence for an already-due case stays incomplete. Check for dropped clauses or cases; claim no
   requirement met while a required observation is unrun.
4. **Trace.** From RUN/lint/<action>-inventory.md list every new or changed public entry point (exported function,
   CLI, request or event handler, callback). Walk one valid, one boundary and one invalid input to its return, error
   or side effect, one trace line per path in RUN/notes/<action>.md. A wrong, unhandled or untested path is a
   finding; a test added for an untested path is titled `<ID> (<letter>)` under the case it extends. An entry point
   missing from the inventory is untraced.
5. **Review** the whole diff against the step plan's steps, paths and justified revisions, affected consumers, Code
   craft, the Coding decision selection and HOME/architecture.md. Look for: missing argument checks or contract
   docstrings at an entry point; missing error paths; silent failures; restating or stale comments; dead code; user
   text concatenated or bypassing the catalog; names outside the planned namespace or exported too wide; stored data
   off the planned schema; a near-copy of existing logic; a plain interaction where the plan called for a rich one; a
   deviation from HOME/architecture.md with no new AD-<n>. Reconcile tests, docs, error behaviour, diagnostics,
   dependencies and limitations. ShipLoop linted and auto-fixed safe formatting on entry: keep or revert each
   auto-fix the lint record names. The lint record supports this review; it does not replace it.
6. **Services** (Service discovery guidance): verify the item's service and observability contracts' due outcomes,
   safe fallback and failure cases. Keep local simulation apart from required remote readback, permission
   enforcement, completion and event retrieval.
7. **Classify and fix.** Material: wrong behaviour on a traced path; a missing or wrong argument check, contract,
   error path or test; a failing command; a misleading comment; logic that should have been composed. Trivial:
   wording, ordering, a sharper name. Reopen no finding an earlier iteration fixed unless its code changed. Fix
   every in-scope finding by changing the work, never a check or its expected result (a test only to fix a
   finding). If anything changed, rerun item 1.
""" + _VERIFY_ASSEMBLY + """\
9. **Later checks.** Each system, release or real-boundary check the criteria need is an open item in `assumptions`
   with its consumer (the stage it is due at) and owner; add any missing one. A boundary no local test proves stays
   pending with its owner in HOME/architecture.md ## Real-boundary checks (Real-boundary test guidance).
10. **Commit nothing yourself.** Keep run state, raw logs, credentials and generated artifacts out of the product
    commit. """ + _ITEM_COMMIT + """
11. **Summary:** entry points traced, each trace that found an issue and its fix, each command with its exit code,
    any required check not run and why, known limitations.
12. Criterion or check unachievable as planned: report revise naming it. Report blocked, with blocked_by, only when
    the user, an access grant or an outside dependency must unblock it.
""",
    "carry-forward": """\
1. **Knowledge home.** Update in place; keep completed evidence apart from future plans, never rewriting it:
   - HOME/environment.md ## Commands: every command that worked.
   - HOME/architecture.md ## Decisions: each AD-<n> this item added; a superseded one moves to ## Superseded, never
     deleted.
   - HOME/environment.md ## Harnesses and suites: suites; focused, smoke and full commands; harness and case
     locators; fixture lifecycle; each test facility's locator, interface, readiness or gap, owner, revalidation
     condition.
   - HOME/architecture.md ## Real-boundary checks: each pending full-suite and real-boundary check with its owner.
   - HOME/spec.md: each R-<n> this item satisfied; an open gap under its R-<n>, an unresolved state or data change
     included (State and data assessment). Keep unaffected clauses, and never relax one to fit the code or tests.
     Test IDs live only in test code: write none here.
   - Open risks, unresolved dependencies, system-test obligations, release prerequisites and any observation no item
     owns: open items in `assumptions`, each with owner and, as `consumer`, the later outer stage it is due at.
   - Carry the prior baseline, incoming delta and updated knowledge locators forward, keeping historical snapshots
     (Current-system baseline guide); retain the house style (House-style guidance) and the learnings the next run
     needs (Persistent project-knowledge guidance).
   - Expand no scope; adopt no tentative idea as policy.
2. **Queue** (Carry-forward mapping guidance). Read RUN/state.md `work_items` with every pending title and context;
   give every observation that affects later work an owner:
   - defect in completed work, or a completed prerequisite new evidence invalidates: a corrective item with
     revalidation, ahead of its consumers;
   - needed research or preparation prerequisite: its own item ahead of every consumer;
   - affected future item: its `context` carries decision locator, rationale, revalidation condition (copy no
     transcript, invent no decision ledger; a context summary is not proof);
   - finding incompatible with the approved work (changed requirement, permission or invocation contract): stop the
     loop and report blocked; it is no queue edit.
   To change the queue give `work_items`: the whole future queue, rows `{"id", "title", "context"}` in prerequisite
   order, no completed or current ID, keeping unrelated pending work. Explain each removal, merge or supersession in
   the summary. Omit `work_items` to keep the queue.
3. **Skill decision**, in `skill`:
   1. *Inspect* the repository skill index (the directory HOME/environment.md ## Skills names, or README or AGENTS.md
      skill links; a missing index is no blocker) and your host's skills; list what you inspected in evidence_refs.
   2. *Decide*, smallest first (Reuse-before-build guidance, Repository-local skill guidance): `none` (no repeated
      procedure, or a code, test or doc change already captures it); `reuse` (an existing skill covers it unchanged;
      different parameter values alone need no new skill); `update` (a small compatible extension capturing a
      demonstrated lesson, keeping supported inputs, defaults and older examples); `create` (no suitable skill, or
      combining contracts would obscure selection or break a consumer). `update` or `create` only when the same
      procedure ran in two or more steps or items of this run, or a pending item or R-<n> says it will recur; put
      those IDs in `skill.evidence`. Capture no transcript or speculative framework.
   3. *Where:* the repository's skill directory (## Skills, or the existing layout), else `skills/<name>/` in
      WORKTREE, added under ## Skills. Never edit an installed or shared skill, install globally, add a dependency,
      connector or privilege, or publish. Derived content keeps source, revision and licence.
   4. *Write it deterministic.* `skills/<name>/SKILL.md` opens with `name` and `description` frontmatter (when to use
      it and when not). Body: what it produces and why; each input (type, required, default and its source); exact
      steps; expected output; failure and recovery; permission boundaries; relative links to the code, tests and
      HOME/spec.md sections it relies on (link requirements, never copy); what needs revalidation. No credentials,
      machine-specific paths or IDs, run or worktree paths. Every mechanical sequence is a script
      `skills/<name>/scripts/<verb>` in a runtime the repository already uses: inputs as arguments, exit 0 on
      success and non-zero with a named message per failure, printing the output SKILL.md describes; SKILL.md runs
      it and does not restate its logic. A judgement step stays in SKILL.md as a numbered instruction with its
      decision rule. Task-specific values stay in evidence.
   5. *Prove.* Run the skill once on this run's real procedure; write command, exit code and output to
      RUN/notes/<action>-skill-trial.md (an update also runs one retained older use). The note says whether a fresh
      reader (given only the index, the skill and a new task) tried it, or "cold-context reuse untested". Presence or
      installation is not proof it runs.
   6. *Register:* a line with the skill's path, when to use it and its inputs in HOME/environment.md ## Skills, and a
      link from the repository skill index; list any index file outside HOME/ in `skill.index`.
   7. *Record:* `skill` = `{"decision", "reason", "path", "evidence", "index"}` (`path` = the SKILL.md for `update` or
      `create`; name a reused skill in `reason`); the trial note in evidence_refs. On accept ShipLoop commits the
      skill directory and the `index` files as their own commit.
   An earlier selection or passing trial is an input, not authority: revalidate for each new task.
4. **Commit nothing.** On accept ShipLoop commits HOME/ (and the skill, item 3.7).
""",
    "system-test-author": """\
1. Gather: the test strategy (HOME/environment.md ## Harnesses and suites, HOME/architecture.md ## Real-boundary
   checks, the test-strategy result), every item's test cases (the `test_cases` hand-off), and the open items quoted
   below (the system-test obligations). Take the latest done test-decision record for each relevant completed item
   (step-plan, test-spec or test) from state.md's accepted history with the locators it kept; infer no whole-product
   coverage from the last transition or item. The current OUTER plans are the latest done records after the most
   recent accepted replan; pending, repeat and blocked results are not plan authority. `evidence_refs`: the action,
   result and test-note locators used.
2. Choose cases: each due-later case from item 1 becomes a system case here or an open item with its due stage
   (item 7). Add cases for the real integration, consumer, runtime, security, accessibility, migration,
   compatibility and operational boundaries that apply; reconcile suite membership and prerequisites first. N/A only
   with the reason; missing access is not N/A.
3. Write the catalog in `summary`, one row per case in the System-test catalog guidance shape (case ID, phase,
   requirement, expected outcome, environment and target, prerequisites, executable reference, owner). A post-release
   case is owned by release-verify and never waived.
4. Write the tests. Reuse the existing harness, frameworks and helpers (Repeatable test-suite guide, Reusable test
   facilities); build only the smallest missing facility; never assume a named skill or MCP is available. Record each
   facility's locator, interface, readiness or gap, owner and revalidation condition in HOME/environment.md
   ## Harnesses and suites. Add the system cases and retained INNER cases to the repeatable full-suite entry point,
   keep the smoke selection, and copy no tests into another suite. Each new test file names the requirement or test
   IDs it covers in its opening lines; shared helpers check their arguments. Check shared setup cost, independent
   assertions, isolation and failure teardown. If the remote framework requires it, version the remote-resident test
   definitions and registration with a repeatable authorized install and invocation.
5. Run each system command once now and confirm its discovery and rerun work. A command that cannot pass here is
   changed to observe the same requirement another way, saying what and why in `summary`. Every case ends validated,
   validated another way or unachievable (item 7); a case written but not run has no end state.
6. `system_commands`: one row per runnable command, shaped like test_commands, suite `focused`, `regression` or
   `check`. `focused` and `regression` suit runners whose output ShipLoop can count and carry the case `ids`; a
   non-runner (shell pipeline, grep, curl probe) is `check`, judged by exit code, no ids or min_tests. A row whose
   cases need a host tool (browser, device, account, service) gets `"host_dependent": true`: ShipLoop then also runs
   the regression commands at system-test and refuses if any of that row's ids appears in their output, as the
   default suite must pass without the host tool. No system test applies: empty list with `system_commands_na` and
   the reason.
7. A case that cannot run here (a browser or account this host cannot reach) is unachievable. Leave its command out
   of `system_commands` (ShipLoop reruns every recorded command and refuses unless each passes). Record it as an
   open item in `assumptions`: `assumption` = case ID and the requirement left unverified; `check` = who does what
   and reports what; `owner`; `reason` it cannot run here; `consumer` = the due stage (handoff, or the stage whose
   external effect it gates). Continue with every runnable case. Report blocked only when nothing else can proceed,
   replan when the plan is wrong.
8. The integrated test plan goes in `summary` under the catalog and in HOME/environment.md ## Harnesses and suites
   (OUTER test-planning handshake): candidate and boundaries, selected cases and oracles, commands, lifecycle and
   sharing decisions, cost, prerequisites, execution owners; which checks run now at system-test and which need the
   authorized release first. Cite HOME/environment.md in `evidence_refs`; the decisions and constraints the plan
   rests on go in `summary`.
""",
    "system-test": """\
1. Name the plan you run: the latest done system-test-author record after the most recent accepted replan, and its
   integrated test plan in that summary and HOME/environment.md ## Harnesses and suites (OUTER test-planning
   handshake). Before running, revalidate its candidate, case selection, target and fixture assumptions. Its
   locators, and its reuse or the concrete mismatch, go in `evidence_refs`. A required planning gap ends as repeat,
   blocked or replan; never guess a command or drop a required case.
2. Before running check prerequisites, fixtures, execution location, target, identity, authorization, remote
   framework availability, and the deployed or test revision. Deploy not to unblock a test; use production only with
   authority.
3. Run the due cases on the intended candidate and boundary (System-test placement guidance, Real-boundary test
   guidance). Substitute no planned case or local mock for a required system observation. A local pass replaces no
   blocked or unrun required remote check and establishes no combined full-suite pass; keep that check's owner and
   boundary. Check repeatability when fixtures changed. Never blindly replay an uncertain external effect.
   `evidence_refs`: each command, candidate and target, scope, cleanup outcome and unrun check.
4. A recorded system command that fails here is no open item: ShipLoop refuses done while it fails. Fix the
   candidate, report replan for missing product work, or blocked when nothing else can proceed.
5. After a material change to code, tests, fixtures, configuration or target, rerun the affected observations; reuse
   unaffected evidence only with its identity and relevance stated.
6. Run any open item system-test-author recorded that this stage can now run, reporting each in the summary (not
   recorded evidence: ShipLoop's rerun covers only recorded system commands). Leave the rest listed with their due
   stage.
7. A required case only a person can run (for example in a signed-in browser), with no route on this host per the
   discovery and test-strategy records and its command left out of `system_commands`, does not block this result.
   Record it as an open item in `assumptions`: case ID, who does what, what they report, owner (a person), due stage
   (handoff, or the stage whose external effect it gates) as `consumer`. Submit done once every other due check and
   ShipLoop's rerun pass; handoff reports it unverified, never as a pass. Report blocked with `awaiting` only when a
   later stage takes an external, hard-to-reverse effect the case gates, or nothing else can proceed. An enabled
   delivery contract keeps its own obligation phases.
8. `summary` classifies every selected case passed, failed, blocked, not-run or justified N/A. Every case ends
   validated, validated another way (what changed and why) or unachievable (items 6-7); a case written but not run
   has no end state. Reconcile each affected requirement clause with its case, required surface and due phase,
   checked surface, candidate, status and evidence. A pass on another surface only supports; source, HTTP or DOM
   structure alone cannot close a rendered interaction. A case not yet due keeps its phase, owner and prerequisites;
   missing evidence for a due case stays incomplete. Check that no clause or case was dropped; claim no requirement
   met while a required observation is unrun.
""",
    "product-acceptance": """\
1. Gather: the original request and intake result, the accepted requirements in HOME/spec.md, the spec and
   architecture changes since the run began, the integrated test plan (latest done system-test-author record after
   the most recent accepted replan, and HOME/environment.md ## Harnesses and suites; OUTER test-planning handshake),
   and the system-test result. Locators in `evidence_refs`.
2. Assess the product against the original outcome, not only the spec: acceptance criteria, cross-cutting
   requirements, consumer impact (Consumer delivery guidance), test evidence, known limits. Reconcile new and
   preserved behaviour against the prior baseline and incoming spec (Current-system baseline guide, Behavior
   traceability guidance) and check durable knowledge for gaps. A recovered description or planned check alone does
   not establish acceptance.
3. Give every request outcome one end state in `summary`: observed by an executed check; observed another way (the
   first method could not, the new check ran and passed); or unachievable here or not yet due, listed in
   `unverified` while the run continues. Try another way to observe it before listing. Each `unverified` entry:
   `outcome`, named `reason`, the `check` its owner does and reports, the `owner`, the `due_stage` that reports it
   (handoff, or the stage whose external effect it gates). Carry in the open items earlier stages recorded
   (system-test-author, system-test). An outcome stated only in the summary has no end state; an empty list says
   every outcome was observed.
4. Keep verified product criteria apart from pending release verification: a case not yet due stays pending with
   owner and prerequisites, so release can proceed. Release readiness is not a claim that every consumer behaviour
   was observed.
5. Classify every selected case in `summary` passed, failed, blocked, not-run or justified N/A; reconcile each
   affected requirement clause with its case, required surface and due phase, checked surface, candidate, status
   and evidence. A pass on another surface only supports; source, HTTP or DOM structure alone cannot close a
   rendered interaction. Missing evidence for a due case stays incomplete. Check that no clause or case was
   dropped; claim no requirement met while a required observation is unrun.
6. Route each gap: missing product work, stale evidence, or a failed or missing due check goes to replan with one
   corrective `work_items` entry each. A missing delivery prerequisite is named in `summary` for release-plan; blocked
   only when nothing can proceed. Acceptance executes no release and proves no remote consumer boundary.
7. A material prerequisite ambiguity, pending or corrective dependency or acceptance gap: request a Backchain
   `review` / `audit` as the Backchain guidance below says; cite its receipt in `evidence_refs`.
""",
    "release-plan": """\
1. Revalidate the integrated test plan for the release target: the latest done system-test-author record after the
   most recent accepted replan, HOME/environment.md ## Harnesses and suites, the system-test result (OUTER
   test-planning handshake); pending, repeat and blocked results are not plan authority. Use Target-native test
   selection for this payload and its deploy or promotion operation, including any revised gate. Reuse applicable
   tests and facilities (Reusable test facilities); add checks only for changed boundaries or coverage gaps, and
   record each new facility's locator, interface, readiness or gap, owner and revalidation condition. An unmet
   earlier deployment or test prerequisite: report replan with corrective work and evidence (ShipLoop reruns the
   outer stages).
2. Write the release steps in `summary` and HOME/environment.md (item 8): target and candidate identity, permission,
   prerequisites, user impact, monitoring, stop conditions. Every operation the user-visible outcome needs is a
   named step with its exact command and authorization status: the deploy, each access or visibility change (for
   example assigning a permission set, activating an app or tab), each browser session a consumer check needs with
   its browser tool. A step no approval covers is a pending approval named now. Keep source return, artifact
   publication, deployment, promotion and consumer verification as separate steps. Order the remaining schema,
   data, service and cutover work with its durable execution owner, observations and recovery limits (Release
   operation guidance, State and data assessment).
3. Record each step's delivery authority in `summary`. A plan authorizes and performs no external operation; a
   required target or authority gap is blocked.
4. Write the rollback procedure in `summary` and HOME/environment.md ## Commands. Isolated run: write it for the
   source return the packet states (return route and rollback recipes come from workspace.md), as plain `git`
   commands with that route's SHAs and branch names, never this run's absolute paths, never for another route
   (Workspace return guidance). Source return happens at release or handoff, not here. Use an authorized delivery
   route from the execution checkout when available (Environment promotion guidance). If the return must precede
   the consumer checks, record the ordering conflict and keep the disposition incomplete; never claim an earlier
   check observed a future return-triggered effect.
5. Write the release test plan in `summary` and HOME/environment.md ## Harnesses and suites: pre and post check
   owners, commands or case selectors, independent expected outcomes, prerequisites, execution versus target
   locations, remote test-definition revision, setup, test and teardown, fixture isolation, sharing and cost,
   cleanup and stop conditions. State what release-check must establish before release, what release-verify
   confirms after, and which observations and cleanup each owns. Each post-release confirm command names the output
   showing the result present and the output showing it absent; release-check runs it once before the real deploy to
   prove it tells them apart.
6. Post-release consumer checks go in `consumer_checks`, shaped like test_commands (a `check` row is judged by exit
   code, no ids or min_tests). ShipLoop runs every one when release-verify reports done and refuses unless each
   passes: in an isolated run with a completed return, in a clean copy of the returned result (no Git history,
   nothing the return plan excluded, no ignored or unmanaged file); with none yet, in the work area, and says so.
   Write paths relative to the starting directory, put what a fresh consumer needs (install, build) in the check,
   and never write into the user's checkout by absolute path. A check only a person can make is an open item in
   `assumptions` (who, where, what to report) with release-verify or handoff as `consumer`, not a command. None
   applies: empty list with `consumer_checks_na` and the reason.
7. `consumer_entry`: `how` a person reaches the result (App Launcher name and URL path, command, page) and the
   repository `sources` files that create that entry.
8. Update HOME/environment.md: target under ## Targets and runtimes; deploy, dry-run, rollback and confirm commands
   under ## Commands; approvals and accounts under ## Access and accounts.
9. Cite HOME/environment.md in `evidence_refs`; the decisions and constraints the plan rests on go in `summary`.
""",
    "release-check": """\
1. Name the release plan you check: the latest done release-plan and system-test-author records after the last
   accepted replan (OUTER test-planning handshake); action, result and plan locators in `evidence_refs`. Guess no
   missing plan: recover it, or report `repeat` (`replan` for missing product work).
2. Against the current target, record in `summary` (evidence in `evidence_refs`): candidate identity and that its
   evidence is current, the target and prerequisites, required approvals, rollback readiness, the execution owner's
   readiness, any target concurrency condition (Release operation guidance).
3. Run the dry-run form of the planned deploy (for example `sf project deploy validate`) once; save the output in
   RUN/notes/<action>-release-check.md and cite it in `evidence_refs`.
4. Run each `consumer_checks` post-release confirm command once against the current target; save its "not there yet"
   output in the same file. A confirm command that cannot tell present from absent is fixed now in
   HOME/environment.md ## Commands and rerun.
5. Isolated run only: run the packet's plan-return command, then decide every undecided path with review-return (a
   dry run; decisions are kept for the return at release). Compare review-return's expected return with the
   procedure in HOME/environment.md; if they differ, correct the procedure and rerun plan-return.
6. Keep stale or failed evidence in `evidence_refs` as is; replay or promote nothing for a fresh observation. A
   material change to code, tests, fixtures, configuration or target invalidates the observations it affects: rerun
   those through the planned route, reuse the rest only with identity and relevance stated.
7. External release N/A waives not items 2-4 for the local candidate (Delivery completion guidance); record a
   justified N/A in `summary` with what you assessed.
""",
    "release": """\
1. Name the release plan and release-check result you act on: the latest done release-plan and system-test-author
   records after the last accepted replan (OUTER test-planning handshake), and release-check's result; locators in
   `evidence_refs`. Recover or report a missing plan (`repeat`, `replan` for missing product work); guess no command.
2. Confirm the exact target, operation, authority (the recorded grant; Delivery authority mapping) and conditions
   are current and release-check's dry run passed against this candidate. If code, tests, fixtures, configuration or
   target changed since, rerun the affected checks first. Anything unmet: release nothing, report `blocked` or
   `replan` with the reason.
3. Run the planned release operation once; save the provider's receipt in RUN/notes/<action>-release.md and cite it
   in `evidence_refs`.
4. Follow it to a terminal state (accepted or running is not done; Release operation guidance). Check postconditions
   now and record in `summary`, separately, the operation's effect and the released artifact's identity.
5. Uncertain outcome (lost reply, timeout, partial receipt): keep every receipt and reconcile with the provider's
   lookup, retry, parameter-binding and conditional-mutation semantics before any retry. Never replay a merge, push,
   deployment or promotion only to complete the graph.
6. Isolated run only: return the candidate (Workspace return guidance): run the packet's plan-return, decide every
   undecided path with review-return, run the packet's return command; the receipt path goes in `evidence_refs`.
7. Release not applicable: record the concrete reason and what you assessed in `summary`. Observe no consumer
   behaviour here; release-verify does.
""",
    "release-verify": """\
1. Name the plans you verify against: the latest done release-plan and system-test-author records after the last
   accepted replan (OUTER test-planning handshake); action, result and plan locators in `evidence_refs`. Recover or
   report a missing plan; guess no command, drop no required case, deploy to make no check available.
2. Run each `consumer_checks` command the release-plan result recorded against the current target (Release operation
   guidance). Keep source synchronization, artifact identity, operation receipt and real consumer behaviour as four
   separate facts in `summary` (Consumer delivery evidence guidance). A source or local test pass does not discharge
   a deployed interaction you did not observe.
3. Browser surface, per required clause record: the consumer entry reached after authentication, the account or
   target, the visible feature, the action and its outcome. Keep non-secret routing state. Require app chrome or
   branding only when the spec asks; an embedded feature can satisfy its accepted boundary.
4. Classify every selected case in `summary` passed, failed, blocked, not-run or justified N/A (Deployment and
   handoff guidance); reconcile each affected requirement clause with its case, required surface and due phase,
   checked surface, candidate, status and evidence. A pass on another surface only supports; source, HTTP or DOM
   structure alone cannot close a rendered interaction. A case not yet due keeps its phase, owner and
   prerequisites. Check that no clause or case was dropped; claim no requirement met while a required observation
   is unrun.
5. A blocked or unknown check stays incomplete. Keep earlier receipts; do not release again blindly.
6. A case needing a signed-in browser or a person's action this host cannot perform: do not loop on it. Record an
   open item in `assumptions` with the steps for that person (where to go, such as a menu entry or URL path, what to
   do) and what they report back; verify every other case. Only when the release cannot be accepted without it,
   report `blocked` with `awaiting` kind `present`; the person's report resumes the run and only the blocked cases
   are rechecked against the same release.
7. Isolated run: this stage cannot return (Which checkout release-verify observes). A defect the checks find in the
   delivered result goes through `replan` with one corrective work item; release then returns the fix. Write
   nothing inside the user's checkout (a file there makes the return receipt stale and blocks handoff).
8. Local-only work: verify the current local candidate and its consumer behaviour; external activation N/A does not
   make these checks N/A.
9. A material change to code, tests, fixtures, configuration or target invalidates the observations it affects:
   rerun those, reuse the rest only with identity and relevance stated.
10. `lessons`, each in detail: `learned`, `considerations` (decisions and risks that matter), `open_next` (what a
    later run should pick up). ShipLoop commits them as the run's learnings, read at intake.
11. Update HOME/environment.md with what the release showed about targets, commands and access.
""",
    "operations": """\
1. Reopen the observability coverage in HOME/environment.md and HOME/architecture.md; cite the sections used in
   `evidence_refs`.
2. Check each against the running system and record in `summary`: monitoring, alerting, log and diagnostic access,
   recovery ownership (who restores and how; the rollback works), support documentation, cleanup, revalidation needs
   (Deployment and handoff guidance). A plan or configuration file is not evidence the service is observed and
   supported.
3. Map each relevant event to its authoritative owner, existing sink and operator retrieval (Service discovery
   guidance), successful and failed logins included where the system authenticates. An inaccessible log is an
   evidence gap, not proof of no logging.
4. Close only evidenced gaps this run owns. Duplicate no provider logs; treat not every failure as an incident; keep
   the required audit-failure and recovery policy.
5. Write the current log and audit retrieval and recovery locators, with observation date and open limits, to
   HOME/environment.md (Service handoff guidance).
6. A justified N/A in `summary` only after assessing the actual operational boundary: what you assessed, why it does
   not apply.
7. Name the release-plan and system-test-author records you rely on (latest done after the last accepted replan;
   OUTER test-planning handshake) with locators in `evidence_refs`. A material change to code, tests, fixtures,
   configuration or target invalidates the observations it affects: rerun those, reuse the rest only with identity
   and relevance stated. An already-due obligation still failed, blocked or unrun stays open, named in `summary`
   with its owner; repair it with no new positive observation.
""",
    "handoff": """\
1. `summary`, one line each, evidence in `evidence_refs`: source (and its return), tests, integration, release,
   consumer behaviour, operations (Deployment and handoff guidance). Base each on a current observation; an intent,
   stale green result or conversation summary is not evidence. Name the release-plan and system-test-author records
   relied on (latest done after the last accepted replan; OUTER test-planning handshake), locators in
   `evidence_refs`.
2. Classify every selected case passed, failed, blocked, not-run or justified N/A; reconcile each requirement clause
   with its case, required surface and due phase, checked surface, candidate, status and evidence. A pass on
   another surface only supports; source, HTTP or DOM structure alone cannot close a rendered interaction. A case
   not yet due keeps its phase, owner and prerequisites; missing due evidence stays incomplete. Claim no
   requirement met while a required observation is unrun.
3. State where release-verify's consumer checks ran (the packet's "Consumer checks (release-verify)" line) or that
   none ran. Checks that ran in the work area did not observe the user's checkout: list that as a limit.
4. `summary` lists every open item still unverified (product-acceptance's `unverified` list and every other stage's
   result), each with who does what and what they report back; add follow-up work, blockers and revalidation
   conditions.
5. Isolated run: handoff needs a current return receipt. If release did not return the candidate, run the packet's
   plan-return, decide every undecided path with review-return, run its return command (Workspace return guidance);
   receipt path in `evidence_refs`.
6. From the returned project, without the run directory, check the knowledge survives: durable documentation links
   resolve in the returned repository (HOME/spec.md, HOME/environment.md, HOME/architecture.md); the AD-<n> entries
   in HOME/architecture.md hold the current service decisions, ownership, unresolved boundaries and revalidation
   conditions (Service discovery guidance); their source and check locators open for a fresh reader. Keep the prior
   baseline's as-of account (Current-system baseline guide). Fix a broken link or missing entry in HOME/ now.
   Work-item context and earlier result references are not a durable index.
7. Read release-verify's `lessons` (quoted in the hand-offs); carry its open-next items into the follow-up work in
   `summary` and report any conflict with what you observed.
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
    "step-plan": "the newly created bounded steps and any parallel or serial execution graph, criteria, test commands, expectations, step skills, conventions and diagnostic obligations",
    "test-spec": "the test cases, their independent oracles, RED/GREEN definitions and command IDs",
    "validate-existing": "the expectation checks, preparatory fixes and environment repairs",
    "implement": "one implementation step's diff: its task and criteria, scope, code contracts, diagnostics, error behaviour, architecture fit and skill use",
    "test": "the item's executable tests, their oracles and suite registration, and the passing command evidence",
    "document": "code and user/operator/project documentation updates",
    "verify": "work-item acceptance evidence, the whole-change review and remaining limitations",
    "carry-forward": "durable learning, the revised queue, the skill decision, pending obligations and revalidation conditions",
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


IMPLEMENTATION_STAGES = stage_spec.with_block("code-craft")


BACKCHAIN_STAGES = stage_spec.with_block("backchain")
TEST_DECISION_STAGES = stage_spec.with_block("test-decision")
TEST_FACILITY_HANDOFF = """\
Test facilities (Reusable test facilities): reuse, configure or extend the existing frameworks and helpers before
defining the smallest missing facility. Read the selected skill and MCP references first; never assume a named skill
or MCP is available or authorized. Record each facility's definition locator, interface, readiness or gap, owner and
revalidation condition in the repository test documentation and in evidence_refs. A stage that writes work_items
also puts the locator in the affected item's context. The stage that owns missing prerequisite work builds and
validates it, within its scope, before the checks that depend on it. Readiness is not test execution; a later stage
reopens the recorded definition instead of inventing another facility.
"""
TEST_DECISION_HANDOFF = """\
Test decisions: reopen the item's test decision and the harness and suite decisions in HOME/environment.md. In the
summary, say which decisions you retain, refine or supersede, and why; put their locators and the step plan's in
evidence_refs. Reassess a missing decision here. A recorded completion does not prove a harness, fixture or target
still works.
"""
OUTER_TEST_HANDOFF = """\
OUTER test plans (OUTER test-planning handshake): the current plans are the latest done system-test-author and
release-plan records after the most recent accepted replan; pending, repeat, and blocked results are not plan
authority, and earlier records are history to revalidate. Name the plan you rely on and put its action, result and
plan locators in `evidence_refs`. Revalidate it for the current candidate and target before relying on it. Recover
a missing plan or report the incomplete or corrective outcome; never guess a command, drop required coverage, or
deploy to make a check available. A plan is not execution evidence. A material change to code, tests, fixtures,
configuration or target invalidates the observations it affects: rerun them through the authorized route, and reuse
unaffected evidence only with its identity and relevance stated.
"""
BACKCHAIN_NATIVE_CALLS = {
    "plan": ("plan", "draft"),
}
BACKCHAIN_AUDIT_STAGES = BACKCHAIN_STAGES - set(BACKCHAIN_NATIVE_CALLS)

# Run-level Backchain passes option (state key ``backchain_passes``): how many review passes the
# Backchain planning child may take.  ``one`` (the default for new runs) is one review/fix/check cycle,
# ``converge`` is two consecutive trivial reviews, ``none`` offers no whole loop at plan.  The CLI, the
# state and SPEC S-10's carve-out name the same three.
BACKCHAIN_PASSES_MODES = ("one", "converge", "none")
DEFAULT_BACKCHAIN_PASSES = "one"


def _require_backchain_passes(backchain_passes: str) -> None:
    if backchain_passes not in BACKCHAIN_PASSES_MODES:
        raise ValueError(f"unknown backchain passes option: {backchain_passes!r}")


def offers_whole_backchain_loop(stage: str, backchain_passes: str) -> bool:
    """Whether `stage` may request a whole `plan`/`draft` Backchain loop in a run with this option.

    The one definition, used for the plan packet's loop text here and for the resource block the navigator
    prints: a stage that does not offer the loop prints the read-only audit route and the loop-resource status.
    """
    _require_backchain_passes(backchain_passes)
    return stage in BACKCHAIN_NATIVE_CALLS and backchain_passes != "none"


# The resource the read-only audit needs (the `backchain-caller/v1` contract); the other six serve a whole loop.
BACKCHAIN_AUDIT_RESOURCE = "Backchain backchain-caller/v1 resource"


def backchain_skills_root() -> Path:
    """The skills directory of this plugin install: where Backchain and the Until Loop adapter sit."""
    return Path(__file__).resolve().parent.parent.parent


def installed_improve_card() -> Path:
    """The Improve card installed beside ShipLoop in this plugin install, by file location (never a name or PATH search).

    The same skills directory as the Backchain and Until Loop resources.  Whether it is usable is
    ``shiploop_standalone_improve.resolve_skill``'s decision, not this function's.
    """
    return backchain_skills_root() / "improve" / "SKILL.md"


def resolved_backchain_resources() -> tuple[tuple[str, str], ...]:
    """Resolve the fixed Backchain/Until Loop resources from this plugin install."""
    skills_root = backchain_skills_root()
    resources = (
        ("Backchain SKILL.md", "backchain/SKILL.md"),
        (BACKCHAIN_AUDIT_RESOURCE, "backchain/references/caller-contract.md"),
        ("Backchain references/convergence.md", "backchain/references/convergence.md"),
        (
            "Backchain prompts/convergence-review.prompt.md",
            "backchain/prompts/convergence-review.prompt.md",
        ),
        ("Until Loop ADAPTER.md", "improve/runtime/until-loop/ADAPTER.md"),
        (
            "Until Loop references/runtime-ephemeral.md",
            "improve/runtime/until-loop/references/runtime-ephemeral.md",
        ),
        (
            "Until Loop scripts/until_loop_ephemeral.py",
            "improve/runtime/until-loop/scripts/until_loop_ephemeral.py",
        ),
    )
    resolved = []
    for label, relative_path in resources:
        path = skills_root / relative_path
        value = (
            str(path.resolve())
            if path.is_file()
            else f"MISSING: skills/{relative_path}"
        )
        resolved.append((label, value))
    return tuple(resolved)


# Record only: the navigator prints the command; nothing refuses a failing check.
BACKCHAIN_CHECK = ("Run the printed `backchain-check` after each candidate revision; a failure is a loop finding; "
                   "cite its receipt in `evidence_refs`.\n")


_BACKCHAIN_ROUTE = """\
Follow the packet's Backchain planning guide for this stage's scoped outcome,
prerequisite and consumer review. Carry selected requirement sections and test
locators through the plan and existing result/context fields. The only Backchain
call route is `source-aware-native`; ShipLoop carries no embedded Backchain mode.

"""
# Printed only where a whole loop may start (plan): the resource gate, the record rules, the child's scope.
_BACKCHAIN_PLAN_CALL = """\
A `source-aware-native` call needs every resource in the packet's printed
"Selected Backchain and Until Loop resources" block below. A `MISSING: ...` entry
blocks the route for that named resource: report it as the blocker, not as
unverifiable, and never substitute a sibling, cache or other install. Record the
binding id, candidate and receipt paths in `evidence_refs` and work-item `context`.
A structural plan, planned check, or experiment that merely ran is not execution
evidence or a passed experiment. Material findings remain visible and cannot clear
ordinary Improve. The planning guide's Source-aware native caller section holds the
capability check the host judges, the incompatibility of an old custom Backchain
loop, and the no-fallback rule.

The Until Loop child is plan-only when invoked by Backchain for dependency analysis:
it may change the candidate plan and permitted planning companions, but may not
commit, push, merge, execute the project, or broaden scope. These restrictions
belong to that Backchain child, not the separate Improve executor's authority.

"""
_BACKCHAIN_AUDIT_HEAD = """\
Request action `review` / stage `audit` only for a material prerequisite
ambiguity, pending/corrective dependency or acceptance gap: a read-only, one-pass
diagnostic that changes no candidate and completes no parent action. A material
finding goes to the stage owner, who within explicit authorized edit bounds may
request exactly one action `repair` / stage `revise`, a whole native operation
that needs the loop resources named in the planning guide's Source-aware native
caller section (the packet's "Loop resources" line reports them)."""
# Modes one and none.  An instruction to write the marker line, not a gate field: the audit text never names
# `required_trivial_reviews`; the child's gate and exit condition are the ones Backchain's convergence reference
# defines for the marker line, and without the line a repair/revise child runs that reference's two-review default.
_BACKCHAIN_AUDIT_ONE_PASS = """ A repair/revise child runs one review/fix/check cycle: put the line
`Backchain passes: one` beside the binding marker in the child request, as Backchain's
convergence reference defines it."""
_BACKCHAIN_AUDIT_WHOLE = """ A whole `plan`/`draft` is requested only
at `plan`."""
# Mode none, at every stage: the run requests no whole loop, so the audit text says that in its place.  `one` is
# the only marker value Backchain's convergence reference defines, so the text does not print `none` as one.
_BACKCHAIN_AUDIT_WHOLE_NONE = """ No whole `plan`/`draft` is requested in this run."""
_BACKCHAIN_AUDIT_TAIL = """ A MISSING loop resource blocks repair/revise; no other install
substitutes. A forbidden revision, nonterminal child or unresolved finding stays
incomplete and is not submitted as a completed parent action.
"""
_BACKCHAIN_IMPROVE_OWNER = """\
Improve is a broader review than Backchain's diagnostic. It reads Backchain findings and the
returned candidate as ordinary inputs; it does not request or count Backchain
passes, and creates no `active_backchain` child, nested Until Loop, retry
dispatcher or new callback. For a dependency diagnostic use a one-pass Backchain
primitive, never a whole Backchain→Until Loop child. A Backchain child is
plan-only (no commit, push, merge or project execution). These restrictions
belong to that Backchain child, not the separate Improve executor's authority.
A protected or out-of-scope change follows the existing blocked or recovery route.
"""


# The plan-stage gate sentence in `converge` mode: the runtime's own two-review gate, as it was printed before the
# Backchain passes option existed.
_BACKCHAIN_PLAN_GATE_CONVERGE = """\
Until Loop owns the callback handle, progress, its `required_trivial_reviews: 2` gate for
two consecutive distinct complete trivial/no-change dependency reviews, recovery, and
terminal transition; Backchain and ShipLoop do not copy that runtime or create another
controller.
"""
# In `one` mode the host writes the gate itself, so the packet prints the gate and the exit condition to copy.
# Owner decision 2026-10-04 (docs/shiploop-fast-planning-plan-2026-10-04.md, "Backchain single pass: mechanism").
# The vendored Until Loop completes at gate 0 on the first report that assesses the exit as satisfied, so the exit
# text is what makes one cycle enough: under the two-review exit text Luna (skill-craft 1.16.1) reported
# `unsatisfied` through pass 6. Backchain's convergence reference states the same clauses for the marker line;
# test/shiploop-navigator-contract.test.py BackchainGateDocumentsTest keeps the two the same.
_BACKCHAIN_PLAN_GATE_ONE = """\
Until Loop owns the callback handle, progress, its review gate, recovery, and terminal
transition; Backchain and ShipLoop do not copy that runtime or create another controller.
Backchain passes: one. Write the child's start contract with `required_trivial_reviews: 0` and this
exit condition verbatim, appending only case-specific clauses: One complete dependency
review/fix/check cycle has run; every finding of that cycle is repaired within the edit
bounds; every `Confirm by` clause on a step this cycle may change meets the planning guide's
Outcomes rule; the printed `backchain-check` is ok on the final candidate and its receipt is
cited; final candidate-specific domain evidence is saved. A pass that completes that cycle
reports `exit_assessment: satisfied` even when it repaired the candidate; Until Loop then
completes the child and no second review runs. Put the line `Backchain passes: one` beside the
binding marker in the child request.
"""


# Printed with the one-pass gate only: its "Write the child's start contract ... verbatim" reads as an order, and the
# `converge` gate text has no such sentence.  Says what the script enforces (nothing refuses a plan without the child)
# and what it cannot see; the dependency audit is the planning guide's duty either way.
_BACKCHAIN_PLAN_CHOICE = """\
The `plan`/`draft` request is your choice: nothing refuses a plan without it, and ShipLoop
cannot see whether the child ran. The planning guide's dependency audit is not optional on
either route. Say in this result's `summary` which route you took and why. The start
contract below applies only if you request the child. The printed `backchain-check` reads
a candidate graph in Backchain's plan schema (Backchain SKILL.md, "Plan document shape"),
not a prose plan.
"""


def _one_pass(backchain_passes: str) -> bool:
    """Whether a Backchain child's gate text is the one-pass text (every mode but `converge`).

    In `none` no whole `plan`/`draft` is offered, but a `repair`/`revise` after a finding still starts a child,
    and that child runs one pass.
    """
    return backchain_passes != "converge"


def _backchain_guidance(stage: str, *, improve_owner: bool = False,
                        backchain_passes: str = DEFAULT_BACKCHAIN_PASSES) -> str:
    """Return host-mediated caller guidance without adding navigator state.

    The loop text and the resource gate are printed only at the stage that may start a whole loop (plan);
    the other Backchain stages print the read-only audit route and the rule that a material finding may
    request one repair/revise.

    ``backchain_passes`` is the run's option (see BACKCHAIN_PASSES_MODES).  ``converge`` prints the two-review
    gate; the default ``one`` prints the one-pass gate and exit condition at plan and a one-line pointer at the
    audit stages.  ``none`` offers no whole loop, so plan prints the audit route the four audit stages print
    (see offers_whole_backchain_loop), and every audit stage says no whole `plan`/`draft` is requested.
    """
    _require_backchain_passes(backchain_passes)
    if improve_owner:
        return _BACKCHAIN_ROUTE + _BACKCHAIN_IMPROVE_OWNER
    if offers_whole_backchain_loop(stage, backchain_passes):
        action, operation = BACKCHAIN_NATIVE_CALLS[stage]
        return _BACKCHAIN_ROUTE + _BACKCHAIN_PLAN_CALL + f"""\
Through `source-aware-native`, the current stage host may
request exactly one action `{action}` / stage `{operation}` within the packet's
scope. Backchain invokes the selected actual Until Loop for its dependency-specific
review/fix/check cycle using `Backchain standalone Until Loop binding: <binding-id>`.
""" + (_BACKCHAIN_PLAN_CHOICE + _BACKCHAIN_PLAN_GATE_ONE if _one_pass(backchain_passes)
       else _BACKCHAIN_PLAN_GATE_CONVERGE) + """\
Backchain returns opaque actual Until Loop terminal evidence only after the child reports
`complete` and its exact receipt is saved. A nonterminal, unresolved, or incompatible
child leaves this parent action incomplete and must not be submitted as a completed parent
action. Only that exact `complete` receipt plus final candidate identity and domain evidence
permits Backchain planning convergence. The draft is a proposed candidate; ShipLoop still owns
acceptance and lifecycle state.
""" + BACKCHAIN_CHECK
    if stage in BACKCHAIN_STAGES:  # an audit stage, or plan in a run that offers no whole loop
        audit = (_BACKCHAIN_AUDIT_HEAD + (_BACKCHAIN_AUDIT_ONE_PASS if _one_pass(backchain_passes) else "")
                 + (_BACKCHAIN_AUDIT_WHOLE_NONE if backchain_passes == "none" else _BACKCHAIN_AUDIT_WHOLE)
                 + _BACKCHAIN_AUDIT_TAIL)
        return _BACKCHAIN_ROUTE + audit + BACKCHAIN_CHECK
    return _BACKCHAIN_ROUTE + """\
This stage has no native Backchain action. Keep relevant findings in ordinary
notes and route a material planning gap through its authorized owner.
"""


# The Backchain item of the spec and plan duties (packet re-cut, 2026-10-11): the stages whose duty folds the Backchain
# caller guidance, so prompt() prints no second copy of it.  The other Backchain stages still print _backchain_guidance.
BACKCHAIN_FOLDED_STAGES = ("spec", "plan")

_BACKCHAIN_ITEM_AUDIT = """\
Request a Backchain `review` / `audit` only for a material prerequisite ambiguity, a pending or corrective
    dependency, or an acceptance gap (Backchain planning guide). It is read-only, one pass, changes no candidate and
    completes no parent action. On a material finding you may request exactly one `repair` / `revise` within your
    edit bounds:
    - it needs every loop resource on the Loop resources line; a MISSING one blocks it, and no other install
      substitutes;
{marker}    - a forbidden revision, a nonterminal child or an unresolved finding leaves this stage incomplete: do not report
      done.
    Run the printed `backchain-check` after each candidate revision; a failure is a finding. Cite its receipt in
    `evidence_refs`. The only call route is `source-aware-native`.{whole}"""
_BACKCHAIN_ITEM_MARKER = "    - put the line `Backchain passes: one` beside the binding marker in the child request;\n"
_BACKCHAIN_ITEM_PLAN = """\
Run the dependency audit of the Backchain planning guide on every route. You may also request one Backchain
    `plan` / `draft` through `source-aware-native`, the only call route.{choice} If you request it:
    - every resource in the printed "Selected Backchain and Until Loop resources" block is required. A `MISSING`
      entry is the blocker to report; never substitute a sibling, cache or other install;
    - Backchain runs the selected Until Loop with `Backchain standalone Until Loop binding: <binding-id>`. The child
      is plan-only: it may change the candidate plan and permitted planning companions, and may not commit, push,
      merge, run the project or broaden scope. {gate}
    - record the binding id, candidate and receipt paths in `evidence_refs` and the affected items' `context`;
    - report done only with the child's exact `complete` receipt saved, with the final candidate's identity and its
      domain evidence. A nonterminal, unresolved or incompatible child leaves this stage incomplete. The draft is a
      candidate; ShipLoop owns acceptance.
    Run the printed `backchain-check` after each candidate revision. It reads a candidate graph in Backchain's plan
    schema (Backchain SKILL.md, "Plan document shape"), not a prose plan. A failure is a finding; cite its receipt in
    `evidence_refs`. A structural plan, a planned check or an experiment that merely ran is not execution evidence.
    Keep material findings visible in `summary`. Carry the selected requirement sections and test locators through
    the plan and the items' `context`."""
_BACKCHAIN_PLAN_CHOICE_ITEM = (" Nothing refuses a plan without it and ShipLoop cannot see whether the child ran, "
                               "so say in `summary` which route you took and why.")
_BACKCHAIN_GATE_ONE_ITEM = """Until Loop owns the callback handle, progress, the review gate,
      recovery and the terminal transition; copy none of it. Write the child's start contract with
      `required_trivial_reviews: 0` and this exit condition verbatim, appending only case-specific clauses: One
      complete dependency review/fix/check cycle has run; every finding of that cycle is repaired within the edit
      bounds; every `Confirm by` clause on a step this cycle may change meets the planning guide's Outcomes rule; the
      printed `backchain-check` is ok on the final candidate and its receipt is cited; final candidate-specific
      domain evidence is saved. A pass that completes that cycle reports `exit_assessment: satisfied` even when it
      repaired the candidate, and no second review runs. Put the line `Backchain passes: one` beside the binding
      marker in the child request;"""
_BACKCHAIN_GATE_CONVERGE_ITEM = """Until Loop owns the callback handle, progress, its
      `required_trivial_reviews: 2` gate for two consecutive distinct complete trivial/no-change dependency reviews,
      recovery and the terminal transition; copy none of that runtime and create no other controller;"""


def _backchain_item(stage: str, backchain_passes: str) -> str:
    """The Backchain item text of the spec or plan duty, for the run's Backchain passes option."""
    _require_backchain_passes(backchain_passes)
    if stage == "plan" and offers_whole_backchain_loop(stage, backchain_passes):
        one = _one_pass(backchain_passes)
        return _BACKCHAIN_ITEM_PLAN.format(choice=_BACKCHAIN_PLAN_CHOICE_ITEM if one else "",
                                           gate=_BACKCHAIN_GATE_ONE_ITEM if one else _BACKCHAIN_GATE_CONVERGE_ITEM)
    whole = ""
    if stage == "plan":
        whole = " No whole `plan`/`draft` is requested in this run."
    return _BACKCHAIN_ITEM_AUDIT.format(marker=_BACKCHAIN_ITEM_MARKER if _one_pass(backchain_passes) else "",
                                        whole=whole)


BACKCHAIN_GUIDANCE = _backchain_guidance("plan")


def _require_stage(stage: str) -> None:
    if stage not in DUTIES:
        raise ValueError(f"unknown navigator stage: {stage!r}")


def _require_delegation(delegation: str) -> None:
    if delegation not in DELEGATIONS:
        raise ValueError(f"unknown navigator delegation: {delegation!r}")


def _require_planning_review(planning_review: str) -> None:
    if planning_review not in stage_spec.PLANNING_REVIEW_MODES:
        raise ValueError(f"unknown planning review option: {planning_review!r}")


# Inline runs replace only the chain-specific paragraphs of these duties; the
# ask-agent text above stays the single source for the delegated route.
_INLINE_DUTY_PARAGRAPHS = {
    "step-plan": (_STEP_PLAN_GRAPH, _STEP_PLAN_INLINE),
    "implement": (_IMPLEMENT_CHAIN, _IMPLEMENT_INLINE),
    "verify": (_VERIFY_ASSEMBLY, _VERIFY_ASSEMBLY_INLINE),
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


def _inline_planning_handoff() -> str:
    return _PLANNING_HANDOFF.replace(*_INLINE_PLANNING_DIRECTIVE)


def _item_commit_rule(execution_mode: str | None) -> str:
    """The item commit rule document and verify print: ShipLoop's rule, then what happens to a file it leaves."""
    left = (stage_spec.item_left(execution_mode) if execution_mode else
            "Any other changed file is not part of the item commit: if the product needs one, report revise so the "
            "step plan declares it; otherwise delete generated output the product does not need.")
    return stage_spec.ITEM_COMMITS + " " + left


def duty(stage: str, *, delegation: str = ASK_AGENT, planning_review: str = "stage",
         backchain_passes: str = DEFAULT_BACKCHAIN_PASSES, execution_mode: str | None = None) -> str:
    """Return one stage duty with the run's implementation-route paragraph.

    ``planning_review`` is the run's option (see stage_spec.PLANNING_REVIEW_MODES): ``stage`` renders the
    text below unchanged, ``none`` swaps the sentences that promise an Improve child the run will not start
    (see _NO_REVIEW_SWAPS).  The literal default ``stage`` keeps catalog renders independent of the option's
    default.  ``backchain_passes`` picks the Backchain item of spec and plan; ``execution_mode`` (state key
    ``execution_mode``) picks what the commit rule says about a file the item commit leaves.
    """
    _require_stage(stage)
    _require_delegation(delegation)
    _require_planning_review(planning_review)
    _require_backchain_passes(backchain_passes)
    text = DUTIES[stage]
    if _BACKCHAIN_ITEM in text:
        text = text.replace(_BACKCHAIN_ITEM, _backchain_item(stage, backchain_passes))
    if _ITEM_COMMIT in text:
        text = text.replace(_ITEM_COMMIT, _item_commit_rule(execution_mode))
    if delegation == INLINE and stage in _INLINE_DUTY_PARAGRAPHS:
        delegated, inline = _INLINE_DUTY_PARAGRAPHS[stage]
        text = text.replace(delegated, inline)
    return _swapped(text, stage, planning_review)


# Planning review option ``none``: sentences that promise an Improve child at a planning stage the run starts
# none for, each swapped for text that does not.  One table of (stage, old, new) rows; ``*`` is text that
# packets of several stages carry (COMMON, the interaction guide, the inline planning handoff).  A row applies only for the recorded mode ``none``, so the stage-mode text is the text
# above, byte for byte.  Each ``old`` must occur exactly once in every stage-mode text it occurs in (the
# delegations and the plan's Backchain call are separate texts) and in at least one: the import-time check in
# _check_swaps fails when an edit to the text above leaves a row matching nothing or twice.
def _graph_order(stages: "frozenset[str]") -> list[str]:
    return [name for name in STAGES if name in stages]


_NONE_REVIEWED = ", ".join(_graph_order(stage_spec.reviewed_stages("none")))
_NO_REVIEW_SWAPS = (
    ("*", """\
after planning results (spec, test-strategy, plan, step-plan, test-spec,
system-test-author, release-plan), after each accepted implement step, and after""",
     "after planning results (" + _NONE_REVIEWED + "),\n"
     "after each accepted implement step, and after"),
)


def _stage_texts(stage: str) -> list[str]:
    """The stage-mode texts a swap row for ``stage`` may match: both delegations, and the plan's Backchain call."""
    if stage == "*":
        return [COMMON, INTERACTION_DESIGN, _inline_planning_handoff()]
    texts = [duty(stage, delegation=delegation) for delegation in DELEGATIONS]
    if stage in BACKCHAIN_STAGES:
        texts.append(_backchain_guidance(stage))
    return texts


def _check_swaps(rows: "tuple[tuple[str, str, str], ...]") -> None:
    """Fail at import when a swap row matches nothing, matches twice in one text, or names a stage the option skips."""
    for stage, old, new in rows:
        if stage != "*" and stage not in stage_spec.PLANNING_CHOICE_STAGES:
            raise RuntimeError(f"navigator planning review swap names a stage the option does not cover: {stage!r}")
        counts = {text.count(old) for text in _stage_texts(stage)}
        if counts not in ({1}, {0, 1}) or old == new:
            raise RuntimeError(f"navigator planning review swap for {stage!r} no longer matches its text once: "
                               f"{' '.join(old.split())[:70]!r}")
    # COMMON's schedule list is the stage-mode reviewed list, in graph order
    if ", ".join(_graph_order(stage_spec.reviewed_stages("stage"))) not in " ".join(COMMON.split()):
        raise RuntimeError("navigator COMMON lists a schedule other than the stage-mode reviewed stages")


def _swapped(text: str, stage: str, planning_review: str) -> str:
    """``text`` with the rows for ``stage`` applied when the run's planning review option starts no child there."""
    if planning_review != "none":
        return text
    for row_stage, old, new in _NO_REVIEW_SWAPS:
        if row_stage == stage:
            text = text.replace(old, new)
    return text


_check_swaps(_NO_REVIEW_SWAPS)


# What stands in the duties where the Backchain route paragraph stood, in a packet that prints the paragraph after the
# result template (the print-order unit: a lookup the packet file repeats whole goes behind the required text).
BACKCHAIN_STUB = "Backchain: the route's paragraph follows the result template."


def _prompt_parts(stage: str, *, delegation: str, backchain_passes: str, planning_review: str,
                  execution_mode: str | None) -> list[tuple[str, str]]:
    """The producer instruction as ``(kind, text)`` parts in print order; ``prompt`` joins them.

    ``kind`` is ``duty``, ``audit`` (the inline route's short optional audit line), ``backchain`` (the route paragraph of a
    stage that may call Backchain), ``craft`` or ``rules``.
    """
    parts = [("duty", duty(stage, delegation=delegation, planning_review=planning_review,
                           backchain_passes=backchain_passes, execution_mode=execution_mode))]
    # The shared blocks (interaction design, planning hand-off, work-item context, test facilities, test decisions,
    # OUTER test plans, selected-case reconciliation) are folded into the duties of the stages they applied to
    # (packet re-cut, 2026-10-11, R2/R3), so none prints here.  The constants stay as the one worded copy.
    if stage in INLINE_AUDIT_STAGES and delegation == INLINE:
        parts.append(("audit", INLINE_BACKCHAIN_AUDIT))
    elif stage in BACKCHAIN_FOLDED_STAGES:
        pass  # the Backchain item is folded into the duty; no loop budget block follows (Until Loop has no size limit)
    elif stage in BACKCHAIN_STAGES:
        parts.append(("backchain", _swapped(_backchain_guidance(stage, backchain_passes=backchain_passes), stage,
                                            planning_review)))
    if stage in IMPLEMENTATION_STAGES:  # implement only: where product code is written (owner, 2026-10-11)
        parts.append(("craft", CODE_CRAFT))
    parts.append(("rules", STAGE_RULES))
    return parts


def prompt(stage: str, *, delegation: str = ASK_AGENT,
           backchain_passes: str = DEFAULT_BACKCHAIN_PASSES,
           planning_review: str = "stage", execution_mode: str | None = None) -> str:
    """Return the single current producer instruction for a navigator graph stage.

    The navigator always passes the run's delegation, Backchain passes option and planning review
    option; the ask-agent default keeps catalog renders identical to runs recorded before the
    delegation setting existed, and the catalog renders the default of each option.
    """
    _require_stage(stage)
    _require_delegation(delegation)
    _require_backchain_passes(backchain_passes)
    _require_planning_review(planning_review)
    return "\n\n".join(text for _, text in _prompt_parts(
        stage, delegation=delegation, backchain_passes=backchain_passes, planning_review=planning_review,
        execution_mode=execution_mode))


def prompt_split(stage: str, *, delegation: str = ASK_AGENT,
                 backchain_passes: str = DEFAULT_BACKCHAIN_PASSES,
                 planning_review: str = "stage", execution_mode: str | None = None) -> tuple[str, str]:
    """``(prompt text, Backchain route paragraph)`` for a packet that prints the paragraph behind its result template.

    The first holds everything ``prompt`` returns, with ``BACKCHAIN_STUB`` where the paragraph stood; the second is the
    paragraph, or "" for a stage without one (the inline route's short audit line stays in place).  Joined back in place
    of the stub, the two are exactly ``prompt``.
    """
    _require_stage(stage)
    _require_delegation(delegation)
    _require_backchain_passes(backchain_passes)
    _require_planning_review(planning_review)
    parts = _prompt_parts(stage, delegation=delegation, backchain_passes=backchain_passes,
                          planning_review=planning_review, execution_mode=execution_mode)
    moved = next((text for kind, text in parts if kind == "backchain"), "")
    return ("\n\n".join(BACKCHAIN_STUB if kind == "backchain" else text for kind, text in parts), moved)


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
""" + REVIEW_FOCUS_CONDITIONS + """\
Do not reread history or rerun a check already recorded green at this commit
unless a finding depends on it. A pass that finds none of these is trivial.
"""


END_REVIEW_FOCUS = """\
End-of-work code review focus. Across every executed work item's change, trace
each new or changed public entry point with a valid, a boundary and an invalid
input, then review the change against the rubric below. Fix violations within
scope. A pass that finds no material violation is trivial.

""" + CODE_CRAFT

# The per-step Improve child's focus (owner decision 2026-10-10: an Improve child reviews every accepted implement step,
# whatever the planning review option says).  The step's tests are written later, so this review is the only check of
# the step's code before them; it carries the Code craft rubric verbatim because the child reads no other file reliably.
IMPLEMENT_STEP_REVIEW_FOCUS = """\
Implementation step review focus. This result is one step of the item's step
plan, and its tests are written later from the test spec, so this review is the
only check of the code before them. Review the step's diff (the step's paths since
the step began) and fix, within those paths, any of these:
- the change does not do the step's task, misses a criterion as the spec's R-<n>
  states it, or does work no criterion asks for (a later step's work, a feature
  the item does not request);
- a file changed outside the step's paths, or unrelated work reverted or
  reformatted;
- a new or changed public entry point that does not check its arguments before
  any effect, swallows an error or returns a success default (Code craft 2);
- a public function without its contract docstring, a comment that restates
  code, or dead code (rules 3-4);
- code placed outside HOME/architecture.md's ## Structure or ## Conventions, or a
  departure with no new AD-<n> under ## Decisions; a name that collides or is
  exported wider than needed (rule 8);
- a near-copy of existing logic, a new unit where an existing one could be
  reused, composed or augmented, or a dependency, option or fallback with no
  present need (rules 1, 9);
- a failure that is not diagnosable, or user-facing text assembled from
  fragments or bypassing the catalog (rules 6-7); for a UI step, a plain or
  static interaction where the plan calls for a rich one (rule 5);
- a step skill listed in the packet and not used, or used against its stated
  purpose, with no reason in the result;
- a behaviour the code now has that no test-spec case covers and the result does
  not list for the test stage;
- a recorded check command that fails, or a new lint finding on a changed line
  with no waiver, after your last edit.
Do not write tests, start a later step, or edit a recorded command. After your
last edit, rerun the step's recorded check commands and ShipLoop's lint for the
step's action (`shiploop lint --action`), and record their exit codes. Commit your
edits. A pass that finds none of these is trivial.

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
    """Compose the Improve child's prompt for ``stage``, adding the Backchain and coding-review guidance where the
    stage uses them.
    """
    _require_stage(stage)
    backchain = ""  # an Improve review never mentions Backchain (owner, 2026-10-11)
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
structural validation alone does not complete this handoff.
"""

    release_guard = ""
    if any(label == "Release operation guidance" for label, _ in STAGE_REFERENCES[stage]):
        # No Improve child runs at the release stage itself (stage_spec: release has no improve), so every Improve
        # that reads this guard is stage-scoped: it assesses and records, and never executes or replays a release
        # effect (SPEC S-3; environment-lifecycle.md#release-operation-ownership).
        performs = """\
its authority. A stage-scoped Improve assesses and records its handoff; it does not
execute or replay a release effect (a deployment, an MCP interaction or any other
release operation). Those run only at the release stage, with a recorded grant and
their required checks. Do not repeat unchanged release effects merely to advance the
review streak. Reconcile uncertain or partial outcomes by reading the recorded
receipts, without inventing provider guarantees; a retry belongs to the release
stage, under the release guidance, with the prior operation/receipt identity and the
provider's supported retry or idempotency procedure.
"""
        release_guard = """\
Read and retain Release operation guidance and the current operation/evidence
locators. Review this stage's plan, readiness checks, or observed outcome within
""" + performs + """\
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
    if stage == "discovery":
        baseline_guard = """\
For this discovery handoff, use the packet's Initial repository baseline
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
For a planning handoff (step-plan, test-spec), change no product code. For release/verification handoffs, reconcile an uncertain external
outcome rather than replaying it.
"""


if len(STAGES) != 24 or len(set(STAGES)) != len(STAGES):
    raise RuntimeError("navigator stage catalog must contain 24 unique stages")
if set(DUTIES) != set(STAGES) or set(IMPROVE_SCOPES) != set(STAGES):
    raise RuntimeError("navigator prompts do not cover the complete graph")


PROMPTS = {stage: prompt(stage) for stage in STAGES}
IMPROVE_PROMPTS = {stage: improve_prompt(stage) for stage in STAGES}
for _delegated, _inline in _INLINE_IMPROVE_REPLACEMENTS:
    if not any(_delegated in text for text in IMPROVE_PROMPTS.values()):
        raise RuntimeError("navigator Improve prompts lost a delegated-route phrase")


__all__ = (
    "ASK_AGENT",
    "BACKCHAIN_PASSES_MODES",
    "COMMON",
    "DEFAULT_BACKCHAIN_PASSES",
    "DELEGATIONS",
    "DUTIES",
    "END_REVIEW_FOCUS",
    "ENVIRONMENT_DISCOVERY_REQUIREMENTS",
    "CODE_CRAFT",
    "IMPLEMENTATION_STAGES",
    "IMPLEMENT_STEP_REVIEW_FOCUS",
    "IMPROVE_PROMPTS",
    "IMPROVE_SCOPES",
    "INLINE",
    "INNER",
    "INNER_GROUPS",
    "OUTER",
    "PLANNING_REVIEW_FOCUS",
    "PLANNING_REVIEW_STAGES",
    "PRELUDE",
    "PROGRESS_REPORTING",
    "PROMPTS",
    "STAGE_PURPOSE",
    "STAGE_REFERENCES",
    "STAGES",
    "STAGE_RULES",
    "duty",
    "improve_prompt",
    "inner_context",
    "prompt",
)
