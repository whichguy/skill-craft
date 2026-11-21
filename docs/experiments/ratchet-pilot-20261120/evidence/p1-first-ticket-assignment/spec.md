### C-1: An open ticket can be assigned through `PUT /tickets/:id/assignee`.
Observable: Create open ticket `T-0001`, then PUT `{"assignee":"Dana"}` to `/tickets/T-0001/assignee`. The returned ticket has `"assignee":"Dana"`.
Source: request

### C-2: An in-progress ticket can be assigned through `PUT /tickets/:id/assignee`.
Observable: Move `T-0001` to `in_progress`, then PUT `{"assignee":"Dana"}` to `/tickets/T-0001/assignee`. The returned ticket has `"assignee":"Dana"`.
Source: request

### C-3: An open ticket can be unassigned through `PUT /tickets/:id/assignee`.
Observable: Given an open ticket assigned to `Dana`, PUT `{"assignee":null}` to its assignee endpoint. The returned ticket has `"assignee":null`.
Source: request

### C-4: An in-progress ticket can be unassigned through `PUT /tickets/:id/assignee`.
Observable: Given an `in_progress` ticket assigned to `Dana`, PUT `{"assignee":null}` to its assignee endpoint. The returned ticket has `"assignee":null`.
Source: request

### C-5: A new assignment replaces the current assignee.
Observable: PUT `{"assignee":"Sam"}` to the assignee endpoint of an open ticket assigned to `Dana`. A subsequent GET of the ticket has the one string value `"assignee":"Sam"`.
Source: request

### C-6: A successful assignee PUT returns the full ticket with HTTP 200.
Observable: After any valid assignee PUT on an active ticket, the response is 200 with the same ticket object as an immediate `GET /tickets/:id`, with keys `id`, `title`, `priority`, `requester`, `status`, `created`, `updated`, `assignee`.
Source: choice: Match the response of the existing ticket mutation endpoints.

### C-7: A resolved ticket rejects every well-formed assignee PUT.
Observable: For an existing `resolved` ticket assigned to `Dana`, PUT `{"assignee":"Sam"}`, `{"assignee":"Dana"}` or `{"assignee":null}`. Each responds 409 with `error.code` equal to `conflict`. Clearing an already unassigned `resolved` ticket returns the same error.
Source: request

### C-8: A closed ticket rejects every well-formed assignee PUT.
Observable: For an existing `closed` ticket assigned to `Dana`, PUT `{"assignee":"Sam"}`, `{"assignee":"Dana"}` or `{"assignee":null}`. Each responds 409 with `error.code` equal to `conflict`. Clearing an already unassigned `closed` ticket returns the same error.
Source: request

### C-9: An assignee conflict identifies the ticket's status.
Observable: For `T-0001` in `resolved` or `closed`, a well-formed assignee PUT returns `{"error":{"code":"conflict","message":"ticket T-0001 is <status> and cannot change assignee"}}`, with `<status>` replaced by the current status.
Source: choice: State errors give the operator the reason in the same style as ticket PATCH.

### C-10: A well-formed assignee PUT for a missing ticket returns the usual ticket lookup error.
Observable: PUT `{"assignee":"Dana"}` to `/tickets/T-0042/assignee` when the ticket is absent. The response is 404 with `{"error":{"code":"not_found","message":"ticket T-0042 not found"}}`. A path ID of `42` likewise yields `ticket 42 not found`.
Source: existing: src/store.js

### C-11: Invalid assignee PUT bodies are rejected before ticket lookup.
Observable: PUT `{}` to `/tickets/T-0042/assignee` when the ticket is absent. The response is 400 `invalid`.
Source: existing: src/app.js

### C-12: An assignee PUT requires the `assignee` field.
Observable: PUT `{}` to an existing ticket's assignee endpoint. The response is 400 `invalid` with message `assignee must be a string or null`.
Source: request

### C-13: A non-null assignee must be a string.
Observable: PUT `{"assignee":0}`, `{"assignee":false}`, `{"assignee":[]}` or `{"assignee":{}}`. Each responds 400 `invalid` with message `assignee must be a string or null`.
Source: request

### C-14: An assignee PUT rejects unknown body fields.
Observable: PUT `{"assignee":"Dana","owner":"Sam"}`. The response is 400 `invalid` with message `unknown field: owner`.
Source: existing: docs/api.md

### C-15: An agent name is stored after trimming leading and trailing whitespace.
Observable: PUT `{"assignee":"  Dana Lee  "}` to an active ticket. Its assignee in the response is exactly `"Dana Lee"`.
Source: choice: Normalize agent names like the service's existing requester names.

### C-16: The zero-length agent name is invalid.
Observable: PUT `{"assignee":""}`. The response is 400 `invalid` with message `assignee must not be empty`.
Source: request

### C-17: A whitespace-only agent name is invalid.
Observable: PUT `{"assignee":"   "}`. The response is 400 `invalid` with message `assignee must not be empty`.
Source: choice: Apply the non-empty check after the same trim used to store a name.

### C-18: A one-character agent name is valid.
Observable: PUT `{"assignee":"x"}` to an active ticket. The response is 200 with `"assignee":"x"`.
Source: request

### C-19: A 64-character agent name is valid.
Observable: PUT a string of exactly 64 ASCII `a` characters as `assignee` to an active ticket. The response is 200 with that exact string.
Source: request

### C-20: A 65-character agent name is invalid.
Observable: PUT a string of exactly 65 ASCII `a` characters as `assignee`. The response is 400 `invalid` with message `assignee must be at most 64 characters`.
Source: request

### C-21: Agent-name length is measured in UTF-16 code units after trimming.
Observable: PUT a name consisting of 32 `😀` characters surrounded by spaces to an active ticket. The 64-code-unit trimmed name is accepted. A name consisting of 33 `😀` characters is rejected as 400 `invalid`.
Source: choice: Use the same JavaScript string length convention as the existing 64-character requester limit.

### C-22: Agent names follow the existing single-line text convention.
Observable: For each U+0000 through U+001F and U+007F, PUT an assignee with that character between `Dana` and `Lee`. Each responds 400 `invalid` with message `assignee must be a single line of text`.
Source: choice: Use the existing requester string rule so a name cannot introduce a tab or newline into the CLI listing.

### C-23: Agent-name identity is case-sensitive.
Observable: On an active ticket assigned to `Dana`, PUT `{"assignee":"dana"}`. A subsequent GET returns `"assignee":"dana"` as a changed value.
Source: choice: Preserve spelling and use exact equality on trimmed names, consistent with existing filter comparisons.

