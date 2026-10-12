# step-plan: re-cut draft (worker B)

## 1. Goal (R1)

Plan this item's change: record `criteria`, `steps`, `test_commands`, `expectations`, `paths` and `follows` in the
result, and write the item's plan note under its heading in FEATURE/plan.md.

## 2. Duty

Change no product file in this stage.

1. **Recheck the item.** Reopen the item's `context` and its section of FEATURE/plan.md, and recheck each condition
   they state. If the plan no longer requires the item, report blocked (blocked_by user, `awaiting` an answer: drop
   or keep the item) and cite the plan section that superseded it. Never skip the item or repair the queue here.
   Keep the change inside the item: available APIs and other parts of the request do not widen it. A prerequisite
   outside the item gets its supplier route in the summary and the blocked outcome.
2. **Test decisions.** Reopen the item's test decision and HOME/test-strategy.md. In the summary, say which
   decisions you retain, refine or supersede and why; put their locators in evidence_refs. Revalidate the harness,
   suite and browser tools for the changed surfaces (Repeatable test-suite guide), and reuse supported choices or
   record a justified revision in the plan note. A remote-resident case needs its framework and an authorized setup,
   invocation, result retrieval and teardown route. Reuse an existing test facility before defining the smallest
   missing one (Reusable test facilities); record its locator and readiness gap in the plan note.
3. **`criteria`** (`[{"id": "C1", "text": "..."}]`). Write each as `<condition>. Confirm by: <command, observation
   or inspection>; pass when <expected result>`. Say whether it must be exercised or inspection suffices, and name
   the R-<n> it serves.
   - A docs or coverage criterion gets a command check, such as a search for the required terms.
   - A condition no command can confirm is not a criterion. List it in the summary as an open item (who does what,
     what they report back) and write `Confirm by: unconfirmable here: <what would confirm it>` in the plan note.
   - When the item adds or changes a public entry point, add a criterion that each one checks its arguments and
     carries a contract docstring (Code craft 2-3), confirmed by its rejection tests and by inspecting the diff.
4. **`steps`**: every implementation step, in order (one is fine). ShipLoop issues one implement packet per step.
   - Size each as one behaviour-level change that a named check proves. Split a step that holds two behaviours each
     confirmable alone, crosses a module or layer boundary (the interface first, then each side), needs "and"
     between two outcomes, or is too large to review in one pass. Merge a step no check can confirm alone (half a
     rename, unused scaffolding) into the step it serves. A single bug fix or mechanical rename is one step.
   - Tests are not a step: the test stage writes them after the last implement step. A step that only changes test
     files is refused unless the whole item is tests.
   - Each step declares `deps` (earlier step IDs it truly needs, or []; list order is not a dependency), the
     `criteria` it satisfies and the `paths` it changes (inside the item's `paths`). Every criterion is satisfied
     by some step.
   - `skills`: reread the host's skills and the repository's skill index now (an earlier item may have added one).
     List `{"name", "why", "locator"}` for each skill with a concrete use in the step, or []. Prefer a
     repository-local skill reused unchanged. `locator`, when given, is the path of an existing SKILL.md or card.
5. **`test_commands`** (`[{"command", "suite", "ids", "criteria"}]`), each run from the repository root. The test
   and verify stages run exactly these.
   - focused: this item's cases, with the IDs they will carry and a runner flag that prints test names (Jest
     `--verbose`, pytest `-v`, `node --test` with its default spec or tap reporter; never dot or junit).
     ID_WORD_RULE. Add `min_tests` where a command must run at least that many. ShipLoop refuses a run that
     executed no test, so check the filter matches.
   - regression: the retained suites the changed paths affect.
   - check: the lint, type and build commands HOME/environment.md records for these files, judged by exit code, with
     no `ids` or `min_tests`. With none, give `check_na` and the reason; with no command at all, `test_commands_na`.
   - Every criterion is named in some command's `criteria`, and a command names only listed criteria. A list too
     large for the test loop's contract is refused: shorten IDs, drop duplicates or split the item.
6. **`expectations`**: each fact the steps build on, as `{"id", "state", "statement", "steps", "paths", "check",
   "from"}`. ShipLoop runs every check on the unchanged item base at validate-existing.
   - Every existing path a step changes or relies on gets `works` (it works today) or `broken` (the request says it
     is broken). Every new path gets `absent` (its place is free).
   - `check` is one read-only command, run from the repository root, that exits 0 while the state holds. For
     `broken`, the reported failure still reproduces: `! npm test -- -t TC-3` or `node cli.js 2>&1 | grep -q
     'TypeError'`.
   - An open plan assumption this item consumes becomes an expectation whose `from` names it.
