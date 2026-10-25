---
bump: patch
---
Prepare's `harness_runs` evidence must show a test running. The saved output is read by the same runner readers the
test stage uses, and it must show at least one test. Before, the gate checked only that the evidence file existed,
and run 5a passed it with a browser page that said it was not the component under test.
- An output ShipLoop cannot read is refused. The refusal names the runners ShipLoop reads and the stack's platform
  card, and says "report blocked" for a harness that cannot be run that way.
- An output whose runner selected no test is refused too.
- The prepare duty now says to save the runner's own output, summary included.
