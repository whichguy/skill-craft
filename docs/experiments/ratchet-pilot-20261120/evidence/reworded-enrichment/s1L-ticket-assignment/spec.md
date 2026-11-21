## Use cases

### U-1: A dispatcher assigns an open or in-progress ticket to an agent, so the agent owns it
Flow: `PUT /tickets/T-0007/assignee` with body `{"assignee": "dana"}` (optionally `X-Actor: sam`). The answer is 200 with the whole ticket, whose `assignee` is `"dana"`. `GET /tickets/T-0007` now shows `"assignee": "dana"`.
Source: request

### U-2: A dispatcher unassigns a ticket, so nobody owns it
Flow: `PUT /tickets/T-0007/assignee` with `{"assignee": null}`. The answer is 200 with the ticket, `"assignee": null`.
Source: request

### U-3: A dispatcher moves a ticket from one agent to another, or repeats an assignment by mistake
Flow: `{"assignee": "li"}` on a ticket held by `dana` makes it `li`'s. Sending `{"assignee": "li"}` again changes nothing: 200, the same ticket, no new history, no second notification. `{"assignee": null}` on an unassigned ticket also changes nothing.
Source: request ("Assigning a ticket to the agent it already has changes nothing"); existing: CONTRIBUTING.md ("A change that changes nothing is not a change")

### U-4: A dispatcher sends a wrong assignment and is refused with a reason
Flow: a body that is not a JSON object, a missing, non-string, empty, whitespace-only, over-long or multi-line `assignee`, an unknown field, an unknown ticket, a resolved or closed ticket, or an over-long `X-Actor`. Each gets the error envelope `{"error": {"code", "message"}}` with the status in the clauses below, and nothing changes.
Source: implied: "an agent is a non-empty name of at most 64 characters", "Only open and in-progress tickets can be assigned"; existing: docs/api.md (Errors), docs/decisions/0004-error-envelope.md

### U-5: An agent is told a ticket was assigned to them
Flow: when a ticket becomes assigned to `dana`, a notification addressed to `dana` about that ticket is queued in the same request (visible in `GET /admin/outbox` as pending). The background worker delivers it; with `NOTIFY_FILE` set, one JSON line with `"to": "dana"` and `"ticket": "T-0007"` is appended.
Source: request ("The agent a ticket is assigned to is notified that it was assigned to them"); existing: docs/decisions/0006-notification-outbox.md

### U-6: Anyone reading a ticket sees who holds it
Flow: `GET /tickets/:id`, every item of `GET /tickets`, the answer to `POST /tickets`, `PATCH /tickets/:id`, `POST /tickets/:id/transition` and `PUT /tickets/:id/assignee` each show `"assignee"`: the agent's name, or `null`.
Source: request ("Every ticket shows its `assignee` (null when unassigned)")

### U-7: An agent or lead lists tickets by assignee, alone or with other filters
Flow: `GET /tickets?assignee=dana` lists `dana`'s tickets; `GET /tickets?assignee=` lists the unassigned ones; `GET /tickets?assignee=dana&status=open&limit=2` lists `dana`'s open tickets, two a page, following `next` with the same filters.
Source: request

### U-8: An auditor asks who assigned a ticket, to whom and when
Flow: `GET /tickets/T-0007/audit` lists an entry for each assignment, reassignment and unassignment with the actor, the time and the `assignee` before and after.
Source: implied: existing docs/decisions/0007-append-only-audit-log.md ("every change to a ticket is recorded")

### U-9: An operator lists tickets on the command line and sees the assignees; the weekly report keeps working
Flow: `node bin/tickets.js --data FILE list` prints a table with an assignee for each ticket; `list --raw` prints the tab-separated lines; `npm run report:weekly` prints the same counts as before.
Source: request ("The command-line listing shows each ticket's assignee"); existing: README.md ("Command line"), scripts/weekly-report.js

