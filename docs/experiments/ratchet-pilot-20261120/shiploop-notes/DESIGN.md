# A candidate ShipLoop change: an owner note is settled by a row in a result, never by a print

Status: accepted by the owner on 2026-11-22 at about 18:48 ("Yes, accept", to "Accept the owner-note fix into
main?"), after the six deliveries of section 7. Sections 2.3, 2.8, 3 and 6 were then corrected to what was accepted;
each correction is dated where it stands, and the text as registered before the deliveries is in the history.

Owner's word, 2026-11-22 about 14:27, to "Design the owner-note fix as the next candidate?": "Yes, design it". The
answer route (`../shiploop-answers/`) stays out of `main`; this is what its tests led to.

How this note came to be: sections 1 to 3 were first written at 14:35 on 2026-11-22, before any code
(`review/DESIGN-as-reviewed.md` is that text). The latest Sol at maximum effort reviewed it on a neutral copy
(14:38 to 14:52; question and answer word for word in `review/`): "Change first", ten findings. Section 4 lists
each finding and what was done with it. Sections 2, 3 and 5 are the design as it stands after the review. No code
existed when this was written.

Since then (same day): the build (16:22), a review of the code by the same reviewer (16:40, "Fix first", eleven
defects; section 6), and the owner's instruction at about 17:00 to build only what is sure and to run only what
would change a major decision. That instruction cut the fixes made before the deliveries to three and the deliveries
to rungs; where it changed a sentence of sections 2 or 5 the sentence says so.

## 1. What is wrong today, measured

An owner note (`shiploop note --run-dir RUN --text "..."`) is the run owner's way to say something to a run in
flight. In ShipLoop 2.6.0 a note is "delivered" when a step is accepted whose packet text held it. Nothing reads
what the step did.

- **On Codex with Sol a printed note does not reach the model: 3 deliveries of 3.** d5 (the note was in two reprints
  of the packet), n4 and n5 (in a `check`'s output and in the next packet). Each session's own record holds the
  note's words in command outputs and in nothing the model was given: a Sol session runs commands through scripts of
  its own that pass on part of the output (`../shiploop-answers/evidence/round-3/given-round3.txt`, and the read of
  the four earlier deliveries in `evidence/earlier-plain-notes.md`). ShipLoop recorded each note as delivered. The
  last message, the done packet and the report say nothing: they never mention owner notes at all.
- **When the model was given the words it acted on them, every time.** Sol: d1, d2 and d4 (a held callback, then a
  packet), and the eight answers of round 1 that the answer route held and then demanded a proof row for. Sonnet:
  m1 (a plain note during the build) and two answers. Fourteen of fourteen. This does not show what the row alone
  does: in those deliveries the hold, the duty text and the proof came together.
- **Even a held callback can arrive cut.** In d4 the refusal reached the model as its first sentence, 216
  characters, without the note; the words came later through a packet the session printed for itself.
- **The mechanics that let a note slip** (`mechanism-map-notes.md`, read from `main`): a `check` that prints a note
  marks it as shown, so the `complete` that follows is not held, and the note is not delivered either; a model that
  re-runs `next` gets the note into the packet's record and the next `complete` delivers it with no hold; a
  `blocked`, `send-back` or `add-work` result delivers the notes its packet showed; a stage with a review delivers
  at the producer's first submission; "printed" is read from the script's own print, so a host that drops the
  middle of a long print is not noticed.
- **After the plan is bound, one stage can change a requirement, and its texts say not to.** `implement` and
  `document` may only add marked lines to a requirement (`step_spec_refusal`). `carry-forward` edits the knowledge
  home and may replace the whole future queue, with no check on a reworded requirement; its reference and its
  packet duty say a changed requirement "is not a queue edit: report `blocked` or pause for direction". In m1 the
  Sonnet session did the sensible thing against that sentence: `document` recorded the note as an open item,
  `carry-forward` revised the requirement, added an architecture decision and queued a work item for it, which took
  4.4 minutes. The delivery was in step with itself.
- **A new run repairs a wrong delivery, 5 of 5** (10.7 to 13.1 minutes on Sol, 17.5 on Sonnet). That stays the way
  for a requester who speaks after the run. This design is for one who speaks during it.

## 2. The change

One sentence: every owner note must be accounted for in a stage's result, by a row that says what the stage did
with it; ShipLoop refuses the result while a row is missing, and the first line of the refusal says which note file
to read; a note a stage cannot act on is carried forward to a stage that can; and the done packet and the report
list every note with what was done.

ShipLoop stays unattended: nothing asks, nothing waits, no stage pauses, no loop gets a limit. A run in which no
note is written prints and stores what 2.6.0 does, with two exceptions: the standing duties of `document` and
`carry-forward` and the rule of `carry-forward`'s loop each carry one clause saying what an owner note that asks for
a requirement change means (2.3; made static after the review of the code, section 6, so that an instruction never
depends on which notes are on file), and the refusal of an unsupported result key lists `notes` among the allowed
keys. `trace --json` is outside this claim: its note fields change (2.7).

### 2.1 The row

A new result key, `notes`, allowed on a `done` result of any producer stage: a list of rows

    {"note": "N1", "did": "applied" | "already" | "carried" | "declined", "detail": "<text>", "item": "<work item>"}

- `applied`: this stage did what the note asks, within what the stage may change. `detail` says what changed.
- `already`: the run already does what the note asks. `detail` says where. This will be common: seven of the ten
  answers of round 1 agreed with what the specification had chosen.
- `carried`: the note needs something this stage may not change. `detail` says what it needs. A later stage owes it
  (2.2).
- `declined`: it cannot be done in this run. `detail` says why. Final; the requester reads the reason.
- `item` goes only with `applied`, and only at `plan` and `carry-forward`, where it is required: the work item that
  does the work (2.3).

### 2.2 Where a note stands, and who owes a row

**The ledger.** Where a note stands is read from the `notes` rows of the run's accepted `done` results, taken in
the order the results were accepted (the run's `history`), all of them, including results that a reconcile or a
send-back later took out of the current view. The latest row for a note decides: `applied`, `already` or
`declined` settles it for the rest of the run; `carried` leaves it open. A note with no row is open. A rewind does
not reopen a settled note: the files it changed are still changed, and a run must never stall on a note it already
answered.

**Who owes.** At a fresh `done` result of a producer stage, the rows owed are exactly:

- every note on file that has no row yet;
- every note whose latest row is `carried`, except that one carried by a stage of a work item (`step-plan` to
  `document`) is owed by `carry-forward` and by no stage of that item before it;
- at `handoff`, every open note whatever its row says.

So a carried note is owed by the next producer result, or, from inside a work item, by that item's
`carry-forward`. Both always come. `carry-forward` and `handoff` are refused a `carried` row: they settle. Every
other stage may carry, `plan` and `prepare` included, so no stage is ever left with a note it can neither act on
nor pass on. A stage the script records without a model's result owes nothing; the note waits for the next
producer result.

**One read per admission.** The notes on file are read once when a result is checked or completed, and the gate and
everything it prints use that one set. A note written after that read has no row, so the next producer result owes
it. If the notes folder cannot be read the result is refused; it is never taken to be empty.

### 2.3 Settling where the queue is made

- At `plan`, `applied` names in `item` a work item of the queue the result leaves.
- At `carry-forward`, `applied` names in `item` a work item of the future queue the result leaves, not the current
  item and not a completed one. A note that needs no work is `already`. When the note changes a requirement, the
  stage revises the requirement's entry in `KNOWLEDGE/spec.md` in place (the ID stays; the entry says the owner
  note revised it; no copy of the old clause is kept inside the entry, because a kept clause would hide the rewrite
  from the list of defaults), and the item follows that requirement, so the item's own step plan and tests are
  written for the revised text. This is what the Sonnet session of m1 did unasked.
- At an outer stage, a note that needs product work is the existing `add-work`. That result is not `done` and holds
  no row; the note stays owed and the first stage of the corrective item accounts for it.

The texts that tell `carry-forward` to block on a changed requirement (its reference, its packet duty and the rule
of its loop) carry the exception: an owner note this stage owes that asks for the change is that direction.
`carry-forward` cannot send back, so without the exception a note that changes a requirement there could only be
blocked or declined. No delivery met this clause (section 7); on Sol it is untested.

**Inside a work item (corrected 2026-11-22, after the deliveries).** The text registered before them said that
`document` carries a note that changes a requirement and that the item in hand is finished as planned while the
note waits for `carry-forward`, "the price of having no way back from a work item's steps to the specification".
Both were wrong about the engine. A stage whose step a note changes sends the step back to `step-plan`, the inner
route the engine already has; `step-plan` rewrites the requirement the note changes (the engine does not guard a
rewrite there), replans the step and writes the row; the wish is built inside the item in hand. Every delivery that
got a note during the build went this way, unprompted (4 of 4). So `document`'s duty is the released one again: a
requirement whose intent moved is a send-back. A stage that cannot do what a note asks within the item still
writes `carried`, and that item's `carry-forward` owes it.

### 2.4 The gate

One validator, at the places a result is admitted:

- **`check` and `complete` of a producer**, at the point in `dispatch` where the hold sits today: after the result
  file is read and before the loop receipt and every other gate, so a note is the first thing a refused result
  says.
- **Before an earlier check's yes is reused**: the rows owed are read again; a refused reuse is recorded as a no.
- **The import of a stage's review**: the result that takes effect (the review's replacement, or the parked one)
  must, if it is `done`, hold rows for exactly the notes the producer's parked result held rows for. No note that
  arrived during the review is taken in there. A review that turns the result into another outcome leaves the notes
  owed. The review's hand-off names each note's file and asks whether the work does what the row says.
- **A producer's exact replay of its parked result** is recognised before the gate and passes as today.

`done` is refused unless the result's `notes` rows are exactly the notes owed, one row each and no other row, and
each row has a `did` of the four, a `detail` that is not empty and not a placeholder, no `carried` at
`carry-forward` or `handoff`, and an `item` where 2.3 asks for one, naming an item as 2.3 says. A `blocked`,
`send-back`, `add-work` or `reconcile` result holds no rows (`notes` is a done-only key) and leaves the notes owed.

**The end of the run.** At `handoff` the notes are read once more just before the final save; a note that arrived
since the first read refuses the completion. The note command reads the run's state again after it has written a
note, and if the run ended in between it says so: the note was not read, start a new run. What is left is the
instant between that last read and the save.

**The refusal's first line can be acted on alone**, for both commands, because a session may show its model only
that much. It names the notes, the folder to read and the file to change:

    ShipLoop check: owner note N1 is not accounted for: read RUN/owner-notes/N1.md, add its row to "notes" in
    RESULT, then run this again.

(`ShipLoop navigator:` for `complete`; one line as printed; several notes are named by id with the folder.) Then
the row's shape and the four meanings of `did`, one line each; then each owed note's words, within the bounds the
packet uses for a note today. Exit code 2, on standard error, as every refusal. A result cannot pass until the row
is there, so a model that saw only the first line still has to open the file to write the row. If the note
changes the stage's work, the lines that follow say to change the work and rerun its checks before completing;
otherwise the row is added and the same command run again.

### 2.5 What goes

The hold (`NotesHeld`, `to_hold`, `mark_held`), the record of what a print showed (`shown.json`, `record_shown`),
the notice a `check` prints in place of a hold, and the delivery record (`owner_notes` in the state, `deliver`,
the line "Owner notes already delivered") are removed, with their readers in the trace, the trace page, the
references and the tests. A note is not "shown" or "delivered" any more: it is open, carried or settled, and that
is read from the ledger. A run saved by 2.6.0 with a delivery record in its state is not resumed by the new build
(one supported version); one that has notes and no delivery record owes rows for them at its next result.

### 2.6 What a stage is told

- Where the packet quotes owner notes today (right after the top block, required in a head), it quotes the notes
  the stage owes, within today's bounds for a note and for the block, and the two footer lines become the duty:

      Each is the run owner's instruction for this run. Account for each in this stage's result, "notes": one
      {"note", "did", "detail"} per note. did: "applied" (this stage did what it asks, within what this stage may
      change; say what changed), "already" (the run already does it; say where), "carried" (it needs something
      this stage may not change; say what; <who owes it next> must then account for it), "declined" (it cannot be
      done in this run; say why). ShipLoop refuses done without them.

  At `carry-forward` and `handoff` the duty leaves `carried` out, and at `plan` and `carry-forward` it adds the
  `item`. A note that was carried is quoted again where it is owed, with who carried it.
- The result template shows the `notes` key only when rows are owed, with the ids; the minimal template that a
  long contract falls back to keeps the duty and the folder.
- Other stages' packets carry one line with the lookup lines: which notes are settled and how, which are carried
  and to whom.
- The note command's own reply says who will account for the note.

### 2.7 What the requester sees

- The done packet lists every note early: its id, how it ended, and the report's path. It tells the host to say in
  its last message what happened to each note.
- The report gets a section "Your notes" after "Decided for you": each note's words and every row (stage, what it
  did, the detail). Where a row names an item, the report says from the run's own record whether that item was
  completed, is still queued, or is no longer in the queue: work that was scheduled is not shown as work that was
  done.
