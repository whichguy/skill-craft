# test-spec: re-cut draft (worker B)

The owner called today's packet "far too elaborate". This draft keeps every gate-backed obligation and cuts the
rest to one line each.

## 1. Goal (R1)

Specify this item's tests: record one case per focused-command ID in `test_cases`, and write each case's entry under
`### <ID>` in FEATURE/test-spec.md. Write no test code.

## 2. Duty

1. **One case per ID.** For each ID the step plan's focused commands list, add one `test_cases` row and one
   `### <ID>` entry. Use no other ID. If a criterion needs an ID no focused command lists, report revise naming it.
2. **Entry fields.** Each entry holds: criterion and R-<n>; surface (unit, public interface, real boundary,
   rendered UI) and due phase; setup and fixture; action; oracle; RED; GREEN; teardown, or "stateless"; the command
   row that runs it; the suite that registers it, and whether it joins smoke.
3. **Oracle.** Take it from the requirement's text, never from the code. Check a golden, fixture or snapshot against
   that text first. The oracle is the expected observation, never only that a page loads. RED is how the case fails
   on the item's base. A case that already passes there is a characterisation case; say so in RED.
4. **Coverage.** Cover positive, failure and boundary behaviour. For each new or changed public entry point, add one
   rejection case per constraint it checks (missing, wrong type or shape, out of range), asserting the error type,
   the named argument and unchanged state.
5. **Isolation.** Isolate each test. Share setup only when shown safe, never mutable state. Give each case its
   failure cleanup. Name the existing harness, helper or fixture each case uses (Reusable test facilities); for a
   missing one, name the smallest facility the test stage must build.
6. **Not here.** Keep every assigned clause with its required surface and due phase.
   - A case due at a later stage (system test, release) goes in `assumptions` as an open item: the case ID,
     criterion, R-<n> and oracle in `assumption`, its `check`, `consumer` the outer stage it is due at, and its owner.
   - A criterion confirmed only by a check command or by inspection gets no case. List it with its confirming
     command under `## Not tested here` in FEATURE/test-spec.md.
   - A criterion that cannot be tested as written: report revise naming it.
7. **Test decisions.** In the summary, say which HOME/test-strategy.md decisions this item keeps, refines or
   supersedes, and why. Put their locators, the step plan's, and the requirement sections you used in
   evidence_refs, with FEATURE/test-spec.md.

## 3. Checked by

- A `test_cases` ID set that differs from the focused command IDs, in either direction.
- A case naming a criterion the step plan lacks, or a requirement with no entry in HOME/spec.md.
- An open item whose consumer is not a later outer stage.

## 4. Guides to keep

Reusable test facilities; Test-case planning guidance; Real-boundary test guidance.
Drop: Repeatable test-suite guide (step-plan placed the harness; this stage cites no harness choice).

## 5. Loop Work (shiploop_loops.WORK["test-spec"])

