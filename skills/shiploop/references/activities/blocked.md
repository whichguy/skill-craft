Stop and ask the user. No product edits. `complete-step` / `clear-step` / `start-step` are illegal while blocked.

ask_user: {{ASK_USER}}
blocked_from: {{BLOCKED_FROM}}
reason: {{BLOCKED_REASON}}

When they answer, invoke `/shiploop complete --reason <answer>` (resumes to `{{RESUME_TO}}`). Do not invent an oracle.
