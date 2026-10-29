---
bump: patch
---
A step after the first no longer fails its test stage because an earlier step's tests pass on its base. The base run
checks RED only for the cases new at the step; an earlier step's cases are run and counted, not judged, and are recorded
as `earlier_steps` in the base record. A focused command that holds only earlier steps' cases, with IDs or with only
criteria, is counted too. Before this, a multi-step item with code was refused at its second step's test stage, and
`red_na` could not exempt those tests.
- `red_na` names only a test ID new at this step, and `retired_tests` refuses an ID a focused command still lists,
  an earlier step's included; both refusals say so. The packet's base rule says no test ID new at this step may pass
  and that an earlier step's IDs are not judged. After a send-back the redone plan's first step sees a committed case as
  new; the refusal names `red_na` for "a case a step committed before a send-back".
- A step plan's refusal of a step that only changes test files now says the test stage writes the tests for the
  behaviour the steps build, true on both routes.
