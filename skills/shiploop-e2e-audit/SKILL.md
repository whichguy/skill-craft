---
name: shiploop-e2e-audit
argument-hint: "[improve [CASE] | mock | check | CASE | SUITE | review PATH] [checkout=PATH] [output=PATH]"
description: >-
  Improve ShipLoop as a general SDLC skill through local end-to-end cases, independent
  review, and qualified candidate comparisons. Use for self-improving ShipLoop,
  ShipLoop E2E campaigns, mock or live audits, package checks, or retained-run review.
  Hosted cases use their dedicated test environment and evidence requirements.
version: 1.0.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# ShipLoop E2E audit

For **improve**, a request to iterate or self-improve ShipLoop, or an ongoing
improvement campaign, use [the improvement procedure](IMPROVE.md). Start with a
fresh local case and evaluate how ShipLoop plans, implements, tests, reviews,
and delivers software. The request authorizes ordinary preflight and local
campaign work within its stated scope. The harness checks the inputs
automatically and retains the result.

For **mock**, **check**, a named smoke or full audit, or **review PATH**, use
[the audit procedure](AUDIT.md) with this card's actual path as `SKILL_ROOT`.
An audit request without a mode runs the mock audit. Hosted cases use their
case-specific test environment, authority, and observation rules.

ShipLoop's builder runs independently. Preserve each attempt and its delivered
work. Keep the app's behavior, what its tests exercised, and the evidence for a
change to ShipLoop visible in the findings report.
