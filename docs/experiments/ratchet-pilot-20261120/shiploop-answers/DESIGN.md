# A candidate ShipLoop change: the requester's answer to a default reaches the specification before the plan is made

Status: a candidate on its own branch. Not on `main`, not released. The owner decides whether it is accepted.

Owner's word, 2026-11-22 07:37, to "Release the list now, and then build the answer route as a candidate?": "Yes,
both". The list is released (ShipLoop 2.6.0). This is the second half.

How this note came to be: sections 1 to 3 were first written at 07:50 on 2026-11-22, before any code
(`review/DESIGN-as-reviewed.md` is that text). The latest Sol at maximum effort reviewed it (08:01; question and
answer word for word in `review/`): "Change first", sixteen findings. Section 4 lists each finding and what was done
with it. Sections 2 and 3 are the design as it stands after the review. No code existed when this was written.

## 1. What is wrong today, measured

ShipLoop 2.6.0 makes the spec stage record each choice it made where the request does not say (`defaults`), and
shows the list to the requester. It does nothing with what the requester then says.

- With the requester's answer written into the specification, builds pass 8 of 8 held-out checks three times of
  three; without it, 3 of 8 three times (the Ratchet program, on the `ticket-due-times` case).
- A one-sentence answer sent as a plain owner note right after the spec changed the build in 2 deliveries of 4, was
  confirmed in 1, and was ignored in 1, where the script recorded the note as delivered all the same.
- With nobody answering, the wrong choice stands: 9 of 20 Sol deliveries on file chose the start-up answer the owner
  ruled wrong (4 of 8 with the list, 5 of 12 before it), and each fails the same five held-out checks.
- The mechanisms as they are (`route-map.md`, read from the code): an owner note is free text bound to no
  requirement; a step that showed it in its packet delivers it when accepted, whatever the step did; no gate reads
  what changed. Planning stages after the spec may reword a requirement (only a dropped ID is refused). No route
  reruns the spec for a note. The stage after the spec, `test-strategy`, is where the list is first shown.

## 2. The change

One sentence: the requester can answer a listed default by its number; if the answer is there when the
`test-strategy` stage submits its result, that stage must rewrite the requirement and prove it to the script; an
answer that comes later is acknowledged, left out of the stages' instructions, and shown in the done packet and the
report as held for a new run.

ShipLoop stays unattended: nothing asks, nothing waits, no stage pauses, no loop gets a limit, and an absent answer
leaves the recorded default in force.

### 2.1 The selector, and recording an answer

Each row of the list is shown with a selector, `<row>@<first eight hex digits of the spec result's action>`, for
example `3@18808b6d`. The number alone is not enough: a planning reconcile can replace the specification, and row 3
of the new list may be another decision.

    shiploop note --run-dir RUN --default 3@18808b6d --text "<the requester's words>"      (or --file)

It is an owner note with one more field, read and validated by the one note reader, so there is one inbox:

    {id, written_at, text, default: {row, spec_action, requirement, question, recorded, entry_sha256}}

`requirement`, `question` and `recorded` (the default as the spec recorded it) are copied from the row;
`entry_sha256` is the digest of the requirement's entry in `KNOWLEDGE/spec.md`, whitespace-normalised, when the
note is written.

Refused, with nothing written: the refusals a note already has; no accepted spec result with a list; a selector
whose action is not the current spec result ("the list changed since that packet"); a row outside the list or a row
whose stored shape is not the five texts; a requirement with no current entry. On a finished run the refusal adds
the done packet's sentence about a new run.

The acknowledgment says three things: the note's id; that it is applied only if it is there when the
`test-strategy` stage next submits its result, and is otherwise held for a new run; and, on a blocked run, that it
does not answer the question the run is waiting on (`resume --answer` does).

### 2.2 In time, late, replaced, superseded

One read of the inbox is made for each fresh admission of a result, and the hold, the gate and the settlement all
use that one set.

- **In time:** a bound note, not yet applied, whose `spec_action` is the current spec result, present at the read
  made when the `test-strategy` producer's `done` result is checked or completed. Of several in-time notes for the
  same row the latest is the answer; the earlier ones are **replaced**.
- **Applied:** the current accepted `test-strategy` result holds an `answers` row for the note. This is read from
  the accepted result (through the projection that a reconcile already narrows), never from the notes' delivery
  record: a note first seen through a held callback is not delivered by that step, and a delivered note need not
  have been applied.
- **Late:** a bound note for the current spec result that was not there at that read: one that arrives during the
  stage's review, at `plan`, or at any later stage.
- **Superseded:** a bound note whose `spec_action` is no longer the current spec result.

If a reconcile reopens `test-strategy` against the same spec result, that stage runs again and every bound note
present then is in time again; nothing carries an old result's proof over.

### 2.3 What the stage is told

In the `test-strategy` packet, when in-time answers exist, a short required block right after the owner notes:

    Answers to defaults (each is the user's decision; apply it before this stage's own work):
      N3 answers 3@18808b6d (R-3). Its words are in the owner notes above; its record is RUN/owner-notes/N3.md.
    For each: rewrite the requirement's entry in KNOWLEDGE/spec.md so that it states what the requester wants and
    nothing the answer replaces; keep the ID and say in the entry that the requester decided it. This stage's own
    output follows the rewritten entry. Return `answers`: one {note, requirement, line} for each, `line` being one
    line of the rewritten entry, word for word. ShipLoop refuses done while an entry reads as it did when its
    answer was written.

The block names notes by id and file and repeats no question or default text, so its size does not grow with
theirs. An in-time note stays in the ordinary owner-notes quote. If it arrived after the packet printed, the
existing hold of the callback prints it, and for a bound note the hold's text carries the same binding and duty.
The owner-notes footer, which says notes do not change ShipLoop's checks, says so for unbound notes only.

