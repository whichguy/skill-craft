Verdict: reject
## What must be true
- Run npm start with PORT set to a free port and GET /health, then try an invalid PORT and verify startup reports it | held
- Create tickets with POST /tickets and check sequential IDs, default priority, initial open status, and an explicit null assignee on create, get, and list | held
- Assign, reassign, and unassign an open ticket and an in-progress ticket, and read back the assignee after each change | held
- Assign a one-character and a 64-character name, and reject empty, 65-character, missing, and non-string names other than null | held
- Try assigning and unassigning resolved and closed tickets and check for conflict with no state change | held
- Repeat an assignment to the same agent and compare the ticket timestamp, audit, outbox, and saved data | held
- Inspect the audit for assignment, reassignment, and unassignment, with the old and new values, X-Actor, and oldest-first order | held
- Run the worker with NOTIFY_FILE and verify the new agent receives a message identifying the assignment and ticket, including after reassignment | held
- Turn off the worker, assign different agents before it runs, and verify each assignment queues a message for its intended agent | held
- Unassign and reassign the same agent or reassign back to a previous agent while the worker is off, then run the worker and check that each real assignment is delivered | broken
- List tickets by a named assignee and by assignee=, and combine each with status and priority against tickets matching only some of the filters | held
- List with no assignee parameter, with each old filter by itself, and across cursor pages in ID order, including a page filtered by assignee | held
- Try invalid request bodies, invalid listing parameters, unknown ticket IDs, and unknown routes and verify the service's JSON error envelope | held
- PATCH a ticket's title and priority, repeat the same patch, and check actor, audit, and updated, then verify a closed ticket rejects edits | held
- Run the forward lifecycle and reopen a resolved ticket, and check that forbidden transitions still return conflict | held
- Create and resolve a ticket as before and check the requester receives both notifications through the worker, with pending and sent visible in the outbox | held
- Start the delivered server from a data file written by the starting service, then assign and restart, and verify assignee, history, pending outbox, and next ID survive | held
- Start with a manually edited DATA_FILE containing an assignee longer than 64 characters and check that the invalid record is rejected at startup | broken
- Set an unusable notification path and observe the failed attempt in the outbox, then restore the path and observe a retry succeed | held
- List assigned and unassigned tickets in the CLI table and raw output, keeping raw ID, status, priority, and title in their original tab-separated positions | held
- Use either CLI filter by itself, show an existing ticket with its history, and check empty results and exit codes without rewriting the data file | held
- Run CLI list with both status and priority flags and compare the matching ticket IDs with the starting CLI | broken
- Run the weekly report on the same data file and verify its total and counts by status and priority | held
- Run npm test and verify the original tests pass as written and Node discovers the added assignment tests under test/ | held
- Run each command in ratchet/acceptance.json and check its exit status | held
## Findings
- Each actual assignment to an agent should notify that agent | The pending notification for an earlier assignment to the same agent suppresses the notification for a later change | Probe: Start with PORT=0 and WORKER_INTERVAL_MS=0, create T-0001, and PUT /tickets/T-0001/assignee with Amina, Jo, then Amina. All three requests returned 200 and the audit recorded all three changes. GET /admin/outbox showed assignment recipients [Amina, Jo], and restarting with the same DATA_FILE, WORKER_INTERVAL_MS=25 and NOTIFY_FILE delivered only [Amina, Jo]. Amina, null, Amina also left just one assignment event.
- The starting CLI list with both status and priority flags includes tickets matching either flag. The request specifies all-filter matching for GET /tickets and adds assignee display to the CLI | The CLI now requires both flags to match, removing rows from an existing command | Probe: Run `node bin/tickets.js --data "$data" list --status open --priority urgent --raw` from both products using the same file with T-0001 open/normal, T-0002 in_progress/urgent and T-0003 open/urgent. The starting CLI returned all three IDs. The delivered CLI returned only T-0003.
- An assignee name is limited to 64 characters, and the starting service's data-file contract rejects invalid records at startup | A data file can introduce an assignee the assignment endpoint rejects | Probe: Set `tickets[0].assignee` to 65 ASCII x characters in a copy of a valid DATA_FILE. Start with PORT=0 and the edited file. GET /tickets/T-0001 returned 200 with all 65 characters. PUT /tickets/T-0001/assignee with the same value returned 400 invalid, “assignee must be at most 64 characters.”
## Decisions made for the requester
- Reuses the requester name rules by trimming whitespace, rejecting control characters, and measuring length in UTF-16 code units | Store names verbatim or measure length in Unicode code points
- Matches the stored name case-sensitively against the query value as supplied and returns an empty result for an unmatched value | Normalize or validate the query value before matching
- Uses the first value when the assignee query parameter is repeated, consistent with the existing query parser | Reject repeated values or apply each of them
- Returns 409 for any assignment request on a resolved or closed ticket, including a request for its current assignee | Return 200 for no-op requests in those states
- Uses the agent name directly as the notification recipient and retains previously queued notifications after reassignment or unassignment | Resolve names through an address directory or withdraw obsolete pending messages
- Uses ticket.assigned as the audit action for assignment, reassignment, and unassignment | Use separate action names for assigning and unassigning
- Shows a hyphen for an unassigned ticket in the CLI table and appends a fifth raw field containing the name or an empty field | Use another placeholder or keep raw output at four fields
