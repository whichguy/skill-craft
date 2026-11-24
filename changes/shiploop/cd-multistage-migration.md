---
bump: minor
---
Strengthen ShipLoop multi-stage CD, per-environment settings, and data-migration planning and execution: carry `release-plan`-owned plan concerns (`migrate-before`, `migrate-after`, `switchover`, `config`, `state`) through `release-check`, `release`, and `release-verify`; enforce concern validation on Improve `--final-result` imports; add `## Release and promotion` to `KNOWLEDGE/environment.md` and reconcile run-note documentation; augment outer CD prompts, stage specs, and guides for ordered destination ladders (`dev` -> `staging`/`test` -> `prod`), per-hop authority, settings parity, and expand/deploy/contract migrations; and support optional multi-stage `promotions` in opt-in `--delivery-contract`.
