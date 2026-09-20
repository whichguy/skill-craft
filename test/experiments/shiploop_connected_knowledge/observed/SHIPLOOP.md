# Project knowledge

## Orion retry UI discovery — 2026-09-20

The selected bounded discovery note is [DISCOVERY.md — Orion retry UI discovery](DISCOVERY.md#orion-retry-ui-discovery).
It records the synthetic approved policy: retry resubmits the existing case to manual
review and must not auto-approve it. The fixture baseline is retained in
[BASELINE.txt](BASELINE.txt); it covers only local case-ID normalization, not gateway
or consumer behavior.

Before any implementation, reopen the discovery note and resolve its runtime route,
authorization, idempotency/read-back, UI-surface, and owner-confirmation gaps.
