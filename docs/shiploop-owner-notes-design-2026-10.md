# ShipLoop owner notes: design

Status: **proposed 2026-10-25; waiting for the owner to choose D1 to D5.** Nothing in packets, verbs or tests has
changed yet. Journal: [shiploop-run-trace-journal.md](shiploop-run-trace-journal.md). Evidence:
[shiploop-owner-notes-evidence/](shiploop-owner-notes-evidence/).

## The ask

Owner, 2026-10-25: the run trace (shiploop 1.12.0) left out feedback written during a run. That was fine for the first
pass, but it is wanted. The goal: the owner writes a note on a running run, and the model reliably sees it at its next
step.

"Reliably" has to survive what a run does to the model's context. Context is cleared between stages, so only what a
command prints reaches the step after it. A chat message to the session is gone after the next clear, and an unattended
run has no chat at all.

## Facts the design rests on

- **The packet is the one text every host gives the model at each step**, and `next` prints it again. A resumed stage
  already gets the owner's words this way: `_answered_lines` in
  [shiploop_navigator.py](../skills/shiploop/scripts/shiploop_navigator.py) quotes `RUN/decisions/<action>.md` as the
  required block `answered`, which every head prints. Owner notes are the same kind of input.
- **The trace is evidence, not state.** An append can fail without failing the command, the trace stops growing at
  32 MB, and nothing resumes from it (`record` in [shiploop_trace.py](../skills/shiploop/scripts/shiploop_trace.py)).
- **state.md is the authority.** The verbs that move the cursor save it under the run lock. A key the validator does
  not know makes a run unloadable (`_validate_current_state`), but optional keys exist (`status_reason`,
  `chain_bindings`, `delegation_hold`).
- **`RUN/notes/` belongs to the model.** The context index calls it "your notes": the model's pass logs and its
  discovery and research notes.
- **The planning heads have little room.** An active packet over 16,000 characters prints a head. The head always
  carries its required blocks (tiers P0 and P1). It adds the lookups, the chrome and the quoted files only while the
  print stays at or under 20,000 characters, because Grok drops the middle of a longer print. A required notes block
  can take what the optional blocks free up. Measured room on the two-item fixture of
  `test/shiploop-head-order.test.py` at the normal install (83-character run directory, 96-character CLI path), worst
  row per stage ([head-room.py](shiploop-owner-notes-evidence/head-room.py),
  [head-room.txt](shiploop-owner-notes-evidence/head-room.txt)):

  | Stage | Room for notes in the head (characters) |
  |---|---|
  | plan | 240 |
  | step-plan | 1,715 |
  | implement | 3,151 |
  | test | 4,541 |
  | every other stage | at least 5,123 |

  At a live run's 163-character run directory, the plan head is already 20,160 characters before any note, 160 past
  the cut. That gap exists today (follow-up F1).

## Terms

- **note**: one thing the owner wrote, `N1`, `N2`, and so on.
- **shown**: the note's full text was printed to the model while an action was current, in that action's packet or in
  a held callback.
- **held callback**: a `complete` that ShipLoop refuses once, because a note the model has not been shown is waiting.
- **delivered**: ShipLoop accepted a step whose packet showed the note. After that, packets only list the note.

Lifecycle: written → shown (by the packet, or by a held callback) → delivered (an accepted `complete` whose packet
showed it) → listed (one lookup line in later packets).

## Decisions

### D1. Where a note lives

| Option | For | Against |
|---|---|---|
| a. a `note` line in `RUN/trace.jsonl` | one file; lock-free append | the trace may lose a line by design (a failed append, the 32 MB cap); every packet render would parse a multi-megabyte JSONL; nothing may resume from the trace |
| b. inside `RUN/state.md` | it is the authority | `note` would take the run lock and race the model's `complete`; the owner's free text would go through every state read and validation |
| c. **`RUN/owner-notes/N<k>.md`, one file per note, with the delivery record in state.md** | each note is written once and never edited; no run lock (the file is created exclusively); a person can read it; the authority still decides delivery | one new directory and one optional state key |
| d. `RUN/notes/owner/` | the brief suggested it | `notes/` is where the model writes; the owner's words should not sit there |

**Recommend c.** It needs three things:

