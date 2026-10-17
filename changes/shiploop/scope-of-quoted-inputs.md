---
bump: minor
---
Packets quote what the stage acts on, and the request gets a sentence index.
- An inline implement step now quotes only its own slice of the item's hand-offs: the criteria the step lists, the
  test-spec cases whose criterion is one of them, and the follows entries its task, those criteria and those cases name
  (R-<n>), with every AD-<n> kept. A line says which step the block is cut to and where every step's criteria are. The
  item's whole set is quoted, as before, on the ask-agent route, when the step lists no criterion the plan defines or
  lists them all, and the follows cut alone falls back to the item's list when the step names none of its R-<n>. The
  implement Improve handoff quotes the same block. On a synthetic two-step item with twenty criteria, step 1's block
  falls from 20.5 KB to 1.4 KB.
- Every save writes `request.md` in the run directory: the request verbatim, then split into sentences `S1..Sn` as a
  display index (the verbatim text still governs and every packet still quotes it). The intake packet points at it, and
  intake's `complete` (and `--check-only`) prints `ShipLoop request notice: ...` naming each sentence the summary does
  not cite (`S2-S4` and `S2 to S4` count as ranges). The notice never refuses. The master index lists the file.
- system-test-author's "Results this stage builds on" lists each completed item's step-plan, test-spec and test result
  and its latest candidate run, and duty 1 says the records in force are the ones listed there, instead of sending the
  model to search state.md's history.
