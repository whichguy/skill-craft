---
name: test-harness
description: >-
  Run a repository's test suite and audit what the run did beyond its exit code: unintended writes to tracked files,
  leftover artifacts, live service calls, secret-shaped or traceback output. Optionally fix the product or the tests in
  a disposable worktree and rerun until clean, and always emit a machine-written report. Use when the user asks to run
  the test harness, audit test side effects, check harness hygiene, or gate a local change on suite plus
  unintended-write cleanliness for a repository or a package inside a monorepo.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  short-description: "Run harness, audit side effects, fix, rerun"
  skill_craft:
    kind: script-backed
---

# test-harness — run suite, audit side effects, fix, rerun

Green exit code is **necessary but not sufficient**. Run the suite, audit side
effects, optionally fix in a worktree, and **always** emit a machine report.

**Not** an improvement loop, a prompt or model evaluation harness, a test
generator, or an adjudicator of domain evals. **RESULT is suite hygiene only**
(suite exit + filesystem and control-channel side effects).

## Binding

`SKILL_ROOT` is the directory of this loaded `SKILL.md`, not the working directory, `PATH` or a guessed install path.
The scripts are bash and Python 3 standard library and make no network calls. Three surfaces stay separate:

| Surface | Meaning |
|---|---|
| `SKILL_ROOT` | the read-only package: this card, `scripts/`, `references/` |
| `--repo` (`WORK_ROOT`) | the repository or package under test; the suite runs with this as its cwd |
| `TEST_HARNESS_RUN_ROOT` | the write root for run records; default `${XDG_STATE_HOME:-$HOME/.local/state}/test-harness/runs` |

```sh
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
TH="$SKILL_ROOT/scripts/run-harness.sh"
```

Examples below spell `bash "$SKILL_ROOT/scripts/run-harness.sh"`; `"$TH"` is the same path.

## Package paths

```text
SKILL_ROOT/scripts/resolve-scope.py        # WORK_ROOT / GIT_ROOT / AUDIT_PREFIX (SSOT)
SKILL_ROOT/scripts/init-run.py
SKILL_ROOT/scripts/discover-test-cmd.sh    # config + Makefile / package / path tiers
SKILL_ROOT/scripts/run-suite.sh
SKILL_ROOT/scripts/worktree-fixloop.sh     # package-aware: suite_cwd under worktree
SKILL_ROOT/scripts/porcelain-delta.py
SKILL_ROOT/scripts/classify-side-effects.py
SKILL_ROOT/scripts/emit-report.py
SKILL_ROOT/scripts/run-harness.sh          # unified once | fix-loop mechanical driver
SKILL_ROOT/scripts/run-harness-hard-supervisor.py  # whole-lifecycle wall clock (the driver re-executes under it)
SKILL_ROOT/scripts/control_policy.py       # resolve/evaluate control channel policy + redaction
SKILL_ROOT/scripts/supervise.py            # reads suite output for unintended-consequence signals and the conclusion
SKILL_ROOT/scripts/test-harness-tests.sh
SKILL_ROOT/references/report-template.md
SKILL_ROOT/references/discovery-matrix.md
SKILL_ROOT/references/local-change-gate.md # normative local change gate (agent)
SKILL_ROOT/references/gate-snippet.md      # pasteable consumer gate block
SKILL_ROOT/references/self-test-matrix.md
SKILL_ROOT/references/operator-guide.md    # how to read a run
SKILL_ROOT/references/side-effect-taxonomy.md  # finding classes and restore rules
```

## Package scope (WORK_ROOT vs GIT_ROOT)

`--repo` may be a **package** path inside a monorepo (e.g. `packages/api`, or a
skill folder inside a larger repository), not only the git toplevel.

| Symbol | Meaning |
|---|---|
| `WORK_ROOT` | Path passed as `--repo` — suite cwd and suite identity |
| `GIT_ROOT` | `git rev-parse --show-toplevel` from `WORK_ROOT` (empty if not git) |
| `AUDIT_PREFIX` | Relpath `GIT_ROOT` → `WORK_ROOT` when nested; empty when equal |

- Suite always runs with cwd = **`WORK_ROOT`** (or worktree `suite_cwd` in fix-loop).
- Porcelain audits **`PORC_REPO`** (`GIT_ROOT` when present), filtered to **`AUDIT_PREFIX`** when nested.
- Neighbor monorepo dirt **outside** the package must not fail the package gate.
- Nested green suite + clean package audit → **`PASS_CLEAN_SCOPED`** (scoped FS audit;
  not “partial tests” — that is `suite_scope=subset`).
