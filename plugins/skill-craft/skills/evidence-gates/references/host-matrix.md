# Evidence-gates host matrix

**Status:** optional toolkit — **not** DevLoop.

Default DevLoop: package **`devloop`** → engine. See that card’s
`references/product-default.md`.

**Honesty:** discovery (skill installed) ≠ execution (native receipt PASS).

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink (opt-in) | `~/.grok/skills/evidence-gates` | `/evidence-gates` only (not bare “devloop”) | historical: 2026-08-09 native smoke only |
| Claude Code | symlink + plugin view | `~/.claude/skills/evidence-gates` | `/evidence-gates` | pending |
| Hermes | materialize-copy | `…/software-development/evidence-gates` | `/evidence-gates` (not bare `/devloop`) | pending |
| Codex | symlink | `~/.codex/skills/evidence-gates` | discovery-ok | deferred |

Package leaf: **evidence-gates**.

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | smoke on H with PASS native receipt |
| Default DevLoop | **never** this package — use skill `devloop` |
