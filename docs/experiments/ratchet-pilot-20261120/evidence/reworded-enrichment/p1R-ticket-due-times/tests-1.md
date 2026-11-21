## Failing now

- C-3 — With due times disabled, `RESPONSE_HOURS=urgent=nonsense` prevents startup. At the latest representable creation instant, disabled-mode creation returns 500 `internal` where 1.4.0 returns 201.
- C-19 — Enabled startup on a mixed file returns ticket details and lists with `due`, including filtered overdue results, while deadlines for two tickets are still absent from the data file.
- C-29 — `npm test` passes the 117 preexisting cases. It runs no new deadline cases under `test/`, so U-8 also fails.

## Discoveries

- The operator documentation identifies the response-hours settings, the action that makes preparation durable, and how to verify completion. | Observable: Follow the documented settings and procedure on a legacy file and inspect the saved assignments before enabling due times. | Why: The build accepts a single `RESPONSE_HOURS` map and can save assignments on graceful shutdown of a disabled service. The operator documentation describes neither.
- A create request whose save fails leaves no ticket or related records for a subsequent successful save to persist. | Observable: Block writes to `DATA_FILE`, submit a ticket and get 500, restore writes, submit another ticket, then inspect the saved state. | Why: The second request returned 201 and its save also persisted the first ticket. C-31 exercises deadline arithmetic failure.
