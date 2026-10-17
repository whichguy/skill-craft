---
bump: minor
---
A model no longer types, and ShipLoop no longer prints, paths the script already knows.
- The producer callback has no `--result` flag. Its label names the one path to write, absolute (`Callback for this stage (run
  once after its work, with the result written to <run>/inbox/<action>.md): python3 <cli> complete --run-dir=<run> --action=<id>`),
  and `complete` reads `RUN/inbox/<action>.md` when `--result` is left out. The flag is still read when given, and any other path is
  still refused.
- A path in `evidence_refs`, or in an assumption's `evidence`, may lead with `RUN/`, `HOME/`, `WORKTREE/` or `GUIDES/` (the
  packet's symbols). ShipLoop expands it before any check, checks that the file exists and stores the absolute path; a leading
  all-capital word and a slash that is none of those roots is refused by name. The same expansion reads an Improve stage's
  `--final-result`.
- An inner stage's Until Loop receipt is listed in `evidence_refs` by ShipLoop when the result leaves it out, once the loop's
  terminal packet has passed its checks. A result that lists it still keeps one entry. The refusal for a loop that never ran no
  longer asks the model to list the receipt.
- The terminal stop is the Pause command with its verb changed: the packet's Halt line reads `Halt (terminal; only on the user's
  explicit stop): the Pause command with `halt` in place of `pause`.` and no longer repeats a second command line.
- The test packet's red-check line names `python3`, like every other printed command, not the interpreter path of the host that
  rendered it.
- An Improve handoff has its own symbol, `CHILD` (the review's directory), defined in its References block; the opening, receipt,
  owner record and review-file lines print as `CHILD/opening.md`, `CHILD/packet.json`, `CHILD/reviews/review-<n>.md`. Its commands
  keep the absolute directory.
- Docs: the README, `references/navigator.md` and `commands/shiploop-complete.md` show `complete` without `--result` and the
  expansion.
