---
bump: minor
---
An owner note (`shiploop note`) is now settled by a row in a stage's result, never by a print. For the run owner: the
next done result of a stage that owes your note must say what it did with it, and the `note` command's reply says
which stage's result that is. ShipLoop refuses that result until it does. The done packet lists every note with how it
ended and tells the host to say so in its last message, and the report has a new section, "Your notes", after "Decided
for you", with each note's words, every row and, for a row that names a work item, whether that item was completed, is
still queued or left the queue. A note sent to a run that has ended is refused; one written in the instant the run
ends is reported as read by no stage (start a new run with it), and in that instant the reply and the saved report can
disagree about it. Leave the note files as `note` wrote them: a note file that cannot be read, or does not read as a
note, refuses the next result until it is fixed. A note that has a row keeps it when its file is deleted: the done
packet, the report and `trace` show its rows, marked as no longer in the run folder, and no later note takes its
number.

For a host: a done result of any stage may carry a new key, `notes`, one row per note the stage owes: `{"note": "N1",
"did": "applied" | "already" | "carried" | "declined", "detail": "..."}`, and at `plan` and `carry-forward` an applied
row names in `item` the work item that does the work (at `carry-forward` a pending one). `detail` and `item` must be
real text: an ellipsis, a text wholly in angle brackets and the template's own placeholders are refused. The packet
quotes the notes a stage owes, with that duty, while they fit (the rest are named by file), and puts their rows in the
result template. ShipLoop refuses `done` while a row is missing, extra or malformed, and the refusal's first line says
what to do and names the notes and the result file (and the note file when it must be read), so it can be acted on
alone (on three rare paths a notice prints before it). `send-back`, `blocked` and `add-work` results hold no rows:
when a note changes the step of a work item, send the step back; `step-plan` then owes the row and may rewrite the
requirement the note changes in place. A note a work item's step carries is owed by that item's `carry-forward`, which
may also rewrite a requirement a note changes and queue the work; `carry-forward` and `handoff` may not carry, and
`handoff` owes every note not settled. An Improve review whose result is done keeps a row for exactly the notes the
reviewed result accounted for (it may correct a row), and a note that arrives during the review is owed by the next
stage; a review that changes the outcome leaves those notes owed. The refusal of a review's result that does not keep
those rows says in its first line what to change and gives the `--final-result` route. Nothing asks and nothing waits.

Gone: the callback held once for a note, the `check` notice, `owner-notes/shown.json`, the state key `owner_notes` and
the line "Owner notes already delivered"; `trace` and `trace.html` show each note as open, carried or settled instead
of shown or delivered. A run saved by the previous version with a note delivered cannot be resumed; start a new run.
`trace` of a finished run of the previous version shows its notes as open, since that version wrote no rows, and
counts a callback it held for a note as a refusal. A run with no note prints and stores what it did before, with these
exceptions: three standing texts, the duty of `step-plan`, the duty of `carry-forward` and the rule of
`carry-forward`'s loop, now say what a stage may do when an owner note it owes asks for a requirement change, and the
refusal of an unsupported result key lists `notes` among the allowed keys. `trace --json` is outside that claim: its
note fields changed (each note has `file_gone`, and a note whose file is gone has no text) and it no longer counts
held callbacks, though it still declares `shiploop-trace/v1`. `shiploop --help` and the README's "Steer a run in
flight" say the row rule.