- A run that halts with a note open shows it as not accounted for.
- `trace` and the trace page show open, carried and settled in place of shown and delivered.

### 2.8 Not built, and why

- **Proof that `applied` is true.** The script checks that a row exists and that an item it names is in the queue,
  and nothing about the product. What the deliveries on file support is that a session acts on a note it has been
  given with a duty attached; they do not separate the row from the rest. The deliveries of section 5 are what test
  it.
- **Reopening a settled note after a rewind.** A reconcile or a send-back that reruns the stage which applied a note
  can undo the change. The row stands; the review of the rerun stage and the report are the checks.
- **A gate on a later queue that drops a note's item.** The report says what became of the item.
- **A new way back from a work item's steps to the specification.** None is needed: the send-back to `step-plan`
  is one, and the deliveries used it (2.3; corrected 2026-11-22, the earlier text said there was none).
- **The selector and binding of the answer route.** An answer to a listed default is a note like any other. No
  sentence is added to the list of defaults: how a host learns to record what a user says is not changed here.
- **Waiting for a note.** Nothing waits.

## 3. Known ways round (for the loophole table, each with a fixture)

| Way round | What happens |
| --- | --- |
| A row says `applied` or `already` and the work does not do it | Passes. The stage's review, where it has one, and the report, which shows the words beside the row, are the checks |
| A row says `declined` for a poor reason | Passes. The requester reads the reason |
| `carry-forward` names an item that does something else, or a later `carry-forward` drops or rewrites the item | Passes. The report says whether the item was completed, queued or dropped |
| A rewind reruns the stage that applied a note and the rerun undoes it | Passes. The row stands |
| The host never records what the user said as a note | Nothing happens |
| A note is written in the instant between the last read at `handoff` and the save | The note command has already said "written"; the report does not hold it |

