---
bump: minor
---
`prepare` now probes that the worktree store and the repository's Git common
directory are writable before creating anything. When a host sandbox denies
either, it exits 3 with status `grant-needed` and an `ASK-AGENT-GRANT-NEEDED`
block naming the blocked paths and the Claude, Codex and Grok grants to add.
The new `preflight` command runs the same probe (plus caller-named `--path`
directories) without preparing.