- `owner-notes/N<k>.md`: a ShipLoop record holding the id, the time it was written and the text. Mode 0600. At most
  8 KB; a longer note is refused with "put the detail in a repo file and name it in the note".
- `owner-notes/shown.json`: written by the script. It records which notes the current action's prints showed in
  full, kept apart for the packet and for a held callback.
- An optional state key `owner_notes`, shaped `{"N1": "<action that delivered it>"}`. It is set in the same save that
  accepts the `complete`.

### D2. When the model sees a note

- a. **The next packet only.** A note written in the middle of a step waits until that step is accepted and committed.
  The step after it sees the note.
- b. **The next packet, plus a held callback (recommend).** If the model runs `complete` while a note it has not been
  shown is waiting, ShipLoop refuses that callback once and prints the note. If the note is about the step, the model
  changes the step. Then it runs the same callback again, which is never held twice for the same note.

b costs one extra callback for each note that arrives during a step. It is the only option where a note about the step
in progress arrives before that step is committed. It also gets the full text to the plan stage, whose head has no room
for it. The trace counts a held callback as held, not as refused. A `--check-only` run prints the waiting notes too, and
counts as showing them.

### D3. When a note counts as delivered

The script decides; the model never marks anything. **A note is delivered when ShipLoop accepts a `complete` for an
action whose packet showed the note in full.**

- A held callback shows the note but does not deliver it. So a note written during step X is shown when X's callback
  is held, quoted again by the next packet (which the model reads after a context clear), and delivered when that next
  step is accepted.
- A note that a head could only name by its file is not delivered either.
- Every failure is safe. A lost `shown.json`, a refused save or a packet cut short leaves the note undelivered, so it is
  quoted again.

After delivery, the note's full text no longer goes into packets. Each later packet carries one lookup line listing the
delivered notes, so a later stage can read one again.

Where notes do not go:

- **Improve packets.** They stay "run /improve, then call done". A note written during an Improve stage reaches the
  producer packet that follows it.
- **Paused and blocked runs.** The note waits for the packet after `resume`. On a blocked run, `note` says the question
  still needs `resume --answer`.
- **Done and halted runs.** `note` refuses there, because no step would read the note.

### D4. How notes fit the packet bounds

The notes block is required (tier P1) and comes right after `answered`. That keeps the owner's words together, ahead
of the stage's own inputs and the result template.

- **The file and a whole print** quote every undelivered note. Each note is quoted up to 1,200 characters and the block
  up to 6,000; past either limit, the note is named by its file instead.
- **A head** quotes notes oldest first while it stays within the limit (the optional blocks give way first, as they
  already do), and names the rest by file. Its smallest form is a single line of about 200 characters, which fits the
  240 the plan head has.
- **The hooks are protected.** Hooks read two strings in a print: the run marker `SHIPLOOP-RUN run=` and the end line
  `=== end ShipLoop print ===`. The renderer breaks both if they appear inside a quoted note, and every line of a note
  is indented.

### D5. What trace.html shows, and whether the page can send a note

