## Decided beyond the request
- C-45 | Requires a failed save to roll back the assignment, timestamp, audit entry and outbox notice in memory and keep the failed change out of later saves. The existing store applies all of those changes before saving and has no rollback. | Return the existing 500 error on a write failure, leave the previous complete file on disk and retain the complete in-memory change for a later save.
- C-34 | Requires the whole service to refuse startup on an invalid stored assignee, including one over 64 characters. The request bounds assignment input, and the existing loader ignores unknown fields and does not enforce even the analogous 64-character API limit on stored requester names. | Enforce the name bound on PUT and load a ticket with an unusable stored assignee as unassigned, keeping the rest of the file available.

## Checked against the product
C-1, C-2, C-5, C-6, C-7, C-8, C-10, C-11, C-12, C-13, C-14, C-16, C-17, C-19, C-20, C-21, C-22, C-23, C-26, C-27, C-28, C-29, C-30, C-31, C-32, C-33, C-34, C-38, C-39, C-40, C-41, C-42, C-45
