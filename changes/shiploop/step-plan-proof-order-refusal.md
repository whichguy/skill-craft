---
bump: minor
---
Step-plan now refuses a step whose Proof cannot pass when that step's implement reports done: a Proof that runs a test
file the item base lacks and no earlier step declares (implement writes no tests, and the step's test stage writes them
only after its implement), or one that reads a file the base lacks which only a later step declares. Before, this fault
was found only after a whole implement Until Loop, as a send-back to step-plan: 9 of the 12 implement send-backs in the
saved runs of 2026-10-03 to 10-31 (8 on Codex Terra 6.1 xhigh). The step-plan Checked-by line names it.
