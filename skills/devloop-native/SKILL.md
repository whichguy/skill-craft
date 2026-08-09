---
name: devloop-native
description: >-
  DevLoop: host-native DEFINE→PROVE→BUILD→STOP using the current agent's tools
  and optional local verify gates. Use when the user says devloop, DevLoop,
  host-native loop, or /devloop-native. NOT the Hermes engine leaf "devloop",
  NOT the engine launcher skill, NOT peer-harness transport.
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
      - devloop
---

# DevLoop

**Package leaf:** `devloop-native` (install path; not the Hermes engine).

Host-native **DEFINE → PROVE → BUILD → STOP**. The **current host agent** is the
loop. Optional CLI helpers only freeze and re-run evidence.

**Primary interface:** invoke this skill like any other skill (say **devloop** /
**DevLoop**). Do **not** require the user to run shell scripts. CLI gates are
optional hard evidence for COMPLETE.

**Invariant:** the script may say **no**, but it may never **do the work** — and
what it says yes to must include **guard file digests**, not only command lines.

## Not for

- Hermes engine skill leaf `devloop` (different product; do not fall back)
- Engine launcher / bootstrap skill that shells to another runtime
- Cross-harness transport (calling another host’s CLI as the loop)
- Subjective design-only work with no machine-checkable verifier

## Step 0 — banner

First line of a DevLoop run:

```text
DevLoop — mode=native host=<this-host> root=<package-root> charter=<path-or-pending>
```

No banner ⇒ this skill did not run (possible misroute to the engine).

## Phases

| Phase | Actor | Gate |
|-------|--------|------|
| **DEFINE** | Agent writes charter JSON | `scripts/devloop-native freeze --charter … --repo …` |
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

Package-root relative (works under symlink install and Hermes copy):

```sh
# Python entrypoint (do NOT wrap with `bash` — bash ignores the shebang)
CLI="$SKILL_ROOT/scripts/devloop-native"
python3 "$CLI" self-check
# or, if +x: "$CLI" self-check
python3 "$CLI" freeze --charter CHARTER.json --repo REPO [--run-dir REPO/.devloop-native/run]
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

State lives under the **target repo** (default `.devloop-native/`), never inside the skill package.

## Procedure (agent)

1. Emit banner. Load `references/loop.md` if detail needed.
2. **DEFINE** — charter with checkable criteria; freeze.
3. **PROVE** — run prove; if all `change` criteria are green, stop with already-green / redefine (do not fake BUILD).
4. **BUILD** — implement with host tools until verifiers can pass; do not edit frozen charter or weaken guard files (redefine instead).
5. **STOP** — stop CLI; report receipt. If exit ≠ 0, fix or HUMAN_REVIEW with real reason.

Never suggest peer harness CLIs or the engine launcher as a fallback for this skill.

## Host matrix

See `references/host-matrix.md`. Discovery ≠ execution. Same package on all hosts.
