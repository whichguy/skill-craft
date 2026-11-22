# Delivered product review

## Shortfalls

Reproduce each finding independently. Start `npm start` on a free `PORT` with a fresh `DATA_FILE` and `NOTIFY_FILE` under `../tmp`. Set `WORKER_INTERVAL_MS=0` so that the worker cannot change the snapshot during the check. Create tickets with `POST /tickets` and JSON such as `{"title":"VPN drops every hour","requester":"maria@example.com"}`. The first two tickets are `T-0001` and `T-0002`. Send assignment JSON to `PUT /tickets/T-0001/assignee` unless the steps specify another ticket.

- **high — A successful retry can lose the assignment.** An operator needs a 200 to mean the assignment, its audit entry, and its pending notification are saved when `DATA_FILE` is configured.
  1. Create an unassigned ticket. With `server_pid` set to the PID of `node src/server.js`, run `mkdir "${DATA_FILE}.${server_pid}.tmp"` to temporarily block the snapshot write.
  2. Send `{"assignee":"Ada"}`. The PUT returns 500 `internal`. A subsequent `GET /tickets/T-0001` already shows Ada and `GET /admin/outbox` shows her pending assignment notice, while the data file still shows a null assignee.
  3. Run `rmdir "${DATA_FILE}.${server_pid}.tmp"` and retry the identical PUT. It returns 200 with Ada, but the data file still has a null assignee. Run `kill -KILL "$server_pid"` to simulate a crash, then restart with the same data file. The ticket is unassigned and the pending notice is gone. Once the write path is available, the retry should save the change and its effects before returning 200.

- **high — The list silently drops a second assignee filter.** A successful list response needs to satisfy every supplied filter. Assign `T-0001` to Ada Lovelace and `T-0002` to Ben. Request `GET /tickets?assignee=Ada%20Lovelace&assignee=Ben`. It returns 200 and lists `T-0001`. Reverse the two parameters and it lists `T-0002`. Neither ticket satisfies both filters. The result should be empty, or the service should reject conflicting repeated values explicitly.

- **medium — A name with 64 characters can be rejected.** The advertised limit should accommodate a name containing a supplementary Unicode character. Generate the body with `node -p 'JSON.stringify({assignee: "a".repeat(63) + "𠮷"})'` and PUT it on an open ticket. The service returns 400 `assignee must be at most 64 characters`, while the same request with 64 ASCII letters returns 200. Both names have 64 Unicode code points and should be accepted. The implementation counts the two UTF-16 code units of `𠮷` separately.

- **low — Unicode line breaks pass the single-line name check.** PUT `{"assignee":"Ada\u2028Ben"}`, using the JSON escape for LINE SEPARATOR. The response is 200 and preserves the separator in `assignee`. U+2029 and U+0085 also pass. The same input with `\n` gets 400 `assignee must be a single line of text`. The documented single-line field should reject embedded line breaks consistently.

- **medium — An invalid Unicode name can be saved but cannot be selected by its exact value.** PUT the literal JSON `{"assignee":"\ud800"}` with the escape as written. It returns 200 and the ticket contains the unpaired surrogate. `GET /tickets?assignee=%ED%A0%80` and `GET /tickets?assignee=%EF%BF%BD` both return an empty list, while `node bin/tickets.js --data "$DATA_FILE" list --raw` prints the replacement character `�` as the assignee. A malformed Unicode value should get 400 before it changes the ticket so that accepted names can round-trip through the exact filter and CLI.

- **high — The CLI displays an assigned ticket as unassigned.** Create two tickets, assign the first with `{"assignee":"-"}`, and leave the second unassigned. Run `node bin/tickets.js --data "$DATA_FILE" list`. Both rows show `-` in the assignee column, even though the README tells operators that `-` means unassigned. The table should distinguish the accepted name from the unassigned marker. The raw output distinguishes them with a literal dash and an empty fifth field.

- **low — The CLI history makes assignment and unassignment look the same.** PUT the values `"Ada"`, `"null"`, `"Ada"`, and `null` in that order as the `assignee` field. Run `node bin/tickets.js --data "$DATA_FILE" show T-0001`. Both the assignment from Ada to the literal name `"null"` and the subsequent unassignment from Ada print `ticket.assigned  assignee Ada -> null`. The history should distinguish an agent name from a cleared value, as the JSON audit already does.

## Choices the customer was not told

- **Lifecycle and ownership.** Transitions keep the assignee through resolution, closure, and reopening. The assignee filter can still find inactive tickets.
- **Existing data.** A version 1 snapshot with no assignee field on a ticket loads that ticket as unassigned.
- **Assignee filter validation.** An impossible nonempty filter value, such as a 65-character name or a string containing a tab, returns 200 with an empty list.
- **Notification recipient.** The service puts the saved name verbatim in the relay record’s `to` field, including a display name such as `Ada Lovelace`. The service performs no address lookup.
- **Queued notifications after another change.** Each actual assignment gets a distinct notification key tied to its audit sequence. Pending notices still go out after reassignment or clearing, and their text uses the title at assignment time.
- **Auditing an unassignment.** Clearing an assignee uses the same `ticket.assigned` action as setting one. The audit change’s `to` value is JSON `null`.