- Allowlist/policy: search `WORK_ROOT` first, then `GIT_ROOT`.

Normative agent gate text: **`references/local-change-gate.md`**.  
Consumer paste block: **`references/gate-snippet.md`**.

## Quick path (prefer the driver)

Agents **SHOULD prefer `run-harness.sh` for both modes** rather than hand-rolling phases:

```bash
# once / audit (default)
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$TARGET_REPO" [--cmd "…"] [--assume-fast]

# fix-loop (worktree + safe restore-on-fail rounds; product edits are agent-owned)
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$TARGET_REPO" --mode fix-loop [--max-rounds 5]
# or: --fix-loop
```

Package example (the suite runs in the package; the audit reads the repository's git state, limited to the package):

```bash
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$MONOREPO/packages/api"
```

## Invocation (agent)

The agent-level argument shape (`--commit` is agent-level; the driver takes the other flags, see rule 11):

```text
test-harness [repo] [--cmd …] [--full] [--once] [--mode once|fix-loop] [--max-rounds 5] [--timeout-secs N] [--commit] [--assume-fast]
```

| Default | Value |
|---|---|
| Profile | Prefer fast; generic test → unknown |
| Max rounds | 5 fix-loop / 1 once |
| Timeout | hard lifecycle ceiling: 3,600s; suite budget fast: 1,200s / full: 3,600s, minus a bounded finalization reserve |
| Launch checkout | audit-only always |
| Fix isolation | disposable worktree under `$RUN_DIR/worktree` |
| RUN_DIR | `<run root>/<slug>/<ts>-<rand>/`; run root = `$TEST_HARNESS_RUN_ROOT`, else `${XDG_STATE_HOME:-$HOME/.local/state}/test-harness/runs`; slug = the sanitized basename of `--repo` |

## Hard rules

1. Never edit the launch checkout in fix modes — only the worktree.
2. Never `git add -A`. No commit unless the operator passed `--commit` (an agent-level flag; the driver does not take it),
   and then only explicit paths.
3. Never weaken assertions to hide side effects.
4. **Reconcile according to workspace ownership.** In once mode, or whenever no
   disposable worktree was actually entered, the driver preserves every
   post-round change and stops for manual reconciliation: a long suite cannot
   distinguish its own writes from concurrent operator/agent WIP. Only a
   harness-owned disposable fix-loop worktree may restore clean-at-pre tracked
   bytes and delete absent-at-pre additions. Even there, dirty-at-pre changes
   are preserved and stop the loop. Reversion uses worktree-only `git restore`
   and never mutates the index.
5. Do not subtract FIX_PATHS from the **audit** delta.
6. **Phase 7 runs `emit-report.py` whenever the lifecycle remains responsive.**
   Classifier execution failure or
   missing/invalid classifier JSON records `round-N/classifier-failure.json` and
   emits `INCOMPLETE_RUN`. Paste **`chat-card.md` verbatim**. Do **not** freehand
   `results.md` or invent summary tables. The sole exception is the enclosing
   hard failsafe terminating a hung audit/report/teardown; exit 124 plus
   `hard-timeout.json` is then authoritative, and no card may be fabricated.
   Emergency evidence records only the worker executable basename and argument
   count; it never persists the raw command or its possibly secret arguments.
7. RESULT tokens are **observations** only (`PASS_CLEAN`, `FAIL_SUITE`, …). Mode limits go in next_steps (e.g. audit-only), never `BLOCKED_*` RESULT tokens.
8. No top-level `$RUN_DIR/side-effects.json` — per-round only; final findings live in `report.json`.
9. **Channel observation:** `run-suite.sh` always writes `stdout.log` + `stderr.log`. The complete run tree is private (`0700` directories, `0600` files). Raw logs, metadata, and emergency timeout evidence are created through retained exclusive no-follow descriptors; pre-existing or raced targets are rejected rather than followed, truncated, or overwritten. Control policy (`control_policy.py` → `control-policy.json`) forbids Traceback/secret-shaped control noise (fail disposition). Chat-card previews are **redact → cap → render**; raw logs stay on disk.
   `forbid_network: true` fails closed with `CONTROL_POLICY_ERROR`: captured-log inspection cannot prove packet isolation, so use an externally network-isolated habitat for that claim.
10. **Agent rule:** if RESULT ≠ `PASS_CLEAN` / `PASS_CLEAN_SCOPED`, **or** stderr has error-shaped lines, **open** `$RUN_DIR/round-N/stderr.log` (and `channels_excerpt.md` when present) before proposing a fix. Never invent PASS without the RESULT line + report path.
11. **Invocation:**  
    `bash "$SKILL_ROOT/scripts/run-harness.sh" --repo <path> [--mode once|fix-loop] [--cmd …] [--full] [--assume-fast] [--max-rounds N]`  
    Default mode is **once**. `--fix-loop` aliases `--mode fix-loop`.
12. **suite_scope:** `full` vs `subset` is labeled on the manifest/chat-card. Subset is **not** a full release gate. Do **not** misuse `PASS_CLEAN_SCOPED` for partial suites (that token means limited **FS audit** scope only).
13. **habitat:** prefer **host** runs so porcelain + TMPDIR audit match the suite. Container/`docker exec` smokes are product checks; do not claim audited FS hygiene unless habitat=host.
14. **Package path:** skill/package subdirs are first-class `--repo` values. See package-scope table and `references/local-change-gate.md`.
15. **No hand-rolled fix-loop plumbing.** Call `run-harness --mode fix-loop`; after a fail, edit product/tests under the worktree `suite_cwd` and re-invoke. Never open-code porcelain restore / multi-round delta.
16. **Timeout ownership:** a monotonic process-group supervisor starts before
    resolve/discovery and encloses init, every suite round, audit/classification,
    reconciliation, reporting, worktree teardown, descendant cleanup, and its
    own exit. It escalates TERM to KILL and can never exceed 3,600s.
    The worker accepts supervision only after consuming a supervisor-owned
    inherited pipe capability; ambient PID/deadline variables cannot bypass it.
    `--timeout-secs N` selects an exact lower hard envelope; `--full` defaults to
    a 3,600s envelope (the suite budget is 3,600s when the profile resolves to
    `full`, which an explicit `--cmd` with `--full` also does, else 1,200s). An undiscovered/default-fast run starts beneath the global
    one-hour failsafe and then applies a 1,200s suite budget. Five percent of the selected
    budget, bounded to 1–60s, is reserved for finalization. Fix-loop rounds share
    one real deadline, so later rounds receive only remaining time. Environment
    overrides above 3,600s fail before any workspace operation. Inner
    watchdogs of the suite itself cannot extend the outer one-hour limit. External
    INT, TERM, and HUP signals are forwarded once at every owned supervisor
    boundary, with cooperative grace before TERM→KILL escalation, so cancelling
    a nested suite reaps its participating descendants. A process that
    deliberately starts an unmanaged session and does not forward signals is
    outside portable POSIX process-group ownership and must provide its own
    explicit cleanup contract.

---

## Phase checklist

### 0 — Resolve

**Prefer the driver** for once and fix-loop:

```bash
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$WORK_ROOT" [--mode once|fix-loop] [--cmd "…"]
```

Manual steps only when debugging:

1. Resolve `TARGET_REPO` / `WORK_ROOT` (skill **package path is first-class**). Sticky CWD there.
2. Resolve scope via SSOT (do **not** hand-roll relpath):

   ```bash
   python3 "$SKILL_ROOT/scripts/resolve-scope.py" --repo "$WORK_ROOT"
   # → work_root, git_root, audit_prefix, porc_repo, suite_rel, slug
   # run-harness / worktree-fixloop also write $RUN_DIR/scope.json
   ```

3. Discover cmd: agent tiers 0–1 (`--cmd`, docs); script **config (1.5)** + tiers 2–5:

   ```bash
   bash "$SKILL_ROOT/scripts/discover-test-cmd.sh" --repo "$WORK_ROOT" [--full]
   ```

4. Profile unknown without `--assume-fast` → **once/audit-only** (driver demotes fix-loop).
5. Create `RUN_DIR`, then **init-run** (required) — driver does this.
6. **Fix-loop:** driver enters worktree via `worktree-fixloop.sh` with **`--repo "$WORK_ROOT"`**;
   suite runs at `suite_cwd`. Porcelain uses `porc_repo` + `--path-prefix "$AUDIT_PREFIX"`.
7. **Once:** suite at `WORK_ROOT`; no worktree.
8. Optional policy and allowlist: `.test-harness.yml`, `test/harness-allowlist.yml` or `.test-harness.json` (searched in WORK_ROOT, then GIT_ROOT).
   Discovery tier 1.5 reads only `$WORK_ROOT/.test-harness.yml` or `.json`, and only a non-empty `cmd` there
   (`source=config`).

### 1–7 — driven by run-harness

| Phase | once | fix-loop |
|---|---|---|
| Baseline / run / audit / classify | 1 round | up to `max-rounds` |
| On pass | emit-report → exit 0 | emit-report → worktree exit → exit 0 |
| On fail | preserve all post state, require manual reconciliation, emit FAIL_* | in a disposable worktree only, restore clean-at-pre suite dirt; dirty-at-pre changes are preserved and stop the loop; otherwise continue within budget |
| Product fix | n/a (audit-only) | **agent** edits worktree then **re-invokes** driver |

Manual porcelain / run-suite / classify / emit only for plumbing debug — see each script's `--help`.

### Fix-loop agent pattern

```bash
# 1) mechanical attempt
bash "$SKILL_ROOT/scripts/run-harness.sh" --repo "$WORK_ROOT" --mode fix-loop
# 2) if FAIL_*: open round logs; edit product/tests under $RUN_DIR/worktree (or suite_cwd)
# 3) re-invoke (driver reuses or re-enters worktree); never hand-roll restore
```

Worktree exit if used outside the driver:

```bash
bash "$SKILL_ROOT/scripts/worktree-fixloop.sh" exit --repo "$WORK_ROOT" --run-dir "$RUN_DIR"
```

---

## Disposition quick map

| Class | Default |
|---|---|
| BASELINE | ok (baseline context only — not chat notes) |
| EXPECTED_ARTIFACT | note |
| UNINTENDED_WRITE | **fail** |
| TMPDIR_LEAK | note — run-relative path; **not repo dirt** |
| LIVE_CALL_SUSPECT | note |
| LIVE_GATE_ON_FAST | fail (confirmed fast only) |
| UNKNOWN | **fail** |

## Fix policy

| Finding | Prefer |
|---|---|
| Logic bug | product |
| Bad expectation / missing cleanup | tests |
| Suite writes product files | TMPDIR + cleanup |
| Unignored litter | gitignore / teardown |
| Live call in unit test | injectable seam |

## Example chat-card (emitted — do not hand-author)

See latest run’s `chat-card.md`. Shape:

```markdown
### 🧪 Test harness · <slug>
## Final result
| Result | PASS_CLEAN_SCOPED | …
## What ran & was verified
| Real cases | 39 PASS · 0 FAIL · 0 SKIP |
### Groups — what was verified
| File / module suite | 39 PASS | per-file or per-module assertions from the runner |
### Case inventory (executed)
- `PASS` `test/api/users.test.js` — users …
## Worked well (hygiene)
## Struggles …
**Next:** done — suite green, checkout clean.
```

Groups come only from the shape of a case name: path-like names form the file or
module group, everything else the other group. The report never invents a claim
about what a test verifies beyond its own name.

## Honest limits

- The self-test (`scripts/test-harness-tests.sh`) passes on macOS (arm64; bash 3.2,
  Python 3.15, git 2.54) and in one Linux container (Debian 13, aarch64; bash 5.2,
  Python 3.13, git 2.47, no network). Other distributions, x86_64 and Python 3.9 to
  3.12 were not run; Python 3.9 grammar was checked by parsing the scripts only.
  `references/self-test-matrix.md` lists what the self-test pins.
- Case and group recognition is line-shape based: `PASS`/`FAIL`/`SKIP` lines, TAP,
  mocha-style failures, suite rollup lines, an optional `RESULT_JSON {…}` summary
  line. A runner that prints none of them is judged by exit code, raw logs and the
  filesystem audit only.
- Fix-loop mode adds a branch (`test-harness/<repository folder name reduced to letters, digits, "_" and "-">-<rand>`) and a
  worktree registration to the repository under test. A clean exit removes both; otherwise they are kept and `fixes.patch` is
  written under the run directory.
- The suite command runs under `bash -lc`, so the caller's login profile is sourced; whatever it prints or exports reaches the
  audited channels. Run records are private (`0700`/`0600`) but the raw logs in them are not redacted: they hold whatever the
  suite printed.
- `forbid_network` cannot be enforced from captured logs; it fails closed.
- Timeouts are wall-clock supervision, not a security sandbox: a process that
  starts an unmanaged session and ignores signals needs its own cleanup contract.

Agents paste this card **verbatim** — do not replace the inventory with a freehand pass/fail summary.
