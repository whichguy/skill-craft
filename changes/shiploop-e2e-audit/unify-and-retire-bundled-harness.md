---
bump: major
---
Retire the 30.6k-line bundled Grok/GAS/Salesforce audit harness, `AUDIT.md`, and
`scripts/resolve_harness.py`, unifying `shiploop-e2e-audit` around the single
source harness under `test/shiploop_e2e/`. Make `SKILL.md` and `IMPROVE.md` a
runnable, host-neutral six-step improvement loop: require every ShipLoop test-case
run to execute in its own independent, isolated, brand-new product Git repository
folder (`$RUN/work`, outside `skill-craft`), align Codex defaults to Sol 6.2
(`xhigh` subject, `max` improver) and Astra 6.2 (`high` reviewer/judge), remove
the stale Python 3.15 requirement, default the first case to `ticket-import`
(keeping `csv-report` as smoke), and fold nomenclature (S-16), Run Review export,
repository `LEARNINGS.md` retention, and `lifecycle.py` hygiene into `IMPROVE.md`.
