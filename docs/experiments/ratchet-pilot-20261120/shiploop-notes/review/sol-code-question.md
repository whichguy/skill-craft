Review code that has just been built from a design you may assume is settled. Be adversarial and concrete: find what is wrong in the code, not what you would have designed differently.

THE FOLDER (your working directory) holds:
- `DESIGN.md`: the design the code was built from. Section 2 is the specification, section 3 the known ways round, section 4 an earlier review of the design and what was decided, section 5 the tests it must pass. Where the code and section 2 disagree, that is a finding; where you disagree with section 2 itself, say so in one line at the end and do not count it as a defect.
- `diff-vs-main.patch`: everything the build changed, against the released engine.
- `tree/`: the files as built (`skills/shiploop/` whole: scripts, references, README; the changed suites and harness files under `test/`; the change note under `changes/`).
- `main/`: the released versions of the engine scripts the build changed, for reading what was there before.

BACKGROUND IN FIVE LINES. ShipLoop is a script-driven delivery harness: a model session does one stage at a time, reads a "packet" the script prints, and calls back with `check` (a dry run of the gates) and `complete` (submit the stage's result). It runs unattended: nothing may ask, wait or pause, and no loop gets a limit. The run owner can write an "owner note" into a run in flight (`shiploop note`). The change: every note must be accounted for by a row in a stage's done result (`notes`: applied, already, carried or declined), the result is refused while a row is missing, the refusal's first physical line must be enough to act on, and the done packet and the report list every note. The old hold, the record of what a print showed and the delivery record are removed.

WHAT I WANT FROM YOU.
1. A verdict in one line: "Ship as built", "Fix first" or "Do not ship", then why.
2. Defects, most serious first, numbered. For each: the file and symbol, a concrete sequence of commands or states that shows the wrong behaviour, what the right behaviour is by the design, and the smallest fix. Say for each whether you ran or traced it, or are inferring.
3. Go through these on purpose:
   a. Every path by which a producer's done result can be accepted (`dispatch`: fresh `check`, fresh `complete`, the reuse of an earlier check's yes, a producer's replay of its parked result, the import of a review with and without `--final-result`, a paused or blocked producer that resumes, stages the script records without a model). For each: is the notes gate applied exactly once, with one read of the notes, before the loop receipt? Can any path accept a done result that owes a row?
   b. The ledger and `owes` in `shiploop_owner_notes.py` against section 2.2: the order of rows, results taken out by a reconcile or a send-back, a note carried inside a work item and then an inner send-back, `add-work` and the corrective item, the last item, `handoff`. Is there a state in which an open note is owed by no result that will come, or in which a settled note is asked for again?
   c. `_row_fault` and `_queue`: the `item` rules at `plan` and `carry-forward` against the queue the result that takes effect leaves, including a result that gives no `work_items`, one that gives an empty list, and a review's replacement.
   d. `import_faults` and `_import_notes_gate`: a replacement that drops a row, changes one, adds one, or changes the outcome.
   e. The end of the run: `_end_read`, its place relative to the save and to `accept_effects`, and the note command's re-read of the state. What is the window that remains, and does anything print a claim that the window makes false?
   f. The refusal: `refusal`, `unreadable`, `arrived`, and how `shiploop_protocol.py` prints `NotesOwed` for `check` and for `complete`. Is the first physical line always the actionable sentence, on standard error, exit 2? Is anything printed before it?
   g. The packet: the owed-notes block's tier and place, the bounds and the forms it shrinks to, the template rows and the minimal fallback template, the lookup line; whether a stage with no note owed prints anything new.
   h. What was removed: is any reader of the hold, of `shown.json`, of the delivery record or of the old trace fields left in `tree/` (engine, references, tests, harness)? Does a saved state with the old key fail in the way the design says, and a state with notes and no rows load?
   i. The tests: which assert less than their names say, which paths of (a) to (h) have no test, and which fixture would pass on a broken engine.
   j. The harness readers under `test/shiploop_e2e/` that read saved traces: what they now do with a row written by the released engine (a held callback), and whether that changes how saved evidence is graded.
   k. The change note: is every sentence of it true of the code?
4. A list of what you could not verify from this folder.

Write for a reader who will decide what to fix from your answer alone. No preamble.
