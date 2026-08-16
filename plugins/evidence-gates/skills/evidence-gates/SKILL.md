---
name: evidence-gates
description: >-
  Optional offline evidence gates (freeze/prove/stop with guard digests) for
  machine-checkable red→green contracts without the autonomous engine. Use when
  the user says evidence-gates, offline evidence gates, freeze prove stop, or
  host-native verify gates. NOT the autonomous engine product.
allowed-tools: all
version: 0.2.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: software-development
    tags:
      - portable-skill
      - multi-host
      - evidence-gates
---

# Evidence gates (optional, not DevLoop)

**Package leaf:** `evidence-gates`
**Status:** not the default DevLoop product.

Default DevLoop is the **engine** via skill **`devloop`**. This package only
freezes charters and re-runs argv verifiers.

Host-native **DEFINE → PROVE → BUILD → STOP** evidence loop. The **current host
agent** may implement BUILD; scripts only say yes/no with **guard digests**.

**Primary interface:** `/evidence-gates` or explicit “offline evidence gates.”
Do **not** treat bare “devloop” as this skill.

**Invariant:** the script may say **no**, but it may never **do the work** — and
what it says yes to must include **guard file digests**, not only command lines.

## Not for

- User asks for **DevLoop** / autonomous machine-verifiable **build** → use
  skill **`devloop`** / engine (never substitute this skill as DevLoop)
- Hermes engine skill leaf `devloop` (different product)
- Cross-harness transport as the loop
- Subjective design-only work with no machine-checkable verifier

## Step 0 — banner

```text
evidence-gates — mode=native host=<this-host> root=<package-root> charter=<path-or-pending>
```

(First line must make clear this is **not** default DevLoop / mode=engine.)

## Phases

| Phase | Actor | Gate |
|-------|--------|------|
| **DEFINE** | Agent writes charter JSON | `scripts/evidence-gates freeze --charter … --repo …` |
| **PROVE** | Agent orchestrates | `… prove --run-dir …` — baseline; **change** criteria must be observed **red** |
| **BUILD** | Agent + **this host’s** tools only | No CLI `build` / `run` |
| **STOP** | Agent requests evidence | `… stop --run-dir …` — re-check digests; re-run **all** verifiers; script writes receipt |

Labels: `native-complete` | `native-blocked` | `native-aborted` | `misrouted`.

COMPLETE only if `stop` exit 0 and `receipt.json` has `"mode": "native"` and `"status": "PASS"`.

## Charter (Layer 0)

See `references/loop.md` and `references/charter-v1.schema.json`.

- Verifiers are **argv arrays** only (no shell `-c`).
- Each criterion has `role`: `change` | `regression`.
- `guard_paths` content is hashed at freeze; drift → blocked.

## CLI (optional hard gates)

```sh
CLI="$SKILL_ROOT/scripts/evidence-gates"
python3 "$CLI" self-check
python3 "$CLI" freeze --charter CHARTER.json --repo REPO [--run-dir REPO/.evidence-gates/run]
python3 "$CLI" prove  --run-dir …
python3 "$CLI" stop   --run-dir …
python3 "$CLI" doctor [--repo REPO]
```

Resolve `SKILL_ROOT` from the installed skill directory that contains this `SKILL.md`.

| Exit | Meaning |
|------|---------|
| 0 | Success / green |
| 1 | Verifiers ran and failed |
| 2 | Blocked (drift, missing tool, never_red, …) |
| 64 | Usage |

State lives under the **target repo** (default `.evidence-gates/`), never inside the skill package.

## Procedure (agent)

1. Emit banner (evidence / mode=native — not mode=engine).
2. **DEFINE** — charter with checkable criteria; freeze.
3. **PROVE** — run prove; if all `change` criteria are green, stop with already-green / redefine.
4. **BUILD** — implement with host tools until verifiers can pass.
5. **STOP** — stop CLI; report receipt.

If the user wanted full DevLoop, redirect to skill **`devloop`** instead of completing this path.

## Host matrix

See `references/host-matrix.md`. Discovery ≠ execution. Same package on all hosts.
