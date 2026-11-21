## Fixed

- C-64 and U-10. An outbox key tied to the ticket and recipient suppressed later real assignments to a former assignee while an earlier notice was pending. The audit sequence now gives each real assignment its own notification key.
- C-87, C-192, U-5 and U-8. Query values bypassed assignment name parsing, and assignment accepted unpaired UTF-16 surrogates that change when encoded. The API shares name validation between PUT and non-empty assignee filters and preserves valid surrogate pairs.
- C-91, C-99, C-101, C-113 and U-9. The listing matched any supplied filter, so ineligible tickets reached pagination and CLI output. The shared predicate now requires every supplied filter to match before paging.
- C-103, C-114 and U-12. The table's dash for an unassigned ticket collided with a valid assignee name, and the single-ticket details omitted current ownership. The table and details show the assignee and use a blank value for unassigned tickets.
- C-123, C-187, C-191 and U-17. A failed save left the live ticket, audit and outbox mutated, consumed identifiers and turned a retry into a no-op. The store restores the pre-change state when saving fails.
- C-133. The loader accepted stored names with excess length, controls, surrounding whitespace or unpaired surrogates. It now requires canonical names and reports the affected ticket field.
- C-136 and C-137. The operations reference lacked rollback guidance for ownership and pending notices. It now covers backing up the data file, the old writer dropping assignees, draining the queue and pausing the old worker.
- C-189. The API reference omitted the assignee field, the assignment endpoint and the assignee filter.
- C-190. The CLI reference omitted the fifth raw column and its empty value for unassigned tickets.
- `npm test`. The assignment suite's intersection assertion failed because the list used OR. The predicate fix makes the suite pass. Added separate `node:test` coverage using the isolated service helper for repeat and former-assignee notifications, validation, active-state restrictions, audit, filter paging, failed-save retry, restart and CLI output. The tests already present in this checkout are unchanged.

## Disputed

- C-135 | the test expects: Git can archive revision `22f8405` to start the previous release | the clause says: the previous release can open a version 1 file saved by this release | the revision is absent, so Git fails before the compatibility assertion.
- C-184 | the test expects: Git can enumerate the original tests at revision `22f8405` | the clause says: the existing tests pass as written | the revision is absent and the frozen check stops before running the suite. All files present under `test/` at the local base are unchanged and the suite passes.
- C-185 | the test expects: Git can enumerate tests at revision `22f8405` to identify new files | the clause says: new assignment coverage is discovered by `npm test` | the revision is absent, so discovery fails before inspecting or executing the new tests.
- C-186 | the test expects: Git can enumerate tests at revision `22f8405` before inspecting the new tests' HTTP setup | the clause says: assignment HTTP tests use the existing isolated setup | the revision is absent, and the new tests use `withService` with port 0 and the worker off.
- U-15 | the test expects: Git can archive revision `22f8405` to run the downgrade | the clause says: the operator can run the previous executable on the saved file | the revision is absent, so the downgrade scenario cannot start the previous executable.
- U-16 | the test expects: Git can read the test tree at revision `22f8405` before running `npm test` | the clause says: the maintainer can run the existing and new tests together | the revision is absent and the frozen check fails before invoking the package test command. The command passes independently.

## Discoveries

- An assignment's audit sequence can identify a distinct notice and remain stable across delivery retries | Observable: Assign to Dana, then Sam, then Dana with the worker off and inspect the two Dana notifications and their keys in the outbox | Why: The old ticket-and-recipient key collided even though the two Dana assignments were separated by a real change.
- A display placeholder such as a dash can be a valid agent name | Observable: Compare CLI table rows for a ticket assigned to `-` and an unassigned ticket | Why: The previous placeholder rendered both rows with the same assignee cell.
- The frozen Git-based checks require a previous-release revision missing from this checkout | Observable: `git cat-file -t 22f8405` fails, and `git log --all --oneline` shows the base at `137198a` and the frozen suite at `21279ea` | Why: Rollback and regression checks abort on Git errors before exercising the corresponding behavior.
