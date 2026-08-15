# prompt-on-change — Grok headless promote (no model pin)

You are debugging a local monitor. Do **not** fetch the watched page yourself.
Do **not** spawn subagents. Do **not** patch calendars or invent outbound actions.

A detect run already wrote evidence. A filled escalation prompt is in this
session or was just issued. If this file is the issued prompt, follow it.

If you are asked only to reason over spliced evidence JSON:

1. If the evidence is still pending (not under `processed/`), claim it with
   `scripts/prompt-on-change claim` using the env already set (`POC_STATE_DIR`).
2. Report previous → new clock time in plain language (the known target is 16:53).
3. End with one fenced `json outcome` block:

```json outcome
{
  "silent": false,
  "claimed": [],
  "condition_id": "",
  "previous_value": "",
  "new_value": "",
  "residual": ""
}
```

Fill previous_value / new_value from the evidence. Never re-act.
