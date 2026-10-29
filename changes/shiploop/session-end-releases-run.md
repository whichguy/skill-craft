---
bump: minor
---
When the host ends a session (a `/clear`, an exit), the run that session owned is released at once, so the next
session drives it without waiting 30 minutes.
- The keepalive registers a session-end hook on every plugin host: Claude Code, Codex and Grok run `SessionEnd`, and
  Cursor runs `sessionEnd`. `shiploop-hook install` writes the same entry. The hook drops the session's binding and
  releases the run only when that session owns it; a subagent's or another session's end changes nothing.
- A killed session sends no session end; the 1.20.0 process check covers that case.
