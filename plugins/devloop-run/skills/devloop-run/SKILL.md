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
argument-hint: plain-English goal (flags optional)
version: 0.4.7
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

**Default user form is flags-free.** The skill argument is the rest of the
line after `/devloop` (or the natural-language ask). **Parse that text** and
**interpolate** engine argv — do **not** require the user to pass `--repo`,
`--lang`, `verify_cmd exactly`, or `--setup-spec`. Those are optional
overrides when the user already typed them.

```text
/devloop create a standalone Battleship Google Apps Script game
```

Headless:

```text
grok -p '/devloop create a standalone Battleship Google Apps Script game' --always-approve
```

Do **not** invent DEFINE/PROVE/BUILD or lifecycle lines. The host
**parses skill arguments**, **interpolates** argv values, **prints the
interpolation**, then execs the shim and relays **stderr**.

### 1. Parse skill arguments → compile → interpolate

Treat the entire skill argument string as the goal. **Parse** it for
signals (product, paths, “new repo”, GAS/mcp, named files/contents). Then
**compile** one request blob (still not BUILD): embed **/goal-shaped phase
intentions** — objective + complete-when — as *text in that blob*, not as
host slash invokes. Then **interpolate** argv **values** from the parsed
blob (the user did not have to type those flags).

#### Phase complete-whens (dialect, not a second controller)

Fold these four (plus SETUP when the user named a new external project) into
the request so DEFINE/PROVE/BUILD/DELIVER share one contract:

| Phase | Intention | Complete when |
|-------|-----------|----------------|
| SETUP (only if user named new GAS / mcp-gas / new hosted project) | Provision git + identity + oracle scaffold | Receipt exists; named product module still absent |
| DEFINE | Admit one charter for this request | 0 blocking questions; every named behavior is in DoD or explicit non-DoD; every integration criterion has `verify_cmd` |
| PROVE | Freeze the observer | Judges trust the explicit `verify_cmd` (or collected tests); no extra criteria off-request |
| BUILD | Implement until the frozen oracle is green | `verify_cmd` exit 0; do not edit `verify_cmd` |
| DELIVER | Land only the verified tree | `delivery_accepted`; raw COMPLETE without that is not success |

If the user named a new GAS/mcp-gas project and did not already pass
`--setup-spec` / `setup exactly:`, compile a `setup exactly: {…}` object
into the **request string** (kind, title, module, oracle). Do **not**
MCP-create or write product files on the host.

**Interpolate** argv values from the parsed skill arguments. Never invent a
fourth *kind* of flag, and never write product files (that is **not** BUILD).
The user is not required to type any of these:

| Parsed from skill arguments | Host interpolates |
|---|---|
| `new repo` / `new repository` / `separate repo` / `fresh repo` / `create a repo` / `newly created repo` / no path named | omit `--repo` (scratch) |
| an absolute path the user named | `--repo PATH` |
| a product or “done” they described (file + contents, GAS module + live oracle, etc.) | `verify_cmd exactly [...]` derived from that description; prefer a **content-checking** oracle (not existence-only) when they named exact file contents — e.g. `["bash","-c","test \"$(cat FILE)\" = VALUE"]`, not just `["test","-f","FILE"]`; add `--lang command` when that oracle is a shell/node argv list |
| new GAS / mcp-gas / new hosted project (and they did not type `--setup-spec`) | `setup exactly: {…}` inside the request string (kind, title, module, oracle) — still no host MCP-create |
| the user already typed `--repo` / `--lang` / `verify_cmd exactly` / `--setup-spec` / `setup exactly:` | those win verbatim — do not re-derive them. Typed `--setup-spec` is pass-through |

**Fail-closed:** after parsing, you still cannot derive any checkable done
from the skill arguments → **stop and ask** for what “done” looks like
(not for flags). Do not invent `pytest`, a path, or a cwd. Never infer cwd
or reuse the last `--repo` path.

### 2. Print the interpolation

Print the interpolation (exact argv constructed) before exec, e.g.:

```text
interpolated: --lang command "new repo. Create result.txt containing exactly one line: devloop-ok verify_cmd exactly [\"bash\",\"-c\",\"test \\\"$(cat result.txt)\\\" = devloop-ok\"]"
```

An existence-only oracle (`["test","-f","result.txt"]`) does **not** satisfy an
exact-content done sentence — the engine's judge will fail-closed on it
(`HUMAN_REVIEW`: test fault, not a re-IMPLEMENT bug). Interpolate content
checks, not just existence, whenever the sentence names a value.

### 3. Exec

`SKILL_ROOT` is the directory containing this SKILL.md. Exec:

```text
bash "$SKILL_ROOT/scripts/devloop-run" -- --lang command "<goal + verify_cmd exactly [...]>"
```

Omit `--lang` / `--repo` from the exec line when step 1 said to omit them.
Pass through only flags the user typed plus what step 1 interpolated
(`--repo`, `--lang`, `--keep-branch`, `--json`, `--setup-spec`). `--setup`
once on a fresh machine (engine **install**, not environment SETUP).
`--host grok` is an override, not required from a Grok skill-dir path.
Shim STATE lines (`target=scratch reason=new_repo_designated`,
`lang=… reason=explicit|none`) label what the shim received — they do not
re-derive argv; that already happened in step 1.

### 4. Relay, don't re-run the loop

- Relay `[devloop-run] BEFORE` / `AFTER` / `STATE` as-is.
- Cite identity (`DevLoop — mode=engine …`), last `STATE`, and exit code.
- **COMPLETE** only if `AFTER exec exit=0`. Exit **2** = stop; compile
  `— ANSWERS:` from the engine `?` lines and re-exec **once** if the user
  answers — do not wrap that in a host goal harness.
- If the stream has no `[devloop-run]` lines, this skill did not run.
- After **exit 0** only: residual polish (UI, docs) may be offered as a
  separate host residual campaign. Never start that campaign on exit 2.

Host matrix, bootstrap, and resolve order:
[references/host-matrix.md](references/host-matrix.md),
[references/bootstrap.md](references/bootstrap.md).
Consumer-channel COMPLETE is engine policy (`references/consumer-channel-verification.md`
under the engine tree).

## One controller; `/goal`-shaped directives only

DevLoop is **one controller**: the engine owns DEFINE → PROVE → BUILD →
DELIVER. This card and its `/devloop` alias must **not** invoke the host
goal harness or `/loop` as the loop (`grok -p` of those slashes is forbidden
— D37). Those harnesses retry exit 2 and erase `HUMAN_REVIEW`.

**Do** use `/goal`-shaped **directives** (intention + complete-when) inside
the compiled `/devloop` request — see the phase table in step 1. That is
goal-engineering *vocabulary*, not a second controller. Keep
`disable-model-invocation: true` on the Grok `/devloop` alias. The shim's
re-entry guard (`DEVLOOP_DEPTH` / `DEVLOOP_NESTING`) refuses nested invokes.

## Forbidden

Host agent inventing charter/phases/BUILD; interpolating a fourth argv piece
beyond `--repo`/`--lang`/`verify_cmd` (typed `--setup-spec` is pass-through);
invoking the host goal harness or `/loop` to drive the loop; rewriting
acceptance tests outside the engine; claiming `mode: native` receipts as
DevLoop; silently pushing after COMPLETE; falling back to **devloop-native**
as DevLoop; inventing a `--repo` path (last-used, `~/src/<slug>`, or cwd)
when the user designated a new repo; declaring COMPLETE without both engine
exit 0 and `AFTER exec exit=0`; MCP-create or product-file writes on the host.
