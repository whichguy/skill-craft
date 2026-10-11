# test-strategy: re-cut draft (worker A)

## 1. Goal (R1)

Map every requirement to the checks that will prove it: write the harnesses, case allocation, suite commands, ID
convention and real-boundary checks to the matching sections of HOME/test-strategy.md.

## 2. Duty

1. Build a risk-based strategy from HOME/spec.md and FEATURE/spec.md before any code. Under HOME/test-strategy.md
   ## Harnesses and suites, allocate each requirement clause to a case or an existing verification record, with its
   independent expected outcome, layer (unit, integration, system, consumer), negative cases, fixtures and data,
   environment and authorization needs, required surface, due stage, owner and prerequisites. Mark every check
   planned; a planned check is not a pass. Name an expected-RED control where test-first work applies.
2. Plan checks for new and preserved behaviour from FEATURE/spec.md and RUN/notes/current-system-baseline.md. An
   unknown existing behaviour needs discovery before you assert a preservation target. An old pass is not a current
   pass.
3. Map each applicable new and preserved non-functional criterion to a check with its environment and workload
   prerequisites. Missing evidence or access is not N/A.
4. Select or revalidate the harnesses and suite entry points (Repeatable test-suite guide). Reuse a prior run's
   harness only after revalidating its fit. Choose target-native tests from the discovered remote code, test assets
   and deployment gate, or record the exclusion with its evidence (Target-native test selection). Choose testing
   systems and browser tools by capability, not product name (for example an HTTP client such as curl, DevTools
   inspection, Playwright browser automation; these are examples, not a checklist). Write in
   ## Harnesses and suites each choice's role, fit, availability, prerequisites, setup and isolation, fixture
   lifecycle, the runner and any coverage or report tool, the selection rationale and its revalidation condition.
   Separate inspection from retained assertions.
5. Reuse, configure or extend the existing frameworks and helpers before defining the smallest missing test facility
   (Reusable test facilities). Read the selected skill and MCP references; never assume a named skill or MCP is
   available or authorized. Record each facility's definition locator, interface, readiness or gap, owner and
   revalidation condition under ## Harnesses and suites. Name a missing facility in `summary` as prerequisite work for
   plan. The stage that owns it builds and validates it before dependent checks. Readiness is not test execution;
   later tests reopen the recorded definition.
6. Under ## Real-boundary checks, record for each check where it runs and what it targets: local, client checks
   against a deployed target, or remote-resident tests. Name the checks that run against the deployed target and how.
   For remote tests, record the framework, availability, access, deployment prerequisites and the authorized route to
   define or register, install and invoke them. A local pass is not a remote pass. Keep local support separate from
   required consumer observations, and do not narrow a behaviour list to a render smoke.
7. For affected service contracts (Service discovery guidance), map cache authorization and invalidation, remote
   reconciliation, async recovery and observability to independent outcomes at their real observation boundary under
   ## Real-boundary checks. A fixture result does not prove live permissions, event delivery or operator log access.
8. Consume the initial baseline from discovery (Initial repository baseline guide); selecting a suite is not proof.
   Record its coverage and limits, and distinguish a passing subset from a failed, blocked, intermittent,
   missing-test or expected-RED observation. Name in `summary` each setup, repair or test-bootstrap prerequisite and
   the evidence it needs before dependent feature checks.
9. Write the focused, smoke and full-suite commands under ## Commands, each in a fenced code block, never in a
   Markdown table cell (an escaped `\|` in a cell becomes a literal pipe, matches nothing and can still exit 0). For
   each, give its inclusion rule, expected cost, environment and fixture prerequisites, and the test IDs it may print.
   A passing command names the IDs or cases it ran. This section is the one owner of the suite commands: later notes
   point at it, and a stale copy elsewhere is a defect to fix. Plan durable regression tests, not one-off probes.
   Smoke is a bounded subset, never evidence for the full suite.
10. Under ## ID convention, declare each ID as the tests will be titled. A listed ID counts only as its own word in a
    test's printed name (a test titled `TC-4a` does not show `TC-4`: title it `TC-4 (a)`).
