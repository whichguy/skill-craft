# release-plan: re-cut draft (worker C)

## 1. Goal (R1)

Plan the release without performing it: write its steps, authority, rollback and checks in
FEATURE/release-plan.md, record the post-release checks in `consumer_checks` and the consumer entry in
`consumer_entry`, and record the target and its commands in HOME/environment.md.

## 2. Duty

```text
1. Revalidate the integrated test plan for the release target: the latest done system-test-author record after the
   most recent accepted replan, FEATURE/system-tests.md and the system-test result. Use Target-native test selection
   for this actual payload and its deploy or promotion operation, including any revised gate. Reuse applicable
   tests and facilities (Reusable test facilities); add checks only for changed boundaries or coverage gaps, and
   record each new facility's locator, readiness or gap and owner. If an earlier deployment or test prerequisite is
   still unmet, report replan with corrective work and its evidence; ShipLoop reruns the outer stages.
2. Write the release steps in FEATURE/release-plan.md: target and candidate identity, permission, prerequisites,
   user impact, monitoring and stop conditions. List every operation the user-visible outcome needs as a named step
   with its exact command and its authorization status: the deploy itself, each separate access or visibility
   change (for example assigning a permission set, activating an app or tab), and each browser session a consumer
   check needs, with the selected browser tool. A step no existing approval covers is a pending approval named now.
   Keep source return, artifact publication, deployment, promotion and consumer verification as separate steps.
   Order the remaining schema, data, service and cutover work and name its durable execution owner, observations
   and recovery limits (Release operation guidance, State and data assessment).
3. Record the delivery authority for each step in FEATURE/release-plan.md. A plan does not authorize or perform an
   external operation. A required target or authority gap is blocked.
4. Write the rollback in FEATURE/release-plan.md. In an isolated run, write it for the source return the packet
   states (its return route and rollback recipes come from workspace.md): that route's SHAs and branch names as
   plain `git` commands, never this run's absolute paths, and never a rollback for another route (Workspace return
   guidance). Source return happens at release or handoff, not here. Use an authorized delivery route from the
   execution checkout if one is available (Environment promotion guidance). If source return must happen before the
   consumer checks can run, record the ordering conflict and keep the disposition incomplete; never claim an earlier
   check observed a future return-triggered effect.
5. Write the release test plan in FEATURE/release-plan.md: pre/post check owners, commands/case selectors,
   independent expected outcomes, prerequisites, execution versus target locations, remote test-definition revision
   where relevant, setup/test/teardown, fixture isolation/sharing and cost, cleanup and stop conditions. Say what
   release-check must establish before release, what release-verify confirms after it, and which observations and
   cleanup operations owns. For each post-release confirm command, name the output that shows the result is present
   and the output that shows it is absent; release-check runs it once before the real deploy to prove it can tell
   them apart.
6. Record the post-release consumer checks as commands in `consumer_checks`, shaped like test_commands; a `check`
   row is judged by its exit code and carries no ids or min_tests. ShipLoop runs every one when release-verify
   reports done and refuses unless each passes. In an isolated run that has a completed return it runs them in a
   clean copy of the returned result (no Git history, nothing the return plan excluded, no ignored or unmanaged
   file); with none recorded yet it runs them in the work area and says so. Write paths relative to the directory
   the command starts in (the copy or the work area), put what a fresh consumer needs (an install, a build) into
   the check itself, and never write into the user's checkout by absolute path. A check only a person can make is
   an open item in `assumptions` for that person (who, where, what to report), with release-verify or handoff as
   its `consumer`, not a command. When no command applies, give an empty list with `consumer_checks_na` and the
   reason.
7. Record in `consumer_entry` how a person reaches the result (`how`: an App Launcher name and URL path, a command,
   a page) and the repository files that create that entry (`sources`).
8. Update HOME/environment.md: the target under ## Targets and runtimes, the deploy, dry-run, rollback and confirm
   commands under ## Commands, and the approvals and accounts the steps need under ## Access and accounts.
9. Cite FEATURE/release-plan.md in `evidence_refs`, and put the decisions and constraints the plan rests on in
   `summary`.
```