### U-10: An operator restarts the service, or upgrades it over a data file written before this change
Flow: with `DATA_FILE`, the assignments and the queued assignment notifications are still there after a restart. A data file written by version 1.4.0 loads, and its tickets are unassigned. A hand-damaged `assignee` stops the start with a message naming the record.
Source: implied: existing docs/decisions/0008-json-data-file.md ("A change to the format must keep loading the files the previous version wrote")

### U-11: An operator watches the outbox, with the worker off or on
Flow: with `WORKER_INTERVAL_MS=0`, `GET /admin/outbox` shows the assignment notification as pending and nothing is delivered. With the worker on it moves to sent.
Source: existing: docs/operations.md (Notifications)

### U-12: Two people assign the same ticket at once, or assign while someone else moves it
Flow: two `PUT`s race; or a `PUT` races `POST /tickets/:id/transition` to `resolved`. Each request is answered with a consistent outcome and no change is recorded twice or half recorded.
Source: implied: the ticket's `assignee` and `status` are shared state changed by concurrent requests

### U-13: A maintainer keeps the service healthy
Flow: `npm test` runs the old tests unchanged and the new ones, and all pass; the docs describe the new behaviour.
Source: request ("its existing tests must still pass as they are. Add node:test tests under test/"); existing: CONTRIBUTING.md (Tests, Releases)

## Clauses

### C-1: Assigning an open ticket to an agent makes the ticket that agent's
Observable: on an open ticket `T-0001`, `PUT /tickets/T-0001/assignee` with `{"assignee": "dana"}` answers 200 and the body's `assignee` is `"dana"`; a following `GET /tickets/T-0001` shows `"assignee": "dana"`.
Source: request

### C-2: Assigning an in-progress ticket to an agent makes the ticket that agent's
Observable: on a ticket whose status is `in_progress`, the same request answers 200 with `"assignee": "dana"`.
Source: request

### C-3: `{"assignee": null}` unassigns an open or in-progress ticket
Observable: on an open (and, separately, an in-progress) ticket assigned to `dana`, `PUT` with `{"assignee": null}` answers 200 with `"assignee": null`; a following `GET` shows `null`.
Source: request

### C-4: Assigning a ticket held by one agent to a different agent replaces the first
Observable: on an open ticket assigned to `dana`, `PUT` with `{"assignee": "li"}` answers 200 with `"assignee": "li"`; the ticket never lists two agents, and `?assignee=dana` no longer lists it.
Source: implied: "assigns the ticket to that agent" and a ticket shows one `assignee`

### C-5: The answer to the assignment request is the whole ticket
Observable: the 200 body is the ticket exactly as `GET /tickets/:id` answers it straight afterwards: `id`, `title`, `priority`, `requester`, `status`, `assignee`, `created`, `updated`.
Source: implied: existing docs/api.md (PATCH and transition answer the ticket)

### C-6: Assigning a ticket to the agent it already has changes nothing
Observable: on a ticket assigned to `dana`, `PUT` with `{"assignee": "dana"}` answers 200 with the ticket as it was: `updated` is unchanged, `GET /tickets/:id/audit` gains no entry, and `GET /admin/outbox` gains no event.
Source: request

### C-7: Unassigning a ticket that has no assignee changes nothing
Observable: on an open ticket with `"assignee": null`, `PUT` with `{"assignee": null}` answers 200 with the ticket as it was: `updated` is unchanged, no audit entry, no outbox event.
Source: implied: "{"assignee": null} unassigns it" and existing CONTRIBUTING.md ("A change that changes nothing is not a change")

### C-8: A resolved ticket cannot be assigned
Observable: `PUT` with `{"assignee": "dana"}` on a `resolved` ticket answers 409 with code `conflict`.
Source: request ("Only open and in-progress tickets can be assigned"); existing: CONTRIBUTING.md ("'The ticket's state does not allow this' is a conflict (409)")

### C-9: A closed ticket cannot be assigned
Observable: the same request on a `closed` ticket answers 409 with code `conflict`.
Source: request; existing: CONTRIBUTING.md

### C-10: A resolved or closed ticket cannot be unassigned
Observable: `PUT` with `{"assignee": null}` on a ticket that is `resolved`, and on one that is `closed`, and that has an assignee, answers 409 with code `conflict`; its `assignee` is unchanged.
Source: request ("assigned or unassigned")

