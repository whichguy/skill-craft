---
bump: minor
---
A session now names its own host before its first native launch: `scripts/ask_agent_host.py` reads exact environment variable names, innermost host first, and prints that host's measured binding from `references/host-bindings.json` (tool names, spawn arguments, the concurrency the host allows, the wait timeout); a host with no measured binding is reported as `unknown`. Codex's section now says it allows four concurrent agents including the parent (launch at most three workers) and to wait with the lifecycle's two-minute observation timeout instead of short polls.
