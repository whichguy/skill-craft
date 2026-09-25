# ShipLoop keepalive hook payloads

Host hook inputs recorded on 2026-09-25 from live runs of Claude Code 2.1.282,
Codex CLI 0.157.0, Grok 1.0.41 and cursor-agent 2026.09.18, with paths and
personal fields scrubbed. `__SESSION__` and `__MARKER__` are filled in by
`test/shiploop-keepalive.test.py`.

`cursor-stop.json` is constructed, not recorded: `cursor-agent -p` never fires
its stop hook. It carries the fields of Cursor's recorded shell-hook payload plus
the documented `status` and `loop_count`. OpenCode has no fixture because its
payloads are built by ShipLoop's own plugin (`skills/shiploop/hooks/opencode-keepalive.js`).
