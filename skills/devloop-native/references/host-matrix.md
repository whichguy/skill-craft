# Evidence-gates host matrix (`devloop-native`)

**Status:** demoted optional toolkit — **not** default DevLoop.

Default DevLoop: package **`devloop-run`** → engine. See that card’s
`references/product-default.md`.

**Honesty:** discovery (skill installed) ≠ execution (native receipt PASS).

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink | `~/.grok/skills/devloop-native` | `/devloop-native` only (not bare “devloop”) | historical: 2026-08-09 native smoke only |
| Claude Code | symlink + plugin view | `~/.claude/skills/devloop-native` | `/devloop-native` | pending |
| Hermes | materialize-copy | `…/software-development/devloop-native` | `/devloop-native` (not bare `/devloop`) | pending |
| Codex | symlink | `~/.codex/skills/devloop-native` | discovery-ok | deferred |

Package leaf: **devloop-native** (avoids reserved engine leaf `devloop`).

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | smoke on H with PASS native receipt |
| Default DevLoop | **never** this package — use `devloop-run` |
