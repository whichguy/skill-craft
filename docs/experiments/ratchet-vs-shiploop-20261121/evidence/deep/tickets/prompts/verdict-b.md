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

- **D-1** (low) An assignee containing invalid UTF-8 is silently altered and accepted. Expected: 400 invalid with the ticket, audit and outbox unchanged. — X: present; Y: absent; Z: present
- **D-2** (low) A malformed UTF-8 byte in the assignee filter matches the agent whose name holds U+FFFD. Expected: 400 invalid or an empty page. — X: present; Y: present; Z: present

## Audit of delivery X

```json
{
 "code": "X",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies/devDependencies fields; the service, CLI and tests ran with no node_modules present",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=47811 ... npm start -> log 'npm notice run node src/server.js' then 'tickets listening on 47811'; requests to 127.0.0.1:47811 answered",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> T-0001 assignee null; PUT /tickets/T-0001/assignee {\"assignee\":\"dana\"} -X-Actor lee -> 200 ticket with assignee \"dana\"; GET /tickets/T-0001 -> assignee \"dana\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "PUT /tickets/T-0001/assignee {\"assignee\":null} (X-Actor sam) -> 200 assignee null, updated moved; audit ticket.unassigned {from:dana,to:null}",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): 'if (ticket.assignee === assignee) return' changed to '... || assignee === null) return' (unassign becomes a no-op); npm test -> 1 fail: TC-1. Restored; suite back to 123/123 pass"
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":\"\"} -> 400 invalid 'assignee must not be empty' on unassigned T-0002 and later on T-0002 assigned to a 64-char name; GET shows assignee unchanged each time",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "PUT 65 x 'a' -> 400 'assignee must be at most 64 characters', ticket still null; PUT 64 x 'a' -> 200 assigned; PUT 65 x 'a' again -> 400, GET still the 64-char name",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "T-0005 open: PUT dana -> 200; transition in_progress; PUT null -> 200 assignee null; PUT dana -> 200. T-0001 (open): assign/unassign/assign all 200",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "T-0005 resolved (assignee dana): PUT lee -> 409 conflict 'ticket T-0005 is resolved and cannot change assignee'; closed: same 409 'is closed'; GET unchanged (assignee dana, same updated), audit count 6 then 7 (only the close transition), outbox 4 events for the ticket unchanged. T-0007 resolved unassigned: PUT dana -> 409, assignee stays null",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): 'if (!isActive(ticket.status)) throw' -> 'if (!isActive(ticket.status) && assignee === null) throw' (assignment of resolved/closed allowed); npm test -> 1 fail: TC-2. Restored; 123/123 pass"
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "T-0005 resolved and then closed, assignee dana: PUT {\"assignee\":null} -> 409 conflict both times; GET still assignee dana, audit and outbox unchanged",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): 'if (!isActive(ticket.status)) throw' -> 'if (!isActive(ticket.status) && assignee !== null) throw' (unassign of resolved/closed allowed); npm test -> 1 fail: TC-2. Restored; 123/123 pass"
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "T-0001 assigned dana (updated .612); PUT dana again -> 200 same body, updated still .612; audit showed no entry between seq 2 (assigned) and seq 3 (unassigned); /admin/outbox had one ticket.assigned for that assignment. Same for T-0023 kim repeated",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign(): removed the line 'if (ticket.assignee === assignee) return { ...ticket };'; npm test -> 3 fail: TC-1, TC-4, TC-5. Restored; 123/123 pass"
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "assignee present in POST /tickets (201), GET /tickets/:id, every item of GET /tickets, PATCH /tickets/T-0023 {title} (200, assignee dana), POST /transition (200, assignee dana/zed), PUT /assignee (200); also after restart from a file and from a legacy file",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> \"assignee\":null; after unassign -> null; tickets from a base-version file load with assignee null",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "NOTIFY_FILE + WORKER_INTERVAL_MS=100: PUT T-0023 dana -> n.jsonl line {type:ticket.assigned, to:dana, subject:'[T-0023] Assigned to you', body:'Ticket T-0023 \"VPN down\" was assigned to you.'}; outbox pending 0, dead 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee=dana -> T-0001, T-0005, T-0006 (all assignee dana, none other) of 8 tickets",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: \"filters.assignee = params.get('assignee') || null\" -> \"params.get('assignee') ? undefined : null\" (named filter ignored); npm test -> 1 fail: TC-3. Restored; 123/123 pass"
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee= -> T-0003, T-0007 (both assignee null) only",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: \"|| null\" -> \"|| undefined\" (empty filter ignored); npm test -> 1 fail: TC-3. Restored; 123/123 pass"
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "?assignee=dana&status=open -> T-0001,T-0006 (closed T-0005 dropped); ?assignee=dana&status=resolved -> []; ?assignee=&status=resolved -> T-0007; ?assignee=dana&priority=low -> []; ?assignee=dana&priority=normal&status=open -> T-0001,T-0006; ?status=resolved&priority=urgent&assignee= -> only T-0021",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "node bin/tickets.js --data run/cli.json list -> header 'ID STATUS PRIORITY REQUESTER UPDATED ASSIGNEE TITLE', rows 'sam', 'ada li', '—'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "original suite passes unmodified; create, PATCH, transitions (incl. reopen, closed final), audit, outbox/worker delivery, restart from data file, 404/405-style router answers, body limit 400, weekly report counts identical to base version on same file",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "cmp of each test/*.test.js and test/helpers.js against base: only test/assignment.test.js differs (new); npm test 123/123 pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "test/assignment.test.js uses node:test, 6 tests TC-1..TC-6, all pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) output lists TC-1..TC-6 alongside the existing suites",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Any assignee PUT on a resolved or closed ticket (other agent, same agent, null, null on an unassigned ticket, agent on an unassigned ticket) answers 409 {error:{code:conflict, message:'ticket T-xxxx is resolved|closed and cannot change assignee'}}; assignee, updated, audit and outbox unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0005 resolved: PUT lee/dana/null -> 409 x3; closed: same; T-0007 resolved unassigned: PUT null and dana -> 409; GET/audit count/outbox count unchanged",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"It answers 400 for invalid input, 404 for an unknown ticket, and 409 for a resolved or closed ticket.\""
  },
  {
   "id": "U-2",
   "behaviour": "{}, number, object, array -> 400 invalid 'assignee must be a string'; extra field -> 400 'unknown field: x'; [], empty body, JSON string, null -> 400 'request body must be a JSON object'; non-JSON -> 400 'not valid JSON'; unknown id -> 404 not_found. Invalid UTF-8 byte 0xFF is accepted and stored as U+FFFD (same as existing title/requester handling)",
   "handling": "acceptable",
   "observed": true,
   "evidence": "PUT /tickets/T-0002/assignee with each body; T-9999 -> 404; invalid UTF-8 -> 200 assignee 'da\\uFFFDna' (POST /tickets with 0xFF in title also 201 with U+FFFD)",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"It answers 400 for invalid input, 404 for an unknown ticket, and 409 for a resolved or closed ticket.\"; \"Unknown fields in a request body are refused (400), so a misspelt field is never silently ignored.\""
  },
  {
   "id": "U-3",
   "behaviour": "Trimmed; whitespace-only -> 400 empty; tab, newline, BEL -> 400 'single line of text'; 64 chars padded with spaces accepted (limit counted after trim); limit counts Unicode code points (64 emoji accepted) while requester counts UTF-16 units (33 emoji refused); filtering uses the trimmed stored form",
   "handling": "acceptable",
   "observed": true,
   "evidence": "PUT '   ' -> 400; '  dana  ' -> 200 'dana'; 'da\\tna','da\\nna','da\\u0007na' -> 400; '  '+64b+'  ' -> 200; 64 x U+1F600 -> 200, 65 -> 400; requester 33 x U+1F600 -> 400; GET ?assignee=dana lists the trimmed one",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A name is trimmed and must contain 1–64 Unicode code points on a single line.\""
  },
  {
   "id": "U-4",
   "behaviour": "One audit entry per real change: ticket.assigned / ticket.unassigned, actor from X-Actor or 'system', changes {assignee:{from,to}}; no entry for repeated assignment or repeated unassign",
   "handling": "sound",
   "observed": true,
   "evidence": "GET /tickets/T-0001/audit: seq2 assigned lee null->dana, seq3 unassigned sam dana->null, seq4 assigned system null->dana; no entries for the repeats",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"An effective change updates the ticket and records who made the change in its audit history.\"; \"Actions include `ticket.created`, `ticket.updated`, `ticket.transitioned`, `ticket.assigned`, and `ticket.unassigned`.\"; \"Repeating the current assignment leaves the ticket, audit and outbox as they were.\""
  },
  {
   "id": "U-5",
   "behaviour": "Assignment and unassignment set updated to the change time; a repeated assignment leaves it",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0001 updated .593 -> PUT dana .612 -> PUT dana .612 -> PUT null .638 -> PUT null .638",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"`updated` | when it last changed; a request that changes nothing leaves it as it was\"; \"Repeating the current assignment leaves the ticket, audit and outbox as they were.\""
  },
  {
   "id": "U-6",
   "behaviour": "Unassigning an already-unassigned open ticket answers 200 with the unchanged ticket: same updated, no audit entry, no notification",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0006 new: PUT null -> 200 updated equal to created; T-0001 after unassign: PUT null again -> 200 same updated, audit had no extra entry, outbox no unassign events",
   "spec": "silent",
   "told": "yes",
   "told_where": "docs/decisions/0009-ticket-assignment.md: \"An unchanged assignment leaves the ticket, audit, and outbox untouched.\""
  },
  {
   "id": "U-7",
   "behaviour": "Outbox event type ticket.assigned, to = the agent name, delivered by the worker after the PUT returns; subject '[T-x] Assigned to you', body 'Ticket T-x \"title\" was assigned to you.'; no dead events. Unassignment sends nothing",
   "handling": "sound",
   "observed": true,
   "evidence": "WORKER_INTERVAL_MS=100 NOTIFY_FILE=run/n.jsonl; PUT T-0023 dana; after 1 s last line of n.jsonl as described; /admin/outbox pending 0 sent 52 dead 0",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"The worker sends each new assignee an assignment notification.\""
  },
  {
   "id": "U-8",
   "behaviour": "Each effective assignment gets its own key ticket.assigned:<id>:<audit seq>, so no notice is dropped while earlier ones are pending",
   "handling": "sound",
   "observed": true,
   "evidence": "Worker off: T-0022 dana, lee, null, dana -> pending events to dana (key :55), lee (:56), dana (:58); after restart with worker all three sent; PUT lee again -> new event key :61 delivered to lee",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/decisions/0009-ticket-assignment.md: \"The audit sequence gives each assignment its own event key, including repeated assignments separated by a change.\""
  },
  {
   "id": "U-11",
   "behaviour": "Assignee persists across SIGTERM restart; a base-version file (no assignee field) loads with assignee null; an invalid assignee in the file (5, 65 chars, empty, tab) refuses to start, exit 2, message naming tickets[1].assignee; a padded name is silently trimmed on load",
   "handling": "sound",
   "observed": true,
   "evidence": "restart -> GET T-0001 assignee dana; base server wrote run/old.json, product started on it -> both tickets assignee null; edited files -> 'cannot start: ...: tickets[1].assignee must be a string' etc.",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/decisions/0009-ticket-assignment.md: \"Store a nullable assignee in each ticket and interpret missing assignees as null when loading earlier data files.\"; docs/operations.md: \"A file it cannot use stops it with a message that names the record\""
  },
  {
   "id": "U-12",
   "behaviour": "Assignee is kept through in_progress, resolved, closed and reopen; ?assignee=<name> keeps returning the ticket; after reopen it can be reassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0008 zed: in_progress and resolved -> assignee zed, ?assignee=zed -> T-0008, ?assignee= excludes it; transition open -> assignee zed; PUT lee -> 200. T-0005 closed keeps dana",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-13",
   "behaviour": "Exact, case-sensitive match on the stored (trimmed) name; filter value not trimmed; an over-long value returns an empty page (200); repeated assignee uses the first value; a whitespace-only value matches nothing (not the unassigned)",
   "handling": "acceptable",
   "observed": true,
   "evidence": "?assignee=Dana -> []; ?assignee=%20dana -> []; 65 chars -> 200 []; dana&lee -> dana's; lee&dana -> lee's; ?assignee=%20 -> []",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"`assignee` | only tickets assigned to this exact name. Use `assignee=` to list unassigned tickets\""
  },
  {
   "id": "U-14",
   "behaviour": "Filter applied before cursor pagination: each matching ticket once, in id order",
   "handling": "sound",
   "observed": true,
   "evidence": "?assignee=dana&limit=2 pages: T-0001,T-0005 | T-0006,T-0009 | T-0011,T-0013 | T-0015,T-0017 next null; ?assignee= pages: T-0003,T-0007 | T-0010,T-0012 | T-0014,T-0016 | T-0018",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"Otherwise, pass it as `cursor`, with the same filters, to get the next page.\""
  },
  {
   "id": "U-15",
   "behaviour": "status+priority now intersect (base used any-match); ?status=open&priority=urgent lists only the open/urgent ticket",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0019 open/low, T-0020 open/urgent, T-0021 resolved/urgent: ?status=open&priority=urgent -> T-0020 only (base src/tickets/query.js used given.some)",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"Filters combine: a ticket is listed only when it matches every filter given, so `?status=open&priority=urgent` lists the open tickets that are urgent.\""
  },
  {
   "id": "U-16",
   "behaviour": "list --raw appends assignee as a fifth tab-separated field, empty for unassigned; names with spaces kept; weekly report counts identical to the base version",
   "handling": "sound",
   "observed": true,
   "evidence": "list --raw: 5 fields per line ('...\\tsam', '...\\tada li', '...\\t'); weekly-report --json output byte-identical between product and base on run/cli.json",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"`list --raw` prints one tab-separated line per ticket in the order id, status, priority, title, assignee. The assignee field is empty for unassigned tickets.\""
  },
  {
   "id": "U-17",
   "behaviour": "ASSIGNEE column before TITLE; unassigned shown as an em dash",
   "handling": "sound",
   "observed": true,
   "evidence": "list -> T-0003 row shows '—'; assigned rows show the name",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"`list` prints a table with an assignee column. An em dash indicates an unassigned ticket.\""
  },
  {
   "id": "U-18",
   "behaviour": "show prints an 'assignee' line, the name or an em dash for unassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "show T-0001 -> 'assignee   sam'; show T-0003 -> 'assignee   —'",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-20",
   "behaviour": "POST /tickets and PATCH /tickets/:id refuse an assignee field with 400 invalid 'unknown field: assignee'",
   "handling": "sound",
   "observed": true,
   "evidence": "POST {title,requester,assignee:dana} -> 400; PATCH T-0023 {assignee:lee} -> 400",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-21",
   "behaviour": "200, application/json; charset=utf-8, the whole ticket including assignee, equal to a following GET; the no-op and unassign answer the same way",
   "handling": "sound",
   "observed": true,
   "evidence": "curl -i PUT T-0023 kim -> 200 content-type application/json; charset=utf-8, body equals GET; repeat -> 200 same; null -> 200 assignee null",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"The endpoint answers 200 with the ticket.\""
  },
  {
   "id": "U-22",
   "behaviour": "docs/api.md documents endpoint, field, filter, audit actions and notification; README documents the CLI columns; decision record 0009 added and indexed; CHANGELOG.md has no new section and package.json version stays 1.4.0",
   "handling": "poor",
   "observed": true,
   "evidence": "diff against base: api.md, README.md, docs/decisions/0009 + README index changed; CHANGELOG.md and package.json identical to base",
   "spec": "silent",
   "told": "no",
   "told_where": "",
   "rerun": true
  },
  {
   "id": "U-26",
   "behaviour": "show leaves the data file byte-for-byte unchanged with --data and with DATA_FILE",
   "handling": "sound",
   "observed": true,
   "evidence": "cp run/cli.json run/cli.copy.json; show T-0001/T-0003 with --data, show T-0002 with DATA_FILE; cmp -> identical both times",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.\""
  },
  {
   "id": "U-27",
   "behaviour": "show lists history oldest first, matching the audit API order, with both assignment entries and the current assignee",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0001 assigned dana by lee then sam by kim: show history 'system ticket.created ...', 'lee ticket.assigned assignee dana', 'kim ticket.assigned assignee dana -> sam'; audit API seq 1,4,5 same order; 'assignee sam' in detail",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "Store change rollback: a failed save restores ticket, audit and outbox",
   "where": "src/store.js apply()",
   "worth": "value",
   "why": "observed: a failed write no longer leaves the in-memory state ahead of the file; applies to every change, not only assignment"
  },
  {
   "what": "Load-time validation of assignee in the data file",
   "where": "src/persistence.js readTicket()",
   "worth": "value",
   "why": "a corrupt assignee stops start-up with a message naming the record, like other fields"
  },
  {
   "what": "Assignee line in the CLI show detail",
   "where": "src/format.js details()",
   "worth": "value",
   "why": "operators see the current assignee next to the history"
  },
  {
   "what": "Decision record 0009 and index entry",
   "where": "docs/decisions/0009-ticket-assignment.md",
   "worth": "neutral",
   "why": "explains the nullable field and outbox key; follows the repository's decision convention"
  }
 ],
 "spec_notes": "The spec (docs/[tool]/spec.md, R-1..R-3) does not contradict the request. It decides several points the request leaves open as ordinary requirement lines with no mark that they are the builder's choices: trimming of names, 409 for resolved/closed, exact case-sensitive filter matching, an empty assignee= matching null, a placeholder in the table and a blank fifth raw column, notifications only on assignment. docs/api.md pins the 64 limit to Unicode code points, which differs from how the requester's 64 limit counts; another correct build need not share that. The spec is silent on what transitions do to the assignee, on POST/PATCH refusing an assignee field, on repeated unassign, on the show detail, and on the changelog/version.",
 "tests_notes": "TC-1..TC-5 each cover many behaviours at once (TC-5 alone: legacy load, persistence, byte-identical no-op file, CLI table, show, raw columns and the weekly report). Tied to internals: TC-2 and TC-6 deepEqual store.snapshot(); TC-6 builds a TicketStore with a fake persistence and calls store.assign() directly; TC-4 drives worker.tick() and reads notifier.delivered; TC-1 reads store.history() and store.outboxReport(). Would fail on another correct build: the em dash placeholder and empty fifth raw field (TC-5), notification wording /Assigned to you/ (TC-4), 64 x U+10400 accepted (TC-2, a UTF-16 count would refuse it), 409 for resolved/closed, trimming '  Dana Lee  ', and one event per assignment with distinct keys.",
 "maintainer": "Store.apply() now snapshots and restores the whole audit log and outbox via toJSON() on every change when a data file is configured, and restores only then; anyone changing apply() or adding effects must keep that rollback and the copy-on-write ticket replacement in step, and memory-only mode does not roll back. The assignment outbox key embeds the audit entry's seq, coupling notification de-duplication to audit numbering."
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
   "evidence": "package.json has no dependencies/devDependencies (diff with base: only version 1.4.0->1.5.2 and description); service started and all probes ran with no npm install",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=<n> npm start -> \"tickets listening on <n>\"; GET /health 200 on that port",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> T-0001; PUT /tickets/T-0001/assignee {\"assignee\":\"dana\"} -> 200 with assignee \"dana\"; GET /tickets/T-0001 -> assignee \"dana\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":null} on the dana ticket -> 200 assignee null; GET -> assignee null",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: `if (ticket.assignee === assignee) return` -> `if (ticket.assignee === assignee || assignee === null) return`; 7 tests failed incl. \"assigns, hands off and clears with an audited timestamp and no effects on repeat\"; reverted, suite back to 134/134"
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":\"\"} -> 400 invalid \"assignee must be null or a single-line agent name of 1 to 64 characters\"; GET shows previous assignee unchanged",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "PUT 64 x 'a' -> 200 with that name; PUT 65 x 'b' -> 400 invalid; GET still shows the 64-character name",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "open ticket: assign dana 200, unassign 200; after transition to in_progress: assign lee 200, unassign 200 (null), assign dana 200",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "resolved ticket assigned to dana: PUT {\"assignee\":\"lee\"} -> 409 conflict \"ticket T-0001 is resolved and cannot be assigned\"; after closed same 409; ticket, audit and outbox JSON identical before/after",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: `if (!isActive(ticket.status)) throw` -> `if (!isActive(ticket.status) && assignee === null) throw`; only \"resolved and closed tickets keep their owners and reject every assignment request\" failed; reverted, 134/134"
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "resolved and closed ticket assigned to dana: PUT {\"assignee\":null} -> 409 conflict; GET still assignee \"dana\"; audit and outbox unchanged",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: `if (!isActive(ticket.status)) throw` -> `if (!isActive(ticket.status) && assignee !== null) throw`; only \"resolved and closed tickets keep their owners and reject every assignment request\" failed; reverted, 134/134"
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":\"dana\"} twice with X-Actor lee, 20 ms apart: second 200 with body equal to the first; ticket, audit and /admin/outbox JSON identical after the repeat; updated unchanged (1.1 s gap probe)",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "deleted the line `if (ticket.assignee === assignee) return { ...ticket };` in src/store.js assign; 4 tests failed incl. \"assigns, hands off and clears with an audited timestamp and no effects on repeat\" and \"overlapping requests leave a single ordered assignment history\"; reverted, 134/134"
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "assignee present on POST (null), GET /tickets/:id, every item of GET /tickets, PATCH response ('dana'), transition response ('dana') and PUT response",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> 201 with \"assignee\":null; cleared ticket GET -> null",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "after PUT dana, /admin/outbox pending has {type:\"ticket.assigned\", to:\"dana\", ticket, key \"ticket.assigned:T-0003:16\"}; with NOTIFY_FILE and worker 100 ms the line {\"type\":\"ticket.assigned\",\"to\":\"dana\",\"subject\":\"[T-0001] Assigned to you\",\"body\":\"Ticket T-0001 \\\"Laptop fan loud\\\" was assigned to you.\"} was written and the event moved to sent",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "tickets dana (closed, in_progress, open), lee, unassigned: GET /tickets?assignee=dana -> T-0001,T-0003,T-0005 only; ?assignee=lee -> T-0004 only",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: `filters.assignee = assignee === '' ? null : assignee` -> `... ? null : undefined`; 2 tests failed: \"assignee, status and priority intersect before cursor pagination\" and \"assignment notices survive clearing, closure and restart and deliver to their recorded recipients\"; reverted, 134/134"
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "GET /tickets?assignee= -> T-0002 (resolved, never assigned) and T-0006 only; a cleared ticket also appears (U-14 probe)",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: `assignee === '' ? null : assignee` -> `assignee === '' ? undefined : assignee`; 2 tests failed: \"assignee, status and priority intersect before cursor pagination\" and \"assignment notices survive clearing, closure and restart ...\"; reverted, 134/134"
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "?assignee=dana&priority=low -> T-0005; &status=in_progress -> T-0003; &status=open&priority=low -> T-0005; ?assignee=&status=open -> T-0006; ?assignee=&status=resolved -> T-0002",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "node bin/tickets.js --data auditdata/cli.json list -> table with ASSIGNEE column: \"sam\", unassigned, \"ada li\", \"null\", unassigned",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "create/patch/transition/audit/outbox/404 routes, X-Actor limit, body limit, list --raw (4 columns) and weekly-report --json (same counts as the base on the same file) all behave as before; the 18 original test files pass. One deliberate change: status+priority now intersect (base returned the union, contrary to its own docs/api.md)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "cmp of every file in base/test with work/Y/test: all 18 identical; npm test passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "test/assignment.test.js, assignment-delivery.test.js, assignment-input-history.test.js, assignment-regressions.test.js use node:test",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) ran 134 tests including the four assignment files, all passing",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "409 conflict \"ticket T-n is resolved|closed and cannot be assigned\" for every PUT on a resolved or closed ticket, including the current agent again and null on an unassigned resolved ticket; ticket, updated, audit and outbox unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "p1 probe: resolved T-0001 (dana): lee/dana/null -> 409 x3, ticket/audit/outbox JSON equal; closed: same; resolved unassigned T-0002: null -> 409, dana -> 409, assignee null",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"Only `open` and `in_progress` tickets accept this request. A `resolved` or `closed` ticket returns 409 `conflict` even when the requested value equals the current one.\""
  },
  {
   "id": "U-2",
   "behaviour": "400 invalid for {}, 5, {}, [], true, extra field (\"unknown field: x\"), [] body, empty body, non-JSON, invalid UTF-8 0xFF (\"request body is not valid UTF-8\"); 404 not_found for T-9999; ticket, audit and outbox unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "p2 probe: statuses 400 x10 with the messages above, 404 for T-9999 and abc; snapshots equal",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"The body must be valid UTF-8, contain exactly the `assignee` field and fit within `MAX_BODY_BYTES` (65,536 by default). Malformed UTF-8 returns 400 `invalid` without changing the ticket, audit history or outbox.\""
  },
  {
   "id": "U-3",
   "behaviour": "Names kept exactly as supplied (no trimming): whitespace-only, tab, newline, U+2028, lone surrogate refused 400; \"  dana  \" stored with its spaces and only found by ?assignee=%20%20dana%20%20, not ?assignee=dana; length counted in UTF-16 units before any trimming (64 chars padded to 66 refused; 32 emoji accepted, 33 refused)",
   "handling": "acceptable",
   "observed": true,
   "evidence": "p2 probe U-3 lines; requester, by contrast, is trimmed before its 64 limit",
   "spec": "open",
   "told": "yes",
   "told_where": "docs/api.md: \"Agent names are well-formed Unicode strings of 1 through 64 UTF-16 code units with at least one non-whitespace character. Control characters and line and paragraph separators are invalid. The service preserves the name as supplied.\""
  },
  {
   "id": "U-4",
   "behaviour": "One ticket.assigned entry per real change with changes {assignee:{from,to}}, actor from X-Actor (lee, sam) or system; repeat records nothing",
   "handling": "sound",
   "observed": true,
   "evidence": "audit after creation: seq7 lee null->dana, seq8 sam dana->null, seq9 system null->dana; the repeated dana PUT added nothing",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A change updates `updated` and records the previous and resulting assignee in the audit log.\"; \"The last action covers both setting and clearing the assignee.\""
  },
  {
   "id": "U-5",
   "behaviour": "Assignment and unassignment set updated to the change time; a repeat leaves it",
   "handling": "sound",
   "observed": true,
   "evidence": "created 14:48:53.142; assign 14:48:54.245; repeat 14:48:54.245; unassign 14:48:56.450",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A change updates `updated` and records the previous and resulting assignee in the audit log.\""
  },
  {
   "id": "U-6",
   "behaviour": "Unassigning an unassigned open ticket answers 200 with assignee null and changes nothing",
   "handling": "sound",
   "observed": true,
   "evidence": "WORKER_INTERVAL_MS=0: null twice on a new ticket -> 200, 200; ticket/audit/outbox equal to just after creation; assign dana, unassign, unassign again -> 200 and unchanged",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"On an eligible ticket, repeating the current value leaves the timestamp, audit history and notifications as they were.\""
  },
  {
   "id": "U-7",
   "behaviour": "Outbox event type ticket.assigned, to = the agent name, subject \"[T-n] Assigned to you\", body naming id and title; delivered by the worker after the PUT returns; no dead events",
   "handling": "sound",
   "observed": true,
   "evidence": "NOTIFY_FILE probe: last line {\"type\":\"ticket.assigned\",\"to\":\"dana\",\"subject\":\"[T-0001] Assigned to you\",\"body\":\"Ticket T-0001 \\\"Laptop fan loud\\\" was assigned to you.\"}; outbox pending 0, dead 0, sent 2",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A change to a name queues a notification to the incoming agent.\"; docs/operations.md: \"A new assignment notifies the incoming agent.\""
  },
  {
   "id": "U-8",
   "behaviour": "Each assignment gets its own key ticket.assigned:<id>:<audit seq>, so successive assignments are all queued and none is dropped",
   "handling": "sound",
   "observed": true,
   "evidence": "worker off: dana, lee, null, dana -> pending dana (key :2), lee (:3), dana (:5); with worker on, after delivery a new lee assignment queued key :6 and was then sent",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/operations.md: \"Each assignment to an agent has its own key based on the audit sequence.\""
  },
  {
   "id": "U-11",
   "behaviour": "assignee saved in the data file (format version 1, new ticket key) and survives restart; a 1.4.0 file without assignee loads as null and can be assigned; assignee 5, a 65-char name or \"\" stops the start with \"tickets[1].assignee is not an agent name or null\" (exit 2)",
   "handling": "sound",
   "observed": true,
   "evidence": "p3/p4 probes: after SIGTERM restart T-0001 dana, T-0002 null; base-written file -> all null; bad files exit 2 with that message",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/operations.md: \"Version 1 files from before assignment load tickets with a missing assignee as unassigned. An explicit assignee must be a valid agent name or `null`.\""
  },
  {
   "id": "U-12",
   "behaviour": "Assignee kept through in_progress, resolved, reopen and closed; ?assignee=dana still returns it, ?assignee= does not; reopened ticket can be reassigned (lee)",
   "handling": "sound",
   "observed": true,
   "evidence": "p2 U-12 lines: assignee dana after each transition, in dana filter true, in empty false; reopen + PUT lee 200; closed keeps lee",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"PATCH and lifecycle changes preserve the assignee.\""
  },
  {
   "id": "U-13",
   "behaviour": "Exact, case-sensitive, untrimmed match; ?assignee=Dana and ?assignee=%20dana -> empty; 65 chars -> 400 invalid; whitespace-only or tab -> 400; repeated parameter uses the first value",
   "handling": "sound",
   "observed": true,
   "evidence": "p1 U-13 lines: Dana [], %20dana [], 65 -> 400, dana&lee -> dana tickets, lee&dana -> lee ticket",
   "spec": "open",
   "told": "yes",
   "told_where": "docs/api.md: \"The assignee filter compares names exactly, including case and surrounding spaces.\"; \"A repeated parameter uses its first value. Invalid status, priority or nonempty assignee values return `invalid`.\""
  },
  {
   "id": "U-14",
   "behaviour": "Filtered listing pages correctly with cursors: every match once, in id order, nothing else",
   "handling": "sound",
   "observed": true,
   "evidence": "11 tickets, limit=2: assignee=dana -> T-0001,3,5,7,9,11; assignee= -> T-0002,6,8, then next null",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"Otherwise, pass it as `cursor`, with the same filters, to get the next page.\""
  },
  {
   "id": "U-15",
   "behaviour": "status and priority together now list the intersection (base 1.4.0 returned the union, contrary to its docs)",
   "handling": "sound",
   "observed": true,
   "evidence": "same file: base ?status=open&priority=urgent -> open/low, open/urgent, resolved/urgent; product -> only open/urgent",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A ticket must match every supplied filter.\"; CHANGELOG.md: \"Listings require every supplied filter to match.\""
  },
  {
   "id": "U-16",
   "behaviour": "list --raw unchanged: four tab-separated fields id, status, priority, title for assigned and unassigned rows; weekly report counts identical to the base",
   "handling": "sound",
   "observed": true,
   "evidence": "awk NF = 4 on every line incl. the \"ada li\" ticket; weekly-report --json identical for product and base on the same file",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"`list --raw` prints one ticket per line with four tab-separated columns in order of id, status, priority and title.\""
  },
  {
   "id": "U-17",
   "behaviour": "ASSIGNEE column: quoted name (\"sam\", \"ada li\", \"null\") or the word unassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "list output shown in evidence for S-17; the agent named \"null\" is distinguishable from unassigned",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"`list` prints a table with an `ASSIGNEE` column that shows a quoted agent name or `unassigned`.\""
  },
  {
   "id": "U-18",
   "behaviour": "show prints an assignee line: quoted name or unassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "show T-0001 -> assignee \"sam\"; T-0002 -> assignee unassigned; T-0004 -> \"null\"",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"`show` displays the current assignee in the ticket details above the history, using the same format.\""
  },
  {
   "id": "U-20",
   "behaviour": "POST /tickets and PATCH /tickets/:id refuse assignee as an unknown field (400)",
   "handling": "sound",
   "observed": true,
   "evidence": "POST with assignee -> 400 \"unknown field: assignee\"; PATCH {\"assignee\":\"dana\"} -> 400 same; ticket unchanged",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-21",
   "behaviour": "200 application/json; charset=utf-8 with the whole ticket incl. assignee, equal to the following GET; same for the no-op and for null",
   "handling": "sound",
   "observed": true,
   "evidence": "p2 U-21 lines: assign, repeat, null all 200 with body equal to GET",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "docs/api.md: \"Answers 200 with the resulting ticket.\""
  },
  {
   "id": "U-22",
   "behaviour": "docs/api.md documents the endpoint, field, filter, audit action and notification; README command-line columns; CHANGELOG sections 1.5.0, 1.5.1, 1.5.2 and package.json version 1.5.2; decision 0009 and operations.md (data file, rollback, keys)",
   "handling": "sound",
   "observed": true,
   "evidence": "read docs/api.md, README.md, CHANGELOG.md, package.json, docs/decisions/0009-ticket-assignment.md, docs/operations.md in the delivered tree",
   "spec": "silent",
   "told": "yes",
   "told_where": "CHANGELOG.md: \"## 1.5.0 (2026-11-22)\" / \"Assign or clear the owner of an active ticket. Changes are audited and incoming agents receive a notification.\" (with 1.5.1 and 1.5.2 sections)",
   "rerun": true
  },
  {
   "id": "U-26",
   "behaviour": "show is read-only: file byte-for-byte unchanged after --data and DATA_FILE invocations",
   "handling": "sound",
   "observed": true,
   "evidence": "cp cli.json cli.copy.json; show T-0001 --data, DATA_FILE=... show T-0002, show T-0004/T-0005; cmp -> identical",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.\""
  },
  {
   "id": "U-27",
   "behaviour": "History oldest first in audit order incl. both assignment entries with their actors; current assignee shown",
   "handling": "sound",
   "observed": true,
   "evidence": "DATA_FILE run: assign dana (X-Actor lee), sam (X-Actor kim); show T-0001 history: created/system, assigned/lee \"assignee dana\", assigned/kim \"assignee dana -> sam\" = audit seq 1,2,3",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"History is oldest first. An assignment change ending in bare `null` clears the assignee, and `\"null\"` is an agent name.\""
  }
 ],
 "extras": [
  {
   "what": "Strict UTF-8 check on the assignment body",
   "where": "src/http.js readJson strictUtf8, used by PUT /tickets/:id/assignee",
   "worth": "value",
   "why": "stops a replacement character becoming part of a saved name and a notification recipient"
  },
  {
   "what": "Rollback of the in-memory ticket, audit and outbox when saving an assignment fails",
   "where": "src/store.js assign",
   "worth": "value",
   "why": "a 500 leaves a consistent state and the same request can be retried (observed)"
  },
  {
   "what": "Assignee line in `show` and quoting of ambiguous names (\"null\", names with \" -> \" or \"; \") in history",
   "where": "src/format.js",
   "worth": "value",
   "why": "keeps the clear distinguishable from an agent named null"
  },
  {
   "what": "status+priority filters now intersect",
   "where": "src/tickets/query.js matchesFilters",
   "worth": "value",
   "why": "fixes the base bug against its documented contract; recorded in the changelog"
  },
  {
   "what": "Rollback instructions for returning to a pre-assignment build",
   "where": "docs/operations.md",
   "worth": "value",
   "why": "warns that the older build drops assignee fields and cannot deliver ticket.assigned"
  },
  {
   "what": "acceptance/ harness (.cjs files, legacy-v1.json) and [tool]/ working notes shipped in the tree",
   "where": "acceptance/, [tool]/",
   "worth": "neutral",
   "why": "not run by npm test and not referenced by README; clutter for a maintainer but harmless"
  },
  {
   "what": "Three release versions (1.5.0, 1.5.1, 1.5.2) for one delivery",
   "where": "CHANGELOG.md, package.json",
   "worth": "neutral",
   "why": "accurate but records the build's internal iterations as releases"
  }
 ],
 "spec_notes": "[tool]/spec.md has use cases and 52 clauses; none contradicts the request. It marks as Open (for the requester) the name rules (C-2), filter matching and repeated parameters (C-27, C-30), the raw column (C-36) and same-agent pending notices (C-22), yet the product and its docs decide all of them (exact untrimmed names, UTF-16 limit, first parameter wins, raw unchanged, per-seq keys) without the spec recording the decision. Decisions stated as ordinary clauses with \"implied\" or \"discovery\" sources: 409 even for no-op requests on resolved/closed tickets (C-5; the request allows 200 there), no notification on clear (C-19), keys per assignment (C-21), rollback after a failed save (C-43), show prints the assignee (C-45), history quoting (C-49, C-51). C-11 is honestly marked \"choice\" and leaves the success body open. The spec pins choices a correct product need not share: 409 for the no-op on resolved tickets, 400 for whitespace-only filter values, exact 1/2/4/8 s retry delays. C-52 (a malformed byte in the filter must not match) is contradicted by the product as observed.",
 "tests_notes": "The new tests are few and very broad: \"assigns, hands off and clears...\" alone covers S-3, S-4, S-7, S-10, S-11, S-12, U-4, U-5, U-6 and U-21, and \"assignee, status and priority intersect...\" covers S-14..S-16, U-13, U-14, U-15, so one break fails a test whose name says little about the cause. Several tests reach into internals: TicketStore, createPersistence with an injected failing rename, readJson, store.assign, outboxReport() and snapshot(), and the exact notification key shape is implied by key-distinctness asserts. Tests that would fail on another correct build: 409 (not 200) for no-op requests on resolved/closed tickets; case-sensitive, untrimmed filter matching (a lower-cased name excluded); ?assignee=%20 answering 400; refusal of U+0085 in names and the X-Actor trimming; exact-equality of whole response bodies with a manual clock; the CLI table format (\"Dana\" quoted, the word unassigned) and exact history line format; the clear producing no outbox event.",
 "maintainer": "The agent-name rule in src/tickets/assignees.js is shared by request validation, the listing filter and data-file loading, and names are stored untrimmed and matched exactly, so changing normalisation (trimming, case) would need a data-file migration and changes in all three places at once. store.assign has its own save-failure rollback that no other store method has, so a later change to apply()/save() must keep the two paths consistent. The CLI history quoting rules in src/format.js are subtle and tested by exact line format."
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
   "evidence": "package.json has no dependencies/devDependencies (node printed undefined undefined); no node_modules in the copy; the server, CLI and tests all ran",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "PORT=60959 WORKER_INTERVAL_MS=0 npm start -> 'npm start' -> 'node src/server.js'; log 'tickets listening on 60959'; GET /health -> {\"status\":\"ok\"}",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "POST /tickets -> 201 assignee null; PUT /tickets/T-0001/assignee {\"assignee\":\"dana\"} -> 200 ticket with \"assignee\":\"dana\"; GET /tickets/T-0001 -> \"assignee\":\"dana\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":null} on T-0001 assigned to dana -> 200 \"assignee\":null; GET shows null",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: 'if (ticket.assignee === assignee) return' changed to '... || assignee === null) return' (unassign becomes a no-op); 4 tests failed: assigns, hands off and clears...; assignee, status and priority intersect before cursor pagination; legacy tickets load unassigned...; assignment notices retry on the normal schedule...; restored, suite back to 127/127 and copy identical to the product (diff -r)"
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "PUT {\"assignee\":\"\"} on a ticket assigned to dana -> 400 invalid 'assignee must be null or a single-line agent name of 1 to 64 characters'; GET still \"assignee\":\"dana\", updated unchanged",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "PUT with 64 'a' -> 200 assignee is the 64-char name; PUT with 65 'a' -> 400 invalid; GET keeps the 64-char name and the same updated",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "open T-0001: assign dana 200, unassign 200; in_progress T-0002: PUT dana -> 200 assignee dana, PUT null -> 200 assignee null",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "T-0003 assigned dana then resolved: PUT lee -> 409 conflict 'ticket T-0003 is resolved and cannot be assigned'; after closing, PUT lee -> 409 '... is closed ...'; ticket, audit and outbox byte-identical before/after",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: 'if (!isActive(ticket.status)) throw' changed to 'if (!isActive(ticket.status) && assignee === null) throw' (assigning a resolved/closed ticket allowed); failed: resolved and closed tickets keep their owners and reject every assignment request; restored, 127/127"
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "resolved T-0003 (assignee dana): PUT null -> 409 conflict; closed: PUT null -> 409; GET still \"assignee\":\"dana\", audit and outbox unchanged",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: 'if (!isActive(ticket.status)) throw' changed to '... && assignee !== null) throw' (unassigning a resolved/closed ticket allowed); failed: resolved and closed tickets keep their owners and reject every assignment request; restored, 127/127"
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "T-0005 assigned dana (X-Actor lee); 1.1 s later PUT dana again -> 200 same body, same updated; GET ticket, GET audit and GET /admin/outbox string-identical before and after",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/store.js assign: removed 'if (ticket.assignee === assignee) return { ...ticket };' (a repeat then writes an audit entry dana->dana, moves updated and queues a notice); failed: assigns, hands off and clears...; overlapping requests leave a single ordered assignment history; restored, 127/127"
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "assignee present in POST /tickets (201), GET /tickets/:id, every item of GET /tickets, PATCH /tickets/:id response, POST transition response and PUT assignee response",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "new ticket -> \"assignee\":null; after unassign -> null; tickets from a pre-change data file -> \"assignee\":null",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "WORKER_INTERVAL_MS=100 NOTIFY_FILE=n.jsonl: PUT dana -> last line of n.jsonl {type ticket.assigned, to dana, ticket T-0001, subject '[T-0001] Assigned to you', body 'Ticket T-0001 \"Broken monitor\" was assigned to you.'}; outbox sent, 0 dead",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "tickets T-0001 open/low dana, T-0002 open/urgent dana, T-0003 resolved/urgent dana, T-0004 open/urgent none, T-0005 open/low lee, T-0006 in_progress/urgent none: GET /tickets?assignee=dana -> T-0001 T-0002 T-0003; ?assignee=lee -> T-0005",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: 'filters.assignee = assignee === \\'\\' ? null : assignee' changed to '... ? null : undefined' (named filter ignored); failed: assignee, status and priority intersect before cursor pagination; restored, 127/127"
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "same data: GET /tickets?assignee= -> T-0004 T-0006 only",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "src/tickets/query.js: 'assignee === \\'\\' ? null : assignee' changed to 'assignee === \\'\\' ? undefined : assignee' (empty filter ignored); failed: assignee, status and priority intersect before cursor pagination; restored, 127/127"
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "?assignee=dana&status=open -> T-0001 T-0002; ?assignee=dana&priority=urgent -> T-0002 T-0003; ?assignee=dana&status=open&priority=urgent -> T-0002; ?assignee=&priority=urgent -> T-0004 T-0006; ?assignee=&status=open&priority=urgent -> T-0004",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "node bin/tickets.js --data cli.json list -> ASSIGNEE column: \"ada li\", unassigned, \"dana\", \"Zoe \\\"Z\\\" O'Neil\" (JSON-quoted names, bare unassigned marker)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "create, PATCH, transitions incl. reopen, audit, outbox, worker delivery, data file restart, CLI list/--raw/show and weekly report all worked; weekly-report --json identical to the base version on the same file; the only changed existing behaviour is status+priority now intersecting (base returned the union), which the request and docs ask for",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "diff -r base/test product/test: only assignment.test.js and assignment-delivery.test.js added, no existing test file changed; npm test 127/127 pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "test/assignment.test.js (5 tests) and test/assignment-delivery.test.js (5 tests) use node:test and ran",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "npm test (node --test) ran 127 tests including the 10 new ones",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Every assign/unassign on a resolved or closed ticket, including the current agent again and null on an unassigned ticket, answers 409 conflict 'ticket T-n is <status> and cannot be assigned'; ticket, updated, audit and outbox unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "resolved T-0003 (dana): PUT lee/dana/null -> 409 x3, GET ticket, audit and outbox identical; closed: same; unassigned resolved T-0004: PUT null and dana -> 409, assignee null",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "docs/api.md: \"Only `open` and `in_progress` tickets accept this request. A `resolved` or `closed` ticket returns 409 `conflict` even when the requested value equals the current one.\""
  },
  {
   "id": "U-2",
   "behaviour": "{} -> 400 'assignee is required'; 5, {}, [] -> 400 invalid; extra field -> 400 'unknown field: x'; [] body, empty body -> 400 'request body must be a JSON object'; non-JSON -> 400 'not valid JSON'; unknown id -> 404 not_found; nothing changed. A 0xFF byte inside the name is decoded to U+FFFD and accepted (200, stored 'd\\uFFFDna')",
   "handling": "acceptable",
   "observed": true,
   "evidence": "PUT /tickets/T-0008/assignee with each body; GET ticket and audit afterwards showed only the 0xFF request as a change",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"The body must contain exactly the `assignee` field and fit within `MAX_BODY_BYTES` (65,536 by default).\"; \"`invalid` | 400 | the request is malformed: a body that is not a JSON object, a missing or wrong field, a query value out of range\""
  },
  {
   "id": "U-3",
   "behaviour": "Name kept exactly as supplied: '   ' refused, '  dana  ' stored with its spaces (a separate agent from 'dana' in filters), tab, newline, U+2028 and lone surrogates refused 400; the 64 limit counts UTF-16 units of the untrimmed name, so a 64-char name padded with spaces is refused while the same padded requester is accepted after trimming",
   "handling": "acceptable",
   "observed": true,
   "evidence": "PUT '   ' 400; '  dana  ' 200 assignee '  dana  '; 'da\\tna','da\\nna','da\\u2028na','\\ud800' 400; padded 64 -> 400; POST requester padded 64 -> 201 trimmed; ?assignee=dana excludes T-0010, ?assignee=%20%20dana%20%20 returns it",
   "spec": "open",
   "told": "yes",
   "told_where": "docs/api.md: \"Agent names are well-formed Unicode strings of 1 through 64 UTF-16 code units with at least one non-whitespace character. Control characters and line and paragraph separators are invalid. The service preserves the name as supplied.\""
  },
  {
   "id": "U-4",
   "behaviour": "One ticket.assigned audit entry per real change with actor from X-Actor (system without it) and changes {assignee:{from,to}}; set and clear share the action; no entry for a repeat",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0005 audit: seq19 lee {from null,to dana}; repeat added nothing; seq20 sam {dana->null}; seq21 system {null->dana}",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A change updates `updated` and records the previous and resulting assignee in the audit log.\"; \"The last action covers both setting and clearing the assignee.\""
  },
  {
   "id": "U-5",
   "behaviour": "Assign and unassign set updated to the change time; a repeat leaves it",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0005 created 14:48:43.955; assign -> updated 14:48:45.157; repeat 1.1 s later -> 14:48:45.157; unassign -> 14:48:46.330",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A change updates `updated` and records the previous and resulting assignee in the audit log.\""
  },
  {
   "id": "U-6",
   "behaviour": "Unassigning an already unassigned active ticket answers 200 with the unchanged ticket; no audit entry, no notice, same updated",
   "handling": "sound",
   "observed": true,
   "evidence": "new T-0006: PUT null twice -> 200, ticket/audit/outbox identical to after creation; assign dana, unassign, unassign again -> identical to after first unassign",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "docs/api.md: \"On an eligible ticket, repeating the current value leaves the timestamp, audit history and notifications as they were.\""
  },
  {
   "id": "U-7",
   "behaviour": "A ticket.assigned outbox event to the agent's name (to: 'dana'), keyed ticket.assigned:<id>:<audit seq>; the worker delivers it after the PUT returns with subject '[T-n] Assigned to you' and body naming id and title; unassigning sends nothing",
   "handling": "sound",
   "observed": true,
   "evidence": "NOTIFY_FILE line {type ticket.assigned, to dana, subject '[T-0001] Assigned to you', body 'Ticket T-0001 \"Broken monitor\" was assigned to you.'}; outbox pending 0, sent 2, dead 0",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A change to a name queues a notification to the incoming agent. Clearing only updates the ticket and its audit history.\""
  },
  {
   "id": "U-8",
   "behaviour": "Each real assignment queues its own notice (key includes the audit seq), so dana, lee, unassign, dana before delivery leaves pending notices for dana, lee and dana; after delivery, a later assignment of lee queues a new one",
   "handling": "sound",
   "observed": true,
   "evidence": "worker off: pending ticket.assigned dana :26, lee :27, dana :29; worker on: lee, null, dana, lee -> five sent events with distinct keys, n.jsonl 5 lines",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "docs/operations.md: \"Each assignment to an agent has its own key based on the audit sequence.\""
  },
  {
   "id": "U-11",
   "behaviour": "Assignee survives restart; a base-version data file (no assignee fields) loads with assignee null and stays version 1; an assignee of 5 or a 65-char name stops the service at start (exit 2) naming tickets[1].assignee; the CLI refuses the same file",
   "handling": "sound",
   "observed": true,
   "evidence": "SIGTERM then restart on t.json -> T-0017 assignee lee; base wrote old.json (grep -c assignee = 0), new build -> all assignee null, ?assignee= lists them; bad5.json/bad65.json -> 'cannot start: ...: tickets[1].assignee is not an agent name or null', exit 2",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/operations.md: \"Version 1 files from before assignment load tickets with a missing assignee as unassigned. An explicit assignee must be a valid agent name or `null`.\""
  },
  {
   "id": "U-12",
   "behaviour": "The assignee is kept through in_progress, resolved, reopen and closed; the named filter keeps returning the ticket and it never appears under assignee=; after reopen it can be reassigned",
   "handling": "sound",
   "observed": true,
   "evidence": "T-0017 zed: after in_progress/resolved/open ?assignee=zed returns it, assignee= does not; PUT lee after reopen -> 200; T-0018 closed keeps zed and ?assignee=zed lists it",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "docs/api.md: \"PATCH and lifecycle changes preserve the assignee.\""
  },
  {
   "id": "U-13",
   "behaviour": "Exact, case-sensitive, untrimmed match; ?assignee=Dana and ?assignee=%20dana -> empty page; 65-char value -> 400 invalid; whitespace-only (%20, %09) -> 400; repeated parameter uses the first value",
   "handling": "sound",
   "observed": true,
   "evidence": "?assignee=Dana -> []; %20dana -> []; 65 a -> 400 'assignee must be an agent name or empty'; dana&assignee=lee -> dana's three; lee&assignee=dana -> T-0005",
   "spec": "open",
   "told": "yes",
   "told_where": "docs/api.md: \"The assignee filter compares names exactly, including case and surrounding spaces.\"; \"A repeated parameter uses its first value. Invalid status, priority or nonempty assignee values return `invalid`.\""
  },
  {
   "id": "U-14",
   "behaviour": "Filtered listings page correctly by cursor",
   "handling": "sound",
   "observed": true,
   "evidence": "8 dana tickets interleaved with others, limit=2 following next: T-0001,T-0002 | T-0003,T-0007 | T-0009,T-0011 | T-0013,T-0015, then next null, same as limit=100; assignee= : T-0004,T-0006 | T-0008,T-0010 | T-0012,T-0014 | T-0016",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"Otherwise, pass it as `cursor`, with the same filters, to get the next page.\""
  },
  {
   "id": "U-15",
   "behaviour": "status and priority together now list the intersection; the base returned the union",
   "handling": "sound",
   "observed": true,
   "evidence": "open/low, open/urgent, resolved/urgent: base build ?status=open&priority=urgent -> T-0001 T-0002 T-0003; this build on the same file -> T-0002 only",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "docs/api.md: \"A ticket must match every supplied filter.\"; CHANGELOG.md: \"Listings require every supplied filter to match.\""
  },
  {
   "id": "U-16",
   "behaviour": "list --raw unchanged: four tab-separated fields id, status, priority, title for assigned (incl. 'ada li') and unassigned tickets; weekly report counts identical to the base build",
   "handling": "sound",
   "observed": true,
   "evidence": "awk NF = 4 on every raw line for both builds; weekly-report --json identical {total 4, byStatus open 3 in_progress 1, byPriority 1/1/1/1}",
   "spec": "open",
   "told": "yes",
   "told_where": "README.md: \"`list --raw` prints one ticket per line with four tab-separated columns in order of id, status, priority and title.\""
  },
  {
   "id": "U-17",
   "behaviour": "ASSIGNEE column shows the JSON-quoted name and a bare 'unassigned' for none; an agent literally named unassigned shows as \"unassigned\"",
   "handling": "sound",
   "observed": true,
   "evidence": "list: T-0002 unassigned vs T-0001 \"ada li\"; agent named unassigned -> \"unassigned\"",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"`list` prints a table with an `ASSIGNEE` column that shows a quoted agent name or `unassigned`.\""
  },
  {
   "id": "U-18",
   "behaviour": "show does not print an assignee field; assignment changes appear only as history lines",
   "handling": "acceptable",
   "observed": true,
   "evidence": "show T-0001 (ada li) and show T-0002 (unassigned) print status, priority, requester, created, updated; no assignee line",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-20",
   "behaviour": "POST /tickets and PATCH /tickets/:id refuse an assignee field as unknown (400)",
   "handling": "sound",
   "observed": true,
   "evidence": "POST with assignee dana -> 400 'unknown field: assignee'; PATCH {assignee:dana} -> 400 'unknown field: assignee'; ticket unchanged",
   "spec": "decided-marked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-21",
   "behaviour": "200 application/json; charset=utf-8 with the whole ticket incl. assignee, equal to the following GET; same for the no-op and for null",
   "handling": "sound",
   "observed": true,
   "evidence": "curl -i PUT dana -> 200 content-type application/json; charset=utf-8, body = GET body; repeat -> 200 same body; null -> 200 assignee null",
   "spec": "decided-marked",
   "told": "yes",
   "told_where": "docs/api.md: \"Answers 200 with the resulting ticket.\""
  },
  {
   "id": "U-22",
   "behaviour": "docs/api.md documents the endpoint, field, filter, audit action and notification; README the CLI column and raw columns; CHANGELOG 1.5.0 with package.json 1.5.0; decision 0009 and an operations.md note on rollback",
   "handling": "sound",
   "observed": false,
   "evidence": "read docs/api.md, README.md, CHANGELOG.md, package.json version 1.5.0, docs/decisions/0009-ticket-assignment.md and its README index",
   "spec": "silent",
   "told": "yes",
   "told_where": "CHANGELOG.md: \"## 1.5.0 (2026-11-22)\" / \"Assign or clear the owner of an active ticket. Changes are audited and incoming agents receive a notification.\"",
   "rerun": true
  },
  {
   "id": "U-26",
   "behaviour": "show (and list) leave the data file byte-for-byte unchanged",
   "handling": "sound",
   "observed": true,
   "evidence": "cmp after 'show T-0001 --data FILE', 'DATA_FILE=FILE show T-0002' and 'list' -> identical each time",
   "spec": "silent",
   "told": "yes",
   "told_where": "README.md: \"`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.\""
  },
  {
   "id": "U-27",
   "behaviour": "show lists history oldest first in audit order, including 'assignee dana', 'assignee dana -> sam', 'assignee sam -> null' with actors lee/kim; the current assignee is visible only through the last history line, not as a field",
   "handling": "acceptable",
   "observed": true,
   "evidence": "show T-0019 history lines match GET /tickets/T-0019/audit seq 50-54 in order and actor",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "store.assign snapshots the ticket, audit and outbox and restores them when the data file save fails",
   "where": "src/store.js assign",
   "worth": "value",
   "why": "A retry after a failed save is applied instead of being swallowed as a no-op (observed with a read-only data directory); other store changes do not have this, so the failure semantics now differ by operation"
  },
  {
   "what": "Status and priority filters now intersect even without assignee (base returned the union)",
   "where": "src/tickets/query.js matchesFilters",
   "worth": "value",
   "why": "Matches the request ('a ticket must match every filter given') and the existing API docs; noted in the changelog"
  },
  {
   "what": "Assignee names JSON-quoted in the CLI table with a bare 'unassigned' marker",
   "where": "src/format.js TABLE_COLUMNS",
   "worth": "value",
   "why": "Keeps an agent named 'unassigned' or a name with spaces unambiguous"
  },
  {
   "what": "Data file validation of the assignee at start",
   "where": "src/persistence.js readTicket",
   "worth": "value",
   "why": "A hand-edited bad assignee is refused with the record named instead of reaching filters and notices"
  },
  {
   "what": "Rollback guidance and decision record",
   "where": "docs/operations.md, docs/decisions/0009-ticket-assignment.md",
   "worth": "value",
   "why": "Warns that an older build drops assignee fields and cannot deliver ticket.assigned events"
  },
  {
   "what": "Version bump to 1.5.0 with a changelog section",
   "where": "package.json, CHANGELOG.md",
   "worth": "neutral",
   "why": "Follows the repository's release convention; no behaviour"
  }
 ],
 "spec_notes": "[tool]/spec.md marks several points Open (C-2 name normalisation and counting, C-22 a second notice to the same agent while one is pending, C-27 name identity, C-30 repeated or out-of-domain filter values, C-36 raw output) but the build decided every one of them; the decisions are recorded only in [tool]/build-1.md 'Discoveries' and the delivered docs, and the spec was not updated. C-5 decides 409 even for a no-op on a resolved or closed ticket (labelled implied) where 200 would also fit the request. C-30 requires status+priority to intersect without saying this changes what the service did before (the base returned the union); only build-1 notes it. C-8 pins the exact 65,536-byte body limit and C-24 pins the 1/2/4/8 s backoff, existing behaviour a correct build need not re-specify. C-14 pins that POST/PATCH reject an assignee field and C-11 leaves the success response open, which the build then fixed at 200 with the ticket. The spec is silent on the CLI show command (assignee display, read-only, history).",
 "tests_notes": "The new tests are long scenarios: 'assigns, hands off and clears...' covers S-3, S-4, S-7, S-10, S-11, S-12 and U-4/U-5/U-6/U-21 in one test, and 'assignee, status and priority intersect...' covers S-14, S-15, S-16 and U-13/U-14/U-15, so a failure does not name the broken behaviour. Tied to internals: 'a failed data file replacement...' mocks fs.renameSync and calls store.assign and snapshot directly; 'legacy tickets load...' and the CLI test build state through TicketStore/createPersistence; the retry test asserts exact backoff delays; the worker test polls with a 3 s deadline and a 30 ms sleep. Would fail on another correct build: asserting 409 for a no-op on a resolved ticket (200 is also acceptable), that a repeated assignee parameter uses the first value and that assignee=%20 is 400, that POST/PATCH reject assignee, that every reassignment to the same agent queues a separate notice with a distinct key, the exact outbox recipient order, the quoted-name/'unassigned' table format, and that an over-limit body padded with whitespace is refused at exactly 65,537 bytes. Nothing tests the CLI show command, npm start or the absence of dependencies.",
 "maintainer": "store.assign has its own snapshot-and-restore path for a failed save while update and transition do not, so anyone changing apply(), the audit log or the outbox must keep that rollback in step, and the store now has two failure behaviours. Notice keys are built from the audit sequence, coupling outbox deduplication to audit numbering. The name rule lives in src/tickets/assignees.js and is shared by request validation, the listing filter and data file loading, so changing it (for example to trim names) changes at once what requests, filters and existing data files accept."
}
```

