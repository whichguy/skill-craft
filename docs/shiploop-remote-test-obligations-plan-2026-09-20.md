# Remote code and native test obligations

## Decision and scope

Adopt a small prompt clarification. ShipLoop already follows MCP gateways into
task-relevant systems, distinguishes local/client-to-remote/remote-resident tests,
and retains test decisions across INNER and OUTER stages. The missing explicit
connection is from remotely held code/test assets and the actual deployment gate
to the decision to select or exclude a native suite.

This evaluates the supplied checkers recommendation; it does not independently
verify that run's org, code inventory, deployment options, or test results.

KISS/YAGNI decisions:

- Adopt affected execution boundaries and actual release requirements as inputs
  to existing test decisions, including remote-only code and test definitions.
- Reject a mandatory row for every language: the same language can run in several
  places, unrelated code need not be tested, and configuration can affect remote
  code without adding a local source file.
- Reject a second inventory, new stage/schema/validator, automatic remote crawl,
  mandatory MCP, or assumed universal native runner. Existing Markdown notes,
  case records, evidence references, and stage owners suffice.
- Keep platform-specific details in the Salesforce card; do not mandate Apex,
  hard-code a universal coverage percentage, or create empty tests to fill a row.

## Evidence and limits

Inspected source at `0e6db6d`: platform-discovery's gateway guidance;
research-loop's bounded discovery; environment-lifecycle's promotion record;
repeatable-test-suites' harness, facility, and local/remote sections; v3 strategy,
implementation, refinement and release prompts. These already cover most of the
recommendation. The change should link these decisions, not restate those guides.

Primary sources checked 2026-09-20:

- [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools):
  tool discovery describes exposed operations. Inferring that this is a complete
  inventory of the backing application's code or tests is unwarranted.
- [Salesforce LWC testing](https://developer.salesforce.com/docs/platform/lwc/guide/testing):
  Jest checks components without connecting to an org or running in a browser.
- [Salesforce deployment test levels](https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_project_deploy_start.html):
  defaults depend on package contents and target; coverage rules also depend on
  selected test level. Development deployment may use NoTestRun. Thus neither
  “every Lightning app requires Apex tests” nor “75% always means this deployment's
  code” is a safe generalization. Packaging/CI routes need their own actual rules.
- [Apps Script remote execution](https://developers.google.com/apps-script/api/how-tos/execute):
  invoking a function has deployment and access prerequisites. This is not proof
  that a project has a test suite or a generic `clasp tests` command.

## Placement in the existing lifecycle

| Existing owner | Added decision or handoff |
| --- | --- |
| discovery / research | Inspect task-relevant remote code, configuration and test assets through supported safe reads; record source/target identity, observation limits and missing access. |
| environment note | Record the chosen deployment/promotion operation's test gate alongside its target and prerequisites. Link it from test decisions. |
| spec / definition done | Existing behavior, boundary and measurable-criterion duties remain sufficient. A test requirement is not evidence of execution. |
| test-strategy / test-spec | Select native checks where affected behavior or the actual gate requires them; justify exclusions from both. Unknown is distinct from required-but-blocked. Use existing cases and due phases. |
| test-author / test-red | Existing facilities/remote-definition rules own registration, known interfaces, setup and meaningful RED; no new authoring stage. |
| implement / test-refine | Revalidate selections and exclusions when actual code, configuration, dependencies, remote assets or delivery route changes. Preserve revised decisions in existing notes. |
| system-test-author / system-test | Existing whole-product reconciliation consumes retained item decisions and preserves later release obligations. |
| release-plan / release-check / release-verify | Recheck the gate for the actual target/operation; existing release handshake assigns pre/post checks and retains unrun blockers. |

Ready to define means the affected boundary and material discovery gaps are
known. Definition done means expectations are specified. Tests planned means
routes, prerequisites and due owners are identified; tests implemented means
definitions are executable/registered where claimed. None substitutes for an
actual required runtime test result.

## Implementation and validation plan

1. Baseline existing smoke and relevant discovery, environment, test-facility and
   v3 guidance suites before changing skill behavior.
2. Add one canonical target-native selection subsection to repeatable-test-suites;
   link it from existing discovery/environment guidance and four relevant v3
   packets. Add a short Salesforce instance of the generic rule.
3. Check persisted/cold packets carry those locators and duties without changing
   graph or result shape. Review the scenarios below independently, then rerun
   relevant suites, packet bounds and generated-package consistency.
4. Preserve independent review findings and exact verification limits here.
   Hermetic prompt checks do not prove future model compliance or live org tests.

| Interpretation case | Required decision |
| --- | --- |
| Local-only change | No remote system, native suite or inventory invented. |
| Confirmed LWC-only development deploy, no affected Apex and no Apex gate | Evidence-backed Apex exclusion; retain LWC and required browser checks. |
| Remote server/test code exists, absent locally, behavior affected | Consider native coverage using the actual exposed route; local file absence cannot exclude it. |
| Configuration-only change can affect existing server code | Include affected regression boundary despite unchanged language/file set. |
| No affected server behavior, but chosen CI/deployment requires native tests | Retain required gate and checks with their actual owner/due phase. |
| Metadata read denied or deployment gate unknown | Unresolved discovery prerequisite, never evidence-backed N/A. |
| Required remote suite known, runner unavailable | Required-but-blocked/unrun; plan minimum missing facility only if justified. |
| Unrelated remote code exists, no applicable gate | No automatic full remote test crawl or invented implementation. |
| Implementation adds a remote call or release target/test level changes | Reopen relevant exclusion, update cases/prerequisites, retain old receipt as historical. |

## Results

Implemented as ShipLoop 0.18.7: one canonical selection subsection, discovery and
environment links, a conditional Salesforce example, and selected v3 packet
reminders. The existing graph, result schemas, state handling and runners are
unchanged. Generated plugin copies and catalog versions were regenerated through
the repository sync script.

Baseline: the repository smoke group and four targeted suites passed before the
first skill edit. Updated checks: 126 tests passed across v3 guidance (23), packet
bounds (7), reference routing (8), navigator v3 (23), environment lifecycle (5),
repeatable experiments (12), generalized discovery (43) and access readiness (5).
Plugin synchronization check and `git diff --check` passed. No new keyword-only
test was added: existing route/anchor and cold-packet tests cover the changed
delivery mechanism; interpretation review addresses the new prose decisions.

An independent skeptical diff review found no material issues. A separate reader
given only the affected references and the nine scenarios (without the expected
decisions) reached the intended selections, exclusions, unresolved and blocked
outcomes. It also identified the correct revalidation of the stale exclusion.
That is a bounded interpretation check, not a before/after effectiveness trial.
Known contracts can support authoring while a target is unavailable; actual
execution/registration still needs evidence as the existing guide requires.

These checks do not establish actual remote code discovery, test execution,
deployment, or universal future model compliance. No Salesforce org was accessed
and no installed host skill binding was changed. Publication and hosted CI
outcomes are reported separately from the local checks above.
