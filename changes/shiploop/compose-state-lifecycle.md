---
bump: minor
---
Packets now ask for composable design and a state lifecycle. Code craft adds "compose before you build" (reuse, compose or augment an existing unit before writing a new one, with a guard against fusing different rules), and the quality loop treats duplicated logic as a material finding. Intake asks who the actors are, whether state is shared or must persist, and what must stay hidden. The interaction-design guidance asks each state's owner, readers, concurrency, end of life, quotas and personal-data handling. The planning review checks platform claims that a decision depends on. The Apps Script card describes the mcp-gas-deploy layer, including that its `srv`/`apiExec` bridge runs client-built code. Evidence: docs/shiploop-composition-state-experiments-2026-09-26.md.
