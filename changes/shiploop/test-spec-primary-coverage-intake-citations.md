---
bump: minor
---
Two judgement stages now end on a script check, not only on the model's word.
- **Test-spec covers every primary requirement (TS1).** At the last work item's test-spec, ShipLoop refuses a
  primary requirement (spec `primary`) that no item's current test-spec case names. A requirement about the tests
  themselves ("the tests run with node --test") goes in the new `suite_requirements` field instead, as
  `{"requirement": "R-<n>", "command": "<a recorded test command>"}`: the suite's recorded run observes it.
  - A row is refused when its requirement has no current spec entry, or when no step plan records its command.
  - A run whose step plans record no test command (documentation only) is not asked.
  - The last item's test-spec packet lists each primary requirement with its cases so far.
  - The check runs after the hand-off gate, so a malformed case still gets its shape refusal first.
- **Intake cites every request sentence (IN1).** A done intake whose summary leaves a sentence `S<n>` of
  `RUN/request.md` uncited is refused, naming each one. Until now it got a counted notice that never refused
  (`ShipLoop request notice`), and that notice is gone.
