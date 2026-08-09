---
name: devloop-run
description: >-
  DevLoop (default): invoke the autonomous devloop engine for a machine-verifiable
  build or debug goal. Use when the user says devloop, DevLoop, or wants an isolated
  fail-closed build with executable tests. Thin shim only — resolve or bootstrap the
  engine, then exec scripts/devloop-run. Portable on Grok, Claude, Codex, and Hermes.
  NOT the demoted offline evidence skill devloop-native. NOT host-agent reimplementation
  of DEFINE/PROVE/BUILD.
version: 0.4.1
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

# DevLoop (engine shim)

**Package leaf:** `devloop-run`  
**User-facing name:** **DevLoop** / **devloop**

This card does **not** implement the loop. It **resolves / bootstraps / execs** the
same engine as Hermes (`scripts/devloop_cli.py` → DEFINE → PROVE → BUILD →
DELIVER+LEARN). See [references/product-default.md](references/product-default.md).

## When to use

- One coherent build or debug goal with machine-checkable success (tests / commands)
- Prefer isolated worktree loop + fail-closed delivery over hand-editing
- User says **devloop**, **DevLoop**, or “run the engine on …”

## When not to use

- Prompt/content optimization, subjective design, trivial one-line edits
- Offline freeze/prove/stop **only** without the engine → optional demoted
  **`devloop-native`** (not this skill; not “DevLoop”)
- Expecting the engine without bootstrap or a pin/seed on a fresh machine

## Step 0 — banner

First line of a DevLoop run:

```text
DevLoop — mode=engine host=<this-host> engine=<resolved-or-pending>
```

No banner ⇒ this skill did not run.

## Agent procedure (strict)

1. Emit the banner.
2. Resolve package root (directory containing this `SKILL.md`).
3. Ensure engine:  
   `bash "$SKILL_ROOT/scripts/devloop-run" --setup`  
   On exit **2**, report the script’s next steps (install pin, auth, transport) —
   **do not** implement phases yourself and **do not** fall back to `devloop-native`
   as DevLoop.
4. Invoke:  
   `bash "$SKILL_ROOT/scripts/devloop-run" -- --repo <ABS_PATH> "<goal>"`  
   (omit `--repo` only when a scratch workspace is the deliverable; pass through
   other engine flags the user requested, e.g. `--json`, `--keep-branch`).
5. Report **engine** stdout and exit code. COMPLETE only when the engine exits **0**
   and (if `--json`) delivery/terminal fields match the engine contract.
6. **Forbidden:** host agent inventing charter/phases/BUILD; rewriting acceptance
   tests outside the engine; claiming `mode: native` receipts as DevLoop success.

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
| Grok | skill-dir install | host-local engine + **Grok transport** (no Hermes required for parity target) |
| Claude Code | skill-dir and/or marketplace plugin | resolve/bootstrap; transport matrix TBD |
| Codex | skill-dir install | resolve/bootstrap; transport matrix TBD |
| Hermes | card optional; engine leaf stays `devloop` | Hermes transport default |

**Honesty:**

- Card install ≠ engine install ≠ successful COMPLETE.
- **`--setup` / `--probe`** are multi-host (bootstrap host-local engine from pin or seed).
- **Hermes host:** Hermes model transport (`HERMES_BIN`) is the default for engine roles.
- **Grok host (parity target):** Grok model transport; Hermes must **not** be required.
  Until the engine pin includes Grok transport, fail closed (exit 2) with next steps —
  never reimplement the loop in the host agent.
- Hermes skillhub leaf name `devloop` is never overwritten by this card.

See [references/host-matrix.md](references/host-matrix.md) and
[references/bootstrap.md](references/bootstrap.md).

## Bootstrap (host-local engine)

Default root: `${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}/devloop`.

Pinned release: [references/engine-pin.json](references/engine-pin.json) (`url` + `sha256`).  
Publish surface: GitHub Release assets on **skill-craft** (`devloop-engine-v*`).  
Packaging: `scripts/package-devloop-engine.sh --from DIR --version X.Y.Z`.

Requires **Python 3** on PATH for setup (marker + safe extract). Prefer `curl` or
`wget` for HTTPS pin download, and `shasum` for verification.

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
| 0 | Probe/setup ok, or engine invoked successfully (engine exit 0) |
| 2 | Engine missing / bootstrap refused / needs human / transport missing |
| other | Pass-through from engine CLI |

## Binding surfaces

| Surface | Env / default |
|---------|----------------|
| Prefer engine | `DEVLOOP_HOME` |
| Host-local engine | `DEVLOOP_DATA_HOME/devloop` → `~/.local/share/devloop` |
| Release pin | `DEVLOOP_ENGINE_PIN` → card `references/engine-pin.json` |
| Override URL/sha | `DEVLOOP_ENGINE_URL`, `DEVLOOP_ENGINE_SHA256` |
| Bootstrap inject | `DEVLOOP_BOOTSTRAP_CMD` (tests / custom) |
| Legacy Hermes seed | `HERMES_HOME/.../devloop`, `~/.hermes/.../devloop` |
| Model transport | Engine: `DEVLOOP_TRANSPORT`, `GROK_BIN`, `HERMES_BIN` (see engine config) |
