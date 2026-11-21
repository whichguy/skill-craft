## Failing now

- C-1 — Creating a high-priority ticket with a configured 25-hour window gave it a deadline 24 elapsed hours after creation.
- C-6 — The service used 24 hours for a new high-priority ticket after startup with a 2-hour override.
- C-7 — An urgent ticket used 4 hours with `DUE_HOURS_URGENT=19`.
- C-9 — Startup accepted `DUE_HOURS_URGENT=0` and listened.
- C-10 — Startup listened when applying the override at the current time would exceed the final supported millisecond.
- C-11 — Startup with `DUE_HOURS_URGENT=four` began listening instead of exiting 2 with the variable diagnostic.
- C-34 — The combined overdue query returned the normal open ticket and the urgent in-progress ticket along with the urgent open ticket.
- C-42 — All 105 legacy ticket records still lacked `due` in the data file after startup.
- C-43 — The data file had no deadline derived from the saved creation instant.
- C-44 — After preparation, the data file had no deadline derived from the saved priority, including for the ticket with a different creation-audit priority.
- C-45 — In a mixed file, the saved deadline stayed present and the unassigned record still lacked a deadline.
- C-46 — The disabled service answered HTTP requests while its existing file still lacked deadlines.
- C-47 — An enabled service returned a successful ticket page with an incomplete file on disk.
- C-48 — An enabled service listened on a partially prepared file.
- C-52 — With enabled mode and an unwritable destination, the unsuccessful create appeared in the next list.
- C-60 — Startup published no prepared replacement and left the original legacy file in place.
- C-61 — The service listened with a legacy file and a blocked replacement, so startup gave no save-failure diagnostic.
- C-63 — A ticket with a stored null deadline passed startup validation.
- C-64 — A ticket with a stored deadline one millisecond before its creation instant passed startup validation.
- C-65 — Preparation overflow emitted a bare `RangeError: Invalid time value` without naming the data path or affected ticket.
- C-71 — The operations guide has no deadline-retaining rollback handoff or warning about the next 1.4.0 save or shutdown.
- C-72 — The operations guide has no offline deadline recovery procedure that preserves the latest 1.4.0 state.
- C-73 — The operations guide has no production preparation, file verification, and activation sequence.
- C-74 — The API reference omits the `due` field and its visibility rule.
- C-75 — The API reference omits overdue listing and still describes the ordinary combined filters as requiring every filter to match.
- C-76 — The README omits the four override variables, their defaults, and the effect of restarting with new hours.
- C-214 — The enabled CLI list used the legacy header without a due column, and the enabled show scenario displayed no saved deadline.
- C-216 — The CLI instructions omit how to display saved deadlines.
- C-231 — There are no new due-time `node:test` files under `test/`.
- C-232 — `npm test` discovered the existing suite alone.
- C-234 — The decision index contains no numbered record on compatible deadline storage and preparation.
- C-235 — `package.json` still reports `1.4.0`.
- C-236 — The changelog has no due-time release entry.
- C-237 — The failed create left `T-0007`, creation audit sequence 2, and pending notification 11 visible.
- C-238 — At ticket-sequence exhaustion, create returned HTTP 201 with `T-9007199254740991` even though the next number would be unsafe.

The failing end-to-end scenarios were U-4, U-6, U-7, U-8, U-9, U-11, U-12, and U-15.

## Discoveries

- Worker suppression governs scheduled application work. | Observable: At interval zero the queued notification stays pending even while the HTTP runtime maintains connections. | Why: Node registered a 30-second HTTP connection timer independently of the ticket worker.
- A graceful stop closes the listener while an accepted request with an incomplete body can still finish and be saved. | Observable: Send either shutdown signal during an HTTP upload, then complete the body after new connections are refused. | Why: Both signals completed the accepted write and saved its result.
- Legacy text validity uses the saved string's length before any HTTP-style normalization. | Observable: A version 1 record with whitespace-only text or embedded controls can load and return those original values. | Why: The legacy file fixture retained those values through a startup and a detail read.
- CLI inspection can work with an unusable server schedule configuration. | Observable: Point `show` at a valid saved file while an unrelated `DUE_HOURS_*` setting is invalid. | Why: The operator can still inspect saved work while diagnosing server settings.
- The 300-second retry ceiling belongs to a calculation outside the reachable worker retry sequence. | Observable: A notification schedules four delays, then becomes dead on failure five. A direct ceiling check needs a specified callable calculation interface. | Why: HTTP and data-file tests can observe 1, 2, 4, and 8 seconds and the terminal failure, with no pending retry left to reach the ceiling.
- Fileless delivery has a public success signal in outbox state. | Observable: With `NOTIFY_FILE` unset, an eligible notification reaches `sent`. | Why: The public interfaces expose the delivery outcome. The in-process delivery record has no public reader.
