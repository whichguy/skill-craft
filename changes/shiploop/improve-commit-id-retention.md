---
bump: patch
---
Prevent `improve-commit` (and `improve-pass`) from committing `docs/shiploop/` edits that drop earlier `R-<n>` requirement or `AD-<n>` architecture decision IDs into `HEAD` before `improve_import` inspects them.
