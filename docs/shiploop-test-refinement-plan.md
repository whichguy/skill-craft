# ShipLoop task-local test planning and refinement

## Outcome and scope

Make the existing cold-resumable execution loop explicitly plan test criteria
before code, then author/refine the executable tests after inspecting the code
just written. Repeat review, plan, application, lint and tests until the existing
two-trivial-pass and final-verification gates permit exit. This increment changes
action prompts, result templates, bounded read-only context projections,
documentation and regression tests; it adds no
stage, new durable schema, framework, integration or deployment permission.

## Audit and decisions

| Question | Current evidence | Information gain and decision |
|---|---|---|
| Can a step start without an execution plan? | `step_plan_start` and `step_plan_validate_execution_proof` bind the twice-reviewed plan to implementation/application. | High: retain the existing plan handoff, including its Markdown authority and cold packets. |
| Is the test plan concrete enough? | The packet body only suggested `Tests and expected outcomes`; `test_strategy` did not distinguish unit, mocks and end-to-end scope. | High: specify a compact case matrix, category decisions, readiness and a post-code refinement checkpoint in every initial/Improve plan. |
| Is there already a post-code improvement loop? | `implement` verifies before `review`; `review → improve-plan → step-plan-* → improve-apply → verify` reassesses the actual code. | High: use those existing actions. Make code, test authoring/refinement and execution ordered duties within them, rather than adding a duplicate nested state machine. |
| Can a failed test close the step? | `verified` checks current successful evidence, `verify` detects late edits, and final verification is fresh. | High: preserve these machine gates; explicitly require failure diagnosis and justified test correction in prompts. |
| Does green prove test adequacy? | The script validates evidence identities and declared checks, not semantic exhaustiveness of test bodies or host prose. | High: document the boundary honestly; reviewers must challenge missing assertions, test-double fidelity and expected-outcome sources every pass. |

## Required durable content

The plan `body` records stable case/contract criterion IDs, exact outputs,
preconditions/inputs, expected results/state/side effects, planned test paths and
check IDs, environment/fixtures, and post-code refinement triggers. It assesses
unit, integration and end-to-end scope, mock/fake use, and browser/service/API
surfaces separately. Each decision is selected, not applicable with a reason,
or required but blocked. Unavailable infrastructure is not a reason to declare
required coverage inapplicable.

After coding, inspect the actual diff and dependencies and author or expand the
tests from the plan. Existing or TDD tests may be retained with evidence and an
explicit adequacy rationale; do not manufacture no-op edits. New observations
refine stimuli and assertions, not the approved acceptance oracle. Record case
deltas, expected-versus-observed results, commands/evidence and unresolved gaps
in existing `test_review`, `test_changes`, `learnings` and `summary` results.
ShipLoop imports these into Markdown; no chat memory or parallel catalog is
authoritative.

Independent review found that execution packets did not advertise their accepted
`step-plan` context, and that initial implementation notes were not projected
for the next cold review. Execution packets now print the plan retrieval command;
`step-context` includes `implementation_test_record` from the original accepted
Markdown result, validated against its recorded completion digest. These are
historical host-reported notes, not evidence that the current tree passes.
No cursor, candidate identity, or durable schema is changed by this projection.

A legitimate test correction records the prior and corrected expectation,
independent requirement/contract evidence, defect diagnosis and coverage
retained or added. A requirements conflict needs explicit disposition, not an
oracle rewrite. Changed manifests use `verify --reason`. Required failed,
blocked or unrun checks remain unfinished. Material code/test gaps and changes
reset convergence; fixes during verification require fresh lint and tests.

## Verification plan

1. Red/green packet tests: both planning routes expose concrete test criteria;
   implementation orders coding, post-code test authoring/refinement and checks;
   review/application retain adequacy, no-change and justified-correction duties.
2. Protocol prompt tests: cold instructions name unit, mock/fake and end-to-end
   consideration, failed/blocked/unrun behavior and no weakening of acceptance.
3. Existing real-Git protocol/step-plan tests: certified plans still gate edits;
   checks still gate implementation and Improve completion; two-trivial policy
   is unchanged. No new capability is inferred from prompt-string tests.
4. Independent review of prompt/reference alignment, Ruff, diff whitespace,
   skill frontmatter and the ShipLoop-only materialized plugin view.

## Design evidence

The local protocol already supplies the necessary sequencing and failure gates.
For test selection, focused and integrated coverage have different failure
signals; no universal test ratio is imposed. Test doubles are useful for isolated
failures but can drift from real dependencies, so they cannot stand in for a
required real-boundary check. Primary practitioner references:
[Google Testing Blog: test fidelity](https://testing.googleblog.com/2024/02/increase-test-fidelity-by-avoiding-mocks.html)
and [Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html).

## Completion evidence

Implemented in the canonical ShipLoop package and synchronized only its plugin
view. The installed Grok and Codex paths resolve to that canonical package.
Independent review caught and corrected the missing cold-plan retrieval command,
the initial implementation-note handoff, and an accidentally weakened real
client-service test trigger. Documentation review also corrected stage ordering,
case-versus-contract IDs, and the distinction between initial and Improve result
fields. No transition, stored schema, framework or external permission changed.

100 distinct Python tests passed across these focused suites and targeted runs:

| Suite | Passing cases |
|---|---:|
| Packets | 15 |
| Protocol, including read-only notes and unsafe/tampered-record rejection | 33 |
| Step planning: 12 record tests and all 5 real-Git CLI methods | 17 |
| Authored contracts | 10 |
| Contract protocol evidence | 10 |
| Check evidence, including failures/timeouts/stale results | 8 |
| Incorporated until policy | 7 |

The step-planning results were verified through its record class and individually
run CLI methods; an earlier full invocation whose exit status was not retained
is not counted as evidence. Cold tests delete the exact submitted draft, recover
accepted case/test notes from Markdown in a fresh process, and reject valid-
Markdown tampering by completion-digest mismatch. Prompt/template regression
tests were red before their implementation edits. Ruff, Git whitespace checks,
17-skill frontmatter validation, and the scoped plugin-view check also passed.
The entire repository or full terminal delivery walk was not rerun for this
increment; passing these checks is not a semantic-completeness claim.