### C-11: A resolved or closed ticket refuses even an assignment that would change nothing
Observable: `PUT` with the assignee the resolved (or closed) ticket already has, and `{"assignee": null}` on a resolved (or closed) ticket with no assignee, each answer 409 `conflict`, not 200.
Source: choice: the state rule is "only open and in-progress tickets can be assigned or unassigned" and is the simplest thing for a caller to rely on; the state is checked before the no-change case

### C-12: A request for a ticket that does not exist is answered 404
Observable: `PUT /tickets/T-0042/assignee` with a valid body, with no such ticket, answers 404 with code `not_found`; so does a path id that is not a ticket id (`/tickets/42/assignee`).
Source: implied: "PUT /tickets/:id/assignee" names a ticket; existing: docs/api.md (`not_found`)

### C-13: `assignee` must be present in the body
Observable: `PUT` with `{}` answers 400 `invalid`, and the ticket's assignee is not cleared; absent is not `null`.
Source: implied: the request names two body forms; an absent field is neither

### C-14: `assignee` must be a string or `null`
Observable: `PUT` with `{"assignee": 5}`, `true`, `false`, `{}`, `[]` or `["dana"]` as the value answers 400 `invalid`.
Source: implied: "an agent is a non-empty name"; existing: src/tickets/validate.js (`must be a string`)

### C-15: An empty or whitespace-only `assignee` is refused, not treated as unassigning
Observable: `PUT` with `{"assignee": ""}`, `{"assignee": "   "}` and `{"assignee": "\t"}` each answer 400 `invalid`; an assigned ticket stays assigned.
Source: request ("non-empty name"); choice: only `null` unassigns, so an empty string cannot unassign by accident

### C-16: A name of 64 characters is accepted
Observable: `PUT` with an `assignee` of exactly 64 characters (for example `"a"` repeated 64 times) answers 200 and the ticket shows that name unchanged. Characters are counted as JavaScript counts string length, in UTF-16 code units, so a name of 64 ASCII letters is the largest sure-to-pass case.
Source: request ("at most 64 characters"); existing: src/tickets/validate.js (`.length`); the runtime rule is JavaScript's string length

### C-17: A name of more than 64 characters is refused
Observable: `PUT` with an `assignee` of 65 characters answers 400 `invalid`; the ticket is unchanged.
Source: request

### C-18: Surrounding whitespace is not part of the name
Observable: `PUT` with `{"assignee": "  dana  "}` answers 200 with `"assignee": "dana"`; the length limit applies to the trimmed text (so 64 characters between spaces is accepted); sending `"dana "` to a ticket already assigned to `dana` changes nothing (C-6).
Source: choice: titles and requesters are already trimmed (src/tickets/validate.js `text`), and an agent name with stray spaces would never match the `assignee` filter

### C-19: A name containing a control character is refused
Observable: `PUT` with an `assignee` containing a tab, a line feed or any character from U+0000 to U+001F or U+007F (sent as a JSON escape such as `"da\tna"`) answers 400 `invalid`. The reason is the command line's tab-separated output, which a tab or line break in a name would break.
Source: existing: src/tickets/validate.js (`CONTROL`) and README.md ("Command line"); implied: the assignee is printed in `list --raw`

### C-20: Any other characters are allowed in a name
Observable: `PUT` with `"Dana Smith"` (an inner space), `"dana@example.com"` and `"Zoë"` each answer 200 and the ticket shows the name as sent. The name `"null"` is a name (the text), and does not unassign.
Source: choice: the request fixes only non-empty and at most 64 characters

### C-21: Agent names are compared exactly
Observable: after assigning `"dana"`, `PUT` with `"Dana"` changes the assignee to `"Dana"` (a change: new audit entry, new notification) and does not take the no-change path; `?assignee=dana` and `?assignee=Dana` list different tickets.
Source: choice: no rule of the request makes two spellings one agent, and folding case would decide an identity the request never gave

