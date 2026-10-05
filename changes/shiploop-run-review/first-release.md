---
version: 0.1.0
---
Adds the ShipLoop Run Review skill (`/skill-craft:shiploop-run-review`): it exports a ShipLoop E2E run's measured numbers into the owner's Run Review page, finds or creates the page, uploads the documents and adds the judgement. The exporter, data contract, starting defaults and page template move here from shiploop-e2e-audit. The export is now `run-review-export/v2`: a counter the host cannot measure (refusals and glue on a Claude run) is left out with its reason instead of reading 0, a `metrics.json` that predates that record is refused, and a stage with no accept time reads n/a instead of 0 min.
