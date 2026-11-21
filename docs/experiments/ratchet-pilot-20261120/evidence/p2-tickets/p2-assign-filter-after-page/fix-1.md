## Fixed

- C-64 | The pending outbox key used the recipient, so a return to a former assignee reused their first notice. Each real assignment now uses the sequence of its own audit entry.
- C-87 | The list query used assignee text verbatim. A non-empty query value now uses the same parser as PUT, including trimming and validation.
- C-97 | The store sliced the first 20 tickets before checking assignee. The default page now holds up to 20 matches.
- C-99 | The store skipped matching tickets beyond the unfiltered page. It now applies all filters to the full set before paging.
- C-101 | The cursor was based on rows the assignee filter might remove. It now points to the last matching row served and only exists when another match remains.
- C-103 | A valid agent called `-` looked identical to an unassigned ticket. The table now leaves the assignee cell blank for unassigned tickets.
- C-114 | The CLI's `show` details lacked the current assignee. They now include the assignee field even when blank.
- C-123 | A save error left the mutated ticket, audit entry and outbox event in memory. The store restores the preceding snapshot before returning the error.
- C-133 | The loader accepted any non-empty assignee string. It now checks stored names against the assignment rules and requires the stored value to be trimmed.
- C-136 | The operations guide lacked rollback instructions for assignees. It now explains copying the file before rollback and how an older writer drops assignees.
- C-137 | The operations guide lacked rollback instructions for pending notices. It now documents draining them with the compatible worker or pausing the old worker.
- C-185 | The new tests lacked persistence and CLI coverage. They now verify restart, persisted audit and notices, CLI output and read-only behavior. They also cover failed saves, a returning assignee and filtered pagination.
- C-187 | A failed save left the assignee set in memory, so the retry looked like a no-op. Restoring the previous ticket lets an identical retry perform the change.
- C-189 | The API reference omitted assignment. It now describes the ticket field, endpoint, request and response rules, and list filter.
- C-190 | The CLI documentation listed only four raw columns. It now documents assignee as the fifth column and an empty value for unassigned tickets.
- C-191 | A failed save consumed live audit and notification identifiers. The rollback restores the preceding audit length and next outbox ID.
- C-192 | PUT accepted unpaired surrogates, which cannot survive UTF-8 output. The assignment parser now rejects them while accepting valid pairs.
- U-5 | The invalid-name cases could slip through because PUT accepted an unpaired surrogate. PUT now refuses it with the existing invalid response.
- U-8 | An assignee search could accept an invalid name or return a short page after filtering. It now validates decoded names and fills pages from the matches.
- U-9 | Listing by status, priority and assignee could produce incomplete pages and cursors based on unrelated tickets. The combined filters now determine the entries and cursors.
- U-10 | A second assignment to Dana with her first notice pending was deduplicated. Each real change to a name queues its own notice with the original recipient.
- U-12 | The full-ticket CLI view omitted current ownership. The details now show it alongside the table and raw listing.
- U-17 | A failed assignment could be visible despite the error, and retry could skip saving. The store now rolls back the failed change and records it normally when retried.

## Disputed

- C-74 | the test expects: its initial filesystem probe error is at most 500 characters with the prescribed temporary path | the clause says: the outbox stores the first 500 characters of a failed delivery error | why they differ: the absolute temporary path produces a 503-character probe error, so the fixture fails before starting the service. The unchanged case passes with `TMPDIR=../tmp` from the workspace, which resolves to the same directory.

## Discoveries

- Temporary path length can prevent C-74 from reaching the worker | Observable: the fixture fails at `extra >= 0` with the inherited absolute `TMPDIR` and passes with `TMPDIR=../tmp` from the workspace | Why: Node includes the sink path in its error message, and the fixture must construct errors of exactly 500 and 501 characters.
- A display marker can also be a valid agent name | Observable: an agent called `-` appears verbatim in the assignee column while an unassigned ticket has a blank cell | Why: the original table used `-` for both values.
- The global audit sequence already identifies each real assignment across restarts | Observable: assignment outbox keys include the matching audit sequence and remain the same on restart or delivery retry | Why: the store can distinguish repeated real assignments without adding a counter or changing the data-file version.