### C-22: Unknown fields in the assignment body are refused
Observable: `PUT` with `{"assignee": "dana", "priority": "high"}` or `{"assignee": "dana", "assigne": "li"}` answers 400 `invalid` and the ticket is unchanged.
Source: existing: docs/api.md (Conventions: "Unknown fields in a request body are refused (400)")

### C-23: A body that is not a JSON object is refused
Observable: an empty body, text that is not JSON (`{"assignee":`), `[]`, `null`, `"dana"` and `5` as the whole body each answer 400 `invalid`.
Source: existing: src/http.js (`readJson`), docs/api.md (`invalid`)

### C-24: A body over MAX_BODY_BYTES is refused
Observable: with `MAX_BODY_BYTES=1024`, `PUT` with a body of more than 1024 bytes answers 400 `invalid` (the full response is delivered; the connection is not reset); the default limit is 65536 bytes.
Source: existing: README.md (Configuration), src/http.js

### C-25: An `X-Actor` header of more than 64 characters is refused
Observable: `PUT` with a valid body and `X-Actor` of 65 characters answers 400 `invalid` and nothing changes; with 64 characters it is accepted.
Source: existing: docs/api.md (Conventions: The actor)

### C-26: A request is checked body first, then the ticket's existence, then its state
Observable: an invalid body sent to a ticket that does not exist answers 400, not 404; a valid body sent to a missing ticket answers 404; a valid body sent to a resolved ticket answers 409; an invalid body sent to a resolved ticket answers 400.
Source: choice: the existing PATCH and transition endpoints validate the body before looking up the ticket; assignment follows them so a client sees one order everywhere

### C-27: A refused request changes nothing and tells no one
Observable: after any 400, 404 or 409 answer to an assignment request, the ticket (including `updated`), its audit entries, the outbox and the data file hold what they held before.
Source: implied: existing docs/decisions/0007 ("no change without an entry") and CONTRIBUTING.md (changes go through the store in one step)

### C-28: Assignment errors use the error envelope
Observable: every 400, 404 and 409 answer of the assignment endpoint has the body `{"error": {"code": "<invalid|not_found|conflict>", "message": "<text>"}}` with a string message and `content-type: application/json; charset=utf-8`.
Source: existing: docs/decisions/0004-error-envelope.md

### C-29: The assignee path answers only PUT
Observable: `GET`, `POST`, `PATCH` and `DELETE` on `/tickets/T-0001/assignee` answer 404 `not_found`; `PUT /tickets/T-0001` (no `/assignee`) still answers 404 `not_found`.
Source: existing: src/router.js and src/app.js (a path that does not answer the method is `not_found`); choice: no other verb is part of the request

### C-30: An assignment is one audited change
Observable: after an assignment that changes the assignee, `GET /tickets/T-0001/audit` ends with exactly one new entry whose `changes` is `{"assignee": {"from": <before>, "to": <after>}}` and no other field: `{"from": null, "to": "dana"}` for a first assignment, `{"from": "dana", "to": "li"}` for a reassignment, `{"from": "li", "to": null}` for an unassignment.
Source: implied: existing docs/decisions/0007 (every change is recorded; `changes` holds before and after)

### C-31: The audit entry of an assignment names the actor and the time
Observable: the entry's `actor` is the trimmed `X-Actor` value (`"sam"`), or `"system"` when the header is absent or blank; its `at` is the time of the change; its `seq` is the next number of the whole log; it is the entry in `GET /tickets/:id/audit` of that ticket only.
Source: existing: docs/decisions/0007, src/http.js (`actorOf`)

### C-32: An assignment that changes the assignee moves `updated`
Observable: after such a change the ticket's `updated` equals the new audit entry's `at`; `created` is unchanged.
Source: existing: docs/api.md ("`updated` when it last changed")

### C-33: Every ticket carries an `assignee` field, null when unassigned
Observable: `GET /tickets/:id` has the key `assignee` (never absent, never `""`): `null` for a ticket nobody has been assigned and for one that has been unassigned, else the agent's name.
Source: request

