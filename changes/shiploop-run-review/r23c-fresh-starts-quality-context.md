---
bump: patch
---
The Run Review export and page now show three more things a run recorded. Fresh starts: each time the model lost its context (a
compaction or a new host session), the calls and seconds it took to re-ground, with the failure and rewrite counts shown as lower
bounds, and a marker on the visit that followed; a run that could not record them says so instead of reading "none". Quality: the
mutation ratio with its operator, the survivors, the held-out checks and the model's writes to its own memory. A visit's context
now follows the harness's stage rows, not the host, so a Grok run shows its calls and peak tokens.
