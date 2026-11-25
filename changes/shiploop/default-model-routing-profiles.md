---
bump: minor
---
Enable built-in per-host planning/execution routing defaults in `shiploop-drive` (Claude: `claude-opus-5-5`/`high` planning and `claude-sonnet-5-5`/`high` execution; Codex: `gpt-6.2-astra`/`high` planning and `gpt-6.2-sol`/`xhigh` execution; Antigravity: `gemini-pro-orchestrator-neon` single-session Orchestrator), with `--no-routing` or explicit `--model`/`-m` after `--` to opt out and `--routing default` to select the built-in preset explicitly.