Recorded beside the table, each with no fixture because nothing is built for it (added 2026-11-22 after the code review and the deliveries):

- The saved report is rendered before that last read: a note written in the instant between can be in the done packet and not in the saved report, and the note command can say "no stage read it" of a note `handoff` settled in the same instant; a yes reused for that completion is not turned into a no. Recorded, not built (the code review's finding 4): a race at the instant a run ends.
- A producer changes its parked draft: `check` says yes and `complete` refuses the same draft. Recorded, not built (finding 5).
- A notice (a hook installing itself, the recovery of an interrupted iteration, the knowledge-return line) prints before a refusal on three rare paths; the refusal for a note that arrives during `handoff` keeps its own shorter wording. Recorded, not built (finding 7).
- About a hundred notes owed at once overflow the minimal result template of a head. Recorded, not built (finding 9); no run on file has had more than one note.
- A session puts its row on a `send-back` result. Refused as a done-only key; the session sends the result again without the row (3 deliveries of 3, 3 to 9 seconds each). The stage that then submits a done result writes the row.
- The host's last message does not mention the note. On Sol the done packet's lines about notes do not reach the model (0 deliveries of 3 checked); the report holds them. On Sonnet the last message says it (1 of 1).

## 4. The review, and what it changed

| # | Finding (Sol 6.2 at max effort; verified in the code by the reviewer where it says so) | Decision |
| --- | --- | --- |
| 1 | The view of current results keeps one result per stage and item, so a later step's result would reopen a settled note; an outer send-back and `add-work` can leave a carried note owed by nobody | The ledger of 2.2: rows in acceptance order over every accepted result, settled is settled, and a carried note is owed by the next producer result or the item's `carry-forward`, both of which always come; `handoff` owes every open note |
| 2 | The gate's place, the reuse of a yes, the review's import, a parked producer's replay and the race with the note command each need their own rule; a failed read of the notes folder is taken as empty today | 2.4: the gate sits where the hold sits; the reuse revalidates and records a no; the import checks the result that takes effect against the parked rows; an exact replay passes first; one read per admission, refused when unreadable; a second read at `handoff` before the save, and the note command re-reads the state |
| 3 | The carry table routed by stage order, not by what a stage may change; `plan` could be left unable to settle a note; `carry-forward` cannot send back | The table is gone. A stage applies what is within its own duty and carries the rest; every stage but `carry-forward` and `handoff` may carry, and the only fixed route is from a work item's steps to its `carry-forward` |
| 4 | The rule for a dropped item both required and forbade a row; an item can be kept and rewritten; a kept "superseded" clause inside an entry hides the rewrite from the list of defaults; `primary.check_queue` does not tie a changed requirement to its item | The dropped-item gate is not built; the report says what became of each item. The requirement is revised in place with no copy of the old clause in the entry. The tie from requirement to item is a duty, recorded as a limit |
| 5 | With today's wording the first sentence of a refused `check` is "the check says no"; a note that lands after the loop closed needs its own recovery line | A formatter for both commands whose first line names the notes, the folder and the result file; the lines after it say when the work must be redone and its checks rerun |
| 6 | Whole packets are 20 to 30 thousand characters; the quotes, carry detail and template rows cannot all be guaranteed room | The block keeps today's bounds for a note and for the block, with the duty and the folder always in the required part; the done packet carries a short summary and the report's path, the report carries the rest |
| 7 | The readers of the print-based bookkeeping: engine, trace writer and reader, trace page, live progress view, references, tests, the E2E note helper and metrics | Removed together (2.5); a whole-packet reader still gets the words in the packet and the lookup line later |
| 8 | What registering the key takes; a stored result must reload without reading note files; byte parity needs its boundary named; resuming 2.6.0 runs must be decided | The shape is checked at load and the exact checks at admission; parity is as stated at the top of section 2; resumption is as stated in 2.5. The sentence for the list of defaults is dropped (2.8) |
| 9 | The earlier live test lost four deliveries of seven to the stand-in's rule; failing five checks does not show the opposite wish was built; declining everything would pass the first reading | Section 5: the rule is repaired and checked on every row on file first; the opposite wish needs the service's own refusal in the check's output, the requirement and the delivery's own tests to agree; a declined note that could have been done counts against the main reading |
| 10 | The smallest useful build is the accountability gate, with requirement rewriting left for later | Not followed in one respect: `carry-forward` may settle a carried note by revising a requirement and queueing the work. The owner asked for a late answer to reach the same run, one delivery shows the product's own steps doing it soundly, and section 5 tests it on both drivers. Everything else is cut to the reviewer's size |

## 5. How it will be judged (fixed before any delivery of the candidate runs)

**Tests with no model, through the real CLI**, both output streams read:

- A note written after the packet printed: `check` says no and its first line names the note and the folder;
  `complete` is refused the same way; the result with the row is accepted. Repeating the same result is refused
  each time, with nothing held "once".
- A note written before the packet prints: the packet quotes it with the duty and a result with the row is accepted
  at the first try. The reprint by `next` settles nothing.
- Each refusal: a missing row, an extra row, an unknown `did`, an empty `detail`, `carried` at `carry-forward` and
  `handoff`, `applied` without `item` at `plan` and `carry-forward`, an `item` that is not in the queue or is the
  current or a completed item.
- The ledger: a row at `implement` of one step stays settled through the next step's result; carried at
  `implement`, not owed at `test` or `document`, owed at `carry-forward`; carried at `discovery`, owed at
  `research`; settled notes stay settled through a reconcile, an inner send-back and an outer send-back; after
  `add-work` the corrective item's first stage owes an open note and the revisited outer stage does not; `handoff`
  owes every open note.
- A yes from `check`, then a note, then `complete` with that same result: refused, and recorded as a no. A note
  that lands after an inner loop has closed: the result with the row is accepted without the loop being run again.
- A review: import of the parked result unchanged, of a replacement that drops a row or changes one, and of one that
  changes the outcome; a note that arrives during the review is owed by the next stage; the producer's replay of
  its parked result passes. A stage the script records, with and without a review.
- A `blocked` result and its resumed stage, a paused producer, `send-back` and `add-work`: no rows, the notes stay
  owed.
- The end: a note written between the two reads at `handoff` refuses the completion; a note written after the run
  ended is refused; the note command's reply when the run ends as it writes.
- A run with no note and closed standard input prints and stores what 2.6.0 does, checked against a saved run of
  it. A stored result with `notes` reloads when the note files are gone.
- The done packet, the report and `trace`; packet sizes with one long note, with several, and with a long run path.
- Each loophole row has a fixture that shows what passes.

**Real deliveries on the two drivers the owner uses** (Codex with gpt-6.2-sol at medium, Claude Code with
claude-sonnet-5-5 at medium), case `ticket-due-times`, each beside the stand-in requester.

The stand-in sends a plain note that contradicts what the list's start-up row decided: the owner's ruling for a
row that chose a separate command or a refusal, the opposite wish for a row that fills the due times in at a start
(`../shiploop-answers/late-notes.json`). Its rule for telling the two is repaired before any run: a start-up row
with no sign of a separate command or a refusal is taken to fill at a start, and it must classify every start-up
row on file as a reader did or as read here (the eighteen judged before, and the rows of n1 to n6). For each
delivery the record holds: the note sent, the stage open then, whether the model was given the words
(`given_to_model.py`), every row, and the outcome.

- **During the build**: six on Sol, two on Sonnet; the note is sent when the first `implement` packet prints.
- **Before the plan**: three on Sol, one on Sonnet; the note is sent when the list is printed.
- **These two counts are superseded (2026-11-22 about 17:00, before any delivery ran).** The owner: run only what
  would change a major decision. The deliveries are rungs, registered in the journal's section 29: first three on
  Sol and one on Sonnet with the note during the build, the one case the released engine loses; then, only if that
  passes, two on Sol with the note before the plan, which can only show a loss; three more on Sol during the build
  only if the first rung is split. Each rung has its stop rule there. The readings M1 to M5 below stand as written.
- The control is on file: on the released engine a plain note during the build was not taken in on Sol (n4, n5: 2
  of 2) and was taken in on Sonnet (m1: 1 of 1).

Readings:

- **M1, accounted.** Every note sent has rows through to `applied`, `already` or `declined`, and no delivery is
  stopped at the gate (a refusal the session recovers from is counted and is not a failure).
- **M2, taken in: the main reading.** In every delivery where a contradicting note was sent, the delivered product
  does what the note asks. For the owner's ruling: the five start-up checks pass. For the opposite wish: the five
  start-up checks fail with the service's own refusal in their output (not a timeout and not a crash), the
  requirement at the end states the wish (a reader blind to the checks), and the delivery's own tests pass. A note
  that is `declined` although the run could still have done it counts against M2; one sent to a row the stand-in
  misread is counted apart.
- **M3, in step with itself.** The five verdicts hold, and the requirement, the tests and the product agree.
- **M4, told.** The done packet and the report list the note with what was done; whether the host's last message
  says so is counted.
- **M5, described.** Minutes and tokens beside a first run without a note, and beside a first run followed by a new
  run (section 11 of the answer route's design), which is the other way to the same product.
- The design is wrong if a delivery loses a note that was written in time, cannot get past the refusal, or reports
  `applied` while the product still does what the note contradicts. If M1, M2 or M3 fails, the candidate is
  reported as it stands and nothing more is built on it without the owner.


## 6. The review of the code, and what was done with it

The same reviewer read the build as committed (`review/sol-code-question.md`, `review/sol-code-answer.md`, word for
word): "Fix first", eleven defects, fixtures that would pass on a broken engine, an audit of the change note.
Nothing in it is against sections 2 to 5.

The owner's instruction of about 17:00 decided the order: before the first deliveries only what a real delivery can
meet is fixed. The rest waits, and is fixed only if the first rung passes and the recommendation is to accept; if
the candidate is not accepted none of it is needed.

| # | Finding | Decision |
| --- | --- | --- |
| 3 | The standing duties of `document` and `carry-forward` and the rule of `carry-forward`'s loop still said to send back or report `blocked` on a changed requirement, against the owed-notes block and 2.3 | **Fixed before the deliveries.** The exception is in the three standing texts, statically. This is the path the first rung tests |
| 7 (first part) | A row whose `note` is not an id crashed the formatter; a scalar `notes` and two rows for one note got a misleading first line | **Fixed before the deliveries.** A model can mistype a row in a real run, and on Sol the first line may be all it is given. The first line now says what is wrong and what to do for each |
| - | Found in reading `_row_fault`: one refusal printed `({listed})` literally | **Fixed before the deliveries** |
| 1 | A note file that cannot be read or decoded is skipped, so a result passes without its row | Waits. Needed for `main`; no delivery meets it |
| 2 | A note written after a settled note's file was removed reuses its id and inherits its row | Waits. Needed for `main`; needs a file removed by hand |
| 4 | The last read at `handoff` sits before the report is rendered: the saved report and the done packet can list different notes, and the note command can say "no stage read it" of a note `handoff` settled; a reused yes is not replaced by a no there | Waits. A race at the instant a run ends; what cannot be closed is recorded as a limit in section 3 |
| 5 | A changed draft on a parked action gets a yes from `check` and a refusal from `complete` | Waits |
| 6 | A placeholder (`...`, text in angle brackets) passes as a `detail`; a lone surrogate passes admission and fails at the write | Waits. If a delivery of the first rung writes a placeholder, that is read as a row filled in as a form, and counted against M2 |
| 7 (rest) | The refusals for a note arriving during `handoff` and for a review's import have their own shorter wording; three notices can print before a refusal on rare paths | Waits |
| 8 | A review's malformed `notes` is skipped when the parked result had none, and refused later by another check | Waits |
| 9 | With a hundred notes the minimal result template overflows the head | Waits; a size no run on file comes near, and likely a recorded limit |
| 10 | The harness's readers grade a saved run of the released engine differently than before (a held callback counted as a refusal; a delivered note read as open) | Waits. Needed for `main`, so that saved evidence is never rescored; the deliveries of this candidate are new runs and are read by `read_notes.py` |
| 11 | `shiploop --help` and the README's "Steer a run in flight" still describe settlement by printing | Waits. Needed for `main` |
| audit | The change note's parity sentence was too broad | The sentence is corrected with the fix of finding 3; the rest of the audit waits with its findings |
| fixtures | Tests that would pass on a broken engine (the ledger across a second step, the reconcile, the end of the run) and paths with no test | Wait with the findings they belong to. The tests for what was fixed now were shown failing on the build as committed |

## 7. What the deliveries showed (2026-11-22, 17:40 to 18:41)

Six real deliveries in two rungs, registered before they ran (the journal's section 29 has the table, the readings
and the findings F80 to F83; the evidence is in `evidence/rungs/`).

- **The note is taken in, 6 of 6.** Sol during the build 3 of 3 (the released engine: the model was given the
  note's words in 0 of 3), Sonnet during the build 1 of 1, Sol before the plan 2 of 2. M1, M2 and M3 hold in every
  delivery; a blind reader found each final requirement states the note's wish. The refusal's first line was given
  to the model in all six.
- **The route was not the one of 2.3.** During the build all four sessions sent the step back to `step-plan`,
  rewrote the requirement there and built the wish inside the item in hand. None finished the item as planned and
  none queued a new item at `carry-forward`. So two sentences of this design are wrong about the engine: 2.3's "the
  item in hand is finished as planned while a carried note waits" and 2.8's "no way back from a work item's steps
  to the specification". A send-back to `step-plan` is that way back, and the engine does not guard a rewrite of a
  requirement there.
- **Told:** the report and the done packet in 6 of 6; the host's last message on Sonnet, never on Sol (the done
  packet's lines about notes were given to the Sol model in 0 of 3).
- **Cost:** about the minutes of a first run alone on Sol (15.4 to 16.8 against 12.6 to 17.2), where a first run
  and a repair run take 25 to 30; one wasted callback per Sol delivery of the first rung (a row put on a
  `send-back`).

**The recommendation by the registered rule: accept.** The owner decides. If accepted, before `main`:

1. The findings of section 6 that `main` needs: 1 (an unreadable note file refuses), 2 (a new note's id is above
   every id in the ledger), 6 (placeholders are not a `detail`), the import half of 7 (its first line names the notes
   and the folder), 8, 10 (saved runs of the released engine are graded as before), 11, and the rest of the change
   note's audit. Recorded as limits and not built: 4 (the instant a run ends), 5 (a changed draft on a parked
   action), the rare notices of 7, and 9 (a hundred notes).
2. The clause added to `document`'s duty comes back out, so `document` says what the released engine says: a
   requirement whose intent moved is a send-back. That is the route every delivery took, and the clause was met by
   none. The clause in `carry-forward`'s duty and loop rule stays: that stage cannot send back, so without it a note
   that changes a requirement there could only be blocked or declined; it is untested on Sol and says so here.
3. 2.3 and 2.8 rewritten to the route the deliveries took.
4. The wide tests once, and one delivery on the final commit.
