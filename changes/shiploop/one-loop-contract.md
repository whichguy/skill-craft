---
bump: patch
---

The test loop, quality loop and Improve child contracts are built and
serialized by one module (the test and quality contracts are byte-identical to
before). An Improve child's exit condition now also requires the reviewed
stage's own done-when criteria, so a review loop ends on what that stage must
achieve, not only on two quiet passes.
