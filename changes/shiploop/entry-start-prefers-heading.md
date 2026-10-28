---
bump: patch
---
A living file's `R-<n>` or `AD-<n>` entry now starts at the ID's first heading or list item. A summary table row or an
overview sentence that begins with the same ID earlier in the file no longer stands for it. The first start of any form
still counts when the ID has no heading or list-item start.
- Before, "AD-4 and AD-10 appear under Superseded." in an overview shadowed `### AD-4 …`, so a superseded decision read
  as current. A row such as `| R-1 | … |` above `### R-1 …` did the same to the requirement.
- In 1,204 knowledge files from past E2E runs, 27 of 5,369 entries move, each from such a line to its heading. No ID
  appears or disappears, and no retired flag changes.