11. For a case that needs a host tool (a browser, a device, an account, a service), name the tool and probe it now by
    doing the case's first step, not by reading its version. While the product does not exist, probe a stand-in, not
    the product's address: for a browser, write a one-line page in RUN/scratch, open it by `file:` URL or from a
    throwaway static server you stop afterwards, and read its title back with the tool as the case will use it; for
    an account or a service, make a harmless read the tool can make today. Cite the probe output in `evidence_refs`.
    Record only a failed probe as an access gap under ## Real-boundary checks, with the requirement it leaves
    unobserved. Give the case its own opt-in command or flag, so the default test command passes without the tool.
12. When the request names a page or screen people use, plan a case that drives it through its user interface (in a
    browser or on a device), with its browser actions and expected visible outcomes and its tool named and probed as
    in item 11 (Consumer testing guide). Otherwise record the outcome as unverified with its owner and due stage
    (handoff, or the stage whose external effect it gates). An HTTP response alone is neither.
13. Before you submit, fix any of these in HOME/test-strategy.md:
    - a step, example or expected result that cannot be replayed exactly: name the concrete inputs, values,
      identifiers and sample interactions;
    - an expected result or check that a weaker stand-in would pass: a hardcoded value, a missing assertion, a
      title-only test, an absent required name;
    - a documented command that does not run what it claims on the target runtime: run it once and record the exit
      code and the cases it executes;
    - a requirement, test ID or case dropped or weakened against the prior accepted version;
    - a claim about what the runtime, platform or a library can do that a decision depends on, with no
      primary-documentation source or probe result: check it, and correct the strategy where it is wrong.
