### C-1: Only the exact environment value `DUE_TIMES=on` enables due times for the HTTP API.
Observable: Start the service with `DUE_TIMES=on` and create a ticket. Its response has a `due` property. Repeat with the variable unset, empty, `off`, `ON`, `true`, `1` or ` on `. The property is absent in every repeat.
Source: request

### C-2: With due times disabled the HTTP API keeps the 1.4.0 response contract.
Observable: At the same clock time with the same legacy state, send the same successful and failing requests to the new release with the flag off and to 1.4.0. The statuses, JSON bodies and JSON content type match. When the new release reads a backfilled file, creating, getting, listing, patching and transitioning tickets still return the seven legacy ticket fields `id`, `title`, `priority`, `requester`, `status`, `created`, `updated`.
Source: request

### C-3: With due times disabled the ticket listing ignores the `overdue` parameter.
Observable: With both past-due and future-due tickets in the data file, the result of `GET /tickets` is identical to the results with `?overdue=true`, `?overdue=false`, `?overdue=`, `?overdue=maybe` or `?overdue=true&overdue=false`.
Source: request

### C-4: With due times disabled the existing status-or-priority behavior is preserved when both filters are supplied.
Observable: Given `T-0001=open/low`, `T-0002=in_progress/urgent`, `T-0003=open/urgent` and `T-0004=resolved/high`, `GET /tickets?status=open&priority=urgent` returns `T-0001`, `T-0002`, `T-0003`.
Source: existing: src/tickets/query.js

### C-5: The default urgent response time is 4 hours.
Observable: With due times enabled and the urgent override absent, create an urgent ticket at `2025-09-01T08:15:00.123Z`. Its `due` is `2025-09-01T12:15:00.123Z`.
Source: request

### C-6: The default high response time is 24 hours.
Observable: With due times enabled and the high override absent, create a high ticket at `2025-09-01T08:15:00.123Z`. Its `due` is `2025-09-02T08:15:00.123Z`.
Source: request

### C-7: The default normal response time is 72 hours.
Observable: With due times enabled and the normal override absent, create a normal ticket at `2025-09-01T08:15:00.123Z`. Its `due` is `2025-09-04T08:15:00.123Z`.
Source: request

### C-8: The default low response time is 168 hours.
Observable: With due times enabled and the low override absent, create a low ticket at `2025-09-01T08:15:00.123Z`. Its `due` is `2025-09-08T08:15:00.123Z`.
Source: request

### C-9: A creation request with no priority uses the normal response time.
Observable: At `2025-09-01T08:15:00.123Z`, omit `priority` from a valid creation request under the default schedule. The response has `due: "2025-09-04T08:15:00.123Z"`.
Source: request

### C-10: Operators can override the response time for each priority through environment settings.
Observable: Start with `DUE_TIMES=on` and `DUE_HOURS_URGENT=2 DUE_HOURS_HIGH=3 DUE_HOURS_NORMAL=5 DUE_HOURS_LOW=7`. Tickets created at `2025-09-01T08:15:00.123Z` have due times `2025-09-01T10:15:00.123Z`, `2025-09-01T11:15:00.123Z`, `2025-09-01T13:15:00.123Z` and `2025-09-01T15:15:00.123Z`, respectively. Setting only `DUE_HOURS_HIGH=3` leaves the other three default durations in effect.
Source: choice: independent startup environment variables follow the service's existing configuration interface.

### C-11: An unset or blank response-time setting takes its priority's default.
Observable: Run with `DUE_HOURS_URGENT` unset, empty or `   `. An urgent ticket created at `2025-09-01T08:15:00.123Z` is due at `2025-09-01T12:15:00.123Z` in each case.
Source: choice: match the blank-value convention for existing numeric environment settings.

### C-12: A nonblank response-time setting accepts decimal digits for whole hours from 1 to 2,400,000,000 inclusive.
Observable: With due times enabled, startup accepts each of `1`, ` 02 ` and `2400000000` for `DUE_HOURS_URGENT`. The value ` 02 ` makes a ticket created at `2025-09-01T08:15:00.123Z` due at `2025-09-01T10:15:00.123Z`. The value `2400000000` makes a ticket created at `1970-01-01T00:00:00.000Z` due at `+275760-09-13T00:00:00.000Z`.
Source: choice: use the existing trimmed whole-number syntax for positive hours, with a maximum whose millisecond duration fits the Node Date range and can be added exactly for representable results.

### C-13: An unusable response-time setting prevents enabled startup with a diagnostic naming the variable.
Observable: For each of `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL`, `DUE_HOURS_LOW`, start with `DUE_TIMES=on` and any of `0`, `-1`, `+1`, `2.5`, `1e2`, `four` or `2400000001`. The process exits 2 before listening. Standard error names the offending variable and describes the whole-number requirement or the range 1 through 2400000000.
Source: choice: follow the service's startup error convention for numeric settings.

### C-14: Disabled service startup ignores response-time overrides.
Observable: With `DUE_TIMES` unset or `off` and `DUE_HOURS_URGENT=bad`, the service starts and `GET /health` returns HTTP 200 with `{"status":"ok"}`.
Source: choice: off-mode startup must still work with the environment of a failed due-time rollout.

### C-15: A new due time is the instant recorded in `created` plus the configured number of elapsed hours.
Observable: Create a high ticket at `2025-03-09T09:59:59.999Z` with the default 24 hours. The response has `created: "2025-03-09T09:59:59.999Z"` and `due: "2025-03-10T09:59:59.999Z"`, a difference of exactly `86400000` milliseconds even with `TZ=America/Los_Angeles`.
Source: request

### C-16: A new due time outside the representable Date range rejects the creation before recording it.
Observable: With `DUE_TIMES=on`, `DUE_HOURS_URGENT=1` and the service clock at `+275760-09-13T00:00:00.000Z`, a valid urgent creation request returns HTTP 500 with `{"error":{"code":"internal","message":"internal error"}}`. The ticket list, audit log, outbox and next ticket number are unchanged.
Source: choice: an unrepresentable server-calculated timestamp is an internal fault under the existing error contract.

### C-17: An enabled creation response exposes the assigned timestamp as `due`.
Observable: Create an urgent ticket at `2025-09-01T08:15:00.123Z` with the default schedule. HTTP 201 includes `due: "2025-09-01T12:15:00.123Z"` as an ISO UTC string alongside the seven existing fields.
Source: request

### C-18: An enabled single-ticket read exposes the stored `due`.
Observable: After creating the urgent ticket at `2025-09-01T08:15:00.123Z` under the default schedule, `GET /tickets/T-0001` returns HTTP 200 with `due: "2025-09-01T12:15:00.123Z"`.
Source: request

### C-19: Every item in an enabled ticket listing exposes its stored `due`.
Observable: Create urgent and low tickets at `2025-09-01T08:15:00.123Z`. An enabled `GET /tickets` returns `due` values `2025-09-01T12:15:00.123Z` and `2025-09-08T08:15:00.123Z`. If both are still open on September 9, `GET /tickets?overdue=true` returns the same due values.
Source: request

### C-20: Patching a ticket's priority leaves its assigned `due` fixed.
Observable: Create a high ticket at `2025-09-01T08:15:00.123Z` with default hours. Patch it to urgent. The HTTP 200 patch response and a following read show `priority: "urgent"` with `due: "2025-09-02T08:15:00.123Z"`.
Source: request

### C-21: Patching a ticket's title leaves its assigned `due` fixed.
Observable: Create a normal ticket at `2025-09-01T08:15:00.123Z` with default hours. Patch its title to `Network unavailable`. HTTP 200 gives the new title with `due: "2025-09-04T08:15:00.123Z"`.
Source: request

### C-22: A lifecycle transition leaves the ticket's assigned `due` fixed.
Observable: Create an urgent ticket at `2025-09-01T08:15:00.123Z` with default hours. Follow the status sequence `in_progress`, `resolved`, `open`, `in_progress`, `resolved`, `closed`. Every HTTP 200 transition response exposes `due: "2025-09-01T12:15:00.123Z"`.
Source: request

### C-23: A successful no-op patch exposes the ticket's assigned `due` when enabled.
Observable: Patch an urgent ticket with its current priority. HTTP 200 includes the same `due: "2025-09-01T12:15:00.123Z"` the ticket had before the patch.
Source: request

### C-24: Changing the configured response hours leaves stored due times fixed.
Observable: Create a high ticket at `2025-09-01T08:15:00.123Z` under the default 24 hours using a data file. Restart enabled with `DUE_HOURS_HIGH=2`. The first ticket still has `due: "2025-09-02T08:15:00.123Z"`. At the same clock instant a second high ticket gets `due: "2025-09-01T10:15:00.123Z"`.
Source: request