### C-34: Every item of the listing carries `assignee`
Observable: each object in `items` of `GET /tickets` has `assignee`, equal to what `GET /tickets/:id` answers for it.
Source: request ("Every ticket shows its assignee")

### C-35: The answers that return a ticket carry `assignee`
Observable: the bodies of `POST /tickets` (201), `PATCH /tickets/:id`, `POST /tickets/:id/transition` and `PUT /tickets/:id/assignee` each have `assignee`.
Source: request ("Every ticket"); existing: docs/api.md

### C-36: A new ticket starts unassigned
Observable: `POST /tickets` answers 201 with `"assignee": null`, and its audit entry lists exactly `title`, `priority`, `requester`, `status` (no `assignee`), as it does today.
Source: implied: nobody is assigned at creation; existing: test/store.test.js and docs/api.md (created entry)

### C-37: A ticket cannot be assigned when it is created or by `PATCH`
Observable: `POST /tickets` with an `assignee` field and `PATCH /tickets/:id` with an `assignee` field each answer 400 `invalid` (unknown field); the ticket's assignee is unchanged.
Source: existing: docs/api.md (Unknown fields); request (assignment is the `PUT` endpoint)

### C-38: Changing a ticket's title or priority keeps its assignee
Observable: `PATCH` with `{"priority": "urgent"}` on a ticket assigned to `dana` answers with `"assignee": "dana"` and adds no assignee to the audit entry.
Source: implied: assignee is a separate field of the ticket

### C-39: Moving a ticket along its lifecycle keeps its assignee
Observable: a ticket assigned to `dana` that goes open → in_progress → resolved → closed keeps `"assignee": "dana"` at every step, and `resolved` → `open` (reopen) also keeps it; the `transition` audit entry lists only `status`.
Source: choice: the request does not say a resolution unassigns; clearing would be a change nobody asked for, and the lead's `?assignee=` listing should still show who worked a resolved ticket

### C-40: Tickets that existed before this change are unassigned
Observable: a ticket loaded from a data file written without an `assignee` field answers `"assignee": null` in `GET /tickets/:id` and in the listing, and can be assigned.
Source: implied: "Everything the service already does keeps working"; existing: docs/decisions/0008 ("A field older files do not have takes its default when they load")

### C-41: `assignee=<agent>` lists the tickets assigned to that agent
Observable: with `T-0001` to `dana`, `T-0002` to `li`, `T-0003` unassigned, `GET /tickets?assignee=dana` lists `["T-0001"]`.
Source: request

### C-42: An empty `assignee=` lists the unassigned tickets
Observable: with the same tickets, `GET /tickets?assignee=` lists `["T-0003"]`: only tickets whose `assignee` is `null`; it answers 200, not 400.
Source: request

### C-43: The `assignee` filter looks at tickets in every status
Observable: a `resolved` or `closed` ticket still assigned to `dana` is listed by `?assignee=dana`; one unassigned is listed by `?assignee=`.
Source: implied: "keeps that agent's tickets"; choice: a resolved ticket keeps its agent (C-39)

### C-44: The `assignee` filter matches the whole name exactly
Observable: `?assignee=dan` and `?assignee=Dana` do not list a ticket assigned to `dana`; `?assignee=dana+smith` and `?assignee=dana%20smith` (query text is decoded as URL form text) list a ticket assigned to `"dana smith"`; `?assignee=null` lists a ticket assigned to the agent named `"null"` and does not list unassigned tickets; the value is not trimmed.
Source: choice: consistent with C-21; the decoding is the URL rule of `URLSearchParams`

### C-45: Any `assignee` filter value is accepted, and one that matches nobody lists nothing
Observable: `?assignee=nobody`, `?assignee=` followed by 65 characters, and `?assignee=%20` answer 200 with `{"items": [], "next": null}` when no ticket has that assignee; none answers 400.
Source: choice: agent names are an open set, unlike statuses and priorities, so no value is out of range

### C-46: Without an `assignee` parameter the listing is not limited by assignee
Observable: `GET /tickets` and `GET /tickets?status=open` list assigned and unassigned tickets alike.
Source: implied: "an empty `assignee=` keeps the unassigned ones" must differ from an absent filter

