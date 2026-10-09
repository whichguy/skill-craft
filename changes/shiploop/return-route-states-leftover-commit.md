---
bump: patch
---
The return-route sentence that every worktree packet prints now says, right after its first sentence, that plan-return commits files left uncommitted, so a run commits nothing by hand for the return except a file plan-return reports as not committed (a credential-like one). The old wording could be read as needing a hand commit before the return.
