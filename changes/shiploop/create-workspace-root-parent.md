---
bump: patch
---

`workspace start` creates one missing parent level of the workspace root (the
usual `<beside the repo>/.shiploop-runs/<name>` layout) instead of refusing it;
a deeper missing tree is still refused.
