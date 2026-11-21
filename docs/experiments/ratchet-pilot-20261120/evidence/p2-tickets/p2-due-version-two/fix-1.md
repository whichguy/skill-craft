# Fix 1

## Fixed

The gate passed 237 of 253 acceptance checks. `npm test` passed all 122 tests, and the syntax and whitespace checks passed. The remaining acceptance failures are recorded below. The loop exit is unsatisfied and continuation is blocked.

- C-1, C-6, C-7, C-9, C-10, C-11, U-6, U-9. The service read a single schedule variable in place of the four specified overrides. It now validates each override at startup and calculates elapsed hours from the ticket's creation instant with millisecond precision. A schedule change applies to future assignments.
- C-34, U-4. Overdue pages inherited the ordinary list's either-filter rule. They now require every supplied status and priority filter before pagination.
- C-42, C-43, C-44, C-45, C-46, C-47, C-48, C-60, C-61, C-65, U-8. Startup previously filled deadlines in memory. Disabled startup now validates the file, fills only missing deadlines from saved creation times and priorities, and makes one atomic save before listening. Enabled startup rejects incomplete files. Preparation reports calculation and save failures with file and record details where applicable.
- C-52, C-237. Failed saves previously left a created ticket, audit entry, notification and advanced counters in memory. Failed ticket writes now restore their prior state and sequence positions.
- C-63, C-64. The reader previously accepted any parseable deadline. It now requires a canonical UTC timestamp later than the saved creation instant.
- C-69, C-190. The writer previously emitted version 2 and the reader accepted it. Both now use version 1, with `due` as an optional field on ticket records.
- C-71, C-72, C-73. The operations runbook now covers production preparation, verification, activation, rollback and restoring deadlines by ticket ID into the latest legacy save.
- C-74, C-75, C-76. The API and configuration docs now describe `due`, overdue eligibility and pagination, and the settings for the response-hour schedule.
- C-214, C-216, U-12. The CLI now shows stored deadlines in enabled human-readable output. It had no due column or detail field and assigned missing deadlines when constructing its read-only store.
- C-234, C-235, C-236. Decision 9 records the storage and rollout rules. Version 1.5.0 and its changelog record the release.
- C-238. Ticket and outbox allocation now check for a representable successor before committing. The local regression covers both counters in both visibility modes and verifies that edits and deduplicated resolutions still save at exhaustion. The frozen rollback comparison remains blocked below.
- C-231, C-232, C-233, U-15, and `npm test`. Added five `node:test` regressions in `test/due.test.js`. `npm test` discovers them with all existing tests. The version 1 correction fixes the existing persistence assertions, and the original test files in this checkout match the incoming Git tree byte for byte. The frozen historical comparisons remain blocked below.

## Disputed

- C-22 | the test expects: a local `22f8405` archive for disabled HTTP comparison | the clause says: disabled HTTP responses match 1.4.0 | why they differ: the archive object is absent and setup fails before comparing responses.
- C-67 | the test expects: to archive and start local `22f8405` | the clause says: the new file starts on unmodified 1.4.0 | why they differ: the archive object is absent and 1.4.0 cannot be launched by this check.
- C-68 | the test expects: to list tickets on the release archived from `22f8405` | the clause says: 1.4.0 shows every ticket after rollback | why they differ: the archive object is absent and setup fails before reading tickets.
- C-70 | the test expects: to create a ticket on the release archived from `22f8405` | the clause says: rollback retains the next ticket number | why they differ: the archive object is absent and setup fails before the legacy create.
- C-124 | the test expects: to obtain a cursor from the release archived from `22f8405` | the clause says: existing cursors remain usable | why they differ: the archive object is absent and setup fails before obtaining a cursor.
- C-138 | the test expects: to create legacy audit history using the release archived from `22f8405` | the clause says: existing audit entries remain append-only | why they differ: the archive object is absent and setup fails before producing the legacy history.
- C-217 | the test expects: to obtain CLI output from the release archived from `22f8405` | the clause says: disabled CLI output keeps the 1.4.0 format | why they differ: the archive object is absent and setup fails before comparing output.
- C-229 | the test expects: to obtain a weekly report from the release archived from `22f8405` | the clause says: the weekly report retains its human-readable format | why they differ: the archive object is absent and setup fails before comparing reports.
- C-231 | the test expects: to enumerate original files using `git ls-tree 22f8405` | the clause says: new due-time tests use `node:test` under `test/` | why they differ: the missing object prevents test discovery through the frozen comparison helper.
- C-232 | the test expects: to discover original test names using an archive of `22f8405` | the clause says: `npm test` discovers both old and new tests | why they differ: the local suite runs, but the missing object prevents the comparison.
- C-233 | the test expects: to compare original test files against `22f8405` | the clause says: existing tests pass without edits | why they differ: the missing object prevents the historical source comparison even though the incoming tests are unchanged and pass locally.
- C-238 | the test expects: to reopen an exhausted-counter file on the release archived from `22f8405` | the clause says: exhausted persistent sequences stay usable and writes without allocation can succeed | why they differ: the frozen test reaches the archive step after the new release's checks in the first scenario, then fails on the missing object. The local regression covers both counters and visibility modes.
- U-7 | the test expects: to start the original file owner from a `22f8405` archive | the use case says: operators prepare a production file before enabling visibility | why they differ: the archive object is absent and setup fails before the rollout flow.
- U-11 | the test expects: to run rollback using the archive of `22f8405` | the use case says: operators can roll back to unmodified 1.4.0 and recover deadlines when returning | why they differ: the archive object is absent and setup cannot launch the rollback release.
- U-14 | the test expects: to create pre-upgrade activity on the release archived from `22f8405` | the use case says: rollout preserves audit and notification activity | why they differ: the archive object is absent and setup fails before recording pre-upgrade activity.
- U-15 | the test expects: to archive `22f8405` and compare its tests and output | the use case says: `npm test` exercises the unchanged original and new tests | why they differ: the archive object is absent and setup fails before running the baseline suite.

## Discoveries

- The frozen suite's historical comparison requires a Git object missing from this checkout | Observable: `git cat-file -t 22f8405` fails, and `git log --all --oneline` lists only `4a0d54f` and `14feaa0` | Why: the suite archives a hard-coded commit or uses it to enumerate original tests. The available `14feaa0` commit labels its package 1.4.0 but already contains the incomplete due-time implementation.
- The elapsed duration between two valid Node dates can exceed the safe integer range even though each endpoint fits | Observable: applying 4,800,000,000 hours to the earliest supported timestamp reaches the latest supported timestamp exactly | Why: adding the interval with `BigInt` preserves millisecond precision across the full supported range.
