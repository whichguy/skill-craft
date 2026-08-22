---
name: devloop
description: >-
  DevLoop (default): invoke the autonomous engine for a machine-verifiable
  build or debug goal. Use when the user says devloop, DevLoop, /devloop, or
  wants an isolated fail-closed build with executable tests. Thin shim: resolve
  or bootstrap the engine, then exec scripts/devloop-run. Runtime hosts: Grok
  and Hermes. Claude/Codex/Cursor: discovery and bootstrap only (transport TBD).
  NOT the demoted offline skill evidence-gates. NOT host-agent DEFINE/PROVE/BUILD.
when-to-use: >-
  User says devloop or DevLoop, runs /devloop, or asks for an isolated
  fail-closed loop with tests. Do not use for prompt tuning, visual design, or
  offline freeze/prove/stop (that is evidence-gates).
argument-hint: plain-English goal
version: 0.5.1
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
- User says **devloop**, **DevLoop**, or `/devloop`

## When not to use

- Prompt/content optimization, subjective design, trivial one-line edits
- Offline freeze/prove/stop only → **`evidence-gates`** (not DevLoop)
- Expecting the engine without `--setup` / pin on a fresh machine

## Handshake

**Default is flags-free.** The skill argument is the rest of the line after
`/devloop`. **Parse that text** — do **not** require the user to pass
`--repo`, `--lang`, `verify_cmd exactly`, or `--setup-spec`. The user is
**not required to type** those. **Print the interpolation**, then exec the
shim and relay **stderr**.

**Every run is an independent worktree.** Omit `--repo` unless the user
named a path (scratch). The engine always cuts a unique worktree — never
edit cwd, the last `--repo`, or a prior checkout. Never infer cwd.

```text
/devloop <goal>
grok -p '/devloop <goal>' --always-approve
```

### 1. Consider session MCP

**Review session MCP before planning.** **Inventory** this session (no
catalog, no install). Prefer a matching **read-capable** tool over inventing
operator tooling. Read-capable = observes the *external* truth in the
done-sentence (deployed URL, live exec, hosted artifact, remote API). A
generic **fs-only** MCP seeing `result.txt` does **not** count. Transient
errors: retry once, then unmatched. Never silent-skip a match.

Reuse a pre-existing CLI/wrapper. **Do not invent a new harness**
(`scripts/*.mjs`). If none: local content-checking `verify_cmd` plus a
concrete request constraint, or fail-closed and ask for a checkable CLI.

**Observe, not act.** Do not implement the product through MCP. Never
fix-then-recheck on the host. **New operator tooling** = committed harness
scripts. Inline `test "$(cat result.txt)" = …` is not tooling.

Print **always**, first matching read-capable tool in session order:

```text
mcp-considered: <server>(<first-matching-read-tool>) | none(<reason>)
mcp-considered: mcp-gas-deploy(list,read) | none(no read-capable session tool matched done-sentence)
```

If a wrapper was chosen: `verify_cmd is the existing MCP-backed CLI <name>; do not write new operator tooling`.
If none: only `do not write new operator tooling` — no generic "prefer MCP".

### 1b. Discover destination contract

When the ask is **hosted** (deploy, live URL, web app, remote runtime),
answer these five slots from discovery — **do not invent a vendor hook**.
Read-only. Do not write the product to “fix” a live error.

1. **identity** — how is a new environment created or selected?
2. **claim** — how does product code attach so inbound work is claimed?
3. **reserved** — which routes / methods / names does the platform already own?
4. **success** — what does a claimed response look like vs yield / empty?
5. **misread** — how do you tell “handlers ran, none claimed” from “platform down”?

**Read** (session order; first hits win): user text → matching session MCP
descriptions / `llmGuidance` → provisioned tree (runtime/bootstrap/README)
→ optional live `status` / HEAD. Unanswered slot = `unknown` or fail-closed
and ask. Worked instances (one destination’s answers) live in
[references/destination-instances.md](references/destination-instances.md),
not as this handshake.

**Print always when hosted:**

```text
env-discovered: <dest-class>: identity=…; claim=…; reserved=…; success=…; misread=…
env-discovered: none(no hosted destination)
```

**Fold** the five bindings into the request string (BUILD constraints), next
to `verify_cmd exactly` / `setup exactly`. Not a fourth argv kind. Typed
user text still wins.

| Ask | Session MCP | mcp-considered (oracle *consider*, not dest-contract) | verify_cmd |
|---|---|---|---|
| hosted/external ask + matching read MCP (example dest: mcp-gas-deploy) | mcp-gas-deploy (list, read) | `mcp-considered: mcp-gas-deploy(list,read)` | existing wrapper if any; else local content check — no new `*verify*` script |
| `result.txt` / empty session | (empty) | `mcp-considered: none(no read-capable session tool matched done-sentence)` | local content check |
| `result.txt` | fs-only MCP | `mcp-considered: none(no read-capable session tool matched done-sentence)` | local content check |

