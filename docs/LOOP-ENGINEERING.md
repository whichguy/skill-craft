# Loop engineering (host practices)

Portable practices for fail-closed loops. This is **documentation**, not a
runtime and not a slash skill. The DevLoop **engine** still owns
DEFINE → PROVE → BUILD → DELIVER+LEARN. Host overlays compose **around**
that loop; they must not become a second controller.

Identical copies (keep in sync):

- `docs/LOOP-ENGINEERING.md`
- `skills/devloop/references/loop-engineering.md`

## Compose graph

Two **scoped tracks**. Do not mix them.

### DevLoop session

User invoked `/devloop` / skill `devloop`.

| When | Overlay | Role |
|------|---------|------|
| **Before** | Validate the spec (`validate-spec.md`; `define-done` / `backchain` if needed) | Prove the done sentence is machine-checkable. Do not require this on every `/devloop`. |
| **During** | `/devloop` only | One build controller. Engine owns the phases. |
| **After** | `/review-coverage` under host `/goal` | residual×2 after engine `COMPLETE`. Not `/devloop` again, not `/loop`. |

Do **not** nest Grok `/goal` or `/loop` inside `/devloop`. `/goal` owns
adversarial completion; DevLoop already owns `COMPLETE`. Nesting them
creates a second COMPLETE gate (false COMPLETE, silent push).

One controller = `/devloop`. Do not grow a host BUILD path on this track.
Frozen oracle, isolated worktree, and `COMPLETE` = `AFTER exec exit=0` apply
**here only**.

### ShipLoop session

User invoked `/shiploop` / skill `shiploop`.

| When | Overlay | Role |
|------|---------|------|
| **Before** | **survey once** (session kind/handles/MCP/initiation/UI → `environment.md`), then **spec once**, then **sequence plan once** (backchain) | Survey is a required prefix inside `validate-spec`, not a new phase. Frozen `done_sentence`. Prep / intermediate deploy / cleanup / a README create-or-revise are DAG steps when implied — brownfield augments an existing tree (`augment: true`) rather than replacing it. |
| **During** | `/shiploop next` emits a `/goal` per running step (cwd is that step's worktree). `/shiploop complete` closes the increment (commit + host merge + next packet). | Host DAG walk. **Not** `/devloop`. **Not** a spec rewrite. |
| **After** | session residual under `/goal` once `steps_drained` | No engine `COMPLETE`. |

ShipLoop owns per-step git worktree/branch isolation (checkout disposable;
branch kept on complete; host merges before `/shiploop complete`). It does **not** inherit
DevLoop’s frozen-oracle or COMPLETE guarantees, and must not import
`worktree.py`, auto-merge, or claim engine `COMPLETE`.

## Practices

| Practice | Lives in | Must not move to |
|----------|----------|------------------|
| One controller (DevLoop session) | `/devloop` Forbidden + Grok alias | Nested `/goal` / `/loop` / host BUILD |
| Fail-closed (no invented oracle / cwd / `--repo`) | Card interpolate + engine admission | `/goal` “best effort” complete |
| COMPLETE = `AFTER exec exit=0` only | Card + `test/devloop-run.test.sh` D37 | Second host gate (silent push, `/goal` verify, evidence-gates receipt) |
| Isolated worktree every run | Shim + engine | Review-converge sticky target, cwd reuse |
| Per-step worktree (ShipLoop) | shiploop claim / complete-step / clear-step | DevLoop `worktree.py` import, auto-merge, second COMPLETE |
| Frozen oracle | Engine PROVE/BUILD | Host rewrite of tests |
| Consumer-channel + `require_*` family | Engine `admission_gates.py` | Host skill / destination-contract nouns |
| Checkable done sentence | `/devloop <goal>` text | Host DEFINE/PROVE/BUILD complete-when table |
| residual×2 | `review-coverage` after DevLoop `COMPLETE`, or after ShipLoop `steps_drained` | Engine (≤3 attempt retry is a different grain) |
| Learning after outcome | Engine DELIVER+LEARN | Host commit to “finish” delivery |
| MCP observe-not-act | Card (`references/mcp-consider.md`) | Engine (does not speak MCP) |

`evidence-gates` is offline freeze / prove / build-on-host / stop — **not**
DevLoop. Never fall back to it when the user asked for DevLoop.

`shiploop` is a **session harness**, not a second DevLoop. It reads artifacts and
prints the next packet. During a ShipLoop session, `/shiploop next` emits a `/goal`
for ready steps (cwd on that step's worktree) and does not rewrite the spec.
The host closer is `/shiploop complete` (procedure on the shiploop card;
the harness script infers the unique running id or happy-path `--to`).
It must not invoke `/devloop`, must not
capture `devloop-run`, must not auto-merge, and must not claim COMPLETE. Bare
“devloop” still routes to skill `devloop`. `.shiploop/plan.md` is a pointer; the
sequence plan is `.shiploop/backchain/plan.json`.

## Prompt-driven, script-enforced (three grains)

Layer 2: scripts do not re-author planning policy. The next card edit
must not grow another bash phrase-matcher.

| Grain | Prompt decides | Script only |
|-------|----------------|-------------|
| **Requirements** | Checkable done, dest contract, interpolate `--repo` / `--lang` / `verify_cmd` from the card table (empty done → stop and ask) | Pin sha256, safe extract, host-local resolve, refuse empty/invalid resolve or transport; `STATE target=` from the `--repo` flag only (`explicit` vs `default`). Do not parse the done sentence in bash. |
| **Inner loop** | Charter / implement / review text | Engine sequencer, frozen oracle, worktree, COMPLETE = `AFTER exec exit=0` |
| **Outer residual** | `/goal` sentence, residual×2, halt rules | Validate H2 fields; print the reference-owned trailer |

Do **not** put DEFINE → PROVE → BUILD in `SKILL.md` or `/goal`.
Do **not** scrape goal prose in `devloop-run`.
Do **not** author STATIC/halt sentences in `scripts/review-coverage`.

## Card maintenance (prompt-align, not more greps)

Future `/devloop` card edits:

1. Put new policy in a **reference** (`mcp-consider.md`,
   `destination-contract.md`, `validate-spec.md`, this file), not another
   paragraph in `SKILL.md`.
2. Add **one** hermetic assertion that the reference exists and names the
   invariant.
3. Treat D37–D46 in `test/devloop-run.test.sh` as the **frozen**
   prompt-align harness.

Use skill **`prompt-align`** against that test file. Do **not** run
`prompt-refine` or Hermes `promptloop` as DevLoop — different oracle.
Do **not** add SKILL.md greps for prose that already lives in a reference.
Do **not** add bash or Python that retells interpolate phrases or `/goal` prose.
