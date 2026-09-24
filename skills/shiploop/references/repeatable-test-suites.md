# Repeatable test suites

Use this guide while planning, authoring, reusing, and reviewing tests. It
strengthens the existing case plan, test bindings, and system-test ownership;
it does not add a framework, state/schema, stage, or second test catalog. Read
[test cases](testing-and-documentation.md#test-cases) for the existing case
record and [global system-test catalog](system-tests.md) for run-wide ownership.

## Select or revalidate the harness

During initial test strategy and planning, inspect the repository's current
runner, suite definitions, fixture helpers, CI commands, and applicable prior
run evidence. Select the existing harness when it fits, or record the concrete
reason a smaller direct check is sufficient. A prior run is a useful lead, not
proof that its harness, dependencies, target, or command still work.
If no adequate route exists, plan the smallest sufficient harness and its missing
prerequisites; justify new tooling by the gap rather than a category label.

Assess the actual platform, runtime, libraries, and browser surfaces alongside
that harness. Consider their supported testing systems: native runners, test
helpers, component fixtures, emulators, and inspection tools where relevant.
Prefer compatible existing or platform/library-supported mechanisms when they
meet the required outcome; integrate them into the repository's suite rather
than add a parallel stack by default. Verify current availability, supported
versions/interfaces, and local or remote execution prerequisites. A tool name
in documentation is not evidence that it is installed, accessible, or suitable.
For an affected remote system or delivery route, apply
[target-native test selection](#select-target-native-tests) before excluding its
native checks; local file inventory alone cannot settle that decision.

For browser behavior, consider Chrome DevTools or equivalent available inspection
tools, and Playwright or equivalent browser automation, to inspect and test the
actual end-browser surface. Pair these with `curl` or existing HTTP/API checks
when both protocol and rendered behavior matter. Choose
the tool by the observation needed, such as rendered DOM/CSS, console errors,
network behavior, interaction, or performance. Apply the existing
[lightweight and browser checks](testing-and-documentation.md#lightweight-and-browser-checks)
policy for surface selection, target/session identity, and access. Interactive
inspection or a recorded flow alone is not a regression assertion: retain the
useful finding as a repeatable test with an independent expected outcome and
suite entry when feasible. Otherwise retain the exact manual procedure and
evidence limits; do not count it as automated coverage.

At global planning, record the major harnesses and complementary diagnostic
tools, their roles and selection rationale in existing test-strategy evidence.
For every INNER change, revalidate the relevant selection against the changed
platform/library versions, interfaces, target, and browser behavior. Reuse an
unchanged, still-supported choice; perform targeted discovery for new surfaces
or gaps rather than restart the whole survey. Carry any revised choice and its
locator into the item plan, with setup/test/teardown and suite placement below.
Tool selection does not authorize an installation or remote operation.

The [Chrome DevTools overview](https://developer.chrome.com/docs/devtools/overview)
illustrates inspection tools; Django's
[testing overview](https://docs.djangoproject.com/en/5.2/topics/testing/overview/)
illustrates platform-provided test support. These are examples, not dependencies.
The contract is capability-based: no language, framework, vendor, browser or
execution location is mandatory. Concrete choices belong to the current project.

For every selected route, retain or link the exact non-secret command/arguments,
stable case ID and selector, intended target/build, required dependencies or
versions, deterministic seed/configuration when relevant, and setup/cleanup
instructions. Revalidate those facts against the current repository and target
before reuse. Keep durable run instructions with the repository's existing test
or project knowledge, rather than only in a transient result or chat.

Confirm runner registration/discovery reaches every durable case in the full
regression route. A zero-selected, filtered-out, or unrun case is not a pass.

Plan the whole-suite cost as well as the changed case: name a focused command
for diagnosis, a smoke subset when one is useful, and the full suite or its
applicable equivalent. Choose smoke membership independently from full-suite
registration and reuse the same test/selector rather than duplicating a case.
A smoke result establishes only that selected subset; it is never evidence that
the full suite passed.

### Calibrate evaluators before costly trials

When selecting or changing a grader, custom runner, output parser or execution
restriction for model trials or other costly runs, does its actual subprocess
accept valid solutions and reject known defects before work is launched? Exercise
the same entrypoint, environment, limits and parsing with a known-bad case, a
reference, and a different valid implementation when the task permits alternatives.
Restrictions must match the task's allowed capabilities. Failed calibration must
stop the launch path; a passing in-process helper or a prior shell command is
insufficient. Distinguish evaluator errors from candidate failures and retain
available usage for both. Preserve original results when correcting the evaluator;
label post-outcome rechecks separately, without promoting them to a clean
predeclared result. Apply [agent and experiment budgets](coding-practices.md#agent-and-experiment-budgets)
when those trials consume tracked resources.

## Reuse and define test facilities

A test facility is a reusable runner, fixture/helper, test environment, native
testing tool, or supported access/inspection route. During test strategy and each
affected plan, inspect existing test configuration, helpers, repository test
documentation and applicable selected skill and MCP capability references.
If the needed route is not described, discover relevant available skills and
MCP tools/resources through the host's supported discovery route; select only
capabilities that meet a named test need.
Follow [reuse before a new mechanism](research-loop.md#reuse-before-a-new-mechanism):
reuse, configure or extend a suitable existing facility before creating another.
Record the concrete gap if none fits. No MCP server, skill wrapper or testing
framework is mandatory; a direct stateless check may need none.

For each selected facility, retain a definition locator in existing strategy/plan
evidence and repository test documentation. Record only the relevant details:

- purpose, test boundary, consuming case/suite selectors and reuse rationale;
- source/package identity and version or digest where available, plus the selected
  skill card and relevant reference/script locators, or MCP server identity and
  supported tool/resource interface;
- exact command or operation, required inputs, observable result/error contract,
  non-secret configuration and execution versus target location;
- availability/readiness evidence, access/authority prerequisites, fixture
  setup/cleanup and isolation/sharing, limitations and revalidation triggers.

Read the selected skill and its relevant resources before using its procedure;
resolve its bundled helpers from that selected package. For MCP capabilities,
inspect the actual available operation/resource contract and relevant schemas;
do not infer an API, tool access, target readiness or authority from a server name
or catalog entry. Discovery or readiness is not test execution, and a successful
tool call is not a passing case without its independent expected outcome.
Use the [existing acquisition and access policy](research-loop.md#acquire-a-reader-and-establish-access-only-when-authorized)
when setup is needed. Selection alone does not authorize installation, login,
provisioning or remote mutation. Reuse current applicable readiness evidence;
use a bounded authorized probe only when a consequential uncertainty remains.

If a required facility is missing, define the smallest missing facility with its
purpose, interface, owner, prerequisites, fixture lifecycle, invocation/registration
route and validation criteria. Assign its implementation or configuration as a
prerequisite in the existing plan; create or extend it within the owning work's
scope and validate readiness before dependent checks. Keep it labeled planned or
blocked until supported by evidence. A planning result may record that unresolved
execution prerequisite; it does not claim the facility exists. If its contract is
unknown, resolve that planning gap before dependent authoring rather than invent
an executable interface. Preserve the assigned stage's expected check state:
facility readiness must not require future product behavior to pass during RED.

Retain implemented helpers/configuration and definitions in the repository's
existing test layout and documentation, with a minimal usage example and check
result/limits. Link them from the repository index for later tests and runs;
do not leave the only definition in chat or disposable run storage. Follow
[reference destinations](project-knowledge.md#reference-handoffs-and-destinations):
portable notes retain package/source identity and how to resolve it, while
run evidence keeps the actual selected host locator and its explicit base.
Do not copy credentials or require an old worktree/session for future reuse.
Create a repo-local skill only when a reusable procedure warrants it under
[reusable product skills](testing-and-documentation.md#reusable-product-skills).
Carry the definition locator and current selection/readiness decision through
ordinary evidence_refs and applicable item context into INNER/OUTER planning and
Improve. Revalidate changed versions, interfaces, targets or access rather than
duplicating the facility or treating its former availability as current proof.

## Carry test decisions through stages

For Navigator v3, retain the run-wide strategy note in the `test-strategy`
result's ordinary `evidence_refs`. Record selected capabilities and concrete
project choices, rationale, execution versus target location, fixture lifecycle,
suite commands/membership, prerequisites, and revalidation conditions there.
During `plan`, put only each item's applicable decisions and strategy locator in
its existing `context`; preserve detailed evidence in linked repository notes.

The script projects the latest completed root `test-strategy` result as the
**Run-wide test strategy source** in later packets. During an INNER item, it
also projects the latest completed `step-plan`, `test-spec`, `test-author`,
`test-refine` or `regression` result for that item as the **Current item
test-decision source**. The item's initial `context` remains unchanged; these
producers retain applicable prior decision locators and revisions through
ordinary `evidence_refs` and durable test notes. Both sources reach the actual
Improve handoff, alongside the separate pending producer result being reviewed.
These pointers derive from `state.md`'s existing `history`/`accepted` records and
immutable results; the script neither reads those evidence links nor
proves the strategy is still applicable. Pending, repeated or blocked attempts
are not promoted to completed sources. Their own result/Improve context
continues to describe that attempt.

Each INNER plan revalidates the relevant strategy and item context. Authoring,
refinement and regression use those decisions and retain justified changes in
ordinary plan/result evidence. Carry the originating strategy locator plus the
current item-specific decisions into repository test documentation and future
item context; whole-system testing reconciles that retained coverage. A missing
decision calls for scoped reassessment; do not guess from a previous tool name.
The latest reviewed item decision can refine the global baseline within its
scope. Conflicts or missing prerequisites remain explicit. Managed/legacy runs
retain their existing test-plan/binding and context routes.

## OUTER test-planning handshake

The existing `system-test-author` and `release-plan` stages own two planning
handshakes: the assembled product's integrated suite, then the checks appropriate
to the actual release boundary. Their consumers acknowledge the applicable plan
and revalidate its assumptions before execution. This is ordinary result and
`evidence_refs` guidance, not a new stage, schema, approval or test catalog.

At `system-test-author`, recover the latest completed test-decision record for
each relevant completed INNER item from `state.md`'s accepted history, using
`step-plan`, `test-spec`, `test-author`, `test-refine` or `regression` and the
prior locators it retained. Read `results/<action>.md` and its relevant test notes.
Reconcile these with the run-wide strategy and assembled candidate; the last
transition or final item's decisions cannot stand for all completed items.
Retain selected action/result and durable test-note locators in the integrated
plan. The packet's current-item projection intentionally ends at the INNER
boundary; OUTER recovery uses the existing history rather than an implicit item.

The integrated plan records requirement-to-case coverage, independent oracles,
focused/smoke/full commands and selectors, execution and target locations,
candidate/test-definition identity, prerequisites, execution owners and boundary,
setup/test/teardown or justified stateless cases, fixture isolation/sharing,
runtime cost and cleanup/stop conditions. Reuse applicable existing decisions
and note changes or gaps. Identify checks runnable at `system-test` separately
from those that need an authorized release and belong to `release-verify`.
An unavailable required boundary remains a named unrun/blocked obligation;
neither authoring nor a local pass satisfies it.

`system-test` confirms this plan still fits before running its assigned checks.
`product-acceptance` reconciles coverage and observations with the accepted
requirements, retaining later release obligations. `release-plan` revalidates the
same suite for the actual release target and defines any necessary additional
checks, including remote-resident definitions and native testing mechanisms.
It assigns pre-release checks to `release-check`, post-release checks to
`release-verify`, and applicable operational observations/cleanup to `operations`.
`release` checks that those prerequisites and stop conditions still hold before
its authorized operation; planning does not authorize deployment. `handoff`
retains repeatable commands, evidence, ownership and unresolved obligations.

For cold recovery, select root-owned, latest `done` `system-test-author` and
`release-plan` records after the most recent accepted `replan`, where those
producers have completed. Follow their relevant `evidence_refs`; keep pending
Improve proposals separate from accepted plans. Pending, `repeat` and `blocked`
attempts are not accepted plan sources. When a producer has not run yet, it owns
creating its plan; a consumer with a missing source must recover it or use its
supported incomplete/correction outcome. Do not require a future release plan
to perform integrated system testing.

A corrective replan makes earlier OUTER plans/results historical inputs. Reuse
them only after reconciling the corrective INNER work and current candidate.
Within the same OUTER pass, changes to product or test code, fixtures,
configuration, dependencies, target or test definitions also invalidate affected
observations. Preserve old receipts, identify the affected checks and rerun them
through the authorized route; unchanged evidence may be reused with a stated
identity and relevance basis. Record the plan being consumed, revalidation and
any mismatch in ordinary result evidence. Improve reviews that handshake and
its test assets within the existing producer subcall. These are host reasoning
obligations: accepted history supplies provenance, not proof of applicability,
test execution or a machine-enforced candidate/evidence match.

## Select target-native tests

Use the existing discovery and environment notes to identify the affected
execution boundaries and actual deployment/promotion test gates. Relevant server
code, served client code, configuration, generated definitions and existing test
assets may live behind an MCP/API rather than in the local repository. An exposed
tool list describes access operations, not a complete inventory of that system.
Use bounded supported reads of the selected system and authoritative definitions;
retain source/target identity, revision when available, and observation limits.
Do not inspect unrelated systems or assume every remote runtime has a test runner.

In the existing test-strategy/case records, retain the native-suite decision and
its discovery/environment evidence:

- Select checks when affected behavior needs that runtime's evidence or the
  actual release operation requires them, including existing remote code affected
  by configuration or dependency changes. Reuse its supported tests/facilities.
- Exclude a native suite only with evidence that neither the affected behavior
  nor the actual release gate requires it. Unrelated code can exist without
  requiring its suite; no code, runner or empty tests should be invented.
- If applicability is unknown, retain the discovery gap and earliest dependent
  owner. If required but unavailable, retain the named prerequisite and due phase
  as blocked/unrun. Missing access, an empty local search or a successful MCP call
  cannot justify N/A or prove a test passed.

Use the existing [local/remote execution contract](#plan-local-and-remote-execution)
for commands, definitions, registration, isolation, authority and results; no
second inventory or row per language is required. At `implement` and `test-refine`,
revalidate affected decisions against actual local and remote code/configuration,
dependencies and test-definition changes. At `release-plan`, recheck the actual
target, payload and operation's test gate. Update the existing cases and evidence
when their basis changes; a prior exclusion is not permanent.

## Plan local and remote execution

Record the **execution location** separately from the target under test. Local
unit tests, a local client checking a deployed service, and **remote-resident**
tests executing inside that service/runtime establish different boundaries.
Choose the applicable routes from the required behavior and the remote system's
actual framework, capabilities, and availability; do not assume local tests can
exercise remote-only behavior or that every remote system exposes a test runner.

Discover the supported runner/framework, invocation interface, runtime/version,
access and authorization, target readiness, and relevant deployment prerequisites
during planning. If remote-resident cases are needed, author and retain their
definitions and registration in the repository, with a repeatable, authorized
route to install/synchronize and invoke them in the remote system. When the
platform owns the definitions, retain an export/version or stable locator and
the reproducible creation/update procedure. Reuse an available framework; plan
the smallest missing mechanism only for a demonstrated gap.
An unavailable target need not block authoring when its framework and contract
are known. If the required capability/interface is still unknown, retain a
planned case specification and its missing prerequisites; do not describe it as
an executable, registered remote test yet.

Apply the same independent oracle, setup, safe sharing, teardown, and rerun rules
to remote cases. Identify the deployed code and test-definition revisions, actual
target/environment, invocation and result retrieval, fixture ownership, and
cleanup of owned test data. Preserve the system's other users and shared state.
Deployment or remote writes still require the existing authorized route.

The full regression route may combine local and remote suites. Retain commands
and case selection for each required part: a local pass is not a remote pass or
evidence that the combined full suite passed. If remote availability, access,
framework support, or required deployment is missing, record that prerequisite
and leave the required check blocked/unrun for its assigned owner and boundary;
do not silently replace it with a mock, drop it, or use an unplanned deployment
to unblock it.

## Give each case a lifecycle

For each INNER or OUTER case, record and implement the smallest applicable lifecycle:

| Part | What it establishes |
| --- | --- |
| Setup | Required fixture, dependency, target state, and readiness; say `none (stateless)` when no state is needed. |
| Test and oracle | The stimulus plus an independently derived observable expected outcome, with its stable ID and executable selector. |
| Teardown | Removal, reset, or isolation check for created state; `none` is also valid for a borrowed/read-only resource when its actual owner and lifecycle scope are named. |

Do not make test order a prerequisite. Stable IDs/selectors let a focused test,
the smoke subset, and the full suite point to the same durable case without
claiming that every suite has run. An oracle must remain grounded in an accepted
requirement, contract, or independently checkable invariant, not reshaped to
match the current implementation.

## Share fixtures only with evidence

Distinguish reusable **infrastructure** (for example, a read-only image,
emulator, or service process) from mutable test **data**. Expensive setup may be
shared only when the cases have evidenced noninterference: the shared resource
is read-only, every case resets it, or each case has a partitioned namespace,
account, port, queue, temporary path, or equivalent boundary. If that evidence
is absent or doubtful, give the case its own fixture. A reset between serial
cases alone does not establish parallel safety.
When noninterference is established and reuse saves meaningful setup/teardown
cost, group compatible cases with the runner's existing fixture scopes rather
than repeating that cost for every case. Keep each assertion independently
selectable; grouping must not create a test-order dependency.

Assess parallel collisions and residual state explicitly. A fixture that is
safe serially can still collide through names, clocks, ports, queues, accounts,
or external rate limits. Budget total runtime and per-worker setup/teardown
cost: reuse may save expensive startup, but not by hiding interference or test
order. Keep the focused path practical without silently dropping the broader
suite.

[pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) and
Playwright's [fixtures](https://playwright.dev/docs/test-fixtures) and
[parallelism](https://playwright.dev/docs/test-parallel) guides illustrate
possible lifecycle and isolation mechanisms only; neither tool is required.

## Preserve honest reruns and outcomes

Arrange cleanup to run after normal assertions, partial acquisition, setup
failure, or a bounded timeout where the runtime permits it. Preserve the
original setup/assertion failure; report a cleanup failure or limit alongside
it rather than masking it. Forced cancellation can leave an external process or
request running, so verify or record the uncertain state instead of claiming
cleanup completed. Do not blindly retry an external action after an ambiguous
result; first inspect its target, logs, and effects, then use the authorized
recovery path.

When creating or changing a stateful case or shared fixture, demonstrate a clean
rerun of that case or relevant subset after teardown to check for residue. Reuse
current repeatability evidence for unchanged fixtures and boundaries. Keep the
selected commands,
seed, dependency/configuration, target identity, and observed pass/fail/blocked/
skip result. A skip needs its concrete reason and is not a pass; an unrun full
suite remains unrun even when the focused or smoke command passed. Do not retain
secrets in commands, fixtures, logs, or project knowledge.

One file owns the suite commands once test strategy is accepted; plans point at
it. Keep each command in a fenced code block, never in a Markdown table cell: a
`\|` escaped for the table becomes a literal pipe in a copied alternation pattern,
matches nothing and can still exit 0. A pass names the IDs or cases it ran, and a
retained command that does not run the suite (for example a directory path the
runner does not expand) is fixed in the stage that finds it.

## Review test assets through Improve

For Navigator v3, the selected actual standalone Improve skill reviews each
planning result, including `test-spec`, and the end-of-work candidate. Within that
candidate scope, its review
includes local and remote-resident test definitions, execution/target locations,
platform/library testing-system fit, browser inspection versus retained test
coverage, remote framework availability and invocation, fixture setup/teardown,
stable IDs/selectors, suite registration, repeatable-run instructions, and
outcome reporting. It does not
invent a parallel Improve algorithm, state machine, or test framework.

An expected RED result during test authoring is useful evidence, not a reason
to weaken the oracle or make production edits merely to turn it green. Preserve
the independent oracle and the expected RED evidence until the scoped
implementation work legitimately satisfies it. Managed and legacy runs retain
their packet-selected review/callback route; do not apply the v3 standalone
handoff to an unmarked older run or run both routes for one candidate.
