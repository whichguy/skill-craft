---
bump: minor
---
Add opt-in external task packets and pinned command arguments to the standalone
task interface. Keep inline transport compatible. Return the actionable task
and mode-specific rules from the existing worker-start check, preserving native
parent launch/collection and acceptance, current/worktree selection, inherited
state, scoped commits, explicit patch delivery and findings-only ephemeral work.
Add packet tamper/path/route regression coverage and harness final-result writing
with separate native evidence validation. Smaller launch payloads are measurable
locally; elapsed-time improvement still requires matched live qualification.