### 2. Interpolate and print

Fill in only these argv pieces — never a fourth *kind*, never write product
files (**not** BUILD):

| Parsed from skill arguments | Host interpolates |
|---|---|
| `new repo` / `new repository` / `separate repo` / `fresh repo` / `create a repo` / `newly created repo` / no path named | omit `--repo` (scratch) |
| an absolute path the user named | `--repo PATH` |
| a checkable "done" sentence, or a product they described (file + contents, hosted module + live oracle) | `verify_cmd exactly [...]`; prefer a **content-checking** oracle when the sentence names exact file contents — e.g. `["bash","-c","test \"$(cat FILE)\" = VALUE"]`, not just `["test","-f","FILE"]`; add `--lang command` when that oracle is a shell/node argv list |
| the ask names a hosted project, session MCP already has an identity/create tool, and they did not type `setup exactly:` or `--setup-spec` | fold `setup exactly: {…}` **inside the request string** so engine SETUP seeds identity/oracle only. Do not write the product. Typed `--setup-spec` is pass-through only |
| the user already typed `--repo` / `--lang` / `verify_cmd exactly` / `--setup-spec` / `setup exactly:` | those win verbatim — do not re-derive them |

**Fail-closed:** still no **checkable done** → **stop and ask** (not for
flags). Do not invent `pytest`, a path, or a cwd. Never infer cwd or reuse
the last `--repo` path.

Print before exec (both shapes):

```text
interpolated: --lang command "new repo. Create result.txt containing exactly one line: devloop-ok do not write new operator tooling verify_cmd exactly [\"bash\",\"-c\",\"test \\\"$(cat result.txt)\\\" = devloop-ok\"]"
mcp-considered: none(no read-capable session tool matched done-sentence)
env-discovered: none(no hosted destination)

interpolated: --lang command "<hosted goal + folded contract + verify_cmd exactly [...]>"
mcp-considered: <server>(<read-tool>)
env-discovered: <dest-class>: identity=…; claim=…; reserved=…; success=…; misread=…
```

An existence-only oracle does **not** satisfy an exact-content done sentence.

### 3. Exec and relay

```text
bash "$SKILL_ROOT/scripts/devloop-run" -- --lang command "<goal + verify_cmd exactly [...]>"
```

Omit `--lang` / `--repo` when step 2 said to omit them. Pass through only
flags the user typed plus what step 2 interpolated (`--repo`, `--lang`,
`--keep-branch`, `--json`, typed `--setup-spec`). `--setup` once on a fresh
machine (engine **install**). `--host grok` is an override. Shim STATE
(`target=scratch reason=new_repo_designated`, `lang=… reason=explicit|none`)
labels what the shim received.

Relay `[devloop-run] BEFORE` / `AFTER` / `STATE` as-is. Cite identity
(`DevLoop — mode=engine …`), last `STATE`, and exit code. **COMPLETE** only
if `AFTER exec exit=0`. Exit **2** = stop. No `[devloop-run]` lines → this
skill did not run.

**Foreground + prompt.** Do not background the shim or hide `[devloop]`
status in a side log. Keep the exec in this conversation. On the first
`HUMAN_REVIEW` / `NEEDS YOUR INPUT` / `AFTER exec exit=2`, stop and prompt the user
with the engine's reason and the `— ANSWERS:` block. Do not wait
out further automatic attempts in silence, and do not only post a postmortem.

Host matrix / bootstrap: [references/host-matrix.md](references/host-matrix.md),
[references/bootstrap.md](references/bootstrap.md).

## Forbidden

One controller: engine owns DEFINE → PROVE → BUILD. Do not invent
charter/phases/BUILD or a fourth argv piece; `setup exactly:` lives in the
request string. Do not invoke Grok `/goal` or `/loop`. Do not rewrite
acceptance tests, claim `mode: native` as DevLoop, silently push after
COMPLETE, fall back to **evidence-gates**, invent a `--repo` path, reuse cwd or a
prior worktree, write the product on the host, invent a new harness
instead of reviewing session MCP first, add a second COMPLETE gate, or
emit a generic "prefer MCP" constraint, or treat one vendor hook as the
handshake (instance answers live in `references/destination-instances.md`),
or background the shim, or swallow `HUMAN_REVIEW` without prompting.
Goal-engineering shape lives *in* the `/devloop` prompt.
`disable-model-invocation: true` on the Grok alias. Nested invoke
(`DEVLOOP_DEPTH` / `DEVLOOP_NESTING`) is refused.