"Do duty items 1-6 of {run}/packets/{action}.md, one entry per case in {feature}/test-spec.md; then run the
`complete --check-only` command printed there and fix each refusal."

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| Every case cites criterion and R-<n>; oracle from requirement text, never code; check golden/fixture/snapshot first | 2, 3 |
| State which test-strategy decisions this item keeps or changes and why | 7 |
| Read the step plan's criteria and focused command IDs | 1 (the hand-offs print them) |
| Record one case per ID in `test_cases` (shape) | 1; shape is the result template's (R2) |
| "implement, test and verify quote them" | CUT: describes other stages (R3) |
| Each ID one a focused command lists; every listed ID gets a case; ShipLoop refuses both mismatches | 1; Checked by |
| Missing ID: step plan must change, report revise | 1 |
| Write each full entry under `### <ID>` | Goal, 1 |
| Entry holds criterion, R-<n>, surface, due phase, setup, action, oracle, RED, GREEN, teardown, command row | 2 |
| Oracle is the expected observation, never only that a page loads | 3 |
| RED or characterisation; test stage records it in red_na | 3 ("red_na" is the test stage's field: CUT from here, R3) |
| Cover positive, failure, boundary | 4 |
| Rejection case per constraint, error type, named argument, unchanged state | 4 |
| Isolate per test; never share mutable state | 5 |
| Plan failure cleanup | 5 |
| Say which suite registers each case and whether it joins smoke | 2 |
| Preserve every assigned clause with surface and due phase | 6 |
| Later case: open item in assumptions with ID, criterion, R-<n>, oracle, check, consumer, owner | 6 |
| "where system-test-author picks it up" | CUT: describes another stage (R3) |
| Check-command or inspection criterion: no case, listed under `## Not tested here` | 6 |
| "This file is a specification, not evidence: test stage writes and runs after implement" | Goal ("Write no test code"); the rest CUT (R3) |
| Criterion untestable as written: revise | 6 |
| Consideration Test: positive, failure, boundary before code | 4 |
| _PLANNING_HANDOFF: preserve key statements, decisions, constraints in summary and registered material | 7 (summary + evidence_refs) |
| _PLANNING_HANDOFF: "At plan and step-plan, consolidate ... sole worker directive" | CUT: another stage's text (R3) |
| _PLANNING_HANDOFF: register planning files and sources as absolute evidence_refs; unrecorded conversation is no handoff | 7 |
| TEST_FACILITY_HANDOFF: reuse before smallest new facility; never assume a skill or MCP | 5 (naming the facility); building and recording it is the test stage's item 1 |
| TEST_FACILITY_HANDOFF: record locator, interface, readiness, owner, revalidation | test stage item 1 (this stage builds nothing) |
| TEST_FACILITY_HANDOFF: carry into item context and the Improve child's notes | CUT: test-spec writes no queue context; Improve mention (R3) |
| TEST_FACILITY_HANDOFF: discovery is not execution; later test reopens the definition | test stage item 1 |
| TEST_DECISION_HANDOFF: reopen test decision and strategy with item context | 7 |
| TEST_DECISION_HANDOFF: locators and revision in evidence_refs and test notes, with step-plan locator and coding sections | 7 (coding-guidance sections CUT: test-spec selects none) |
| TEST_DECISION_HANDOFF: missing decision reassessed here; completion does not prove a harness works | CUT here: test-spec runs no harness; kept in the test stage's item 2 |

## 7. Size

- Today: duty 2,670 + planning hand-off 513 + TEST_FACILITY_HANDOFF 807 + TEST_DECISION_HANDOFF 560 +
  consideration 58 + Work 357 = 4,965 characters.
- New: 2,700 characters for goal, duty and checked-by.


## Tightened (pass 2)

Duty size (inline): 2,360 -> 1,773 characters (-25%). Goal: "Specify this item's tests: one `test_cases` row per focused-command ID, with oracle, RED and GREEN. Write no test code."; short goal: "specify this item's tests".

Text now in `DUTIES['test-spec']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
Write no test code in this stage.

1. One `test_cases` row per ID the step plan's focused commands list; no other ID. A criterion that needs an
   unlisted ID: report revise naming it.
2. Each row (Test-case planning guidance): `criterion`, `requirement` (R-<n>), `oracle`, `red`, `green`. Put surface
   (unit, public interface, real boundary, rendered UI; Real-boundary test guidance) and due phase, setup and
   fixture, action, teardown (or "stateless"), command row, registering suite and smoke membership in those fields
   or the summary.
3. Oracle from the requirement's text, never the code; check any golden, fixture or snapshot against it. It is an
   observation, never only that a page loads. RED: how it fails on the item's base, or "characterisation" if it
   already passes.
4. Cover positive, failure and boundary. Each new or changed public entry point: one rejection case per constraint
   (missing, wrong type or shape, out of range), asserting the error type, the argument named and unchanged state.
5. Isolate each test: no shared mutable state, each with its failure cleanup. Name the harness, helper or fixture
   it uses (Reusable test facilities); for a missing one, the smallest facility the test stage must build.
6. Due at a later stage (system test, release): an `assumptions` open item (case ID, criterion, R-<n> and oracle in
   `assumption`; `check`; `consumer` = that outer stage; owner). Confirmed only by a check command or inspection: no
   case; list it with its command in the summary. Untestable as written: report revise naming it.
7. Summary: which harness and suite decisions in HOME/environment.md this item keeps, refines or supersedes, and
   why. evidence_refs: their locators, the step plan's, the requirement sections used.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
