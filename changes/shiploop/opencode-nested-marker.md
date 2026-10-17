---
bump: patch
---
An OpenCode session started from a Claude Code shell is no longer held to the Skill-call record when an Improve stage is completed. It inherits Claude's session variables but has no Skill tool, so the exit the refusal named could never be taken; its own `OPENCODE` marker now wins over the inherited Claude session, as the Codex and Cursor markers already did. A test derives the host list from the hook installer's table and fails when a non-Claude host has no nested marker.
