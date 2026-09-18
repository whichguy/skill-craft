# Release-evidence triage contract v1

This document is the authority for this repository's release-evidence decision.

Read `data/bundle.json`. It supplies a string `candidate`, optional string
`target`, optional ordered `required_checks`, and `receipts`. The default target
is `staging`; the default required checks are `unit` then `integration`.
Each receipt has `candidate`, `target`, `check`, numeric integer `attempt`, and
`status` (`pass`, `fail`, or `block`). Ignore a receipt whose candidate or target
does not match the current request. For each required check, use only the matching
receipt with the largest numeric attempt. Missing receipts remain missing.

Write exactly this object to `output/decision.json`, preserving required-check
order and using a selected row of `{"check", "attempt", "status"}`; use
`null` and `"missing"` for a missing row:

```json
{
  "workflow": "release-v1",
  "candidate": "input candidate",
  "target": "resolved target",
  "required_checks": ["resolved checks"],
  "selected_receipts": [{"check": "unit", "attempt": 2, "status": "pass"}],
  "decision": "clear or blocked",
  "deployment_authorized": false
}
```

The decision is `clear` only when every selected required receipt is `pass`.
Any missing, `block`, or `fail` result is `blocked`. This local triage does not
authorize a deployment.
