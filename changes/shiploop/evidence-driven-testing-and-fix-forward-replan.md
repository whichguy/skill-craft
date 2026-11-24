---
bump: minor
---

# Evidence-driven testing, triage, and commit-then-amend fix-forward

- **Evidence reveal at `test`:** `test` now reads `KNOWLEDGE/architecture.md`, inspects the implementation's product diff (`RUN/fields/<action>-product-diff.patch`) against quoted `test_cases` and `not_covered`, and can register newly discovered focused/regression IDs directly via `added_tests`. If `test` edits product code while fixing a revealed defect, ShipLoop re-verifies the step's `Proof` at `test` `done`.
- **Structured triage and forwarding:** `test` may emit optional `test_findings` (`none`, `local`, `amend-remaining`, `system-test`) and optional open `assumptions`; `test_findings` and `not-exercisable` `mutant_dispositions` forward to `document`, `reflect-and-revise`, `system-test-author`, and `system-test`.
- **Commit-then-amend fix-forward (`replan_remaining`):** Non-final `document` steps may report `done` with `replan_remaining: {"reason", "affects"}` so ShipLoop commits completed step work and recaptures the lint base before re-opening `step-plan` with completed steps frozen `"done": true`.
- **Synced planning and hardened outer testing:** `test-strategy` consumes intake open questions and may emit optional `assumptions` due at `plan`, `prepare`, or outer stages; `step-plan` can update `test_layers`/`targets` and inherits passing regression commands from earlier items; `system-test` routes product defects to `add-work` and wrong/uncountable commands to `send-back` (`system-test-author` / `release-plan`) without direct product edits.
