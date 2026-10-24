---
bump: minor
---
- **An end-of-work code fix names its regression test:** at the end-of-work review (carry-forward), improve-commit
  refuses a commit that changes code, not only tests, without a `Regression test:` line naming the test in the same
  commit that fails without the fix; ShipLoop checks that a test file in the commit holds it. `Regression test: none:
  <why>` is the other exit. Step and planning reviews owe no line. The Improve handoff states the rule beside the other
  message rules.
