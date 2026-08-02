---
name: devloop-run
description: >-
  Use when invoking the devloop engine for a machine-verifiable build/debug goal:
  resolve or bootstrap the engine CLI, then run with an explicit --repo or scratch
  request. Portable card for Grok, Claude, Codex, and Hermes; first --setup (or
  first run) can materialize a host-local engine under ~/.local/share/devloop.
  Setup/probe are multi-host; full autonomous engine loops still default to Hermes
  transport until a non-Hermes runtime ships.
version: 0.3.0
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

**Honesty:**
- Installing the card on three hosts is multi-host **discovery**.
- **`--setup` / `--probe`** are multi-host (bootstrap host-local engine from pin or seed).
- **Full autonomous engine runs** still use a **Hermes-default** model transport
  (`HERMES_BIN`, write-safe roots). Claude/Codex/Grok can run the card and bootstrap
  the tree; completing a real devloop goal without Hermes needs a future portability
  transport (not this card alone).
- Multi-host runtime still requires successful resolve/bootstrap **on that machine**.
- The Hermes skillhub leaf name `devloop` is never overwritten by this card.

## Bootstrap (host-local engine)

Default root: `${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}/devloop`.

Pinned release: [references/engine-pin.json](references/engine-pin.json) (`url` + `sha256`).  
Publish surface: GitHub Release assets on **skill-craft** (`devloop-engine-v*`), not a
dedicated engine monorepo (unless that is chosen later).  
Packaging: `scripts/package-devloop-engine.sh --from DIR --version X.Y.Z` (deny-check
fails on host-absolute path / home-PII leakage).

Requires **Python 3** on PATH for setup (marker + safe extract). Prefer `curl` or
`wget` for HTTPS pin download, and `shasum` for verification.

See [references/bootstrap.md](references/bootstrap.md) and [references/host-matrix.md](references/host-matrix.md).

## Truth table

| Situation | Result |
|-----------|--------|
| Valid `DEVLOOP_HOME` | Use it (no bootstrap) |
| Host-local engine present | Use `…/devloop` |
| Hermes / `/opt/data` seed present | Use seed (no clobber of Hermes leaf) |
| Missing engine + pin URL + matching sha256 | Bootstrap host-local; write marker last |
| Missing engine + `--no-bootstrap` | Exit **2** |
| sha256 mismatch | Exit **2**; no partial install |
| Tarball path escape (`..` / abs) | Exit **2**; refuse extract |
| `--force-bootstrap` on unmarked tree | Exit **2** unless `--force-hard` |
| `--setup` | Ensure + print `engine=…` |
| `--probe` | Resolve only; does not bootstrap |
| Card copied alone (no monorepo cwd) | Still bootstraps via card-local pin |

**Resolve order:** `DEVLOOP_HOME` → host-local → Hermes/`/opt/data` → bootstrap (unless `--no-bootstrap`).

**Bootstrap sources (first win):** `DEVLOOP_BOOTSTRAP_CMD` → `DEVLOOP_ENGINE_URL` or pin → seed copy.

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
| Release pin | `DEVLOOP_ENGINE_PIN` → card `references/engine-pin.json` |
| Override URL/sha | `DEVLOOP_ENGINE_URL`, `DEVLOOP_ENGINE_SHA256` |
| Bootstrap inject | `DEVLOOP_BOOTSTRAP_CMD` (tests / custom) |
| Legacy Hermes | `HERMES_HOME/.../devloop`, `~/.hermes/.../devloop` |