7. **`paths`**: every file the item will change, as repository-relative files or globs, including the test files
   the test stage will write. The item commit takes these files, the changed documentation and HOME/. An item with
   no test command and only non-code paths skips the test stage; one whose diff touches no code or test path skips
   document.
8. **`follows`**: each R-<n> and AD-<n> this item follows. Each must exist in HOME/spec.md or HOME/architecture.md.
9. **Plan note**, under the item's heading in FEATURE/plan.md. Write:
   - the outcome and the invariants kept; the contracts and responsibilities that change;
   - the target files, interfaces and conventions, matched to the house style (House-style guidance);
   - each step's failure cases and the diagnostics and errors it must produce;
   - the documentation to change; the integration impact and release prerequisites;
   - the readiness, completion and revalidation conditions;
   - the Coding decision guide's selection: the actual runtime and version, artifact and boundary, and links to only
     the matching sections;
   - when code or stored data is added or moved: reopen the plan's Namespace and data map and each touched
     environment's current tree. Name each file, module and public symbol with its environment, home namespace,
     visibility and collision check (an import or load test, a deploy validation, or a name search). Name each
     stored field, key, table or payload with its owning environment, migration (unneeded, an earlier step, this
     step, or a deploy obligation) and round-trip check. Give the reason for a changed placement or schema
     (Namespace and placement guidance, Schema and storage guidance);
   - each pinned value a check replays (fixed dice, seed data), labelled a source-check fixture, separate from the
     runtime control. Confirm an external oracle (golden file, fixture, snapshot) agrees with the task;
   - when interactions, UI or service state change: a Design basis paragraph or exact section links. Recheck the
     Interaction design guide's matching subsections (incoming and outgoing events, connection lifecycle, UI
     planning) and, for services, the Service discovery guidance; do not copy the prior plan. Give the baseline and
     delta; the actors, events, connections and state owner; the planned recovery checks; for UI, the component,
     interaction and skin premises, the design guidance identity and version or digest (or the named fallback), and
     the rich interactions planned. A human-facing UI defaults to an ambitious, highly interactive design: name the
     rich interactions (direct manipulation, inline editing, live preview, keyboard paths, animated transitions)
     and any scaled back, with its user, target or accessibility reason; and the locators of its sources and checks.

   The plan note gathers upstream material as supporting references. Each step's task and criteria stay its only
   directive.
10. **Knowledge.** Write a structural choice HOME/architecture.md lacks as the next AD-<n> under ## Decisions and
    cite it in the step. Add a newly working command to HOME/environment.md ## Commands. Keep every R-<n> and AD-<n>.
    Write nothing else in HOME/.
11. **Execution graph.** Ask-agent: give each change that needs no other its own step with `deps` [] and join them
    in a later step that needs both, so the parallel chain can run them together (serial only on an explicit user
    or host limit). For dependency-independent steps, write the graph now, even behind an initial serial prefix:
    direct dependencies, readiness and completion criteria, shared-resource exclusions and the integration node.
    Put its path and content digest in the plan note and evidence_refs. Use the Parallel-chain guide for late
    creation or revision; planning never starts the dispatcher.
    Inline: record no execution graph; the run issues the steps one at a time.
12. **evidence_refs**: absolute paths of the FEATURE/plan.md section, every planning file you wrote, and the
    requirement sections and test locators you used.

Shared blocks still printed after the duty: the Backchain guidance (ask-agent) or INLINE_BACKCHAIN_AUDIT (inline),
unchanged.

## 3. Checked by

- `follows` missing, or an ID with no entry in HOME/spec.md or HOME/architecture.md.
- A step skill `locator` that does not exist.
- A HOME/ change that loses an R-<n> or AD-<n>.
- `steps`, `criteria`, `test_commands` and `paths` that do not fit (item 4-7 rules), and `expectations` without a
  state, a check or a known step.

## 4. Guides to keep

Repeatable test-suite guide; Reusable test facilities; Coding decision guide; House-style guidance; Namespace and
placement guidance; Schema and storage guidance; Interaction design guide; Service discovery guidance; Parallel-chain
guide (ask-agent only); Backchain planning guide.

