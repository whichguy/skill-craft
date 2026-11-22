# A candidate ShipLoop change: an owner note is settled by a row in a result, never by a print

Status: a design, before any code. Not on `main`, not released. The owner decides whether the candidate that
follows is accepted.

Owner's word, 2026-11-22 about 14:27, to "Design the owner-note fix as the next candidate?": "Yes, design it". The
answer route (`../shiploop-answers/`) stays out of `main`; this is what its tests led to.

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
  m1 (a plain note during the build) and two answers. Fourteen of fourteen.
- **Even a held callback can arrive cut.** In d4 the refusal reached the model as its first sentence, 216
  characters, without the note; the words came later through a packet the session printed for itself.
- **The mechanics that let a note slip** (`mechanism-map-notes.md`, read from `main`): a `check` that prints a note
  marks it as shown, so the `complete` that follows is not held, and the note is not delivered either; a model that
  re-runs `next` gets the note into the packet's record and the next `complete` delivers it with no hold; a
  `blocked`, `send-back` or `add-work` result delivers the notes its packet showed; a stage with a review delivers
  at the producer's first submission; "printed" is read from the script's own print, so a host that drops the
  middle of a long print is not noticed.
- **After the plan is bound, one stage can change a requirement, and its reference says not to.** `implement` and
  `document` may only add marked lines to a requirement (`step_spec_refusal`). `carry-forward` edits the knowledge
  home and may replace the whole future queue, with no check on a reworded requirement; its reference text says a
  changed requirement "is not a queue edit: report `blocked` or pause for direction". In m1 the Sonnet session did
  the sensible thing against that sentence: `document` recorded the note as an open item, `carry-forward` revised
  the requirement with the superseded text kept, added an architecture decision and queued a work item for it,
  which took 4.4 minutes. The delivery was in step with itself.
- **A new run repairs a wrong delivery, 5 of 5** (10.7 to 13.1 minutes on Sol, 17.5 on Sonnet). That stays the way
  for a requester who speaks after the run. This design is for one who speaks during it.

## 2. The change

One sentence: every owner note must be accounted for in a stage's result, by a row that says what the stage did
with it; ShipLoop refuses the result while a row is missing, and the refusal names the note's file and quotes it;
a note a stage may not act on is carried to the stage that may, which must settle it; and the done packet and the
report list every note with what was done.

ShipLoop stays unattended: nothing asks, nothing waits, no stage pauses, no loop gets a limit. A run with no note
behaves as 2.6.0.

### 2.1 The row

A new result key, `notes`, on a `done` result of any producer stage: a list of rows

    {"note": "N1", "did": "applied" | "already" | "carried" | "declined", "detail": "<text>", "item": "<work item>"}

- `applied`: this stage did what the note asks, in its own work. `detail` says what changed.
- `already`: the run already does what the note asks. `detail` says where (a requirement, a file). This is the
  common case: seven of the ten answers of round 1 agreed with what the specification had chosen.
- `carried`: the note needs something this stage may not change (a requirement during a work item's steps, the
  queue after the plan is bound). `detail` says what it needs. The note goes to this stage's carry target (2.2).
- `declined`: it cannot be done in this run. `detail` says why. Final.
- `item` is given only with `applied`, at `plan` and `carry-forward`: the work item that does it.

### 2.2 Who owes a row

A note is **open** from the moment it is written until an accepted result holds a row for it with `applied`,
`already` or `declined`. Where a note stands is read from the run's current accepted results, the projection that
a reconcile or a send-back already narrows: a row in a result that was taken out no longer counts, and the note is
open again for the stages that rerun.

- A note no accepted result names is owed by the **next `done` result of whatever producer stage is current**.
- A note whose latest row is `carried` is owed by the **carry target** of the stage that carried it, at that
  stage's next `done` result, and by no stage in between.

Carry targets, fixed in one table:

| Stage that carries | Target |
| --- | --- |
| intake, discovery, research | spec |
| spec, test-strategy | plan |
| plan | none: it settles (a requirement it cannot settle is the existing `reconcile`, after which the reopened stage owes the row) |
| prepare, and every stage of a work item (step-plan to document) | the next carry-forward |
| carry-forward | none: it settles |
| each outer stage but the last | the next outer stage |
| handoff | none: it settles |

