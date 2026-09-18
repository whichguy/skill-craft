# Test authoring action

Discover the repository's actual test infrastructure and author or refine executable tests from SPEC.md. Preserve independent expected outcomes and existing adequate coverage. Retain work in this repository. Production files and SPEC.md are immutable for this action; expected RED is legitimate evidence when the accepted behavior is missing. Record exact commands, observed results and any unavailable evidence in TESTING.md.

## Test cases

Define expected behavior before implementation when possible. In the spec, name
observable acceptance criteria. Before source code, the existing planning result
`body`/`plan` contains a compact criteria matrix: each stable case ID maps its
contract `T-` ID and exact `produces` string to preconditions/input, expected
output/state/side effect, planned test path/selector, check ID, and
environment/fixture. This is the durable pre-code plan, not a new result schema
or a second test catalog. In the sequence, plan tests/documentation as
deliverables, not an afterthought.
For behavioral requirements, also link `R-/F-/T-` IDs from the
[product behavior model](behavioral-requirements.md#behavior-model). Cases must
state the expected source/destination or unchanged state, outputs and side
effects, including applicable invalid-event and recovery sequences. Model IDs
never substitute for exact manifest acceptance strings.

Keep one compact case record per distinct behavior, or a parameterized record
for equivalent boundaries:

| Field | Record |
| --- | --- |
| Case and requirement | Stable case ID (for example, `TC-07`), mapped contract `T-` ID, criterion, and exact step `produces` or lifecycle acceptance string. |
| Preconditions and input | Initial state, fixtures, role, relevant configuration, and stimulus/action. |
| Expected outcome | Observable result, state change or absence of side effects; explicit error behavior and justified tolerance/time bound where relevant. Never just “works.” |
| Scope, surface, and environment | Unit/integration/end-to-end scope, mock/fake strategy, and separately selected browser/service/API view; target environment alias, real versus simulated dependencies, readiness requirements. |
| Executable reference | Planned or actual test path/symbol/selector and check-manifest ID, or a reproducible manual procedure when automation is genuinely unavailable. |
| Observation | Separately record actual outcome, passed/failed/blocked/not-run status, checked revision/build, and evidence reference. Expected is not actual. |

Cover relevant success, invalid input, boundary/empty cases, permission failures,
dependency failure, and regressions. Assess timing, retry/idempotency, concurrency,
accessibility, and other risks when the behavior makes them relevant; do not
generate irrelevant cases to fill a checklist. A bug fix should have a regression
case that distinguishes broken from intended behavior where feasible.

Example, not a universal requirement:

| Case | Given / when | Expected | Layer / runner | Observed |
| --- | --- | --- | --- | --- |
| TC-07 / reject invalid change | Known state; submit an invalid value | Defined validation error; original state unchanged | API if exposed, otherwise local contract; link to actual test | Not run until evidence exists |

Use executable tests with clear assertions as the detail source when sufficient;
add concise Markdown case/index entries where intent or expected outcomes are
not apparent. Do not duplicate entire test implementations or maintain a giant
second test catalog. Case IDs supplement, never replace, the manifest's exact
`acceptance` strings. A case description or file-existence check is not execution.
Manual evidence must remain labeled manual; it does not replace mandatory
script-run lint/test checks or certify a required automated case as passed.

After code, inspect the actual diff, changed dependencies, and code learnings;
then author or refine the executable tests from that evidence and the pre-code
matrix. A TDD or reused test may be retained only with an explicit adequacy
rationale and evidence that it covers the criterion; do not manufacture a
no-op edit. New observations can refine stimuli or assertions, but do not
silently rewrite accepted behavior.

Run current required checks through `verify`; preserve failures and explain test
or manifest changes. Include documentation/example checks where applicable. A
test correction records its reason, the before/after oracle, an independent
requirement/contract source, and coverage retained or added. Do not change
expected outcomes or remove assertions merely to match a bug. A requirement
conflict needs explicit disposition, not an oracle rewrite. Do not rerun a
flaky failure until lucky green and call its cause resolved.



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
