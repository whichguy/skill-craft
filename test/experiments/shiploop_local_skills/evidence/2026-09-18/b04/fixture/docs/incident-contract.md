# Incident-evidence triage contract v1

This document is authority only for incident triage. Read `data/bundle.json` with
`incident`, optional `target` (default `production`), ordered `checks`, and
receipt rows containing `incident`, `target`, `check`, numeric `attempt`, and
`status`. Select the latest matching numeric attempt for each requested check.

Write exactly `output/decision.json` with `workflow: "incident-v1"`, the resolved
`incident`, `target`, `required_checks`, ordered `selected_receipts`, and a
`decision` of `clear` only when every selected receipt is `pass`; otherwise use
`investigate`. There is no release pass/fail or deployment authorization in this
incident output. This contract does not replace either release contract.