### C-47: A ticket must match every filter given
Observable: with `T-0001` open/high/`dana`, `T-0002` open/low/`dana`, `T-0003` closed/high/`dana`, `T-0004` open/high/unassigned: `?assignee=dana&status=open` lists `T-0001, T-0002`; `?assignee=dana&priority=high` lists `T-0001, T-0003`; `?assignee=dana&status=open&priority=high` lists `T-0001`; `?assignee=&status=open` lists `T-0004`; `?status=open&priority=high` lists `T-0001, T-0004`. The service today lists a ticket that matches any one of the filters given (src/tickets/query.js `matchesFilters`, `given.some`), which contradicts docs/api.md; it must list only those matching all of them, for `status` with `priority` too.
Source: request ("a ticket must match every filter given"); existing: docs/api.md ("a ticket is listed only when it matches every filter given")

### C-48: A filtered listing pages in id order with cursors
Observable: `?assignee=dana&limit=2` over five of `dana`'s tickets amid others answers two items in id order and a `next`; following `?assignee=dana&limit=2&cursor=<next>` gives the next two, then the last one with `next: null`; no ticket is repeated or skipped.
Source: existing: docs/api.md (List tickets), docs/decisions/0005-cursor-pagination.md

### C-49: When `assignee` is given more than once, the first is used
Observable: `?assignee=dana&assignee=li` lists the same tickets as `?assignee=dana`.
Source: choice: the existing `status` and `priority` filters read the first value (`URLSearchParams.get`)

### C-50: The existing listing parameters keep their rules next to the new one
Observable: `?assignee=dana&status=done`, `&priority=critical`, `&limit=0`, `&limit=101`, `&limit=x` and `&cursor=abc` each answer 400 `invalid`; `?limit=100` is accepted; the default page size is 20; `?offset=40` is ignored.
Source: existing: docs/api.md (List tickets), test/query.test.js

### C-51: Assigning a ticket queues one notification for the agent
Observable: after an assignment that sets the assignee to `dana` (from unassigned or from another agent), `GET /admin/outbox` has, in `pending`, one new event with `to` `"dana"` and `ticket` `"T-0007"`, present as soon as the 200 is answered and without the worker running.
Source: request ("The agent a ticket is assigned to is notified that it was assigned to them"); existing: docs/decisions/0006

### C-52: The assignment notification is delivered, not left dead
Observable: with the worker on and a working notifier, the event reaches `sent` in `GET /admin/outbox` (never `dead`), and with `NOTIFY_FILE` one line is appended for it with `"to": "dana"` and `"ticket": "T-0007"`; its `subject` and `body` are non-empty and both name the ticket id `T-0007`, and the body names the ticket's title. The wording is otherwise open.
Source: existing: src/templates.js (a type with no template goes dead) and CONTRIBUTING.md ("A new kind of notification needs a template"); choice: the ticket id so the agent knows which ticket

### C-53: The assignment notification has the type `ticket.assigned`
Observable: the outbox event and the notification line carry `"type": "ticket.assigned"`.
Source: choice: follows the existing `ticket.created` and `ticket.resolved` names; a consumer such as the mail relay needs a stable type to tell it from the others

### C-54: Reassigning notifies only the new agent
Observable: assigning `dana`'s ticket to `li` adds one event with `to` `"li"`; no event is added for `dana`.
Source: request (the agent assigned to is notified); choice: the request names no notice to a former assignee

### C-55: Unassigning notifies no one
Observable: `PUT` with `{"assignee": null}` that changes the assignee adds no outbox event.
Source: request (a notification only "that it was assigned to them")

### C-56: The requester is not notified of an assignment
Observable: an assignment adds no event addressed to the ticket's `requester` (unless the requester's name is itself the assigned agent's name, in which case the one event is the agent's).
Source: choice: the request notifies only the agent

### C-57: A change that changes nothing queues no notification
Observable: the repeated assignment of C-6 and the repeated unassignment of C-7 add no outbox event, and a 409, 404 or 400 answer adds none (C-27).
Source: existing: CONTRIBUTING.md; request

