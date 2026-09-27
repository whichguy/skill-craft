---
bump: minor
---
`improve-complete --action <id>` no longer takes a completion record. Each review pass writes `reviews/review-<n>.md` and the check output `reviews/checks.md`; ShipLoop imports the last two passes (the last one when the first pass changed nothing) and `checks.md`, and writes the summary itself. The model supplies only optional `--notes` (lessons), `--final-result` (when the review changed a decision) and `--no-commit`. `parent-return.md` is the one command. The `--result` flag of `improve-complete` is removed; stopped and reconcile receipts are unchanged.
