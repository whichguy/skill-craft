---
bump: patch
---
Refuse `classification: trivial` in `improve-pass` when that specific pass edited any code or test (`behavioural`) file, ensuring a confirmation pass verifies code/test edits while keeping doc-only and confirmation passes eligible for `trivial`.
