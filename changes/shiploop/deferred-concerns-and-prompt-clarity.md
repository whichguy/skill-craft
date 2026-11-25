---
bump: minor
---

Refine deferred-concerns lifecycle and clarify stage prompt checklists:

- Stop triggering an extra upfront `step-plan` Improve review on rolling-wave `W2+` items whose plan concerns were set to `"deferred"` (`shiploop_navigator._first_item_review`, replacing the rule from `415f6831b`); allow deferred `step-plan` results to optionally record applicable step-mapped concerns (`shiploop_concerns.check_step_plan`), and surface a non-blocking deferred-concerns reminder checklist in `product-acceptance` and `release-verify` packets (`shiploop_concerns.deferred_items`, `shiploop_navigator._deferred_concerns_lines`).
- Document the updated schedule in `skills/shiploop/references/improve-stages.md` and update `_improve_line()` wording for `document` Improve reviews over full diffs before committing steps.
- Add concise, language-neutral pre-submit checklist reminders across `test-strategy` (unit/component row for UI/client code), `plan` (canonical `concerns` shapes), `prepare` (summary/TAP reporter), `step-plan` (`absent` expectation for new standalone `proof` scripts and `A<n>` settlement), `test-spec` + `references/testing-and-documentation.md` (preserve intermediate observable state invariants), `test` (mutation scope & `mutant_dispositions`), and `release-check` / `handoff` (`return-plan.md` and open `A<n>` assumptions).
