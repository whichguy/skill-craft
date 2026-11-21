## Failing now

- C-2: At the largest representable creation instant, the disabled release returned HTTP 500 for an urgent creation that 1.4.0 accepted with HTTP 201.
- C-10: The four `DUE_HOURS_*` overrides left creation deadlines at their defaults, both with all overrides set and with only the high override set.
- C-12: The minimum, trimmed leading-zero value, and maximum all left the urgent interval at four hours. The service also attempted to listen with either out-of-range value.
- C-13: The service attempted to listen for every invalid value tested across the four priority variables, instead of exiting 2 with the variable named in the diagnostic.
- C-24: After restart, the original high ticket retained its deadline and the second high ticket still received the default 24-hour deadline despite the two-hour override.
- C-40, C-43: The enabled queries returned `T-0001` and `T-0002` along with `T-0003`. The status and priority filters matched on either value.
- C-50: A creation with `DUE_TIMES` unset wrote a `due` key into the new ticket record.
- C-52: Enabled startup attempted to listen on the incomplete file whether the ticket missing `due` was open or closed.
- C-56: Enabled startup rejected the null, number, empty, and `tomorrow` values with `is not a time`. It attempted to listen with an offset timestamp, a timestamp missing milliseconds, and February 30.
- C-57, C-58: Disabled startup rejected the file containing `due: "tomorrow"` with `tickets[0].due is not a time`, preventing reads and the diagnostic-preserving save.
- C-59, C-60, C-61, C-62, C-63, C-64, C-65, C-66, C-67, C-68, C-69, C-70, C-71, C-72, C-73, C-74, C-75, C-76, C-77, C-78, C-79, C-147: Node exited 1 with `MODULE_NOT_FOUND` when invoked on `scripts/backfill-due-times.js`.
- C-80: The operations guide has the legacy data-file instructions and omits the due-time rollout sequence.
- C-84, C-85: The operations guide omits rollback instructions, including the loss of saved deadlines on a 1.4.0 save and how to merge deadlines before re-enabling.
- C-206: Enabled CLI `show` printed the legacy fields and history with no `due` line.
- C-207: Enabled CLI `show` exited 2 for the record with `due: "tomorrow"` instead of printing its legacy details and history.
- C-217: The `test/` directory contains only the 1.4.0 test files.
- C-218: `npm test` passed and reported baseline cases. The release has no new due-time test file for it to run.
- C-220: The API guide has the legacy ticket shape and listing parameters, with no `due` or `overdue` contract.
- C-221: The README configuration omits `DUE_TIMES` and the four `DUE_HOURS_*` settings.
- C-222: The decisions index has no new record covering version-1 due-time compatibility.
- C-223: The package still reports version `1.4.0` and the changelog has no due-time release entry.

## Discoveries

- Disabled creation never computes a deadline, even at the limit of the service clock. | Observable: With `DUE_TIMES=off` and the clock at `+275760-09-13T00:00:00.000Z`, a valid urgent creation returns HTTP 201 with the seven legacy fields. | Why: 1.4.0 accepts that creation. The new release returned HTTP 500 even though it would hide the deadline.
- The four `DUE_HOURS_*` variables are the only response-hour inputs. `RESPONSE_HOURS` is ignored. | Observable: With the four settings unset, `RESPONSE_HOURS=urgent=2` leaves an enabled urgent creation due four hours later, and `RESPONSE_HOURS=bad` does not affect disabled startup. | Why: The build uses this undocumented variable to change enabled deadlines and rejects a malformed value even while disabled. 1.4.0 ignores it.
- The legacy title and requester limits count UTF-16 code units after trimming. | Observable: A title of 100 repetitions of `🙂` is accepted and 101 are rejected. A requester of 32 repetitions is accepted and 33 are rejected. | Why: The ASCII boundary tests did not distinguish code-unit length from Unicode character count.
