---
name: devloop-run
description: >-
  Use when invoking the devloop engine for a machine-verifiable build/debug goal:
  resolve or bootstrap the engine CLI, then run with an explicit --repo or scratch
  request. Portable card for Grok, Claude, Codex, and Hermes; first --setup (or
  first run) can materialize a host-local engine under ~/.local/share/devloop.
version: 0.2.0
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
      - grok
      - claude
      - codex
---

# devloop-run

Thin **router + preflight + optional bootstrap** for the autonomous **devloop** engine.
This package does **not** vendor the full engine in git. It installs as a portable
skill card on each host; the engine is resolved or materialised **host-locally**.

## When to use

- One coherent build or debug goal with machine-checkable success (tests / commands)
- Prefer isolated worktree loop + fail-closed delivery over hand-editing

## When not to use

- Prompt/content optimization, subjective design, trivial one-line edits
- Expecting the engine without bootstrap or a seed source on a fresh machine

## Canonical invoke

```sh
# From skill package root (skill-dir or plugin view)
bash scripts/devloop-run --setup          # ensure engine (bootstrap if needed)
bash scripts/devloop-run --probe          # show selected engine path
bash scripts/devloop-run -- "Create slug.py with slugify..."
bash scripts/devloop-run -- --repo /abs/path/to/repo "Add normalize empty check"
```

After skill-dir install, package root is `~/.grok/skills/devloop-run` (Grok),
`~/.claude/skills/devloop-run` (Claude), or `~/.codex/skills/devloop-run` (Codex).

## Host matrix

| Host | Discovery (skill card) | Execution |
|------|------------------------|-----------|
| Grok | skill-dir install | yes after engine resolves or `--setup` bootstrap |
| Claude Code | skill-dir and/or marketplace plugin | same |
| Codex | skill-dir install | same |
| Hermes | skill-dir card (`devloop-run`); engine leaf stays `devloop` | yes when engine resolves |

**Honesty:** Installing the card on three hosts is multi-host **discovery**. Multi-host
**runtime** requires a successful resolve/bootstrap **on that machine**. The Hermes
engine leaf name `devloop` is never overwritten by this card.

## Bootstrap (host-local engine)

Default root: `${XDG_DATA_HOME:-$HOME/.local/share}/devloop`.

| Source | When |
|--------|------|
| Existing valid engine | `DEVLOOP_HOME`, host-local, Hermes, `/opt/data` |
| `DEVLOOP_BOOTSTRAP_CMD` | Custom installer; tests inject fakes |
| `DEVLOOP_ENGINE_URL` | `file://` tree/tgz or `https://…tgz` |
| Seed copy | Copy from Hermes/`/opt/data` engine if present (no network) |

See [references/bootstrap.md](references/bootstrap.md) and [references/host-matrix.md](references/host-matrix.md).

## Exit codes (card preflight)

| Exit | Meaning |
|------|---------|
| 0 | Probe/setup ok, or engine invoked |
| 2 | Engine missing / bootstrap refused / needs human |
| other | Pass-through from engine CLI |

## Binding surfaces

| Surface | Env / default |
|---------|----------------|
| Prefer engine | `DEVLOOP_HOME` |
| Host-local engine | `DEVLOOP_DATA_HOME/devloop` → `~/.local/share/devloop` |
| Bootstrap inject | `DEVLOOP_BOOTSTRAP_CMD`, `DEVLOOP_ENGINE_URL` |
| Legacy Hermes | `HERMES_HOME/.../devloop`, `~/.hermes/.../devloop` |
