# Reader answers, round 1

## a2
- Q1a: no. "The new service persists missing deadlines on startup while the feature can stay off." (the alternative "Run a standalone offline migration command" is the one not chosen)
- Q1b: not said. Decided part only says it "persists missing deadlines on startup".
- Q2a: no. "No manual preparation is required."
- Q2b: not said. after.md never mentions refusing or failing to start.
- Q3: partly. Present: "a DUE_TIMES=on startup assigns every missing due from the ticket's stored creation time and priority, saves the file, and then serves." Missing: nothing says it never refuses or fails to start because due times are missing.
- Q4: Substance changed: the trigger moved from a "dark start" (flag off; "preparation runs automatically on startup") to "a DUE_TIMES=on startup", and the "requester decided" attribution was added.

## a3
- Q1a: no. "Start the new binary while DUE_TIMES is off so it atomically fills missing deadlines before listening."
- Q1b: not said.
- Q2a: no. "Existing tickets missing due never require manual preparation."
- Q2b: not said. No refusal wording in after.md.
- Q3: partly. Present: "startup with DUE_TIMES=on must generate missing due times from each ticket's creation time and saved priority, save the resulting file, and then serve." Missing: no statement that the start never refuses because due times are missing (only "never require manual preparation").
- Q4: Substance changed: before the backfill ran "even when visibility is off"; after it is stated for "startup with DUE_TIMES=on", with an added "no manual preparation" statement.

## a4
- Q1a: yes. "Run the offline backfill before setting the flag."
- Q1b: yes. "Enabled startup refuses data with missing due values."
- Q2a: no. "startup with DUE_TIMES=on fills every missing due time ... saves the file, and then starts serving."
- Q2b: not said. after.md has no statement of refusal (its only nearby text is "disabled startup on legacy data").
- Q3: partly. Present: "fills every missing due time from the ticket's own creation time and priority, saves the file, and then starts serving." Missing: no statement that it never refuses to start because due times are missing.
- Q4: Substance changed: the offline backfill with the service stopped, and the enabled-start refusal ("fails to start enabled"), were replaced by a startup fill with DUE_TIMES=on that saves and then serves.

## a5
- Q1a: yes. "While the sole writer is stopped, run npm run backfill:due."
- Q1b: yes. "Enabled startup refuses a file with any missing due times."
- Q2a: no. "startup with `DUE_TIMES=on` fills missing deadlines from stored creation time and priority, saves the file, then listens."
- Q2b: no. "Missing deadlines do not cause startup refusal."
- Q3: fully. "fills missing deadlines from stored creation time and priority, saves the file, then listens. Missing deadlines do not cause startup refusal."
- Q4: Substance changed: the explicit offline command `npm run backfill:due` and the enabled-startup refusal were replaced by an automatic fill at DUE_TIMES=on startup with no refusal.

## a6
- Q1a: no. "First start the candidate with the flag off, check the populated file, then enable and restart." (the standalone migration command is the alternative not chosen)
- Q1b: not said.
- Q2a: no. "startup automatically fills every missing deadline ... saves the file, and only then serves requests."
- Q2b: no. "missing deadlines never cause startup to refuse a valid legacy file."
- Q3: fully. "when DUE_TIMES=on, startup automatically fills every missing deadline from the ticket's created instant and stored priority, saves the file, and only then serves requests ... missing deadlines never cause startup to refuse".
- Q4: Substance changed: the backfill was tied to any startup regardless of flag ("Verify flag-off startup writes complete data"); after ties it to DUE_TIMES=on and adds the "never refuse" statement.

## b1
- Q1a: no. "The new release backfills existing tickets at start even with DUE_TIMES off and saves the file."
- Q1b: not said.
- Q2a: no. "nobody prepares the data file by hand".
- Q2b: no. "It never refuses to start because due times are missing."
- Q3: fully. "when the service starts with DUE_TIMES `on`, it gives every ticket that has no due time one, from that ticket's own creation time and priority, saves the file, and then serves. It never refuses to start because due times are missing."
- Q4: Substance changed: before, the backfill ran at start "whether or not DUE_TIMES is on"; after it runs when DUE_TIMES is `on` ("with DUE_TIMES not `on` the start does not touch the file"), plus the no-refusal statement.

## b3
- Q1a: no. "at the first start the file is rewritten with a due time on every ticket, with no visible change in answers; the operator then sets DUE_TIMES=on."
- Q1b: not said.
- Q2a: no. "Nobody prepares the data file by hand".
- Q2b: no. "it never refuses to start because due times are missing"; also "a file whose tickets lack `due` never refuses the start."
- Q3: fully. "when the service starts with DUE_TIMES `on`, it gives every ticket without a `due` one (created + hours(priority), hours as set then), saves the file, and then serves; it never refuses to start because due times are missing."
- Q4: not available (before.md contains only "None"). after.md itself says it replaces "the spec's earlier default of backfilling before switch-on".

## Summary table

| folder | Q1a | Q1b | Q2a | Q2b | Q3 | Q4 in three words |
|---|---|---|---|---|---|---|
| a2 | no | not said | no | not said | partly | trigger moved, flag-on |
| a3 | no | not said | no | not said | partly | flag-on trigger added |
| a4 | yes | yes | no | not said | partly | offline backfill replaced |
| a5 | yes | yes | no | no | fully | offline command replaced |
| a6 | no | not said | no | no | fully | flag-on, no refusal |
| b1 | no | not said | no | no | fully | flag-on, no refusal |
| b3 | no | not said | no | no | fully | not available |
