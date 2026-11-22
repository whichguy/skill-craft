Verdict: accept
## Findings
none
## Decisions made for the requester
- Set the schedule with four startup environment variables. Unset or blank values use the defaults, and enabled settings accept positive whole hours up to JavaScript's maximum safe integer. | Use a single schedule setting, reload it while the service runs, or support zero and fractional hours.
- Return HTTP 500 without creating a ticket if its deadline would exceed Node.js's timestamp range. During preparation, stop startup with the file and ticket identified. | Clamp the deadline to the nearest representable timestamp.
- Prepare missing deadlines during enabled startup and save them before listening. | Require operators to prepare and verify the file with a separate command before enabling the service.
- Allow enabled operation without a data file for local use. | Require persistence whenever due times are enabled.
- Preserve assigned deadlines while the flag is off and defer assignment for tickets created in that mode until the next enabled startup, using their priority and the schedule at preparation. | Assign and save deadlines at creation even while the flag hides them.
- When enabled, accept a single exact `overdue=true` or `overdue=false` and reject other supplied forms with HTTP 400. | Ignore malformed values or use the first of repeated values.
- Apply overdue eligibility to tickets matching either of the supplied status and priority filters, preserving the ordinary listing's union semantics. | Require both filters to match on overdue requests.
- Keep deadline assignment out of audit entries and emit no notifications during preparation. | Record deadline assignment in creation or backfill audit entries.
- Preserve malformed saved deadlines while off and refuse enabled startup until the bad value is repaired. | Treat a malformed deadline as missing and assign a replacement automatically.
- Store deadlines as an optional field in the existing version-1 file. If 1.4.0 rewrites the file and drops the fields, prepare them again on re-upgrade. | Keep a separate deadline store to preserve assignments across 1.4.0 writes.
- Keep human-readable CLI list and show output as before, regardless of the HTTP flag. | Display saved deadlines in the human-readable CLI output.