### C-24: Assigning the current agent again is a no-op on an active ticket.
Observable: Assign `Dana`, advance the clock, then PUT `{"assignee":" Dana "}` while the ticket is active. The response ticket is exactly equal to the ticket before the repeat, including `updated`.
Source: request

### C-25: Unassigning an already unassigned active ticket is a no-op.
Observable: Advance the clock after creation, then PUT `{"assignee":null}` to the still-open ticket's assignee endpoint. The response ticket is exactly equal to the ticket before the PUT, including `updated`.
Source: choice: Apply the existing unchanged-value convention to a repeated clear.

### C-26: A no-op assignee PUT appends no audit entry.
Observable: Compare `GET /tickets/:id/audit` before and after assigning the current name again or clearing an already null assignee on an active ticket. The response bodies are identical.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-27: A no-op assignee PUT queues no notification.
Observable: With the worker disabled, compare `GET /admin/outbox` before and after assigning the current name again or clearing an already null assignee. The response bodies are identical.
Source: existing: CONTRIBUTING.md

### C-28: A no-op assignee PUT leaves the configured data file untouched.
Observable: With the worker disabled, compare the data file before and after assigning the current name again or clearing an already null assignee. File contents and modification time are unchanged.
Source: existing: src/store.js

### C-29: A rejected assignee PUT leaves the ticket unchanged.
Observable: Compare the existing ticket's GET response immediately before and after an assignee PUT that fails with 400 or 409. The two ticket bodies are identical.
Source: existing: src/store.js

### C-30: A rejected assignee PUT appends no audit entry.
Observable: With the worker disabled, compare the stored audit log before and after 400, 404 or 409 responses to assignee PUTs. Its contents are identical.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-31: A rejected assignee PUT queues no notification.
Observable: With the worker disabled, compare `GET /admin/outbox` before and after 400, 404 or 409 responses to assignee PUTs. The response bodies are identical.
Source: existing: CONTRIBUTING.md

### C-32: A real assignee change updates the ticket's `updated` timestamp.
Observable: Start with `updated` equal to `2025-09-01T08:00:00.000Z`. At `2025-09-01T08:01:00.000Z`, assign, reassign or clear a currently assigned ticket. The returned `updated` is `2025-09-01T08:01:00.000Z`.
Source: existing: docs/api.md

### C-33: An assignee change preserves the ticket fields outside `assignee` and `updated`.
Observable: Compare a ticket immediately before and after a successful assignee change. Its `id`, `title`, `priority`, `requester`, `status` and `created` values are identical.
Source: choice: The assignee endpoint edits one field apart from the existing last-change timestamp.

### C-34: Newly created tickets are unassigned.
Observable: POST a valid new ticket. Its 201 ticket body contains `"assignee":null`.
Source: request

### C-35: GET of an individual ticket exposes its current assignee.
Observable: `GET /tickets/T-0001` returns the `assignee` key with `null` before assignment, `"Dana"` after assigning Dana, and `null` again after clearing.
Source: request

### C-36: Every list item exposes its current assignee.
Observable: Given unassigned `T-0001` and `T-0002` assigned to `Dana`, `GET /tickets` returns the item values `null` and `"Dana"`, respectively, at the `assignee` key.
Source: request

### C-37: PATCH leaves the current assignee on the returned ticket.
Observable: PATCH `{"priority":"urgent"}` on a non-closed ticket assigned to `Dana`. The 200 response and subsequent GET both contain `"assignee":"Dana"`. On an unassigned ticket, the same operation exposes `"assignee":null`.
Source: request

### C-38: Lifecycle transitions preserve the current assignee.
Observable: Assign `Dana` to an open ticket, then move it through `in_progress`, `resolved` and `closed`. Each 200 transition response contains `"assignee":"Dana"`. On a separate assigned ticket, the allowed `resolved` to `open` transition also returns its existing name. An unassigned ticket's transition response contains `"assignee":null`.
Source: choice: Assignment is independent of lifecycle changes, including closing and reopening.

### C-39: POST creation continues to reject an `assignee` input field.
Observable: POST `{"title":"VPN","requester":"Lee","assignee":"Dana"}` to `/tickets`. The response is 400 `invalid` with message `unknown field: assignee`.
Source: existing: src/tickets/validate.js

### C-40: PATCH continues to reject an `assignee` input field.
Observable: PATCH `{"assignee":null}` to `/tickets/T-0001`. The response is 400 `invalid` with message `unknown field: assignee`.
Source: existing: src/tickets/validate.js

### C-41: The transition endpoint continues to reject an `assignee` input field.
Observable: POST `{"to":"in_progress","assignee":"Dana"}` to `/tickets/T-0001/transition`. The response is 400 `invalid` with message `unknown field: assignee`.
Source: existing: src/tickets/validate.js

### C-42: A real assignee change appends exactly one audit entry.
Observable: After a real assign, reassign or unassign on `T-0001`, `GET /tickets/T-0001/audit` has exactly one additional entry with `ticket:"T-0001"`. Its `at` equals the new ticket `updated`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-43: An assignment audit entry uses action `ticket.assigned`.
Observable: A first assignment or a reassignment appends an entry whose `action` value is exactly `"ticket.assigned"`.
Source: choice: Follow the existing `ticket.<event>` action naming for setting an assignee.

### C-44: An unassignment audit entry uses action `ticket.unassigned`.
Observable: Clearing a named assignee appends an entry whose `action` value is exactly `"ticket.unassigned"`.
Source: choice: Give removal a distinct action in the same naming convention.

### C-45: An assignee audit entry records only the old and new assignee values in `changes`.
Observable: Make the assignee transitions null to Dana, Dana to Sam, and Sam to null. The corresponding `changes` objects are exactly `{"assignee":{"from":null,"to":"Dana"}}`, `{"assignee":{"from":"Dana","to":"Sam"}}`, and `{"assignee":{"from":"Sam","to":null}}`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-46: An actual assignment queues one notification to the new assignee.
Observable: With the worker disabled, compare the outbox before and after assigning an active ticket to `Dana`, including when replacing `Sam`. There is exactly one new event, with `to:"Dana"` and `ticket` equal to the ticket ID.
Source: request

