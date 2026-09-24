# Testing and documentation contract

Read only the section named by the current packet. These are stack-neutral host
requirements within existing stages, not new CLI fields or semantic guarantees.
Reuse repository conventions and available tools; do not install a framework or
create a service just to satisfy a test-category label.

Before product execution, use the current packet's planning checks. The
`test-strategy`, `plan`, `step-plan` and `test-spec` producers plan the checks,
and each is followed by its Improve review. Planning checks do not certify future
product test results. Product acceptance remains blocked until its real
implementation checks run. Research evidence does not prove that a live
environment stayed unchanged; see
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

When correctness depends on ordering or interruption, control the operation's
release or retain a trace showing the required intermediate states in order.
An arbitrary delay followed by an eventual-state assertion does not prove that
the intended interleaving occurred. Bound waits and release any held work during
teardown, including when an assertion fails.

## Local and outer-test boundary

An item's checks prove only that item's candidate. The run's global system-test
catalog, its authoring and pre-deployment execution, final release checks and
post-deployment observation belong to `system-test-author`, `system-test`,
`product-acceptance`, `release-check` and `release-verify`. Plan global cases
before delivery sequencing; author and improve their fixtures in their owned
work; execute them against the assembled or deployed target only when their
prerequisites and authorization exist. A local mock or simulator cannot
substitute for a required real boundary, and an unobserved future deployment is
not test evidence.

Likewise, a prerequisite repo-local skill is an earlier work item with its own
validation before a consumer relies on it. A reusable procedure discovered
during product work follows `skill-assess` and `skill-validate`. Neither
authorizes global installation or lets a late skill edit bypass final product
or outer test evidence.

## Stage readiness and completion

Apply only the current stage's row below. **Definition of Ready**
means its required inputs, authority and prerequisites are available. **Definition
of Done** means its scoped output and due evidence exist. These are host duties
inside the existing graph, not new result fields or mechanical semantic gates.
Use existing requirement sections, case records and result/evidence locators;
do not copy this table into every work item or create a second acceptance ledger.

| Existing stages | Ready inputs | Done for this activity |
| --- | --- | --- |
| intake, discovery, research | Request, applicable sources and scoped investigation | Consumer intent, baseline observations, constraints and material unknowns retained; an investigated failure is not product readiness |
| spec | Reconciled sources and decision basis | Independently verifiable clauses and required surfaces defined; unresolved criteria remain prerequisites |
| test-strategy, plan | Defined criteria and initial baseline | Cases/verification methods allocated by surface, target, owner and due phase; prerequisites ordered before consumers |
| prepare, select-work, step-plan | Authorized preparation or selected item with supplier evidence | Actual prerequisites and bounded item Ready/Done criteria revalidated; relevant clause/case locators retained |
| test-spec | Assigned clauses and accepted strategy | Inputs, independent expected observations, required surfaces, fixtures and execution phases specified |
| baseline, test-red | Starting candidate and applicable checks | Actual baseline or meaningful expected failure observed and classified; missing coverage/setup failure is not a passing product check |
| test-author, system-test-author | Independent cases and permitted test scope | Executable checks or justified reproducible manual procedures supplied, discoverable and bound to clauses; authoring does not claim execution |
| implement | Ready item, independent expectations and edit authority | Scoped candidate supplied; accepted criteria are preserved |
| test-green, regression, static-checks | Current candidate and selected checks | Actual results recorded only for the behavior/surface those checks observe |
| test-refine | Original cases plus implementation evidence | Retained, added, removed or narrowed cases reconciled with an independent basis; required coverage cannot disappear |
| document, skill-assess, skill-validate | Current artifacts and relevant documentation/reuse criteria | Documentation and selected skill checks or justified N/A recorded; neither substitutes for product verification |
| verify, integration-verify, system-test | Candidate at the assigned boundary and cases due there | Due clauses reconciled to current observations; invalidated checks rerun and later-phase cases explicitly retained |
| integrate, carry-forward | Reviewed item and assembly/next-consumer requirements | Assembly and remaining obligations retained with owner, phase and locators; assembly is not deployment |
| product-acceptance | Original outcome and whole-product evidence | All due criteria may establish pre-release readiness; distinguish corrective or blocked work from release-only behaviors that remain pending and are not yet observed |
| release-plan, release-check | Current candidate, authority and pending delivery cases | Release route and readiness established with post-release checks and recovery; no implied external operation |
| release | Current authorized operation and target | Actual effect and candidate/target identity recorded separately from behavior |
| release-verify | Actual release and applicable consumer prerequisites | Required post-release consumer observations recorded or left incomplete |
| operations, handoff | Current results and applicable operational/return duties | Due evidence reconciled, remaining limits retained, applicable consumer entry identified, current workspace return taken from its verified receipt |

