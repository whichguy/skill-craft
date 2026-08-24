Stop and ask the user. No product edits. `complete-step` / `clear-step` / `start-step` are illegal while blocked.

ask_user: {{ASK_USER}}
blocked_from: {{BLOCKED_FROM}}
reason: {{BLOCKED_REASON}}

When they answer, invoke `/shiploop update --to {{RESUME_TO}} --reason <answer>` then invoke `/shiploop next`. Do not invent an oracle.
