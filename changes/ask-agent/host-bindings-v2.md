---
bump: minor
---
Upgrade host bindings to `skill-craft/host-bindings/v2`: add Cursor IDE (`CURSOR_AGENT`, `CURSOR_CONVERSATION_ID`, `Task` fresh and `resume="self"` fork, foreground parallel) and OpenCode (`OPENCODE`, unqualified) detection and bindings, update Claude Code `2.1.330` (`subagent_type="fork"`, foreground parallel), Codex `0.171.0` (`fork_turns="all"` vs `"none"`, `interrupt_agent`), and Grok Build `1.0.92` (`isolation="worktree"` forbidden, foreground parallel, no native fork), and pin byte-identical parity with ShipLoop's packaged bindings.