### C-58: Each assignment that changes the assignee gets its own notification, even while an earlier one is still pending
Observable: with the worker off, `PUT dana`, `PUT li`, `PUT dana` on one ticket gives three pending events, in order `to` `dana`, `li`, `dana`; unassign then assign `dana` again gives a second event for `dana`; their `key` values all differ. The outbox must not fold them into one by its pending-key rule (decision 6), which would silently drop the notification of the second agent.
Source: implied: "the agent a ticket is assigned to is notified"; existing: src/outbox.js (`enqueue` returns the pending event with the same key) and src/store.js (`notify`'s default key `type:ticket`)

### C-59: A queued assignment notification is not withdrawn when the ticket changes hands again
Observable: `dana`'s pending event stays pending, and is delivered, after the ticket is reassigned to `li`, unassigned, or resolved.
Source: choice: the outbox only ever sends or fails an event (decision 6); the event records what happened at that moment

### C-60: The notification does not make the request slower or fail
Observable: with the worker off (`WORKER_INTERVAL_MS=0`), or with a notification file that cannot be written, the assignment still answers 200; the failure shows only as a pending or dead event.
Source: existing: docs/decisions/0006 (requests never call the notifier)

### C-61: Existing notifications are unchanged
Observable: creating a ticket still queues one `ticket.created` event to the requester; resolving still queues one `ticket.resolved` to the requester (a resolved-reopened-resolved ticket within one pending window still queues one); assignment adds nothing to either.
Source: existing: docs/api.md, docs/operations.md, test/api.test.js

### C-62: Two identical assignments at the same time change the ticket once
Observable: two simultaneous `PUT`s of `{"assignee": "dana"}` to one open ticket both answer 200 with `"dana"`; the audit log has one assignment entry for it and the outbox one event.
Source: implied: "a thing done twice that should happen once"; runtime: the service is one Node.js process and runs each change in one step

### C-63: Two different assignments at the same time leave the later one
Observable: simultaneous `PUT`s of `dana` and `li` both answer 200; the ticket shows whichever was applied last (one of the two, never a mix), there are two assignment entries with the second's `from` equal to the first's `to`, and two events, one for each agent.
Source: implied: each effective change is audited and notified

### C-64: An assignment at the same time as a resolution is consistent
Observable: a `PUT` of `dana` racing a `transition` to `resolved` on an in-progress ticket ends one of two ways: the assignment applied first (200, then the ticket is `resolved` and `dana`'s) or the resolution applied first (the `PUT` answers 409 and the ticket is `resolved` and unassigned). No other result, and no audit entry for a refused request.
Source: implied: C-8 and the state rule

### C-65: The assignee is kept in the data file
Observable: with `DATA_FILE`, after an assignment the file's ticket record has `assignee` before the 200 is answered; after a restart `GET /tickets/T-0007` shows the same assignee, including for resolved and closed tickets, and `?assignee=dana` lists the same tickets.
Source: implied: README.md (the data file keeps state across restarts); existing: docs/decisions/0008 ("a field added to a ticket is added there too, or it is lost at the next restart")

### C-66: A data file from before this change loads
Observable: a version 1 data file whose ticket records have no `assignee` starts the service; every ticket is unassigned; nothing else (tickets, audit, outbox, next number) is lost; the file's `version` stays 1 and a file the new service writes has no new top-level field, so the previous version can still read it.
Source: existing: docs/decisions/0008 (the format has a version; files of the previous version must load); choice: no version bump, so going back to 1.4.0 still starts (it ignores `assignee`, which stays in the audit log)

### C-67: A data file with an unusable assignee is refused
Observable: a ticket record whose `assignee` is a number, `""`, whitespace only, 65 characters long or has a control character (and is not `null` and not absent) stops the start with `<file>: tickets[<index>].assignee is not ...` naming the field; the service does not listen.
Source: existing: README.md and docs/operations.md ("At start the service checks every record")

### C-68: Queued assignment notifications survive a restart
Observable: with `DATA_FILE` and the worker off, an assignment's pending event is still pending after a restart, and with the worker on it is delivered once.
Source: existing: docs/decisions/0006 and docs/decisions/0008 (the outbox is saved with the change)

### C-69: The command line's raw listing carries the assignee after the title
Observable: `node bin/tickets.js --data FILE list --raw` prints per ticket one line of five tab-separated fields: id, status, priority, title, assignee, in that order; the first four are what they were; the fifth is empty for an unassigned ticket.
Source: request ("The command-line listing shows each ticket's assignee"); existing: README.md ("scripts/weekly-report.js ... reads these columns by position, so they must keep their positions"); choice: the fifth position and an empty value

### C-70: The command line's table shows the assignee
Observable: `node bin/tickets.js --data FILE list` prints a header line with `ASSIGNEE` among the column titles; each ticket's row shows its agent's name under it, and a placeholder, `-`, for an unassigned ticket; the other columns keep their titles and order; `no tickets` still prints for none.
Source: request; choice: `-` as the placeholder, so the column is never blank or reads `null`

### C-71: The command line's `show` prints the assignee
Observable: `node bin/tickets.js --data FILE show T-0007` prints a line with the label `assignee` and the agent's name (or `-` when unassigned) with the other fields, and the history line of an assignment change names the field `assignee`.
Source: implied: "Every ticket shows its assignee"; choice: label and placeholder

### C-72: The weekly report is unchanged
Observable: `node scripts/weekly-report.js --data FILE --json` prints the same `total`, `byStatus` and `byPriority` counts for the same tickets whether or not any is assigned, and exits 0; the text form lists the same sections.
Source: existing: scripts/weekly-report.js, README.md

### C-73: The rest of the command line keeps working
Observable: `list --status S`, `--priority P`, `--raw`, `--data`, `-h`; the `DATA_FILE` fallback; the exit codes (0 done, 1 no such ticket, 2 usage or data file problem); and read-only access (the data file is never written by it) are as before.
Source: existing: bin/tickets.js and README.md

### C-74: Existing endpoints answer as before, apart from the new field
Observable: `GET /health`, `POST /tickets`, `GET /tickets/:id`, `PATCH /tickets/:id`, `POST /tickets/:id/transition`, `GET /tickets/:id/audit` and `GET /admin/outbox` answer the same statuses, codes and bodies as before, a ticket body only gaining `assignee`; a closed ticket still refuses `PATCH` with 409; a resolved ticket still accepts it.
Source: request ("Everything the service already does keeps working"); existing: docs/api.md

### C-75: The existing tests pass as they are
Observable: `npm test` run on the repository with the existing files under test/ unmodified exits 0 with no existing test failing or skipped.
Source: request

### C-76: New node:test tests under test/ cover the new behaviour, and `npm test` runs them with the old
Observable: new test files (or new tests in new files) under test/ use `node:test`; `npm test` exits 0 and lists them; between them they exercise assigning, unassigning, reassigning, the no-change case, the state refusals, the name limits (64 and 65), the body errors, the notification, the filter (alone and combined), persistence of the assignee and the command line's listing.
Source: request

### C-77: The service still has no dependencies
Observable: `package.json` has no `dependencies` and no `devDependencies`, and `npm start` runs `node src/server.js` on `PORT` using only Node's standard library (Node.js 22 or later).
Source: existing: CONTRIBUTING.md and README.md

### C-78: docs/api.md describes the new behaviour
Observable: docs/api.md shows the `assignee` field of the ticket, the `PUT /tickets/:id/assignee` endpoint with its body, its 400/404/409 cases and the no-change rule, the `assignee` listing parameter including the empty value, the assignment audit entries and the `ticket.assigned` notification.
Source: existing: CONTRIBUTING.md ("a change of behaviour comes with ... "; docs/api.md is the API's document)

### C-79: The changelog and version record the change
Observable: `CHANGELOG.md` has a new top section for 1.5.0 that mentions ticket assignment, and `package.json` `version` is `1.5.0`.
Source: existing: CONTRIBUTING.md (Releases); choice: a minor version, as 1.1.0 was for `PATCH`
