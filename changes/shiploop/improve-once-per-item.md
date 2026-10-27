---
bump: minor
---
Improve reviews implement once per work item instead of once per step, and test-spec has no Improve review.
- **The item review.** It runs after the item's last accepted implement step, before its test stage, and covers the item's
  whole change. Its review base is the tree the item's first step began from, and its focus names the item's steps. So
  the tests the test stage writes next cover the review's fixes.
- **A round that changed nothing is skipped.** A round of steps that changed no file (reissued steps after a send-back)
  still gets no review.
- **Test-spec has no Improve review.** The test stage's own checks bind its cases: RED on the base, the candidate run and
  the mutation check.
- **Why.** Over seven runs, step reviews found something in 11 of 40, and test-spec reviews made 2 real catches in 14. On
  DeepSeek battleship, 12 step reviews took 28 minutes for 3 real code fixes. The estimate there is 22 reviews down to
  11, about 31 minutes.
- **Other changes.**
  - The planning review option now covers four stages.
  - The IMP-4 shadow record is gone: it measured a per-step trigger this rule replaces.
  - The test-spec re-review narrowing is gone with the review.
