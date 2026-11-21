## Failing now
none (all 32 items, C-1 to C-26 and U-1 to U-6, pass on the product as it stands; each command runs in under 10 s)

## Discoveries
- Choices made, none a spec change: acceptance tests start `node src/server.js` as a process on a free port and use HTTP, the command line and the data file only; the C-10 delivery check reads `NOTIFY_FILE` with the worker on at 50 ms. C-21 compares `test/` against the pre-change commit 78ae658 and runs those files. C-22 checks that a new test file mentions `assignee` and that `npm test` runs more tests than the old files alone. Acceptance files are not named `*.test.js`, so `npm test` does not pick them up.
- The CLI tests locate the ASSIGNEE column from the header's offset and do not assume a position or placeholder text (C-19 Open); `--raw` tests read fields 1-4 only (C-20 Open).
- Tests avoid whitespace-only and control-character names, the order of 400 vs 409 checks, the audit action name, notification wording and duplicate-pending behaviour (the Open points).