### C-25: The create endpoint refuses a client-supplied `due` field.
Observable: Add `"due":"2025-09-02T08:15:00.123Z"` to a valid `POST /tickets` body. With the feature either enabled or disabled, the response is HTTP 400 with `{"error":{"code":"invalid","message":"unknown field: due"}}`.
Source: existing: src/tickets/validate.js

### C-26: The patch endpoint refuses a client-supplied `due` field.
Observable: Send `{"due":"2025-09-02T08:15:00.123Z"}` in `PATCH /tickets/T-0001`. With the feature either enabled or disabled, the response is HTTP 400 with `{"error":{"code":"invalid","message":"unknown field: due"}}`.
Source: existing: src/tickets/validate.js

### C-27: The transition endpoint refuses a client-supplied `due` field.
Observable: Send `{"to":"in_progress","due":"2025-09-02T08:15:00.123Z"}` to `POST /tickets/T-0001/transition`. With the feature either enabled or disabled, the response is HTTP 400 with `{"error":{"code":"invalid","message":"unknown field: due"}}`.
Source: existing: src/tickets/validate.js

### C-28: An open ticket past its due time qualifies for the overdue listing.
Observable: At `2025-09-01T12:15:00.124Z`, an open ticket with `due: "2025-09-01T12:15:00.123Z"` appears in enabled `GET /tickets?overdue=true`.
Source: request

### C-29: An in-progress ticket past its due time qualifies for the overdue listing.
Observable: At `2025-09-01T12:15:00.124Z`, an `in_progress` ticket with `due: "2025-09-01T12:15:00.123Z"` appears in enabled `GET /tickets?overdue=true`.
Source: request

### C-30: A resolved ticket is excluded from the overdue listing.
Observable: At `2025-09-01T12:15:00.124Z`, a resolved ticket with `due: "2025-09-01T12:15:00.123Z"` is absent from enabled `GET /tickets?overdue=true`.
Source: request

### C-31: A closed ticket is excluded from the overdue listing.
Observable: At `2025-09-01T12:15:00.124Z`, a closed ticket with `due: "2025-09-01T12:15:00.123Z"` is absent from enabled `GET /tickets?overdue=true`.
Source: request

### C-32: A ticket with a future due time is excluded from the overdue listing.
Observable: At `2025-09-01T12:15:00.122Z`, neither an open nor an in-progress ticket due at `2025-09-01T12:15:00.123Z` appears in enabled `GET /tickets?overdue=true`.
Source: request

### C-33: A ticket is excluded from the overdue listing at the exact instant it is due.
Observable: At `2025-09-01T12:15:00.123Z`, neither an open nor an in-progress ticket due at `2025-09-01T12:15:00.123Z` appears in enabled `GET /tickets?overdue=true`. Each appears 1 millisecond later if its status stays active.
Source: request

### C-34: Reopening a ticket whose due time passed restores its overdue eligibility.
Observable: On September 2 reopen a resolved ticket due at `2025-09-01T12:15:00.123Z`. The next enabled `GET /tickets?overdue=true` includes that now-open ticket.
Source: request

### C-35: The overdue listing uses one current clock instant for the whole page.
Observable: With the worker disabled, arrange two open tickets with the same due instant. After setup, configure the clock to return the exact due instant on its next read and 1 millisecond later on subsequent reads. One `overdue=true` request returns `{"items":[],"next":null}`. The next request returns both.
Source: choice: a single time for a request gives equal treatment to tickets due at the same instant.

### C-36: An enabled listing without `overdue` imposes no due-time restriction.
Observable: An enabled `GET /tickets` returns the same IDs as an unfiltered 1.4.0 listing given open, in-progress, resolved and closed tickets with both past and future due times.
Source: request

### C-37: The exact value `overdue=false` imposes no due-time restriction.
Observable: With the flag on, `GET /tickets?overdue=false` returns the same page as `GET /tickets` for a mix of past-due, future-due and closed tickets.
Source: choice: false turns off the optional overdue restriction.

### C-38: Enabled listings reject values of `overdue` other than the lowercase strings `true` and `false`.
Observable: With the flag on, send `?overdue`, `?overdue=`, `?overdue=TRUE`, `?overdue=1`, `?overdue=%20true` or `?overdue=maybe`. Each returns HTTP 400 with `{"error":{"code":"invalid","message":"overdue must be true or false"}}`.
Source: choice: strict boolean strings follow the API's treatment of recognized query values.

### C-39: When `overdue` is repeated the enabled listing uses its first value.
Observable: With the flag on, `?overdue=true&overdue=false` gives the same page as `?overdue=true`. The reverse order gives the same page as `?overdue=false`. A first value of `maybe` returns HTTP 400 even if followed by `true`.
Source: choice: the existing status, priority, limit and cursor parsers take the first value of repeated parameters.

### C-40: Enabled status and priority filters intersect as documented.
Observable: Given `T-0001=open/low`, `T-0002=in_progress/urgent` and `T-0003=open/urgent`, an enabled `GET /tickets?status=open&priority=urgent` returns only `T-0003`.
Source: existing: docs/api.md

### C-41: The enabled overdue filter intersects with the supplied status filter.
Observable: Given past-due open and in-progress tickets, `?overdue=true&status=in_progress` returns only the in-progress tickets. With `status=resolved` the page is `{"items":[],"next":null}`.
Source: request

### C-42: The enabled overdue filter intersects with the supplied priority filter.
Observable: For `?overdue=true&priority=urgent`, an open urgent ticket overdue by 1 millisecond is returned. An equally overdue open low ticket and an urgent open ticket due 1 millisecond in the future are excluded.
Source: request

### C-43: An enabled listing using all three filters requires a match for each filter.
Observable: At a time past the due dates of `T-0001=open/low`, `T-0002=in_progress/urgent` and `T-0003=open/urgent`, `?overdue=true&status=open&priority=urgent` returns only `T-0003`.
Source: existing: docs/api.md

### C-44: The enabled priority filter tests the current priority without changing the deadline used for overdue eligibility.
Observable: Create a high ticket with the default schedule at `2025-09-01T08:15:00.123Z`. Patch its priority to urgent. On September 1 at 13:00 UTC it is absent from `?overdue=true&priority=urgent`. At `2025-09-02T08:15:00.124Z` it appears for urgent but is absent for high.
Source: request

### C-45: Overdue eligibility is applied before cursor pagination.
Observable: At a fixed clock time suppose `T-0001` and `T-0003` are ineligible while `T-0002` and `T-0004` are overdue and active. With `?overdue=true&limit=1`, page one contains `T-0002` and a non-null `next`. Passing that cursor with the same query returns `T-0004` with `next: null`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-46: Each overdue cursor request uses the eligibility at that request's time.
Observable: Fetch `?overdue=true&limit=1` with `T-0001` and `T-0003` overdue, `T-0002` due in 1 millisecond, and all three open. Advance the clock by 2 milliseconds. Fetch the next page using the first page's `next` with the same filters. It contains `T-0002`.
Source: choice: cursors carry the last returned ID under the existing paging protocol, so overdue eligibility is evaluated anew on later requests.

### C-47: Passing a due time produces no ticket mutation.
Observable: With the worker off, capture a ticket, its history and the data file bytes. Move the clock from 1 millisecond before to 1 millisecond after its due time and list overdue tickets. The ticket's state, history and file bytes match the capture.
Source: choice: overdue is a read-time predicate on an existing status and a stored deadline.

### C-48: Passing a due time produces no notification.
Observable: After delivering a ticket's creation notification, advance its clock past the due time and let the worker run. `GET /admin/outbox` has the same events in the same states it had before the deadline passed.
Source: request

### C-49: Enabled creation writes the assigned `due` in the ticket's version-1 data-file record before reporting success.
Observable: Create a high ticket at `2025-09-01T08:15:00.123Z` with the default hours and `DATA_FILE` set. Immediately after HTTP 201, read the file while the process is still up. It contains `version: 1` and the matching ticket record has `due: "2025-09-02T08:15:00.123Z"`.
Source: request

### C-50: When due times are disabled, creation leaves the new ticket eligible for backfill.
Observable: With `DATA_FILE` set, create an urgent ticket at `2025-09-01T08:15:00.123Z` with `DUE_TIMES` unset. Its persisted record has no `due` key. The offline backfill using the default hours assigns `2025-09-01T12:15:00.123Z` to that record.
Source: choice: off-mode creation stays on the legacy path until an operator runs the backfill.

### C-51: The new release retains existing valid stored due times through disabled-mode saves.
Observable: Start the new release with a file containing `T-0001` due at `2025-09-01T12:15:00.123Z` and `DUE_TIMES=off`. Change its priority, allow any pending outbox deliveries to save, and stop the service. The file still has the original `due` for `T-0001`.
Source: request