### C-47: An assignment notification uses type `ticket.assigned`.
Observable: `GET /admin/outbox` reports the event caused by a named assignment with `type:"ticket.assigned"`.
Source: choice: Follow the outbox's existing `ticket.<event>` type naming.

### C-48: Each distinct assignment gets its own pending notification key.
Observable: With the worker off, assign `T-0001` successively to `Dana`, `Sam` and `Dana` again. The three assignment events stay pending with recipients `Dana`, `Sam`, `Dana` in that order. Each has key `ticket.assigned:T-0001:<seq>`, substituting that assignment's audit sequence number.
Source: choice: The audit sequence distinguishes separate assignments even for the same recipient while prior notifications are pending.

### C-49: An assignment event captures the ticket title at assignment time.
Observable: Assign `T-0001` while its title is `VPN drops`. Its event has `data:{"title":"VPN drops"}` even after a subsequent title PATCH.
Source: existing: src/store.js

### C-50: Clearing the assignee leaves the outbox unchanged.
Observable: With the worker off, clear a non-null assignee. The outbox before and after that PUT is identical, including any pending notification created by the earlier assignment.
Source: choice: The request calls for notifying the agent who receives the assignment. Clearing has no recipient and existing events stay queued.

### C-51: Assignment delivery tells the recipient that the ticket was assigned to them.
Observable: Enable the worker with a writable `NOTIFY_FILE`. The line delivered for assigning ticket `T-0001` titled `VPN drops` to `Dana` has `type:"ticket.assigned"`, `to:"Dana"`, `ticket:"T-0001"`, subject `[T-0001] Assigned to you`, and body `Ticket T-0001 "VPN drops" was assigned to you.`.
Source: choice: Use an assignment template with the ticket ID and captured title, following the existing notification style.

### C-52: Resuming service preserves a saved named assignee.
Observable: With `DATA_FILE` configured, assign `T-0001` to `Dana` and restart. GET of that ticket returns `"assignee":"Dana"`.
Source: existing: docs/decisions/0008-json-data-file.md

### C-53: Resuming service preserves a saved cleared assignee.
Observable: With `DATA_FILE` configured, clear `Dana` from `T-0001` and restart. GET of that ticket returns `"assignee":null`.
Source: existing: docs/decisions/0008-json-data-file.md

### C-54: A saved assignment is recorded with its audit entry and its outbox event in one file replacement.
Observable: With the worker disabled and `DATA_FILE` set, immediately after an assignment's 200 response, a single read of the JSON file finds the new `tickets[].assignee`, the corresponding entry in `audit`, and the corresponding pending event in `outbox.events`. A read racing that replacement sees a complete before-state or after-state.
Source: existing: docs/decisions/0008-json-data-file.md

### C-55: Version-1 ticket records that omit `assignee` load as unassigned.
Observable: Start from a version-1 file written before assignment existed. GET of an old ticket that omits that key returns `"assignee":null`; it also appears in the unassigned listing and has the same preexisting audit history.
Source: existing: docs/decisions/0008-json-data-file.md

### C-56: Newly saved ticket records explicitly contain `assignee`.
Observable: In the version-1 JSON written by a save, every ticket has an `assignee` key. Its value is the exact current name string or JSON null, including for previously loaded tickets that omitted the field.
Source: choice: Write the full current ticket using the existing version-1 document shape.

### C-57: A present but invalid stored assignee prevents startup.
Observable: In an otherwise valid data file, set `tickets[0].assignee` to a number, boolean, object, array, empty string, untrimmed name, name longer than 64 UTF-16 code units or name with a prohibited control character. Startup exits 2 with stderr including the path followed by `: tickets[0].assignee must be null or a valid agent name`.
Source: choice: Allow legacy omission while requiring an explicitly stored value to match the canonical ticket representation.

### C-58: A named assignee query keeps tickets with that exact current assignee.
Observable: Given ticket assignees `Dana Lee`, `dana Lee`, `Dana Lee Jr` and null, `GET /tickets?assignee=Dana%20Lee` responds 200 with only the first ticket.
Source: request

### C-59: An empty assignee query keeps only unassigned tickets.
Observable: Given tickets assigned to `Dana` plus an unassigned one, `GET /tickets?assignee=` responds 200 with only the ticket whose assignee is JSON null.
Source: request

### C-60: Omitting the assignee query leaves the list unrestricted by assignee.
Observable: Given one assigned and one unassigned ticket, `GET /tickets` with no other filters returns both in `items`.
Source: request

### C-61: All supplied list filters are combined by intersection.
Observable: Use four tickets in ascending ID order with respective `(status, priority, assignee)` values `(open, urgent, Dana)`, `(in_progress, urgent, Dana)`, `(open, low, Dana)` and `(open, urgent, null)`. `GET /tickets?status=open&priority=urgent&assignee=Dana` returns only `T-0001`. Replacing `assignee=Dana` with `assignee=` returns only `T-0004`.
Source: request

### C-62: Assignee queries select by current value independently of lifecycle status.
Observable: Assign `Dana` to a ticket, then move it to `closed`. `GET /tickets?assignee=Dana` still includes it, as does `GET /tickets?assignee=Dana&status=closed`.
Source: request

### C-63: A non-empty assignee query normalizes a name in the same way as an assignee PUT.
Observable: `GET /tickets?assignee=+Dana+Lee+` matches the stored name `Dana Lee` after decoding and trimming, with case and interior spacing preserved.
Source: choice: Accept the same name spelling at the write and read boundaries.

### C-64: Non-empty assignee queries that fail name validation are invalid.
Observable: Each of `assignee=++`, `assignee=Dana%09Lee` and `assignee=` followed by 65 ASCII `a` characters returns 400 `invalid`. A value of exactly 64 ASCII `a` characters is accepted.
Source: choice: Validate a non-empty query value like an agent name, reserving the decoded zero-length value for unassigned tickets.

### C-65: A bare assignee parameter is equivalent to an empty assignee parameter.
Observable: `GET /tickets?assignee` has the same response as `GET /tickets?assignee=`.
Source: choice: Use the existing query parser's decoded representation, in which both spellings have a present zero-length value.

### C-66: A repeated recognized list parameter uses its first value.
Observable: `GET /tickets?assignee=Dana&assignee=Sam` has the same response as `GET /tickets?assignee=Dana`. The first-value convention also continues for `status`, `priority`, `limit` and `cursor`.
Source: existing: src/tickets/query.js

