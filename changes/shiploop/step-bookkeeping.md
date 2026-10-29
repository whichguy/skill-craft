---
bump: minor
---
Each step's tests are held to what the earlier steps proved (design T section 9.1 step 3).
- A later step's base run holds only the IDs due at that step to failing. Before, an earlier step's case, which passes
  on the next step's base, was refused there as "passes on the base", and `red_na` could not name it, so a step after
  the first could not finish a test stage whose command spans steps.
- Floors add up across steps: a step's test stage runs at least an earlier step's accepted count of the command plus
  the IDs newly due at this step. A new ID in `red_na` is not added, since its test may already be in that count.
- A command whose IDs a step narrows is held to its `min_tests` only from the step at which all of them are due.
- A test the step's document stage or its review adds is registered in the result's `added_tests` (`id`, `command`),
  and every later run of that command must show it. It is never held to failing on a base.
- validate-existing's preparatory fix moves the base of the item's first step only. Before, from the second step on,
  the base run, the mutation check and red-check ran on the tree before the first step whenever the item had a
  preparatory fix.
- The packets that reconcile an item (carry-forward, system-test-author) list every step's test and document
  results, not only the last step's. Open items, these lists and the not-covered hand-off read one per-step list of
  results (`planning_revision.step_actions`).
