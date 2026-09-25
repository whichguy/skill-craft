---
bump: minor
---
Installing the ShipLoop plugin from the marketplace now sets up the status hook: the package carries generated hook files for Claude Code, Codex, Grok and Cursor. Claude Code and Codex show the status block to you after each ShipLoop call (Codex asks you to trust the hook once in `/hooks`). Grok and Cursor run the hook but cannot display it, so the in-packet block stays the display there. The hook now recognizes each host's payload shape.
