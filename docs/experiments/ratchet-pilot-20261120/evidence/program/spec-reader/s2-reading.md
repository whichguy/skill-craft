## Decided beyond the request
- C-45 | Requires a failed save to roll back the running ticket, timestamp, audit and outbox state and allow a clean retry. The existing store mutates those records before saving, and whole-file replacement protects the saved file without rolling back memory. | Return the existing 500 `internal` error and leave the previous file intact while retaining the attempted change in memory, as existing mutations do.
- C-34 | Requires startup to fail with a record-specific diagnostic for a malformed saved assignee. The current loader ignores `assignee`, and its checks for known text fields do not generally enforce API length limits. | Validate names on PUT and load a ticket with a malformed saved assignee as unassigned, preserving the rest of the file.

## Checked against the product
C-1, C-2, C-5, C-6, C-7, C-8, C-9, C-10, C-11, C-12, C-13, C-14, C-16, C-17, C-19, C-20, C-21, C-22, C-23, C-24, C-26, C-27, C-28, C-29, C-30, C-31, C-32, C-33, C-34, C-35, C-36, C-37, C-38, C-39, C-40, C-41, C-42, C-44, C-45