14. Put in `evidence_refs` HOME/test-strategy.md, each probe output and each source you used.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Repeatable test-suite guide (repeatable-test-suites.md#select-or-revalidate-the-harness): item 4.
- Target-native test selection (repeatable-test-suites.md#select-target-native-tests): item 4.
- Reusable test facilities (repeatable-test-suites.md#reuse-and-define-test-facilities): item 5.
- Service discovery guidance (service-discovery.md#verification): item 7.
- Drop (never cited): Current-system baseline guide (item 2 reads the baseline note directly), Test-case planning
  guidance, System-test catalog guidance, State and data assessment. Unsure about State and data assessment: spec
  item 7 writes its checks into FEATURE/spec.md, and item 1 here allocates every clause, so the guide adds nothing
  the text needs.
- Policies the prose names: Initial repository baseline guide (item 8), Consumer testing guide (item 12).

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| T1 Risk-based strategy from the spec before code. | Item 1 |
| T2 Outcomes, layers, negative cases, fixtures, environment and authorization, owner per check. | Item 1 |
| T3 Planned vs executed; expected-RED controls. | Item 1 |
| T4 Allocate each clause to a case or record with surface, due phase, owner, prerequisites. | Item 1 (## Harnesses and suites). Unsure: no named section of HOME/test-strategy.md holds a run's allocation; this draft uses ## Harnesses and suites |
| T5 Local support separate from consumer observations; no render-smoke narrowing. | Item 6 |
| T6 NFRs to checks with prerequisites; missing evidence is not N/A. | Item 3 |
| T7 Read the Repeatable test-suite guide. | Item 4 |
| T8 Select harnesses and entry points; reuse prior harness after revalidation. | Item 4 |
| T9 Target-native selection: remote assets, deployment gate, selections or exclusions. | Item 4 |
| T10 Testing systems and browser tools by capability. | Item 4 |
| T11 Record roles, fit, availability, prerequisites; inspection vs assertions. | Item 4 |
| T12 curl, DevTools, Playwright as examples, not a checklist. | Item 4 |
| T13 Browser UI criteria: plan browser actions and visible outcomes. | Item 12 |
| T14 HTTP success alone does not validate them. | Item 12 |
| T15 Apply the Consumer testing guide; retain access gaps. | Item 12; access gaps: item 11 |
| T16 Link the durable strategy note with rationale, fixture lifecycle, entry points, revalidation. | Items 4, 14 |
| T17 Exact focused, smoke, full commands with inclusion, cost, prerequisites. | Item 9 |
| T18 One file owns the commands; others point at it; stale copy is a defect. | Item 9 (## Commands is the owner). Unsure: today allows "e.g. the repository's testing doc" as the owner; this draft fixes it to ## Commands, which may link the repository's doc |
| T19 Fenced code block, never a table cell (escaped pipe). | Item 9 |
| T20 A passing command names the IDs it ran. | Item 9 |
| T21 Durable regression tests; smoke never evidence for full. | Item 9 |
| T22 Execution location separate from target location. | Item 6 |
| T23 Remote framework, access, prerequisites; authorized route for remote tests. | Item 6 |
| T24 A local pass is not a remote pass. | Item 6 |
| T25 Initial baseline guide: consume the observed baseline; selection is not proof. | Item 8 |
| T26 Coverage and limits; passing subset vs failed/blocked/intermittent/missing/RED. | Item 8 |
| T27 Name setup/repair/bootstrap prerequisite and evidence, in evidence_refs and planned item context. | Item 8 (`summary`; plan carries it into item context, plan item 10) |
| T28 Prior baseline and spec sections for new and preserved checks. | Item 2 |
| T29 Unknown semantics need discovery; old pass is not current. | Item 2 |
| T30 Service discovery checks: cache, reconciliation, async, observability. | Item 7 |
| T31 Independent outcomes at real boundary; fixtures do not prove live behaviour. | Item 7 |
| T32 Settle these now, so later stages do not guess. | CUT: a reason; items 9-12 say "now" where it binds |
| T33 For each command, the test IDs it may print. | Item 9 |
| T34 Host-dependent case: name tool, probe by first step, not version. | Item 11 |
| T35 Stand-in probe (scratch page, file: URL or throwaway server; harmless read). | Item 11 |
| T36 Failed probe is an access gap recorded now with the requirement unobserved. | Item 11 |
| T37 Opt-in command; default command passes without the tool. | Item 11 |
| T38 ID_WORD_RULE. | Item 10 |
| T39 Declare each ID as the tests will be titled. | Item 10 |
| T40 Page or screen: UI-driving case, or unverified with owner and due stage; HTTP alone is neither. | Item 12 |
| T41 Planning review focus lead "(the Improve child applies ...)". | Item 13 lead; Improve mention CUT (R3) |
| T41 focus conditions 1-5. | Item 13 ("correct the plan" becomes "correct the strategy") |
| Test: target-native tests across unit, integration, system, consumer layers. | Items 1, 4 |
| Deploy: which checks run against the deployed target, and how. | Item 6 |
| Tools: test runner and any coverage or report tool. | Item 4 |
| TEST_FACILITY 1 (read skill and MCP refs; reuse before the smallest new facility; never assume availability). | Item 5 |
| TEST_FACILITY 2 (definition locator, interface, readiness, owner, revalidation in evidence_refs and test docs). | Item 5 (## Harnesses and suites) |
| TEST_FACILITY 3 (carry locators into item context and the Improve child's notes). | Item context: CUT here, test-strategy has no work items (plan item 10 carries them); Improve CUT (R3) |
| TEST_FACILITY 4 (planning names missing work; owning stage builds it before dependent checks). | Item 5 |
| TEST_FACILITY 5 (readiness is not execution; later tests reopen the definition). | Item 5 |
| _PLANNING_HANDOFF 1, 4. | Items 8, 14 |
| _PLANNING_HANDOFF 2-3 (plan and step-plan only). | CUT (R3) |
| Renderer: Planning phase intent "Map requirements to observable checks, targets, setup, isolation, due stages; planned checks are not passed." | Goal, items 1, 4; renderer drops the line |
| Renderer: Improve line. | CUT (R3) |

## 6. Size

- Today: 8,586 characters.
- Proposed: 6,994 characters (81%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.
