# ShipLoop keepalive hook payloads

Host hook inputs recorded on 2026-09-25 from live runs of Claude Code 2.1.282,
Codex CLI 0.157.0, Grok 1.0.41 and cursor-agent 2026.09.18, with paths and
personal fields scrubbed. `__SESSION__` and `__MARKER__` are filled in by
`test/shiploop-keepalive.test.py`.

`cursor-stop.json` is constructed, not recorded: `cursor-agent -p` never fires
its stop hook. It carries the fields of Cursor's recorded shell-hook payload plus
the documented `status` and `loop_count`. OpenCode has no fixture because its
payloads are built by ShipLoop's own plugin (`skills/shiploop/hooks/opencode-keepalive.js`).

`claude-skill.json` is the PostToolUse payload of a Skill-tool call, recorded on 2026-10-16 from Claude Code 2.1.301
(`claude -p` with a `--settings` hook that matched `Skill` and saved its stdin), with paths and ids scrubbed. The recorded
`tool_input` was `{"skill": ..., "args": ...}` and the payload carried `session_id`, `prompt_id`, `tool_use_id` and
`transcript_path`; `__SKILL__` and `__ARGS__` stand where the test puts the call it checks.
