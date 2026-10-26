---
bump: minor
---
New: the run's owner can leave a note on a running run with
`shiploop note --run-dir RUN --text TEXT` (or `--file PATH`), and the model sees it at its next step.

- Each note is its own file, `RUN/owner-notes/N<k>.md`. Writing one takes no run lock.
- The next packet quotes every note no accepted step has delivered. A head with little room quotes what fits and names
  the rest by file; the plan head prints one line.
- A callback run while a note the packet did not print in full is waiting is held once, with the note printed. The same
  callback then goes through.
- A note is delivered only when the script accepts a step whose packet showed it, recorded in `state.md`
  `owner_notes`.
- `shiploop trace` and `trace.html` show each note's state. The page builds the `note` command to copy. A held callback
  counts as held, not refused.