Shared blocks: OUTER test plans is folded into item 1 (this stage owns the release plan and consumes
system-test-author's). Test facilities is folded into item 1. The planning hand-off is folded into item 9. None
needs to print for this stage.

## 3. Checked by

- `consumer_checks` missing, or empty without `consumer_checks_na`.
- `consumer_entry` missing, or a `sources` entry that is not a file in the repository.
- `assumptions` missing, or an open item whose consumer is not a later OUTER stage.
- FEATURE/system-tests.md, FEATURE/release-plan.md or HOME/environment.md missing or empty at this close.

## 4. Guides to keep

- Release operation guidance (environment-lifecycle.md#release-operation-ownership): item 2.
- Target-native test selection (repeatable-test-suites.md#select-target-native-tests): item 1.
- Environment promotion guidance (environment-lifecycle.md#carry-the-route-into-final-delivery): item 4.
- Workspace return guidance (workspace-lifecycle.md#inner-assembly-and-final-return): item 4.
- State and data assessment (requirements-definition.md#state-and-data-change-assessment): item 2.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 1.
- Reusable test facilities (repeatable-test-suites.md#reuse-and-define-test-facilities): item 1.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Record post-release consumer checks as commands in `consumer_checks` (shape, `check`) | 6 |
| ShipLoop runs every one at release-verify, refuses unless each passes | 6 |
| Isolated run with a return: clean copy; none yet: work area and says so | 6 |
| Paths relative to the start directory; fresh-consumer needs in the check; never write the user's checkout | 6 |
| A person-only check is an open item "in the plan" (who, where, what), not a command | 6, now "in `assumptions`" with its consumer |
| No command applies: empty list with `consumer_checks_na` | 6 |
| Create an authorized release/recovery plan (identity, permission, prerequisites, impact, rollback, monitoring, checks, stop) | 2, 4, 5 |
| Every operation as a named step with exact command and authorization status | 2 |
| Deploy, access or visibility changes, browser sessions with the browser tool | 2 |
| An uncovered step is a pending approval named now | 2 |
| Record `consumer_entry` {how, sources} | 7 |
| ShipLoop refuses a plan without one and checks its sources exist | Checked by |
| Confirm command: name present and absent outputs; release-check runs it once | 5 |
| Distinguish source return, publication, deployment, promotion, consumer verification | 2 |
| A plan does not authorize or perform; a target or authority gap is blocked | 3 |
| Revalidate the integrated test plan for the release target | 1 |
| Target-native test selection for the payload and operation, incl. revised gate | 1 |
| Retain pre/post owners, selectors, outcomes, prerequisites, locations, revision, lifecycle, cost, cleanup, stop | 5 |
| Reuse applicable tests; define additional checks only for changed boundaries or gaps | 1 |
| Retain the release test plan in evidence_refs: what release-check and release-verify establish | 5, 9 (now written to FEATURE/release-plan.md and cited) |
| Release operation guidance: order schema/data/service/cutover; owner, observations, recovery | 2 |
| Unmet earlier prerequisites: outer replan with corrective work and evidence | 1 |
| Source return at release or handoff "once no Improve child is active" | 4 (the Improve clause CUT: R3 advance Improve; the return stages enforce it) |
| Use an authorized delivery route from the execution checkout if available | 4 |
| Source return before consumer checks: record the ordering conflict, incomplete disposition | 4 |
| Isolated run rollback: route SHAs and branches as plain git, no absolute paths, no other route | 4 |
| Consideration Test: plan the post-release checks | Goal, 5, 6 |
| Consideration Deploy: plan the release, rollback and post-release checks | Goal, 2, 4, 5 |
| Done-when: delivery authority recorded before acceptance | 3 (where it is written) |
| (new, R4) Where the plan and environment facts are written | 2-5 (FEATURE/release-plan.md), 8 (HOME/environment.md sections) |
| OUTER test plans: latest done records after the most recent replan; pending/repeat/blocked not authority | 1 |
| OUTER: retain locators in this result and the Improve child's notes | 9 (Improve half CUT: R3) |
| OUTER: owner creates the plan; later stage revalidates | 1 (revalidates system-test-author's), 2-5 (creates its own) |
| OUTER: recover a missing plan; never guess commands, drop coverage, deploy for a check | 1, 3 |
| OUTER: a plan is not execution evidence; material change invalidates observations | 1 (revalidate); rerun half belongs to the executing stages |
| Test facilities: reuse first, smallest missing facility, never assume a skill or MCP | 1 ("never assume" CUT here: the release steps name the tool and its authorization status in 2) |
| Test facilities: record locator, interface, readiness or gap, owner, revalidation | 1 (interface and revalidation condition folded into "locator, readiness or gap and owner"; keep both if unsure) |
| Test facilities: carry locators into item context and the Improve child's notes | CUT: no item context at an OUTER stage; R3 |
| Test facilities: planning names prerequisite work; owner builds before dependent checks | 1 (replan for an unmet prerequisite) |
| Test facilities: discovery is not execution | 3 ("a plan does not ... perform") |
| Planning hand-off: preserve decisions, constraints in summary; register files in evidence_refs | 9 |
| Planning hand-off: "At plan and step-plan ..." and "each reviewed step's criteria" | CUT: R3, other stages |
| "Improve: Every release-plan result ... starts this action's Improve child" | CUT: R3 advance Improve |

## 6. Size

- Today: DUTIES 4,089 + considerations 88 + OUTER test plans 954 + Test facilities 807 + planning hand-off 560 =
  6,498 characters.
- Proposed duty (the fenced text above): 4,727 characters, with no shared block printed (-27%).


## Tightened (pass 2)

Duty size (inline): 4,887 -> 4,552 characters (-7%). Goal: 'Plan the release without performing it: steps and rollback in `summary` and HOME/environment.md, `consumer_checks`, `consumer_entry`.'; short goal: 'plan the release'.

Text now in `DUTIES['release-plan']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. Revalidate the integrated test plan for the release target: the latest done system-test-author record after the
   most recent accepted replan, HOME/environment.md ## Harnesses and suites, the system-test result (OUTER
   test-planning handshake); pending, repeat and blocked results are not plan authority. Use Target-native test
   selection for this payload and its deploy or promotion operation, including any revised gate. Reuse applicable
   tests and facilities (Reusable test facilities); add checks only for changed boundaries or coverage gaps, and
   record each new facility's locator, interface, readiness or gap, owner and revalidation condition. An unmet
   earlier deployment or test prerequisite: report replan with corrective work and evidence (ShipLoop reruns the
   outer stages).
2. Write the release steps in `summary` and HOME/environment.md (item 8): target and candidate identity, permission,
   prerequisites, user impact, monitoring, stop conditions. Every operation the user-visible outcome needs is a
   named step with its exact command and authorization status: the deploy, each access or visibility change (for
   example assigning a permission set, activating an app or tab), each browser session a consumer check needs with
   its browser tool. A step no approval covers is a pending approval named now. Keep source return, artifact
   publication, deployment, promotion and consumer verification as separate steps. Order the remaining schema,
   data, service and cutover work with its durable execution owner, observations and recovery limits (Release
   operation guidance, State and data assessment).
3. Record each step's delivery authority in `summary`. A plan authorizes and performs no external operation; a
   required target or authority gap is blocked.
4. Write the rollback procedure in `summary` and HOME/environment.md ## Commands. Isolated run: write it for the
   source return the packet states (return route and rollback recipes come from workspace.md), as plain `git`
   commands with that route's SHAs and branch names, never this run's absolute paths, never for another route
   (Workspace return guidance). Source return happens at release or handoff, not here. Use an authorized delivery
   route from the execution checkout when available (Environment promotion guidance). If the return must precede
   the consumer checks, record the ordering conflict and keep the disposition incomplete; never claim an earlier
   check observed a future return-triggered effect.
5. Write the release test plan in `summary` and HOME/environment.md ## Harnesses and suites: pre and post check
   owners, commands or case selectors, independent expected outcomes, prerequisites, execution versus target
   locations, remote test-definition revision, setup, test and teardown, fixture isolation, sharing and cost,
   cleanup and stop conditions. State what release-check must establish before release, what release-verify
   confirms after, and which observations and cleanup each owns. Each post-release confirm command names the output
   showing the result present and the output showing it absent; release-check runs it once before the real deploy to
   prove it tells them apart.
6. Post-release consumer checks go in `consumer_checks`, shaped like test_commands (a `check` row is judged by exit
   code, no ids or min_tests). ShipLoop runs every one when release-verify reports done and refuses unless each
   passes: in an isolated run with a completed return, in a clean copy of the returned result (no Git history,
   nothing the return plan excluded, no ignored or unmanaged file); with none yet, in the work area, and says so.
   Write paths relative to the starting directory, put what a fresh consumer needs (install, build) in the check,
   and never write into the user's checkout by absolute path. A check only a person can make is an open item in
   `assumptions` (who, where, what to report) with release-verify or handoff as `consumer`, not a command. None
   applies: empty list with `consumer_checks_na` and the reason.
7. `consumer_entry`: `how` a person reaches the result (App Launcher name and URL path, command, page) and the
   repository `sources` files that create that entry.
8. Update HOME/environment.md: target under ## Targets and runtimes; deploy, dry-run, rollback and confirm commands
   under ## Commands; approvals and accounts under ## Access and accounts.
9. Cite HOME/environment.md in `evidence_refs`; the decisions and constraints the plan rests on go in `summary`.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids. Restored once: pending, repeat and blocked results are not plan authority (item 1).