A late, replaced or superseded bound note is kept out of the owner-notes quote and out of the hold: no stage is told
to act on it, and it holds no callback. Later packets carry one status line, with the delivered notes:
`Answers held for a new run: N4 (3@18808b6d, R-3); carry on with the accepted plan.` Nothing promises that a later
stage leaves the requirement alone; nothing checks it today either.

### 2.4 The gate

One validator, at the three places the `defaults` gate already sits, with these inputs:

- **`check` and `complete` of the `test-strategy` producer** (in `_evaluate`): the expected set is the in-time
  answers of this admission's inbox read.
- **Before an earlier check's yes is reused** (in `dispatch`): the same check runs again; a yes given before a note
  arrived says nothing about it.
- **The import of the stage's review**: the expected set is the note ids of the `answers` the producer's parked
  result carries. No new note is taken in here: a note that arrives while the review runs is late. This keeps a
  finished review from meeting a gate it has no pass left to satisfy.

Done is refused unless the result's `answers` rows are exactly the expected notes, one row each and no other row,
and for each row:

1. `requirement` is the requirement the note is bound to, and its entry exists and is not retired;
2. the entry's normalised digest differs from the note's `entry_sha256`;
3. `line` is not empty and is, with whitespace normalised, one physical line of that entry.

Each refusal names the note, the requirement and what is missing; at a review's import it names the result path and
the callback with `--final-result`, as the other import gates do. `answers` is an optional, done-only result key
allowed at `test-strategy`, stored loose (any list of text maps loads, and so does a result without it), so a run
saved before this change, a run parked in a review, and a run long past planning all load. The exact checks live at
the gates only.

What the gate shows is narrow, and is said so: the entry changed and the result quotes a line of it. It does not
show that the entry now says what the requester asked.

### 2.5 Where the requester sees it

- The list's block in the `test-strategy` packet shows each row's selector and one more sentence for the host: if
  the user answers a default, record it at once with the note command and `--default <selector>`; it is applied if
  it is recorded before this stage submits its result, and held for a new run otherwise.
- The done packet and the report mark each answered row: `answered by the requester (N3): "<words>"; applied at
  test-strategy: <line>`; or `answered by the requester (N4) after test-strategy had submitted its result:
  "<words>"; held for a new run`; replaced and superseded answers are listed under the table with the row they were
  written for. A held answer gets the existing sentence about a new run. The mark "changed after the spec stage"
  stays for a row a stage rewrote with no answer.
- The report is written when the run ends; a note that lands after that is refused by the note command, as today.

### 2.6 Not built, and why

- **A window that reaches the `plan` stage.** `prepare` and `step-plan` read the accepted strategy's `test_layers`
  and `targets`; an answer applied at `plan` would leave them planned for the old requirement, with no route to
  refresh them. The price is a short window: the time the `test-strategy` producer takes.
- **Applying a held answer in the same run**, and **starting the new run for it.** No delivery has shown either is
  needed; the measured effect is for answers before the build.
- **Judging whether the rewritten entry says what the requester asked.** A script cannot.
- **Confirming a default.** An answer that agrees with the default makes the stage say in the entry that the
  requester decided it. That passes the gate and is a confirmation, not a correction; the evaluation counts it so.

## 3. Known ways round (for the loophole table, in the same commit, each with a fixture that shows it)

| Way round | What happens |
| --- | --- |
| The entry's heading is renamed, or a line "the requester decided this" is appended, and the old clause stays; `line` quotes the appended line or the old clause | Passes. The stage's review and the report, which shows the words and the line side by side, are the only checks |
| The named requirement is rewritten and another requirement still states the old behaviour | Passes. Not looked for |
| The host never records the user's reply as an answer | Nothing happens; the reply is whatever the host makes of it |
| The answer arrives after `test-strategy` has submitted its result | Held for a new run; said in the acknowledgment, the packets' status line, the done packet and the report |
| A later stage rewords the requirement of a held answer on its own | Not prevented, as today; the list's "changed after the spec stage" mark shows it |

## 4. The review, and what it changed

| # | Finding (Sol 6.2 at max effort, verified here where marked) | Decision |
| --- | --- | --- |
| 1 | An answer taken in at a review's import can reach a review that has no pass left | Intake closes when the producer submits; the import only revalidates the producer's rows (2.2, 2.4) |
| 2 | A held note is not delivered by its step, and a delivered note need not be applied (verified in `owner_notes.to_hold`, `mark_held`, `deliver`) | Application is read from the accepted result, not the delivery record; the hold's text carries the binding (2.2, 2.3) |
| 3 | The three gate sites take one validator with different inputs; rows must match the expected ids exactly | As written in 2.4 |
| 4 | The note command takes no run lock, so a note can land between the hold, the gate and the save | One inbox read per admission; the acknowledgment states the cutoff (2.1, 2.2) |
| 5 | A row number can bind to another decision after a reconcile | The selector carries the spec result's action; refusals for a changed list, a loose row, a missing entry (2.1) |
| 6 | A reconcile invalidates a result's proof and leaves the edit on disk | Superseded answers are shown, never transferred; a reopened stage takes answers afresh (2.2) |
| 7 | The new result key must load loose, and a run parked in a review is the fixture that matters | 2.4, and a test for it |
| 8 | A required block that repeats question and default text can outgrow the head | The block names ids and files only (2.3) |
| 9 | The window should stop at `test-strategy`: later planning reads its structured records (verified: `_test_strategy_result`, `_check_submitted_layers`) | Adopted (2.2, 2.6) |
| 10 | Keep one note command and one inbox; the common reader must return the binding; the footer and the hold's text must agree with it | Adopted (2.1, 2.3) |
| 11 | Keep `line` as evidence and narrow the claim; a renamed heading or an appended line passes | Adopted; the loophole rows say so (2.4, 3) |
| 12 | A late answer needs an acknowledgment and a disposition, and must stay out of the actionable quote and the hold | Adopted (2.3, 2.5) |
| 13 | The feature can stay unattended; `note --default` must not read as answering a blocked question | Adopted (2.1) |
| 14 | The test matrix around the transitions | Section 5 |
| 15 | Five of six is a smoke signal (16 percent by chance); register a paired correction, and count confirmations apart | Section 5, with what could not be done as proposed |
| 16 | Not verifiable from the export: reuse of a yes at this stage, a live review whose hand-off changes, full packet bounds | Left to the build's tests |

