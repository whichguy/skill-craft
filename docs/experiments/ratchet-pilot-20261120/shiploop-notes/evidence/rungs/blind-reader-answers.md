# The blind reader's answers, word for word (first rung)

## g1, g2, g3 (one reader, 2026-11-22 about 18:00)

**g1**
1. Different from before.md? YES. before.md has the service fill missing due times automatically at startup before listening ("On startup the only writer assigns missing timestamps ... saving all of them before listening"). The message wants no fill at startup: a separate operator command, run with the service stopped, does the fill, and the service refuses to start (naming the command) if DUE_TIMES is on and any ticket lacks a due time ("Do not fill in due times when the service starts").
2. after.md states what the message asks? YES. "With the service stopped, the operator runs `node scripts/backfill-due-times.js` ... Startup never fills missing values. Enabled startup refuses an incomplete file and names the command."
3. Contradiction remaining? NO. Nothing in after.md contradicts the message. It also drops the old startup-fill text.
4. Says it changed because of a message from the requester? YES. "owner clarification N1 on explicit backfill".

**g2**
1. Different from before.md? YES. before.md has an explicit offline backfill and startup that refuses an incomplete file ("Startup with on and an incomplete existing file fails with migration guidance"). The message asks for the opposite: no hand preparation, startup with DUE_TIMES on fills missing due times itself, saves, then serves, and never refuses ("It never refuses to start because due times are missing").
2. after.md states what the message asks? YES. "Startup with DUE_TIMES on fills every missing due from the stored creation time and current stored priority ... saves the version-1 snapshot atomically, and then serves."
3. Contradiction remaining? NO. The offline backfill command and the refusal on incomplete data are both gone. The only mention of the file is the verification step "Read the file while the service is live," which does not conflict.
4. Says it changed because of a message from the requester? YES. "Basis: existing-data and rollback request and owner clarification, 2026-11-22."

**g3**
1. Different from before.md? YES. before.md has startup with the gate off filling missing due values before listening ("Before listening, save missing due values ..."). The message wants no startup fill: a separate stopped-service command fills them, and startup with DUE_TIMES on refuses and names the command if any ticket lacks a due time ("If the service is started with DUE_TIMES set to on while any ticket has no due time, it refuses to start and names that command").
2. after.md states what the message asks? YES. "with the service stopped, run `DATA_FILE=path node scripts/backfill-due-times.js` to save missing due values ... With the gate on, an incomplete file must stop startup and name the command."
3. Contradiction remaining? NO. It adds "Verify legacy startup with the gate off does not backfill," which agrees with the message.
4. Says it changed because of a message from the requester? NO. There is no "Basis" line and no mention of a clarification, message or note from the requester in after.md. The only source mention is the "Acceptance —" heading.

Final lines:
- g1: the final requirement DOES state what the message asks.
- g2: the final requirement DOES state what the message asks.
- g3: the final requirement DOES state what the message asks. It never mentions the requester's message as the reason for the change.

(Note: g1/answer.txt and g3/answer.txt are word-for-word identical. g2's answer is the opposite behaviour. The three files for each folder were all read in full.)

## k1 (a second reader, 2026-11-22 about 18:16)

1. YES. before.md says the service backfills missing due times itself at startup, "regardless of `DUE_TIMES`" (the file is saved "before any request"). answer.txt asks that the service NOT do this at start ("Do not fill in due times when the service starts") and that a separate operator command do it instead, with the service refusing to start when `DUE_TIMES` is on and a ticket lacks a due time.

2. YES. after.md: "the service never fills in due times when it starts. An operator stops the service and runs a separate command, `node bin/backfill-due.js [--data FILE]`... which gives every ticket that has no due time one, from that ticket's own `created` and `priority`, and saves the file". It also states the refusal: "If the service starts with `DUE_TIMES=on` while any ticket has no due time, it refuses to start (exit 2, a log line) and the message names `bin/backfill-due.js`."

3. NO. I found nothing in after.md that contradicts answer.txt. The old startup-backfill behaviour is gone. The closest thing is "With `DUE_TIMES` not `on` the service starts on such a file and leaves it as it is." answer.txt only asks for refusal when `DUE_TIMES` is on, so that is consistent.

4. YES. after.md opens with "Owner note N1 (2026-11-23) revised this requirement: the service never fills in due times when it starts."

k1: the final requirement DOES state what the message asks.

# The second rung (h1, h2; a third reader, same question, 2026-11-22 about 18:43)

**h1**

1. Does answer.txt ask for something different from before.md? YES. Before: startup itself runs a repeatable backfill "before listening, even with the flag off". Answer: startup must not fill anything ("Do not fill in due times when the service starts"); an operator runs a separate command with the service stopped, and a start with DUE_TIMES on and any ticket lacking a due time must refuse and name that command.
2. Does after.md state what answer.txt asks for? YES. Quote: "Starting the service never fills in existing deadlines." Also: "requires a separate, repeatable command: stop the service and run `DATA_FILE=... npm run migrate:due`" and "With the feature on and any due value absent, startup fails and names `npm run migrate:due`." The command computes from creation time and stored priority ("From each persisted record's creation time and stored priority, calculate any missing due time") and saves the file ("A migration write failure leaves the old file available").
3. Does after.md still state anything that contradicts answer.txt? NO. The old "runs a repeatable backfill before listening, even with the flag off" is gone. (Nothing in after.md says the old API stays visible or that startup fills anything.)
4. Does after.md say it was changed because of a message from the requester? YES, in one place. Quote: "The November 2026 operator clarification requires a separate, repeatable command". It does not say "the requester's message" in those words, but it names an operator clarification as the cause of the change.

**h2**

1. Does answer.txt ask for something different from before.md? YES. Before: "On startup, the single service writer fills missing deadlines ... It atomically persists a changed snapshot before listening, even with visibility off". Answer: startup must not fill anything ("Do not fill in due times when the service starts"); a separate operator command, run with the service stopped, does it, and an enabled start with any ticket lacking a due time refuses and names the command.
2. Does after.md state what answer.txt asks for? YES. Quote: "With the service stopped, operators run `npm run backfill:due-times` to fill missing deadlines from each stored ticket's created timestamp and current priority. The command atomically saves the changed snapshot". Also "Startup never fills deadlines. Enabled startup refuses a file containing any ticket without a deadline and names the command." One small difference: it says "current priority", while answer.txt says "that ticket's own creation time and priority", which means the same thing.
3. Does after.md still state anything that contradicts answer.txt? NO. The startup-fill sentence is gone.
4. Does after.md say it was changed because of a message from the requester? NO. I found no phrase about a clarification, note or message from the requester. The text just states the new behaviour.

**Verdicts**
- h1: the final requirement DOES state what the message asks.
- h2: the final requirement DOES state what the message asks.
