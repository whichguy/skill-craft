---
bump: minor
---
A context lost in the middle of a stage can now pick up where it left off. Every packet names the
action's pass log (`notes/<action>.md`), where each pass records what it checked and what is left,
and the run context index gains an "In progress" section (the action, its pass log, loop packets,
ShipLoop test runs so far and revisions used) and a "Script records" section listing ShipLoop's own
test runs, loop packets, lint records and Improve receipts. A result that cites a local file that
does not exist is refused. `verify` now reads the item's implement, test-green, regression and
static-checks results, and `handoff` reads product-acceptance and operations.
