---
bump: patch
---
The procedure walk validates a derived expected result instead of only asking that it be replayable. It is printed in
the planning review focus, in the spec and test-strategy duties and in test-spec's duty 4.
- It names the spec rule that permits each action that decides the outcome, and recomputes the expected result from
  the checked walk.
- A helper that applies the actions without checking that each is permitted, or the product under test alone, does
  not count as a check.
- The review focus covers cases the review itself adds or changes. The review records the case, the method and the
  recomputed result, or marks it `NOT-REPLAYED: <reason>`, which leaves it open.
