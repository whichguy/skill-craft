---
bump: minor
---
Planning knowledge now outlives the run. Planning stages keep `docs/shiploop/` in the product repository up to date: `README.md` (index), the living `spec.md` with stable `R-<n>` requirement IDs, `environment.md`, `test-strategy.md`, and this run's `features/<slug>/` record (spec delta, plan, test spec, system tests, release plan, outcome). At `prepare`, each `test-spec`, `release-plan` and `release-verify`, ShipLoop refuses `done` until that close's files exist. It screens the files for credentials, refuses a living spec that drops an earlier committed requirement ID, and commits exactly `docs/shiploop/`. The workspace return always keeps `docs/shiploop/**`. Every packet names the knowledge home and the files its stage keeps current, so the next run starts from them.
