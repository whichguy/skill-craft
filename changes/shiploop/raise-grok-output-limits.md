---
bump: patch
---
Raise ShipLoop's retired Grok-era 16,000/20,000 stdout and packet-head limits (`HEAD_LIMIT`, `HEAD_REQUIRED_END`, `PRINT_LIMIT`, `shiploop_protocol.OUTPUT_LIMIT`, and `shiploop_status_hook.WINDOW`) to 30,000 characters (29,500 for `HEAD_REQUIRED_END`), matching the lowest common ceiling across Claude Code (~30,000-char Bash stdout), Codex, and Antigravity.
