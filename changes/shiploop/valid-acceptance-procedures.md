---
bump: minor
---
Acceptance procedures are checked where they are written: a procedure whose actions are named but cannot all happen is
found and revised in planning, not discovered at release.
- The planning review focus, which the spec and test-strategy duties hold and every planning review (spec,
  test-strategy, plan, step-plan, test-spec, system-test-author, release-plan) prints, gains one condition: walk an
  ordered procedure from its stated start (can the actor reach that start under recorded authority, can each action
  occur in the state the preceding actions leave, can the chosen observer see the expected result?), record an
  unreachable start as an open prerequisite, revise an invalid action or oracle, claim no execution from a plan, and
  treat an observation made before its setup changed as stale.
- test-spec applies it to its own cases (new duty item 4; the later items are renumbered 5-8), and its loop gains the
  exit condition that each case's procedure can happen as written from its stated start, or its unreachable start is an
  open item. A forbidden action stays its own failure case. A procedure another record holds is cited by its locator in
  the case's `oracle` or the open item's `check`, so implement, its Improve, test, verify, system-test-author and the
  open item's consumer use that one procedure.
- test-strategy writes a consumer interface case with its start (actor, entry route, initial state) and ordered
  actions under `## Real-boundary checks`, with an ID later stages cite.
- The test-case planning guide gains a Procedure validity section: the six facts a procedure states (start, actions,
  oracle, observation, ownership, evidence), validity kept apart from execution, and three faults to look for.
- Unchanged: a test case keeps exactly its six fields (a `procedure` key is still refused), and an opt-in consumer
  check stays outside the focused command set.
