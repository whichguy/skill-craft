Verdict: reject
## What must be true
- Run npm start on an available PORT and get 200 with {"status":"ok"} from /health. | held
- With due times on, create urgent, high, normal and low tickets and see UTC due timestamps 4, 24, 72 and 168 hours after creation, including 72 hours when priority is omitted. | held
- Change the response hours through operator configuration and observe the new hours on newly created tickets without editing code. | held
- Change a ticket's priority and restart with changed response hours, then confirm the ticket keeps its original due timestamp. | held
- With due times on, see the same due timestamp on create, get, list, patch and transition responses, and see it when viewing a ticket in full on the CLI. | held
- Request overdue=true with past and future tickets in each status and see only past-due open and in-progress tickets. | held
- Page the overdue listing in ticket ID order, with status or priority filters still applied. | held
- Prepare a copy of a 1.4.0 data file before enabling due times, then inspect the file for durable due timestamps calculated from each existing ticket's own creation time and priority, including resolved and closed tickets. | held
- Restart after backfill with different response hours and confirm that the existing due timestamps, tickets, updates, audit and outbox records are preserved. | held
- Leave DUE_TIMES unset or set to a value other than on and verify the original response shapes and behavior, including ignoring overdue as an unknown query parameter and retaining the original CLI show output for an ordinary ticket. | held
- Open a data file written by the new release with the unmodified 1.4.0 server and CLI, and verify every ticket is visible and the next ID is usable. | held
- Without overdue filtering, combine status and priority and follow a cursor to see the same results 1.4.0 returns, including its actual either-filter behavior. | broken
- Create, edit, and transition a ticket and check sequential IDs, trimming, no-op updates, invalid input and closed-ticket errors, actor and audit history, and pending creation and resolution notifications. | held
- Run the worker with a notification file and verify it delivers creation and resolution notifications and records them as sent. | held
- Use CLI list, filtered list, raw and show, and run the weekly report against the same file without rewriting it, keeping the four tab-separated raw columns and original exit codes. | held
- Read a legacy file containing two titles that differ by an actual carriage return versus a literal backslash and r, and distinguish them in the CLI raw title column. | broken
- Start on an invalid data file and get the existing startup error instead of serving an empty store. | held
- Run npm test and see the unmodified existing tests and added node:test coverage pass without installing dependencies. | held
## Findings
- 1.4.0 ordinary listing includes a ticket that matches either the requested status or the requested priority. | Turning on due times makes the same ordinary listing require both filters, changing which tickets callers see even when they omit overdue. | Probe: Run both releases with PORT=0 and copies of a file containing open high tickets T-0001 and T-0005, in-progress urgent tickets T-0002 and T-0006, and no open urgent tickets. Prepare the new copy and request GET /tickets?status=open&priority=urgent&limit=2, then follow next. The old service and the new service with DUE_TIMES unset returned HTTP 200 with T-0001 and T-0002, then T-0005 and T-0006. With DUE_TIMES=on the new service returned HTTP 200 with {"items":[],"next":null}.
- 1.4.0 raw CLI output preserves the title text of records its version-1 reader accepts. | The new CLI replaces a carriage return with a literal backslash and r, making two distinct stored titles indistinguishable in raw output even with due times off. | Probe: Seed a valid version-1 JSON file with titles "First\rpart" and "First\\rpart" using those JSON spellings. Run DUE_TIMES=off node bin/tickets.js --data FILE list --raw in both releases. Both exited 0. Splitting stdout at LF and then TAB gave distinct fourth columns in 1.4.0 and "First\\rpart" for both records in 1.5.2 when represented as JSON.
## Decisions made for the requester
- Configure whole response hours per priority with the four RESPONSE_HOURS_* environment variables, including zero as immediate. | Read the schedule from a configuration file or support fractional hours.
- Prepare the version-1 file with the separate npm run prepare:due-times command while its writer is stopped. | Backfill implicitly on a dark service startup before a separate activation.
- Store each deadline in the existing version-1 ticket record. | Store deadlines in a separate file keyed by ticket ID.
- Recover promises after rollback writes from a separate pre-rollback snapshot passed to preparation. | Preserve promises in a separate live store that the old release never rewrites.
- Expose due in enabled CLI show and retain the existing table and raw column layout. | Add a due column to the human-readable list table.
- Interpret enabled overdue=false as an ordinary listing, validate other values with HTTP 400, and use the first repeated value. | Treat every value except true as an ignored parameter.
