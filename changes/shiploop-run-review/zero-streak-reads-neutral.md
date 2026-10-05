---
bump: patch
---
The Backchain pass strip on the Run Review page no longer says a one-pass loop "closes at 2": when a loop document's `trivialRequired` is 0 it draws no streak axis or target and says "no trivial-streak requirement on this loop"; a document with no `trivialRequired` (an older export) is drawn as before, with the target at 2. The loop card already lists the new `Backchain passes option` and `Candidate match` facts. The page needs one republish to show this.
