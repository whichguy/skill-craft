Fixtures of the delivered-quality tests (`test/shiploop-e2e-quality.test.py`).

* `tiny-product/`: a three-file JavaScript delivery with one test file and a stand-in for `node --test` (`check.py`, which reads
  the sources as text and prints a node TAP summary, so the mutation runner can be driven without node). The 12 sites, the 5
  mutants the tests catch and the 7 they do not (4 in `lib.js`, 1 in `other.js`, 2 in `unused.js`, which no test loads) are
  computed by hand in the tests and agree with a real `node --test` run (node v25.9.0).
* `reference_checkers.py`: a hermetic Checkers service with one defect switch per held-out check
  (`test/shiploop_e2e/checks/checkers_accept.py`). It reads the PORT environment variable and ends by itself after two minutes.
* `reference_user_listing.py`: the `user-listing` brownfield case's reference delivery, written over
  `test/shiploop_e2e/fixtures/node-base`, with an independent alternative and fourteen targeted defects
  (`build(dest, variant)`), for its held-out checks (`test/shiploop_e2e/checks/user_listing_accept.py`) and the base's pristine
  tests. Its tests are in `test/shiploop-e2e-brownfield.test.py`.
* `reference_ticket_assignment.py` and `reference_ticket_escalation.py`: the `ticket-assignment` brownfield case's reference
  delivery, written as edits over `test/shiploop_e2e/fixtures/node-tickets`, and its follow-on `ticket-escalation`'s, written
  over the first one's reference (which stands in for the first run's delivery). Each has an independent alternative and
  targeted defects (`build(dest, variant)`), for the held-out checks (`test/shiploop_e2e/checks/ticket_assignment_accept.py`,
  `ticket_escalation_accept.py`) and the base's pristine tests. Their tests are in
  `test/shiploop-e2e-brownfield-tickets.test.py`.
* `memory-write-events.jsonl`: the shape of `events.jsonl` lines 599 to 606 of the saved run
  `/Users/dadleet/e2e-runs/20261008/r3-checkers-sonnet` (a Claude session writing two files under its profile's memory folder),
  reduced to the keys the detector reads, with the home folder renamed, plus one Grok-shaped line.
* `gate-records.json`: the keys `run._main` hands to `quality_gate`, extracted from the saved `result.json` of
  `/Users/dadleet/e2e-runs/20261008/r3-battleship-grok-none` (stopped by hand, engine active, no tracked file),
  `r3-checkers-sonnet` (a finished delivery) and `r2-battleship-grok-none` (a regraded, mixed-host run).
