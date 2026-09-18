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

