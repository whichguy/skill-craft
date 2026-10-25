---
bump: minor
---
Every mutant that survives the test stage's mutation check needs a test that kills it, or a disposition. Before, the
check refused only when no mutant was killed, so a partial survival passed silently.
- **Dispositions:** the test result's new `mutant_dispositions` lists one entry per survivor, each with its evidence:
  - `equivalent`: no input the contract allows tells them apart;
  - `out-of-scope`: not product behaviour, such as a tool's generated file;
  - `not-exercisable`: no test this runner can run reaches it.
- **Refusal:** it lists each survivor as `file:line:column` and names both exits. It is not a kill-rate target, and it
  forbids weakening an oracle to lower the count.
- **Reuse:** a resubmission that changes only the dispositions reuses the latest mutation run while the candidate
  tree and the focused commands are unchanged, so no mutant runs again.
- **End of work:** the end-of-work review checks that a later edit has not made a recorded disposition untrue, and
  that a claimed kill has a run behind it.
