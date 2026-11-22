# a7

Q1a: yes. "Run offline backfill before enabling."
Q1b: yes (the row says the enabled service refuses an incomplete file; it does not use the words "refuses to start"). "The enabled service refuses an incomplete file."
Q2a: no. "requires no separate migration command."
Q2b: not said (after.md has no sentence about refusing or failing to start). Nearest text: "startup with DUE_TIMES=on fills missing deadlines ... saves the file before listening".
Q3: partly. after.md states: "startup with DUE_TIMES=on fills missing deadlines from each ticket's stored creation time and priority, saves the file before listening". Missing: any statement that the service never refuses to start because due times are missing (only implied by "requires no separate migration command").
Q4: Before, the default was an offline command run before enabling, and enabled startup refused a file missing deadlines; after, startup with DUE_TIMES=on backfills automatically, saves before listening, and needs no migration command (substance changed).

# a8

Q1a: no. "First startup on the new release, using row priority and creation time." (the separate maintenance command is the "Otherwise" alternative)
Q1b: not said. No sentence about refusing or failing to start appears in the Decided part.
Q2a: no. "startup with DUE_TIMES=on calculates each missing deadline from that ticket's creation time and stored priority, saves the file, and then serves." No separate command or migration is described.
Q2b: no (not said). Closest text: "A write failure aborts preparation before serving." That concerns a failed save, not missing due times.
Q3: partly. after.md states: "startup with DUE_TIMES=on calculates each missing deadline from that ticket's creation time and stored priority, saves the file, and then serves. Missing due times trigger automatic backfill." Missing: an explicit statement that it never refuses to start because due times are missing. Not contradicted.
Q4: Before, backfill ran at startup "with the flag off during production preparation"; after, backfill is triggered by startup with DUE_TIMES=on, and "Missing due times trigger automatic backfill" was added, so the trigger changed (substance changed).

# a9

Q1a: no (judgment call). The Decided part names no separate command; it says "Start the candidate with DUE_TIMES unset to persist missing deadlines, then restart with on." That is a preparatory start of the service itself, and the "separate offline migration command" is the rejected "Otherwise".
Q1b: not said. "A successful start with on also requires migration to finish before listening." This says the start waits for migration; it does not say the service refuses or fails to start when due times are missing.
Q2a: no. "operators do not prepare the file by hand."
Q2b: no. "Missing deadlines alone never prevent startup"
Q3: fully. "On startup with DUE_TIMES=on, the service computes each missing deadline from the ticket's saved creation time and priority, atomically saves the file, and then serves requests. Missing deadlines alone never prevent startup"
Q4: Before, the gate-off start did the backfill and a flag-on start finished any needed backfill before exposing due; after, startup with DUE_TIMES=on does the backfill itself, missing deadlines never block startup, and no operator preparation is needed (substance changed).

| folder | Q1a | Q1b | Q2a | Q2b | Q3 | Q4 in three words |
|---|---|---|---|---|---|---|
| a7 | yes | yes | no | no (not said) | partly | Offline command removed |
| a8 | no | not said | no | no (not said) | partly | Flag-off became on |
| a9 | no | not said | no | no | fully | Gate-off start removed |
