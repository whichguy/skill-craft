---
bump: minor
---
A step's commit survives a call that stops anywhere between Git's commit and the saved state (design T section 9.1,
2c-0, Astra's finding 2).
- The commit stage still writes its pending record before it commits. It now records the commit (the ledger row's
  `commit`, the `commits/<action>.txt` file) and drops `pending` in the same journaled save as the state that advances
  past the step. Before, it did that first, so a call killed after Git committed and before the state was saved left
  HEAD on the step's own commit with no pending record, and the retry refused it.
- The call that enters the next step records the step's base after its save. A call killed between them left that step
  with no iteration record, and the commit stage skipped it. The next call of any command but `status` and `report`
  now records the base from HEAD, so the step is committed like the others.
