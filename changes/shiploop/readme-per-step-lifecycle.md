---
bump: patch
---
The README describes the lifecycle the code runs: each step is built, tested, documented, reviewed and committed before the
next begins, and there is no `verify` stage (23 producers, 7 inner stages in 4 phases). It states the step's gates (lint on
the lines changed, the proof, the base run on the step's base, graded tests, the commit stage and its retry), the ask-agent
route as it stands, and a status section: the build order, what is accomplished, in progress and pending, with a small
dependency picture.
