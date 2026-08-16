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
argument-hint: goal
version: 0.4.5
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

User-facing form is `/devloop <plain English>`. Do **not** invent
DEFINE/PROVE/BUILD or lifecycle lines. The host **interpolates** argv from the
plain text, **prints the interpolation**, then execs the shim and relays
**stderr**.

```text
/devloop <goal>
```

Headless:

```text
grok -p '/devloop <goal>' --always-approve
```

### 1. Interpolate

Read the plain-English request and fill in only these argv pieces — never
invent a fourth, and never write product files (that is **not** BUILD):

| Text signal | Host fills in |
|---|---|
| `new repo` / `new repository` / `separate repo` / `fresh repo` / `create a repo` / `newly created repo` / no path named | omit `--repo` (scratch) |
| an absolute path the user named | `--repo PATH` |
| a checkable "done" sentence | `verify_cmd exactly [...]`; add `--lang command` when that oracle is a shell/node argv list |
| the user already typed `--repo` / `--lang` / `verify_cmd exactly` | those win verbatim — do not re-derive them |

**Fail-closed:** no machine-checkable done in the request → **stop and ask**
for one. Do not invent `pytest`, a path, or a cwd to make something checkable.
Never infer cwd or reuse the last `--repo` path.

### 2. Print the interpolation

Before exec, print the exact argv constructed, e.g.:

```text
interpolated: --lang command "new repo. Create result.txt containing exactly one line: devloop-ok verify_cmd exactly [\"test\",\"-f\",\"result.txt\"]"
```

### 3. Exec

`SKILL_ROOT` is the directory containing this SKILL.md. Exec:

```text
bash "$SKILL_ROOT/scripts/devloop-run" -- --lang command "<goal + verify_cmd exactly [...]>"
```

Omit `--lang` / `--repo` from the exec line when step 1 said to omit them.
Pass through only flags the user typed plus what step 1 interpolated
(`--repo`, `--lang`, `--keep-branch`, `--json`). `--setup` once on a fresh
machine. `--host grok` is an override, not required from a Grok skill-dir
path. Shim STATE lines (`target=scratch reason=new_repo_designated`,
`lang=… reason=explicit|none`) label what the shim received — they do not
re-derive argv; that already happened in step 1.

### 4. Relay, don't re-run the loop

- Relay `[devloop-run] BEFORE` / `AFTER` / `STATE` as-is.
- Cite identity (`DevLoop — mode=engine …`), last `STATE`, and exit code.
- **COMPLETE** only if `AFTER exec exit=0`. Exit **2** = stop.
- If the stream has no `[devloop-run]` lines, this skill did not run.

Host matrix, bootstrap, and resolve order:
[references/host-matrix.md](references/host-matrix.md),
[references/bootstrap.md](references/bootstrap.md).
Consumer-channel COMPLETE is engine policy (`references/consumer-channel-verification.md`
under the engine tree).

## One controller, not Grok `/goal`

DevLoop is **one controller**: the engine owns DEFINE → PROVE → BUILD. This
card and its `/devloop` alias must **not** invoke Grok `/goal` or `/loop` —
`/goal` retries exit 2 and erase `HUMAN_REVIEW`, duplicating the engine's own
retry ladder. Goal-engineering shape (objective + done) lives *in* the
`/devloop` prompt text, not as a second slash. Keep
`disable-model-invocation: true` on the Grok `/devloop` alias. The shim's own
re-entry guard (`DEVLOOP_DEPTH` / `DEVLOOP_NESTING`; see
`scripts/devloop-run --help`) refuses nested invokes — interpolation happens
once, host-side, before that guard is ever reached.

## Forbidden

Host agent inventing charter/phases/BUILD; interpolating a fourth argv piece
beyond `--repo`/`--lang`/`verify_cmd`; invoking Grok `/goal` or `/loop`;
rewriting acceptance tests outside the engine; claiming `mode: native`
receipts as DevLoop; silently pushing after COMPLETE; falling back to
**devloop-native** as DevLoop; inventing a `--repo` path (last-used,
`~/src/<slug>`, or cwd) when the user designated a new repo; declaring
COMPLETE without both engine exit 0 and `AFTER exec exit=0`.
