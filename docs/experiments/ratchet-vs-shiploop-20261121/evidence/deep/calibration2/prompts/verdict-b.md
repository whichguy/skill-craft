# Three deliveries of one request: which is the better feature?

Three builders each delivered the same customer request (below). Each delivery was audited by running it: every
stated requirement, a list of conditions the request leaves unsaid, its tests, its specification and its documents.
Items the audits disagreed on were run again on all three by another person, and every defect an auditor reported
was tried on all three. You have the audits (with those re-runs applied) and the defect table. The deliveries are
labelled X, Y and Z; the labels and their order carry no meaning. You do not have the products and should not guess
at them beyond the audits.

Judge as the person who will run this feature and keep it working: what does each delivery give that the others do
not, and does it matter? Size is not quality: a longer specification, more tests or more code count only through
what the audits show they bought, and count against a delivery where the audits show they cost (requirements the
customer did not ask for, tests that pin one builder's choices, code a maintainer must carry). Count each
consequence once, however many audit lines mention it.

For each pair (X-Y, X-Z, Z-Y):

- `better`: `<letter>-much`, `<letter>-some` (naming the better delivery) or `same`.
- `advantages`: each real advantage of either side, with the audit line or defect id behind it (`ref`) and whom it
  matters to: `requester`, `operator`, `maintainer` or `no one`.
- `lesser_lacks`: what the lesser delivery would need to match the better one, as a list of concrete changes.
- `one_task_closes`: `yes` if one short follow-up task (about an hour of the same builder's work) would close that
  list, else `no`. `yes` when `better` is `same`.
- `why`: three sentences at most.

Answer with one JSON object and nothing else:

```json
{"pairs": [{"pair": "X-Y", "better": "same", "advantages": [{"of": "X", "what": "...", "ref": "U-4", "matters_to": "operator"}], "lesser_lacks": ["..."], "one_task_closes": "yes", "why": "..."}]}
```

## The request

This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add ticket assignment. `PUT /tickets/:id/assignee` with a JSON body `{"assignee": "<agent>"}` assigns the ticket to that agent, and `{"assignee": null}` unassigns it; an agent is a non-empty name of at most 64 characters. Only open and in-progress tickets can be assigned or unassigned. Assigning a ticket to the agent it already has changes nothing. Every ticket shows its `assignee` (null when unassigned). The agent a ticket is assigned to is notified that it was assigned to them. `GET /tickets` gains an `assignee` filter: `assignee=<agent>` keeps that agent's tickets and an empty `assignee=` keeps the unassigned ones; a ticket must match every filter given. The command-line listing shows each ticket's assignee. Everything the service already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.

## The inventory


## Stated requirements

- **S-1**: The service has no npm dependencies: package.json lists no dependencies and it runs on Node's standard library alone.
- **S-2**: `npm start` runs src/server.js, listening on the port in the PORT environment variable.
- **S-3**: `PUT /tickets/:id/assignee` with the JSON body `{"assignee": "<agent>"}` assigns the ticket to that agent: afterwards the ticket's `assignee` is that agent.
- **S-4**: `PUT /tickets/:id/assignee` with the JSON body `{"assignee": null}` unassigns the ticket: afterwards its `assignee` is null.
- **S-5**: An agent is a non-empty name: `{"assignee": ""}` is refused and the ticket's assignee does not change.
- **S-6**: An agent is a name of at most 64 characters: a 64-character name is accepted, a 65-character name is refused and the ticket's assignee does not change.
- **S-7**: Open and in-progress tickets can be assigned and unassigned: assigning and unassigning an `open` ticket and an `in_progress` ticket succeeds.
- **S-8**: A ticket that is not open or in-progress (resolved or closed) cannot be assigned: the request is refused and the ticket is left unchanged.
- **S-9**: A ticket that is not open or in-progress (resolved or closed) cannot be unassigned: the request is refused and the ticket keeps its assignee.
- **S-10**: Assigning a ticket to the agent it already has changes nothing (the ticket, its history and the notifications stay as they were).
- **S-11**: Every ticket shows its `assignee`: the field is present on every ticket the API returns (`GET /tickets/:id`, each item of `GET /tickets`, and the ticket returned by create, change, transition and assignment).
- **S-12**: A ticket's `assignee` is null when it is unassigned, including a newly created ticket.
- **S-13**: The agent a ticket is assigned to is notified that it was assigned to them.
- **S-14**: `GET /tickets?assignee=<agent>` keeps only that agent's tickets.
- **S-15**: `GET /tickets?assignee=` (empty value) keeps only the unassigned tickets.
- **S-16**: A ticket must match every filter given: `assignee` combined with `status` and/or `priority` lists only the tickets matching all of them.
- **S-17**: The command-line listing (`bin/tickets.js list`) shows each ticket's assignee.
- **S-18**: Everything the service already does keeps working.
- **S-19**: The service's existing tests still pass as they are (unmodified).
- **S-20**: There are node:test tests under test/ for the new behaviour.
- **S-21**: `npm test` runs the new tests together with the existing ones.

## Conditions the request leaves unsaid

- **U-1**: What a caller gets when assigning or unassigning a ticket that is not open or in-progress (resolved or closed), including a request that would change nothing there (the current agent again, or null on an unassigned ticket), and that the stored assignee stays as it was.
  - Probe: Start the service. POST /tickets with a valid body; PUT /tickets/<id>/assignee {"assignee":"dana"}; POST /tickets/<id>/transition {"to":"in_progress"}, then {"to":"resolved"}. PUT {"assignee":"lee"}, PUT {"assignee":"dana"} and PUT {"assignee":null}; record each status and body, then GET the ticket, GET /tickets/<id>/audit and GET /admin/outbox. Transition to closed and repeat. Also create a second ticket, move it to resolved without assigning it, and PUT {"assignee":null} and {"assignee":"dana"}.
  - Outcomes that would be acceptable: Any refusal that leaves assignee, `updated`, the audit and the outbox unchanged; 409 with {"error":{"code":"conflict",...}} and a message naming the status matches the API's convention (400, or 200 with the unchanged ticket, leave the data alone but differ from it). For a request that changes nothing on a resolved/closed ticket, either 409 or 200 with the unchanged ticket, if consistent and documented.
- **U-2**: What the endpoint answers for a malformed request: no `assignee` field, a non-string non-null value (a number, an object, an array), extra unknown fields, a body that is not a JSON object, a body that is not valid JSON or not valid UTF-8, and an unknown ticket id.
  - Probe: Create a ticket; PUT /tickets/<id>/assignee with each of: {}, {"assignee":5}, {"assignee":{}}, {"assignee":[]}, {"assignee":"dana","x":1}, [], an empty body, text that is not JSON, and a JSON body whose assignee string holds the invalid UTF-8 byte 0xFF; then PUT /tickets/T-9999/assignee {"assignee":"dana"}. Record statuses and error codes, and GET /tickets/<id> and its audit to confirm nothing changed.
  - Outcomes that would be acceptable: 400 `invalid` in the error envelope for each malformed body, the ticket unchanged and no audit entry or notice (a missing field must not be treated as null); 404 `not_found` for the unknown ticket. Another error status also refuses; ignoring unknown fields is a weaker but request-compatible choice.
- **U-3**: How an agent name is normalised and which characters it may hold: surrounding whitespace, a whitespace-only name, tabs, line breaks and other control characters, and whether the 64-character limit counts before or after trimming.
  - Probe: Create a ticket; PUT /tickets/<id>/assignee with {"assignee":"   "}, {"assignee":"  dana  "}, {"assignee":"da\tna"}, {"assignee":"da\nna"}, and a 64-character name padded with spaces; GET the ticket after each; then GET /tickets?assignee=dana and run `node bin/tickets.js --data FILE list --raw`.
  - Outcomes that would be acceptable: Whitespace-only refused as empty; surrounding whitespace trimmed (or kept as part of the name) consistently, with filtering using the same stored form; control characters refused with 400 like title and requester, or accepted only if the human listing still shows the name on one line; the limit applied the same way the requester's is.
- **U-4**: Whether an assignment or unassignment is recorded in the audit log, under which action, with which actor and changes, and that a no-op records nothing.
  - Probe: Create a ticket; PUT /tickets/<id>/assignee {"assignee":"dana"} with header X-Actor: lee; PUT the same body again; PUT {"assignee":null} with X-Actor: sam; PUT {"assignee":"dana"} with no X-Actor header; GET /tickets/<id>/audit and read the entries after creation.
  - Outcomes that would be acceptable: One entry per real change, e.g. action `ticket.assigned`/`ticket.unassigned` or `ticket.updated`, actor from X-Actor (`system` without it), changes {"assignee":{"from":null,"to":"dana"}}; no entry for the repeated assignment. Omitting audit entries satisfies the request's wording but not the service's convention.
- **U-5**: Whether an assignment or unassignment moves the ticket's `updated` time, and whether a no-op leaves it as it was.
  - Probe: Create a ticket and note `updated`; wait a second; PUT {"assignee":"dana"} and read `updated`; PUT {"assignee":"dana"} again and read it; PUT {"assignee":null} and read it.
  - Outcomes that would be acceptable: Assignment and unassignment set `updated` to the time of the change; the repeated assignment leaves it unchanged. Not moving it on assignment is a defensible alternative if documented.
- **U-6**: Whether unassigning an open or in-progress ticket that is already unassigned (including a repeated unassign) is a no-op like re-assigning the same agent.
  - Probe: Start with WORKER_INTERVAL_MS=0. POST /tickets, then PUT {"assignee":null} twice; GET the ticket, GET /tickets/<id>/audit and GET /admin/outbox and compare with the ticket right after creation. Then assign "dana", unassign, unassign again and compare the same three.
  - Outcomes that would be acceptable: A successful response showing assignee null, with the same `updated`, no new audit entry and no notification. Recording an audit entry for it is also acceptable if documented.
- **U-7**: Where the assignment notification goes and whether it can be delivered: the agent is a name, not an address; each notification type needs wording; what the message says; and whether the PUT waits for delivery.
  - Probe: Start with NOTIFY_FILE=/tmp/n.jsonl and WORKER_INTERVAL_MS=100; create a ticket; PUT /tickets/<id>/assignee {"assignee":"dana"}; wait a second; read the last line of /tmp/n.jsonl and GET /admin/outbox (pending, sent and dead).
  - Outcomes that would be acceptable: A sent notification of an assignment type (e.g. `ticket.assigned`) with `to` = the agent's name (or an address derived from it, if documented), a subject and body naming the ticket id and title, and no dead events; delivery through the outbox after the PUT returns, or sending inside the PUT, both fit.
- **U-8**: Whether every assignment notifies its agent when assignments of one ticket follow each other before the worker delivers, given that the outbox drops an enqueue whose key is still pending (the default key is type + ticket).
  - Probe: Start with WORKER_INTERVAL_MS=0; create a ticket; assign it to dana, then to lee, then unassign, then assign dana again; GET /admin/outbox and read the pending events' `to` and `key`. Then let the worker deliver them, assign lee again and check that a new pending event for lee appears.
  - Outcomes that would be acceptable: lee has a pending notification; dana either one or two. Keys that include the agent, or one notification per assignment, are both fine; losing the current assignee's notification is not.
- **U-11**: Whether `assignee` is kept in the data file across restarts, whether a data file written before this change (tickets with no `assignee` field) still loads, and what an invalid assignee in the file does at start.
  - Probe: Start with DATA_FILE=/tmp/t.json; create and assign a ticket; stop (SIGTERM) and start again; GET the ticket. Separately, run the previous version with DATA_FILE, create tickets, stop it, start the new version on the same file and GET /tickets; also hand-edit a ticket's assignee to 5 or a 65-character name and start.
  - Outcomes that would be acceptable: Assignee survives the restart; old files load with assignee null (no format version change, or a version bump that still reads version 1); an invalid assignee in the file is refused at start with a message naming the record.
- **U-12**: What happens to the assignee when a ticket is moved to in_progress, resolved, closed or reopened, and whether the assignee filter still returns it afterwards.
  - Probe: Create a ticket; assign dana; transition to in_progress, then resolved, GETting the ticket and GET /tickets?assignee=dana and /tickets?assignee= after each; transition to open (reopen) and read again, then PUT {"assignee":"lee"}; on another ticket go through resolved to closed and read again.
  - Outcomes that would be acceptable: Keeping the assignee through every transition (filters combine with status to find active work) is fine; clearing it when the ticket leaves open/in-progress is also defensible if documented and audited, with those tickets then in the empty `assignee=` filter.
- **U-13**: How the `assignee` filter value matches: exact and case-sensitive or not, whether it is trimmed, and what a value that cannot be an accepted name (longer than 64 characters, malformed) or a repeated `assignee` parameter answers.
  - Probe: Assign tickets to dana; GET /tickets?assignee=Dana, ?assignee=%20dana, ?assignee=<65 characters>, ?assignee=dana&assignee=lee; read statuses and items.
  - Outcomes that would be acceptable: Exact match on the stored (normalised) name, or a trimmed or case-insensitive match if assignment stores the same form; an over-long value either 400 `invalid` or an empty page; a repeated parameter treated as the existing filters treat one (e.g. the first value), or refused.
- **U-14**: Whether a listing filtered by `assignee` still pages correctly through its cursor.
  - Probe: Assign more tickets to dana than one page holds, with other tickets in between; GET /tickets?assignee=dana&limit=2, then follow each `next` cursor with the same filter until `next` is null; do the same with `assignee=`.
  - Outcomes that would be acceptable: Every matching ticket exactly once across the pages, in id order, and no other ticket.
- **U-15**: Whether `status` and `priority` given together without `assignee` list the intersection (as docs/api.md describes) or keep what the service does today.
  - Probe: Create an open/low ticket, an open/urgent ticket and a resolved/urgent ticket; GET /tickets?status=open&priority=urgent and compare with the same query on the previous version.
  - Outcomes that would be acceptable: Only the open/urgent ticket (every filter applied, as the request and docs say); keeping the previous version's result is also arguable under 'everything keeps working' if documented.
- **U-16**: Whether `list --raw` gains an assignee column, where, and how an unassigned ticket appears in it.
  - Probe: With a data file holding tickets assigned (one to a name with a space, such as "ada li") and unassigned, run `node bin/tickets.js --data FILE list --raw` and count tab-separated fields per line; run `node scripts/weekly-report.js --data FILE --json` and compare its counts with the previous version on the same file.
  - Outcomes that would be acceptable: Raw output unchanged, or the assignee appended as a fifth column after title with an empty field (or a fixed marker) for unassigned; the weekly report's counts identical either way.
- **U-17**: How the `list` table shows the assignee of an unassigned ticket.
  - Probe: With a data file holding an assigned and an unassigned ticket, run `node bin/tickets.js --data FILE list`.
  - Outcomes that would be acceptable: An assignee column with the name for assigned tickets and a blank, '-' or the word null for unassigned, as long as the two are distinguishable.
- **U-18**: Whether the command-line ticket detail (`show`) prints the assignee.
  - Probe: With a data file holding an assigned and an unassigned ticket, run `node bin/tickets.js --data FILE show <id>` for each.
  - Outcomes that would be acceptable: Printing the assignee (and an explicit unassigned state) is welcome; omitting it is compatible with the request.
- **U-20**: Whether `POST /tickets` and `PATCH /tickets/:id` accept an `assignee` field.
  - Probe: POST /tickets with a valid body plus "assignee":"dana"; PATCH /tickets/<id> {"assignee":"dana"}; read statuses and the ticket.
  - Outcomes that would be acceptable: Both refuse it as an unknown field (400), or accept it with exactly the same validation, state rule, audit and notification as the PUT endpoint.
- **U-21**: What a successful `PUT /tickets/:id/assignee` answers.
  - Probe: Create a ticket; PUT /tickets/<id>/assignee {"assignee":"dana"}; record status, content-type and body and compare with GET /tickets/<id>; repeat the same PUT and compare; PUT {"assignee":null} and record the same.
  - Outcomes that would be acceptable: 200 with the whole ticket including `assignee` (also for the no-op); 204 or another success status with an empty body is acceptable if a following GET shows the assignment; a ticket body without `assignee` is not.
- **U-22**: Whether the documentation and release records describe the change: docs/api.md (endpoint, ticket field, filter, audit action, notification), README command-line columns, a CHANGELOG.md section with a version bump in package.json, and a decision record if a format or rule changed.
  - Probe: Read docs/api.md, README.md, CHANGELOG.md, package.json `version` and docs/decisions/ in the delivered tree and look for the assignee endpoint, field, filter and notification.
  - Outcomes that would be acceptable: api.md documents all of it; a new changelog section and version; a decision record optional unless the data file format or a convention changed.
- **U-26**: The command-line ticket detail (`show`) stays read-only.
  - Probe: Copy a data file holding assigned and unassigned tickets; run `node bin/tickets.js --data FILE show <id>` and then `DATA_FILE=FILE node bin/tickets.js show <id>`; compare the file with the copy byte for byte after each.
  - Outcomes that would be acceptable: The file is byte-for-byte unchanged after each command.
- **U-27**: The command-line ticket detail keeps showing the ticket's history in oldest-first order, including assignment changes.
  - Probe: With DATA_FILE set, create a ticket, assign it to dana with X-Actor: lee and then to sam with X-Actor: kim; stop the service; run `node bin/tickets.js --data FILE show <id>` and compare its history with GET /tickets/<id>/audit.
  - Outcomes that would be acceptable: The existing history lines and both assignment entries appear oldest first, in the same order as the audit API, and the current assignee is visible in the detail.

## The defect table (each defect with what each delivery did when it was tried)

- **D-1** (low) Delivered documents not updated; README misstates the list --raw columns. Expected: docs/api.md and README describe the endpoint, assignee field, filter, audit action, notification and the fifth raw column; a CHANGELOG section and version bump. — X: present; Y: present; Z: present
- **D-2** (low) An assignee holding invalid UTF-8 is accepted and stored with a replacement character. Expected: 400 invalid and the ticket unchanged. — X: present; Y: present; Z: present
- **D-3** (low) An agent named "-" cannot be told apart from an unassigned ticket in the list table. Expected: Assigned and unassigned tickets distinguishable (refuse "-" or use a marker no name can be). — X: present; Y: present; Z: present
- **D-4** (low) Data file load does not apply the assignee rules beyond non-empty string. Expected: Start refused with a message naming the record, as an assignee of 5 or "" already is. — X: present; Y: present; Z: present
- **D-5** (high) Assignment notification is sent to the ticket's requester, not to the assigned agent. Expected: A ticket.assigned notification addressed to dana; the requester is not told the ticket is assigned to them. — X: absent; Y: present; Z: absent
- **D-6** (low) The 64-character limit counts UTF-16 code units, refusing names of fewer than 64 characters. Expected: The 33-character name accepted. — X: present; Y: present; Z: present

## Audit of delivery X

```json
{
 "code": "X",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies or devDependencies; the service started and served every probe with no node_modules folder present.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47455 npm start ran 'node src/server.js' and logged 'tickets listening on 47455'; GET /health -> 200 {\"status\":\"ok\"}; POST /tickets -> 201.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PUT /tickets/T-0001/assignee {\"assignee\":\"dana\"} -> 200 with assignee \"dana\"; GET /tickets/T-0001 -> assignee \"dana\".",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":null} on the assigned open ticket -> 200 with assignee null; GET shows assignee null.",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/tickets/validate.js assignment(): 'body.assignee === null ? null : text(...)' changed to 'false ? null : text(...)' (null refused with 400); npm test: 121 pass, 1 fail, the failing test 'a ticket is assigned, reassigned and unassigned, each change audited with before and after'. Undone; suite back to 122/122."
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":\"\"} -> 400 {\"error\":{\"code\":\"invalid\",\"message\":\"assignee must not be empty\"}}; the audit shows no entry for it and the ticket kept its assignee.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "PUT with a 64-character name -> 200, assignee is the 64 a's; PUT with 65 characters -> 400 invalid 'assignee must be at most 64 characters'; GET afterwards still shows the 64-character name.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "Open ticket: assign dana -> 200, unassign -> 200. After transition to in_progress: assign kim -> 200, unassign -> 200 null, assign dana -> 200.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "Resolved ticket: PUT {\"assignee\":\"lee\"} -> 409 conflict 'ticket T-0001 is resolved: only open and in-progress tickets can be assigned'; closed: same 409 naming closed. Ticket, audit and outbox compared byte for byte before and after: unchanged.",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/store.js assign(): 'if (!isActive(ticket.status)) {' changed to 'if (!isActive(ticket.status) && false) {'; npm test: 121 pass, 1 fail, 'only open and in-progress tickets can be assigned, and errors use the envelope'. Undone; suite back to 122/122."
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "Resolved ticket assigned to dana: PUT {\"assignee\":null} -> 409 conflict; closed: same; GET shows assignee still dana, audit and outbox unchanged.",
   "spec": "none",
   "proved": "passes",
   "proved_by": "src/store.js assign(): 'if (!isActive(ticket.status)) {' changed to 'if (!isActive(ticket.status) && assignee !== null) {' (unassigning a resolved/closed ticket succeeds); npm test: 122 pass, 0 fail. No test covers unassigning a resolved or closed ticket. Undone; suite 122/122."
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "Second PUT {\"assignee\":\"dana\"} -> 200 with the same ticket (same updated); audit kept one ticket.assigned entry; outbox kept one dana event. Later probe with a 1 s gap: updated unchanged by the repeat.",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/store.js assign(): deleted 'if (ticket.assignee === assignee) return { ...ticket };'; npm test: 121 pass, 1 fail, 'assigning the agent a ticket already has changes nothing'. Undone; suite back to 122/122."
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "assignee present on POST /tickets (201), GET /tickets/:id, every item of GET /tickets?limit=100 (checked 'assignee' in each), PATCH (200), POST transition (200) and PUT assignee (200).",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> assignee null; after unassign GET -> null; tickets loaded from a 1.4.0 data file -> null.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "Assign dana -> outbox pending event type ticket.assigned, to \"dana\", key ticket.assigned:T-0001:dana; with NOTIFY_FILE and WORKER_INTERVAL_MS=100 the line {\"type\":\"ticket.assigned\",\"to\":\"dana\",\"subject\":\"[T-0001] Assigned to you\",...} was written and the outbox showed 2 sent, 0 dead.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": "",
   "rerun": true
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "9 tickets, dana on 5, lee on 1: GET /tickets?assignee=dana -> exactly T-0001,T-0003,T-0005,T-0007,T-0009.",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/tickets/query.js parseListQuery(): 'assignee === \"\" ? null : assignee' changed to 'assignee === \"\" ? null : undefined' (agent filter ignored); npm test: 121 pass, 1 fail, 'the assignee filter keeps an agent or the unassigned, and every filter must match'. Undone; suite 122/122."
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee= -> exactly the three unassigned tickets T-0004,T-0006,T-0008.",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/tickets/query.js parseListQuery(): 'assignee === \"\" ? null : assignee' changed to 'assignee === \"\" ? undefined : assignee' (empty filter ignored); npm test: 121 pass, 1 fail, 'the assignee filter keeps an agent or the unassigned, and every filter must match'. Undone; suite 122/122."
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "assignee=dana&status=open -> 4 open dana tickets (in_progress T-0003 excluded); assignee=dana&priority=urgent -> T-0001,T-0007; assignee=dana&status=open&priority=urgent -> T-0001,T-0007; assignee=&priority=urgent -> T-0004 only.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "node bin/tickets.js --data probe-data/t.json list -> table with an ASSIGNEE column after PRIORITY: sam, '-', 'ada li'.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "Create, PATCH, transitions, closed-ticket 409s, pagination, cursor errors, body limit, X-Actor limit, /health, /admin/outbox, the worker, persistence across SIGTERM restart, CLI list/show and scripts/weekly-report.js --json (identical counts to 1.4.0 on the same file) all behaved as before. The one change: status+priority together now intersect (1.4.0 returned the union), which is what docs/api.md already promised and what the request demands.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "diff -r base/test work/X/test: only test/assignment.test.js added; npm test: 122/122 pass.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "test/assignment.test.js uses node:test with 5 tests of the new behaviour; they ran and passed.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) ran all 19 test files including assignment.test.js: 122 tests.",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Every PUT on a resolved or closed ticket answers 409 conflict naming the status ('ticket T-0001 is resolved: only open and in-progress tickets can be assigned'), including the no-op cases (current agent again, null on an unassigned resolved ticket). Ticket, updated, audit and outbox unchanged.",
   "handling": "sound",
   "observed": true,
   "evidence": "p1 probe: resolved ticket with dana: PUT lee/dana/null -> 409 x3, ticket/audit/outbox identical before and after; closed: same; second ticket resolved unassigned: PUT null -> 409, PUT dana -> 409, assignee null.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "{} -> 400 invalid 'assignee is required'; 5, {}, [], true -> 400 'assignee must be a string'; extra field -> 400 'unknown field: x'; [] body, empty body -> 400 'request body must be a JSON object'; non-JSON -> 400 'not valid JSON'; unknown ticket T-9999 or 'abc' -> 404 not_found. A body with the invalid UTF-8 byte 0xFF is accepted: 200 and the name is stored as 'da\\uFFFDna' with an audit entry and a notification.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p2 probe, each status recorded; GET and audit after the malformed bodies showed no change except the 0xFF request, which assigned 'da\\uFFFDna'.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "Names are trimmed (JS trim, including no-break space); whitespace-only refused as empty; tab and newline refused 400 'must be a single line of text'; the 64 limit counts after trimming (a padded 64-character name is accepted); the filter matches the stored trimmed form exactly (?assignee=%20dana finds nothing).",
   "handling": "sound",
   "observed": true,
   "evidence": "p2 U3 probes: '   ' -> 400, '  dana  ' -> 200 'dana', 'da\\tna' -> 400, 'da\\nna' -> 400, ' '+64c+'  ' -> 200 64c; p3 ?assignee=%20dana -> []; CLI list --raw shows names on one line.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "Each real change appends one audit entry with action ticket.assigned (also for unassign), actor from X-Actor or 'system', changes {assignee:{from,to}}; a no-op appends nothing.",
   "handling": "sound",
   "observed": true,
   "evidence": "p1 audit: seq 2 ticket.assigned lee {from:null,to:dana}; repeat dana added nothing; seq 3 ticket.assigned sam {from:dana,to:null}; later entries actor 'system' without the header.",
   "spec": "none",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-5",
   "behaviour": "Assignment and unassignment set updated to the time of the change; a repeated assignment leaves it as it was.",
   "handling": "sound",
   "observed": true,
   "evidence": "p2: created 14:26:49.053Z; after 1.1 s assign -> updated 14:26:50.158Z; after 1.1 s repeat -> 14:26:50.158Z; after 1.1 s unassign -> 14:26:52.363Z.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-6",
   "behaviour": "Unassigning an already unassigned open ticket answers 200 with assignee null and changes nothing: same updated, no audit entry, no notification.",
   "handling": "sound",
   "observed": true,
   "evidence": "p2: two PUT null on a new ticket -> 200 each, updated same as at creation, audit length 1, outbox identical; after assign+unassign, a further PUT null left audit at 3 entries, outbox and updated unchanged.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "An outbox event of type ticket.assigned with to = the agent's name, delivered by the worker after the PUT returns; message subject '[T-0001] Assigned to you', body 'Ticket T-0001 \"Laptop dead\" is now assigned to you.'; no dead events.",
   "handling": "sound",
   "observed": true,
   "evidence": "NOTIFY_FILE=probe-data/n.jsonl WORKER_INTERVAL_MS=100: last line {\"id\":2,\"key\":\"ticket.assigned:T-0001:dana\",\"type\":\"ticket.assigned\",\"to\":\"dana\",...}; outbox pending 0, sent 2, dead 0.",
   "spec": "none",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-8",
   "behaviour": "The outbox key includes the agent (ticket.assigned:<id>:<agent>), so each agent gets its own notification; a re-assignment to an agent whose earlier notice is still pending is merged into that pending one.",
   "handling": "sound",
   "observed": true,
   "evidence": "WORKER_INTERVAL_MS=0, dana, lee, null, dana: pending [[dana, ticket.assigned:T-0001:dana],[lee, ticket.assigned:T-0001:lee]]. With the worker on: lee delivered (sent [lee]), then dana and lee again -> pending [dana, lee].",
   "spec": "none",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-11",
   "behaviour": "assignee is saved in the data file and survives a SIGTERM restart; a 1.4.0 file (no assignee field) loads with assignee null and can then be assigned; on a hand-edited file an assignee of 5 or '' is refused at start naming tickets[1].assignee, but a 65-character name, a name with a tab, or a whitespace-only name loads without complaint.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p4: restart -> GET shows assignee sam; p5b: base wrote old2.json, new version listed it with assignee null and PUT dana -> 200; p5 edits: 5 -> exit 2 'tickets[1].assignee is not a non-empty string', '' -> exit 2 same, 65 chars / tab / '   ' -> 'listening'.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-12",
   "behaviour": "The assignee is kept through in_progress, resolved, closed and reopen; the ticket stays in its agent's filter and out of the empty filter; after reopen it can be reassigned.",
   "handling": "sound",
   "observed": true,
   "evidence": "p3: in_progress and resolved -> assignee dana, in ?assignee=dana true, in ?assignee= false; reopen -> dana; PUT lee -> 200; another ticket closed -> still kim and listed by ?assignee=kim.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-13",
   "behaviour": "Exact, case-sensitive match on the stored name, not trimmed; a 65-character value answers 200 with an empty page; a repeated assignee takes the first value.",
   "handling": "sound",
   "observed": true,
   "evidence": "p3: ?assignee=Dana -> []; ?assignee=%20dana -> []; 65 x's -> 200 []; ?assignee=dana&assignee=lee -> dana's 5 tickets; ?assignee=lee&assignee=dana -> T-0002.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-14",
   "behaviour": "Cursor paging with the assignee filter returns every match once, in id order, and nothing else.",
   "handling": "sound",
   "observed": true,
   "evidence": "p3: assignee=dana&limit=2 followed through next -> T-0001,T-0003,T-0005,T-0007,T-0009; assignee=&limit=2 -> T-0004,T-0006,T-0008.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-15",
   "behaviour": "status and priority together now list only tickets matching both (1.4.0's matchesFilters used some(), so it returned the union).",
   "handling": "sound",
   "observed": true,
   "evidence": "p3: ?status=open&priority=urgent -> only open urgent tickets (T-0001,T-0004,T-0007,T-0011), the resolved urgent T-0012 excluded; code diff some() -> every().",
   "spec": "none",
   "told": "yes",
   "told_where": "docs/api.md: \"Filters combine: a ticket is listed only when it matches every filter given, so `?status=open&priority=urgent` lists the open tickets that are urgent.\""
  },
  {
   "id": "U-16",
   "behaviour": "list --raw gains a fifth column, assignee, after title; an unassigned ticket has an empty fifth field; the weekly report's counts are identical to 1.4.0's.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "raw output: 'T-0001<TAB>open<TAB>normal<TAB>Assigned one<TAB>sam', 'T-0002<TAB>...<TAB>Unassigned one<TAB>', 'T-0003<TAB>...<TAB>Spaced name<TAB>ada li'; awk: 5 fields per line; weekly-report --json identical for new and base on the same file.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-17",
   "behaviour": "The table's ASSIGNEE column shows the name, or '-' for an unassigned ticket. An agent actually named '-' is accepted and shows the same as unassigned.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "list: 'T-0001 open normal sam ...', 'T-0002 open high - ...'; PUT {\"assignee\":\"-\"} -> 200.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-18",
   "behaviour": "show does not print the current assignee among its fields; assignment changes appear only in its History lines.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "show T-0001 fields: status, priority, requester, created, updated; History has 'ticket.assigned assignee dana -> sam'; show T-0002 has no assignee line.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-20",
   "behaviour": "POST /tickets and PATCH /tickets/:id refuse an assignee field as unknown (400 invalid 'unknown field: assignee').",
   "handling": "sound",
   "observed": true,
   "evidence": "p2: POST with assignee -> 400; PATCH {\"assignee\":\"dana\"} -> 400.",
   "spec": "none",
   "told": "yes",
   "told_where": "docs/api.md: \"Unknown fields in a request body are refused (400), so a misspelt field is never silently ignored.\""
  },
  {
   "id": "U-21",
   "behaviour": "200 application/json; charset=utf-8 with the whole ticket including assignee, for assignment, the no-op and unassignment; identical to a following GET.",
   "handling": "sound",
   "observed": true,
   "evidence": "p1/p2: PUT dana -> 200 ticket equal to GET; repeat -> 200 same ticket; PUT null -> 200 assignee null; content-type application/json; charset=utf-8.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-22",
   "behaviour": "No delivered document mentions assignment: docs/api.md, README.md, CHANGELOG.md and docs/decisions are byte-identical to the base; package.json version is still 1.4.0; README still says list --raw has four columns (id, status, priority, title).",
   "handling": "poor",
   "observed": true,
   "evidence": "diff -rq base product: only src/ files and test/assignment.test.js differ; grep -i assign in docs, README, CHANGELOG: nothing about the feature.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "show leaves the data file untouched with --data and with DATA_FILE.",
   "handling": "sound",
   "observed": true,
   "evidence": "cp t.json copy.json; show T-0001 / T-0002 with --data, show T-0003 with DATA_FILE; cmp after each -> identical.",
   "spec": "none",
   "told": "yes",
   "told_where": "README.md: \"`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.\""
  },
  {
   "id": "U-27",
   "behaviour": "show's History lists the entries oldest first in the audit API's order, including 'lee ticket.assigned assignee dana' and 'kim ticket.assigned assignee dana -> sam'; the current assignee is not shown as a field.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "show T-0001 history: created, lee assigned dana, kim dana -> sam, matching GET /tickets/T-0001/audit order before the stop.",
   "spec": "none",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "status and priority filters together now intersect instead of union (matchesFilters some() -> every())",
   "where": "src/tickets/query.js matchesFilters",
   "worth": "value",
   "why": "The request requires every filter to match; this also fixes 1.4.0's disagreement with docs/api.md. It changes an observable result of an existing query, unannounced in the CHANGELOG."
  },
  {
   "what": "assignee appended as a fifth column of list --raw",
   "where": "src/format.js RAW_COLUMNS",
   "worth": "neutral",
   "why": "Not asked (only the listing); position-reading weekly report unaffected, but README still documents four columns."
  },
  {
   "what": "Notification key per agent (ticket.assigned:<id>:<agent>)",
   "where": "src/store.js assign",
   "worth": "value",
   "why": "Keeps a pending notice for one agent from swallowing the next agent's notice."
  }
 ],
 "spec_notes": "none",
 "tests_notes": "The new tests each cover several behaviours: test 1 checks assign, reassign, unassign, the actor and the audit changes together; test 2 bundles the resolved-ticket conflict, the 404, and three validation cases; test 5 bundles the agent filter, the unassigned filter, assignee+priority, and the status+priority intersection. Test 3 compares whole ticket bodies with deepEqual, which relies on the manual clock not moving; test 4 relies on the outbox key including the agent (another correct build that sends both notices a different way would still pass, but one that notifies inside the PUT and never uses the outbox would fail). Nothing tests unassigning a resolved or closed ticket (S-9 broke without a failure), closed tickets at all, in_progress assignment, acceptance of a 64-character name, updated, the data file round trip, or anything in the command line (there is no CLI test file).",
 "maintainer": "The documents: README, docs/api.md and the CHANGELOG describe the service as if assignment did not exist and still promise four raw columns, so the next person learns the feature only from the code and the tests. The quiet change of matchesFilters from some() to every() alters an existing query's result with no note, and S-9 (no unassign on resolved/closed) has no test, so a refactor of the state check in TicketStore.assign could drop it unnoticed."
}
```

## Audit of delivery Y

```json
{
 "code": "Y",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies/devDependencies; diff -rq against base shows package.json unchanged; service started and served with plain node",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47311 npm start -> log \"tickets listening on 47311\"; GET /health -> 200 {\"status\":\"ok\"}",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "PUT /tickets/T-0001/assignee {\"assignee\":\"dana\"} -> 200, body assignee \"dana\"; GET /tickets/T-0001 -> assignee \"dana\"",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":null} on T-0001 (assigned dana) -> 200, assignee null; GET shows null",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/store.js assign: `if (ticket.assignee === assignee || assignee === null) return { ...ticket };` -> \"a ticket is assigned, reassigned and unassigned...\" fails (plus the already-failing notification test); restored, suite back to 121 pass / 1 fail"
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":\"\"} -> 400 invalid \"assignee must not be empty\"; assignee stayed null",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "65 a's on unassigned T-0002 -> 400 \"at most 64 characters\", assignee stayed null; 64 a's -> 200 stored; 65 again -> 400, assignee kept the 64-char name",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "open T-0001: assign dana 200, unassign 200; in_progress T-0002: assign kim 200, unassign 200, assign dana 200",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "resolved T-0002 (dana): PUT lee -> 409 conflict \"ticket T-0002 is resolved: only open and in-progress tickets can be assigned\"; closed: same 409; ticket, updated, audit and outbox byte-identical before/after",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/store.js assign: `if (!isActive(ticket.status) && assignee === null) {` -> \"only open and in-progress tickets can be assigned, and errors use the envelope\" fails; restored, suite back to 121/1"
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "resolved and closed T-0002 (dana): PUT null -> 409 conflict; assignee still dana, audit/outbox unchanged",
   "spec": "none",
   "proved": "passes",
   "proved_by": "src/store.js assign: `if (!isActive(ticket.status) && assignee !== null) {` (unassign of resolved/closed allowed) -> suite unchanged at 121 pass / 1 fail (only the pre-existing notification failure); restored"
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "PUT dana twice on T-0001: same body, updated unchanged (…:01.803Z), no audit entry; with worker on, notify file stayed at 2 lines after the repeat",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/store.js: deleted `if (ticket.assignee === assignee) return { ...ticket };` -> \"assigning the agent a ticket already has changes nothing\" fails; restored, suite back to 121/1"
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "assignee field present on POST /tickets (201), GET /tickets/:id, every item of GET /tickets, PATCH response, transition responses and PUT responses",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> assignee null; after unassign -> null; tickets from an old data file load with null",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "wrong",
   "observed": true,
   "evidence": "NOTIFY_FILE + WORKER_INTERVAL_MS=100: create (requester maria@example.com), PUT {\"assignee\":\"dana\"}; delivered line {\"type\":\"ticket.assigned\",\"to\":\"maria@example.com\",\"subject\":\"[T-0001] Assigned to you\"}; dana is never notified, the requester is told it is assigned to them",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": "",
   "rerun": true
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee=dana -> T-0001,T-0002,T-0006,T-0009 only (all dana, incl. closed)",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: `filters.assignee = assignee === '' ? null : undefined;` -> \"the assignee filter keeps an agent...\" fails; restored, suite back to 121/1"
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee= -> T-0003,T-0005,T-0007,T-0008 only (all null)",
   "spec": "none",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: `filters.assignee = assignee === '' ? undefined : assignee;` -> \"the assignee filter keeps an agent...\" fails; restored, suite back to 121/1"
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "?assignee=dana&status=open -> 3 open dana tickets; &status=closed -> T-0002; ?assignee=&status=resolved -> T-0003; ?assignee=dana&status=open&priority=urgent -> T-0006 only; ?assignee=dana&priority=normal -> T-0001,T-0002,T-0009",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "node bin/tickets.js --data FILE list -> ASSIGNEE column after PRIORITY with names (\"dana\", \"ada li\") and \"-\" for unassigned; list --raw has assignee as 5th field",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "existing test files pass; weekly-report --json counts identical to the base script on the same file; CLI show/list work; old data file loads; status/priority/cursor listing works",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "diff -rq base product: no existing test file differs; all their tests pass in npm test (the one failure is in the new assignment.test.js)",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "test/assignment.test.js, 5 node:test tests, ran in npm test",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) ran 122 tests including the 5 in assignment.test.js; exit 1 because one new test fails",
   "spec": "none",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "409 conflict in the error envelope naming the status for every assign/unassign on resolved or closed, including no-op requests (current agent again, null on unassigned); assignee, updated, audit and outbox unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "resolved/closed T-0002: PUT lee, dana, null -> 409 x3, audit and outbox byte-identical; resolved unassigned T-0003: PUT null and dana -> 409",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "400 invalid for {}, 5, {}, [], true, extra field, [] body, empty body and non-JSON; unknown id 404 not_found; a body with byte 0xFF is accepted and stored with U+FFFD (\"da\\ufffdna\")",
   "handling": "acceptable",
   "observed": true,
   "evidence": "each malformed body -> 400 invalid with field message; PUT /tickets/T-9999/assignee -> 404; 0xFF body -> 200 assignee \"da�na\" (same lossy decoding as title in the base)",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "trimmed; whitespace-only refused as empty; tab, newline and other control characters refused 400 \"single line of text\"; 64-char limit applied after trimming, like requester; filter matches the stored trimmed form",
   "handling": "sound",
   "observed": true,
   "evidence": "\"   \" -> 400; \"  dana  \" -> stored \"dana\"; \"da\\tna\", \"da\\nna\", \"da\\u0007na\" -> 400; \"  \"+64 a's+\"  \" -> 200; ?assignee=dana lists the trimmed one",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "one audit entry per real change, action ticket.assigned for both assign and unassign, actor from X-Actor or system, changes {assignee:{from,to}}; no entry for a repeat",
   "handling": "sound",
   "observed": true,
   "evidence": "audit after dana (X-Actor lee), dana again, null (sam), dana (no header): entries lee null->dana, sam dana->null, system null->dana",
   "spec": "none",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-5",
   "behaviour": "assignment and unassignment set updated; a repeated assignment leaves it unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "updated 01.785 -> 01.803 on assign, stays 01.803 on repeat, 01.828 on unassign",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-6",
   "behaviour": "unassigning an unassigned ticket returns 200 with the unchanged ticket, same updated, no audit entry, no notification; same for a repeated unassign",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0008: PUT null twice -> updated unchanged, audit and outbox byte-identical; assign/unassign/unassign -> last left updated, audit and outbox unchanged",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "a ticket.assigned event is delivered through the outbox after the PUT with subject \"[T-0001] Assigned to you\" and a body naming id and title, but `to` is the ticket's requester, not the agent; no dead events",
   "handling": "poor",
   "observed": true,
   "evidence": "last line of NOTIFY_FILE: {\"type\":\"ticket.assigned\",\"to\":\"maria@example.com\",\"subject\":\"[T-0001] Assigned to you\",...}; outbox sent shows to maria@example.com",
   "spec": "none",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-8",
   "behaviour": "one event per assignment with key ticket.assigned:<id>:<agent>, so successive assignments are not dropped (re-assigning dana while her event is pending is deduplicated); but every event goes to the requester, so neither dana nor lee is ever notified",
   "handling": "poor",
   "observed": true,
   "evidence": "worker off: dana, lee, null, dana -> pending keys ticket.assigned:T-0009:dana and :lee, both to r9@x; worker on: after delivery, assigning lee again delivered a new event, to the requester",
   "spec": "none",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-11",
   "behaviour": "assignee survives restart; a base-version file (no assignee field) loads with assignee null, version unchanged; assignee 5 refused at start naming tickets[0].assignee; a 65-character or tab-holding assignee in the file is accepted at start",
   "handling": "acceptable",
   "observed": true,
   "evidence": "SIGTERM + restart on a.json -> T-0010 \"ada li\", T-0001 \"dana\"; base server wrote old.json, product loaded it with assignee null; bad5 -> exit 2 \"tickets[0].assignee is not a non-empty string\"; bad65 and badtab -> started listening",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-12",
   "behaviour": "assignee kept through in_progress, resolved, closed and reopen; ?assignee=dana keeps returning it; after reopen it can be reassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0018 dana -> in_progress/resolved/open all keep dana and appear in ?assignee=dana; PUT lee after reopen -> 200; closed T-0002 keeps dana and is in ?assignee=dana",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-13",
   "behaviour": "exact, case-sensitive, untrimmed match on the stored name; over-long value returns an empty page; repeated parameter uses the first value",
   "handling": "sound",
   "observed": true,
   "evidence": "?assignee=Dana -> []; ?assignee=%20dana -> []; 65 chars -> 200 []; ?assignee=dana&assignee=lee -> dana's tickets; lee&dana -> []",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-14",
   "behaviour": "cursor paging with the assignee filter returns every matching ticket once in id order",
   "handling": "sound",
   "observed": true,
   "evidence": "?assignee=dana&limit=2 over 3 pages -> T-0001,T-0002 | T-0006,T-0009 | T-0014,T-0016, next null; ?assignee= over 5 pages -> all 10 unassigned once",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-15",
   "behaviour": "status and priority together list the intersection (the base listed the union)",
   "handling": "sound",
   "observed": true,
   "evidence": "product ?status=open&priority=urgent -> T-0006,T-0011 only; base server on its own file -> T-0001..T-0004 (union)",
   "spec": "none",
   "told": "yes",
   "told_where": "docs/api.md: \"Filters combine: a ticket is listed only when it matches every filter given, so `?status=open&priority=urgent` lists the open tickets that are urgent.\""
  },
  {
   "id": "U-16",
   "behaviour": "list --raw appends assignee as a 5th tab-separated field, empty for unassigned; a name with a space stays in one field; weekly report counts identical to base",
   "handling": "sound",
   "observed": true,
   "evidence": "awk NF -> 18 lines of 5 fields; \"T-0010\\topen\\tlow\\tlow ticket\\tada li\"; weekly-report --json identical for product and base scripts",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-17",
   "behaviour": "ASSIGNEE column shows \"-\" for unassigned; an agent literally named \"-\" is accepted and shows the same",
   "handling": "acceptable",
   "observed": true,
   "evidence": "list table: T-0003 \"-\" , T-0010 \"ada li\"; PUT {\"assignee\":\"-\"} -> 200",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-18",
   "behaviour": "show does not print an assignee field; assignment changes only appear in its History lines",
   "handling": "acceptable",
   "observed": true,
   "evidence": "show T-0010 prints status, priority, requester, created, updated and history \"ticket.assigned  assignee sam -> ada li\"; show T-0003 has no assignee line",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-20",
   "behaviour": "POST /tickets and PATCH /tickets/:id refuse assignee as an unknown field",
   "handling": "sound",
   "observed": true,
   "evidence": "both -> 400 invalid \"unknown field: assignee\"",
   "spec": "none",
   "told": "yes",
   "told_where": "docs/api.md: \"Unknown fields in a request body are refused (400), so a misspelt field is never silently ignored.\""
  },
  {
   "id": "U-21",
   "behaviour": "200 with the whole ticket including assignee, content-type application/json; same for the no-op and for unassign",
   "handling": "sound",
   "observed": true,
   "evidence": "curl -i PUT -> HTTP/1.1 200, content-type application/json; charset=utf-8, body equal to GET",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-22",
   "behaviour": "no documentation changed: README, docs/api.md, CHANGELOG.md and package.json version (1.4.0) identical to the base; README still says raw columns are id, status, priority, title",
   "handling": "poor",
   "observed": true,
   "evidence": "diff -rq base product: only src files and the new test differ",
   "spec": "none",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "show leaves the data file byte-for-byte unchanged with --data and with DATA_FILE",
   "handling": "sound",
   "observed": true,
   "evidence": "cmp after list, show --data, DATA_FILE show -> identical",
   "spec": "none",
   "told": "yes",
   "told_where": "README.md: \"`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.\""
  },
  {
   "id": "U-27",
   "behaviour": "show history is oldest first and includes both assignment entries with actors, in the same order as GET /tickets/:id/audit; the current assignee is visible only as the last history line",
   "handling": "acceptable",
   "observed": true,
   "evidence": "T-0010 assigned \"ada li\" (X-Actor lee), \"sam\" (kim), \"ada li\" (kim): show lists lee ticket.assigned assignee ada li; kim ada li -> sam; kim sam -> ada li, matching the audit order",
   "spec": "none",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "GET /tickets filters now intersect (matchesFilters uses every instead of some)",
   "where": "src/tickets/query.js",
   "worth": "value",
   "why": "the base listed the union for status+priority, contrary to docs/api.md; needed for S-16"
  },
  {
   "what": "Outbox key for assignment includes the agent (ticket.assigned:<id>:<agent>)",
   "where": "src/store.js assign",
   "worth": "value",
   "why": "successive assignments to different agents are not deduplicated away"
  },
  {
   "what": "Data file loading checks the assignee is null or a non-empty string",
   "where": "src/persistence.js readTicket",
   "worth": "value",
   "why": "a hand-edited non-string assignee is refused at start with the record named"
  },
  {
   "what": "ticket.assigned notification template",
   "where": "src/templates.js",
   "worth": "neutral",
   "why": "needed for the notification; its wording \"assigned to you\" misleads because it is sent to the requester"
  }
 ],
 "spec_notes": "none",
 "tests_notes": "The five tests each bundle several behaviours: the first covers assign, reassign, unassign and audit actor/changes; the second covers the state rule, 404 and three validation cases; the fifth covers both assignee filters, a combined filter and the status+priority intersection. \"each new agent is notified through the outbox\" expects two pending ticket.assigned events with to = the agent names, which ties it to an outbox key that includes the agent; another correct build using the default type+ticket key (one pending notification, acceptable in the inventory) would fail it. It currently fails against this product. Nothing tests in_progress assignment, unassigning a resolved/closed ticket (S-9: breaking it left the suite unchanged), the 64-character acceptance, the CLI columns, persistence of assignee or the transitions keeping it.",
 "maintainer": "The notification recipient is a hard-coded argument in TicketStore.assign (ticket.requester), and the template says \"assigned to you\", so fixing who is told means deciding how an agent name maps to an address, which nothing documents. Assign and unassign share the ticket.assigned audit action and the raw CLI now has a fifth column that weekly-report reads by position, yet README and docs/api.md still describe the old service, so the next person has no written contract to change against."
}
```

## Audit of delivery Z

```json
{
 "code": "Z",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "cat package.json: no dependencies/devDependencies fields; service started and ran every probe with no node_modules present",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "`PORT=47977 WORKER_INTERVAL_MS=0 npm start` -> log 'npm notice run node src/server.js' and 'tickets listening on 47977'; curl localhost:47977/health -> {\"status\":\"ok\"}; lsof shows node src/server.js listening on 47977",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets then PUT /tickets/T-0001/assignee {\"assignee\":\"dana\"} -> 200 ticket with \"assignee\":\"dana\"; GET /tickets/T-0001 -> \"assignee\":\"dana\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":null} on T-0001 (assigned dana) -> 200 \"assignee\":null; GET -> \"assignee\":null",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): `if (ticket.assignee === assignee) return` -> `if (ticket.assignee === assignee || assignee === null) return`; 2 tests failed: 'a ticket is assigned, reassigned and unassigned...' and 'again: a ticket is assigned...'; restored, 127/127 pass"
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "T-0002 assigned lee; PUT {\"assignee\":\"\"} -> 400 {\"error\":{\"code\":\"invalid\",\"message\":\"assignee must not be empty\"}}; GET -> assignee still \"lee\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "PUT 64 x 'a' -> 200, assignee length 64; PUT 65 x 'b' -> 400 invalid 'assignee must be at most 64 characters'; GET -> assignee still the 64-character name",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "open T-0001: PUT dana -> 200, PUT null -> 200; T-0003 moved to in_progress: PUT dana -> 200 assignee dana, PUT null -> 200 assignee null",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "T-0004 assigned dana, moved to resolved: PUT lee -> 409 {\"error\":{\"code\":\"conflict\",\"message\":\"ticket T-0004 is resolved: only open and in-progress tickets can be assigned\"}}; after closed: PUT lee -> 409 same message naming closed; ticket JSON, audit length and /admin/outbox identical before and after",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): `if (!isActive(ticket.status)) {` -> `if (!isActive(ticket.status) && assignee === null) {`; 2 tests failed: 'only open and in-progress tickets can be assigned, and errors use the envelope' and its 'again:' copy; restored, 127/127 pass"
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "resolved T-0004 (assignee dana): PUT {\"assignee\":null} -> 409 conflict; closed: PUT null -> 409; GET -> assignee still dana; audit and outbox unchanged",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "src/store.js assign(): `if (!isActive(ticket.status)) {` -> `if (!isActive(ticket.status) && assignee !== null) {` (unassigning a resolved/closed ticket allowed); suite still 127/127 pass; restored, 127/127 pass"
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "T-0010 assigned dana; snapshot GET ticket, GET audit, GET /admin/outbox; PUT dana again -> 200; all three identical to the snapshot (updated unchanged, no audit entry, no new outbox event)",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): deleted the line `if (ticket.assignee === assignee) return { ...ticket };`; 2 tests failed: 'assigning the agent a ticket already has changes nothing' and its 'again:' copy; restored, 127/127 pass"
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "assignee present in the bodies of POST /tickets (null), PUT assignee, GET /tickets/:id, PATCH /tickets/:id (priority high -> \"assignee\":null), POST transition, and every item of GET /tickets (checked hasOwn on all 11 items)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> \"assignee\":null; after unassign -> null; tickets from a data file written by the base version load with assignee null",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "NOTIFY_FILE=probe-data/n.jsonl WORKER_INTERVAL_MS=100; create, PUT dana, wait 1s: last line {\"key\":\"ticket.assigned:T-0001:dana\",\"type\":\"ticket.assigned\",\"to\":\"dana\",\"subject\":\"[T-0001] Assigned to you\",\"body\":\"Ticket T-0001 \\\"VPN broken\\\" is now assigned to you.\"}; outbox pending 0 sent 2 dead 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": "",
   "rerun": true
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee=dana&limit=100 -> only tickets with assignee dana (T-0004 closed, T-0007, T-0008, T-0010, T-0011); lee/null/other tickets excluded",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: `filters.assignee = assignee === '' ? null : assignee;` -> `... ? null : undefined;` (agent filter ignored); 2 tests failed: 'the assignee filter keeps an agent or the unassigned...' and its 'again:' copy; restored, 127/127 pass"
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee=&limit=100 -> only tickets with assignee null (T-0001, T-0003, T-0005, T-0009); a ticket assigned the string \"null\" is excluded",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: `filters.assignee = assignee === '' ? null : assignee;` -> `assignee === '' ? undefined : assignee;` (empty filter ignored); 2 tests failed: 'the assignee filter keeps an agent or the unassigned...' and its 'again:' copy; restored, 127/127 pass"
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "assignee=dana&priority=high -> T-0003, T-0009 (both high, dana); assignee=&priority=low -> only unassigned low; assignee=dana&status=open&priority=low -> only open low dana; assignee=dana&status=closed -> T-0002 only",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "node bin/tickets.js --data probe-data/main.json list -> table header 'ID STATUS PRIORITY ASSIGNEE REQUESTER UPDATED TITLE' with 'lee', 'dana', 'ada li', '-' for unassigned; list --raw adds assignee as a fifth tab field",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "existing suite 127/127 passes; create/patch/transition/audit/outbox/worker/persistence/CLI show/list --status/weekly report all worked in probes; weekly-report --json on the same file gives identical counts with the base and new code; one deliberate change: status+priority together now intersect (base returned the union)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "cmp of every file in base/test against work/Z/test: no differences; npm test 127 pass 0 fail",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "test/assignment.test.js (5 node:test tests) and test/assignment-again.test.js (the same 5 tests with an 'again:' prefix) run and pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) output lists the assignment tests among the existing ones; 127 total",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Every assign, re-assign of the current agent, or unassign of a resolved or closed ticket (assigned or not) answers 409 conflict 'ticket T-n is <status>: only open and in-progress tickets can be assigned'; ticket (assignee, updated), audit and outbox stay as they were",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0004 dana -> in_progress -> resolved: PUT lee/dana/null -> 409 x3; closed: same 409 x3; ticket JSON, audit count and outbox JSON compared equal; unassigned resolved T-0005: PUT null -> 409, PUT dana -> 409, assignee null",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-2",
   "behaviour": "400 invalid for {}, number, object, array, true, unknown field x, body [], empty body, non-JSON; 404 not_found for T-9999; nothing changes. A body with the invalid UTF-8 byte 0xFF inside the name is accepted and stored with U+FFFD in its place",
   "handling": "acceptable",
   "observed": true,
   "evidence": "PUT {} -> 400 'assignee is required'; {\"assignee\":5}/{}/[]/true -> 400 'assignee must be a string'; {\"assignee\":\"dana\",\"x\":1} -> 400 'unknown field: x'; [] and '' -> 400 'request body must be a JSON object'; 'not json' -> 400; 0xFF -> 200 assignee code points 64 61 fffd 6e 61 and an audit entry; PUT /tickets/T-9999/assignee -> 404 not_found",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "Name trimmed before storing; whitespace-only refused as empty; tab and newline refused 'must be a single line of text'; 64 limit applied after trimming (same text() rule as requester); filter matches the stored trimmed form",
   "handling": "sound",
   "observed": true,
   "evidence": "PUT \"   \" -> 400 empty; \"  dana  \" -> 200 assignee \"dana\"; \"da\\tna\" and \"da\\nna\" -> 400; two spaces + 64 chars + two spaces -> 200 length 64; two spaces + 65 chars -> 400; GET /tickets?assignee=dana finds the trimmed one",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "One audit entry per real change, action ticket.assigned for both assignment and unassignment, actor from X-Actor or 'system', changes {assignee:{from,to}}; a repeated assignment records nothing",
   "handling": "sound",
   "observed": true,
   "evidence": "PUT dana (X-Actor lee), PUT dana again, PUT null (X-Actor sam), PUT dana (no header) -> audit after creation: 'lee ticket.assigned {from:null,to:dana}', 'sam ticket.assigned {from:dana,to:null}', 'system ticket.assigned {from:null,to:dana}'",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-5",
   "behaviour": "Assignment and unassignment set updated to the change time; a repeated assignment leaves it unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "updated 14:27:14.271 at create; after 1.1 s PUT dana -> 14:27:15.374; PUT dana again -> 14:27:15.374; after 1.1 s PUT null -> 14:27:16.479",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-6",
   "behaviour": "Unassigning an already-unassigned open ticket answers 200 with the unchanged ticket; no updated change, no audit entry, no notification, also after assign-unassign-unassign",
   "handling": "sound",
   "observed": true,
   "evidence": "WORKER_INTERVAL_MS=0: create, PUT null twice -> 200 assignee null, ticket/audit/outbox equal to the snapshot after creation; assign dana, unassign, unassign again -> ticket/audit/outbox equal to the snapshot after the first unassign",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "Outbox event type ticket.assigned to the agent's name, key ticket.assigned:<id>:<agent>, delivered by the worker after the PUT returns; subject '[T-n] Assigned to you', body names id and title",
   "handling": "sound",
   "observed": true,
   "evidence": "NOTIFY_FILE + WORKER_INTERVAL_MS=100: last line {\"type\":\"ticket.assigned\",\"to\":\"dana\",\"subject\":\"[T-0001] Assigned to you\",\"body\":\"Ticket T-0001 \\\"VPN broken\\\" is now assigned to you.\"}; outbox dead []",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-8",
   "behaviour": "The outbox key includes the agent, so each agent gets its own pending event; a repeat for an agent whose event is still pending is merged into it; after delivery a new assignment enqueues a new event",
   "handling": "sound",
   "observed": true,
   "evidence": "worker off: dana, lee, null, dana -> pending assigned events dana|ticket.assigned:T-0001:dana and lee|ticket.assigned:T-0001:lee; restart with worker 100 ms: both sent, then PUT lee -> new pending event for lee. With worker on, dana,lee,dana,lee spaced 0.5 s -> four deliveries dana,lee,dana,lee",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-11",
   "behaviour": "Assignee survives a SIGTERM restart; a data file written by the base version (no assignee field) loads with assignee null and can be assigned; a file assignee of 5 or '' is refused at start naming tickets[0].assignee; a 65-character, tab-containing or space-padded assignee in the file is accepted",
   "handling": "acceptable",
   "observed": true,
   "evidence": "DATA_FILE restart -> GET shows assignee dana; base server wrote old.json (no 'assignee' text), new server lists T-0001:null T-0002:null and PUT works; bad-number/bad-empty -> exit 2 'tickets[0].assignee is not a non-empty string'; bad-65chars, bad-control ('da\\tna'), bad-spaces started and served those values (requester of 65 chars in a file is accepted the same way)",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-12",
   "behaviour": "Assignee kept through in_progress, resolved, reopen to open and closed; the agent filter still returns the ticket and the empty filter does not; a reopened ticket can be reassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "after in_progress/resolved/open: assignee dana, in ?assignee=dana true, in ?assignee= false; reopened PUT lee -> 200 assignee lee; second ticket through closed -> assignee dana",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-13",
   "behaviour": "Exact, case-sensitive match on the stored name; the filter value is not trimmed; an over-long value gives an empty page (200); a repeated parameter uses the first value",
   "handling": "acceptable",
   "observed": true,
   "evidence": "?assignee=Dana -> 200 []; ?assignee=%20dana -> 200 []; ?assignee=<65 z> -> 200 []; ?assignee=dana&assignee=lee -> dana's tickets; ?assignee=lee&assignee=dana -> [] (no lee tickets); ?assignee=ada+li and ada%20li both find 'ada li'",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-14",
   "behaviour": "Cursor paging keeps the assignee filter: every matching ticket once, in id order",
   "handling": "sound",
   "observed": true,
   "evidence": "?assignee=dana&limit=2 following next: 3 pages T-0002 T-0003 T-0005 T-0007 T-0009 T-0011 = single-page result; ?assignee=&limit=2: 2 pages T-0004 T-0006 T-0008 T-0010 = single-page result",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-15",
   "behaviour": "status and priority together now list the intersection (matchesFilters some -> every); the base version listed the union",
   "handling": "sound",
   "observed": true,
   "evidence": "open/low, open/urgent, resolved/urgent; GET ?status=open&priority=urgent: new -> T-0002 only; base server on the same steps -> T-0001, T-0002, T-0003",
   "spec": "silent",
   "told": "yes",
   "told_where": "docs/api.md: \"Filters combine: a ticket is listed only when it matches every filter given, so `?status=open&priority=urgent` lists the open tickets that are urgent.\""
  },
  {
   "id": "U-16",
   "behaviour": "list --raw appends the assignee as a fifth tab-separated field after title, empty for unassigned; the weekly report's counts are unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "list --raw: 'T-0004\\topen\\tlow\\tp1\\tada li' 5 fields; unassigned 'T-0006\\topen\\thigh\\tp3\\t' 5 fields; weekly-report --json identical with base and new code: total 12, open 11, closed 1, low 6, normal 3, high 3",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-17",
   "behaviour": "The list table has an ASSIGNEE column after PRIORITY; an unassigned ticket shows '-'",
   "handling": "sound",
   "observed": true,
   "evidence": "node bin/tickets.js --data probe-data/main.json list -> 'T-0006  open    high      -         pat ...' beside 'T-0003  open    high      dana ...'",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-18",
   "behaviour": "show does not print an assignee field; assignment changes appear only in its History lines, and an unassigned ticket shows no assignee state",
   "handling": "acceptable",
   "observed": true,
   "evidence": "node bin/tickets.js --data FILE show T-0003 (assigned dana) -> fields status, priority, requester, created, updated only; History has 'system  ticket.assigned  assignee dana'",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-20",
   "behaviour": "POST /tickets and PATCH /tickets/:id refuse an assignee field as unknown",
   "handling": "sound",
   "observed": true,
   "evidence": "POST /tickets {title,requester,assignee:'dana'} -> 400 'unknown field: assignee'; PATCH {assignee:'dana'} -> 400 'unknown field: assignee'",
   "spec": "silent",
   "told": "yes",
   "told_where": "docs/api.md: \"Unknown fields in a request body are refused (400), so a misspelt field is never silently ignored.\""
  },
  {
   "id": "U-21",
   "behaviour": "200 application/json; charset=utf-8 with the whole ticket including assignee, for assignment, the no-op and unassignment",
   "handling": "sound",
   "observed": true,
   "evidence": "PUT dana -> 200 ctype application/json; charset=utf-8, body equal to the following GET; repeat -> 200 the same body; PUT null -> 200 ticket with assignee null",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-22",
   "behaviour": "No delivered document changed: docs/api.md has no endpoint, field, filter, audit action or notification; README.md still says list --raw has the columns id, status, priority, title; CHANGELOG.md unchanged; package.json version still 1.4.0; no decision record",
   "handling": "poor",
   "observed": true,
   "evidence": "diff -rq base product: only src files, docs/spec.md and the two test files differ; grep -i assign README.md docs/api.md docs/operations.md CHANGELOG.md -> no hits",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-26",
   "behaviour": "show leaves the data file byte-for-byte unchanged with --data and with DATA_FILE",
   "handling": "sound",
   "observed": true,
   "evidence": "copied main.json; `show T-0012 --data` and `DATA_FILE=... show T-0005` -> Buffer.equals with the copy true after each",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.\""
  },
  {
   "id": "U-27",
   "behaviour": "show's History lists creation and both assignment entries oldest first with their actors, in the audit API's order; the current assignee is visible only as the last history line ('assignee dana -> sam')",
   "handling": "acceptable",
   "observed": true,
   "evidence": "assign dana (X-Actor lee), then sam (X-Actor kim); show T-0012 -> 'system ticket.created ...', 'lee ticket.assigned assignee dana', 'kim ticket.assigned assignee dana -> sam'; GET /tickets/T-0012/audit same order",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "assignee as a fifth column of list --raw",
   "where": "src/format.js RAW_COLUMNS",
   "worth": "value",
   "why": "scripts can read the assignee; appended after title so weekly-report.js counts are unchanged (observed); undocumented in README, which still names four columns"
  },
  {
   "what": "load-time check of a ticket's assignee in the data file",
   "where": "src/persistence.js readTicket",
   "worth": "value",
   "why": "refuses a non-string or empty assignee at start, and reads files without the field as null"
  },
  {
   "what": "test/assignment-again.test.js, a copy of test/assignment.test.js with 'again:' prefixed to each name",
   "where": "test/assignment-again.test.js",
   "worth": "liability",
   "why": "doubles the new tests without adding a check; two files to keep in step on every change"
  }
 ],
 "spec_notes": "docs/spec.md restates each sentence of the request six times (shall / acceptance / rationale / non-goal / traceability / review note) and decides nothing: it is silent on every unstated condition (status code for resolved/closed tickets, audit action, outbox key per agent, trimming, filter matching, raw column, documents). It does not contradict the request. The built behaviour makes choices the spec never records: 409 for resolved/closed, unassignment audited as ticket.assigned, outbox key including the agent, assignee appended to list --raw, and the status+priority filter changed from union to intersection.",
 "tests_notes": "The two new files are identical apart from the 'again:' prefix, so each assignment behaviour is checked twice and every mutation fails two tests. Tests bundle several behaviours: the first test covers assign, reassign, unassign and audit actor/changes; the second covers the resolved conflict, 404 and three validation cases; the filter test covers assignee=<agent>, assignee=, a combination and the status+priority intersection. Not covered: unassigning a resolved/closed ticket (S-9 mutant passes), closed tickets, in_progress tickets, a 64-character name, list items' assignee, the CLI table and raw output, persistence of assignee, the notification template. Tests pin ids T-0001.. and the agent names, and the no-op test deepEquals the whole ticket; they would pass on another correct build that uses the same 'pending' outbox report, but the notification test depends on one pending event per agent (a build that sends inside the PUT or keys by ticket would fail it).",
 "maintainer": "The behaviour is spread thinly across validate.js, query.js, store.js, persistence.js, format.js and templates.js, with no document saying what the endpoint returns, which audit action it writes or what list --raw now prints, so the next person must read the code to learn the contract. The silent change of matchesFilters from some to every alters an existing listing result and is recorded nowhere but the code and one test line; and the duplicated test file must be edited in step."
}
```