### C-67: The CLI table displays each ticket's current assignee.
Observable: Run `node bin/tickets.js list` on a file containing a ticket assigned to `Dana Lee`. Its `ASSIGNEE` cell contains the full name `Dana Lee`.
Source: request

### C-68: The table places `ASSIGNEE` after `TITLE`.
Observable: For a non-empty table the column labels in order are `ID`, `STATUS`, `PRIORITY`, `REQUESTER`, `UPDATED`, `TITLE`, `ASSIGNEE`.
Source: choice: Append the new column so the existing columns retain their order.

### C-69: The first four raw CLI columns retain their positions.
Observable: Given ticket `T-0001` with status `open`, priority `urgent` and title `VPN drops`, the first four tab-separated values of its `list --raw` line are `T-0001`, `open`, `urgent`, `VPN drops` in that order.
Source: existing: README.md

### C-70: Raw CLI listing appends the current assignee as the fifth tab-separated column.
Observable: With only an open urgent `T-0001` titled `VPN drops` and assigned to `Dana Lee`, `list --raw` stdout is `T-0001\topen\turgent\tVPN drops\tDana Lee\n`. If unassigned, stdout is `T-0001\topen\turgent\tVPN drops\t\n`. Here `\t` and `\n` denote literal tab and newline characters.
Source: choice: Extend the listing while preserving the report's positional input. An empty fifth field represents null without colliding with a valid name.

### C-71: CLI `show` presents the assignee in the full ticket details.
Observable: `node bin/tickets.js show T-0001` prints a field labeled `assignee` after `updated` and before the `History` section. The field's value is the current name or blank for an unassigned ticket.
Source: choice: Follow the existing full-ticket presentation and the human-readable list's blank value for null.

### C-72: The CLI retains its existing set of list options.
Observable: `node bin/tickets.js list --assignee Dana` exits 2 with stderr starting `tickets: unknown option --assignee`.
Source: choice: The requested filter belongs to the HTTP API. The CLI change is to ticket display.

### C-73: New assignment behavior is covered by `node:test` files under `test/`.
Observable: Inspect the new test files under `test/` for `node:test` cases covering assignment, unassignment, validation, state restrictions, no-ops, ticket representations, notifications, filtering, persistence and CLI output.
Source: request

### C-74: `npm test` discovers the assignment tests.
Observable: Run `npm test`. Its `node --test` output includes the new assignment cases alongside the existing cases.
Source: request

### C-75: The original test files stay unchanged.
Observable: Compare the pre-feature files under `test/` with the built feature. Their contents are byte-for-byte equal.
Source: request

### C-76: The original test suite still passes.
Observable: Run `npm test` on the built feature. Every preexisting test passes, with exit 0 for the suite.
Source: request

### C-77: The service retains its dependency-free Node.js runtime.
Observable: `package.json` declares no npm dependencies. With Node.js 22 or later, `npm start` runs `node src/server.js` without a package installation.
Source: existing: README.md

### C-78: The service listens on the configured `PORT`.
Observable: Start with `PORT=0`. The startup log identifies the assigned TCP port and `GET /health` works there. The declared port default is 4180 for an unset or empty `PORT`.
Source: existing: README.md

### C-79: An unusable numeric configuration setting stops startup.
Observable: Set `PORT=http` or `PORT=65536`. Each process exits 2 with a stderr line naming `PORT`. Accepted port values are whole numbers from 0 through 65535.
Source: existing: src/config.js

### C-80: Requests can be logged to standard error using `LOG_REQUESTS=1`.
Observable: With `LOG_REQUESTS=1`, an assignee PUT produces one request log line with the method, URL, status and elapsed milliseconds. When unset or empty, request logging is off.
Source: existing: docs/operations.md

### C-81: `SIGTERM` shuts the service down cleanly.
Observable: A running process receiving `SIGTERM` stops its worker, lets in-flight requests finish and saves configured state before exiting 0.
Source: existing: docs/operations.md

### C-82: `GET /health` returns the health response.
Observable: GET `/health` responds 200 with exactly `{"status":"ok"}`.
Source: existing: src/app.js

### C-83: API responses use the existing JSON media type.
Observable: An API success or error has `content-type: application/json; charset=utf-8`, including on the assignee route.
Source: existing: docs/api.md

### C-84: API errors use the existing error envelope.
Observable: An invalid request, missing resource or state conflict has an `error` object containing a string `code` and a human-readable string `message`, with the established mappings `invalid` to 400, `not_found` to 404, `conflict` to 409 and `internal` to 500.
Source: existing: docs/decisions/0004-error-envelope.md

### C-85: Unexpected request faults have the existing generic error response.
Observable: Trigger an unexpected handler exception. The response is 500 with exactly `{"error":{"code":"internal","message":"internal error"}}`.
Source: existing: src/errors.js

### C-86: An unknown route returns the existing route-not-found response.
Observable: GET `/nowhere` returns 404 with `{"error":{"code":"not_found","message":"no route for GET /nowhere"}}`.
Source: existing: src/app.js

### C-87: A recognized path with an unsupported method returns the method-specific route-not-found response.
Observable: GET `/tickets/T-0001/assignee` returns 404 with `{"error":{"code":"not_found","message":"/tickets/T-0001/assignee does not answer GET; it answers PUT"}}`.
Source: existing: src/app.js

### C-88: A route accepts a single optional trailing slash.
Observable: PUT a valid assignee body to `/tickets/T-0001/assignee/` on an active ticket. The outcome matches the same PUT without the final slash.
Source: existing: src/router.js

### C-89: Path parameters are percent-decoded before lookup.
Observable: PUT a valid assignee body to `/tickets/T%2D0001/assignee`. The request targets `T-0001`.
Source: existing: src/router.js

### C-90: Malformed percent-encoding in a matched path parameter is invalid.
Observable: PUT to `/tickets/%E0%A4%A/assignee`. The response is 400 `invalid` with message `path segment %E0%A4%A is not valid percent-encoding`.
Source: existing: src/router.js

### C-91: A parameter occupies a single path segment.
Observable: PUT to `/tickets/T-0001/extra/assignee`. The response is 404 `not_found`.
Source: existing: src/router.js

### C-92: A JSON-writing endpoint requires an object body.
Observable: PUT no body, whitespace only, `null`, `[]`, `"Dana"`, `1` or `true` to the assignee route. Each returns 400 `invalid` with message `request body must be a JSON object`.
Source: existing: src/http.js

