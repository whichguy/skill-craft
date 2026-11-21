# Delta 1

## What I used and tried

- Read the request, specification, plan, build and test reports, README, API and operations guides, and assignment and persistence decisions. The build and test reports listed no unfinished or failing work. There were no fix or referee reports in `ratchet/`.
- Started the service with `PORT=0 npm start` and used the HTTP API to create, assign, retry, reassign and clear tickets. Checked conjunctive filters, the unassigned queue, encoded names, cursor continuation after reassignment, lifecycle refusals and reopening. Tried name, actor, intake, body and query limits, including 32 versus 33 emoji and the configured and default request byte boundaries. Sent malformed JSON, raw invalid UTF-8, and malformed query escapes.
- Ran `list`, `list --raw`, `show` and the weekly report on the saved file. Checked that raw output retained the first four fields and included an empty fifth field for an unassigned ticket. Compared CLI history for clear and marker-like names. Restarted with the same data and enabled the worker after renaming and reassigning a ticket. Compared the resulting JSON lines with the queued events and audit, and verified a notification retry after recovering its sink.
- Tried a legacy file, an over-limit saved assignee, a saved assignee with invalid UTF-8, and an in-memory restart. Forced a replacement failure on a disposable data file and confirmed the committed state survived and a retry succeeded. The remaining staging file held an uncommitted snapshot until the retry. Also tried using one path for both state and notifications. Stopped the service processes by PID. `npm test` passed all 132 tests.

## Added clauses

- **C-201** — product keeps to it: yes. A notice queued for `VPN drops every hour` still used that title after the ticket was renamed to `VPN still drops` and the worker was enabled on restart.
- **C-202** — product keeps to it: yes. Each delivered key matched its own assignment audit sequence and actor, including both notices to Dana. A later assignment to Dana after restart received a distinct key that matched its own audit entry.
- **C-203** — product keeps to it: yes. `show` distinguished the unassigned marker from the quoted names `"—"` and `"null"` on both sides of assignment history changes.
- **C-204** — product keeps to it: no. A `PUT` with a raw `0xFF` in the assignee string returned 200, stored `Ana�`, audited that name and queued a notice to it.
- **C-205** — product keeps to it: no. Both `assignee=Ana%FF` and `assignee=Ana%EF%BF%BD` returned 200 and selected the tickets owned by `Ana�`.
- **C-206** — product keeps to it: no. The service started on a version-1 file containing a raw invalid byte in the saved name and returned `Ana�` as the assignee.
- **C-207** — product keeps to it: no. With the state and sink paths identical, the outbox reported `sent`. The shared file held the version-1 state document with zero delivery lines.