### C-52: An enabled service refuses an existing data file with any ticket missing `due`.
Observable: Start with `DUE_TIMES=on` and a version-1 file whose ticket at index 1 lacks `due`, including if that ticket is closed. The process exits 2 before listening. Standard error contains the file path and `tickets[1].due is required when DUE_TIMES=on`. File bytes remain as they were.
Source: choice: fail before serving a partial rollout and direct operators to the exact missing record.

### C-53: A valid empty data file satisfies the enabled startup gate.
Observable: Start with `DUE_TIMES=on` and a valid version-1 document with `tickets: []`. `GET /tickets` returns HTTP 200 with `{"items":[],"next":null}`.
Source: choice: an empty ticket collection has no deadline to backfill.

### C-54: An enabled first start at a nonexistent configured data path can begin empty.
Observable: Start with `DUE_TIMES=on` and a `DATA_FILE` path that does not exist. `GET /tickets` returns `{"items":[],"next":null}`. The first normal-priority ticket created at `2025-09-01T08:15:00.123Z` appears in the file with `due: "2025-09-04T08:15:00.123Z"`.
Source: choice: preserve first-start behavior for a new installation that has no legacy records.

### C-55: Due times work with the existing in-memory service mode.
Observable: With `DATA_FILE` unset and `DUE_TIMES=on`, create an urgent ticket at `2025-09-01T08:15:00.123Z`. Its due is `2025-09-01T12:15:00.123Z`. The same running process reads it and lists it as overdue after that time without creating a data file.
Source: existing: docs/decisions/0008-json-data-file.md

### C-56: An enabled service refuses an existing ticket with a malformed stored `due`.
Observable: With `DUE_TIMES=on`, load a version-1 file containing `due` equal to `null`, a number, an empty string, `tomorrow`, `2025-09-01T08:15:00-04:00`, `2025-09-01T12:15:00Z` or `2025-02-30T12:15:00.123Z` in turn at ticket index 0. In each case startup exits 2 before listening and standard error contains the path and `tickets[0].due is not an ISO UTC time`.
Source: choice: stored due values must round-trip exactly through Node's ISO UTC format with milliseconds and a trailing Z.

### C-57: Disabled service accepts legacy data when a field previously ignored by 1.4.0 contains a malformed `due` value.
Observable: Add `"due":"tomorrow"` to a valid legacy ticket record. With `DUE_TIMES=off`, startup succeeds and the single-ticket response has the same seven fields and values as in 1.4.0.
Source: choice: off mode keeps the legacy read contract while the backfill and enabled startup validate due values.

### C-58: A disabled-mode save preserves a malformed stored `due` for diagnosis.
Observable: Start disabled on an otherwise valid file containing `"due":"tomorrow"` and patch that ticket's title. The response has no `due`. In the saved file the ticket still has `due: "tomorrow"`, which the backfill diagnoses upon its next run.
Source: choice: an off-mode write must leave the stored value available for validation at rollout instead of treating it as unassigned.

### C-59: Backfill writes due times into the existing data file before production enablement.
Observable: Stop the data file's service process. Run `DATA_FILE=data/tickets.json node scripts/backfill-due-times.js` with `DUE_TIMES` unset. On exit 0 the file itself has a valid `due` on every ticket. A subsequent `npm start` with that path and `DUE_TIMES=on` serves the stored times.
Source: choice: a separate offline command keeps the operator CLI read-only and gives the single data-file writer an explicit migration step.

### C-60: The offline backfill does not start an HTTP listener.
Observable: Run the command on a valid file with `DUE_TIMES` unset and a service-only setting such as `PORT=http`. It completes backfill with exit 0 without listening.
Source: choice: the migration needs the data path and response-hour settings only.

### C-61: Backfill uses each missing-due record's stored creation time.
Observable: In the same file, use two high tickets with equal `updated` times and different `created` values `2025-09-01T08:15:00.123Z` and `2025-09-02T09:00:00.000Z`. Backfill with default hours on September 15. The recorded due values are `2025-09-02T08:15:00.123Z` and `2025-09-03T09:00:00.000Z`.
Source: request

### C-62: Backfill uses each missing-due record's stored priority.
Observable: Prepare a legacy high ticket created at `2025-09-01T08:15:00.123Z` whose audit entry shows it was once urgent. Under the default schedule its backfilled `due` is `2025-09-02T08:15:00.123Z`.
Source: choice: use the current priority in the record, which the request identifies as the input and every valid legacy record provides.

### C-63: Backfill applies the configured response times.
Observable: Run the offline command with `DUE_HOURS_HIGH=6` and `DUE_TIMES` unset against a legacy high ticket created at `2025-09-01T08:15:00.123Z`. The file records `due: "2025-09-01T14:15:00.123Z"`.
Source: choice: use the same schedule settings for initial assignment to existing tickets and to new tickets.

### C-64: Backfill assigns missing due times to tickets at every lifecycle status.
Observable: Backfill a file with one open, one in-progress, one resolved and one closed ticket, all urgent and created at `2025-09-01T08:15:00.123Z`. Each record has `due: "2025-09-01T12:15:00.123Z"` under the default hours.
Source: request

### C-65: Backfill interprets an accepted legacy creation timestamp by its instant.
Observable: Backfill a file with an urgent ticket whose `created` is the legacy-accepted value `2025-09-01T04:15:00.123-04:00`. The persisted `created` string stays as written and the default schedule gives `due: "2025-09-01T12:15:00.123Z"`.
Source: choice: keep loading timestamps accepted by the old reader while writing canonical UTC deadlines.

### C-66: Backfill leaves all previously assigned valid due times fixed.
Observable: In a mixed file, high-priority `T-0001` already has `due: "2025-09-02T08:15:00.123Z"`. High-priority `T-0002` has no `due` and was created at `2025-09-01T08:15:00.123Z`. Backfill with `DUE_HOURS_HIGH=2`. The resulting deadlines are `2025-09-02T08:15:00.123Z` and `2025-09-01T10:15:00.123Z`, respectively.
Source: request

### C-67: Backfill is a no-write operation when every ticket already has a valid `due`.
Observable: Rerun the command on a fully backfilled valid file with different valid overrides. It exits 0. The entire file is byte-for-byte identical, including `savedAt`. An empty valid ticket collection is also a no-op.
Source: choice: a retry should preserve the original deadlines and should cause no data-file change when there is nothing to fill.

### C-68: Backfill preserves the legacy fields of each ticket.
Observable: Compare `tickets` before and after successful backfill with the added `due` properties removed. The arrays are deeply equal, including record order, IDs, statuses, current priorities and both original timestamps.
Source: request

### C-69: Backfill preserves the next ticket number.
Observable: Backfill a valid file with `nextNumber: 42`. The file still has `nextNumber: 42`. The first subsequent creation by the service gets ID `T-0042`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-70: Backfill preserves the audit log.
Observable: A file with audit entries numbered 1 through 5 still has exactly those entries with the same contents after backfill.
Source: choice: assigning derived metadata offline leaves the history of user changes intact.

### C-71: Backfill preserves the complete outbox.
Observable: After backfilling a file holding pending, sent and dead events, the `outbox` object is deeply equal to the original, including `nextId`, retry times and failure counts. No delivery takes place during the command.
Source: request

### C-72: Backfill requires a configured data-file path.
Observable: Run `node scripts/backfill-due-times.js` with `DATA_FILE` unset, empty or all whitespace. It exits 2 and prints `DATA_FILE is required for due-time backfill` to standard error without creating a data file.
Source: choice: the offline command needs an explicit path to an existing production file.

### C-73: Backfill refuses a configured path that does not exist.
Observable: Run the command with `DATA_FILE=data/missing.json` where that file does not exist. Exit status is 2 and standard error contains `data/missing.json: does not exist`. The file remains absent.
Source: choice: a misspelt migration path must not be mistaken for a successfully migrated production file.

### C-74: Backfill refuses an invalid legacy data file without replacing it.
Observable: Run the command against malformed JSON, or against a version-1 document with `tickets[1].priority: "critical"`. It exits 2. Standard error names the file and contains `is not JSON` or `tickets[1].priority is not a priority`, respectively. File bytes are identical to their input.
Source: existing: docs/decisions/0008-json-data-file.md

### C-75: Backfill refuses malformed existing due values without replacing the file.
Observable: In a valid legacy file make ticket index 0 lack `due` and put `"due":null` on the ticket at index 1. Backfill exits 2. Standard error contains the path and `tickets[1].due is not an ISO UTC time`. File bytes are identical to their input.
Source: choice: a present invalid deadline is an error requiring operator attention rather than another unassigned deadline.

