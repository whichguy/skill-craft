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
| **Before** | **preflight**, then **approach**, **survey**, **research**, and a checkable **spec**; then native bounded **sequence** planning and only lifecycle-selected preparation | The Markdown run records the source of truth. Sequence planning uses a short forward draft plus backwards prerequisite audit, then a validated compatible DAG import; no external planner is required. Survey retains destination writer, reserved/product layout, routing, lint/live-identity oracle, references, and UI constraints. The lifecycle explicitly places preparation, quality, and publication as none, DAG, or outer work. |
| **During** | `/shiploop next` reprints one action; `/shiploop complete --action ID --result FILE` advances only that durable action | One ready worktree step at a time. Implement and every Improve iteration run concrete lint and required tests through a manifest. Improve reads Git history, reviews, plans/applies fixes, verifies, and makes a verbose learning-oriented primary commit. Two trivial-only iterations still require final verify and broader-plan review. |
| **After** | `coverage → quality → publish? → handoff`; action-bound `replan` may add a corrective pending step | Review Coverage must be bound/tracked/clean; quality always runs fresh acceptance/integration evidence, and `quality: true` adds focused quality review. Publication remains authorized, host-reported evidence. Handoff records limitations and generic ShipLoop proposals; it does not prove semantic or remote success. |

ShipLoop owns per-step git worktree/branch isolation (checkout disposable;
branch kept on a merge complete; harness `merge --no-ff --no-edit` only after
fresh final evidence and session-baseline checks). It does **not** inherit
DevLoop’s frozen-oracle or COMPLETE guarantees, and must not import
`worktree.py`, auto-resolve merge conflicts, or claim engine `COMPLETE`.

## Practices

| Practice | Lives in | Must not move to |
|----------|----------|------------------|
| One controller (DevLoop session) | `/devloop` Forbidden + Grok alias | Nested `/goal` / `/loop` / host BUILD |
| Fail-closed (no invented oracle / cwd / `--repo`) | Card interpolate + engine admission | `/goal` “best effort” complete |
| COMPLETE = `AFTER exec exit=0` only | Card + `test/devloop-run.test.sh` D37 | Second host gate (silent push, `/goal` verify, evidence-gates receipt) |
| Isolated worktree every run | Shim + engine | Review-converge sticky target, cwd reuse |
| Per-step worktree (ShipLoop) | ShipLoop action receipt / local merge gate | DevLoop `worktree.py` import, auto-merge, second COMPLETE |
| Frozen oracle | Engine PROVE/BUILD | Host rewrite of tests |
| Consumer-channel + `require_*` family | Engine `admission_gates.py` | Host skill / destination-contract nouns |
| Checkable done sentence | `/devloop <goal>` text | Host DEFINE/PROVE/BUILD complete-when table |
| residual×2 | `review-coverage` after DevLoop `COMPLETE` | Engine (≤3 attempt retry is a different grain) |
| Learning after outcome | Engine DELIVER+LEARN | Host commit to “finish” delivery |
| MCP observe-not-act | Card (`references/mcp-consider.md`) | Engine (does not speak MCP) |

`evidence-gates` is offline freeze / prove / build-on-host / stop — **not**
DevLoop. Never fall back to it when the user asked for DevLoop.

`shiploop` is a **session harness**, not a second DevLoop. It reads durable
Markdown artifacts and prints the next action. It must not invoke `/devloop`,
capture `devloop-run`, auto-resolve merge conflicts, or claim COMPLETE. A
small-context host obtains bounded state with `shiploop context`, not a full
packet echo. The canonical sequence is `.shiploop/backchain/plan.md`, and
the only revision paths are post-inner or outer `replan` with a validated
pending-only DAG.

## Prompt-driven, script-enforced (three grains)

Layer 2: scripts do not re-author planning policy. The next card edit
must not grow another bash phrase-matcher.

| Grain | Prompt decides | Script only |
|-------|----------------|-------------|
| **Requirements** | Checkable done, dest contract, interpolate `--repo` / `--lang` / `verify_cmd` from the card table (empty done → stop and ask) | Pin sha256, safe extract, host-local resolve, refuse empty/invalid resolve or transport; `STATE target=` from the `--repo` flag only (`explicit` vs `default`). Do not parse the done sentence in bash. |
| **Inner loop** | Charter / implement / review text. Host inner loops (ShipLoop Implement/Improve, residual Improve B) mandate lint-after-write after code is written: run every available linter (writer, repo-configured, generic syntax already present — do not install); dest-writer lint/validate is dest-syntax SoT; live dest is identity oracle; dest-mandated syntax wins over generic. Frozen reprints the lint oracle even when Exclusive is `(none)` | Engine sequencer, frozen oracle, worktree, COMPLETE = `AFTER exec exit=0`. Do not import dest MCP lint into the DevLoop engine |
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
