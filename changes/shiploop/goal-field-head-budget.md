---
bump: patch
---
The status line's trailing `Goal:` field is documented with its measured cost: it rides on every non-milestone packet and
grew each journalled printed head by ` · Goal: ` plus the goal's length (99 characters on the reference case). `test-spec`
at the short run-directory fixture is now 45 characters over the print limit, so it prints a head instead of whole; its
head still carries the stage duties, result template and references, which a test now asserts directly.