### C-76: Backfill refuses an invalid response-time setting without replacing the file.
Observable: With `DUE_TIMES` unset and `DUE_HOURS_LOW=0`, run the command on a valid file lacking due times. It exits 2, names `DUE_HOURS_LOW` and the range 1 through 2400000000 on standard error, and leaves the original file bytes intact.
Source: choice: validate the migration schedule using the same limits as enabled service startup.

### C-77: Backfill refuses an unrepresentable computed due time without replacing the file.
Observable: Backfill a valid file where the urgent ticket at index 1 has `created: "+275760-09-13T00:00:00.000Z"` and no due time. With the default hours the command exits 2. Standard error gives the file path and `tickets[1].due cannot be represented as a time`. File bytes are identical to their input, including any earlier eligible record.
Source: choice: keep the original file if any missing due cannot be computed.

### C-78: Backfill publishes a complete version-1 document through atomic replacement.
Observable: When at least one deadline is newly assigned, a reader opening `DATA_FILE` during a successful migration sees a complete original document or a complete backfilled document at that path. The command uses a temporary file in the same directory and a rename as the commit point.
Source: existing: docs/decisions/0008-json-data-file.md

### C-79: A backfill write failure leaves the original file available for retry.
Observable: Induce failure writing the temporary file or renaming it over `DATA_FILE`. The command exits 2, identifies the target file and reason on standard error, and leaves the original bytes at `DATA_FILE`. Removing the failure and rerunning exits 0 with all missing due times filled.
Source: choice: operators need a safe retry after failure before the atomic replacement.

### C-80: The documented rollout makes the offline command the last data-file writer before enabled startup.
Observable: The operations instructions give this order for an existing production file: stop the service that owns it, copy the file for backup, run the backfill with the intended response-time settings, then start with the same `DATA_FILE`, the intended settings and `DUE_TIMES=on` only after exit 0. If the service has created tickets while off since a previous backfill, the instructions repeat the offline step before enabling.
Source: choice: the existing data-file ownership model requires one writer and the enablement gate requires a complete backfill.

### C-81: The unchanged 1.4.0 service starts directly on a file written by the new release.
Observable: Set `DATA_FILE` for the unmodified 1.4.0 service from baseline commit `374883eff92f98a6a85893d55835d5b422e45f02` to a version-1 file containing both backfilled tickets and tickets created while enabled. With no file conversion and the new service stopped, 1.4.0 starts and `GET /health` returns HTTP 200 with `{"status":"ok"}`.
Source: request

### C-82: The unchanged 1.4.0 service shows every ticket from the new release's file.
Observable: On 1.4.0 using that file, page through `GET /tickets?limit=1` with successive `next` cursors. It returns every pre-existing and newly added ticket in numeric ID order. Each `GET /tickets/:id` has its original seven legacy fields and values, with no `due`.
Source: request

### C-83: The unchanged 1.4.0 service can continue issuing ticket IDs from the new release's file.
Observable: Start the baseline service directly on a new-release file containing `T-0001` and `T-0002` with `nextNumber: 3`. Create a ticket in 1.4.0. It receives `T-0003` and the resulting file still contains all three tickets.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-84: The operations instructions explain the behavior of a 1.4.0 save during rollback.
Observable: The rollback procedure stops the new service, keeps a copy of its data file and starts 1.4.0 on the current file. It states that 1.4.0 reads the tickets and drops `due` when it next saves, including on clean shutdown. It directs operators to keep the pre-rollback copy as the record of previously assigned deadlines.
Source: existing: src/persistence.js

### C-85: Rollout documentation preserves the original deadlines across a subsequent re-enable after a 1.4.0 write.
Observable: The rollback instructions explain that, with the service stopped, operators reapply only the saved `due` values by ticket ID from the pre-rollback copy to the current data file before running backfill again. The current file keeps all rollback-era edits and tickets. Reapplied deadlines keep their original values and backfill assigns only the missing ones.
Source: choice: 1.4.0 can continue serving the current file but its writer drops additive ticket properties, so the existing file-copy practice retains the originally assigned deadlines.

### C-86: The service continues to require no npm dependencies.
Observable: `package.json` adds no runtime or development dependencies and Node.js 22 can run `npm start` and `npm test` without installing packages.
Source: existing: CONTRIBUTING.md

### C-87: `npm start` continues to launch `src/server.js` on the configured `PORT`.
Observable: Start with `PORT=0`. The startup line names the assigned port and `GET /health` on that port succeeds. Supplying a free nonzero port in the supported range makes the startup line name that port.
Source: existing: README.md

### C-88: The default service port remains 4180.
Observable: The startup configuration for an unset or blank `PORT` resolves to `4180`.
Source: existing: src/config.js

### C-89: The service still refuses an invalid configured port.
Observable: `PORT=http`, `PORT=-1`, `PORT=1.5` and `PORT=65536` each cause exit 2 before the server listens. Standard error names `PORT` and the whole-number requirement or the inclusive range `0` through `65535`.
Source: existing: src/config.js

### C-90: An unset or blank `DATA_FILE` still makes the service in-memory only.
Observable: Run with `DATA_FILE` unset, empty or all whitespace. Create `T-0001`. Restart and the listing is `{"items":[],"next":null}`.
Source: existing: README.md

### C-91: The request logging switch still accepts only the exact value `1`.
Observable: With `LOG_REQUESTS=1`, one `GET /health` adds one request log line to standard error with method, URL, status 200 and elapsed time in milliseconds. With the variable unset, blank or `true`, it adds none.
Source: existing: src/config.js

### C-92: `SIGTERM` still causes a clean shutdown.
Observable: Send `SIGTERM` to the service process with a request in flight. The worker stops, the request can complete, the state is saved and the process exits 0.
Source: existing: docs/operations.md

### C-93: The health endpoint continues returning the existing success object.
Observable: `GET /health` returns HTTP 200 with exactly `{"status":"ok"}` with either flag state.
Source: existing: docs/api.md

### C-94: HTTP responses still use the JSON content type.
Observable: A successful `GET /health` and a failing `GET /missing` each have `content-type: application/json; charset=utf-8`.
Source: existing: docs/api.md

### C-95: Malformed requests still use the invalid error envelope.
Observable: Submit invalid JSON to `POST /tickets`. The response is HTTP 400 with `{"error":{"code":"invalid","message":"request body is not valid JSON"}}`.
Source: existing: src/http.js

### C-96: Unknown routes still use the not-found error envelope.
Observable: `GET /missing` gives HTTP 404 with `{"error":{"code":"not_found","message":"no route for GET /missing"}}`.
Source: existing: src/app.js

### C-97: Unsupported methods still use the not-found error envelope.
Observable: `DELETE /tickets/T-0001` gives HTTP 404 with `{"error":{"code":"not_found","message":"/tickets/T-0001 does not answer DELETE; it answers GET, PATCH"}}`.
Source: existing: src/app.js

### C-98: Well-formed requests disallowed by ticket state still use the conflict error envelope.
Observable: Attempt `open` to `resolved` for `T-0001`. The response is HTTP 409 with `{"error":{"code":"conflict","message":"ticket T-0001 cannot go from open to resolved: it can go to in_progress"}}`.
Source: existing: docs/decisions/0004-error-envelope.md

### C-99: Unexpected handler failures still use the opaque internal error envelope.
Observable: Cause the store used by the HTTP handler to throw an unexpected exception on a read. The response is HTTP 500 with exactly `{"error":{"code":"internal","message":"internal error"}}`.
Source: existing: src/errors.js

### C-100: Unexpected handler failures still appear in the service log.
Observable: Cause an unexpected exception with text `broken read` while handling `GET /tickets`. The log contains an error for `GET /tickets failed` with `broken read`.
Source: existing: docs/decisions/0004-error-envelope.md

### C-101: Error envelopes retain optional details when supplied by an application error.
Observable: When a handler throws an invalid application error with message `bad` and details `{"field":"title"}`, the HTTP 400 body is `{"error":{"code":"invalid","message":"bad","details":{"field":"title"}}}`.
Source: existing: src/errors.js

### C-102: A trailing slash still selects the same HTTP route.
Observable: `GET /tickets/` has the same status and body as `GET /tickets` for the same state.
Source: existing: src/router.js

### C-103: Route parameters are still percent-decoded.
Observable: Given `T-0001`, `GET /tickets/T%2D0001` returns the same HTTP 200 ticket as `GET /tickets/T-0001`.
Source: existing: src/router.js

### C-104: Invalid percent-encoding in a route parameter is still a request error.
Observable: `GET /tickets/%E0%A4%A` gives HTTP 400 with `{"error":{"code":"invalid","message":"path segment %E0%A4%A is not valid percent-encoding"}}`.
Source: existing: src/router.js

