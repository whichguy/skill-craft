# Loop engineering (host practices)

Portable practices for fail-closed loops. This is **documentation**, not a
runtime and not a slash skill. The DevLoop **engine** still owns
DEFINE → PROVE → BUILD → DELIVER+LEARN. Host overlays compose **around**
that loop; they must not become a second controller.

Identical copies (keep in sync):

- `docs/LOOP-ENGINEERING.md`
- `skills/devloop/references/loop-engineering.md`

## Compose graph

| When | Overlay | Role |
|------|---------|------|
| **Before** | `c-plan`; optional `define-done` or `backchain` | Clarify or spec a checkable done sentence. Do not require these on every `/devloop`. |
| **During** | `/devloop` only | One build controller. Engine owns the phases. |
| **After** | `/review-coverage` under host `/goal` | residual×2. Not `/devloop` again, not `/loop`. |

Do **not** nest Grok `/goal` or `/loop` inside `/devloop`. `/goal` owns
adversarial completion; DevLoop already owns `COMPLETE`. Nesting them
creates a second COMPLETE gate (false COMPLETE, silent push).

## Practices

| Practice | Lives in | Must not move to |
|----------|----------|------------------|
| One controller | `/devloop` Forbidden + Grok alias | Nested `/goal` / `/loop` / host BUILD |
| Fail-closed (no invented oracle / cwd / `--repo`) | Card interpolate + engine admission | `/goal` “best effort” complete |
| COMPLETE = `AFTER exec exit=0` only | Card + `test/devloop-run.test.sh` D37 | Second host gate (silent push, `/goal` verify, evidence-gates receipt) |
| Isolated worktree every run | Shim + engine | Review-converge sticky target, cwd reuse |
| Frozen oracle | Engine PROVE/BUILD | Host rewrite of tests |
| Consumer-channel + `require_*` family | Engine `admission_gates.py` | Host skill / destination-contract nouns |
| Checkable done sentence | `/devloop <goal>` text | Host DEFINE/PROVE/BUILD complete-when table |
| residual×2 | `review-coverage` **after** COMPLETE | Engine (≤3 attempt retry is a different grain) |
| Learning after outcome | Engine DELIVER+LEARN | Host commit to “finish” delivery |
| MCP observe-not-act | Card (`references/mcp-consider.md`) | Engine (does not speak MCP) |

`evidence-gates` is offline freeze / prove / build-on-host / stop — **not**
DevLoop. Never fall back to it when the user asked for DevLoop.

## Card maintenance (prompt-align, not more greps)

Future `/devloop` card edits:

1. Put new policy in a **reference** (`mcp-consider.md`,
   `destination-contract.md`, this file), not another paragraph in
   `SKILL.md`.
2. Add **one** hermetic assertion that the reference exists and names the
   invariant.
3. Treat D37–D46 in `test/devloop-run.test.sh` as the **frozen**
   prompt-align harness.

Use skill **`prompt-align`** against that test file. Do **not** run
`prompt-refine` or Hermes `promptloop` as DevLoop — different oracle.
Do **not** add SKILL.md greps for prose that already lives in a reference.
