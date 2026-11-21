## Failing now

- C-36. The CLI displays `-` both for an unassigned ticket and for a ticket whose assignee is named `-`.
- C-42. The new `node:test` cases exercise the assignment API, change effects and assignee filters. They do not exercise CLI listing.
- C-44. The PUT returned 500 with `error.code: "internal"` after the data path was obstructed. The live ticket still showed the new assignee, the audit entry had been appended, and the outbox contained a pending assignment notice. After restoring the data path, the same PUT returned 200 while the saved file remained unchanged.

## Discoveries

- An unrelated successful save must not make a previously refused assignment durable. | Observable: Obstruct the data path, issue an assignment PUT that returns 500, restore the path, create a different ticket, and restart. The original ticket, audit, and outbox should retain their pre-PUT assignment state. | Why: The file was unchanged immediately after the failed PUT, but creating the other ticket saved the leaked assignee, audit entry, and pending notice.
