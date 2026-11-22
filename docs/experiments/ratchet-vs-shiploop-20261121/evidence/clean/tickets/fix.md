# Fix pass on the assignment change

`npm test` before the pass: 122 tests, 122 pass. After it: 126 tests, 126 pass. Each shortfall in look.md was reproduced
on the running service (`node src/server.js` with a scratch `DATA_FILE` and `NOTIFY_FILE`, `WORKER_INTERVAL_MS=0`) before
it was judged. The four new tests, in `test/assignment-fixes.test.js`, fail without the source changes and pass with them.

## Shortfalls

- **A successful retry can lose the assignment (high):** fixed. A change whose save fails now restores the store to its state before the change (`TicketStore.apply`), so the 500 leaves nothing in memory and the same PUT, sent again, assigns and saves it; this also covers `PATCH` and transitions, which share the step. Test: `an assignment whose save fails changes nothing, and the same request sent again is saved`.
- **The list silently drops a second assignee filter (high):** fixed. A filter given more than once must match each of its values (`filterValue` in `src/tickets/query.js`), so `?assignee=Ada%20Lovelace&assignee=Ben` lists nothing; the same rule covers `status` and `priority`, which dropped a second value the same way. Test: `a filter given more than once lists only the tickets that match every value`.
- **A name with 64 characters can be rejected (medium):** fixed. Text limits count Unicode code points (`text` in `src/tickets/validate.js`), so `"a" x 63 + "𠮷"` is accepted; titles and requesters share the rule. Test: `an agent name is at most 64 characters counted as Unicode code points`.
- **Unicode line breaks pass the single-line name check (low):** not changed. The request sets no line rule for names; the product's one-line rule (since 1.4.0, for titles and requesters too) exists to keep the command line's tab-separated output whole, and U+2028, U+2029 and U+0085 do not break it, so refusing them is hardening the request does not ask for. Documented what "one line" refuses and accepts.
- **An invalid Unicode name can be saved but cannot be selected by its exact value (medium):** fixed. Text that is not valid Unicode (an unpaired surrogate) is 400 `invalid` before anything changes, so every accepted name can be found by the exact `assignee` filter. Test: `an agent name that is not valid Unicode is refused before it changes the ticket`.
- **The CLI displays an assigned ticket as unassigned (high):** not changed. It needs an agent literally named `-`; the request allows any non-empty name, so refusing `-` would add a rule it does not have, and the delivered tests fix `-` as the table's unassigned marker. Documented that the table and `show` print both as `-`, and that `list --raw` tells them apart.
- **The CLI history makes assignment and unassignment look the same (low):** not changed. It needs an agent literally named `null`, and any other marker for a cleared value could be some agent's name too; `GET /tickets/:id/audit` tells them apart. Documented in the README.

## Choices documented

- **Lifecycle and ownership** (the assignee is kept through resolve, close and reopen; the filter finds inactive tickets): docs/api.md, the ticket's `assignee` field, "Assign or unassign a ticket" and "List tickets"; CHANGELOG.md 1.5.0.
- **Existing data** (a version 1 ticket with no `assignee` loads as unassigned; a bad saved assignee stops the start): docs/operations.md, "The data file"; CHANGELOG.md 1.5.0.
- **Assignee filter validation** (an impossible value such as 65 characters or a tab lists nothing, with 200; the value is exact and not trimmed): docs/api.md, "List tickets".
- **Notification recipient** (`to` is the name verbatim, no address lookup): docs/api.md, "Assign or unassign a ticket" and "The outbox"; docs/operations.md, "Notifications"; CHANGELOG.md 1.5.0.
- **Queued notifications after another change** (a key per assignment with its audit `seq`; pending notices still go out after reassignment or clearing, with the title at assignment time): docs/api.md, "Assign or unassign a ticket" and "The outbox"; docs/operations.md, "Notifications"; CHANGELOG.md 1.5.0.
- **Auditing an unassignment** (same `ticket.assigned` action, `to` is JSON `null`; clearing notifies no one): docs/api.md, "Assign or unassign a ticket" and "A ticket's history"; CHANGELOG.md 1.5.0.
- **Unchanged shortfalls:** the one-line rule and the separators it accepts (docs/api.md, "The ticket"); `-` for both an unassigned ticket and an agent named `-`, and `assignee Ada -> null` for both a clearing and an agent named `null` (README.md, "Command line").
- **The fixes themselves:** a failed save answered 500 and undone (docs/api.md, "Errors"; docs/operations.md, "The data file"); a filter given twice (docs/api.md, "List tickets"); code-point limits and valid Unicode (docs/api.md, "The ticket").
- **Release record:** CHANGELOG.md gains 1.5.0 for the whole assignment change, including that filters now combine as documented (1.4.0 listed a ticket matching any one filter); package.json is 1.5.0, as CONTRIBUTING.md asks.
