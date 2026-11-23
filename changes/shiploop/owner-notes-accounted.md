---
bump: minor
---
An owner note (`shiploop note`) is now settled by a row in a stage's result, never by a print. For the run owner: the
stage that next submits a done result must say what it did with your note, and the `note` command's reply says which
stage that is. The done packet lists every note with how it ended and tells the host to say so in its last message,
and the report has a new section, "Your notes", after "Decided for you", with each note's words, every row and, for a
row that names a work item, whether that item was completed, is still queued or left the queue. A note written as the
run ends is reported as read by no stage; start a new run with it.

For a host: a done result of any stage may carry a new key, `notes`, one row per note the stage owes:
`{"note": "N1", "did": "applied" | "already" | "carried" | "declined", "detail": "..."}`, and at `plan` and
`carry-forward` an applied row names in `item` the work item that does the work (at `carry-forward` a pending one).
The packet quotes the notes a stage owes with that duty and puts their rows in the result template. ShipLoop refuses
`done` while a row is missing, extra or malformed, before any other gate, and the refusal's first line names the
notes, their folder and the result file, so it can be acted on alone. A note a work item's step carries is owed by
that item's `carry-forward`, which may revise the requirement it changes in place and queue the work; `carry-forward`
and `handoff` may not carry, and `handoff` owes every note not settled. An Improve review keeps the rows of the result
it reviews. Nothing asks and nothing waits.

Gone: the callback held once for a note, the `check` notice, `owner-notes/shown.json`, the state key `owner_notes` and
the line "Owner notes already delivered"; `trace` and `trace.html` show each note as open, carried or settled instead
of shown or delivered. A run saved by the previous version with a note delivered cannot be resumed; start a new run.
A run with no note prints and stores what it did before, with two exceptions: the standing duties of `document` and
`carry-forward` and the rule of `carry-forward`'s loop now say what an owner note that asks for a requirement change
means, and the refusal of an unsupported result key lists `notes` among the allowed keys. `trace --json` is outside
that claim: its note fields changed.