Drop (never cited by the new text): Cold-start evidence guidance, Current-system baseline guide, Git-history
investigation guide, Repository-local skill guidance, Implementation constitution, Decision carry-forward guidance,
State and data assessment, UI planning ownership when applicable. **Unsure:** State and data assessment is also read
by `_improve_prompt` (the `assessment` block keys on the label). Dropping it from step-plan removes that Improve
paragraph too. Keep the label if that review paragraph must stay.

## 5. Loop Work (shiploop_loops.WORK["step-plan"])

Today's Work already points at the packet; keep it, with "duty items 1-12" named:
"Do duty items 1-12 of {run}/packets/{action}.md, writing the result at {run}/inbox/{action}.md and this item's
section of {feature}/plan.md; then run the `complete --check-only` command printed there and fix each refusal."

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences: work inside loop, do not edit contract, satisfied only when shown after last edit, refused done: fix, restart, resubmit) | Shared "What to execute" section (once for every inner stage) |
| Change no product file | Duty head |
| 1. Reopen context and plan section, recheck conditions | 1 |
| Plan no longer requires item: blocked, awaiting drop/keep, cite section | 1 |
| Never skip or repair the queue here | 1 |
| Keep change inside item; APIs/request do not widen | 1 |
| Outside prerequisite: supplier route + blocked, not future bullet | 1 ("not a future bullet" folded into "in the summary and the blocked outcome") |
| Reopen test decision and test strategy | 2 |
| Keep prior decision locators and revision in evidence_refs; retained/refined/superseded | 2 |
| 2. criteria shape | 3 |
| Condition. Confirm by ... pass when | 3 |
| Exercised vs inspection; trace to R-<n> | 3 |
| Docs/coverage criterion gets a command check | 3 |
| Unconfirmable: open item + plan note marker | 3 |
| Public entry point criterion (Code craft 2-3) | 3 |
| 3. steps, in order, one is fine; one packet per step | 4 |
| Size rules (split, merge, single fix one step) | 4 |
| Tests are not a step; test-only step refused | 4 |
| deps, criteria, paths; every criterion satisfied | 4 |
| skills: reread index, list, prefer local, locator rule | 4 |
| "The implement packet prints these" | CUT: describes the implement packet (R3) |
| 4. test_commands shape, from repo root; test and verify run exactly | 5 |
| ShipLoop refuses a run that executed no test (filter matching nothing exits 0) | 5 (shortened) |
| focused: IDs and name-printing flag; never dot/junit; ID_WORD_RULE | 5 |
| min_tests | 5 |
| regression | 5 |
| check: lint/type/build, exit code, no ids; check_na; test_commands_na | 5 |
| Every criterion in some command; command names only listed criteria | 5 |
| Too large for test loop contract: shorten/drop/split | 5 |
| Revalidate testing systems and browser tools; place harness and suite (Repeatable test-suite guide) | 2 |
| Reuse or justified revision | 2 |
| Remote-resident case: framework + setup/invocation/retrieval/teardown route | 2 |
| Reuse test facilities before smallest new one (guide) | 2 |
| Carry locator and readiness gap into item context and the Improve child's context/notes | 2: "record ... in the plan note". **Changed home**: step-plan cannot write the queue's `context` (only plan and carry-forward replace work_items); the Improve mention is cut (R3) |
| 5. expectations: each fact, not a health check; shape | 6 |
| works/broken/absent rules | 6 |
| check: read-only, exits 0; broken example | 6 |
| Open plan assumption becomes expectation with from | 6 |
| ShipLoop runs every check at validate-existing | 6 |
| 6. paths incl. test files | 7 |
| Item commit takes paths, docs, HOME/ | 7 |
| No test command + non-code: skips test; no code/test path: skips document | 7 |
| 7. Plan note under item heading | 9 |
| outcome, invariants; contracts; failure cases and diagnostics; docs; integration and release prerequisites; readiness/completion/revalidation | 9 |
| Coding decision guide: runtime, version, artifact, boundary; link matching sections | 9 |
| Namespace and data map; name symbols with environment, namespace, visibility, collision check; stored data with owner, migration, round trip; reason for change (guides) | 9 |
| Source-check fixture label; external oracle agrees | 9 |
| Design basis paragraph: recheck guide subsections and Service discovery; baseline/delta; actors/events/connections/state owner; recovery checks; UI premises, design identity, rich interactions; ambitious UI default; locators | 9 |
| 8. Write structural choice as AD-<n>, cite it | 10 |
| Newly working command in environment.md | 10 |
| Keep every R-<n> and AD-<n> | 10 |
| Write only the knowledge home; do not commit it yourself | 10 ("Write nothing else in HOME/"); "do not commit" moves to the shared locations line (ShipLoop commits HOME/ on accept, already printed once) |
| 9. evidence_refs: plan section, planning files, requirement sections, test locators | 12 |
| Unrecorded conversation is not a planning handoff | CUT: restates the evidence_refs obligation in 12 |
| Consolidate upstream material as supporting references; step criteria sole directive | 9 (closing paragraph) |
| _STEP_PLAN_GRAPH (independent steps, deps [], join; serial only on limit; graph contents; path+digest in notes and evidence_refs; Parallel-chain guide; never start dispatcher) | 11 (ask-agent) |
| _STEP_PLAN_INLINE | 11 (inline) |
| Consideration Develop: target files, interfaces, conventions; house-style match contract | 9 |
| Consideration Test: record test commands; test and verify run them | 5 |
| Consideration Deploy: integration impact, release prerequisite | 9 |
| Consideration Tools: ShipLoop records lint base; name linters, type checks, builds | 5 (check commands); "ShipLoop records the lint base" CUT: a ShipLoop action with no duty |
| TEST_FACILITY_HANDOFF / TEST_DECISION_HANDOFF | Already skipped for step-plan; their content is in 2 |
| Result template field `follows` (no duty sentence today) | 8: **added**, today's duty never told the producer to fill it although the gate refuses it |

