---
bump: minor
---
Keepalive: host hooks stop an agent from ending its turn while a run can still move, for Claude Code, Codex, Grok, Cursor and OpenCode. A marketplace install brings them (declared in `host-hooks.json`, generated per host); a skill-directory install adds them with `scripts/shiploop-hook install --host HOST`. See `references/keepalive.md`.
Only one session per run is kept alive; parallel workers and second terminals on the same run are let go, and ownership passes on when the owner's turn ends.
New `shiploop hook-status` (read-only JSON run status) and a `Keepalive marker:` line in every packet.
New `scripts/shiploop-drive` runs or resumes host sessions until a run is done, paused, blocked or stuck; use it for unattended Cursor and OpenCode runs.
A question about the loop no longer pauses the run, and the agent is told not to pause on its own to ask whether to continue; only an explicit stop or pause, or a real blocker, does.
