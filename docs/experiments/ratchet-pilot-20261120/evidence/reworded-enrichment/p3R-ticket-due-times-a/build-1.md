## Done

- C-1, C-2. Verified `npm start` and health on OS-assigned ports and ran the suite with Node.js v26.12.1 and no npm dependencies.
- C-3, C-6, C-7. Added the exact `DUE_TIMES=on` switch and independent response-hour settings. Compared disabled HTTP workflows against stock 1.4.0 with the switch unset, empty and `ON`, including on prepared data. An invalid hours setting used on startup exits and names the setting.
- C-4, C-5, C-8, C-9. Assigned UTC deadlines from creation time and priority, including the default `normal` priority. All enabled ticket responses expose `due` and mutation bodies reject it.
- C-10, C-11, C-19, C-20. Deadlines stay fixed through schedule changes, edits, lifecycle moves and restarts. Enabled creation works in memory and saves a file-backed ticket, audit entry and notification before returning 201.
- C-12, C-13, C-14, C-15, C-16. Added strict overdue selection for active tickets, composed with the existing filters and cursor validation. Verified the deadline boundary, numeric ID order, empty and exactly full last pages, and resuming after a ticket stops matching.
- C-17, C-18, C-21, C-22, C-23, C-24. Enabled startup fills missing deadlines for all statuses before serving. Preparation keeps existing deadlines, ticket data and numbering. Tested interruption before replacement, a failed replacement, a failed directory sync after replacement, and retry on the same file. Disabled ticket, worker and shutdown saves retain assigned deadlines.
- C-25, C-26, C-27. Verified that audit history, no-op updates, existing notifications and pending-key deduplication behave as before. Preparing a file and passing a deadline produce no notification.
- C-28, C-29. Started stock 1.4.0 from revision `ada051d8b4eca7b4b67a5b904f50fc7dd5612ff6` on unchanged copies of new-release files from disabled rollout, after preparation, and after enabled creation. Health, cursor walks and direct reads succeeded for every saved ticket in all three copies.
- C-30, C-31, C-32. Verified the CLI table, ticket details and history, four raw columns and weekly JSON counts on both legacy and prepared files. The reads left the file byte-for-byte intact.
- C-33, C-34. `npm test` passed all 133 reported entries. The 117 original entries remain intact. Added 15 `node:test` cases and a frozen 1.4.0 reader fixture.
- Updated the README, API and operations documents, changelog and decision index. Recorded the version 1 format decision in ADR 9 and set the package version to 1.5.0.

## Not done

none

## Discoveries

- C-6 accepts trimmed whole response hours from 1 through 876,000 for this build | Observable: enabled startup accepts the bounds and rejects zero, fractions and values above the upper bound | Why: the existing settings parser handles bounded integers and the range covers the response schedules.
- C-13 uses the first `overdue` value and activates the filter only for `true` | Observable: `overdue=false&overdue=true` gives an ordinary page | Why: existing query parameters use the first value.
- C-14 retains the existing OR between `status` and `priority`, with overdue eligibility required separately | Observable: `overdue=true&status=open&priority=urgent` can include an overdue `in_progress` urgent ticket | Why: 1.4.0 implements OR where the old API guide described an intersection. The guide now describes the implemented behavior.
- C-18 prepares at enabled startup with one writer and requires file and directory sync before binding for a nonempty file | Observable: a failed sync prevents startup. If it fails after replacement, retry syncs the complete prepared file without rewriting it | Why: a process can be interrupted between replacement and directory sync.
- C-18 refuses a preparation with an unrepresentable deadline and identifies the file, ticket and hours setting | Observable: an existing creation instant at the upper Date boundary causes `cannot start` and leaves the active file intact | Why: a positive response duration can overflow a valid legacy creation instant.
- C-21 assigns deadlines missing after a 1.4.0 rewrite using the next enabled startup’s schedule and the then-recorded priorities | Observable: a stock 1.4.0 clean stop strips `due`, even after a read-only session | Why: the legacy writer projects only its recognized fields.
- C-23 keeps `updated` during preparation | Observable: the before and after ticket timestamps match | Why: deadline preparation does not represent an agent edit.
- C-25 keeps the creation audit fields and adds no preparation entries | Observable: `due` is absent from creation audit changes and existing history is byte-for-byte equivalent as JSON data | Why: the derived assignment uses no ordinary ticket mutation.
- C-30 keeps the existing human-readable CLI columns and `show` fields | Observable: the before and after CLI outputs match | Why: deadline display is on the HTTP API.
