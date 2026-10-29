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

`claude-session-end.json` is the SessionEnd payload recorded on 2026-10-28 from a `claude -p` session (Claude Code
2.1.312, a `--settings` SessionEnd hook that saved its stdin; `docs/shiploop-owed-outcome-evidence/session_end_probe.out`),
with paths and ids scrubbed: `reason` was `other` for an ordinary exit. `codex-session-end.json`, `grok-session-end.json`
and `cursor-session-end.json` are constructed, not recorded: each carries its host's recorded stop fields that identify
the session, with the host's session-end event name (Codex 0.165.0 and Grok 1.0.70 name `SessionEnd`, cursor-agent
2026.09.23 names `sessionEnd`), and no per-turn fields. The keepalive's `session_end` looks the session id up under
every host, so it does not depend on telling them apart.
