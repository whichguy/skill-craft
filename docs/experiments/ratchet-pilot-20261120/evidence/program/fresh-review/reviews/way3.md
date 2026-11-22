Verdict: reject
## What must be true
- Run npm start with PORT=0 and get HTTP 200 from GET /health on the reported port. | held
- Create a ticket and see assignee null on create, detail, listing, edit and transition responses while it remains unassigned. | held
- Assign an open ticket, replace its assignee, and unassign it with PUT and a JSON null. | held
- Assign and unassign an in-progress ticket, and receive conflict for both operations on resolved and closed tickets. | held
- Assign a one-character name and a 64-character name, and get invalid for an empty or 65-character name, a missing field, a wrong type, malformed JSON or an unknown field. | held
- Send a valid assignment for a missing ticket and get the existing not_found error envelope. | held
- Repeat the current assignment or unassign an already unassigned active ticket and verify that the ticket, updated time, audit and outbox stay the same. | held
- Inspect audit after changing the assignee and see the actor and the before and after values, in order. | held
- Assign and reassign to different agents while the worker is off, see pending events for both agents, then start the worker and see the messages delivered through NOTIFY_FILE. | held
- List by a named assignee, by an empty assignee and without an assignee filter, and verify that named and unassigned results are distinct. | held
- Combine assignee, status and priority with independently matching tickets and receive only their intersection, including when assignee is omitted. | held
- Page an assignee-filtered listing in ticket ID order with limit and next, and get the existing invalid envelope for bad status, priority, limit or cursor. | held
- Use the operator CLI to list assigned and unassigned tickets and see who each displayed ticket is assigned to. | held
- Use the existing CLI status and priority flags together and get the same tickets as before on the same data file. | broken
- Run list --raw and verify that ID, status, priority and the full title occupy their original tab-delimited positions. | held
- Run the weekly JSON report and check its total and status and priority counts against the same data file. | held
- Use CLI show to read ticket details and history, confirm the CLI leaves the file intact, and check the existing exit codes for missing tickets and usage errors. | held
- Open a file written by the starting service and get its tickets as unassigned, with the existing audit and outbox intact and no ID reuse. | held
- Restart after changing an assignment and confirm that the assignment, history and pending outbox survive. | held
- Create, edit and transition tickets using existing routes, and verify sequential IDs, default priority, validation, closed-ticket restrictions and patch no-op behavior. | held
- Edit the title or priority of a resolved ticket through PATCH and see the edit recorded in its history. | broken
- Create and resolve a ticket and verify its requester still receives the original notifications. | held
- Run npm test with the unchanged starting tests and the added node:test assignment tests. | held
## Findings
- The starting API allowed title and priority edits on resolved tickets. The request limits assignment changes by status. | PATCH now rejects edits on resolved tickets with HTTP 409 conflict. | Probe: On both services, POST /tickets with a title of "VPN" and a requester, then POST /tickets/T-0001/transition with {"to":"in_progress"} and then {"to":"resolved"}. PATCH /tickets/T-0001 with {"title":"VPN on floor 3","priority":"urgent"} returned 200 and added a ticket.updated audit entry on the starting service. The delivery returned 409 with "ticket T-0001 is resolved and can no longer change", and GET still showed title "VPN" and priority "normal".
- The starting CLI combined its existing status and priority flags by matching either value. The request changes filter matching for GET /tickets and asks the CLI listing to show the assignee. | The CLI now requires both flags to match, so it omits tickets previously returned. | Probe: Run node bin/tickets.js --data FILE list --status open --priority urgent from both product directories with the same file containing T-0001 open/normal, T-0002 resolved/urgent, T-0003 open/high and T-0004 open/normal. The starting CLI returned all four IDs. The delivery exited 0 and printed "no tickets".
## Decisions made for the requester
- Trim assignment names, reject blank names and internal control characters, and count UTF-16 code units, following the existing text validator. | Preserve whitespace verbatim or count Unicode code points.
- Compare nonempty assignee filters exactly and return an empty page for names with no matches. A repeated query key uses its first value, as with the existing GET filters. | Normalize or validate filter values, or reject duplicate keys.
- Reject all assignment requests on resolved and closed tickets with 409, including a repeat of the current assignee. | Return 200 for a no-op on an inactive ticket.
- Use the stored agent name as the notification recipient. | Look up a delivery address for the agent.
- Retain earlier pending assignment messages and coalesce pending messages for the same ticket and agent. | Withdraw superseded messages or queue a separate message for each change back to a previously assigned agent.
- Send no message to the former assignee when unassigning and record the audit action as ticket.assigned for both assigning and unassigning. | Notify the former agent or use a distinct audit action for unassignment.
- Show a hyphen for an unassigned ticket in the table and place ASSIGNEE after PRIORITY. The show command keeps its existing details layout and exposes assignment changes in history. | Use a different placeholder or column position, or add an assignee field to show.
- Append the assignee to list --raw as a fifth tab-delimited field, empty for unassigned tickets. The four existing fields retain their positions and the weekly report counts are unchanged. | Keep the raw listing at four fields.
