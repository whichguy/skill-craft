---
name: steer
description: >-
  Session harness (not DevLoop): spec once, one backchain sequence plan, then
  walk ready steps by emitting a paste-ready /goal per running id. Use when the
  user says steer, session harness, or what's the next step. Never invoke
  /devloop. After every increment invoke skill steer-next — do not rely on chat
  memory.
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
      - session-sm
---

# Steer (session harness, not DevLoop)

**Package leaf:** `steer`

Banner (first line of any invoke):

```text
steer — session harness (not DevLoop)
```

`steer` owns session state. It does not implement the product, does not claim
DevLoop COMPLETE, and must not invoke `/devloop`. Planning requires the sibling
**backchain** skill (fail-closed via `dep_roots.backchain`).

Practices: skill-craft `docs/LOOP-ENGINEERING.md` (Steer session track).

## When to use

- User says **steer** or wants an artifact-backed next step
- A run already has `.steer/` and context may be gone
- Spec once → sequence plan once → walk via `/goal` → session residual

## When not to use

- Bare **devloop** / DevLoop → skill **`devloop`**
- Offline freeze/prove/stop → **`evidence-gates`**
- Packet reprint only → skill **`steer-next`**
- Residual×2 engine alone → **`review-coverage`** / **`review-converge`**

## Procedure

1. Print the banner `steer — session harness (not DevLoop)`.
2. `SKILL_ROOT` = directory containing this `SKILL.md`.
3. `python3 "$SKILL_ROOT/scripts/steer" init --prompt "…" --run-dir DIR` once
   if there is no live `state.json`. `--implementer host` is the default.
   `--implementer devloop` fails closed.
4. **Invoke skill `steer-next`** (or run its CLI). Follow the whole packet.
5. Do only the **Next prompt**. Write only the canonical files it names.
6. Run the **When done invoke** lines (`update` / `complete-step` / `clear-step`
   on this CLI). `steer next` already claimed ready ids `running`.
7. Invoke **steer-next** again. Repeat until the packet says stop.
8. **Never** invoke skill `devloop`, slash `/devloop`, or `steer capture` of
   `devloop-run`.

## CLI

```sh
CLI="$SKILL_ROOT/scripts/steer"
python3 "$CLI" init [--prompt TEXT] [--run-dir DIR] [--implementer host] [--force] [--bound-plan PATH] [--repo PATH]
python3 "$CLI" next [--run-dir DIR]
python3 "$CLI" update --run-dir DIR --to PHASE [--reason TEXT] [--resume-to PHASE]
python3 "$CLI" status [--run-dir DIR]
python3 "$CLI" start-step --run-dir DIR --id ID
python3 "$CLI" complete-step --run-dir DIR --id ID
python3 "$CLI" clear-step --run-dir DIR --id ID
```

| Exit | Meaning |
|------|---------|
| 0 | Success |
| 2 | Blocked (illegal transition, missing artifact, hash drift, unsupported implementer) |
| 64 | Usage |

State lives under the **run dir** (default `cwd/.steer`), never inside this
package.

## Host matrix

See [references/host-matrix.md](references/host-matrix.md). Discovery ≠ execution.
