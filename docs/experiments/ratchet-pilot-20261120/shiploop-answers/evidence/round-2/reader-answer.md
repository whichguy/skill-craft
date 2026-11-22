# Reader answers, round 2

## e1
- Q1a: no. "Start the new release with the flag off; startup writes any missing deadlines before listening."
- Q1b: not said. Nothing in the Decided part mentions refusing or failing to start.
- Q2a: no. "start the new release with the flag off to atomically save due for missing tickets before serving"
- Q2b: not said. No sentence says startup refuses or fails over missing due times.
- Q3: partly. Covered: "startup also completes this save before enabled service readiness", "Use each record's creation timestamp and stored priority". Missing: no statement that a start never refuses because due times are missing; the text is framed around a flag-off start.
- Q4: evidence lines only. A line was added: "TC-3 in test/due-times.test.js checks a failed migration leaves the previous file byte-for-byte intact. The exact-release TC-4 run verifies the old reader on candidate-written data. (W1/S1)"

## e2
- Q1a: no. "Start the new release while disabled and verify the startup backfill before enabling it."
- Q1b: not said.
- Q2a: no. "Startup backfills only missing deadlines from the stored priority and creation, before serving."
- Q2b: not said. The only startup-failure sentence is "A failed migration prevents startup." That is about a failed migration, not missing due times.
- Q3: partly. Covered: backfill of missing deadlines from priority and creation, before serving, in an atomic save. Missing: it never says an enabled start does this, and it does not say a start never refuses over missing due times. The default rollout is "starts the new version with exposure off, verifies the file and restarts enabled", and "A failed migration prevents startup" is stated.
- Q4: nothing. The two texts are the same.

## e3
- Q1a: yes. "Stop the writer, run the offline backfill, then enable the flag."
- Q1b: not said.
- Q2a: yes. "An offline command fills missing due fields from each stored ticket's creation time and priority"
- Q2b: yes. "Enabled startup refuses incomplete persisted data."
- Q3: no. It is contradicted: an offline command is required, and "Enabled startup refuses incomplete persisted data" and "refuse early enablement" are the opposite of what was asked.
- Q4: nothing. The two texts are the same.

## e4
- Q1a: no. "Start the new release with the flag off and let it backfill before it listens."
- Q1b: not said.
- Q2a: no. "Before accepting HTTP traffic, migrated records missing due are assigned from their stored creation and priority and saved atomically, even with the flag off."
- Q2b: not said. "Startup fails if the backfill cannot persist." That is about a failed write, not missing due times.
- Q3: partly. Covered: fill from stored creation and priority, atomic save, before serving, flag off included. Missing: it does not say an enabled start does this or that a start never refuses over missing due times. It adds a failure when the backfill cannot persist, which the answer does not mention.
- Q4: nothing. The two texts are the same.

## e5
- Q1a: no. "Start the new binary with the flag off. Startup backfills before accepting traffic."
- Q1b: not said.
- Q2a: no. "Fill missing deadlines from each row's stored creation time and priority before serving requests."
- Q2b: not said.
- Q3: partly. Covered: fill from creation time and priority, "Save atomically", before serving. Missing: it never mentions DUE_TIMES or the flag being on, and says nothing about never refusing to start.
- Q4: nothing. The two texts are the same.

## e6
- Q1a: no. "Start the new release with the feature off and inspect the resulting file before enabling it."
- Q1b: not said.
- Q2a: no. "The rollout default is startup preparation before the listener opens, including while presentation is disabled."
- Q2b: not said.
- Q3: partly. Covered: "fills missing due timestamps from stored creation time and priority and persists them atomically", before the listener opens, with presentation disabled included. Missing: it does not say an enabled start does this, and it does not say a start never refuses.
- Q4: nothing. The two texts are the same.

## f1
- Q1a: no. "The first start of the new release on the production file fills every missing due and rewrites the file, even with DUE_TIMES off; operators then set DUE_TIMES=on."
- Q1b: not said.
- Q2a: no. "every ticket without a `due` gets created + hours of its own priority; if any was filled the file is saved at once, whatever DUE_TIMES is"
- Q2b: not said. "A file with an invalid `due` (not a time) is refused" concerns an invalid value, not a missing one.
- Q3: partly. Covered: creation time plus the hours of its own priority, saved at once, "whatever DUE_TIMES is" (so on included), save in the service's start. Missing: it does not say the service then serves, and it does not say a start never refuses over missing due times.
- Q4: evidence lines only. A line was added: "Met by src/store.js (fill in the constructor, `TicketStore.open` saves) and src/persistence.js; tests test/due-datafile.test.js. (W1/S1)"

| folder | Q1a | Q1b | Q2a | Q2b | Q3 | Q4 |
|---|---|---|---|---|---|---|
| e1 | no | not said | no | not said | partly | evidence lines only |
| e2 | no | not said | no | not said | partly | nothing |
| e3 | yes | not said | yes | yes | no | nothing |
| e4 | no | not said | no | not said | partly | nothing |
| e5 | no | not said | no | not said | partly | nothing |
| e6 | no | not said | no | not said | partly | nothing |
| f1 | no | not said | no | not said | partly | evidence lines only |
