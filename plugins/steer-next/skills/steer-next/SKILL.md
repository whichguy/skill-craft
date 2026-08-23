---
name: steer-next
description: >-
  Reprint the steer session packet (and claim newly ready step ids as running).
  Use after every steer increment or when context was wiped. Thin wrapper around
  steer next. No update, no complete-step, no product-tree edits. Not DevLoop.
allowed-tools: all
version: 0.1.0
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

# Steer-next (packet printer)

**Package leaf:** `steer-next`

Banner:

```text
steer-next — reprint the steer packet
```

`steer-next` execs harness `steer next`. It does not accept `update`,
`complete-step`, or `start-step`. It may write `.steer/steps/<id>.json`
`status=running` for newly ready ids (harness bookkeeping).

Requires sibling **steer** (`STEER_ROOT` / `dep_roots.steer`). Missing harness
is exit 2.

## Procedure

1. Print the banner.
2. `SKILL_ROOT` = directory containing this `SKILL.md`.
3. `python3 "$SKILL_ROOT/scripts/steer-next" --run-dir DIR`
4. Follow the whole packet. Then run the harness When done lines.

Never invoke `/devloop`.
