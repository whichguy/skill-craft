---
bump: minor
---
A loop whose receipt carries `progress.last_pass_changed_tree` (the unchanged-content review gate, which counts nothing) now exports `trivialRequired: 0` and a `Review gate` fact saying whether the last pass changed the content, in place of a streak the receipt no longer has.
