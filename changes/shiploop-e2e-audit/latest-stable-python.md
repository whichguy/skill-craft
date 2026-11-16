---
bump: major
---
Require Python 3.15 or newer for the ShipLoop E2E audit harness instead of 3.10+.
Use a supported local interpreter first on PATH; no particular Python manager
or new dependency is required. This changes only the prerequisite: model defaults,
experiment baselines and runtime experiment behavior are unchanged.
