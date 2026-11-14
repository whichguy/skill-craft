# Local change gate — normative agent contract

Use this after any code-touching change when the operator (or skill) expects a
**local change gate**: run the package suite, audit side effects, and treat the
RESULT line as the observation of record.

This is **not** an improvement loop, a prompt or model evaluation harness, a test
generator, or an adjudicator of domain evals. RESULT is **suite hygiene only**.

Pasteable consumer wording: **`gate-snippet.md`**.

## Package scope (WORK_ROOT vs GIT_ROOT)

| Symbol | Meaning |
|---|---|
| `WORK_ROOT` | Path the operator passed as `--repo` (suite cwd). Skill subdirs are first-class. |
| `GIT_ROOT` | `git rev-parse --show-toplevel` from `WORK_ROOT` (empty if not a git work tree). |
| `AUDIT_PREFIX` | Relative path from `GIT_ROOT` → `WORK_ROOT` when nested; empty when equal. |

Rules:

1. **Suite cwd is always `WORK_ROOT`** (or worktree `suite_cwd` in fix-loop). Never collapse a
   skill package path to the monorepo toplevel just because git lives higher up.
2. **FS audit uses `GIT_ROOT` + `AUDIT_PREFIX`.** Porcelain paths are git-root-relative;
   joins are `Path(GIT_ROOT) / path`. When nested, only dirt under `AUDIT_PREFIX` is
   audited. Neighbor monorepo dirt must not fail a package gate.
3. **RESULT tokens:**
   - `PASS_CLEAN` — suite green, side effects clean, **full** FS audit (`WORK_ROOT == GIT_ROOT`, no cap).
   - `PASS_CLEAN_SCOPED` — suite green, side effects clean under a **scoped** FS audit
     (`fs_scope` in `package` / `git-visible-only` / `no-git`, or non-empty `audit_prefix`).
   - `PASS_CLEAN_SCOPED` is **not** “we only ran half the tests.” That is `suite_scope=subset`.
4. Allowlist / control policy: search **`WORK_ROOT` first**, then `GIT_ROOT`.

## Normative gate (agent)

After product or test edits in a package:

```bash
# SKILL_ROOT = the directory of the loaded test-harness SKILL.md (see SKILL.md "Binding"); never a guessed install path
# WORK_ROOT  = this package or repo root (portable — not a hard-coded machine path)
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$WORK_ROOT" [--cmd "…"] [--assume-fast]
# expect: test-harness RESULT=PASS_CLEAN or PASS_CLEAN_SCOPED
```

**Once (default):** single round, no worktree.

**Fix-loop:** prefer the driver over hand-rolling phases:

```bash
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$WORK_ROOT" --mode fix-loop [--max-rounds 5]
# mechanical: worktree enter → rounds (pre/suite/post/classify; safe restore on fail) → emit → exit
# dirty-at-pre changed/deleted paths are preserved and stop for manual reconciliation
# product fixes: edit under worktree suite_cwd, re-invoke — do not open-code porcelain
```

Resolve scope (do not hand-roll):

```bash
python3 "$SKILL_ROOT/scripts/resolve-scope.py" --repo "$WORK_ROOT"
# writes also to $RUN_DIR/scope.json when using run-harness / worktree-fixloop
```

Portable WORK_ROOT examples:

| Consumer | WORK_ROOT |
|---|---|
| Whole repository | `$(git rev-parse --show-toplevel)` from any path in the clone |
| Package in a monorepo | `$(git rev-parse --show-toplevel)/packages/<name>` (audit limited to that prefix) |
| Skill or plugin folder inside a larger repository | the folder that holds its `tests/` or `scripts/` suite |

Hard rules:

1. **Green suite exit is necessary but not sufficient.** Side-effect fail findings
   (unintended writes, control forbids, live gates on fast) block the gate.
2. **Never weaken assertions** to hide side effects or monorepo neighbor dirt.
3. **Do not claim PASS** without the greppable `test-harness RESULT=…` line and run dir.
4. If RESULT ≠ `PASS_CLEAN` / `PASS_CLEAN_SCOPED`, open `$RUN_DIR/round-N/stderr.log`
   (and `channels_excerpt.md` when present) before proposing a fix.
5. Package runs: prefer `--repo` = skill/package directory. Nested monorepo dirt
   outside `AUDIT_PREFIX` is out of scope for that run.
6. Paste `chat-card.md` verbatim; optional ≤4-sentence gloss. Point operators at
   `$RUN_DIR/report.html` (open it in a browser).
7. **Prefer `run-harness` for both modes** rather than hand-rolling Phase 0–7.
   Fix-loop plumbing (worktree, restore, multi-round porcelain) must never be open-coded.
8. **Never auto-restore a changed/deleted path that was dirty at round pre.**
   Preserve the exact post state, inspect `round-N/restore.json`, and reconcile
   manually before another round.

## Discovery (hermetic suites)

At package `WORK_ROOT`, order is: `--cmd` → **`.test-harness.yml`/`json` `cmd`** → Makefile →
package.json → hermetic path wrappers. When no Makefile / package.json / config wins:

| Path | cmd | profile | notes |
|---|---|---|---|
| `tests/run_*.test.sh` | `bash tests/run_….test.sh` | **fast** | preferred offline wrappers (first in name order) |
| `tests/run.py` | `python3 tests/run.py` | **fast** | `suite_scope=full` |
| `tests/run.sh` | `bash tests/run.sh` | **fast** | residual live risk if script dials network — prefer wrappers |

See `discovery-matrix.md` for full tier order.

## Self-test matrix

| Case | Expect |
|---|---|
| Root clean suite | `PASS_CLEAN` |
| Nested package + root dirt, package clean | `PASS_CLEAN_SCOPED` |
| Nested package suite writes product file | `FAIL_SIDE_EFFECTS` |

See also `self-test-matrix.md`. Pinned in `scripts/test-harness-tests.sh`.

## Phase 0 — resolve (package path first-class)

Agents **SHOULD prefer** `run-harness.sh` for both once and fix-loop rather than hand-rolling:

```bash
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$WORK_ROOT" [--mode once|fix-loop]
```

Manual phases only when debugging plumbing:

1. Resolve `TARGET_REPO` / `WORK_ROOT` (skill subdir OK). Sticky CWD there.
2. Compute scope via `resolve-scope.py` (do **not** hand-roll relpath).
3. Discover cmd at `WORK_ROOT` (agent tiers 0–1; script config + tiers 2–5).
4. `init-run` with `repo=work_root`, plus `work_root` / `git_root` / `audit_prefix` fields.
5. Baseline / post porcelain with `--repo "$PORC_REPO"` and `--path-prefix` when nested.
6. Run suite with `--repo "$SUITE_CWD"` (`WORK_ROOT` or worktree suite_cwd).

## Related

- Paste block: `gate-snippet.md`
- Skill entry: `../SKILL.md`
- Discovery tiers: `discovery-matrix.md`
- Self-test pins: `self-test-matrix.md`
- Side-effect classes: `side-effect-taxonomy.md`
- Operator reading: `operator-guide.md`