### C-93: Malformed JSON is rejected by the common body reader.
Observable: PUT raw text `{"assignee":` to the assignee route. The response is 400 `invalid` with message `request body is not valid JSON`.
Source: existing: src/http.js

### C-94: The body reader enforces the configured byte limit inclusively.
Observable: With the default `MAX_BODY_BYTES` of 65536, a valid assignee object padded with JSON whitespace to 65536 UTF-8 bytes is accepted on an active ticket. One more byte produces 400 `invalid` with message `request body is larger than 65536 bytes`. With `MAX_BODY_BYTES=1024`, the corresponding boundary is 1024 versus 1025 bytes.
Source: existing: src/http.js

### C-95: `MAX_BODY_BYTES` has the existing configuration range.
Observable: Startup accepts whole-number settings from 1024 to 1048576 inclusive. Values 1023 or 1048577 cause exit 2 with a message naming `MAX_BODY_BYTES`.
Source: existing: src/config.js

### C-96: An audit actor supplied by the client is trimmed.
Observable: Send `X-Actor:   ops-user  ` with any actual assignee change. The appended entry has `"actor":"ops-user"`.
Source: existing: src/http.js

### C-97: An absent or blank audit actor defaults to `system`.
Observable: Omit `X-Actor` on one assignee change and send an all-spaces value on a second. Both entries have `"actor":"system"`.
Source: existing: src/http.js

### C-98: An audit actor is limited to 64 characters.
Observable: An assignee PUT on an active ticket accepts an `X-Actor` value of 64 ASCII `a` characters. A value of 65 ASCII `a` characters returns 400 `invalid` with message `X-Actor must be at most 64 characters`.
Source: existing: src/http.js

### C-99: Ticket IDs are allocated as a positive sequence starting at 1.
Observable: Consecutive creations in an empty service return HTTP 201 tickets with IDs `T-0001`, `T-0002`, and so on. Following `T-9999`, the next ID is `T-10000`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-100: Previously allocated ticket numbers are retained across restarts.
Observable: Create `T-0001` with persistence enabled, change its assignee, then restart. The next creation returns `T-0002`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-101: A valid POST to `/tickets` opens a ticket.
Observable: POST `{"title":"VPN","requester":"Lee"}` to `/tickets`. It returns 201 with a ticket whose `status` is `open`.
Source: existing: docs/api.md

### C-102: Creation defaults omitted priority to `normal`.
Observable: POST a valid title and requester with no priority. Its ticket has `"priority":"normal"`.
Source: existing: docs/api.md

### C-103: Creation and PATCH validate priority against the existing vocabulary.
Observable: For applicable requests, each of `low`, `normal`, `high`, `urgent` is accepted. A supplied value of `critical`, `HIGH` or null is 400 `invalid`.
Source: existing: src/tickets/validate.js

### C-104: Ticket creation requires a title string.
Observable: POST a new ticket with no `title`, or with a non-string `title`. The response is 400 `invalid` with message `title must be a string`.
Source: existing: src/tickets/validate.js

### C-105: Ticket creation requires a requester string.
Observable: POST a new ticket with no `requester`, or with a non-string `requester`. The response is 400 `invalid` with message `requester must be a string`.
Source: existing: src/tickets/validate.js

### C-106: Title and requester input follow the existing trimmed single-line text convention.
Observable: Creation with `"title":"  VPN drops  "` and `"requester":"  Lee  "` stores `VPN drops` and `Lee`. A supplied string that trims to empty or contains U+0000 through U+001F or U+007F after trimming is 400 `invalid`. The same title rule applies to PATCH.
Source: existing: src/tickets/validate.js

### C-107: Title length is limited to 200 trimmed UTF-16 code units.
Observable: A title of 200 ASCII `a` characters is accepted for create or PATCH. At 201 the response is 400 `invalid` with message `title must be at most 200 characters`.
Source: existing: src/tickets/validate.js

### C-108: Requester length is limited to 64 trimmed UTF-16 code units.
Observable: Creation accepts a requester of 64 ASCII `a` characters. At 65 the response is 400 `invalid` with message `requester must be at most 64 characters`.
Source: existing: src/tickets/validate.js

### C-109: A new ticket's timestamps both represent creation time in UTC.
Observable: With the clock at `2025-09-01T08:00:00.000Z`, creation sets both `created` and `updated` to exactly `2025-09-01T08:00:00.000Z`.
Source: existing: src/store.js

### C-110: The creation audit entry retains its original fields.
Observable: The `ticket.created` entry for a new ticket titled `VPN` with requester `Lee` and default priority has exactly `{"title":{"from":null,"to":"VPN"},"priority":{"from":null,"to":"normal"},"requester":{"from":null,"to":"Lee"},"status":{"from":null,"to":"open"}}` as its `changes`.
Source: existing: test/store.test.js

### C-111: An existing ticket can be retrieved by its ID.
Observable: `GET /tickets/T-0001` for an existing ticket responds 200 with the current ticket, including the existing fields `id`, `title`, `priority`, `requester`, `status`, `created` and `updated`.
Source: existing: docs/api.md

### C-112: GET of a missing ticket returns 404.
Observable: `GET /tickets/T-0042` with no such ticket returns 404 `not_found`.
Source: existing: docs/api.md

### C-113: Ticket PATCH accepts title or priority changes on a non-closed ticket.
Observable: On a ticket in `open`, `in_progress` or `resolved`, send valid PATCH bodies with only `title`, only `priority`, or both. Each responds 200 with the full ticket showing the supplied changes.
Source: existing: src/store.js

### C-114: Ticket PATCH requires at least one field.
Observable: PATCH `{}` responds 400 `invalid` with message `nothing to change: give a title or a priority`.
Source: existing: src/tickets/validate.js

### C-115: A closed ticket rejects PATCH.
Observable: PATCH a closed `T-0001` with a valid title or priority, including the existing value. The response is 409 `conflict` with message `ticket T-0001 is closed and can no longer change`.
Source: existing: src/store.js

### C-116: PATCH records only the fields whose values changed.
Observable: For a ticket titled `VPN` with priority `normal`, PATCH `{"title":"VPN","priority":"urgent"}`. The resulting `ticket.updated` entry has exactly `{"priority":{"from":"normal","to":"urgent"}}` as its `changes`.
Source: existing: test/store.test.js

### C-117: PATCH of unchanged values is a no-op.
Observable: Advance the clock, then PATCH an active ticket with its existing title and priority. The 200 ticket body, audit history and outbox are identical to their preceding values.
Source: existing: docs/api.md

