# test: re-cut draft (worker B)

## 1. Goal (R1)

Write a test for every case in FEATURE/test-spec.md, titled with its ID, and make every recorded command pass in
WORKTREE; record `red_na`, `retired_tests` and `lint_waivers` in the result and each test change's reason in
RUN/notes/<action>.md.

## 2. Duty

1. **Write the cases.** Write each FEATURE/test-spec.md case as a test titled with its ID as its own word, in the
   suite and command its entry names, asserting the spec's oracle, never the code's behaviour. Reuse the existing
   harness, helpers and fixtures first (Reusable test facilities); never assume a named skill or MCP is available
   or authorized. Build a missing facility within this item and validate it before the tests that use it. Record
   each new facility in HOME/test-strategy.md ## Harnesses and suites with its locator, interface, readiness, owner
   and revalidation condition. Do not write a case due at a later stage.
2. **Test decisions.** Reopen the item's test decision and HOME/test-strategy.md. Record a harness, boundary or
   suite decision the implementation changed in HOME/test-strategy.md ## Harnesses and suites. In the summary, say
   which decisions you retain, refine or supersede and why; put their locators and the step plan's in evidence_refs.
   A recorded completion does not prove a harness, fixture or target still works.
3. **Gaps.** Read the implement results' `not_covered`. A behaviour or rejection case the spec lacks becomes a
   sub-case of the closest `### <ID>` entry in FEATURE/test-spec.md, with its oracle from the spec, and its test is
   titled `<ID> (<letter>)`. When no entry fits, report revise. Each new or changed public entry point gets its
   rejection cases. Test a new error path or debug output, on and off, with safe diagnostic context.
4. **Run and fix.** After each change, run every recorded command, the red-check command and the lint command. Find
   each failure's cause with one small observation (product defect, invalid test, environment) and fix the product
   code. Change a test, fixture, golden file or threshold only for an independent reason, written in
   RUN/notes/<action>.md. Never weaken, delete or skip a test to get green. A repeated unchanged failure is not
   progress: change the approach.
5. **End states.** Each case ends as one of:
   - validated: run, and the observation matches the oracle;
   - validated another way: the first method could not observe it, so another method ran and passed, still titled
     with the ID; the summary says what changed and why;
   - unachievable: a named reason and the requirement it leaves unverified; report revise.

   A case written but not run is not an end state.
6. **Result fields.**
   - `red_na`: each new test that passes on the item base without this change, `[{"id", "reason"}]`.
   - `retired_tests`: each test this item deliberately retires, `[{"id", "reason": "<the R-<n> or AD-<n> that
     retires it>"}]`. Any other drop below a command's floor is refused.
   - `lint_waivers`: each lint finding that must stay, `{"id": "<printed ID>", "reason": "<why>"}`.
7. **Proof limits.** A passing command proves only the cases it runs. A smoke or subset run never stands for a
   recorded command. A local pass does not replace a required remote or real-boundary check. Keep probes and
   experiments in RUN/scratch. Never install, download or fetch a tool or dependency. Never commit or push.
8. **Revise** (name the case or command, why, the requirement it leaves unverified, and every required command that
   could not run) when:
   - a failure is proven unachievable: it contradicts the spec or another requirement, needs an absent tool, access
     or authority, or would exceed the item;
   - a recorded command is wrong or cannot run here;
   - an existing suite the changed paths now affect must join the regression command;
   - the step plan recorded no test command for code this item changes.

   Report blocked, with blocked_by, only when the user, an access grant or an outside dependency must unblock it.

## 3. Checked by

- The lint gate refuses done once after applying an auto-fix, and while a new finding on a changed line has no
  waiver.
- ShipLoop mutates a sample of the item's changed product lines and refuses done when the focused tests catch none.
- A `red_na` or `retired_tests` entry without an ID and a reason.

## 4. Guides to keep

Reusable test facilities; Repeatable test-suite guide; Target-native test selection; Test-case planning guidance;
Real-boundary test guidance.
Drop: House-style guidance (test code follows Code craft rule 1, printed whole), Iteration and verification guidance
(not cited).

## 5. Loop Work (shiploop_loops.WORK["test"])

