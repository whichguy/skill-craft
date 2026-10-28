---
bump: patch
---
A step's spec write-back can no longer add a requirement. A marked line counted as inside an R-n entry even when the
step's own edit had added that entry, so a step could add `R-2` and pass the gate. Now only an entry the committed
spec holds takes a step's lines. A new requirement is refused as "outside an R-n entry the committed spec holds", and
the refusal names send-back.