### C-118: The transition endpoint accepts the existing lifecycle edges.
Observable: `POST /tickets/:id/transition` with `{"to":"<target>"}` returns 200 with the new status for exactly the allowed pairs `open → in_progress`, `in_progress → resolved`, `resolved → closed` and `resolved → open`.
Source: existing: docs/api.md

### C-119: The transition endpoint rejects forbidden lifecycle edges.
Observable: For any pair of known states outside the four allowed pairs, including the same state twice and each move out of `closed`, the transition responds 409 `conflict`.
Source: existing: src/tickets/states.js

### C-120: A transition requires a recognized `to` value.
Observable: Send `{}` or `{"to":"done"}` to the transition endpoint. Each returns 400 `invalid` with message `to must be one of open, in_progress, resolved, closed`.
Source: existing: src/tickets/validate.js

### C-121: A transition audit entry continues to describe the status change.
Observable: Move an open ticket to `in_progress`. The new `ticket.transitioned` entry has exactly `{"status":{"from":"open","to":"in_progress"}}` as its `changes`.
Source: existing: src/store.js

### C-122: A status filter selects exactly the requested status.
Observable: In a series of tickets with different statuses, `GET /tickets?status=open` returns only `open` tickets. The same exact matching applies to `in_progress`, `resolved` and `closed`.
Source: existing: docs/api.md

### C-123: A priority filter selects exactly the requested priority.
Observable: In a series of tickets with different priorities, `GET /tickets?priority=urgent` returns only `urgent` tickets. The same exact matching applies to `low`, `normal` and `high`.
Source: existing: docs/api.md

### C-124: Invalid status filters return 400.
Observable: `GET /tickets?status=done` or `GET /tickets?status=` returns 400 `invalid` with message `status must be one of open, in_progress, resolved, closed`, including when a valid assignee filter is supplied.
Source: existing: src/tickets/query.js

### C-125: Invalid priority filters return 400.
Observable: `GET /tickets?priority=critical` or `GET /tickets?priority=` returns 400 `invalid` with message `priority must be one of low, normal, high, urgent`, including when a valid assignee filter is supplied.
Source: existing: src/tickets/query.js

### C-126: Unknown list query parameters are ignored.
Observable: With no other query pairs, `GET /tickets?offset=40&sort=title` returns the same first page as `GET /tickets`.
Source: existing: test/query.test.js

### C-127: A list response uses the existing cursor-page shape.
Observable: `GET /tickets` returns 200 with exactly the top-level keys `items` and `next`. With no matches, its body is `{"items":[],"next":null}`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-128: List order follows numeric ticket ID order.
Observable: When all three match, `T-0002`, `T-9999`, `T-10000` appear in that order in the list.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-129: The default list page limit is 20.
Observable: With 23 matching tickets, omitting `limit` returns 20 items on the first page.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-130: The explicit list limit accepts whole numbers from 1 through 100 inclusive.
Observable: With at least 101 matches, `limit=1` returns one item and `limit=100` returns 100 items. Each of `0`, `101`, `-1`, `2.5`, `x` and an empty value returns 400 `invalid` with message `limit must be a whole number from 1 to 100`.
Source: existing: src/tickets/query.js

### C-131: Filtering happens before paging.
Observable: Give `T-0001`, `T-0003` and `T-0005` to `Dana`, with other tickets interleaved. `GET /tickets?assignee=Dana&limit=2` returns `T-0001` and `T-0003` with non-null `next`, even though the first two IDs include a nonmatching ticket.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-132: A cursor resumes strictly after the last returned ticket ID.
Observable: Pass the first page's `next` as `cursor` with the same filters. The earliest matching ticket with ID numerically greater than the prior page's last ID is first on the next page, even if the cursor's referenced ticket has since ceased to match.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-133: The last list page has a null continuation.
Observable: `next` is null when precisely `limit` matching tickets remain, as well as when fewer remain. When more matches remain it is an opaque, version-1 base64url cursor for the last ticket returned.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-134: An unusable list cursor returns 400.
Observable: Send `cursor=`, `cursor=abc`, a cursor with an unsupported version, or one whose decoded sort key is `T-1`. Each responds 400 `invalid` with message `cursor is not one this service issued`.
Source: existing: src/pagination.js

### C-135: Audit entries use a global sequence beginning at 1.
Observable: Create `T-0001`, create `T-0002`, then assign `T-0001`. The item sequence numbers in `T-0001`'s audit are `[1,3]`, and `T-0002`'s creation has `seq:2`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-136: Ticket history retains previous entries in their original order.
Observable: Compare `GET /tickets/T-0001/audit` before and after a successful assignment. The 200 `{"items":[...]}` response contains the same older entries first, followed by the new one, without entries for other tickets.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-137: History for a missing ticket returns 404.
Observable: `GET /tickets/T-0042/audit` with no such ticket returns 404 `not_found`.
Source: existing: test/api.test.js

### C-138: The existing status and priority filters intersect when supplied together.
Observable: With `T-0001` open low, `T-0002` in-progress urgent, and `T-0003` open urgent, `GET /tickets?status=open&priority=urgent` returns only `T-0003`.
Source: existing: docs/api.md

### C-139: Ticket creation still queues the requester notification.
Observable: With the worker off, create `T-0001` with requester `Lee` and title `VPN drops`. One new pending event has `type:"ticket.created"`, `key:"ticket.created:T-0001"`, `to:"Lee"`, `ticket:"T-0001"` and `data:{"title":"VPN drops"}`.
Source: existing: src/store.js

### C-140: Resolving a ticket still queues the requester notification.
Observable: Assign `T-0001` to `Dana` while its requester is `Lee`, then move the ticket to `resolved`. With the worker off, the new event has `type:"ticket.resolved"`, `key:"ticket.resolved:T-0001"`, `to:"Lee"` and `ticket:"T-0001"`.
Source: existing: src/store.js

### C-141: Only creation and resolution still trigger requester notifications.
Observable: With requester `Lee` distinct from the assignee, compare Lee's queued events before and after a title or priority PATCH, an assignment, or a transition to `in_progress`, `open` or `closed`. The events for Lee are identical.
Source: existing: src/store.js

