---
bump: minor
---
The test stage's three gates now say what they did, and no text the model reads shows the refused-run cap.
- `complete` at the test stage prints one `Gates:` line per gate result after the next packet (after the `--check-only`
  sentence for a check-only run): `Gates: base: skipped (no item base was recorded ...)`, `Gates: candidate: [focused] ... ->
  passed (3 ran, floor 3)`, `Gates: mutation: 2 of 3 mutants of the changed product lines killed ...`. Before, the three
  summaries were discarded, and a base run or mutation check that did nothing (no item base, no focused command, no changed
  line a mutation operator matched) wrote `disposition: passed`, the word a proof files. Such a record now says
  `disposition: skipped` with `passed: true` (every reader of `passed` and of `could-not-run` is unchanged) and keeps its
  reason under `skipped`. The E2E harness (`fidelity.gates_not_exercised`, `metrics.skipped_gates`) counts a record by either
  marker.
- The refused-run tally prints the count and what it counts, never the cap: the test packet's "Refused runs ... 0 of 11"
  line is gone at zero and reads "Refused runs for this action so far: N (base, candidate and mutation runs together); if
  they keep coming, <the stage's route out>." above it (the old text said base and candidate only; a refused mutation check
  counts too). The same wording replaces the cap in the test rerun list, both refusal tails of `verify`, the tails of the base
  run and the mutation check, and the two "does not count" sentences. The cap stays in the script: `ShipLoop test run: ... was
  refused N times; done is no longer accepted` still names the route out when it stops accepting done.
- The test result template's `summary` placeholder asks for what no ShipLoop record holds (the tests added and what each
  asserts, the test decisions retained, refined or superseded, any test changed to pass a run and why) and the test stage's
  duty 2 no longer asks for the decision locators and the step plan in `evidence_refs`, which no gate reads and the next
  packet lists itself. A new ledger row, `test-summary`, keeps both obligations in the packet.
