# Testing and documentation contract

Read only the section named by the current packet. These are stack-neutral host
requirements within existing stages, not new CLI fields or semantic guarantees.
Reuse repository conventions and available tools; do not install a framework or
create a service just to satisfy a test-category label.

Before product execution, use the current packet's planning checks. Compatibility
planning-loop runs repeatedly review case expectations and run lint/tests of the
research/behavior/specification artifacts through `planning-verify`; a v3 navigator
uses its `test-strategy`, `plan`, and `step-plan` producer duties, each followed by
its standalone Improve handoff. Neither route's planning checks certify future product
test results. Product acceptance remains blocked until its real implementation checks
run.
Research tests use the exact `research evidence` acceptance and inspect the
question/source relationships and asserted contracts; they do not prove that a
live environment stayed unchanged. See
[Research evidence and freshness](research-loop.md#evidence-and-freshness).

For affected interactions, follow the shared
[review and evidence guidance](behavioral-requirements.md#review-evidence-and-reuse).
Separate event receipt, durable acceptance, processing/state effects and the
required consumer outcome. Plan independent expected recovery outcomes for
applicable crash/retry and stale-session boundaries. For UI work, test actual
rendered behavior, accessibility and meaningful async cues, including reduced
motion and interruption where applicable; a screenshot cannot establish timing
or reconciliation. Planning reviews proposed checks; later execution records
actual results and unresolved gaps. These checks use the existing stage and
Improve handoff, not a new campaign.

## Managed Improve checkpoints

This section applies only when the current packet is a managed Improve child
under `managed_improve_protocol_version: 1`. The ShipLoop parent remains at
`managed-improve`; the child controller owns the following phase progression
and records it in the bound Markdown receipt. Do not start standalone Improve,
create `.until-loop` state, or use legacy phase callbacks to duplicate these
checkpoints.

1. **Initial local test plan.** Before source edits, retain the complete case
   matrix. `step-plan` and `step-plan-revise` require it; the local-plan child
   converges it before it releases code.
2. **Per-iteration product plan.** Before each Apply, `improve-plan` requires
   the current test plan plus coverage/context evidence, explicit prerequisite
   satisfaction evidence and learnings. Run one `improve-plan-verify` planning
   check. This is one checked plan record, not a nested two-trivial plan
   campaign.
3. **Post-code refinement.** After Apply, `test-refine` inspects actual code
   and dependencies before changing tests. It returns the complete current test
   plan and `refinement_reason`; retained/new cases keep independent expected
   outcomes. A changed oracle requires an external requirement/contract basis.
4. **Executable-test authoring.** `test-author` maps every retained/new planned
   case to real test files/selectors and exact check commands. `verify` later binds
   those IDs and ordered command arguments to the actual check manifest. Its `test_refinement` record
   describes authored, updated or reused tests. This checkpoint never claims
   the tests passed.
5. **Documentation and skill validation.** `iteration-document` records the
   documentation/reuse assessment. If it selects a repo-local skill,
   `skill-validate` verifies its entrypoint/index, inputs, helper or example
   checks, failure/recovery behavior and host limits before verification.
   Discovery or a frontmatter-only check is not successful use.
6. **Actual verification.** `verify` runs the bound manifest after code, tests, docs
   and selected skill evidence are current. Failed, stale, blocked or unrun
   checks are incomplete. A product defect found by a tests/fixtures-only scope
   returns corrective-work evidence; it cannot be hidden by weakening the
   expected result.

Use these packet fields. They stay in the child/parent Markdown records; they
are not a second global test catalog.

```json
{
  "test_plan": {
    "cases": [
      {
        "case_id": "CASE-CSV-001",
        "contract_id": "T-CSV-001",
        "requirement": "CSV labels containing commas remain one field after export.",
        "inputs": ["A fixture record with a comma in its label."],
        "expected_outcome": "The exported field is quoted and parses back to the original label.",
        "test_selectors": ["test/test_csv.py::test_quotes_commas"],
        "check_ids": ["T-CSV-001"],
        "environment": "Local Python environment with the repository CSV parser.",
        "fixture": "A temporary CSV output containing one comma-bearing label."
      }
    ],
    "coverage": [
      {"surface": "unit", "disposition": "selected", "reason": "CSV quoting is a deterministic local transformation."},
      {"surface": "mock_fake", "disposition": "not-applicable", "reason": "The selected serializer has no collaborator boundary."},
      {"surface": "integration", "disposition": "not-applicable", "reason": "This scoped contract has no service integration."},
      {"surface": "end_to_end", "disposition": "not-applicable", "reason": "This local serializer has no end-user journey."},
      {"surface": "browser_service_api", "disposition": "not-applicable", "reason": "This selected contract exposes no browser or API boundary."}
    ]
  }
}
```

Every surface appears once with `selected`, `not-applicable`, or
`required-but-blocked`; the latter prevents release. Each case retains the
accepted contract ID and exact expected outcome, even when several cases share
a test command. `test_selectors` are safe repository-relative
`path::selector` references, not a claim that the selector ran.

```json
{
  "test_refinement": {
    "cases": [
      {
        "case_id": "CASE-CSV-001",
        "disposition": "authored",
        "test_paths": ["test/test_csv.py"],
        "check_ids": ["T-CSV-001"],
        "coverage": "The test exercises the planned comma-escaping boundary.",
        "oracle": {"decision": "unchanged"}
      }
    ]
  },
  "test_bindings": {
    "bindings": [
      {
        "check_id": "T-CSV-001",
        "argv": ["python3", "test/test_csv.py"],
        "case_ids": ["CASE-CSV-001"],
        "selectors": ["test/test_csv.py::test_quotes_commas"],
        "selection": {"mode": "direct", "evidence": "The script runs its unittest suite including the quoting assertion."}
      }
    ]
  }
}
```

`disposition` is `authored`, `updated`, or `reused`. A reused case must add an
`adequacy_reason`. A corrected oracle must state its old/new expected outcomes,
independent basis and preserved coverage. The next `verify` action, not this
record, establishes whether the named checks passed.

Every case/check and planned selector must be covered by `test_bindings` at
`test-author`. Its `argv` must exactly match the later test-kind manifest row.
Direct selection names each test path or selector in `argv`. For suite discovery,
use `selection:{mode:"suite",evidence:"...",evidence_path:"..."}`: the existing
repo-local discovery/config file must name every selected path or selector.
The script freezes that file with the authored tests and rejects later changes.
These bindings establish command identity; review still must assess assertion quality.
Selected skill-example check commands likewise must name their example path.

The child, not the parent, counts a completed review cycle after these duties
are satisfied. It returns a certificate only after its current evidence and
the binding's convergence/reviewer rules hold. A mandatory independent review
blocks when unavailable unless the binding explicitly authorizes and records a
self-review fallback.

New runs select this policy with `init --independent-review optional`, `required`,
or `required-with-fallback`. A required counted pass supplies a commit-result
`independent_review:{status:"performed",evidence_ref:"reviews/current.md"}`.
The existing run-relative record is bound as evidence. An explicitly allowed
fallback instead records `status:"unavailable"`, `fallback:"self-review"`,
`reason`, and `evidence_ref`. The reviewer identity and judgment remain
host-reported; missing required evidence is refused.

### Local and outer-test boundary

A managed local-plan or product certificate proves only its bound candidate and
checks. The parent delivery DAG still owns the global system-test requirements,
their producer/test-owner steps, pre-deployment integration/journey execution,
final release checks and post-deployment observation. Plan global cases before
delivery sequencing; author and improve their fixtures in their owned work;
execute them against the assembled/deployed target only when their prerequisites
and authorization exist. A local mock or simulator cannot substitute for a
required real boundary, and an unobserved future deployment is not test evidence.

Likewise, a prerequisite repo-local skill is an earlier DAG producer with its
own validation before a consumer relies on it. A reusable procedure discovered
during product work follows the child `iteration-document` and selected
`skill-validate` path. Neither route authorizes global installation or lets a
late skill edit bypass final product/outer test evidence.

### Current product and replacement evidence

At product final verification the adapter derives `invalidation_impact` from
the actual baseline-to-final Git artifact bytes and binds it into the child
certificate. It names selected contracts/outputs and all known potentially
affected local cases, SYS cases, documentation and skills. The map is
conservative (`certainty:"uncertain"`); a host cannot narrow away required
checks by declaring a small impact. Mode-only changes still count through the
full candidate fingerprint.

Each system-test owner captures its original product fingerprint and completed
producer identities when it merges. A later product or suite change makes
affected historical evidence stale. `context --section system-test-requirements`
shows that map. Frozen original SYS cases and receipts are retained. Add new
equivalent SYS cases and pending test owners with the same requirement,
expected outcome, environment and deployment target, and execute the existing
or updated tests against the current candidate. Author all changed suites
before final re-execution; a replacement may honestly reuse its tests and
record an audit-only commit. This avoids manufacturing new files on every
verification pass. The separately certified `REVIEW_CONVERGE.md` ledger is
excluded from the product fingerprint.

Quality supplies this result field when the map lists stale SYS cases:

```json
{
  "system_test_revalidation": {
    "version": 1,
    "product_content_identity_sha256": "COPY_CURRENT_PRODUCT_CONTENT_IDENTITY_SHA256",
    "replacements": [
      {"stale_case_id": "SYS-PRE-001", "replacement_case_id": "SYS-PRE-002"}
    ]
  }
}
```

The script verifies every replacement has fresh completed check/contract proof
for the current product; a replacement that is itself stale cannot discharge
an old case. The final quality manifest also reruns all completed local test
bindings and selected skill examples on the assembled tree. Retrieve exact
commands from `context --section sdlc`; combine them with lint and every
whole-product acceptance check. The current implementation conservatively
retains that full required set. It does not claim precise impact analysis or
support silently discarding obsolete commands. Changes to those contracts
require explicit corrective planning and compatible executable evidence.

## Test cases

Use the selected [maintained product requirements](project-knowledge.md#maintained-product-requirements),
not only the current change's spec. Follow the
[reference handoff map](project-knowledge.md#reference-handoffs-and-destinations)
to retain the requirement section, test path/selector and actual result location
as distinct locators; planned cases and source inspection are not passing evidence.

Define expected behavior before implementation when possible. In the spec, name
observable acceptance criteria. Before source code, the existing planning result
`body`/`plan` contains a compact criteria matrix: each stable case ID maps its
contract `T-` ID and exact `produces` string to preconditions/input, expected
output/state/side effect, planned test path/selector, check ID, and
environment/fixture. This is the durable pre-code plan, not a new result schema
or a second test catalog. In the sequence, plan tests/documentation as
deliverables, not an afterthought.
Use [repeatable test suites](repeatable-test-suites.md) to make those existing
cases executable and reusable: select/revalidate the harness, give each case a
setup/oracle/teardown decision, isolate fixtures, and link focused, smoke and
full commands. It adds no protocol or framework requirement.
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

## Surface selection

### Lightweight and browser checks

Apply this tool-choice policy during discovery, test planning, INNER verification,
system tests and post-release verification; perform only the current stage's
authorized duties. It adds no stage, required product, or result schema.

Prefer the smallest, lowest-overhead **available tool that establishes the
expected outcome**. Use `curl` or an existing HTTP/API client for suitable status,
headers, response-body/contract and service checks. Set bounded timeouts and safe
request limits; inspect the intended target, response and relevant redirects,
not only an exit code or HTTP 200. A login page can itself return 200. Avoid
unnecessary frameworks, persistent integrations and redundant probes.

For every destination-test plan, explicitly consider whether a browser is needed.
Use an available authorized browser surface (Chrome DevTools, browser automation,
or equivalent) when the requirement concerns rendered UI, JavaScript, navigation,
drag/drop, accessibility, or session/SSO/MFA/other browser-specific authentication
that a raw request does not establish. Do not require a failed curl attempt first
when the needed observation is clearly browser-only. An API-only check does not
need a browser merely because a web interface also exists. These tools can be
complementary: cheap protocol checks plus the smallest necessary real UI journey.

If curl reaches a redirect/login or gives an ambiguous access failure, preserve
what was observed and inspect the relevant authorized browser route before
concluding the destination is inaccessible. Confirm the intended account/role,
tenant, target and actual app behavior; a successful service/deployment identity
or logged-in browser is not proof the intended consumer can use the feature.
When user sign-in or approval is genuinely needed, follow
[early access readiness](research-loop.md#early-access-readiness), ask promptly
and recheck after the response. Do not bypass access controls, disable TLS
verification, export browser cookies/tokens to force curl to work, or put secrets
in commands, notes, Git, screenshots or network traces. Use supported credential
handling; redact/minimize diagnostic artifacts and never commit browser auth state.

Record the selected tool/surface, target and non-secret user role, expected versus
observed behavior, evidence location and limits in the existing test plan/results.
Relate a browser observation to the intended target and current candidate/version
where observable; disclose any missing identity link rather than claiming that
an interaction with an older or different deployment verifies the new artifact.
Retain reusable access/test procedures in project knowledge, not credentials.
If the required browser capability or authorized session is unavailable, keep
that check blocked/unverified; do not replace it with source inspection, a mock
or a curl success. Preserve a successful deployment receipt separately, and do
not redeploy merely because a browser check needs login. Browser tests that
write data still need suitable authorization, fixtures and cleanup.

The boundary is supported by the [curl FAQ](https://curl.se/docs/faq.html)
(curl does not execute page JavaScript), [DevTools network inspection](https://developer.chrome.com/docs/devtools/network/reference/)
and [Playwright's authentication guidance](https://playwright.dev/docs/auth)
(browser auth state is sensitive). These are examples, not required dependencies.

### Security, fuzzing, and ongoing maintenance

The lifecycle must explicitly assess security testing, fuzzing, and dependency
maintenance. These are risk-based choices, not mandatory technology-specific
tools. Record `required` or a concrete `not-applicable` reason for security and
fuzz testing; unavailable required work is `blocked`. Selected tests map stable
`T-` IDs to actual step test contracts at sequence time. Expected outcomes,
fixtures, real versus simulated boundaries and executable evidence remain part
of the ordinary test plan; a policy declaration is not a passed test.

Consider authorization boundaries, data exposure, unsafe input, dependency and
supply-chain risks. Fuzzing is useful for parsers, serializers, protocol/state
machines and untrusted-input boundaries when it can have a meaningful oracle.
Record resource/time limits, reproducible seeds or minimized failing inputs,
isolation and no-unintended-side-effect expectations. Do not perform intrusive
security tests on a live service without authorization.

For ongoing dependency updates, evaluate the advisory source, responsible owner,
cadence, mechanism, validation before release and rollback. A six-hour cadence
is an example to justify, not ShipLoop's default. `dag` means an explicitly
scoped implementation producer in this delivery; `operate-later` records a
future operational policy without creating a scheduler or updater. Prefer
reviewed, testable, reversible updates over assuming the application can safely
replace its own dependencies. Any persistent automation or production change
still needs task-specific authorization. `not-applicable` and `blocked` require
clear reasons; do not conceal an unresolved requirement as future work.

The new-run `lifecycle.risk_policy` shape is:

```json
{
  "risk_policy_version": 1,
  "security": {"decision": "not-applicable", "rationale": "Explain this increment's actual risk assessment."},
  "fuzz": {"decision": "not-applicable", "rationale": "Explain why fuzzing has no meaningful target or oracle here."},
  "maintenance": {"decision": "not-applicable", "rationale": "Explain why ongoing dependency maintenance is outside this increment."}
}
```

Replace these explanatory reasons with concrete findings; they are not default
waivers. `required` security/fuzz decisions add a nonempty unique `case_ids`
list. The same test may cover both concerns, but each ID must identify exactly
one DAG test definition. `blocked` may retain planned case IDs but cannot pass
sequence. `not-applicable` carries no selected case IDs.

Maintenance `dag` and `operate-later` add nonempty strings `owner`,
`advisory_source`, `cadence`, `mechanism`, `validation`, and `rollback`, plus
`step_id`: a real DAG producer for `dag`, null for `operate-later`. A selected
maintenance policy is run-wide: its producer must precede every DAG publication.
No field itself schedules
anything. Other decisions omit these selected fields. Malformed or unknown
versions fail validation rather than becoming a legacy exemption.

### Layers and real boundaries

Before code, record test scope and replacement strategy separately from the
browser/service/API views. Do not infer one decision from another:

| Decision | Select when | Record |
| --- | --- | --- |
| Unit | A local rule, transformation, boundary, or isolated contract needs direct diagnosis. | Planned case/test path and the outputs, errors, invariants, or state effects asserted. |
| Integration | Collaboration across real local components, persistence, messages, or an exposed contract carries risk. | Boundary, dependency setup, fixture isolation, and observable cross-component effect. |
| End-to-end | A critical user or operational journey needs proof through its actual entrypoint. | Entry path, selected environment, user-visible result, and required readiness/cleanup. |
| Mock/fake | An isolated dependency must be replaced for diagnosis, cost, determinism, or unavailable infrastructure. | Replaced dependency, reason, fidelity limit, and the retained real-boundary check or its blocked cause. |

At survey/spec, and whenever changed behavior warrants it, assess each
browser/service/API surface:

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

For every unit/integration/end-to-end scope, mock/fake strategy, and
browser/service/API view, record **selected**, **not applicable with reason**, or
**required but blocked with cause**. Lack of tools, access, an endpoint, or a ready
environment does not make a relevant check inapplicable. A mock or fake can
support an isolated assertion; it is not proof of a required real dependency or
entrypoint boundary. Retain that real-boundary check or mark it blocked. Reassess
the selection after discoveries, and propagate additional work through
pending-only replanning.

When the original request names a runtime, entry point, or material dependency,
retain it as a user requirement distinct from verified contracts, observed
practices, and assumptions. A local fixture or preview can exercise its local
route, and its route evidence stays separate from target compatibility, but it
cannot supply a capability absent from the requested target. Delivery outside the
authorized scope does not by itself make that compatibility non-applicable.
Establish compatibility with target-compatible source or local evidence where
possible; otherwise retain the gap as unresolved or blocked.

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
Keep the [maintained requirements home and incoming links](project-knowledge.md#reference-handoffs-and-destinations)
consistent with accepted changes; comments and README link to that home rather
than replacing it with a description of the latest implementation.

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

## Iteration documentation and reuse

The legacy versioned route with `iteration_documentation_protocol_version: 1` has a mandatory
`iteration-document` action after each `improve-apply` and before `verify`.
The initial implementation enters Improve, so its first candidate also receives
this gate before the step can finish. An assessment is required; needless edits
or skill creation are not. Follow the packet's exact result schema. Old unmarked
runs retain their original callbacks and cannot claim this new receipt.

A managed product child retains the same substantive documentation and reusable
skill obligations, but its controller owns their placement and evidence inside
the child receipt. It must update or explicitly assess relevant README/interface
documentation before actual verification, and it must complete the explicit
`skill-validate` checkpoint when a skill is selected. A managed packet's child
phase/result shape takes precedence over the legacy `iteration-document`
callback; do not run both routes for one candidate.

The result has `summary`, `documentation`, `reusable_skill`, Boolean `material`
and `learnings`. Both assessment objects start with `decision`, `rationale`,
`paths` and `references`. Decisions are `created`, `updated`, `reused` or
`not-needed`. For `not-needed`, both path arrays are empty and the rationale
explains the actual no-work decision. Other decisions name existing safe
repo-relative reference files; created/updated docs also name their actual files.
A reusable skill names exactly one `SKILL.md` within its local directory and
adds `purpose`, `when`, `how`, `inputs` and `validation`. The packet contains a
minimal example, not a suggested default verdict. If work is required but blocked,
use the printed pause/repair route instead of mislabeling it `not-needed`.

Skill entrypoints need nonempty frontmatter `name` and `description`; references
must include a repo-local index that names the entrypoint. The script checks
those declared files/links and the receipt binding; meaningful input defaults,
verification procedures, security semantics and future usefulness still require
host review. Do not mistake a minimal frontmatter check for complete Agent Skills
schema validation or a working helper test.

Read the actual code/test diff, accepted step plan, current knowledge and relevant
repo docs. Prefer colocated concise contracts/comments for non-obvious behavior;
incrementally update affected README sections and existing design/architecture/
environment notes, or give a concrete unchanged reason. Always assess the repo
README (record absence and decide whether this step needs one). Use AGENTS.md for
short stable project navigation/conventions when useful, not run state, secrets,
raw observations or copied manuals. Link detailed durable knowledge once from
the existing appropriate index instead of duplicating it.

### Reusable product skills

This content guidance applies across modes; use the current packet's result
format, not a different protocol's documentation receipt.

Ask whether a reusable repo-local skill would materially help later steps or
maintenance. Check existing skills first. Record a decision and rationale even
when the answer is no. Create or update one only for a demonstrated reusable
procedure or boundary, not a narrow transcript of this step or a speculative
framework. Reuse existing repo layout, or `skills/<name>/SKILL.md` when none is
established. Keep it inside the product worktree; no global installation, new
connector or privilege change follows from this decision.

A useful local skill documents:

- a discriminating name/description and when to use it (and meaningful exclusions);
- why it helps, the task/output it supports and the known limitations;
- variable inputs with types/required/default rules and safe example invocation;
- how to perform/verify the procedure, expected outcomes, failure/recovery and
  permission boundaries without embedding credentials or machine-specific IDs;
- relative references to relevant code, tests and design/environment material,
  with revalidation triggers for volatile assumptions.

When behavior depends on maintained product requirements, link the applicable
sections using [the reference handoff policy](project-knowledge.md#reference-handoffs-and-destinations).
Do not copy those clauses into a second skill-owned spec or point a reusable
product skill at disposable run/worktree paths. Portable skills accept the
repository/source locators they need as inputs instead of guessing another package.

Expose the skill through an existing repo skill index, README or a short relevant
AGENTS.md reference, stating when future planners should read it. Name the intended
future consumer and required inputs; do not assume every host automatically
discovers every local skill folder. Validate frontmatter and referenced paths,
exercise changed helpers/examples when applicable, and record unrun limitations
honestly. A file-existence check is not proof the procedure works. Keep new work
inside the accepted step; broader missing outputs use existing replan/pause routes.

The script saves the result in the ordinary Markdown action/iteration records.
Verification and commit consume its binding; future reviews/plans read the local
index, linked skill/docs and current knowledge. There is no new documentation
database. Changed files must pass the following lint/tests before commit. A
material addition or changed instruction resets convergence; the script also
conservatively treats any worktree edit during this action as material. Thus the
new artifacts receive subsequent review-and-improve passes, not an unchecked
last-minute handoff. Include the recorded learnings in the primary commit.

For this versioned route, editing the worktree after the documentation receipt
invalidates it even if later tests pass. Use the printed `repair` route to return
to review and obtain a new documentation assessment and fresh checks. Merely
rerunning `verify` cannot renew that receipt. Unmarked legacy runs retain their
earlier late-edit handling.

## Implementation constitution

Use these stack-neutral defaults in the current step, not a new governance loop.
Respect user requirements, approved contracts, applicable repository instructions
and established language/style tooling. A conflict needs clarification, not a
silent override. Never relax safety or acceptance to claim simplicity.

1. **Smallest sufficient change.** Solve the current requirement. Reuse local
   conventions; avoid unrelated cleanup, speculative features, new dependencies,
   configuration knobs or fallback paths without a present need. A no-change
   result is valid; do not manufacture edits to satisfy an iteration.
   Apply the selected [project implementation conventions](navigator.md#project-implementation-conventions)
   for this work item, revalidate changed assumptions and justify departures.
   Existing code is evidence, not a mandate to copy stale or unsafe practice.
2. **Useful abstraction.** Prefer direct, readable code and cohesive functions.
   Extract a helper/interface when it clarifies current behavior, removes actual
   duplication, or isolates a real boundary. Explain the present benefit of new
   indirection; do not build a framework for hypothetical reuse or force unrelated
   code through one abstraction.
3. **Explicit boundaries.** Check untrusted inputs and public preconditions:
   shape, domain constraints and relevant state before effects. Use established
   validators and clear error behavior; do not swallow failure or invent success
   defaults. Avoid redundant internal checks, but retain revalidation when state
   or trust can change. Validation is not authorization. Test invalid inputs and
   expected unchanged state where relevant.
4. **Compact, useful documentation.** Prefer clear names. Comment on intent,
   invariants, surprising constraints and tradeoffs, not obvious syntax. Document
   changed public/non-obvious contracts as specified in [Documentation](#documentation).
   No mandatory comment on every function, machine-only tags, copied code prose,
   or abbreviated names merely to save tokens. Keep essential caveats.
5. **Evidence before polish.** Plan tests first; inspect code before refining
   actual tests; run required lint/tests after edits. Update affected README/docs.
   Prefer existing tools and focused cases over checklist-driven test layers.
   Preserve the independent expected outcome and required real-boundary evidence.
6. **One convergence owner.** A v3 standalone Improve child uses the selected
   Improve card and its bound Until Loop for review, plan, apply, check and
   two-trivial assessment within the parent-supplied scope/no-commit constraint.
   A versioned managed Improve child retains its managed binding for the same
   ownership boundary. ShipLoop owns its parent action, DAG and certificate
   import. Do not wrap either child's per-iteration plan in another converging
   Improve loop, count its passes in the parent, or use a legacy callback in
   parallel. A material change reopens affected evidence; an unavailable
   mandatory reviewer blocks unless the binding explicitly records an authorized
   self-review fallback.

In existing `body`/`plan`, note consequential design choices. During review use
existing findings; record changes or justified exceptions in `summary`/`learnings`
where that action permits them. Personal style preferences alone are trivial;
behavior/security/contract changes are material. Never downgrade the script's
classification. This is host judgment, not a new field, score or proof of quality.

## Iteration

Also read the current global catalog through `context --section
system-test-requirements` when offered. Cross-step tests have separate
prerequisite-owned activities; they never replace this step's required tests.
Use the [system-test contract](system-tests.md#reassessment-change-and-closure)
for the carry-forward/replan checkpoint and pre/post-deployment test sequencing.

Use [Test cases](#test-cases), [Surface selection](#surface-selection), or
[Documentation](#documentation) only when the current step needs their record
shape or selection rules; do not load unrelated sections or past cycles.

The packet owns the order. This table locates duties and records; it is not a
second scheduler. Keep the [Test cases](#test-cases) oracle/reuse rules,
[Surface selection](#surface-selection) decisions and
[Documentation](#documentation) contract rather than duplicating them per phase.

| Current action | Duty and existing record |
| --- | --- |
| Managed parent `managed-improve` | Keep the parent action fixed and follow only the child packet/import route. The parent neither advances a child phase nor counts a child review. |
| Managed local-plan child | Require the complete pre-code `test_plan` in `step-plan` and `step-plan-revise`; it converges that plan before implementation. |
| Managed product child `improve-plan` / `improve-plan-verify` | Bind product findings, complete test plan, coverage/context evidence, prerequisites and learnings; validate/check the plan once before Apply, with no nested plan-convergence campaign. |
| Managed product child `improve-apply` → `test-refine` → `test-author` | Apply scoped code, then refine the complete test plan from actual code and author/update/reuse executable tests with independent oracle evidence. Those records do not claim checks passed. |
| Managed product child `iteration-document` / `skill-validate` | Record documentation/reuse assessment. When a skill is selected, validate its actual entrypoint/index and example/helper checks before verification; do not install it globally. |
| Managed product child `review` | Begin from current history/knowledge and compare actual code/tests/environment/docs with independent expectations. The child retains findings, test/research assessment and learnings. |
| Managed product child `verify` / `carry-forward` / `commit` / `final-verify` | Run current required checks after all bound artifacts are current, record carry-forward evidence, retain the primary learning/audit-commit evidence, and let the child decide convergence before returning a certificate. |
| Legacy `step-plan` / `improve-plan`, then nested plan convergence | Put the pre-code case-to-contract matrix in `body`/`plan`. Use the implementation constitution; only a finalized plan authorizes its scoped code edits. |
| Legacy `implement` / `improve-apply` | Write certified code, inspect actual diff/learnings, then author/refine tests and docs. Initial adequacy and justified oracle corrections use `test_review`; Improve application deltas use `test_changes` and `learnings`. Retained/TDD tests need evidence of adequacy, not a manufactured edit. |
| Legacy `review` | Begin with current Git history and knowledge; compare actual code/tests/environment/docs with independent expectations. Record findings, `test_review`, `learnings` and `research_assessment`; new material research questions require investigation. |
| Legacy `iteration-document` (versioned runs) | Required docs/README and reusable-local-skill decision, with safe paths, reasons, intended readers and learnings. Make scoped documentation/skill edits before fresh verification, not after it. |
| Legacy `verify` / `final-verify` | Run required lint/tests and relevant examples/links; diagnose failures. In versioned runs, any source edit after `iteration-document` requires repair, renewed review/documentation and fresh checks; merely rerunning verify cannot renew the documentation receipt. Legacy repairs also remain material. Required failed, blocked or unrun checks remain unfinished. Put case/check evidence in `summary`; a test-oracle change needs independent justification. |
| Legacy `carry-forward` | Use the [carry-forward contract](carry-forward.md) for scoped observations/evidence or explicit no discoveries. A current-step correction returns to review and fresh checks; prior evidence is stale. |
| Legacy `commit` | Include test/docs deltas or no-change reasons and required review, nested-plan, apply, versioned iteration-document and carry-forward learnings verbatim. Two trivial-only cycles and fresh final verification remain mandatory. |
| `post-inner` after either route | Reassess broader tests, environments, contracts, README and prerequisites. Resolve pending-work obligations through validated pending-only replanning; generic ShipLoop proposals go to its journal. |

Keep case IDs, independent sources, environment, observed outcomes and evidence
references compact in the permitted result fields above. Results are imported
into authoritative Markdown; no sidecar schema or assumed chat memory is needed.
Keep essential facts inline and detail linked for a fresh context. Update product
artifacts before verification; run-only observations go in the packet's inbox,
not into the product tree after checks (which would stale the evidence).

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
