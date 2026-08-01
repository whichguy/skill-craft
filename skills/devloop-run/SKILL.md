---
name: devloop-run
description: >-
  Use when invoking the Hermes-backed devloop engine for a machine-verifiable
  build/debug goal: resolve the installed devloop CLI and run it with an explicit
  --repo or scratch request. Discovery card for all hosts; execution requires a
  resolved Hermes/devloop engine tree (not multi-host runtime).
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
    engine: true
    runtime_hosts:
      - hermes
---

# devloop-run

Thin **router + preflight** for the autonomous **devloop** engine. This package does
**not** vendor the engine. The engine remains under Hermes skillhub (or
`DEVLOOP_HOME`). Installing this skill on Claude/Grok/Codex is **discovery only**.

## When to use

- One coherent build or debug goal with machine-checkable success (tests / commands)
- Prefer isolated worktree loop + fail-closed delivery over hand-editing

## When not to use

- Prompt/content optimization, subjective design, trivial one-line edits
- Claiming multi-host execution without a Hermes/devloop engine present

## Canonical invoke

```bash
# From skill package (after install, package root is the skill leaf)
bash scripts/devloop-run -- "Create slug.py with slugify..."
bash scripts/devloop-run -- --repo /abs/path/to/repo "Add normalize empty check"
bash scripts/devloop-run -- --help
```

Or via PATH if the skill root is known:

```bash
python3 "${DEVLOOP_HOME:-$HERMES_HOME/skills/software-development/devloop}/scripts/devloop_cli.py" "..."
```

## Host matrix (honesty)

| Host | Discovery | Execution |
|------|-----------|-----------|
| Hermes (container/host with engine tree) | yes | yes, if engine resolves |
| Claude / Grok / Codex | yes (skill card) | only if engine path resolves on this machine; else exit 2 |

## Preflight exit codes

| Exit | Meaning |
|------|---------|
| 0 | CLI invoked; pass-through of engine exit when engine ran |
| 2 | Engine not found / binding incomplete — needs human (install engine or set `DEVLOOP_HOME`) |
| 1 | Usage error or engine hard failure (non-2) |

## Binding surfaces (do not collapse)

| Surface | Env / default |
|---------|----------------|
| Engine package root | `DEVLOOP_HOME` → `$HERMES_HOME/skills/software-development/devloop` → `~/.hermes/.../devloop` → `/opt/data/.../devloop` |
| Hermes home | `HERMES_HOME` (optional) |
| Transport | engine-owned (`HERMES_BIN`, etc.) — not this card |

See [references/host-matrix.md](references/host-matrix.md) and monorepo
[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).