### C-105: Ticket write endpoints still require a JSON object body.
Observable: Create, patch or transition with an omitted, blank or non-object JSON body, such as `null`, `[]` or `"hello"`. HTTP 400 gives `{"error":{"code":"invalid","message":"request body must be a JSON object"}}`.
Source: existing: src/http.js

### C-106: The default maximum request body remains 65,536 bytes.
Observable: With `MAX_BODY_BYTES` unset or blank, a valid create JSON object padded with whitespace to 65,536 UTF-8 bytes succeeds. Pad it to 65,537 bytes and HTTP 400 gives `error.code: "invalid"` with message `request body is larger than 65536 bytes`.
Source: existing: README.md

### C-107: `MAX_BODY_BYTES` still accepts whole-number settings from 1,024 to 1,048,576 inclusive.
Observable: Startup accepts `1024` and `1048576`. It exits 2 before listening for `1023`, `1048577` or `2048.5`, with standard error naming `MAX_BODY_BYTES`.
Source: existing: src/config.js

### C-108: The body-size check still uses the configured inclusive byte limit.
Observable: With `MAX_BODY_BYTES=1024`, a valid creation JSON object padded to 1,024 bytes succeeds. The same body padded to 1,025 bytes returns HTTP 400 with `{"error":{"code":"invalid","message":"request body is larger than 1024 bytes"}}`.
Source: existing: src/http.js

### C-109: Unknown request body fields still cause a validation error.
Observable: Add `"owner":"dana"` to an otherwise valid create or transition body, or send a patch with `"requester":"li"`. The response is HTTP 400 with `error.code: "invalid"` and `error.message` equal to `unknown field: owner` or `unknown field: requester`.
Source: existing: docs/api.md

### C-110: Creating a ticket still returns HTTP 201 with the created ticket.
Observable: Send `{"title":"VPN drops","requester":"li@example.com"}` to `POST /tickets`. Its HTTP 201 body equals the HTTP 200 response body from reading its returned ID immediately afterward.
Source: existing: docs/api.md

### C-111: New tickets still start in the open state.
Observable: A valid create request returns a ticket with `status: "open"` for any of the four priorities.
Source: existing: docs/api.md

### C-112: Ticket IDs still use a positive sequential number with at least four digits.
Observable: The first two tickets in an empty store are `T-0001` and `T-0002`. Given `nextNumber: 9999`, the next two are `T-9999` and `T-10000`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-113: Ticket numbers still continue across a restart.
Observable: Create `T-0001` and `T-0002` with persistence, then restart. The next creation returns `T-0003`.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-114: The creation timestamp still records the time of creation.
Observable: Create a ticket with the clock at `2025-09-01T08:15:00.123Z`. The response gives `created: "2025-09-01T08:15:00.123Z"`, and subsequent mutations leave that value fixed.
Source: existing: docs/api.md

### C-115: A new ticket's updated timestamp still starts at its creation instant.
Observable: Create a ticket at `2025-09-01T08:15:00.123Z`. The response gives `updated: "2025-09-01T08:15:00.123Z"`.
Source: existing: src/store.js

### C-116: The create endpoint still defaults omitted priority to normal.
Observable: Send `{"title":"VPN drops","requester":"li@example.com"}`. The created ticket has `priority: "normal"` with either flag state.
Source: existing: docs/api.md

### C-117: Ticket priority still accepts exactly the four existing lowercase values.
Observable: Creation and patch accept `low`, `normal`, `high` and `urgent`. Values `critical`, `HIGH`, `null` and `""` each return HTTP 400 with `error.message: "priority must be one of low, normal, high, urgent"`.
Source: existing: src/tickets/validate.js

### C-118: A supplied title is still trimmed before storage.
Observable: Create or patch with title `"  VPN drops  "`. The ticket has `title: "VPN drops"`.
Source: existing: src/tickets/validate.js

### C-119: The supplied title still must be a nonempty string after trimming.
Observable: Creating without a title or supplying a nonstring title for a create or patch gives HTTP 400 with `error.message: "title must be a string"`. A supplied string of only spaces gives HTTP 400 with `error.message: "title must not be empty"`.
Source: existing: src/tickets/validate.js

### C-120: The title limit remains 200 characters after trimming.
Observable: A title of 200 `x` characters is accepted. A title of 201 `x` characters gives HTTP 400 with `error.message: "title must be at most 200 characters"`.
Source: existing: src/tickets/validate.js

### C-121: A ticket title must still fit on one raw output line.
Observable: A title containing an embedded U+0000 through U+001F or U+007F character, including `one\ttwo` or `one\ntwo`, gives HTTP 400 with `error.message: "title must be a single line of text"` when otherwise valid.
Source: existing: src/tickets/validate.js

### C-122: A supplied requester is still trimmed before storage.
Observable: Create with requester `"  li@example.com  "`. The ticket has `requester: "li@example.com"`.
Source: existing: src/tickets/validate.js

### C-123: The requester still must be a nonempty string after trimming.
Observable: Omitting requester or supplying a nonstring gives HTTP 400 with `error.message: "requester must be a string"`. A requester of only spaces gives HTTP 400 with `error.message: "requester must not be empty"`.
Source: existing: src/tickets/validate.js

### C-124: The requester limit remains 64 characters after trimming.
Observable: A requester of 64 `r` characters is accepted. One of 65 gives HTTP 400 with `error.message: "requester must be at most 64 characters"`.
Source: existing: src/tickets/validate.js

### C-125: A ticket requester must still be single-line text.
Observable: An otherwise valid requester containing an embedded U+0000 through U+001F or U+007F character, including `one\ttwo` or `one\ntwo`, gives HTTP 400 with `error.message: "requester must be a single line of text"`.
Source: existing: src/tickets/validate.js

### C-126: A requester still need not be an email address.
Observable: A valid create request with `requester: "Help Desk"` succeeds and keeps that requester string.
Source: existing: docs/api.md

### C-127: Reading an existing ticket still returns HTTP 200.
Observable: After ticket creation, `GET /tickets/T-0001` returns HTTP 200 with that ticket object.
Source: existing: docs/api.md

### C-128: A valid request for a missing ticket still returns HTTP 404.
Observable: Read, patch, transition or request audit history for missing `T-0042` using otherwise valid requests. Each gives `{"error":{"code":"not_found","message":"ticket T-0042 not found"}}` with HTTP 404. For `GET /tickets/42` the same status and code accompany the message `ticket 42 not found`.
Source: existing: src/store.js

### C-129: A patch still accepts a title, a priority or both.
Observable: Patch an open ticket with `{"title":"New title"}`, then `{"priority":"low"}`, then `{"title":"Final title","priority":"high"}`. Each returns HTTP 200 with the changed values and preserves existing fields omitted by that patch.
Source: existing: docs/api.md

### C-130: An empty patch is still invalid.
Observable: `PATCH /tickets/T-0001` with `{}` returns HTTP 400 with `{"error":{"code":"invalid","message":"nothing to change: give a title or a priority"}}`.
Source: existing: src/tickets/validate.js

### C-131: A closed ticket still rejects patches.
Observable: For closed `T-0001`, even a valid patch giving the existing title returns HTTP 409 with `{"error":{"code":"conflict","message":"ticket T-0001 is closed and can no longer change"}}`.
Source: existing: src/store.js

### C-132: An actual ticket mutation still sets its updated timestamp to the time of the change.
Observable: Create at `2025-09-01T08:00:00.000Z`. At `2025-09-01T08:01:00.000Z` patch its priority to a different value or transition it to `in_progress`. The HTTP 200 response in either case gives `updated: "2025-09-01T08:01:00.000Z"`.
Source: existing: docs/api.md

### C-133: A no-op patch still leaves the updated timestamp unchanged.
Observable: Create a normal ticket at `2025-09-01T08:00:00.000Z` and at `2025-09-01T08:01:00.000Z` patch its priority to normal again. HTTP 200 gives `updated: "2025-09-01T08:00:00.000Z"`.
Source: existing: docs/api.md

### C-134: Ticket lifecycle transitions still follow the existing directed state graph.
Observable: The complete set of moves returning HTTP 200 with the target status is `open → in_progress`, `in_progress → resolved`, `resolved → closed` and `resolved → open`. Every other pair from the four named statuses, including self-transitions and any move from closed, yields HTTP 409 `conflict` without changing the ticket.
Source: existing: src/tickets/states.js

### C-135: An invalid or omitted transition target still fails validation.
Observable: A transition body of `{}` or a `to` value of `done`, `null` or `OPEN` gives HTTP 400 with `error.message: "to must be one of open, in_progress, resolved, closed"`.
Source: existing: src/tickets/validate.js

