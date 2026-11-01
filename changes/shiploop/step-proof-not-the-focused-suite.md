---
bump: patch
---
Step-plan's proof bullet now says a step's Proof is never the focused command or a filtered copy of it, in place of "reuse a
recorded command that proves them": the focused command runs this item's tests, which the test stage writes after the step's
implement, so as a Proof it runs nothing and the plan came back. The step-plan Improve review also looks for a check that needs an
unwritten test.
