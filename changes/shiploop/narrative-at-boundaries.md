---
bump: patch
---
The run narrative is shown at the boundaries a person looks for, not at every stage. The packet prints the full
narrative when the last accepted stage is `prepare` (preparation complete), a work item's `carry-forward` (the queue
moved), `product-acceptance`, `release` or `handoff`, and at the start of a run; every other stage carries the one-line
status instead, which now ends with the run's own goal (`· Goal: <goal>`) so a packet between boundaries still names
what the run is for. Measured over 102 saved runs, the earlier rule asked for the narrative at 20 of 23 stages and the
model showed it at 61% of 2,111 emissions (median 70% a run, 5 runs at zero); a one-item run now asks 6 times instead
of 21 (a three-item run 8 instead of 29): 71-73% fewer across one to five items.

The card now says to relay a packet's progress block and never compose one: it previously said both "tell the user at
most one line per completed step" and "briefly report the milestone", which the status-display reference contradicts
("the model writes neither"). Compose-instead-of-relay is the behaviour that produced 61% narrative compliance.