### C-136: An unfiltered ticket list still uses the existing cursor response shape.
Observable: `GET /tickets` returns HTTP 200 with exactly the two top-level keys `items` and `next`. For an empty store the body is `{"items":[],"next":null}`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-137: Ticket lists still sort in ascending numeric ID order.
Observable: When matching tickets include `T-0002`, `T-9999` and `T-10000`, the listing puts those IDs in that order regardless of their due times.
Source: existing: docs/decisions/0002-prefixed-sequential-ids.md

### C-138: The default listing page size remains 20.
Observable: Create 23 tickets. Omitting `limit` gives `T-0001` through `T-0020` with a non-null cursor. Following it gives `T-0021` through `T-0023` with `next: null`.
Source: existing: docs/api.md

### C-139: The listing still accepts decimal whole-number limits from 1 to 100 inclusive.
Observable: Given 101 eligible tickets, `limit=1`, `limit=002` and `limit=100` yield 1, 2 and 100 items, respectively. `limit=0`, `limit=101`, `limit=2.5`, `limit=-1`, `limit=ten` and `limit=` each yield HTTP 400 with `error.message: "limit must be a whole number from 1 to 100"`.
Source: existing: src/tickets/query.js

### C-140: The ticket listing still accepts the four named statuses as status filter values.
Observable: With one ticket per status, each of `status=open`, `status=in_progress`, `status=resolved` and `status=closed` returns the single ticket in that status when used alone. `status=done` and `status=` return HTTP 400 with `error.message: "status must be one of open, in_progress, resolved, closed"`.
Source: existing: docs/api.md

### C-141: The ticket listing still accepts the four named priorities as priority filter values.
Observable: With one ticket per priority, each of `priority=low`, `priority=normal`, `priority=high` and `priority=urgent` returns the single ticket at that priority when used alone. `priority=critical` and `priority=` return HTTP 400 with `error.message: "priority must be one of low, normal, high, urgent"`.
Source: existing: docs/api.md

### C-142: The listing still ignores unrecognized query parameters.
Observable: `GET /tickets?offset=40&sort=title` returns exactly the same page as `GET /tickets` on the same state with either flag state.
Source: existing: test/query.test.js

### C-143: A next-page cursor still encodes the last returned ticket's ID using cursor format version 1.
Observable: When page one ends at `T-0002` and more matches remain, `next` is `eyJ2IjoxLCJhZnRlciI6IlQtMDAwMiJ9`, the base64url encoding of `{"v":1,"after":"T-0002"}`. This remains true when the page is filtered by `overdue=true`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-144: The cursor still resumes strictly after its ticket ID.
Observable: Fetch a first page ending at `T-0002`. If subsequent data or filter eligibility changes remove `T-0002` from the matching set, following that cursor with the same filters still starts at the first matching ID numerically greater than 2.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-145: The cursor is still null exactly when no matching item follows the page.
Observable: With 2 matching tickets, `limit=2` returns both with `next: null`. With `limit=1` the first page has a cursor. Using a usable cursor after every matching numeric ID returns `{"items":[],"next":null}`.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-146: Unusable supplied cursors still yield a listing error.
Observable: Send an empty cursor, `abc`, a base64url encoded object with `v: 2`, a version-1 cursor with an empty `after`, or a version-1 cursor with `after: "T-1"`. Each returns HTTP 400 with `{"error":{"code":"invalid","message":"cursor is not one this service issued"}}`.
Source: existing: src/store.js

### C-147: The cursor format remains usable after due times are enabled.
Observable: Fetch a first page ending at `T-0001` while due times are off. After backfill and enabled startup, pass its `next` as `cursor` with the same filters. The page starts after `T-0001` and includes `due` for every returned ticket.
Source: existing: docs/decisions/0005-cursor-pagination.md

### C-148: An explicit actor is still trimmed before recording.
Observable: Patch a ticket using `X-Actor:   dana  `. Its appended audit entry has `actor: "dana"`.
Source: existing: src/http.js

### C-149: The default actor remains system.
Observable: A change with no `X-Actor` header and a change with a blank header each append an entry with `actor: "system"`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-150: The actor limit remains 64 characters after trimming.
Observable: A valid write with an actor of 64 `a` characters succeeds. At 65 it returns HTTP 400 with `{"error":{"code":"invalid","message":"X-Actor must be at most 64 characters"}}`.
Source: existing: src/http.js

### C-151: Ticket history still returns its existing audit envelope.
Observable: `GET /tickets/T-0001/audit` returns HTTP 200 with exactly `{"items":[...]}`, containing only that ticket's entries in oldest-first order.
Source: existing: docs/api.md

### C-152: Each real ticket change still appends one audit entry.
Observable: Create `T-0001`, patch its title and transition it to `in_progress`. Its audit actions are exactly `ticket.created`, `ticket.updated` and `ticket.transitioned`, in that order.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-153: Audit sequence numbers still count entries across the entire log from 1.
Observable: Create `T-0001`, create `T-0002`, then patch `T-0001`. Ticket 1 has audit sequence numbers 1 and 3, while ticket 2 has sequence number 2.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-154: Later changes still preserve existing audit entries.
Observable: Save the full contents of the creation entry. Patch and transition the ticket, then restart from the data file. The original entry is deeply equal to the saved entry, with the additional entries following it.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-155: A creation audit entry retains its legacy field shape.
Observable: Create `T-0001` at `2025-09-01T08:15:00.123Z` as `dana` with title `VPN drops`, default priority and requester `li@example.com`. Its entry is `{"seq":1,"ticket":"T-0001","action":"ticket.created","actor":"dana","at":"2025-09-01T08:15:00.123Z","changes":{"title":{"from":null,"to":"VPN drops"},"priority":{"from":null,"to":"normal"},"requester":{"from":null,"to":"li@example.com"},"status":{"from":null,"to":"open"}}}` in either mode.
Source: existing: test/store.test.js

### C-156: The patch audit entry still includes only fields changed by the patch.
Observable: Patch a normal ticket to high while also giving its existing title. The last entry has `action: "ticket.updated"` and `changes: {"priority":{"from":"normal","to":"high"}}` in either mode.
Source: existing: test/store.test.js

### C-157: The transition audit entry still records the status move.
Observable: Transition an open ticket to `in_progress`. The last entry has `action: "ticket.transitioned"` and `changes: {"status":{"from":"open","to":"in_progress"}}` in either mode.
Source: existing: docs/api.md

### C-158: A no-op patch still appends no audit entry.
Observable: Repeat the existing title and priority on a newly created open ticket. Its audit still has exactly the one creation entry.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-159: A no-op patch still enqueues no notification.
Observable: With the worker off, compare `GET /admin/outbox` before and after repeating the same title and priority in a patch. The responses have deeply equal bodies.
Source: existing: CONTRIBUTING.md

### C-160: Creation still enqueues a received notification for the requester.
Observable: With the worker off, create `T-0001` with title `VPN drops` and requester `li@example.com`. Its only pending event has `id: 1`, `type: "ticket.created"`, `key: "ticket.created:T-0001"`, `ticket: "T-0001"`, `to: "li@example.com"` and `data: {"title":"VPN drops"}`, including when due times are enabled.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-161: Resolving a ticket still enqueues its resolved notification.
Observable: With the worker off, move `T-0001` from open to in-progress to resolved. The first move adds no event. The second adds one pending event with `type: "ticket.resolved"` and `key: "ticket.resolved:T-0001"`, to the ticket's requester with the existing title-only `data` object.
Source: existing: docs/api.md

### C-162: Ticket mutations still commit alongside the audit entry and any resulting outbox event.
Observable: With persistence and the worker off, inspect the file as soon as creation returns HTTP 201. One complete document contains the created ticket, its creation audit entry, the pending received notification and the advanced counters.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-163: A pending notification key still suppresses duplicate events.
Observable: With the worker off, resolve, reopen, move to in-progress, then resolve one ticket again. Exactly 1 pending `ticket.resolved:T-0001` event exists.
Source: existing: docs/operations.md

### C-164: A sent or dead notification key still permits a later enqueue.
Observable: After a resolved event with ID 2 becomes sent or dead, reopen the ticket, move it to in-progress and resolve it again. The new resolved notification has ID 3 while the previous event retains ID 2 and its sent or dead state.
Source: existing: src/outbox.js

### C-165: The outbox endpoint still returns events grouped in their existing state arrays.
Observable: `GET /admin/outbox` returns HTTP 200 with `pending`, `sent` and `dead` arrays, even if all are empty. Each event has the existing keys `id`, `key`, `type`, `to`, `ticket`, `data`, `status`, `attempts`, `created`, `nextAttemptAt`, `lastError`, `sentAt`.
Source: existing: docs/api.md

