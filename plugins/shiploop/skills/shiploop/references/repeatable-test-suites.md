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

For each INNER case, record and implement the smallest applicable lifecycle:

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

## Review test assets through Improve

For Navigator v3, every producer result is followed by the selected actual
standalone Improve skill. Within that producer's candidate scope, its review
includes local and remote-resident test definitions, execution/target locations,
remote framework availability and invocation, fixture setup/teardown, stable IDs/selectors, suite
registration, repeatable-run instructions, and outcome reporting. It does not
invent a parallel Improve algorithm, state machine, or test framework.

An expected RED result during test authoring is useful evidence, not a reason
to weaken the oracle or make production edits merely to turn it green. Preserve
the independent oracle and the expected RED evidence until the scoped
implementation work legitimately satisfies it. Managed and legacy runs retain
their packet-selected review/callback route; do not apply the v3 standalone
handoff to an unmarked older run or run both routes for one candidate.
