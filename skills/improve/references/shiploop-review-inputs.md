# Improve: ShipLoop review inputs

The fixed review inputs of every ShipLoop Improve prompt, word for word; the handoff adds the focus, the stage's own scope and the locators. Where they say "the packet's" guide or policy, it is the line of that name in the handoff's reference list. [The core](shiploop-route.md#review-inputs) states what every review applies: open a section below only when its condition holds for this candidate.

## Every review

Read only for the full wording of what the core's Review inputs state.

Read the selected skill card and follow the Until Loop runtime bound by that card.  Use the
parent-provided candidate scope, prior producer result, relevant lessons, expected
check state, allowed edits, authority, and evidence/return locators.
The selected Improve card supplies execution capabilities and the review loop.
The stage requirements below qualify this candidate and its authority.
Freeze selected staged/unstaged/untracked candidate paths and excluded unrelated
work in the existing child scope, or retain the exact inventory locator when large.
An empty initial commit or unmoved HEAD does not replace named untracked candidate
files with the latest commit's diff. Git history supplies context, not scope.

Treat the relevant work-item `context`, parent `evidence_refs`, plan notes, and
packet-selected reference locators as parent-supplied cold-context inputs. Reopen
and revalidate only the sources relevant to this candidate, then retain a compact
current locator, decision, rationale, and revalidation result in the child review
notebook. Do not replace those source locators with copied transcripts, a new child
ledger, or an unverified summary.

Follow the selected Improve card's review, commit and completion policies under
this binding's authority; preserve explicit task overrides and an existing child's
frozen contract. The parent owns acceptance, callbacks and workspace return.
For a planning handoff (step-plan, test-spec), change no product code. For release/verification handoffs, reconcile an uncertain external
outcome rather than replaying it.

## Requirements, references and baseline

Read when the review needs the full wording of the Maintained requirements policy or the Reference handoff policy, or the candidate affects quality criteria or needs baseline evidence.

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

## Identity or access discovery

For identity or access discovery, use supported non-mutating probes and
sanitized evidence. Normal supported tool-managed authentication and tool
configuration metadata without session material remain allowed. Builders and
reviewers must not read, decode, retain, or report local authentication,
session, or credential-store contents.

## Interactions and UI

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

## Current-system recovery

For current-system recovery or affected product work, carry selected prior-baseline
and incoming-spec sections into this child's existing contract before review.
Check preservation, evidence/intent separation, consequential gaps and durable
retention within this candidate's scope; a package-guide link alone is insufficient.

## Planning results

Read when the candidate is the result of a planning stage (it produced plans, specifications or reference material).

For every planning-producing candidate, author coherent supporting reference
material with key accepted statements, decisions, constraints, acceptance context,
and exact source locators. It supplies planning-pass context; it is neither the
user prompt nor a second directive. Each reviewed step's task/ready/done
criteria remain its sole assignment. Register every generated planning file in
the producer result's `evidence_refs`. If this Improve result supplies a revised
`final_result`, preserve the prior registered references and add its new planning
files; do not discard evidence just because the reference material was consolidated.
Explicit local project documents may remain absolute references. A URL is a
reference-only citation until its needed material is supplied as a local artifact.

On the ask-agent route read "a second directive" as "a second worker directive" and "Each
reviewed step's task/ready/done criteria remain its sole assignment" as "The dispatch step's
task/ready/done contract remains the sole assignment".

## Repository-local skills

When this candidate selects, uses or changes a repository-local skill, carry its
repo index, selected entrypoint, effective input/default sources, applicable
product contract and validation locators from the parent's evidence/selection
note into this child's existing contract/review notes before the first review.
Review task fit, supported overrides, current defaults and preserved older uses;
for a split, check distinct triggers and retained consumers. Reuse of an unchanged
skill does not require an edit. A no-fit decision needs its inspected sources and
rationale. Missing execution or fresh-reader evidence stays untested. The host
authors this handoff; a successful runtime receipt alone cannot prove skill use.

## Tests and test evidence

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