A stage with no target is refused a `carried` row. Notes hop at most along that table, so no note is carried
round in a circle.

### 2.3 What settling means where the plan is made

- At `plan`, `applied` needs `item`: an id of the work items the result leaves.
- At `carry-forward`, `applied` needs `item`: an id of the **future** queue the result leaves (a new item, or one
  kept or rewritten). The stage revises the requirement in `KNOWLEDGE/spec.md` first when the note changes one,
  keeping the superseded text under it, and the item follows that requirement. This is what m1 did unasked.
- A later `carry-forward` whose `work_items` drops an item that an accepted row names, before that item is done,
  must hold a new row for that note (another item, or `declined`); otherwise the replacement is refused.
- At an outer stage, a note that needs product work is the existing `add-work`; the stage's later `done` result
  holds the row. `item`, when given there, must name a work item of the run.

The reference text of `carry-forward` changes with this: a changed requirement is still no queue edit, except
where an owner note carried to the stage asks for it; then the stage revises the requirement and queues the work.

### 2.4 The gate

One validator, where the `defaults` gate sits: at `check` and `complete` of a producer (`_evaluate`, first among
the gates, so a note is the first thing a refused result says), before an earlier check's yes is reused, and at
the import of a stage's review. One read of the notes is made for each admission of a result.

`done` is refused unless the result's `notes` rows are exactly the notes owed, one row each and no other row, and
for each row: `did` is one of the four; `detail` is not empty and not a placeholder; `carried` only where the
stage has a target; `item` present where 2.3 asks for it and naming an item as 2.3 says.

At the import of a review the owed set is the notes the producer's parked result holds rows for; no note that
arrived during the review is taken in there (it is owed by the next producer result). The review's hand-off names
each note's file and asks: does the work do what the row says?

A `blocked`, `send-back`, `add-work` or `reconcile` result carries no rows (`notes` is a done-only key), and the
notes stay owed. A stage recorded by the script with no packet owes nothing.

**The refusal carries the note.** Its first sentence holds the note's id, the file to read and the key to add,
because a session may show its model only that much:

    ShipLoop navigator: this result does not account for owner note N1: read RUN/owner-notes/N1.md and add to the
    result "notes": [{"note": "N1", "did": ..., "detail": ...}].

then the four meanings of `did` in one line each, then each owed note's words, whole. `check` says no with the
same text and the same exit code. A result cannot pass until the row is there, so a model that saw only the first
sentence still has to open the file to write the row.

### 2.5 What goes

The hold (`NotesHeld`, `to_hold`, `mark_held`), the record of what a print showed (`shown.json`, `record_shown`),
the print a `check` makes in place of a hold, and the delivery record (`owner_notes` in the state, `deliver`) are
removed. A note is not "shown" or "delivered" any more: it is open, carried or settled, and that is read from
results. A run saved by 2.6.0 while it holds a delivery record is not resumed by the new build (one supported
version).

### 2.6 What a stage is told

- Where the packet quotes owner notes today (right after the top block, required in a head), it quotes every note
  the stage owes, and the two footer lines become the duty:

      Each is the run owner's instruction for this run. Account for each in this stage's result, "notes": one
      {"note", "did", "detail"} per note. did: "applied" (this stage did what it asks; say what changed),
      "already" (the run already does it; say where), "carried" (it needs a requirement or the plan changed, which
      this stage may not do; say what it needs; <target> then settles it), "declined" (it cannot be done in this
      run; say why). ShipLoop refuses done without them.

  A note carried to the stage is quoted the same way, with who carried it and that stage's `detail`.
- The result template shows the `notes` key only when rows are owed, with the ids.
- Other stages' packets carry one status line, with the lookup lines: which notes are settled and how, and which
  are carried and to where.
- The list of defaults in the `test-strategy` packet gains one sentence for the host: if the user answers one,
  record their words at once with the note command; the stage in hand must account for it.

### 2.7 What the requester sees

- The done packet lists every note: its words, and each row (stage, what it did, the detail). It tells the host to
  say in its last message what happened to each note.
- The report gets a section "Your notes" after "Decided for you": the same, as a table.
- A run that halts with a note still open shows it as not accounted for.
- `trace` shows open, carried and settled in place of shown and delivered.

