---
bump: minor
---
Before writing anything, `prepare`, `inspect`, `close` and `check-context` now
probe that the worktree store and the repository's Git common directory are
writable. When a host sandbox denies either, the command exits 3 with status
`grant-needed`, the blocked paths, the directories to grant (the stable
`<state>/ask-agent` base for the default store), and an `ASK-AGENT-GRANT-NEEDED`
message with the detected host's fix first, the exact rerun command and an
instruction for the agent to stop rather than work around it. The new
`preflight` command runs the same probe, plus caller-named `--path`
directories, without preparing. The probe is `scripts/host_write_grants.py`,
shared byte-identically with ShipLoop.

The helper now runs under Claude Code's Bash sandbox. The Git configuration
that sandbox injects into every command (its proxy's `http.*` and
`credential.*` keys, and `safe.directory` for the current directory and
`<cwd>/*`) no longer counts as a Git context override. Any other injected key,
or a `safe.directory` naming `*` or another path, is still refused.