### C-166: New pending outbox events are still immediately eligible for delivery.
Observable: After creation at `2025-09-01T08:15:00.123Z` with the automatic worker off, the pending event shows `attempts: 0`, both `created` and `nextAttemptAt` equal to `2025-09-01T08:15:00.123Z`, and both `sentAt` and `lastError` equal to null. A worker pass at that exact clock instant delivers the event.
Source: existing: src/outbox.js

### C-167: The default worker interval remains 500 milliseconds.
Observable: With `WORKER_INTERVAL_MS` unset or blank, the startup log says `worker every 500 ms`.
Source: existing: README.md

### C-168: The worker interval still accepts whole milliseconds from 0 through 3,600,000.
Observable: Startup accepts `WORKER_INTERVAL_MS=0` and `WORKER_INTERVAL_MS=3600000`. Values `-1`, `1.5` and `3600001` cause exit 2 with a diagnostic naming `WORKER_INTERVAL_MS`.
Source: existing: src/config.js

### C-169: A worker interval of 0 still disables background work.
Observable: Run with `WORKER_INTERVAL_MS=0` and `NOTIFY_FILE` set to an absent file. Create one ticket. Its event stays pending and no notification file is created.
Source: existing: docs/operations.md

### C-170: A successful delivery still marks the event sent.
Observable: Deliver a pending event on its first attempt at `2025-09-01T08:15:00.123Z`. The sent record has `attempts: 1`, `sentAt: "2025-09-01T08:15:00.123Z"`, `nextAttemptAt: null` and `lastError: null`. Later worker passes leave it in the sent array without redelivery in uninterrupted operation.
Source: existing: src/outbox.js

### C-171: Failed deliveries still wait for exponential backoff.
Observable: Fail the first four attempts, advancing the clock to each retry in turn. The next retry is scheduled 1,000, 2,000, 4,000 and 8,000 milliseconds after the respective failure, with the event in `pending`. It is ineligible 1 millisecond before each retry instant and eligible at the instant itself. The shared backoff calculation caps delays at 300,000 milliseconds.
Source: existing: docs/operations.md

### C-172: The fifth failed delivery still makes a notification dead.
Observable: After 5 failures for one event the outbox retains it in `dead` with `attempts: 5`, `nextAttemptAt: null` and the last failure message in `lastError`. Further worker passes do not retry it.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-173: A stored delivery failure message remains capped at 500 characters.
Observable: Fail a delivery with a 501-character error message. The outbox stores the first 500 characters in `lastError`.
Source: existing: src/outbox.js

### C-174: A dead notification still produces a warning.
Observable: Fail delivery 5 times for notification 1 of type `ticket.created` to `li@example.com` with error `relay unavailable`. Standard error logs a warning containing `notification 1 (ticket.created to li@example.com) is dead after 5 attempts: relay unavailable`.
Source: existing: src/worker.js

### C-175: Notification delivery still appends one JSON line per attempt that sends successfully to the configured file.
Observable: With `NOTIFY_FILE` configured, successfully deliver a created event and a resolved event. The file has two newline-terminated JSON records, each with `at`, `id`, `key`, `type`, `to`, `ticket`, `subject` and `body`.
Source: existing: docs/operations.md

### C-176: An unset or blank notification path still keeps deliveries in memory.
Observable: Leave `NOTIFY_FILE` unset or blank, create one ticket and let the worker deliver it. The service notifier's in-memory deliveries contain one received message and no file is written for it.
Source: existing: README.md

### C-177: The received notification retains its existing text.
Observable: Deliver a creation event for `T-0001` with title `VPN drops`. Its subject is `[T-0001] We received your request` and its body is `Your request "VPN drops" is ticket T-0001. The help desk will be in touch.` in either mode.
Source: existing: src/templates.js

### C-178: The resolved notification retains its existing text.
Observable: Deliver a resolved event for `T-0001` with title `VPN drops`. Its subject is `[T-0001] Resolved` and its body is `Ticket T-0001 "VPN drops" was resolved. Reply within 7 days to reopen it.` in either mode.
Source: existing: src/templates.js

### C-179: An unknown notification type still goes through the existing retry path.
Observable: Load a pending event of type `ticket.misfiled` and let the worker attempt it. `lastError` is `no template for notification type ticket.misfiled` after the first attempt. Reaching 5 failures places the event in `dead`.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-180: An unrecorded delivery still may be repeated after restart.
Observable: Restart from a version-1 file whose pending event already has a line in `NOTIFY_FILE` from a delivery that did not reach the data-file save. A successful delivery after the restart appends a line with that same event ID and key.
Source: existing: docs/decisions/0006-notification-outbox.md

### C-181: The data file still holds one whole version-1 state document.
Observable: After a ticket or delivery changes, `DATA_FILE` contains top-level keys `version`, `savedAt`, `nextNumber`, `tickets`, `audit` and `outbox` with `version: 1`. The outbox contains `nextId` and `events`.
Source: existing: docs/decisions/0008-json-data-file.md

### C-182: Ongoing service saves still replace the whole data file atomically.
Observable: After a successful change, the service has written a temporary file beside the data file and renamed it into place. A reader opening the fixed data-file path observes the whole old or whole new document during the write. After success there is no temporary file from the save.
Source: existing: docs/decisions/0008-json-data-file.md

### C-183: Restart still restores all saved ticket, audit and outbox state.
Observable: Save two tickets, transition one, then record one delivery with another still pending. Restart with the worker off and read all tickets, their histories and the outbox. They equal the responses captured before shutdown, including assigned due times when enabled.
Source: existing: docs/decisions/0008-json-data-file.md

### C-184: The disabled new service still accepts existing version-1 files without due times.
Observable: Point the new service with `DUE_TIMES` unset to a valid 1.4.0 file. It starts and returns all its existing tickets with their original values.
Source: existing: docs/decisions/0008-json-data-file.md

### C-185: An unreadable or malformed data file still stops service startup.
Observable: Try a configured existing file that cannot be read, a file containing `{ not json`, or a JSON array instead of a document. Startup exits 2 with standard error containing the path and the corresponding reason `cannot be read`, `is not JSON` or `is not a data file`.
Source: existing: src/persistence.js

### C-186: The service still rejects unsupported data-file versions.
Observable: With either flag state, a document with `version: 2` causes exit 2 before listening. Standard error contains the path and `has version 2; this service reads version 1`.
Source: existing: docs/decisions/0008-json-data-file.md

### C-187: Legacy ticket record validation still rejects invalid field values.
Observable: In an otherwise valid file corrupt one ticket field at a time: noncanonical ID `T-1`, empty `title`, empty `requester`, priority `critical`, status `done`, invalid `created` or invalid `updated`. Startup exits 2 and identifies the file and the corresponding `tickets[0].<field>`.
Source: existing: src/persistence.js

### C-188: Duplicate ticket IDs still prevent startup.
Observable: Duplicate a `T-0001` ticket in an otherwise valid file. Startup exits 2 and standard error names the file and states `ticket T-0001 appears twice`.
Source: existing: src/persistence.js

### C-189: The file's next ticket number still has to be greater than every stored ticket number.
Observable: A valid file with `T-0002` and `nextNumber: 2` causes exit 2 and standard error names the file and reports `nextNumber 2 would reuse the number of T-0002`. With `nextNumber: 0` it reports `nextNumber is not a positive whole number`.
Source: existing: docs/operations.md

### C-190: Invalid audit records still prevent startup.
Observable: Replace `audit` with a non-array, omit `actor` or `at` in a record, or remove `to` from an audit field change. Startup exits 2 and identifies the file and the affected location, such as `audit[0].changes.priority needs from and to`.
Source: existing: src/persistence.js

### C-191: Audit sequence gaps still prevent startup.
Observable: Give a file audit entries with sequence numbers 1 and 3. Startup exits 2 and standard error contains the path and `audit[1].seq is 3, not 2: the log is append-only`.
Source: existing: docs/decisions/0007-append-only-audit-log.md

### C-192: Invalid outbox records still prevent startup.
Observable: In a file with an outbox event at index 0, supply an invalid legacy event field, for example `id: 0`, `key: ""`, `type: ""`, `to: ""`, `status: "lost"`, `attempts: -1`, `data: []`, invalid `created`, or invalid `nextAttemptAt` for a pending event. Each causes exit 2 and standard error identifies the path and `outbox.events[0].<field>`.
Source: existing: src/persistence.js

### C-193: The file's next outbox ID still has to be greater than every stored event ID.
Observable: For a file with event ID 2, setting `outbox.nextId: 2` causes exit 2, naming the path and reporting `outbox.nextId 2 would reuse an event id`. Setting `nextId` to 0 reports `outbox.nextId is not a positive whole number`.
Source: existing: src/persistence.js

