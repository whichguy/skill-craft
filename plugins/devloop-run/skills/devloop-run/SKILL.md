---
name: devloop-run
description: >-
  DevLoop (default): invoke the autonomous engine for a machine-verifiable
  build or debug goal. Use when the user says devloop, DevLoop, /devloop-run,
  or (on Grok) /devloop, or wants an isolated fail-closed build with executable
  tests. Thin shim: resolve or bootstrap the engine, then exec scripts/devloop-run.
  Runtime hosts: Grok and Hermes. Claude/Codex: discovery and bootstrap only
  (transport TBD). NOT the demoted offline skill devloop-native. NOT host-agent
  DEFINE/PROVE/BUILD.
when-to-use: >-
  User says devloop or DevLoop, runs /devloop-run or Grok /devloop, or asks for
  an isolated fail-closed loop with tests. Do not use for prompt tuning, visual
  design, or offline freeze/prove/stop (that is devloop-native).
argument-hint: repo path and goal
version: 0.4.4
license: MIT
platforms:
  - linux
  - macos
metadata:
  short-description: Run the DevLoop engine (shim only)
  skill_craft:
    kind: script-backed
    engine: true
    runtime_hosts:
      - hermes
      - grok
---

# DevLoop

Shim only. The engine does DEFINE → PROVE → BUILD → DELIVER+LEARN.
See [references/product-default.md](references/product-default.md).

`SKILL_ROOT` is the directory containing **this** `SKILL.md` (installed skill-dir
or plugin path, not the physical checkout behind a symlink).

## When to use

- One coherent build or debug goal with machine-checkable success
- Isolated worktree loop over hand-editing
- User says **devloop**, **DevLoop**, `/devloop-run`, or Grok `/devloop`

## When not to use

- Prompt/content optimization, subjective design, trivial one-line edits
- Offline freeze/prove/stop only → **`devloop-native`** (not DevLoop)
- Expecting the engine without `--setup` / pin on a fresh machine

## Procedure

Do **not** invent the identity banner or lifecycle lines. Run the script; relay **stderr**.

```text
SKILL_ROOT = directory containing this SKILL.md
bash "$SKILL_ROOT/scripts/devloop-run" --setup
bash "$SKILL_ROOT/scripts/devloop-run" -- --repo <ABS_PATH> "<goal>"
```

Omit `--repo` only when a scratch workspace is the deliverable. Pass through
engine flags the user requested (`--json`, `--keep-branch`). `--host grok` is an
override, not required when invoking via a Grok skill-dir path.

**New-repo designation — one signal, no guessing.** `--repo PATH` always wins.
If `--repo` is omitted and the goal designates a new repo (case-insensitive:
`new repo`, `new repository`, `separate repo`, `fresh repo`, `create a repo`,
`newly created repo`), still **omit** `--repo` — the shim's existing scratch
mechanism (a fresh git repo under the write-safe root, worktreed) *is* the
new-repo deliverable. Do not reuse the last `--repo` path, do not infer cwd,
do not invent `~/src/<slug>`. The shim prints
`[devloop-run] STATE target=scratch reason=new_repo_designated` (or
`reason=default` when there is no designation) so relay that line as-is.

- Relay stderr. Do not rewrite `[devloop-run] BEFORE` / `AFTER` / `STATE` lines.
- Cite identity line (`DevLoop — mode=engine …`), last `STATE`, and exit code.
- **COMPLETE** only if `AFTER exec exit=0` (engine exit 0). Exit **2** = stop;
  report last `STATE` and the script’s next steps.
- If the stream has no `[devloop-run]` lines, this skill did not run.

Host matrix, bootstrap, and resolve order:
[references/host-matrix.md](references/host-matrix.md),
[references/bootstrap.md](references/bootstrap.md).
Consumer-channel COMPLETE is engine policy (`references/consumer-channel-verification.md`
under the engine tree).

## Forbidden

Host agent inventing charter/phases/BUILD; rewriting acceptance tests outside
the engine; claiming `mode: native` receipts as DevLoop; silently pushing after
COMPLETE; falling back to **devloop-native** as DevLoop; inventing a `--repo`
path (last-used, `~/src/<slug>`, or cwd) when the user designated a new repo.