Completion is phase-specific. A post-release case that is **not yet due** stays
pending through pre-release acceptance; that alone does not block reaching the
release that supplies its prerequisite. A required case already due but failed,
blocked or not run prevents declaring that boundary complete. Retain corrective
work through the existing repeat/blocked/replan routes. Do not postpone an
already-due check simply to advance. For an enabled delivery contract, preserve
its fixed obligation phases and correction rules; this guidance does not move them.

## Test cases

Use the selected [maintained product requirements](project-knowledge.md#maintained-product-requirements),
not only the current change's spec. Follow the
[reference handoff map](project-knowledge.md#reference-handoffs-and-destinations)
to retain the requirement section, test path/selector and actual result location
as distinct locators; planned cases and source inspection are not passing evidence.

Define expected behavior before implementation when possible. In the spec, name
observable acceptance criteria. Before source code, the step-plan and test-spec
results contain a compact criteria matrix: each stable case ID maps its
requirement or `T-` ID to preconditions/input, expected output/state/side
effect, planned test path/selector, check command, and environment/fixture. This is the durable pre-code plan, not a new result schema
or a second test catalog. In the sequence, plan tests/documentation as
deliverables, not an afterthought.
Use [repeatable test suites](repeatable-test-suites.md) to make those existing
cases executable and reusable: select/revalidate the harness, give each case a
setup/oracle/teardown decision, isolate fixtures, and link focused, smoke and
full commands. It adds no protocol or framework requirement.
For behavioral requirements, also link `R-/F-/T-` IDs from the
[product behavior model](behavioral-requirements.md#behavior-model). Cases must
state the expected source/destination or unchanged state, outputs and side
effects, including applicable invalid-event and recovery sequences.

Keep one compact case record per distinct behavior, or a parameterized record
for equivalent boundaries:

| Field | Record |
| --- | --- |
| Case and requirement | Stable case ID (for example, `TC-07`), mapped requirement or `T-` ID, and criterion. |
| Preconditions and input | Initial state, fixtures, role, relevant configuration, and stimulus/action. |
| Expected outcome | Observable result, state change or absence of side effects; explicit error behavior and justified tolerance/time bound where relevant. Never just “works.” |
| Scope, surface, and environment | Unit/integration/end-to-end scope, mock/fake strategy, and separately selected browser/service/API view; target environment alias, real versus simulated dependencies, readiness requirements. |
| Due phase and owner | The existing activity that must obtain this observation, its owner and prerequisites. Separate pre-release checks from post-release consumer verification. |
| Executable reference | Planned or actual test path/symbol/selector and check command, or a reproducible manual procedure when automation is genuinely unavailable. |
| Observation | Separately record actual outcome, passed/failed/blocked/not-run status, checked revision/build, and evidence reference. Expected is not actual. |

Keep each affected, independently verifiable requirement clause linked to this
record or another existing verification record. Preserve its **required** surface
and due phase separately from the surface actually checked. A supporting unit
pass cannot close a required deployed interaction. At test refinement and
acceptance, reconcile the original selected inventory with current records;
explain every removal, narrowing or reassignment with its independent requirement
or correction basis. Retain unresolved coverage instead of silently dropping it.
Use a compact table or equivalent existing notes, not mandatory extra files.

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
second test catalog. A case description or file-existence check is not execution.
Manual evidence must remain labeled manual; it does not replace mandatory
lint/test checks or certify a required automated case as passed.

After code, inspect the actual diff, changed dependencies, and code learnings;
then author or refine the executable tests from that evidence and the pre-code
matrix. A TDD or reused test may be retained only with an explicit adequacy
rationale and evidence that it covers the criterion; do not manufacture a
no-op edit. New observations can refine stimuli or assertions, but do not
silently rewrite accepted behavior.

Run current required checks at `test-green`, `regression`, `static-checks` and
`verify`; preserve failures and explain test changes. Include documentation/example checks where applicable. A
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
or equivalent) when the requirement concerns browser-rendered UI, page JavaScript, navigation,
drag/drop, accessibility, or session/SSO/MFA/other browser-specific authentication
that a raw request does not establish. Do not require a failed curl attempt first
when the needed observation is clearly browser-only. An API-only check does not
need a browser merely because a web interface also exists. These tools can be
complementary: cheap protocol checks plus the smallest necessary real UI journey.

Make that choice during planning, before implementation. In the existing case
record, name the available runner or manual procedure, why its observation is
sufficient, and any setup/session/fixture prerequisites. Carry the selection
into the step plan and validation; tool availability alone is not coverage.
The tool names below are examples, not a requirement to try or install every
candidate. Use the host-supported browser connection and control route; a tool
name does not authorize a different transport or access to a personal profile.
For native desktop/mobile UI, select the corresponding supported UI test surface
rather than inventing a browser requirement.

| Observation needed | Candidate method | Evidence boundary |
| --- | --- | --- |
| HTTP status, headers, response contract or service behavior | `curl` or the repository's HTTP/API client | Does not establish rendered UI or page JavaScript behavior. |
| Rendered elements, layout, console errors or browser network activity | Chrome DevTools or equivalent browser inspection | Record the action and observed result; inspection alone is not an automated regression test. |
| Repeatable user interactions and visible state transitions | Playwright or equivalent available browser automation | Assert the expected user-visible outcome after the action, not merely that a click completed. |

For browser-based UI acceptance, plan the actual browser sequence: starting state,
user action, expected visible result and applicable viewport, keyboard/focus or accessibility
conditions. For example, a form-validation case submits an invalid value and
checks the displayed error and preserved input; a successful page request alone
does not establish that behavior. Prefer stable role/label locators and bounded
condition-based assertions over brittle DOM paths or fixed sleeps. Retain a
screenshot or trace when it supports the criterion; a screenshot alone cannot
prove interaction or timing. Use the existing fixture/cleanup and suite-placement
guidance in [repeatable test suites](repeatable-test-suites.md).

Record the relevant browser/version, headed or headless mode, viewport and other
conditions that affect the criterion. Select supported-browser coverage from
requirements and risk; one observed configuration does not prove others. Verify
session readiness in the chosen runner: an interactive signed-in tab does not
establish access in an isolated automation context or CI. Record mocked,
intercepted or offline dependencies; a rendered result from those fixtures does
not close a required live integration check.
When visual comparison is selected, use a reviewed baseline and controlled
rendering conditions; do not mask or disable the behavior under test to obtain
a match. Keep keyboard/accessibility checks tied to their own criteria rather
than infer them from a screenshot or successful role-based locator.

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
For a browser consumer, distinguish the account/tenant/instance from the usable
entry route after authentication and redirects. Retain a non-secret URL/path or
supported navigation locator, visible feature identity, and the rendered action
and outcome for each required behavior. A service home or login page alone is
not the feature entry. An embedded feature can be valid: require particular app
chrome, navigation or branding only when the accepted criteria require it.
Redact session tokens while retaining non-secret routing state needed to identify
the feature; origin and pathname alone may not identify an SPA route. Confirm
the supplied entry reaches the intended feature through the supported user route.
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
(browser auth state is sensitive). [Playwright's testing practices](https://playwright.dev/docs/best-practices)
support user-visible assertions, stable locators and isolated tests. These are
examples, not required dependencies.

### Security, fuzzing, and ongoing maintenance

Test strategy must explicitly assess security testing, fuzzing, and dependency
maintenance. These are risk-based choices, not mandatory technology-specific
tools. Record `required` or a concrete `not-applicable` reason for security and
fuzz testing; unavailable required work is `blocked`. Selected tests map stable
`T-` IDs to actual item test cases at planning time. Expected outcomes,
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
is an example to justify, not ShipLoop's default. Maintenance can be an
explicitly scoped work item in this delivery, or a future operational policy
recorded without creating a scheduler or updater. Prefer
reviewed, testable, reversible updates over assuming the application can safely
replace its own dependencies. Any persistent automation or production change
still needs task-specific authorization. `not-applicable` and `blocked` require
clear reasons; do not conceal an unresolved requirement as future work.

Record each decision with concrete findings and, for `required` security or
fuzz work, the case IDs that cover it; a `blocked` decision keeps its planned
cases open. A maintenance decision names its owner, advisory source, cadence,
mechanism, validation and rollback.

### Layers and real boundaries

Before code, record test scope and replacement strategy separately from the
browser/service/API views. Do not infer one decision from another:

| Decision | Select when | Record |
| --- | --- | --- |
| Unit | A local rule, transformation, boundary, or isolated contract needs direct diagnosis. | Planned case/test path and the outputs, errors, invariants, or state effects asserted. |
| Integration | Collaboration across real local components, persistence, messages, or an exposed contract carries risk. | Boundary, dependency setup, fixture isolation, and observable cross-component effect. |
| End-to-end | A critical user or operational journey needs proof through its actual entrypoint. | Entry path, selected environment, user-visible result, and required readiness/cleanup. |
| Mock/fake | An isolated dependency must be replaced for diagnosis, cost, determinism, or unavailable infrastructure. | Replaced dependency, reason, fidelity limit, and the retained real-boundary check or its blocked cause. |

At discovery/spec, and whenever changed behavior warrants it, assess each
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

Review documentation for new or changed files/modules, classes, public
functions/interfaces and non-obvious internal boundaries. Provide the small,
colocated contract a caller or maintainer needs: purpose; inputs/preconditions; outputs;
errors; side effects; and only relevant invariants, timing, ownership, or
retry/idempotency constraints. Link to the applicable test cases. Use docstrings,
comments, interface documentation, or a small module reference as appropriate.
At file/module level explain responsibility and entry points; at class level
explain ownership, lifetime and invariants; at function level explain the caller's
contract. Include only what applies, following the repository's conventions.
Do not narrate every line, repeat obvious types/signatures, or mandate boilerplate
for trivial helpers. One authoritative explanation plus links is preferable to
copies in source, README, run receipts, and chat. Add an index only when navigation
needs it. Precision takes priority over advisory word, character or token limits;
never omit a necessary contract, error condition or material caveat to meet them.

Add or preserve key **tombstone comments** where a tempting removed approach could
reintroduce a defect: briefly name what must not return, why it failed, and the
replacement or relevant regression/decision reference. Put the warning at the
surviving decision point; do not retain dead code or add a tombstone for every
deletion. Revalidate existing warnings when behavior changes; remove or update
them only when their reason no longer applies.

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
Before step execution, store proposed docs/cases in the spec/plan results; discovery
and research do not create product files. Plan documentation outputs and checks explicitly.

## Iteration documentation and reuse

`document` records the documentation disposition for the current item, and
`skill-assess` and `skill-validate` record the reusable-skill decision and its
checks. An assessment is required; needless edits or skill creation are not.
Update or explicitly assess relevant README and interface documentation before
actual verification, and complete `skill-validate` when a skill is selected.

Read the actual code/test diff, accepted step plan and relevant repo docs.
Prefer colocated concise contracts/comments for non-obvious behavior;
incrementally update affected README sections and existing design/architecture/
environment notes, or give a concrete unchanged reason. Always assess the repo
README (record absence and decide whether this step needs one). Use AGENTS.md for
short stable project navigation/conventions when useful, not run state, secrets,
raw observations or copied manuals. Link detailed durable knowledge once from
the existing appropriate index instead of duplicating it.

### Reusable product skills

Describe the disposition in `summary` and link its evidence in `evidence_refs`,
alongside the packet's `outcome`. ShipLoop preserves those ordinary references;
it does not validate skill frontmatter,
index links, meaningful execution or compatibility through a skill-specific
receipt. Those remain host review and verification obligations.

During `discovery`, read the existing repo skill index or relevant README/AGENTS
links and inspect plausible skills before proposing new implementation. A missing
index is not a blocker and does not itself justify creating a skill. During each
`step-plan`, reopen the current index and relevant contracts: an earlier item may
have created or evolved a skill since the plan was written. Record fit or no fit
and revalidate any earlier selection against this item's requirements. Discovery
inspects skill packages without editing them and records findings under the
existing project-knowledge notes/index policy. Create or evolve skill packages
during authorized implementation or documentation work.

Ask whether a reusable repo-local skill would materially help later steps or
maintenance. Check existing skills first. Record a decision and rationale even
when the answer is no. Create or update one only for a demonstrated reusable
procedure or boundary, not a narrow transcript of this step or a speculative
framework. Reuse existing repo layout, or `skills/<name>/SKILL.md` when none is
established. Keep it inside the product worktree; no global installation, new
connector or privilege change follows from this decision.

Choose the smallest useful disposition after reading the candidate's actual
contract and examples:

- **Reuse unchanged** when existing inputs/defaults cover the task; different
  data or parameter values alone do not require another skill.
- **Update locally** when a small compatible extension captures a demonstrated
  lesson. Preserve supported inputs, defaults and older examples; add only the
  conditional rule or helper the new evidence warrants.
- **Create separately** when no suitable skill exists or combining contracts
  would obscure selection or break an existing consumer. Keep the older skill
  when its use remains supported and distinguish their triggers in the index.
- **No skill work** when a normal code/test/doc change captures the learning
  adequately. Assessment does not require skill creation or edits.

Treat installed/shared skills as reusable inputs, not edit targets for a product
run. If specialization is needed, place it in the product's local skill layout,
and record the adaptation rationale. When copying or deriving external skill
content, retain its source/revision and applicable license. Avoid a dependency
on a machine-specific installed path. Do not modify or install global skills.

A useful local skill documents:

- a discriminating name/description and when to use it (and meaningful exclusions);
- why it helps, the task/output it supports and the known limitations;
- variable inputs with types/required/default rules and safe example invocation;
- how to perform/verify the procedure, expected outcomes, failure/recovery and
  permission boundaries without embedding credentials or machine-specific IDs;
- relative references to relevant code, tests and design/environment material,
  with revalidation triggers for volatile assumptions.

Default stable repository conventions, not changing identities, credentials or
authorization. Explicit task inputs override defaults only within the skill's
supported contract. Re-read current source contracts/configuration when the
default depends on them. Keep task-specific values and observations in the task
evidence; save the reusable decision rule and its rationale in the skill.

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

For changed skills, validate both the motivating example and an older supported
use, plus meaningful default/override and failure cases. For a cold-context trial,
give a fresh reader only the repository index, linked skill/resources and a new
task; preserve whether it actually found and applied the procedure. Record the
selected entrypoint, effective inputs, disposition, checks and remaining limits
in ordinary evidence. A missing fresh-reader trial remains untested, not proof
of cross-context reuse. Do not copy the conversation into the skill to make a
trial pass.

Keep a compact selection note in the existing plan/evidence home: disposition
and rationale; repo index and selected entrypoint; effective non-secret inputs
and their default/override sources; applicable product contract; validation
locators and limits; and what changes require revalidation. Link the relevant
sources in ordinary `evidence_refs`, with explicit repository/run bases. No fit
needs a reason and the inspected sources, not an invented entrypoint or check.
When creating the work queue, put only the relevant selection/index locator and
revalidation condition in the item's `context`. Later changes update the linked
plan/evidence note, not the script-owned queue. Before Improve's first review,
carry relevant locators into its host-authored contract/review notes; a parent
packet alone does not populate the child contract.

At `carry-forward`, maintain the existing repo index/README link and link that
entrypoint from `SHIPLOOP.md` so another item or run can discover the current
local skills. Retain stable procedures/default sources outside disposable run
storage. Keep task-specific values and raw checks in evidence; a prior selection
or passing check is a revalidation input, not authority for the next task.

## Implementation constitution

Use these stack-neutral defaults in the current step, not a new governance loop.
Respect user requirements, approved contracts, applicable repository instructions
and established language/style tooling. A conflict needs clarification, not a
silent override. Never relax safety or acceptance to claim simplicity.

Use the [coding decision guide](coding-guidance.md#select-guidance) when planning,
implementing or verifying an item. It links conditional practices and platform
contracts; read only applicable sections and retain their decision/check locators
in the existing plan and review notes. The rules below and the
[documentation contract](#documentation) remain authoritative for their subjects.

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
   At CLI, file, subprocess or service boundaries, distinguish missing/malformed
   input, execution failure and a successful transport carrying an error result.
   Check the documented response contract before using its payload. Keep required
   evidence failures explicit; optional diagnostics may be unavailable without
   replacing a valid result. A fallback must be supported by the contract.
4. **Compact, useful documentation.** Prefer clear names. Comment on intent,
   invariants, surprising constraints and tradeoffs, not obvious syntax. Document
   changed public/non-obvious contracts as specified in [Documentation](#documentation).
   No mandatory comment on every function, machine-only tags, copied code prose,
   or abbreviated names merely to save tokens. Keep essential caveats.
5. **Evidence before polish.** Plan tests first; inspect code before refining
   actual tests; run required lint/tests after edits. Update affected README/docs.
   Prefer existing tools and focused cases over checklist-driven test layers.
   Preserve the independent expected outcome and required real-boundary evidence.
   Confirm a reused result applies to the candidate, command, configuration and
   target it actually checked; revalidate affected evidence after changes. Missing, stale
   or skipped required evidence is incomplete, never a pass. Evaluate acceptance
   using its authoritative criterion; supporting diagnostic or health scores
   cannot substitute for a different required outcome. For a changed decision rule, exercise a valid case
   and a discriminating failure, including conflicting signals when relevant.
6. **One convergence owner.** A bound Improve child uses the selected Improve
   card and its bound Until Loop for review, plan, apply, check and
   two-trivial assessment within the parent-supplied scope and commit policy.
   Those two passes are self-passes by one executor, not independent reviews.
   ShipLoop owns the parent action, the graph and the child's import. Do not
   wrap the child's work in another converging loop or count its passes in the
   parent. A material change reopens affected evidence.

In the plan note, record consequential design choices; record changes or
justified exceptions in the result summary and its evidence notes. Personal
style preferences alone are trivial; behavior/security/contract changes are
material. This is host judgment, not a new field, score or proof of quality.

## Iteration

Cross-item system tests have separate prerequisite-owned activities; they never
replace this item's required tests. Use the
[system-test contract](system-tests.md#reassessment-change-and-closure) at
`carry-forward` and for pre/post-deployment test sequencing.

Use [Test cases](#test-cases), [Surface selection](#surface-selection), or
[Documentation](#documentation) only when the current stage needs their record
shape or selection rules; do not load unrelated sections or past items.

The packet owns the order. This table locates duties and records; it is not a
second scheduler.

| Current stage | Duty and existing record |
| --- | --- |
| `step-plan`, `test-spec` | Put the pre-code case-to-requirement matrix in the plan and test notes. Use the implementation constitution; only the accepted plan authorizes its scoped code edits. |
| `baseline`, `test-author`, `test-red` | Observe the item's starting state, author executable tests from the independent cases, and record the expected RED failure without production edits. |
| `implement` | Write the planned code; inspect the actual diff and learnings. |
| `test-green`, `test-refine`, `regression` | Run the authored tests; refine cases from the code actually written with an independent basis; run the affected regression set. Required failed, blocked or unrun checks remain unfinished. |
| `document`, `skill-assess`, `skill-validate` | Required docs/README and reusable-local-skill decision, with safe paths, reasons and intended readers. Make documentation/skill edits before fresh verification, not after it. |
| `static-checks`, `verify` | Run required lint/tests and relevant examples/links; diagnose failures. A source edit after documentation needs its affected checks rerun. A test-oracle change needs independent justification. |
| `integrate`, `integration-verify` | Assemble through authorized Git/worktree work and recheck the combined candidate. Assembly is not deployment. |
| `carry-forward` | Use the [carry-forward contract](carry-forward.md) for scoped observations and the future queue. The last carry-forward's Improve review covers every executed step together. |

Keep case IDs, independent sources, environment, observed outcomes and evidence
references compact in the result summary and its linked notes. Results are
imported into authoritative Markdown; no sidecar schema or assumed chat memory
is needed. Keep essential facts inline and detail linked for a fresh context.
Update product artifacts before verification; run-only observations go in the
packet's inbox, not into the product tree after checks (which would stale the
evidence).

## Deployment and handoff

Use the [stage completion map](#stage-readiness-and-completion).
`product-acceptance` precedes `release`: it reconciles due product checks and
explicit pending post-release cases. `release-verify` obtains the latter's actual
observations; `handoff` reconciles the final evidence.

At `product-acceptance`, reassess the selected browser/service/API views against
the whole product, not only the final item. Match the checks to every
acceptance criterion. Review expected-versus-observed outcomes, test adequacy,
function/API contracts, README accuracy, and environment identity. Required
blocked/not-run checks remain unfinished. Product changes discovered here use
corrective work items through `replan`, including documentation-only fixes, not
direct edits around the inner loop.

If whole-product acceptance depends on a real deployment, plan authorized
deployment/readiness and dependent verification as earlier work items or as the
pending post-release cases that `release-verify` owns. Do not certify that
acceptance locally while waiting for a later release. Record the release's
actual effect separately from its consumer observations, and inspect prior
delivery before retries. Failed/unknown delivery checks keep the release
unfinished; pause for direction when correction requires work or authority
unavailable at that stage. Never implicitly authorize rollback or redeployment.

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
