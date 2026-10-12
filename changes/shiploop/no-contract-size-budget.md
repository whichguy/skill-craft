---
bump: minor
---
ShipLoop no longer limits the size of an inner-loop contract (the bundled Until Loop is now 0.8.3, which has no size limit either). The 16 KiB state budget (9,216-byte contract budget, report reserve and bookkeeping reserve) is gone with the Until Loop runtime's own cap (Until Loop 0.8.1+): `improve-start` accepts any opening, step-plan accepts any `test_commands` list, and the Backchain guidance and Improve context no longer print a byte allowance. A deep run directory could previously push the verify stage's contract over the budget and block every item. Contract building, the one-contract-per-action rule, exit and repeat conditions and receipts are unchanged.
