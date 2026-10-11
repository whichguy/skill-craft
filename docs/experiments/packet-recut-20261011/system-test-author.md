# system-test-author: re-cut draft (worker C)

## 1. Goal (R1)

Author the whole-product system tests: write one catalog row per case and the integrated test plan in
FEATURE/system-tests.md, record each runnable case's command in `system_commands`, and record each case that cannot
run here as an open item in `assumptions`.

## 2. Duty

```text
1. Gather the sources. Read the run's test strategy (HOME/test-strategy.md and the test-strategy result), every
   item's test cases (the `test_cases` hand-off), the open items quoted below, and the system-test obligations
   under FEATURE/plan.md ## Open. Take the latest done test-decision record for every relevant completed item
   (step-plan, test-spec or test) from state.md's accepted history, with the locators it retained. Do not infer whole-product coverage from the last transition or final item. Put the action, result
   and test-note locators you used in `evidence_refs`.
2. Choose the cases. Each due-later case from item 1 becomes a system case here, or an open item with its due stage
   (item 7). Add cases for the real integration, consumer, runtime, security, accessibility, migration,
   compatibility and operational boundaries that apply. Reconcile suite membership and prerequisites before adding
   a case. Mark a boundary N/A only with the reason it does not apply; missing access is not N/A.
3. Write the catalog in FEATURE/system-tests.md: one row per case in the System-test catalog guidance shape (case
   ID, phase, requirement, expected outcome, environment and target, prerequisites, executable reference, owner).
   A post-release case is owned by release-verify; required post-release checks stay assigned to release-verify,
   never waived.
4. Write the tests. Reuse the existing harness, frameworks and helpers first (Repeatable test-suite guide, Reusable
   test facilities), and build only the smallest missing facility. Never assume a named skill or MCP is available
   or authorized. Record each facility's locator, interface, readiness or gap, owner and revalidation condition in
   FEATURE/system-tests.md. Add the new system cases and the retained INNER cases to the repeatable full-suite
   entry point and keep the smoke selection; do not copy tests into another suite. Each new test file names the
   requirement or test IDs it covers in its opening lines, and shared test helpers check their arguments. Check
   shared setup cost, independent assertions, isolation and failure teardown. When the remote framework requires
   it, version the remote-resident test definitions and their registration, with a repeatable authorized install
   and invocation.
5. Run each system command once now, and confirm its discovery and rerun work. A command that cannot pass here is
   changed to observe the same requirement another way; say what changed and why in `summary`. Every case ends
   validated, validated another way, or unachievable (item 7). A case written but not run is not an end state.
6. Record `system_commands`, one row per runnable command, shaped like a step plan's test_commands. Each row's
   suite is `focused`, `regression` or `check`. `focused` and `regression` are for runners whose output ShipLoop
   can count, and carry the case `ids`. A command that is not a test runner (a shell pipeline, a grep, a curl
   probe) is suite `check`, judged by its exit code, with no ids or min_tests. Mark a row `"host_dependent": true`
   when its cases need a host tool (a browser, a device, an account, a service): ShipLoop then also runs the
   project's regression commands at system-test and refuses if any of that row's ids appears in their output,
   because the default suite must pass without the host tool. When no system test applies, give an empty list with
   `system_commands_na` and the reason.
7. A case that cannot run here (for example a browser or an account this host cannot reach) is unachievable. Leave
   its command out of `system_commands`, because ShipLoop reruns every recorded command and refuses unless each
   passes. Record it in `assumptions` as an open item: `assumption` names the case ID and the requirement it leaves
   unverified; `check` says who does what and what they report; `owner` names that person; `reason` says why it
   cannot run here; `consumer` is the stage it is due at (handoff, or the stage whose external effect it gates).
   Continue with every case that can run. Report blocked only when nothing else can proceed, and replan when the
   plan is wrong.
8. Write the integrated test plan in FEATURE/system-tests.md under the catalog (OUTER test-planning handshake): the
   current candidate/boundaries, selected cases and oracles, commands, lifecycle/sharing decisions, cost,
   prerequisites and execution owners. Say which checks run now at system-test and which need the authorized
   release first. Cite FEATURE/system-tests.md in `evidence_refs`, and put the decisions and constraints the plan
   rests on in `summary`.
```

