# Host matrix — prompt-on-change

**Honesty:** discovery (skill installed) ≠ execution (CLI ran and printed
`LLM_ESCALATION:` or the documented empty stdout).

| Host | Prompt | Scripts | Install | Runtime |
|------|--------|---------|---------|---------|
| Grok Build | escalation prompt portable | CLI | symlink `~/.grok/skills/prompt-on-change` | CLI; schedule is host-local |
| Claude Code | same prompt file | CLI | symlink `~/.claude/skills/prompt-on-change` + plugin view | CLI |
| Codex | same prompt file | CLI | symlink `~/.codex/skills/prompt-on-change` | CLI |
| Hermes | same prompt file | CLI | managed **copy** `~/.hermes/skills/software-development/prompt-on-change` | proven historically under foreign `productivity/` leaf; do not clobber that tree |
| Cursor | same prompt file | CLI | extra symlink `~/.cursor/skills/prompt-on-change` (`install.sh` has no Cursor host yet) | CLI or `/loop`; do not claim Automations as runtime |

Hermes materialization is a copy with provenance
`~/.hermes/skills/software-development/.skill-craft/prompt-on-change.json`.
The live productivity leaf is a **foreign** tree — skip it forever.

Live Hermes 5m runner (`detect_runner.sh`, `no_agent`) stays on its current
`DETECT_DIR` until env is retargeted after a healthy cycle.
