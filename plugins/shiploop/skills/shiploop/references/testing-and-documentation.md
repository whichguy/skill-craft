# Testing and documentation contract

Read only the section named by the current packet. These are stack-neutral host
requirements within existing stages, not new CLI fields or semantic guarantees.
Reuse repository conventions and available tools; do not install a framework or
create a service just to satisfy a test-category label.

Before execution, the [planning loops](planning-loops.md) repeatedly review case
expectations and run lint/tests of the research/behavior/specification artifacts through
`planning-verify`. Those checks do not certify future product test results.
Product acceptance remains blocked until its real implementation checks run.
Research tests use the exact `research evidence` acceptance and inspect the
question/source relationships and asserted contracts; they do not prove that a
live environment stayed unchanged. See
[Research evidence and freshness](research-loop.md#evidence-and-freshness).

## Test cases

Define expected behavior before implementation when possible. In the spec, name
observable acceptance criteria. In the sequence, map cases to each step's exact
`produces` and plan the tests/documentation as deliverables, not an afterthought.
Use stable case IDs to connect requirements, executable tests, and evidence.
For behavioral requirements, also link `R-/F-/T-` IDs from the
[product behavior model](behavioral-requirements.md#behavior-model). Cases must
state the expected source/destination or unchanged state, outputs and side
effects, including applicable invalid-event and recovery sequences. Model IDs
never substitute for exact manifest acceptance strings.

Keep one compact case record per distinct behavior, or a parameterized record
for equivalent boundaries:

| Field | Record |
| --- | --- |
| Case and requirement | Stable case ID, criterion, and exact step output or lifecycle acceptance string. |
| Preconditions and input | Initial state, fixtures, role, relevant configuration, and stimulus/action. |
| Expected outcome | Observable result, state change or absence of side effects; explicit error behavior and justified tolerance/time bound where relevant. Never just “works.” |
| Layer and environment | Local/component, browser, service, API, or another justified surface; target environment alias, real versus simulated dependencies, readiness requirements. |
| Executable reference | Test path/symbol/selector and check-manifest ID, or a reproducible manual procedure when automation is genuinely unavailable. |
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

Run current required checks through `verify`; preserve failures and explain test
or manifest changes. Include documentation/example checks where applicable.
Do not change expected outcomes or remove assertions merely to match a bug.
Do not rerun a flaky failure until lucky green and call its cause resolved.

## Surface selection

At survey/spec, and whenever changed behavior warrants it, assess each surface:

| Surface | Select when | Expected evidence |
| --- | --- | --- |
| Local/component | Logic, transformations, boundaries, or isolated contracts can be checked directly. | Assert outputs, errors, invariants, and relevant state effects. |
| Browser | Rendered behavior, navigation, interactions, accessible use, or a critical user journey matters. | Exercise the actual relevant UI and assert user-visible outcomes; a page-load screenshot alone is insufficient. |
| Service | A running process, job, message consumer, persistence boundary, or component collaboration carries the risk. | Exercise behavior through the boundary and inspect completion/state/dependency effects; a healthy process alone proves only readiness. |
| API | A callable external contract is exposed or changed, regardless of transport. | Check request/response or message contracts, validation, authorization, errors, compatibility, and side effects as applicable. |

Browser/service/API are overlapping views, not a mandatory three-level ladder.
Select the smallest set that proves the relevant behavior; a single case can
cover multiple views without duplicate tests. Prefer focused tests for fast
diagnosis, plus necessary integrated journeys. A library without those surfaces
can record them as not applicable with a reason; do not invent a browser or API.

Record a decision for each view: **selected**, **not applicable with reason**, or
**required but blocked with cause**. Lack of tools, access, an endpoint, or a ready
environment does not make a relevant check inapplicable. Reassess the selection
after discoveries, and propagate additional work through pending-only replanning.

Environment is separate from test layer. Record the intended local/test/staging/
deployment role, artifact/version identity, readiness probe, required non-secret
configuration/role, isolated data, and cleanup. A mock, local server, or staging
result is evidence for that environment only, not proof of the real deployment.
Do not record credentials, personal data, or sensitive endpoints in public docs.

Preparation and deployment must precede checks that require them. Add explicit
dependencies/producers, or authorized outer-before preparation, rather than a
circular “test before deploy before test” plan. Use only authorized environments;
do not run destructive tests, load tests, send notifications, or mutate production
data without appropriate authority and controlled fixtures/cleanup.

## Documentation

Maintain documentation with the changed behavior, before that iteration's final
checks and commit. Respect the existing language/tooling conventions.

For changed public functions/interfaces and non-obvious internal boundaries,
provide a small, colocated contract: purpose; inputs/preconditions; outputs;
errors; side effects; and only relevant invariants, timing, ownership, or
retry/idempotency constraints. Link to the applicable test cases. Use docstrings,
comments, interface documentation, or a small module reference as appropriate.
Do not narrate every line, repeat obvious types/signatures, or mandate boilerplate
for trivial helpers. One authoritative explanation plus links is preferable to
copies in source, README, run receipts, and chat. Add an index only when navigation
needs it; token efficiency must not remove a material caveat.

Review the **product README** on every implementation/Improve iteration. Update
affected sections or explicitly record “unchanged” with why. Check, as relevant:

- purpose and scope; prerequisites and non-secret setup/configuration;
- how to run/use the product, with a minimal example and expected result;
- how to run lint/tests, locate case expectations, and interpret success/failure;
- links to detailed function/API contracts instead of pasted reference manuals;
- links to relevant sequence/state diagrams and transition expectations; keep
  those consistent with the concise contracts, case documentation, and code;
- environment/deployment verification and safe operational/recovery limitations.

Exercise changed example commands in an authorized, appropriate environment.
Check paths/links and available documentation lint; record anything not executed
as unverified, not passed. A required unverified example blocks its acceptance.
No need to rewrite unrelated sections or create every listed section for every
product. Missing/stale docs that materially mislead use, testing, or safety are
material findings, even if the fix is a short sentence.

Product README, function docs, and enduring test-case docs belong in the product
worktree and Git. They are **not** ShipLoop state. Do not put run cursors, receipt
dumps, raw logs, or generic harness journals in them. `AGENTS.md` remains optional.
Before step execution, store proposed docs/cases in the spec/plan results; survey
does not create product files. Plan documentation outputs and checks explicitly.

## Iteration

Use [Test cases](#test-cases), [Surface selection](#surface-selection), or
[Documentation](#documentation) only when the current step needs their record
shape or selection rules; do not load unrelated sections or past cycles.

1. **Implement/review:** inspect the current cases and expected outcomes, relevant
   surface/environment decisions, changed function contracts, and product README.
   Review still begins with current Git history. Read only the current step's
   records and linked sections, not all historical receipts or every source file.
   Complete the structured `research_assessment` required by the research
   protocol; questions about changed environmental conditions or unsupported
   best-practice assumptions are material when they affect the current step.
2. **Plan/apply:** fix code, tests, and docs together. Add or revise cases where
   behavior or new learning requires it; preserve the agreed acceptance criteria.
   Resolve required research with concrete evidence and revise tests when its
   answer changes the known conditions. An evidence gap is not resolved merely
   because an unchanged test command passed.
3. **Verify:** run lint and all required current-step tests, compare actual against
   expected outcomes, and check changed documentation examples/links. Required
   failed, blocked, or unrun cases keep the step unfinished; they earn no clean pass.
4. **Carry forward:** distill observations useful to another iteration using the
   [carry-forward contract](carry-forward.md). Record changed environment/test
   prerequisites and documentation implications, their scope and evidence, or
   explicitly record no discoveries. A current-step correction returns to review
   and fresh checks; do not reuse the old pass as proof of the corrected state.
5. **Commit:** include test-case and documentation deltas or explicit no-change
   reasons in the existing review/changes/validation/learnings record. Two
   trivial-only cycles and fresh final verification remain required. Include
   carry-forward learnings verbatim alongside review and apply learnings.
6. **Post-inner:** ask whether learnings require broader test cases, surface or
   environment changes, function contracts, README updates, or prerequisite steps.
   Resolve carried pending-work obligations through a validated pending-only plan
   revision; generic ShipLoop ideas go to its separate journal.

Persist a compact record in the existing result: case IDs and source references,
test/documentation changes or no-change rationale, environment, observed outcome,
and evidence references. Use `body`/`plan` during planning, `test_review` for
implementation/review/quality, `test_changes` and `learnings` while applying,
and `summary` at verification/commit. Results are imported into authoritative
Markdown; no new sidecar schema or assumed chat memory is needed. Keep essential
facts inline and detail linked so a fresh context can resume. Update the product
artifacts before verification; record run-only observations in the packet's inbox
result, not in the product tree after checks (which would stale the evidence).

## Deployment and handoff

At outer quality, reassess the selected browser/service/API views against the
whole product, not only the final step. Match the manifest to every exact
`lifecycle.acceptance` string. Review expected-versus-observed outcomes, test
adequacy, function/API contracts, README accuracy, and environment identity.
Required blocked/not-run checks remain unfinished. Product changes discovered
here use corrective DAG steps, including documentation-only fixes, not direct
outer-checkout edits around the inner loop.

If whole-product acceptance depends on a real deployment, plan authorized
deployment/readiness and dependent verification **as DAG work before outer
quality**. Do not certify that acceptance locally while waiting for a later
outer publish. Outer-loop publication may add final delivery smoke checks after
publication; document their expected outcomes and record real results in its
existing `verification`/`evidence` fields. Inspect prior delivery before retries.
Failed/unknown delivery checks keep publication unfinished; pause for direction
when correction requires work or authority unavailable at that stage. Never
invent a replan command at `publish` or implicitly authorize rollback/redeployment.

Handoff links the checked case documentation, function/interface reference, and
product README. Summarize passed/failed/blocked/not-run outcomes, actual tested
environment/version, manual versus automated evidence, and limitations without
copying logs. Show generic ShipLoop proposals separately. Passing declared
commands does not prove that cases or documentation are semantically complete;
the host must perform this review and report uncertainty honestly.

## Design basis

These principles inform the contract without selecting a technology stack:
observable browser behavior and isolation ([browser-testing guidance](https://playwright.dev/docs/best-practices));
focused tests plus necessary integrated coverage, rather than a blanket end-to-end
mandate ([Google Testing Blog](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html));
concise, structured technical reference with links to usage guidance
([Diataxis reference guidance](https://diataxis.fr/reference/)).
