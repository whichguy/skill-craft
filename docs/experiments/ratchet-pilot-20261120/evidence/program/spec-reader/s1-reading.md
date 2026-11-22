## Decided beyond the request
- C-45 | Requires a failed save to roll back the live assignee, timestamp, audit entry and notice, and prevents a later save from persisting the change. `src/store.js` applies live changes before saving and has no rollback when saving throws. | Return the existing storage error and keep the complete change in memory. The old snapshot stays on disk until another save succeeds, and a restart before then loads that snapshot.
- C-34 | Requires startup to fail with a record-specific diagnostic for numeric, empty or overlength assignees in an otherwise usable file. `src/persistence.js` drops unknown fields and does not enforce the API's 64-character requester limit on saved records. | Load the file, treat an invalid stored assignee as unassigned, and enforce the name bound on assignment requests.

## Checked against the product
C-1, C-2, C-5, C-6, C-7, C-8, C-9, C-10, C-11, C-12, C-13, C-14, C-16, C-17, C-19, C-20, C-21, C-22, C-23, C-24, C-26, C-27, C-28, C-29, C-30, C-31, C-32, C-33, C-34, C-35, C-38, C-39, C-40, C-41, C-42, C-44, C-45