"Do duty items 1-4 of {run}/packets/{action}.md until every case is a passing test the focused command runs; write
each test change's independent reason in {run}/notes/{action}.md."

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| Read the implement results: an uncovered behaviour is a test-spec gap | 3 |
| Change a test/fixture/golden/threshold only for an independent reason, recorded in notes; never weaken/delete/skip | 4 |
| Repeated unchanged failure is not progress | 4 |
| Reuse existing harness, helpers, fixtures; record new one in test-strategy ## Harnesses and suites | 1 |
| Record a changed test decision (harness, boundary, suite) there too | 2 |
| Each new or changed entry point gets rejection cases | 3 |
| Gap: sub-case of closest entry, oracle from spec, titled `<ID> (<letter>)`; new entry needs a command, so revise | 3 |
| Test new error path or debug output on and off with safe context | 3 |
| Adding an existing suite to regression changes a recorded command: blocked + revise | 8 |
| Probes in Scratch, never in suite | 7 |
| Passing command proves only its cases; smoke/subset never stands for a recorded command; local not remote | 7 |
| Never install/download/fetch; never commit or push | 7 |
| Every case ends as passing test, another method (titled, says what changed), or unachievable (revise); written-not-run is not an end | 5 |
| Case due later is an open item, not written here; system-test-author picks it up | 1 ("Do not write a case due at a later stage"); the pickup CUT (R3) |
| Characterisation test: red_na shape | 6 |
| retired_tests shape; other drop below floor refused | 6 |
| lint_waivers shape | 6 |
| After a refusal at done: fix, restart loop, resubmit | Shared "What to execute" section |
| Revise when unachievable / recorded command wrong or cannot run; name case, why, requirement, commands not run | 8 |
| No test command recorded for code: revise | 8 |
| Blocked only for user, access, outside dependency | 8 |
| Consideration Test (case end states) | 5 |
| Consideration Test: "report blocked with blocked_by access only when nothing else can proceed" (case_end_states) | 8 (blocked line) |
| Consideration Tools: lint gate runs before ShipLoop's test runs | Checked by |
| TEST_FACILITY_HANDOFF: read skill and MCP references; reuse before smallest new; never assume available | 1 |
| TEST_FACILITY_HANDOFF: record locator, interface, readiness, owner, revalidation in evidence_refs and test docs | 1 (HOME/test-strategy.md; the locator also lands in evidence_refs through 2) |
| TEST_FACILITY_HANDOFF: carry locators into item context and Improve notes | CUT: test writes no queue context; Improve mention (R3) |
| TEST_FACILITY_HANDOFF: owning stage builds and validates before dependent checks, within scope | 1 |
| TEST_FACILITY_HANDOFF: readiness is not execution; later test reopens definition | 1 (a facility is "validated before the tests that use it"); "later test reopens" CUT here, kept in the shared block for later stages |
| TEST_DECISION_HANDOFF: reopen test decision and strategy | 2 |
| TEST_DECISION_HANDOFF: locators, revision, step-plan locator, coding sections; retained/refined/superseded | 2 (coding-guidance sections CUT: the test stage selects none) |
| TEST_DECISION_HANDOFF: missing decision reassessed here; completion does not prove harness works | 2 ("reassessed" folded into "Reopen"; completion line kept) |
| Loop Work: write/fix tests titled with ID, registered, spec oracle not code | 1 |
| Loop Work: run every command, red-check, lint | 4 |
| Loop Work: one small observation, fix product, test change only for recorded reason | 4 |

## 7. Size

- Today: duty 3,516 + TEST_FACILITY_HANDOFF 807 + TEST_DECISION_HANDOFF 560 + considerations 740 + Work 556 =
  6,179 characters.
- New: 4,350 characters.


## Tightened (pass 2)

Duty size (inline): 3,977 -> 3,725 characters (-7%). Goal: 'Write a test per quoted case, titled with its ID; make every recorded command pass in WORKTREE; fields go in the result.'; short goal: "write and run this item's tests".

Text now in `DUTIES['test']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. **Write the cases.** Each quoted test case becomes a test titled with its ID as its own word, in the suite and
   command its case names (Repeatable test-suite guide, Target-native test selection), asserting the spec's oracle,
   never the code's behaviour. Reuse existing harness, helpers and fixtures first (Reusable test facilities); never
   assume a named skill or MCP is available. Build a missing facility within this item and validate it before the
   tests that use it; record it in HOME/environment.md ## Harnesses and suites (locator, interface, readiness,
   owner, revalidation condition). Write no case due at a later stage.
2. **Test decisions.** Reopen the item's test decision and HOME/environment.md's harness and suite decisions. Record a
   harness or suite decision the implementation changed in ## Harnesses and suites, and a real-boundary decision in
   HOME/architecture.md ## Real-boundary checks. Summary: which decisions you retain, refine or supersede and why;
   locators and the step plan's in evidence_refs. A recorded completion does not prove a harness, fixture or target
   still works.
3. **Gaps.** Read the implement results' `not_covered`. A behaviour or rejection case the spec lacks becomes a
   sub-case of the closest quoted case with its oracle from the spec (Test-case planning guidance), titled
   `<ID> (<letter>)`; none fits: report revise. Each new or changed public entry point gets rejection cases. Test a
   new error path or debug output, on and off, with safe diagnostic context.
4. **Run and fix.** After each change run every recorded command, the red-check command and the lint command. Find
   each failure's cause with one small observation (product defect, invalid test, environment) and fix the product.
   Change a test, fixture, golden file or threshold only for an independent reason written in RUN/notes/<action>.md.
   Never weaken, delete or skip a test to get green. A repeated unchanged failure is not progress: change approach.
5. **End states.** Each case ends as:
   - validated: run, and the observation matches the oracle;
   - validated another way: the first method could not observe it, another ran and passed, still titled with the ID;
     the summary says what changed and why;
   - unachievable: a named reason and the requirement left unverified; report revise.
   A case written but not run has no end state.
6. **Result fields.** `red_na`: each new test passing on the item base without this change, `[{"id", "reason"}]`.
   `retired_tests`: each test this item deliberately retires, `[{"id", "reason": "<the R-<n> or AD-<n> that retires
   it>"}]` (any other drop below a command's floor is refused). `lint_waivers`: `{"id": "<printed ID>", "reason":
   "<why>"}` per lint finding that must stay.
7. **Proof limits.** A passing command proves only the cases it runs; a smoke or subset run never stands for a
   recorded command; a local pass does not replace a required remote or real-boundary check (Real-boundary test
   guidance). Probes and experiments go in RUN/scratch. Install, download or fetch nothing. Never commit or push.
8. **Revise** (naming the case or command, why, the requirement left unverified, and every required command that
   could not run) when: a failure is proven unachievable (contradicts the spec or another requirement, needs an
   absent tool, access or authority, or would exceed the item); a recorded command is wrong or cannot run here; an
   existing suite the changed paths now affect must join the regression command; the step plan recorded no test
   command for code this item changes. Report blocked, with blocked_by, only when the user, an access grant or an
   outside dependency must unblock it.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
