# Reader answers, round 3

## m1

Q1a: no. "The new release writes due into the data file at its first start even with the flag off"
Q1b: not said. The Decided part does not mention refusing or failing to start.
Q2: The note asks that the service does not fill in due times at start; an operator runs a separate command and the service refuses to start with DUE_TIMES on until then. "I want that step explicit: an operator stops the service and runs a separate command" and "it refuses to start and names that command."
Q3a: yes. "Backfill is an explicit operator step: the operator stops the service and runs a separate command (`node bin/backfill-due.js --data FILE`, or DATA_FILE)" (current text; the start-time backfill is marked "Superseded 2026-11-22").
Q3b: yes. "Started with DUE_TIMES=on while any ticket has no `due`, it refuses to start (exit 2, message names the command and the count)."
Q4: fully. The note's three points are all stated: no fill at start ("The service does not backfill when it starts."), the operator's separate command that fills from creation time and priority and saves the file ("gives every ticket without `due` one, from that ticket's own creation time and priority ... and saves the file"), and refusal with DUE_TIMES=on naming the command ("it refuses to start (exit 2, message names the command and the count)").
Q5: The behaviour changed from backfilling at service start to an explicit operator command plus a refusal to start with DUE_TIMES=on while tickets lack due, and the text says why: "REVISED 2026-11-22 by owner note N1 (run owner, 21:47Z)"; the old text is kept marked "Superseded", and two "Implemented" lines were added.

## n4

Q1a: yes. "Run the offline migration before enabling the flag."
Q1b: yes. "Startup fails early if the file still has missing deadlines."
Q2: The note asks that the service fills the due times in by itself when it starts with DUE_TIMES on and never refuses. "it gives every ticket that has no due time one ... saves the file, and then serves. It never refuses to start because due times are missing."
Q3a: yes (a separate pre-activation step, though no operator or command is named). "Backfill stored tickets before activating" and "Verify the original 1.4.0 reader can start on the migrated file". Judgment call: the text calls it a standalone "operation" done "before activating" but never says "operator" or "command".
Q3b: yes. "Activation on an incomplete persisted file fails before listening."
Q4: no. It states the opposite: backfill is a separate step before activating ("Backfill stored tickets before activating") and an incomplete file makes activation fail ("fails before listening"), where the note asks for automatic fill at start and no refusal.
Q5: nothing (the two texts are the same apart from the first line of before.md).

## n5

Q1a: yes. "Stop the writer and run the backfill command before starting with DUE_TIMES=on."
Q1b: yes. "Startup rejects an unprepared populated file."
Q2: The note asks that the service fills the due times in by itself when it starts with DUE_TIMES on and never refuses. "it gives every ticket that has no due time one ... saves the file, and then serves. It never refuses to start because due times are missing."
Q3a: yes. "an operator stops the file owner and runs the backfill before enabling."
Q3b: yes. "Enabled startup with any missing due rejects a populated unprepared file."
Q4: no. It states the opposite: an operator runs the backfill before enabling ("an operator stops the file owner and runs the backfill before enabling") and enabled startup rejects a populated unprepared file, where the note asks for automatic fill at start and no refusal.
Q5: nothing (the two texts are the same apart from the first line of before.md).

| folder | Q1a | Q1b | Q2 in three words | Q3a | Q3b | Q4 | Q5 in three words |
|---|---|---|---|---|---|---|---|
| m1 | no | not said | operator command, refuse | yes | yes | fully | start backfill replaced (owner note) |
| n4 | yes | yes | auto-fill, never refuse | yes | yes | no | nothing |
| n5 | yes | yes | auto-fill, never refuse | yes | yes | no | nothing |
