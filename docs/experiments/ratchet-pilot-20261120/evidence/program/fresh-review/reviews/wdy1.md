Verdict: reject
## What must be true
- Run npm start on a free PORT and GET /health to see 200 with status ok. | held
- With DUE_TIMES unset or set to a value other than on, create, fetch, patch, transition and list tickets with the 1.4.0 response shape, and verify that overdue query values and due-hours settings leave those API responses unchanged. | held
- With DUE_TIMES=on, create urgent, high, normal, low and default-priority tickets and see an ISO due equal to created plus 4, 24, 72, 168 and 72 hours respectively on create, get, patch, transition and list. | held
- Change response hours through configuration and restart to see the new hours apply to new tickets while already assigned deadlines stay fixed, including after priority changes. | held
- Query overdue=true with both past and future due times and all four statuses, then page and filter the results to see only open and in-progress tickets whose deadlines have passed. | held
- Use the documented startup procedure on a 1.4.0 data file and verify that legacy deadlines are on disk before the first enabled API response, derive from the stored creation time and priority, and survive repeating the procedure with different hours. | held
- On the new release, create a ticket while DUE_TIMES is off, then change its priority and the response hours before enabling visibility. Verify that its saved deadline still reflects the priority and schedule at creation. | broken
- Start the actual 1.4.0 release against the file written by the delivery and retrieve every legacy and new ticket. | held
- Create and fetch tickets with sequential IDs, default normal priority and trimmed text, and verify invalid payloads, unknown routes and missing IDs keep the 1.4.0 responses. | held
- Patch a ticket, repeat the same patch, transition through the lifecycle including reopening, and verify audit entries, actor, timestamps and conflict responses match 1.4.0. | held
- With no overdue filter, list by status, by priority and by both, and compare the actual 1.4.0 matches in ID order, cursor pagination and invalid-query responses. | held
- Check the outbox with the worker off and with delivery enabled, and verify notifications, history and the next ticket ID persist across a restart. | held
- Run the read-only CLI list, filtered list, raw list and show, including with DUE_TIMES off, and verify its exit codes and the weekly report's counts and raw column positions still work. | held
- Run npm test including the builder's node:test tests under test/ and verify the prior tests are unchanged and pass. | held
## Findings
- A new ticket gets a deadline based on its priority and response hours at creation. Later priority or schedule changes leave that deadline fixed. | The flag also disables assignment. A ticket created on the new release while the flag is off gets its deadline from its later priority and the schedule at re-enablement. | Probe: Start with PORT=0 DUE_TIMES=on DATA_FILE pointing to a temporary file and create a ticket to prepare the file. Restart with DUE_TIMES=off DUE_HOURS_NORMAL=9 on the same file. POST /tickets with priority normal returned 201 for T-0002 with created 2026-11-22T02:20:03.533Z. PATCH /tickets/T-0002 with priority urgent returned 200. The file retained T-0001's due and T-0002 still had no due. Restart with DUE_TIMES=on DUE_HOURS_URGENT=2. GET /tickets/T-0002 returned due 2026-11-22T04:20:03.533Z, two hours after creation using the later urgent priority and schedule.
## Decisions made for the requester
- Configure each priority with its own DUE_HOURS_* variable, accept positive whole hours, and apply changes at restart. | Support fractional or zero hours, or reload a shared schedule while the process runs.
- Reject an enabled create whose deadline falls outside the timestamp range with HTTP 500 before saving, and refuse enabled preparation on overflow. | Reject the schedule at startup when a new ticket could exceed the timestamp range.
- Backfill synchronously on enabled startup before accepting traffic, and allow enabled operation without a data file for local use. | Provide a separate preparation command and require a prepared file for enabled startup.
- When enabled, accept exactly one overdue=true or overdue=false and return 400 for other supplied forms. | Ignore malformed values or take the first repeated value.
- Intersect overdue eligibility with the existing union of status and priority matches when both filters are present. | Require both status and priority to match in the overdue listing.
- Keep deadline assignment out of the audit log. | Record it in creation and backfill audit entries.
- Refuse enabled startup for a malformed stored due value and preserve it while visibility is off. | Treat a malformed deadline as missing and recompute it.
- Keep the human-readable CLI list and show output unchanged when deadlines are enabled. | Display the deadline in the human-readable CLI while preserving the raw column contract.
- Keep rollback compatible with the unmodified 1.4.0 reader. After a 1.4.0 save drops the due fields, re-upgrade computes missing deadlines from the then-current ticket data and schedule. | Preserve deadline assignments across old-writer saves in an additional store.
