---
bump: patch
---
Synchronize ShipLoop's static linter and inner-loop reference docs (`lint-catalog.md`, `run-options.md`, `inner-loop.md`, `guide-map.md`, `coding-guidance.md`) with current gate and Case Spec behavior, wire `lint-catalog.md` into stage routing (`STAGE_REFERENCES`, `POLICIES`, and stage duties) so discovery/prepare/step-plan/inner stages leverage it consistently, and add drift-guard regression tests.