The page gets an **Owner notes** panel under Now. For each note it shows the text (screened for credentials like
packet text), when it was written (in the viewer's local time) and its state: waiting for a packet; shown in the
packet or a held callback of action X; or delivered by step #n. It also says whether that step's summary cites the
note's id. The digest gets one line (`Notes: 3 · N1 delivered #12 (cited) · N2 shown · N3 waiting`), and `--json`
gets the whole list.

The page is a static file opened from disk, so it cannot write a file itself. The options:

- a. **A composer that builds the command (recommend).** A text box, the exact
  `python3 <CLI> note --run-dir <RUN> --text '…'` command with shell quoting, and a Copy button. It works on every host
  and needs nothing running.
- b. `shiploop trace --serve`, a localhost server with a per-run token that accepts a POST. That means a long-running
  process the hooks never see, a port, and cross-site protection. Not now.
- c. A claude.ai artifact whose shared database the run polls. That ties ShipLoop to one host. No.

### Later, not in this change

- **Standing notes** (`note --standing`, quoted in every packet until withdrawn). The plan head has no room for a block
  that never leaves.
- **Chat feedback becomes a note.** This needs a SKILL.md line such as "Feedback the user gives during a run: record it
  with `note` so later packets carry it." The card is at 30,488 of its 30,500 bytes, so it needs a trim first.

## The text packets would add

Block `owner-notes` (tier P1, after `answered`; in the file, in a whole print, and in a head while it fits):

```text
Owner notes (the run owner wrote these during the run; verbatim, oldest first):
    N2 21:04Z  Use the existing date helper in src/util/dates.ts; do not add a date library.
    N3 21:10Z  The board must also work at phone width.
Act on each where it applies to this stage; the summary says, by id, what you did or which later stage it is for.
Notes do not change the callback, the result template or ShipLoop's checks; if one conflicts with them, the summary
says so.
```

In a head with room for only some notes, the quoted ones are followed by:

```text
    N4, N5 are not printed here for room: read RUN/owner-notes/N4.md and RUN/owner-notes/N5.md before acting.
```

In a head with room for none (the smallest form):

```text
Owner notes N2 to N5 (4 notes, 1,940 characters) are not printed here for room: read each RUN/owner-notes/N<id>.md before acting; the summary says, by id, what you did about each.
```

Block `owner-notes-delivered` (tier lookup, after `builds-on`; in the file, and in heads with room):

```text
Owner notes already delivered: N1 (step 12), N2 (step 14), in RUN/owner-notes/; read one again when this stage's work touches it.
```

A held callback (D2 b; on stderr, exit 2, the state unchanged):

```text
ShipLoop held this callback: the owner wrote a note after this action's packet was printed.
    N3 21:10Z  The board must also work at phone width.
If it changes this step's work, change the work and the result first. Then run the same callback again; it is not held
twice for the same note. The summary says, by id, what you did about it.
```

What `note` prints to the owner:

```text
Owner note N3 written: RUN/owner-notes/N3.md. The run is at W2 implement (action ab12cd…); the model sees the note
at its next ShipLoop callback or `next`.
```

## What the build would change

- `shiploop_owner_notes.py` (new): writing, listing, the undelivered set, the shown record and the block lines. The
  `note` verb in `shiploop_protocol.py`.
- `shiploop_navigator.py`: the two blocks; head selection that shrinks the notes block to fit; the hold in `complete`;
  delivery in the accepted save; the optional `owner_notes` key.
- `shiploop_trace.py` and the page: the notes model, the digest line, the panel and the composer.
- `references/status-display.md` for the owner's usage, and an entry in the context-index map if its budget allows.
- Tests through the real CLI:
  - a note quoted by `next` and delivered by an accepted `complete`;
  - a note written during a step holds the callback once and is quoted again by the next packet;
  - in the plan stage, the smallest form keeps the head at or under 20,000 characters at the normal install, with
    every required token;
  - the run marker and the end line cannot be planted through a note;
  - done, halted and retired runs refuse a note and write nothing;
  - the page panel and the composer.

  The head-order tier table gains `owner-notes`.
- A change note `changes/shiploop/owner-notes.md` (bump: minor), a journal entry, and the quick tier.

Write boundaries. Shiploop 1.13.1 (`a677b55d`, which this design is rebased on) changed `shiploop_protocol.py` and
`shiploop_trace.py`:

- routed verbs are no longer traced;
- `protocol.main` keeps a `_DEPTH` counter, and only the outermost call records the command and resets
  `shiploop_trace.ACTIVE`;
- packet lines are written only while `ACTIVE` is set, that is, while a traced command runs on a run that loaded as
  current.

The build keeps to these rules:

- `note` is a protocol verb, so it is recorded once by the outermost `main` and sets nothing up on a run that is not
  current. A note on a retired or unloadable run, or with bad arguments, leaves the run exactly as it was.
- The note's packet-quote ids ride on the packet line, so they are recorded only while `ACTIVE` is set, like every
  packet line.
- `shown.json` is written only by `emit`, beside the packet file it already writes, and by a held callback. A held
  callback writes nothing else.
- Every other refusal, every read-only view, and every routed verb (chain, lint, red-check, backchain-check) leaves the
  run byte-identical. The shiploop-chain, backchain-check, cross-run and navigator-contract suites pin this.

## Follow-ups found while measuring

- **F1.** At a 163-character run directory, the plan head prints 20,160 characters with no note at all: 160 past
  Grok's cut, so Grok drops the middle of it. The head-order tests check printed length only at the 83-character
  install. Not part of this change.