Shared blocks: OUTER test plans is folded into items 1 and 8 (this stage owns the plan, so only the "create or
reconcile" half applies). Test facilities is folded into item 4. The planning hand-off is folded into item 8. None
of the three needs to print for this stage.

## 3. Checked by

- `system_commands` missing, or empty without `system_commands_na`.
- `assumptions` missing, or an open item whose consumer is not a later OUTER stage.
- At system-test, ShipLoop reruns every command recorded here and refuses unless each passes.
- release-plan is refused while FEATURE/system-tests.md is missing or empty.

## 4. Guides to keep

- Repeatable test-suite guide (repeatable-test-suites.md#select-or-revalidate-the-harness): item 4.
- System-test catalog guidance (system-tests.md#catalog-shape): item 3.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 8.
- Reusable test facilities (repeatable-test-suites.md#reuse-and-define-test-facilities): item 4.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Record the system tests in `system_commands` (shape; suites) | 6 |
| A non-runner command is suite `check`, exit code, no ids/min_tests | 6 |
| `focused`/`regression` for countable runners | 6 |
| Mark `host_dependent`; ShipLoop runs regression and refuses if ids appear | 6 |
| ShipLoop runs every one at system-test, refuses unless each passes | 7 (reason) and Checked by |
| Run each system command once while authoring | 5 |
| A command that cannot pass is changed to observe another way | 5 |
| A case that cannot run here is unachievable; leave its command out | 7 |
| Record it as an open item in `assumptions` (case, requirement, owner, due stage) | 7, now mapped to the row fields |
| Continue with every runnable case; blocked only when nothing else can proceed | 7 |
| A command recorded as not run is not an end state | 5 |
| No system test applies: empty list with `system_commands_na` | 6 |
| Reopen the run-wide test strategy source | 1 |
| Latest done test-decision record per completed item, with prior locators | 1 |
| Read every item's test cases, open items, FEATURE/plan.md ## Open | 1 |
| Each due-later case becomes a system case or an open item | 2 |
| Keep selected action/result and test-note locators in evidence_refs | 1 |
| Do not infer whole-product coverage from last transition | 1 |
| Reconcile suite membership and prerequisites before adding cases | 2 |
| Author cases from the assembled candidate and global strategy | 2, 4 |
| Cover integration, consumer, runtime, security, ... boundaries | 2 |
| Justified N/A says why; does not erase a required check with missing access | 2 |
| Integrate retained INNER cases with full-suite entry point; keep smoke; no copies | 4 |
| New test file names its IDs; shared helpers check arguments | 4 |
| Review setup cost, assertions, isolation, teardown (Repeatable test-suite guide) | 4 |
| Verify actual discovery and rerun commands | 5 |
| Author/version remote-resident definitions and registration | 4 |
| Retain an integrated test plan (candidate, cases, oracles, commands, ...) | 8, now written to FEATURE/system-tests.md and cited in evidence_refs |
| Which checks run now vs after the authorized release | 8 |
| Required post-release checks stay assigned to release-verify | 3 |
| Consideration Test: author against real boundaries, run each once | 2, 5 |
| Consideration Test: three case end states (open item "in the summary") | 5, 7 (open item goes in `assumptions`, which the gate checks; "summary" was wrong) |
| Consideration Deploy: plan which tests run against the deployed target | 8 |
| OUTER test plans: current plans are the latest done records after the last replan | Shared OUTER test plans text; for this stage CUT: it owns the plan, item 1 names its sources |
| OUTER: retain action, result, plan locators in this result and the Improve child's notes | 1, 8 (Improve half CUT: R3 advance Improve) |
| OUTER: owner creates or reconciles; later stage revalidates | 8 (owner half); the consumer half CUT: R3, other stages |
| OUTER: recover a missing plan; never guess commands, drop coverage, deploy for a check | 1, 2, 6; "deploy for a check" CUT: this stage deploys nothing (STAGE_RULES and release guidance hold it) |
| OUTER: a plan is not execution evidence; material change invalidates observations | 5 (each command runs now); the rerun rule belongs to the executing stages |
| Test facilities: read skill/MCP references, reuse before defining the smallest facility | 4 |
| Test facilities: never assume a skill or MCP is available or authorized | 4 |
| Test facilities: record locator, interface, readiness/gap, owner, revalidation | 4 (FEATURE/system-tests.md) |
| Test facilities: carry locators into item context and the Improve child's notes | CUT: no item context at an OUTER stage; R3 advance Improve |
| Test facilities: planning names prerequisite work; owner builds it before dependent checks | 4 (this stage builds it) |
| Test facilities: discovery is not execution; a later test reopens the definition | 5 (run each command); reopen half is the consumer's |
| Planning hand-off: preserve decisions, constraints, acceptance context in summary | 8 |
| Planning hand-off: "At plan and step-plan, consolidate ..." | CUT: R3, other stages |
| Planning hand-off: each reviewed step's criteria remain its sole directive | CUT: R3, no steps here |
| Planning hand-off: register produced planning files as absolute evidence_refs | 8 |
| "Improve: Every system-test-author result ... starts this action's Improve child" | CUT: R3 advance Improve |

## 6. Size

- Today: DUTIES 3,668 + considerations 846 + OUTER test plans 954 + Test facilities 807 + planning hand-off 560 =
  6,835 characters.
- Proposed duty (the fenced text above): 4,631 characters, with no shared block printed (-32%).
