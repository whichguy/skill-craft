Stop and ask the user. No product edits. `complete-step` / `clear-step` / `start-step` are illegal while blocked.

ask_user: {{ASK_USER}}
blocked_from: {{BLOCKED_FROM}}
reason: {{BLOCKED_REASON}}

When they answer, invoke `/shiploop complete --reason <answer>` (resumes to `{{RESUME_TO}}`). Do not invent an oracle.

When `blocked_from` is validate-spec and the reason is an unresolved handle,
relief is one of: (1) user supplies the missing access — resume
`validate-spec`, re-probe (IDs/endpoints may populate handle `value`; **never**
persist a token/password — `--reason` is copied into `state.json`; use `access established`
after an out-of-band secret + re-probe); (2) this increment will
create it (`create` handle; `initiation: needed` when required) — resume
`validate-spec`; (3) shrink the spec to drop the dependency — resume
`validate-spec`. Other `blocked_from` keep the generic resume line. Do not
invent a mock, a second writer, or a quieter spec.