### 2.8 Not built, and why

- **Proof that `applied` is true.** The script checks that a row exists, that an item it names is in the queue, and
  nothing about the product. In round 1 the stronger proof of the answer route (the requirement's text changed) was
  never what stopped a result: no command was refused for it. What made the sessions act was being given the words
  with a duty attached.
- **The selector and binding of the answer route.** An answer to a listed default is a note like any other.
- **A way back from a work item's steps to the specification.** A note that changes a requirement during a step is
  carried; the item in hand is finished as planned, and `carry-forward` queues the change. Stopping the item
  half-way needs a route ShipLoop does not have.
- **Waiting for a note.** Nothing waits.

## 3. Known ways round (for the loophole table, each with a fixture)

| Way round | What happens |
| --- | --- |
| A row says `applied` or `already` and the work does not do it | Passes. The stage's review, where it has one, and the report, which shows the words beside the row, are the checks |
| A row says `declined` for a poor reason | Passes. The requester reads the reason |
| `carry-forward` names an item that does something else | Passes. Not looked for |
| The host never records what the user said as a note | Nothing happens |
| A note is written in the last seconds of the run, after `handoff` was submitted | Refused by the note command once the run is done, as today; in the gap before that, as today's limit says, it can miss the report |

## 4. How it will be judged (fixed before any delivery of the candidate runs)

**Tests with no model, through the real CLI.** A note written after the packet printed: `check` says no and quotes
it, `complete` is refused, the result with the row is accepted. A note written before the packet prints: the
packet quotes it with the duty and a result with the row is accepted at the first try. Each refusal: a missing
row, an extra row, an unknown `did`, an empty `detail`, `carried` at `plan`, `carry-forward` and `handoff`,
`applied` without `item` at `plan` and `carry-forward`, an `item` that is not in the queue. The carry chain: a row
carried at `implement` is not owed at `test` or `document` and is owed at `carry-forward`; carried at `discovery`,
owed at `spec`. A queue replacement that drops a note's item. `blocked`, `send-back` and `add-work` carry no rows
and leave the note owed. A reconcile and a send-back that take a result out reopen its notes. A review's import of
an unchanged result and of one that drops a row; a note that arrives during the review is owed by the next stage.
A yes from `check`, then a note, then `complete`: refused. A run with no note and closed standard input behaves as
2.6.0. The done packet, the report and `trace` list the notes. Packet sizes stay inside their budgets. Each
loophole row has a fixture that shows what passes.

**Real deliveries on the two drivers the owner uses** (Codex with gpt-6.2-sol at medium, Claude Code with
claude-sonnet-5-5 at medium), case `ticket-due-times`, each with the stand-in requester. The control is on file:
on the released engine a plain note during the build was not taken in on Sol (n4, n5: 2 of 2) and was taken in on
Sonnet (m1: 1 of 1).

- **During the build** (six on Sol, two on Sonnet): when the first `implement` packet prints, the stand-in sends a
  plain note that contradicts what the list's start-up row decided, as in the test of section 10 of the answer
  route's design, with its rule for telling the row repaired (a row with no sign of a separate command or a
  refusal is taken to fill at a start).
- **At the list** (three on Sol, one on Sonnet): the same note, sent when the list is printed.
- N1, both drivers. Every note sent is accounted for: the accepted results hold its rows through to `applied`,
  `already` or `declined`, and no delivery is stopped at the gate (a refusal the session recovers from is counted,
  not a failure).
- N2, the main reading. Where the note contradicts the row and is not declined, the delivered product does what
  the note asks: the five start-up checks agree with the note sent (they pass for the owner's ruling and fail for
  the opposite wish).
- N3. The delivery agrees with itself: the five verdicts hold, its own tests pass, and a reader blind to the checks
  finds the requirement at the end states the note.
- N4. The requester is told: the done packet and the report list the note with what was done, and the last message
  says so.
- N5, described: minutes and tokens beside a first run without a note, and beside a first run followed by a new
  run, which is the other way to the same product (section 11 of the answer route's design).
- If N1, N2 or N3 fails, the candidate is reported as it stands and nothing more is built on it without the owner.