## 7. Size

- Today: duty 10,385 (ask-agent) + considerations 352 + Work 296 = 11,033 characters.
- New: 9,900 characters for goal, duty and checked-by (both graph variants included; inline prints about 9,300).
  The step-plan duty carries most of the gate's obligations, so it stays the longest inner duty.


## Tightened (pass 2)

Duty size (inline): 8,791 -> 8,078 characters (-9%). Goal: "Plan this item's change: `criteria`, `steps`, `test_commands`; `expectations`, `paths`, `follows` in the result."; short goal: "plan this item's steps".

Text now in `DUTIES['step-plan']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
Change no product file in this stage.

1. **Recheck the item.** Reopen its `context` and recheck each condition. If the plan no longer requires it, report
   blocked (blocked_by user, `awaiting` an answer: drop or keep) citing the superseding result; never skip the item
   or repair the queue here. Keep the change inside the item: available APIs and other parts of the request do not
   widen it. A prerequisite outside the item gets its supplier route in the summary and the blocked outcome.
2. **Test decisions.** Reopen the item's test decision and HOME/environment.md's harness and suite decisions. In the
   summary say which you retain, refine or supersede and why; locators in evidence_refs. Revalidate harness, suite
   and browser tools for the changed surfaces (Repeatable test-suite guide); reuse supported choices or record a
   justified revision. A remote-resident case needs its framework and an authorized setup, invocation, result
   retrieval and teardown route. Reuse an existing facility before the smallest missing one (Reusable test
   facilities); record its locator and readiness gap in the summary.
3. **`criteria`** (`[{"id": "C1", "text": "..."}]`). Each: `<condition>. Confirm by: <command, observation or
   inspection>; pass when <expected result>`; say whether it must be exercised or inspection suffices, and name the
   R-<n> served.
   - A docs or coverage criterion gets a command check (a search for the required terms).
   - A condition no command can confirm is not a criterion: list it in the summary as an open item (who does what,
     what they report back) with `Confirm by: unconfirmable here — <what would confirm it>`.
   - A new or changed public entry point: add a criterion that it checks its arguments and carries a contract
     docstring (Code craft 2-3), confirmed by its rejection tests and by inspecting the diff.
4. **`steps`**: every implementation step in order (one is fine); ShipLoop issues one implement packet per step.
   - Size each as one behaviour-level change a named check proves. Split a step with two separately confirmable
     behaviours, one crossing a module or layer boundary (interface first, then each side), joining two outcomes with
     "and", or too large for one review. Merge a step no check confirms alone (half a rename, unused scaffolding)
     into the step it serves. A single bug fix or mechanical rename is one step.
   - Tests are not a step (the test stage writes them after the last implement step); a step changing only test
     files is refused unless the whole item is tests.
   - Each step declares `deps` (earlier step IDs it truly needs, else []; list order is no dependency), the
     `criteria` it satisfies and the `paths` it changes (inside the item's `paths`). Every criterion is satisfied by
     some step.
   - `skills`: reread the host's skills and the repository's skill index (an earlier item may have added one). List
     `{"name", "why", "locator"}` for each with a concrete use in the step, else []. Prefer a repository-local skill
     reused unchanged. `locator`, when given, is an existing SKILL.md or card path.
5. **`test_commands`** (`[{"command", "suite", "ids", "criteria"}]`), run from the repository root; the test and
   verify stages run exactly these.
   - focused: this item's cases with the IDs they carry and a runner flag that prints test names (Jest `--verbose`,
     pytest `-v`, `node --test` default spec or tap reporter; never dot or junit). A listed ID counts only as its own word in a test's printed name (for example, a test titled `TC-4a` does not show `TC-4`: title it `TC-4 (a)`). `min_tests`
     where a command must run at least that many. ShipLoop refuses a run that executed no test, so check the filter.
   - regression: the retained suites the changed paths affect.
   - check: the lint, type and build commands HOME/environment.md records for these files, judged by exit code, no
     `ids` or `min_tests`. None: `check_na` with the reason; no command at all: `test_commands_na`.
   - Every criterion is named in some command's `criteria`, and a command names only listed criteria. A list too
     large for the loop contract is refused: shorten IDs, drop duplicates or split the item.
6. **`expectations`**: each fact the steps build on, `{"id", "state", "statement", "steps", "paths", "check",
   "from"}`; ShipLoop runs every check on the unchanged item base at validate-existing.
   - Every existing path a step changes or relies on is `works` or `broken` (the request says it is broken); every
     new path is `absent` (its place is free).
   - `check`: one read-only command from the repository root that exits 0 while the state holds. For `broken`, the
     reported failure still reproduces: `! npm test -- -t TC-3` or `node cli.js 2>&1 | grep -q 'TypeError'`.
   - An open plan assumption this item consumes becomes an expectation whose `from` names it.
7. **`paths`**: every file the item changes (repository-relative files or globs), including the test files the test
   stage writes. The item commit takes these, the changed documentation and HOME/. No test command and only non-code
   paths skips the test stage; a diff touching no code or test path skips document.
8. **`follows`**: each R-<n> and AD-<n> followed; each must exist in HOME/spec.md or HOME/architecture.md.
9. **Plan record** in the item's `context` or the summary:
   - outcome and invariants kept; contracts and responsibilities that change;
   - target files, interfaces and conventions, matched to the house style (House-style guidance);
   - each step's failure cases and the diagnostics and errors it must produce;
   - documentation to change; integration impact and release prerequisites; readiness, completion and revalidation
     conditions;
   - the Coding decision guide's selection: runtime and version, artifact and boundary, links to only the matching
     sections;
   - code or stored data added or moved: reopen the Namespace and data map in HOME/architecture.md ## Structure and
     each touched environment's tree. Per file, module and public symbol: environment, home namespace, visibility,
     collision check (import or load test, deploy validation, or name search). Per stored field, key, table or
     payload: owning environment, migration (unneeded, earlier step, this step, deploy obligation), round-trip
     check. Reason for a changed placement or schema (Namespace and placement guidance, Schema and storage guidance,
     State and data assessment);
   - each pinned value a check replays (fixed dice, seed data), labelled a source-check fixture apart from the runtime
     control; confirm an external oracle (golden file, fixture, snapshot) agrees with the task;
   - interactions, UI or service state changing: a Design basis paragraph or exact section links, rechecking the
     Interaction design guide's matching subsections and, for services, Service discovery guidance; copy no prior
     plan. Give baseline and delta; actors, events, connections and state owner; planned recovery checks; for UI the
     component, interaction and skin premises, design guidance identity and version or digest (or named fallback),
     and the rich interactions planned (a human-facing UI defaults to ambitious and highly interactive: direct
     manipulation, inline editing, live preview, keyboard paths, animated transitions; give the reason for any
     scaled back); the UI decisions this step owns (UI planning ownership guide); locators of sources and checks.
   This record is supporting reference; each step's task and criteria stay its only directive.
10. **Knowledge.** A structural choice HOME/architecture.md lacks: next AD-<n> under ## Decisions, cited in the
    step. A newly working command: HOME/environment.md ## Commands. Keep every R-<n> and AD-<n>; write nothing else
    in HOME/.
11. **Execution graph.** Record none: an inline run issues the steps one at a time.
12. **evidence_refs**: absolute paths of every planning file written, and the requirement sections and test locators
    used.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids. Defect fix (coordinator): the unconfirmable-condition clause no longer puts `Confirm by: unconfirmable here` in a criterion; it lists an open item in the summary with that marker. UI planning ownership guide cited in the Design basis item and added to STAGE_REFERENCES.