## 5. How it will be judged (fixed before any delivery of the candidate runs)

**Tests with no model, through the real CLI.** An in-time answer is shown, refused when unanswered, refused when the
entry is unchanged, refused when `line` is not in the entry, refused when an extra row claims another note, and
accepted when all hold. `check`, then a yes, then a note, then `complete` with the same result: held once, then
refused, then accepted after the rewrite. A `check` that first reveals a note. A hold whose record cannot be
written. A producer that is paused or blocked and resumes. A parked review: import of the unchanged result, of a
replacement that drops a row, and of one whose line the review edited away; a note that arrives during the review
is late. A reconcile that keeps the spec and one that replaces it. A late answer causes no hold and no refusal and
is shown as held in the status line, the done packet and the report. The note refusals. A run with no answers and
closed standard input behaves as 2.6.0. A saved run without the key, and one parked in a review, load. Packet
sizes stay inside their budgets. Each loophole row has a fixture that shows what passes.

**Real deliveries, on the two drivers the owner uses to examine how a run went** (owner, 2026-11-22: "sonnet 5.5
med and sol 6.2 med are the drivers that are the ones we will use to examine how the performance went"): Codex with
gpt-6.2-sol at medium, and Claude Code with claude-sonnet-5-5 at medium. Case `ticket-due-times`, built from the
candidate's commit through the experiment's launcher, each delivery with a stand-in requester.

The review asked for matched pairs forked from one accepted specification. The harness cannot continue two runs
from one saved point, so the comparison is by condition, and that limit is stated. Every delivery runs alike until
its list is printed. The stand-in then answers the row about how existing tickets get their due times (the start-up
row), always, with the owner's ruling, through the printed selector. By what that row says, an answered delivery
is a **correction** (the row makes the operator run a command first, or refuses to start) or a **confirmation** (it
already fills the due times in at start). A delivery whose list has no start-up row gets no answer and is counted
apart.

Planned: six deliveries on Sol and three on Sonnet, in batches, with no test tier beside them. Corrections are
expected in about four Sol deliveries of ten and rarely on Sonnet (neither of its two deliveries with the list chose
the refusal).

- The control is on file: of the Sol deliveries whose specification chose the refusal and got no answer, none
  passes the five checks that start the service on a file without due times (d3, k2, k3 and five without the list:
  0 of 8).
- R1, both drivers. Every answered delivery records its proof: the accepted `test-strategy` result holds the
  `answers` row, and no delivery is stopped at the gate (a refusal the session recovers from is counted and is not
  a failure).
- R2, corrections. In every correction the rewritten requirement no longer makes the operator run a command first
  and no longer refuses to start (read by hand, by a reader not told how the checks came out).
- R3, corrections. Every correction passes those five checks. Two corrections are the least that is read; Sol
  deliveries are added, to a ceiling of twelve, until there are three. A correction on Sonnet is read by the same
  rule and reported apart.
- R4, both drivers: how the run went, beside the same driver's deliveries of the released product on file. For each
  driver: the five verdicts, the eight checks, minutes, output tokens, the cost where the host reports one, the
  seconds of `test-strategy` (the stage that applies the answer), and refused commands. One rule: no verdict or
  check fails for a cause that is the route's. Each failure is read from the run; one whose cause is known on the
  released product (a session that starts ShipLoop twice, for one) is reported and not counted against the route.
  The figures themselves are described, each with the archive's range beside it.
- Described: one Sol delivery whose answer is sent after the stage has submitted, to see the acknowledgment, the
  status line, the done packet and the report say "held" and the build stay as planned; and the plain-note figures
  on file (2 of 4 changed) beside these.
- If R1, R2, R3 or R4's rule fails, the candidate is reported as it stands and nothing more is built on it without
  the owner.

## 6. The review of the code, and what was done with it (written 2026-11-22, 10:18, before any delivery)

The latest Sol at maximum effort read the built code (the first commit's tree) on a neutral copy: "Fix first", 22
findings (`review/sol-code-question.md`, `review/sol-code-answer.md`, word for word). Each was sorted here. The rule
used: fix what a normal run can meet or what makes a display or a refusal say something untrue; record as a known
limit what only an unusual file layout, a race at the instant a run ends, or an unrealistic size can trigger.

| # | Finding | Decision |
| --- | --- | --- |
| 1 | A review's import can lose an owed answer when the note's file is gone or unreadable | Fixed: the import takes the owed ids from the parked result itself. A row whose note can no longer be read must be kept, with its line still in the entry; it is not a dead end (the builder's point: refusing outright would strand an unattended run) |
| 2 | An entry's span can hold a second requirement written as a list item; editing only that one passes as proof | Recorded in the loophole table with a fixture; the shared entry parser is not changed. In the ten specifications on file every requirement is a heading and none is laid out that way |
| 3 | A note published at the instant a run ends can be acknowledged and miss the saved report | Recorded as a limit in the reference text |
| 4 | The producer's replay of its parked result is refused after the review edited the quoted line | Fixed: an exact replay is recognised before the hold and the gate |
| 5 | Dozens of answers outgrow the result template's room | Recorded: an answer set is at most one per row of the list; no cap |
| 6 | A packet can quote one note and ask for proof of another (two reads of the inbox) | Fixed: one read per packet |
| 7 | The review may never see the requester's words when a hold was their only delivery | Fixed: the hand-off names the note files and asks for the comparison |
| 8 | A later stage can be told to reread a superseded or replaced answer | Fixed: bound notes are left out of the delivered-notes lookup |
| 9 | Displays misstate dispositions (no status in the parked review; "the accepted plan" before one exists; halted and superseded cases) | Fixed |
| 10 | The summary explains a mark no row carries, and tells the host every row is a choice made for the user | Fixed |
| 11 | The acknowledgment on a blocked run can name a resume flag that is refused | Fixed, for plain notes too |
| 12 | Some refusals omit the note, the requirement or the note's file | Fixed |
| 13 | The binding's ID check is ASCII-only; two spec results could share eight hex digits | First fixed; second recorded |
| 14 | The stand-in requester can answer the wrong row | Fixed: rows are scored on the start-up decision, a tie sends nothing, and a self-check over the ten saved lists picks the start-up row in each of the nine due-times lists and nothing in `hello`'s |
| 15 | The producer's paths share one read as designed | No change (a confirmation) |
| 16 | Stored rows with whitespace at the edges would not reload | Fixed: stored texts are kept as they are |
| 17 to 21 | Tests that assert less than their names, and cases not covered | Tests added with the fixes |
| 22 | What the reviewer could not verify from the export (reuse of a yes at this stage, a live review, hosts) | Left to the suites and to the deliveries |

## 7. The round on both drivers: thirteen real deliveries (2026-11-22, 10:46 to 11:45)

Built from the candidate's second commit (`3577bb050abc23c73875347e9d3be25047e3a60e`) through the experiment's
launcher, case `ticket-due-times`: ten deliveries on Codex with gpt-6.2-sol at medium (`a1` to `a9`, and `c1`) and
three on Claude Code with claude-sonnet-5-5 at medium (`b1` to `b3`). No test tier ran beside them. They were read by
`read_answers.py` (`evidence/round-1/answers.txt` and `answers.json`), `figures.py` (`figures.txt`) and `windows.py`
(`windows.txt`). Two fresh Sonnet readers judged the rewritten requirements from the row, the answer and the
requirement before and after, and were not told how any check came out (`reader-question.md`; `reader-answer.md` for
a2 to a6, b1 and b3; `reader-answer-2.md` for a7 to a9; what they read is in `export/`).

**Every delivery passes:** 13 of 13 pass the five verdicts and 8 of 8 held-out checks, the five start-up checks
among them.

| | Sol (10) | Sonnet (3) |
| --- | --- | --- |
| Answered through the selector, and applied | a2, a3, a4, a5, a6, a7, a8, a9 | b1, b3 |
| of these, corrections (the row made the operator run a command first and refused to start) | a4, a5, a7 | none |
| of these, confirmations (the row already filled the due times in at a start) | a2, a3, a6, a8, a9 | b1, b3 |
| Nothing sent, counted apart | a1: its list of two rows has no start-up row | b2: two of its four rows tie on the start-up decision |
| Answer sent late on purpose | c1 | |

Which is a correction was read by the readers from the row alone (their Q1), and agrees with the reading made here.

### Against what section 5 registered

- **R1, met: 10 of 10.** Each answered delivery's accepted `test-strategy` result holds its `answers` row. No
  delivery was stopped at the gate, and no command was refused for a reason naming `answers`, in any of the
  thirteen. The stand-in wrote each answer within two seconds of the list being printed, so each arrived after the
  packet: in all ten the stage's callback was held once to show it, and in five (a3, a5, a9, b1, b3) that hold was
  the only print of the answer; the stage's saved packet carries the block in the other five.
- **R2, met as registered, with one thing to say.** In each of the three corrections the reader finds that the row
  made the operator run a command first and refused to start, and that the rewritten requirement makes the operator
  run nothing (Q2a: no, three of three) and states no refusal (Q2b). a5 says outright that missing deadlines do not
  cause a refusal. a4 and a7 say the start fills the due times in, saves and serves, and say nothing of refusing:
  they leave out the requester's last sentence, "It never refuses to start because due times are missing."
- **R3, met: three corrections, and each passes the five start-up checks.** The control on file is 0 of 8 Sol
  deliveries that chose the refusal and got no answer. The third correction came in the three deliveries added under
  the rule (a7 to a9); ten Sol deliveries were run, against a ceiling of twelve.
- **R4, met: no verdict and no check failed in any delivery,** so no failure had to be traced. The figures, beside
  the same driver's deliveries of the product with the list that are on file (eight on Sol and two on Sonnet,
  `../shiploop-defaults/evidence/`):

| | Sol, this round (10) | Sol, on file (8) | Sonnet, this round (3) | Sonnet, on file (2) |
| --- | --- | --- | --- | --- |
| The five start-up checks | 10 pass | 5 pass; the 3 that chose the refusal fail | 3 pass | 2 pass |
| Minutes | 11.6 to 18.9, median 16.0 | 12.7 to 18.4 | 23.7 to 25.7 | 27.2 (and 43.6 with a test tier beside it) |
| Output tokens | 25,713 to 35,244 | 26,904 to 39,624 | 177,667 to 194,450 | 195,151 and 209,968 |
| Cost | the host reports none | the host reports none | $7.90 to $9.16 | $9.82 and $10.58 |
| Seconds of `test-strategy` | 46 to 74 with an answer, median 55; 24 in a1, without one | 23 to 54, median 38.5 | 87 and 100 with an answer; 88 in b2, without one | 94 (one figure) |
| Commands that ended non-zero with an error text, each recovered in the session | 2 to 8, the one held callback of an answered delivery among them | 2 and 7 (the two counted) | 8 to 16, the same | 13 (the one counted) |

  An answer in time costs the stage that applies it about a quarter of a minute on Sol and nothing that shows on
  Sonnet. Time, tokens and cost of a whole delivery are as on file. What else was refused at
  `test-strategy` (in a2, a3, a6, b1 and the unanswered b2) is the `test_layers` check that the released product
  already has.

### The late answer (c1): described, and not what was expected

Section 5 expected the acknowledgment, the status line, the done packet and the report to say "held", and the build
to stay as planned. The first two happened. The stand-in wrote the answer one second after the stage's result was
accepted; the acknowledgment said it was held for a new run, and the `plan` packet carried "Answers held for a new
run: N1 (3@2d3fc034, R-3); nothing in this run applies it."

The build did not stay as planned. The row had already chosen to fill the due times in at a start, "including
during flag-off preparation"; the requester's words tie it to a start with `DUE_TIMES` on. The `plan` stage's
producer read the note and returned `reconcile` to `spec`: "Reopen R-3 to make flag-on startup the migration trigger
and align the strategy and plan with owner note N1." The second specification says "R-3 incorporates owner note N1",
its list has two rows and no start-up row, and the delivery passes 8 of 8 in 16.2 minutes.

So the product's own way back, a planning reconcile, applied a held answer that the packet had just said nothing in
the run applies. One delivery, at the earliest late moment, while planning was still open. Two things follow:

- **The display said something untrue.** After the reconcile the note stands as superseded, and the done packet and
  the report said "which a reconcile replaced; not applied". The script has no proof either way; the requirement did
  adopt the answer. The wording is corrected in the commit that follows this record: a superseded answer is shown
  as "not checked against the specification that replaced it".
- **What a stage does with a held answer during the build is not known.** There the plan is bound and no reconcile
  is open. Section 8 registers deliveries that send the answer then.

### What else the round shows

- **The window is about a minute, and under half a minute when nothing holds the stage.** From the list being
  printed to the accepted `test-strategy` result: 24 and 29 seconds in the two Sol deliveries where no answer came
  in time (a1, c1), and 46 to 74 with one; on Sonnet 88 without and 87 to 100 with. Counted to the accepted plan it
  is 49 to 134 seconds on Sol and 147 to 165 on Sonnet (`windows.txt`), so a window that reached the plan would be
  about two minutes. The stand-in answers within two seconds; a person reading a list cannot be expected to. Section
  2.6 names this price. The round measures it.
- **The proof is as narrow as section 2.4 says, and these builds did not need more.** Of the ten rewritten
  requirements, five state the whole answer (reader's Q3 "fully": a5, a6, a9, b1, b3) and five leave out the
  sentence that the service never refuses to start (a2, a3, a4, a7, a8). All ten builds start on a file without due
  times, fill them in and never refuse (the five start-up checks).
- **Seven of the ten answers were confirmations.** Of the lists with a start-up row, 3 of 8 on Sol and 0 of 2 on
  Sonnet had chosen the refusal (c1's row, a ninth on Sol, filled the due times in at a start too).
- **Two lists gave the stand-in nothing to answer.** a1's specification filled the due times in at a start by itself
  and did not list that as a choice (each of the nine due-times lists saved before this round has such a row). b2's
  list has two rows on the decision, "when do the production tickets get their due times" and "what happens to
  tickets that still lack one at a start, for example after a roll-back", and the stand-in's rule sends nothing on a
  tie.
- **A gap in the reading.** For b3 the reader script did not find the requirement's text as the spec stage left it
  (`export/b3/before.md` holds "None"), so the reader's Q4 for b3 is "not available". b3 is a confirmation and no
  registered reading rests on it.

## 8. An answer during the build: registered before those deliveries run (2026-11-22, 12:28)

**Why.** For a person the answer comes after the plan is bound (section 7: the window is about a minute). The one
late delivery of round 1 had its answer applied by a planning reconcile, which is open only until the plan is
accepted. What a run does with a held answer once the build has begun has not been seen.

**The deliveries.** Six on Codex with gpt-6.2-sol at medium and one on Claude Code with claude-sonnet-5-5 at medium,
case `ticket-due-times`, built from the commit that carries this section. That commit also carries the corrected
wording for a superseded answer and the stand-in's new mode: `answer-at-implement` sends the requester's words, the
same as in round 1, through the selector of the start-up row of the list as it then stands, when the first
`implement` packet prints. A list with no such row, or with two that tie, gets nothing and is counted apart. No
delivery is added to reach a count.

**What is read for each delivery, from its run:**

1. What the requester is told: the acknowledgment, the status line of the packets that follow, the done packet and
   the report.
2. What the run did with the answer, one of three. **Carried on:** the requirement's entry reads at the end as it
   did when the answer was written, and nothing a stage returned or committed afterwards builds what the answer
   says against the row. **Acted on it:** the entry was rewritten after the answer, or a stage's result or a commit
   after it cites the note or builds what it says. **Stopped:** the run blocked, halted or did not end.
3. Whether the delivery agrees with itself: the five verdicts and the eight held-out checks, and, by reading, whether
   the product's start-up behaviour (the five start-up checks) is what the specification's entry says at the end.

Read apart: deliveries whose row had chosen the refusal or a separate command, where the held answer contradicts
the plan (3 of 8 Sol lists in round 1, so about two of six, and possibly none), and deliveries whose row already
fills the due times in at a start, where it does not.

**No rule passes or fails here.** The design promises nothing about what a stage does with a held answer (2.3:
"Nothing promises that a later stage leaves the requirement alone"). What each outcome will be taken to mean is
fixed now:

- Every delivery carries on and the displays say held: the late path does what the design says. Where the row chose
  the refusal, the delivery is then expected to fail the five start-up checks, as an unanswered one does.
- A stage acts on a held answer during the build: the status line's "nothing in this run applies it" is not true of
  the product and the script holds no proof of what was done. The candidate is reported with that. Whether held
  answers are kept from the stages or given a way back that the script owns is the owner's decision.
- A run stops: reported as a failure of the late path.

Time, tokens and cost are described beside round 1.

## 9. Answers during the build: seven deliveries (2026-11-22, 12:29 to 13:05)

Built from the commit that registered them (`da8689fdf38035603958dbe6606f450c1b605abe`): six on Codex with gpt-6.2-sol at medium (`e1` to `e6`, in
two batches of three) and one on Claude Code with claude-sonnet-5-5 at medium (`f1`). Another session's test tier
was running on the machine for part of the time (load 11 to 15 on 18 cores). In each delivery the stand-in wrote its
answer when the first `implement` packet printed, 116 to 246 seconds after the list was printed on Sol and 423 on
Sonnet (`evidence/round-2/answer-times.txt`). The note command accepted each one and answered "held for a new run".
Read with the extended `read_answers.py` (its block "the held answer"; `evidence/round-2/answers.txt` and
`answers.json`) and by a fresh Sonnet reader given the row, the answer, and the requirement as it read when the
answer was written and at the end (`reader-question.md`, `reader-answer.md`, `export/`).

**Every run carried on: 7 of 7.** This is the first of the three outcomes fixed in section 8.

- **No run stopped.** All seven ended done, with no reconcile and nothing blocked after the answer.
- **No stage acted on the answer.** In five deliveries (e2, e3, e4, e5, e6) the requirement's entry at the end has
  the digest stored with the note when the answer was written. In e1 and f1 the implement stage added one line that
  names tests and files, and the behaviour described is the same. The reader says "nothing" changed five times and
  "evidence lines only" twice. No accepted result after the answer names the note (the reader script's matches in
  e6 and f1 are the product "answering" a request).
- **The requester is told.** The line "Answers held for a new run: N1 (...); nothing in this run applies it." is in
  16 to 23 packets of each run. Each done packet and each report marks the answered row: "Answered by the requester
  (N1) after test-strategy had submitted its result: "..."; held for a new run."
- **The host's last message says so where it matters.** e3: "This release uses an offline backfill before
  activation. ShipLoop recorded the later request for automatic startup backfill for a separate run." e4 says it
  too ("held your later startup clarification for a follow-on run, but the delivered code already does what it
  describes"). The other five last messages do not mention the held answer (`last-messages.txt`).

**The one delivery whose plan the answer contradicts delivers what the requester said they do not want.** e3's row:
"Stop the writer, run the offline backfill, then enable the flag." Its requirement at the end, unchanged: "An
offline command fills missing due fields ... Enabled startup refuses incomplete persisted data." It passes the five
verdicts and fails the five start-up checks (3 of 8), as an unanswered delivery with that choice does (0 of 8 pass
them). The run went on for 6.3 minutes after the answer. One such row came in six Sol lists; a third were expected.

The other six rows already fill the due times in at a start, and their deliveries pass 8 of 8.

**Figures beside round 1.** Sol: 10.7 to 16.8 minutes (11.6 to 18.9), 21,777 to 35,215 output tokens (25,713 to
35,244). `test-strategy` took 24 to 63 seconds with no answer in time, median 40; with one, in round 1, 46 to 74,
median 55. So the "quarter of a minute" of section 7 is a difference of medians inside ranges that overlap. Sonnet,
one delivery with two work items: 35.6 minutes, $10.42, 214,672 output tokens (round 1: 23.7 to 25.7 minutes,
$7.90 to $9.16; on file 27.2 and 43.6 minutes, $9.82 and $10.58).

### Where the candidate stands after both rounds (twenty deliveries)

| When the answer is on file | What happens | Seen |
| --- | --- | --- |
| In time: before `test-strategy` submits, which is 24 to 74 seconds after the list is printed on Sol and 87 to 100 on Sonnet | Applied. The stage rewrites the requirement, the script holds the proof, the build follows | 10 of 10; the 3 corrections pass the five start-up checks (0 of 8 unanswered) |
| Late, while planning is still open (until the plan is accepted, about one more minute) | Held by the script. The plan stage took the product's own way back, a reconcile, and the specification adopted the answer | 1 of 1 (c1); the script does not own this |
| Late, once the build has begun (2 to 7 minutes after the list) | Held. The run finishes as planned and says so. A build planned against the answer stays as planned | 7 of 7 carried on; the 1 contradicted delivery fails the five start-up checks |

- The route does what its design says in every delivery, at no cost that shows.
- It changes what is built only for an answer that arrives within about a minute of the list. The stand-in manages
  that. A person reading the list will not: for a person the candidate records the answer, shows it as held, and
  leaves the delivery as planned.
- Not tested: the new run that a held answer points to (whether a second run with the requester's sentence repairs
  a delivery like e3, and what it costs); a host that relays a person's answer; a list with two rows on one
  decision (b2 of round 1).
- Whether the candidate goes into main is the owner's decision.

## 10. What should a late answer do: two tests, registered before either runs (2026-11-22, 13:32)

**The owner's word, 13:16:** "Not yet", to "Accept the answer route into main as it stands?". The message that put
the question named the next step: send the same answer during the build as a plain owner note, and run a second
ShipLoop run on the wrong delivery with the requester's sentence as the request, to see whether a late answer is
better taken in on the spot or by a new run, and what each costs.

**Why.** Section 9: a late answer through the selector is held, 7 of 7, and a delivery whose plan it contradicts
stays wrong (e3). Two ways already exist for a person's answer and need no new engine code to test. A plain owner
note is shown to the stage in hand; sent during planning it changed the build in 2 deliveries of 4 (F61). The new
run is what the done packet tells the requester to start. Neither has been measured for an answer that arrives
during the build.

### Test A: a plain note during the build

Six deliveries on Codex with gpt-6.2-sol at medium and one on Claude Code with claude-sonnet-5-5 at medium, case
`ticket-due-times`, built from this commit. When the first `implement` packet prints, the stand-in sends a plain
owner note, with no selector, whose words contradict what the list's start-up row decided (`late-notes.json`,
written before any run):

- a row that makes the operator run a separate command first, or refuses to start, gets the owner's ruling: the
  service fills the due times in at a start with `DUE_TIMES` on and never refuses;
- a row that already fills them in at a start gets the opposite wish: an explicit offline command, and a refusal to
  start while a ticket has no due time.

So every delivery is a contradicted one, where section 9 got one in six. The five start-up checks tell which
behaviour was built: they pass for a product that fills at a start and never refuses, and fail for one that refuses
(the control: 0 of 8). The stand-in classifies the row by rule (`requester.py --note-at`; its self-test must agree
with the eighteen rows read so far); a row it cannot classify, a list without a start-up row and a tie get nothing
and are counted apart. No delivery is added to reach a count.

Read for each delivery:

1. **Taken in or not.** By the five start-up checks against the note sent (the owner's ruling is taken in when they
   pass; the opposite wish is taken in when they fail), and by a reader blind to the checks, on the requirement as
   it read when the note was written and at the end: does it state at the end what the note asks?
2. **Whether the delivery agrees with itself.** Its own tests pass in the delivered tree, the five verdicts hold, and
   the requirement at the end describes the behaviour the product has.
3. **What it cost.** Minutes from the note to the end, beside section 9's 6.3 to 10.7 on Sol when the answer was
   held; commands refused after the note; whether the run stopped.
4. **What the requester is told** at the end about the note.

One caution fixed now: a delivery that takes in the opposite wish fails five held-out checks because it obeyed. That
is read as taken in, not as a failed delivery.

What each outcome will be taken to mean:

- Taken in and in step with itself in most deliveries: a late answer can be handed to the stage in hand, and the
  route's late half should do that, with proof, in place of holding it.
- Ignored, or half taken in (the product changes and the requirement or the tests do not, or the reverse): the
  stage in hand is not a safe place for a late answer, and the new run is.
- Runs that stop, or verdicts that fail: the same, more strongly.

### Test B: a new run on a wrong delivery

Four deliveries on disk chose the separate command and the refusal, and their delivered product fails the five
start-up checks: e3 (section 9), k2 and k3 (the round on the tree joined with ShipLoop 2.5.0) and d3 (the list's
first wave). For each, a second ShipLoop run starts in a copy of the delivered project, built from this commit
(`second_run.sh`, which uses the harness's own follow-on route, `run.py --continue-from <that delivery> --prompt`;
the delivery it starts from is not written to). The request is the owner's ruling, word for word (the note `start`
of `late-notes.json`), which is what the done packet tells a requester to do: "start a new run on this project with
a sentence that says what you want instead." The eight checks of `ticket-due-times` grade the result, passed as they
stand in the catalogue. Four second runs on Codex with gpt-6.2-sol at medium; e3's also on Claude Code with
claude-sonnet-5-5 at medium. There is no stand-in: nothing is sent during these runs.

Read for each second run:

1. The eight checks, the five start-up checks above all: each project it starts from fails them.
2. Its minutes and output tokens, beside a first run's (10.7 to 18.9 minutes on Sol in sections 7 and 9).
3. What it changed: the diff against the project it started from, and which requirement entries.
4. What its own list of defaults holds, and what the requester is told at the end.

One limit fixed now: k2, k3 and d3 were delivered by earlier builds of ShipLoop (2.5.0 and 2.4.1, each with the
list). A second run that stumbles on what an earlier build left is reported as that, apart from e3's.

What each outcome will be taken to mean:

- Repaired in all, 8 of 8: the new run the done packet points to is a working answer to a late correction, at the
  price measured.
- Not repaired in some: "held for a new run" is a promise the product does not keep, and the route's late half
  cannot rest on it.

No rule passes or fails in either test. The two prices are put side by side for the owner.

## 11. What a late answer should do: the two tests (2026-11-22, 13:32 to 14:13)

Twelve deliveries, built from the commit that registered them (`fe87f5beac30cc8934da9ea5828503d28abb9796`). Read with the reader extended for
them (`read_answers.py`: its blocks "the late note" and "second run"; `evidence/round-3/answers.txt` and
`answers.json`), by a fresh Sonnet reader blind to the checks (`reader-question.md`, `reader-answer.md`, `export/`),
and, for what a Codex session was given, by `given_to_model.py` (`given-round3.txt`, `given-round1.txt`).

### Test B: a new run repairs the wrong delivery, 5 of 5

| Second run | Started from | Driver | Checks | Minutes | Output tokens | What it changed |
| --- | --- | --- | --- | --- | --- | --- |
| s1 | e3 | Sol | 8 of 8 | 10.8 | 20,738 | 12 files, 176 lines added and 33 removed; 5 lines of source; R-3 and R-5 |
| s2 | k2 | Sol | 8 of 8 | 11.8 | 23,064 | 12 files, 170 and 57; 28 lines of source; R-3 |
| s3 | k3 | Sol | 8 of 8 | 13.1 | 27,288 | 12 files, 133 and 74; 4 lines of source; R-3 and R-4; one default listed |
| s4 | d3 | Sol | 8 of 8 | 10.7 | 19,675 | 8 files, 111 and 59; 5 lines of source; R-3 and R-6 |
| t1 | e3 | Sonnet | 8 of 8 | 17.5 | 122,407 ($6.23) | 10 files, 405 and 29; 18 lines of source; R-3 and R-6; two defaults listed |

Each project a second run started from fails the five start-up checks; each second run passes all eight. The
deliveries they started from were left as they were (the launcher compared HEAD and status before and after). The
three that earlier builds of ShipLoop had delivered (k2, k3, d3) gave no trouble. Each last message says what
changed in an operator's words, for example "Operators can start the service directly with a legacy data file."

The price: on Sol 10.7 to 13.1 minutes and 19,675 to 27,288 output tokens, against 10.7 to 18.9 minutes and 21,777
to 38,392 for a first run today; on Sonnet 17.5 minutes and $6.23, against 23.7 to 39.7 minutes and $7.90 to
$12.39. By the meaning fixed in section 10: the new run the done packet points to is a working answer to a late
correction.

### Test A: a plain note during the build

Three of the seven deliveries got a note.

- **Counted apart, four.** n3's list has no start-up row. In n1, n2 and n6 the stand-in could not tell what the row
  had decided, and sent nothing: each row fills the due times in at a start and says so without a filling verb in
  its decided part ("Start the upgraded service with the feature off and verify the data file before enabling").
  The rule agreed with the eighteen rows read before and failed on three of the next four such rows, so the
  opposite wish was sent in no Sol delivery. That is the stand-in's limit, and mine.
- **n4 and n5, Sol: not taken in, 2 of 2.** Each row had chosen an offline command and a refusal; each note was the
  owner's ruling, sent 161 and 159 seconds after the list. Each delivery fails the five start-up checks (3 of 8).
  The requirement is the same at the end as when the note was sent (the reader: "nothing" changed, and it still
  makes the operator run a command and still refuses). No result names the note. The last message tells the
  operator to run the offline backfill and says nothing of a note. The done packet and the report do not mention
  that a note exists. ShipLoop's own record calls the note delivered, by the `test` step whose packet quoted it.
- **m1, Sonnet: taken in fully, 1 of 1.** Its row filled the due times in at the first start; the note was the
  opposite wish, sent 491 seconds after the list. The `document` step of the item in hand recorded it as an open
  item and said why it was not applied there ("W1's accepted spec and tests have start-time backfill ...; W2's plan
  must settle it"). `carry-forward` applied it: it revised R-5 with the superseded text kept, added an architecture
  decision, and added a work item ahead of the next one ("Explicit due backfill command and DUE_TIMES startup
  refusal (owner note N1)"), which took 4.4 minutes. The 148 tests pass and the five verdicts hold; the reader says
  the requirement at the end states the note fully and says why it changed. The five start-up checks fail because
  the delivery obeyed, which section 10 fixed beforehand as taken in. The report names the note 37 times and the
  last message explains the design as the owner note's. The run took 39.7 minutes and $12.39, with three work
  items.

**Why Sol did not take the note in: it was never given the note's words.** Read from each Codex session's own record (`given_to_model.py`; `evidence/round-3/given-round3.txt`): in n4 and n5
the note's words were printed by two commands each, the `check` that showed the note and the next packet, which
quoted it, and they were given to the model in no output. A Sol session runs its commands through scripts of its
own that pass on part of what a command printed: in n4 the two commands printed 8,957 and 29,378 characters inside
one call of the model's, which gave it 8,112; in n5 they printed 37,381 and 30,234 and the model was given 5,564
and 4,626, one of them with the line that announces an owner note and without the note. In round 1 the same words did reach the model in each Sol delivery read (a4, a5,
a7; `evidence/round-1/given-round1.txt`): there ShipLoop held the stage's callback, a refused command whose text
the session did read, in a4 one call later than the command, and then refused `done` until the proof row was
there. In the Sonnet deliveries (m1, b1) every output that held the words was given to the model whole. Neither
record shows a model's own reasoning.

### What the two tests say

1. **A new run is a working answer to a late correction, on both drivers** (5 of 5).
2. **Handing a late answer to the stage in hand works only where it is received.** On Sonnet it was received and
   handled by the product's own steps, `carry-forward` and an added work item, in 4.4 minutes against 17.5 for a
   new run there. On Sol it was not received at all. One delivery on Sonnet, two on Sol.
3. **On Codex with Sol, a text ShipLoop prints is not a text the model reads.** What reached the model in round 1
   was a held callback together with a refusal that names what is missing: ten answers of ten were applied. A
   print in a check's output and a quote in the next packet reached it in neither of two.
4. **For released ShipLoop, apart from this candidate:** a plain owner note sent during the build can be recorded
   as delivered while the model never sees it, and then neither the last message nor the done packet nor the report
   says that a note existed (n4, n5).

### Where this leaves the candidate

- An answer in time is applied and built (section 7). A person is not in time.
- A late answer through the selector is held and said to be held (section 9), and the new run it points to repairs
  the delivery (this section). That is the same new run a requester can start today without the candidate, from
  the list ShipLoop 2.6.0 already prints.
- What would let a person's answer land inside the run is the thing that worked on Sol when it was in time: a
  callback held with a refusal that names what is owed. On Sonnet the model did the rest by itself; on Sol nothing
  but that reaches it.
- Whether the candidate goes into main, and whether owner notes get that treatment, are the owner's decisions.
