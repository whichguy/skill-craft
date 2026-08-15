---
name: devloop-run
description: >-
  DevLoop (default): invoke the autonomous devloop engine for a machine-verifiable
  build or debug goal. Use when the user says devloop, DevLoop, or wants an isolated
  fail-closed build with executable tests. Thin shim only — resolve or bootstrap the
  engine, then exec scripts/devloop-run. Portable on Grok, Claude, Codex, and Hermes.
  NOT the demoted offline evidence skill devloop-native. NOT host-agent reimplementation
  of DEFINE/PROVE/BUILD.
version: 0.4.2
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
---

# DevLoop (engine shim)

**Package leaf:** `devloop-run`  
**User-facing name:** **DevLoop** / **devloop**

This card does **not** implement the loop. It **resolves / bootstraps / execs** the
engine (`scripts/devloop_cli.py` → DEFINE → PROVE → BUILD → DELIVER+LEARN).
See [references/product-default.md](references/product-default.md).

`SKILL_ROOT` is the directory containing **this** `SKILL.md` (the installed skill-dir
or plugin path, not the physical checkout behind a symlink).

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
2. Set `SKILL_ROOT` to the directory containing this `SKILL.md`.
3. On **Grok Build**, pass `--host grok` (or `export DEVLOOP_HOST=grok`) on every
   card invoke. Do not rely on `pwd -P`.
4. Ensure engine:  
   `bash "$SKILL_ROOT/scripts/devloop-run" --host grok --setup`  
   (omit `--host grok` only on Hermes/Claude/Codex; on those hosts pass `--host`
   for that host or let install-path detect run).  
   On exit **2**, report the script’s next steps (install pin, auth, transport) —
   **do not** implement phases yourself and **do not** fall back to `devloop-native`
   as DevLoop.
5. Invoke:  
   `bash "$SKILL_ROOT/scripts/devloop-run" --host grok -- --repo <ABS_PATH> "<goal>"`  
   (omit `--repo` only when a scratch workspace is the deliverable; pass through
   other engine flags the user requested, e.g. `--json`, `--keep-branch`).
6. Report **engine** stdout and exit code. COMPLETE only when the engine exits **0**
   and (if `--json`) delivery/terminal fields match the engine contract. Never treat
   a fail-closed exit **2** as success.
7. **Forbidden:** host agent inventing charter/phases/BUILD; rewriting acceptance
   tests outside the engine; claiming `mode: native` receipts as DevLoop success;
   silently pushing after COMPLETE to “finish” delivery.

## Canonical invoke

```sh
SKILL_ROOT="${SKILL_ROOT:-$HOME/.grok/skills/devloop-run}"   # installed path
bash "$SKILL_ROOT/scripts/devloop-run" --host grok --setup
bash "$SKILL_ROOT/scripts/devloop-run" --host grok --probe
bash "$SKILL_ROOT/scripts/devloop-run" --host grok -- \
  --repo /abs/path/to/repo "Add normalize empty check"
```

Hermes host: `--host hermes` (or omit; Hermes skill-dir / seed detect).  
Claude/Codex: `--host claude` / `--host codex` (bootstrap only; transport TBD).

After skill-dir install, package root is `~/.grok/skills/devloop-run` (Grok),
`~/.claude/skills/devloop-run` (Claude), or `~/.codex/skills/devloop-run` (Codex).

## Host matrix

| Host | Discovery (skill card) | Execution |
|------|------------------------|-----------|
| Grok | skill-dir install | host-local engine + **Grok transport**; Hermes must not be required. Pin 0.2.0 declares `transports` including `grok`. |
| Claude Code | skill-dir and/or marketplace plugin | resolve/bootstrap; transport TBD |
| Codex | skill-dir install | resolve/bootstrap; transport TBD |
| Hermes | card optional; engine leaf stays `devloop` | Hermes transport default |

**Honesty:** card install ≠ engine install ≠ COMPLETE. `--setup` / `--probe` bootstrap
host-local from the pin. Hermes skillhub leaf `devloop` is never overwritten.

See [references/host-matrix.md](references/host-matrix.md) and
[references/bootstrap.md](references/bootstrap.md).

## Truth table

| Host | Resolve order |
|------|----------------|
| `grok` / `claude` / `codex` | `DEVLOOP_HOME` → host-local only → pin/URL/CMD bootstrap. **No** Hermes seed unless `DEVLOOP_ALLOW_HERMES_SEED=1`. |
| `hermes` / `auto` | `DEVLOOP_HOME` → host-local → Hermes/`/opt/data` seed → bootstrap |

| Situation | Result |
|-----------|--------|
| Valid `DEVLOOP_HOME` | Use it (no bootstrap) |
| Host-local engine present | Use `…/devloop` |
| Missing engine + pin URL + matching sha256 | Bootstrap host-local; write marker last |
| Missing engine + `--no-bootstrap` | Exit **2** |
| Grok host, pin/engine lacks `grok` transport | Exit **2** (do not improvise) |
| `--setup` | Ensure + print `engine=…` |
| `--probe` | Resolve only; does not bootstrap |

Bootstrap encyclopedia (sha256, extract, locks, markers): [references/bootstrap.md](references/bootstrap.md).

## Exit codes (card preflight)

| Exit | Meaning |
|------|---------|
| 0 | Probe/setup ok, or engine invoked successfully (engine exit 0) |
| 2 | Engine missing / bootstrap refused / needs human / transport missing |
| other | Pass-through from engine CLI |

## Loop engineering

When the goal delivers something a **consumer receives**, COMPLETE requires
**channel-faithful** oracles (observe that channel via the production path), not
source greps. Unobservable required channels must block, not skip-green. Engine
reference: `references/consumer-channel-verification.md` under the engine tree.