### C-194: Unrecognized record fields still stay out of ticket API responses.
Observable: Add `"arbitrary":"ignore me"` to a valid saved ticket. The API response omits `arbitrary` with either flag state.
Source: existing: docs/decisions/0008-json-data-file.md

### C-195: Store reads still return ticket copies.
Observable: Change the `status` and `due` properties of a ticket returned by the store's single-ticket read, then change its priority on the returned list item. A fresh read still shows the original status, assigned due time and priority.
Source: existing: test/store.test.js

### C-196: The operator CLI still opens the file read-only.
Observable: Capture the data file bytes. Run `node bin/tickets.js list` and `node bin/tickets.js show T-0001` using that file, both before and after backfill and with either flag state. After each invocation the bytes are unchanged.
Source: existing: README.md

### C-197: The CLI still accepts its data-file path from `DATA_FILE` or `--data FILE`.
Observable: Put `T-0001` in the file set by `DATA_FILE` and give it a different title in a second file. `node bin/tickets.js show T-0001` shows the first title. Adding `--data` with the second path shows the second title.
Source: existing: bin/tickets.js

### C-198: The normal CLI list still prints the existing table.
Observable: With one ticket, `node bin/tickets.js list` prints columns headed `ID`, `STATUS`, `PRIORITY`, `REQUESTER`, `UPDATED` and `TITLE` in that order. Headers and rows have two spaces between padded columns. The updated field displays `2025-09-01 08:15` for `2025-09-01T08:15:00.123Z`. The output is the same for the matching legacy fields in migrated and unmigrated files.
Source: existing: src/format.js

### C-199: The CLI still prints its existing empty-table message.
Observable: A `list` command that finds no tickets writes exactly `no tickets\n` to standard output and exits 0.
Source: existing: bin/tickets.js

### C-200: The CLI status filter still selects tickets by their status.
Observable: With open and closed tickets in the file, `node bin/tickets.js list --status open` only prints open tickets.
Source: existing: README.md

### C-201: The CLI priority filter still selects tickets by their priority.
Observable: With urgent and low tickets in the file, `node bin/tickets.js list --priority urgent` only prints urgent tickets.
Source: existing: README.md

### C-202: The CLI keeps its legacy matching when both list filters are supplied.
Observable: Given `T-0001=open/low`, `T-0002=in_progress/urgent`, `T-0003=open/urgent` and `T-0004=resolved/high`, `list --status open --priority urgent --raw` prints rows for `T-0001`, `T-0002`, `T-0003` in either flag state.
Source: existing: bin/tickets.js

### C-203: The CLI list still traverses all eligible tickets in numeric ID order.
Observable: With 101 matching records, `node bin/tickets.js list --raw` writes 101 rows, starting with `T-0001` and ending with `T-0101` for an initial sequence.
Source: existing: bin/tickets.js

### C-204: CLI raw output still has exactly the four positional tab-separated columns.
Observable: For `T-0001` with status open, priority urgent and title `VPN drops`, one line of `list --raw` is exactly `T-0001\topen\turgent\tVPN drops\n`, with actual tabs and newline. There is one line per selected ticket, no header and no due column in either flag state. An empty selection writes zero bytes.
Source: existing: README.md

### C-205: The CLI show command preserves its legacy details and history.
Observable: For an existing ticket `show T-0001` exits 0, prints its ID and title first, prints `status`, `priority`, `requester`, `created` and `updated` in order, then a blank line followed by `History` and its oldest-first audit entries. With no stored due or with due times disabled, this output matches 1.4.0.
Source: existing: src/format.js

### C-206: Enabled CLI show displays the assigned due time in the full ticket details.
Observable: Run `DUE_TIMES=on node bin/tickets.js show T-0001` against a saved ticket with `due: "2025-09-01T12:15:00.123Z"`. There is a field labeled `due` on a separate line after `updated` and before `History`, with value `2025-09-01T12:15:00.123Z`. The same command with the flag off omits that line.
Source: choice: show is the full-ticket view, while the table and raw listing retain their existing layouts.

### C-207: Enabled CLI show can still inspect tickets that have no valid stored deadline.
Observable: Against a valid legacy file with no `due`, or with `"due":"tomorrow"` on `T-0001`, `DUE_TIMES=on node bin/tickets.js show T-0001` exits 0 and prints its legacy fields and history without a due line.
Source: choice: the read-only CLI remains available to inspect tickets before correcting or backfilling a data file.

### C-208: The CLI show command keeps its exit status for a missing ticket.
Observable: With a valid file, `node bin/tickets.js show T-0042` exits 1 and writes `tickets: ticket T-0042 not found\n` to standard error.
Source: existing: bin/tickets.js

### C-209: CLI usage errors still exit 2.
Observable: Run with an unknown option, an unknown command or `--data` without a value. The command exits 2 and standard error starts with `tickets: ` followed by the error and the usage text.
Source: existing: bin/tickets.js

### C-210: The CLI help command still works without opening a data file.
Observable: With `DATA_FILE` unset, `node bin/tickets.js --help` and `node bin/tickets.js -h` each exit 0 and print the usage for `tickets [--data FILE] list [--status STATUS] [--priority PRIORITY] [--raw]` and `tickets [--data FILE] show ID`.
Source: existing: bin/tickets.js

### C-211: CLI data-file failures still exit 2.
Observable: Without a configured file the CLI prints `tickets: no data file: set DATA_FILE or pass --data FILE` and usage to standard error. With a non-existent or corrupt configured file, standard error includes the path and `does not exist` or `is not JSON`. Each exits 2.
Source: existing: bin/tickets.js

### C-212: A bad CLI filter value still exits 2.
Observable: Against a valid file, `list --status done` exits 2 and prints `tickets: status must be one of open, in_progress, resolved, closed\n` to standard error.
Source: existing: bin/tickets.js

### C-213: The weekly JSON report still counts the same tickets by the existing raw columns.
Observable: With exactly one open urgent ticket and one resolved high ticket, `node scripts/weekly-report.js --data data/tickets.json --json` produces `{"total":2,"byStatus":{"open":1,"in_progress":0,"resolved":1,"closed":0},"byPriority":{"low":0,"normal":0,"high":1,"urgent":1}}` followed by a newline, before or after backfill and in either flag state.
Source: existing: scripts/weekly-report.js

### C-214: The weekly report still supports its existing human-readable entry point.
Observable: `DATA_FILE=data/tickets.json npm run report:weekly` prints a report with the heading `Ticket report for the week of YYYY-MM-DD` using the UTC calendar date, followed by the existing `By status`, `By priority` and `total` counts.
Source: existing: README.md

### C-215: The weekly report remains read-only.
Observable: Hash the data file before and after a weekly report run. Both hashes match, including when the file holds due times.
Source: existing: docs/operations.md

### C-216: Existing tests continue to pass unchanged.
Observable: Every pre-existing file under `test/` is byte-for-byte identical to the 1.4.0 baseline. A run of `npm test` finishes with exit 0 and no failed tests.
Source: request

### C-217: The new behavior is covered by `node:test` tests under `test/`.
Observable: New `test/*.test.js` files use `node:test` and exercise enabled creation for each default, overrides, deadline immutability, overdue boundaries and filtering, disabled compatibility, backfill, persistence and rollback compatibility.
Source: request

### C-218: The standard test command runs the new tests with the existing suite.
Observable: One invocation of `npm test` runs `node --test` and reports passing cases from both baseline files and the newly added due-time tests.
Source: request

### C-219: The new files follow the existing CommonJS module convention.
Observable: New JavaScript modules use strict mode, Node's standard library imports and named CommonJS exports where they export an interface.
Source: existing: CONTRIBUTING.md

### C-220: The API documentation describes the enabled ticket shape and overdue parameter.
Observable: `docs/api.md` identifies `due` as an ISO UTC timestamp and explains when it is exposed, the exact accepted `overdue` values, the strict deadline comparison, the active statuses and how enabled filters combine with cursor pages.
Source: choice: publish the new API contract where existing clients find the ticket and listing contracts.

### C-221: The configuration documentation lists the feature switch and the four response-hour settings.
Observable: `README.md` gives the exact name and default for `DUE_TIMES`, `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL` and `DUE_HOURS_LOW`, including the hour range and that schedule changes affect future assignments.
Source: choice: expose the operator-controlled settings in the same configuration table as the current settings.

### C-222: A new decision record documents the data-file compatibility rule.
Observable: The decisions index points to an accepted record for adding `tickets[].due` to format version 1. The record gives the backfill and rollback consequences without rewriting prior decisions.
Source: existing: CONTRIBUTING.md

### C-223: The release metadata follows the existing release convention.
Observable: The next release increments the package version from `1.4.0` and `CHANGELOG.md` has a heading for the same new version describing the due-time change.
Source: existing: CONTRIBUTING.md
