# DevLoop host matrix

**Honesty:** discovery (skill installed) ≠ execution (loop completed with native receipt).

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink | `~/.grok/skills/devloop-native` | NL “devloop” / `/devloop-native` | **PASS** 2026-08-09 — live `grok -p` smoke `~/src/devloop-grok-smoke` receipt mode=native status=PASS |
| Claude Code | symlink + plugin view | `~/.claude/skills/devloop-native` | `/devloop-native` (skill-dir smoke only) | pending |
| Hermes | materialize-copy | `~/.hermes/skills/software-development/devloop-native` | `/devloop-native` (not bare `/devloop`) | pending |
| Codex | symlink | `~/.codex/skills/devloop-native` | discovery-ok | deferred |

User-facing name: **DevLoop**. Package leaf: **devloop-native** (avoids reserved engine leaf `devloop`).

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | smoke on H with PASS receipt |
| Harness-native on three | smokes on Grok + Claude + Hermes |