### C-142: The existing requester notification messages retain their wording.
Observable: For `T-0001` titled `VPN drops`, the creation message subject is `[T-0001] We received your request` and body is `Your request "VPN drops" is ticket T-0001. The help desk will be in touch.` The resolution message subject is `[T-0001] Resolved` and body is `Ticket T-0001 "VPN drops" was resolved. Reply within 7 days to reopen it.`
Source: existing: src/templates.js

### C-143: The outbox suppresses a repeated pending key.
Observable: With the worker disabled, resolve, reopen, move to `in_progress` and resolve `T-0001` again. There is one pending event with key `ticket.resolved:T-0001`.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-144: A key can enqueue again after its previous event is sent or dead.
Observable: After the earlier `ticket.resolved:T-0001` event becomes sent or dead, reopen and resolve the ticket again. A pending event with the same key and a fresh event ID appears.
Source: existing: src/outbox.js

### C-145: The admin outbox response groups every event by delivery state.
Observable: GET `/admin/outbox` responds 200 with exactly `pending`, `sent` and `dead` arrays, each containing the records in its state with the existing keys `id`, `key`, `type`, `to`, `ticket`, `data`, `status`, `attempts`, `created`, `nextAttemptAt`, `lastError` and `sentAt`.
Source: existing: docs/api.md

### C-146: A newly enqueued notification uses the existing initial delivery state.
Observable: With the worker off, assign a ticket at `2025-09-01T08:01:00.000Z`. The new event has `status:"pending"`, `attempts:0`, `created` and `nextAttemptAt` equal to that time, with `lastError:null` and `sentAt:null`.
Source: existing: src/outbox.js

### C-147: The outbox allocates event IDs in order.
Observable: In an empty outbox, create a ticket and assign it. The creation event has `id:1` and the assignment event has `id:2`. With persistence enabled, the next event after restart has `id:3`.
Source: existing: src/outbox.js

### C-148: The existing worker handles assignment delivery.
Observable: Immediately after a successful PUT with the worker disabled, the new assignment event is pending and there is no notification line for it. On a successful enabled worker tick, it is delivered through the same notifier as requester events. A failing delivery is recorded against that event without a failed PUT response.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-149: `WORKER_INTERVAL_MS` controls the worker's existing interval.
Observable: The default interval is 500 ms for an unset or empty setting. Startup accepts whole numbers from 0 through 3600000 ms. A value of 3600001 causes exit 2 with a message naming `WORKER_INTERVAL_MS`.
Source: existing: src/config.js

### C-150: A zero worker interval disables automatic delivery.
Observable: Set `WORKER_INTERVAL_MS=0`, configure a fresh `NOTIFY_FILE`, then create and assign a ticket. The notifications stay pending and the notification file is never created while this process runs.
Source: existing: docs/operations.md

### C-151: The file notifier appends one JSON line per delivery.
Observable: Configure `NOTIFY_FILE` and deliver a creation and an assignment. The file contains one newline-terminated JSON record per delivery with keys `at`, `id`, `key`, `type`, `to`, `ticket`, `subject` and `body`.
Source: existing: src/notifier.js

### C-152: The notifier keeps deliveries in memory when no notification file is configured.
Observable: With `NOTIFY_FILE` unset or empty, a successful worker tick appends the delivered record to the notifier's in-memory `delivered` list.
Source: existing: src/notifier.js

### C-153: A successful delivery stays recorded as sent.
Observable: After one successful attempt on a fresh pending assignment event, the admin response shows it under `sent` with `attempts:1`, a UTC `sentAt`, `nextAttemptAt:null` and `lastError:null`. A later worker tick leaves the event sent without a further delivery.
Source: existing: src/outbox.js

### C-154: Failed delivery uses the existing retry schedule.
Observable: Force four consecutive failures on one assignment event. After attempts 1, 2, 3 and 4 it is pending with `nextAttemptAt` respectively 1000, 2000, 4000 and 8000 ms after the corresponding failure, capped by the unchanged backoff ceiling of 300000 ms. It is ineligible for retry before `nextAttemptAt`.
Source: existing: docs/operations.md

### C-155: A notification becomes dead on the fifth failed attempt.
Observable: Fail an event on five due attempts. The event remains in `GET /admin/outbox` under `dead` with `attempts:5`, `nextAttemptAt:null` and the last failure in `lastError`. Later ticks leave it dead.
Source: existing: docs/operations.md

### C-156: A dead notification is logged as a warning.
Observable: When an event reaches its fifth failure, stderr contains one warning identifying its ID, type, recipient, attempts and last error.
Source: existing: docs/operations.md

### C-157: Failed delivery records the last error within the existing length cap.
Observable: A delivery exception with a 501-character message results in `lastError` equal to the first 500 characters of that message.
Source: existing: src/outbox.js

### C-158: An unfinished delivery can be attempted again after a crash.
Observable: If the process stops after append to `NOTIFY_FILE` but before recording success to `DATA_FILE`, the pending event is retried after restart with the same `key` and `id`.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-159: State is process-local when `DATA_FILE` is unset or empty.
Observable: Start with no configured data file, create and assign a ticket, then restart. The new process returns an empty ticket list, an empty outbox, and ID `T-0001` for its first creation.
Source: existing: docs/decisions/0008-json-data-file.md

### C-160: A missing configured data file starts an empty service.
Observable: Set `DATA_FILE` to a path that does not exist. The service starts with `{"items":[],"next":null}` from `GET /tickets`, and the first successful creation writes the file.
Source: existing: src/persistence.js

### C-161: The persisted document keeps version 1 and its existing top-level shape.
Observable: Inspect the file after a successful change. Its top-level keys are `version`, `savedAt`, `nextNumber`, `tickets`, `audit` and `outbox`, with `version:1` and `outbox` containing `nextId` and `events`.
Source: existing: src/persistence.js

### C-162: A successful save leaves the configured data file as the sole replacement result.
Observable: Save to a new directory dedicated to `tickets.json`. After a successful change, the directory contains `tickets.json` as a complete JSON document with no leftover temporary file.
Source: existing: test/persistence.test.js

### C-163: State restoration retains the existing ticket, audit and outbox data.
Observable: After a persisted assignee change with the worker disabled, restart with the same file and worker setting. The ticket response, history and admin outbox are identical to their pre-restart values.
Source: existing: docs/decisions/0008-json-data-file.md

### C-164: A data file that fails validation stops startup with a diagnostic.
Observable: With an unusable `DATA_FILE`, startup exits 2, with the path and reason on stderr. For non-JSON the reason is `is not JSON`, for version 2 it is `has version 2; this service reads version 1`, and for a ticket of priority `critical` at index 3 it is `tickets[3].priority is not a priority`.
Source: existing: src/persistence.js

