# Closing look

I read the request, specification, plan, build and test reports, and the API, configuration and operations documentation. The workspace contained no fix or referee reports. All 134 tests from `npm test` and all 301 acceptance checks passed. I also exercised the service and operator tools with temporary version-1 files.

I ran dark startup and preparation, enabled startup and restart with changed hours, all four priorities and the default, a zero-hour deadline, malformed and repeated overdue parameters, and page sizes at and beyond the limits. I edited and resolved a prepared ticket, checked its audit and delivered notifications, ran CLI `show` and raw `list`, and compared their output with the weekly report. The suites also exercised the exact overdue and maximum-date boundaries, configuration limits, and write and rename failures during preparation.

I exported the original 1.4.0 release from Git and started it on the exact file the new service wrote. I paged through all seven tickets, fetched each by ID, changed an existing ticket's priority, created an eighth ticket, and followed the runbook to re-enable due times. Separately, I tested exhaustion of each persisted counter, a forced rename failure during an enabled create and a retry after lifting the fault, preparation under two time zones and a known umask, and the title and requester boundaries on both releases.

The observed `savedAt` refresh follows the snapshot writer convention, and C-78 already protects a no-op retry. C-77 already specifies the failure signal operators need from preparation. The raw title escape probe confirmed that ambiguous title spelling still preserves the positional counting contract in C-255 and C-280.

## Added clauses

- C-281 — product keeps to it: no. Both counter probes returned 201, saved `9007199254740992` in the affected counter, and caused the next startup to exit 2.
- C-282 — product keeps to it: no. The documented roll-forward kept ticket `T-0008` and the older ticket's priority edit. It moved that older ticket's deadline three hours later even though the original was available in the saved pre-rollback copy.
- C-283 — product keeps to it: no. Offline preparation under umask `022` changed the data file from `0600` to `0644`.
- C-284 — product keeps to it: no. The failed create returned 500 and left the file bytes intact. The ticket and its deadline, audit entry and receipt were already visible over HTTP. A successful retry allocated `T-0002` and saved both tickets.
- C-285 — product keeps to it: yes. Preparing the same offset-free creation value produced `12:15Z` under UTC and `19:15Z` under America/Los_Angeles. The runbook directs operators to use the recording time zone.
- C-286 — product keeps to it: yes. Both releases accepted 100 supplementary characters in a title and 32 in a requester, and rejected one more in either field. Single-code-unit characters reached the documented limits of 200 and 64.
- C-287 — product keeps to it: yes. The preparation tests forced a write failure and a rename failure and verified cleanup of the temporary sibling in both cases.
