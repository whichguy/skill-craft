Fixtures of the delivered-quality tests (`test/shiploop-e2e-quality.test.py`).

* `tiny-product/`: a three-file JavaScript delivery with one test file and a stand-in for `node --test` (`check.py`, which reads
  the sources as text and prints a node TAP summary, so the mutation runner can be driven without node). The 12 sites, the 5
  mutants the tests catch and the 7 they do not (4 in `lib.js`, 1 in `other.js`, 2 in `unused.js`, which no test loads) are
  computed by hand in the tests and agree with a real `node --test` run (node v25.9.0).
* `reference_checkers.py`: a hermetic Checkers service with one defect switch per held-out check
  (`test/shiploop_e2e/checks/checkers_accept.py`). It reads the PORT environment variable and ends by itself after two minutes.
* `memory-write-events.jsonl`: the shape of `events.jsonl` lines 599 to 606 of the saved run
  `/Users/dadleet/e2e-runs/20261008/r3-checkers-sonnet` (a Claude session writing two files under its profile's memory folder),
  reduced to the keys the detector reads, with the home folder renamed, plus one Grok-shaped line.
