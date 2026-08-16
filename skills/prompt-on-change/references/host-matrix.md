# Host matrix — prompt-on-change

**Honesty:** discovery (skill installed) ≠ execution (wrapper ran and printed
`LLM_ESCALATION:` or the documented empty stdout / `CLAIM_EMPTY`).
Grok runtime is proven only when `test/prompt-on-change-grok-native.test.sh`
ran with `POC_GROK_LIVE=1`, or `test/prompt-on-change-e2e.test.sh` with
`POC_E2E=1`, not from skill-dir install. Success tokens:
`references/e2e-success.md`. Coverage inventory:
`references/coverage-matrix.md`.

Native default is the author + same-turn escalation prompts. Debug/issue verbs
(`status`, `explain`, `issue`, `issue --exec`) are host-visible lifecycle.
The wrapper CLI is optional and only a runtime when Python deps resolve.

Session delivery (2.2.0) is Grok-only: `run --to grok:<uuid>` resumes that
id if a local session dir exists and is not live, starts it if missing, and
refuses (issues the file, no Grok) when live or uncertain. Claude Channels,
Codex/Hermes/Cursor inject, and Cursor Automations are not this slice.
Hermes stays file-claim. Cursor stays issue-the-file. An open Grok session
may `/loop` a config itself; that is not wrapper inject.

| Host | Prompts | Scripts | Install | Agent card | Plugin | Runtime |
|------|---------|---------|---------|------------|--------|---------|
| Grok Build | author + escalation + schedule | `scripts/prompt-on-change` (`status` / `explain` / `issue --exec`) | symlink `~/.grok/skills/prompt-on-change` | `~/.grok/agents/prompt-on-change.md` (`--agents`) | git URL or local path to `plugins/prompt-on-change` — **never** `name@marketplace` | CLI when Python resolves; live headless proven only by `POC_GROK_LIVE=1` |
| Claude Code | same prompt files | same wrapper | symlink `~/.claude/skills/prompt-on-change` + plugin view | `~/.claude/agents/prompt-on-change.md` | Claude marketplace pin (after main ship) | CLI when Python resolves |
| Codex | same prompt files | same wrapper | symlink `~/.codex/skills/prompt-on-change` | none | `name@marketplace` when pinned | CLI when Python resolves |
| Hermes | same prompt files | same wrapper | managed **copy** `~/.hermes/skills/software-development/prompt-on-change` | none | skill-dir only | proven historically under foreign `productivity/` leaf; do not clobber that tree |
| Cursor | same prompt files | same wrapper | symlink `~/.cursor/skills/prompt-on-change` | none | n/a | CLI or `/loop`; do **not** claim Automations as runtime |

Hermes materialization is a copy with provenance
`~/.hermes/skills/software-development/.skill-craft/prompt-on-change.json`.
The live productivity leaf is a **foreign** tree — skip it forever.

Live Hermes 5m runner (`detect_runner.sh`, `no_agent`) stays on its current
`DETECT_DIR` until env is retargeted after a healthy cycle.

Grok plugin install examples (path / git only):

```sh
grok plugin install /path/to/skill-craft/plugins/prompt-on-change
grok plugin install whichguy/skill-craft
```
