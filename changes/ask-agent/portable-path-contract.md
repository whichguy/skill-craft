---
bump: patch
---

Share Git's `/` path separator and protected-path set between the task and workspace helpers. Reject unnormalized path segments in workspace relative paths while preserving one trailing directory marker and legal POSIX Git filenames such as `C:notes`. Reject Windows drive-qualified or drive-relative task scopes.