### C-165: Saved ticket numbering cannot reuse an existing ID.
Observable: A file containing `T-0002` with `nextNumber:2` stops startup with a message ending in `nextNumber 2 would reuse the number of T-0002`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-166: The data-file reader rejects duplicate ticket IDs.
Observable: A file with two tickets with ID `T-0001` and an otherwise valid `nextNumber` stops startup with a message ending in `ticket T-0001 appears twice`.
Source: existing: src/persistence.js

### C-167: The data-file reader rejects a gap in the audit sequence.
Observable: Remove entry 2 from a file whose audit sequence is 1, 2, 3. Startup fails with a message ending in `audit[1].seq is 3, not 2: the log is append-only`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-168: The data-file reader rejects invalid outbox states.
Observable: Set `outbox.events[0].status` to `lost`. Startup fails with a message ending in `outbox.events[0].status is not one of pending, sent, dead`.
Source: existing: src/persistence.js

### C-169: Saved event numbering cannot reuse an existing event ID.
Observable: Give a data file an outbox event with ID 2 and set `outbox.nextId` to 2. Startup fails with a message ending in `outbox.nextId 2 would reuse an event id`.
Source: existing: src/persistence.js

### C-170: The operator CLI reads the configured data file.
Observable: With `DATA_FILE` pointing to one valid file, `node bin/tickets.js list` lists the tickets in that file. Adding `--data FILE` pointing to another valid file lists the tickets from the explicit file.
Source: existing: README.md

### C-171: The operator CLI leaves the data file untouched.
Observable: Compare the contents and modification time after each of `list`, `list --raw` and `show T-0001` with the file before invocation. Each is identical.
Source: existing: docs/operations.md

### C-172: CLI list returns every matching ticket in numeric ID order.
Observable: With more than 100 matching tickets, `list` and `list --raw` each contain every matching ID once in ascending numeric order.
Source: existing: bin/tickets.js

### C-173: CLI list continues to honor its status and priority options.
Observable: With tickets of varied status and priority, `list --status open` selects open tickets and `list --priority urgent` selects urgent tickets. These options also work with `--raw`. An invalid value for either option exits 2.
Source: existing: README.md

### C-174: An empty human-readable CLI list prints the existing empty message.
Observable: With no matching tickets, `list` exits 0 and stdout is exactly `no tickets\n`, with a literal newline.
Source: existing: bin/tickets.js

### C-175: An empty raw CLI list prints nothing.
Observable: With no matching tickets, `list --raw` exits 0 with empty stdout.
Source: existing: bin/tickets.js

### C-176: The human-readable list keeps its existing time format.
Observable: A ticket updated at `2025-09-01T08:01:42.123Z` has `2025-09-01 08:01` in its `UPDATED` cell.
Source: existing: src/format.js

### C-177: CLI show retains the ticket's existing detail fields.
Observable: `show T-0001` exits 0 and prints the ID and title on the first line, followed by fields labeled `status`, `priority`, `requester`, `created` and `updated` in that order.
Source: existing: src/format.js

### C-178: CLI show retains the ticket history.
Observable: `show T-0001` prints a `History` section after the ticket details. Each entry shows the time to the minute, actor, action and field changes, oldest first.
Source: existing: src/format.js

### C-179: CLI show of a missing ticket exits 1.
Observable: With a valid data file, `show T-0042` for a missing ticket exits 1 and stderr is `tickets: ticket T-0042 not found` followed by one newline.
Source: existing: bin/tickets.js

### C-180: CLI usage errors exit 2.
Observable: Running `show` without an ID, invoking an unknown option, or listing without either source of a data path exits 2 with a diagnostic beginning `tickets: ` and the existing usage lines.
Source: existing: bin/tickets.js

### C-181: CLI data file errors exit 2.
Observable: `list` with a file that is missing or malformed exits 2 with a stderr diagnostic identifying the file.
Source: existing: bin/tickets.js

### C-182: The weekly report counts the same tickets after an assignee change.
Observable: Run `node scripts/weekly-report.js --data FILE --json` before and after changing only an assignee. Both runs exit 0 and return identical `total`, `byStatus` and `byPriority` counts.
Source: existing: scripts/weekly-report.js

### C-183: The weekly report retains its existing text output.
Observable: Run `DATA_FILE=FILE npm run report:weekly`. The report still shows `Ticket report for the week of YYYY-MM-DD` with the current UTC date, followed by `By status`, `By priority` and the total.
Source: existing: scripts/weekly-report.js

### C-184: The weekly report leaves the data file untouched.
Observable: Run the weekly report with an explicit data file, then compare the file contents and modification time with their values before invocation. Both are identical.
Source: existing: docs/operations.md

### C-185: Combined CLI filters use the same intersection as the API.
Observable: With one open low ticket, one in-progress urgent ticket and one open urgent ticket, `list --status open --priority urgent` includes only the open urgent ticket, in either output format.
Source: choice: Keep HTTP and CLI listings on the shared ticket filter semantics.

### C-186: The CLI table uses a blank assignee cell for an unassigned ticket.
Observable: Run `node bin/tickets.js list` on a file with an unassigned ticket. Its row has an empty `ASSIGNEE` value after `TITLE`.
Source: choice: An empty cell represents null without colliding with a valid agent name.

### C-187: Client errors on the assignee route leave the data file untouched.
Observable: With the worker disabled and a data file configured, compare its contents and modification time before and after assignee PUTs returning 400, 404 or 409. Both are identical.
Source: existing: src/store.js

### C-188: PATCH of a missing ticket returns the existing lookup error.
Observable: PATCH `/tickets/T-0042` with `{"title":"VPN"}` when the ticket is absent. The response is 404 `not_found` with message `ticket T-0042 not found`.
Source: existing: src/store.js

### C-189: Transition of a missing ticket returns the existing lookup error.
Observable: POST `{"to":"in_progress"}` to `/tickets/T-0042/transition` when the ticket is absent. The response is 404 `not_found` with message `ticket T-0042 not found`.
Source: existing: src/store.js

### C-190: The CLI help flags display usage successfully.
Observable: With `DATA_FILE` unset, `node bin/tickets.js --help` or `node bin/tickets.js -h` exits 0 and prints the existing `list` and `show` usage lines to stdout.
Source: existing: bin/tickets.js
