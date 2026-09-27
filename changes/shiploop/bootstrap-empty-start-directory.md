---
bump: minor
---

`workspace start` on an empty, non-Git directory initializes it as a Git
repository on `main` with one empty baseline commit (the user's identity when
configured, otherwise the workspace identity). The model no longer writes Git
setup commands for a new product, which on Grok's auto permission mode were
cancelled and ended the session three times in one run.
