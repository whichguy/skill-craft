# Discovery matrix

How the harness finds the suite command and profile.

## Ownership split

| Tier | Owner | Sources | Profile |
|---|---|---|---|
| 0 | **Agent** | Explicit `--cmd` / user text | As stated, else `unknown` |
| 1 | **Agent** | `AGENTS.md` / `CLAUDE.md` / README “Run tests with…” | As docs declare, else `unknown` |
| **1.5** | `discover-test-cmd.sh` | **Config:** `$REPO/.test-harness.yml` or `.test-harness.json` with non-empty `cmd` | from file, else `fast`; `suite_scope`/`habitat` default `full`/`host`; `source=config` |
| 2 | script | Makefile: `test-fast` > `test` > `check` > `test-ci`. With `--full` the first existing of `test-all`, `test-ci`, `test`, `check` wins instead | `test-fast` → `fast`; `test-all` / `test-ci` under `--full` → `full`; `test`, `check` and `test-ci` otherwise → `unknown` |
| 3 | script | `package.json` scripts: `test:fast` / `test:unit` / `test` / `check` | fast-named → `fast`; generic → `unknown` |
| 3b | script | **Hermetic suites** (before generic tier 4): `tests/run_*.test.sh` (first in name order) > `tests/run.py` > `tests/run.sh` | all → **`fast`**, `habitat=host`, `suite_scope=full` (wrappers preferred over bare `run.sh`) |
| 4 | script | `test/run-all.sh`, `harness/*.sh` | `unknown` |
| 5 | script | Package-local `tests/scripts.test.sh`, `scripts/test-harness-tests.sh` | `fast` |
| 6 | Agent | Ask once; headless → stop `no test command` | — |

**Config before Makefile.** A package that needs a pinned suite (or profile) should put:

```yaml
cmd: python3 tests/run.py
profile: fast
suite_scope: full
habitat: host
```

in `.test-harness.yml` at `WORK_ROOT`. Discover keys are allowed in the same file as
control-policy keys (`control_policy.py` KNOWN_KEYS); they do not alter policy merge.

Makefile / package.json at **package** `WORK_ROOT` still win when **no** config `cmd` is set.
`tests/run.sh` as fast documents residual live risk if the script dials network —
prefer `run_*.test.sh` offline wrappers when both exist.

### Discover output

A project whose layout none of the tiers recognise pins its suite with a `.test-harness.yml`
(tier 1.5) rather than waiting for a new built-in tier. Discover returns JSON fields:

```json
{"cmd":"…","profile":"fast|full|unknown","suite_scope":"full|subset","habitat":"host","source":"path|config|…"}
```

Subset is **not** a full release gate. `PASS_CLEAN_SCOPED` means limited **filesystem** audit,  
never “we only ran half the tests.”

The script **never** parses prose docs. On no candidate it exits **2** with
`{"error":"no_deterministic_candidate"}`.

## Profile gate

- `fast` only when: repo docs declare hermetic/fast, user passes `--assume-fast` /
  states hermetic, the target is fast-named (`test-fast`, `test:fast`, `test:unit`),
  config pins `profile: fast`, or a built-in path guess matched (tiers 3b and 5: the
  hermetic-suite paths, `tests/scripts.test.sh`, the harness's own self-test).
  `fast` is what lets `--mode fix-loop` run without `--assume-fast` and what makes a
  live-gate environment variable a hard fail.
- Generic `make test` / `npm test` / `make check` → **`unknown`**.
- `unknown` without confirmation → audit-only; no automatic fix loop
  (`run-harness` demotes `--mode fix-loop` → once unless `--assume-fast`).
- `LIVE_GATE_ON_FAST` hard-FAIL applies only under confirmed `fast`.

## Prefer hermetic

Default to the fastest hermetic path. Use `--full` only when the claim under test
requires live/smoke proof.

## Driver scope (`run-harness.sh`)

The shell driver uses **tier 0 (`--cmd`), tier 1.5 (config), and tiers 2–5**. It does **not**
parse AGENTS.md/README (tier 1). Modes: `--mode once` (default) or `--mode fix-loop`
(alias `--fix-loop`). Fix-loop is mechanical (worktree + restore-on-fail rounds);
product code fixes remain agent-owned (edit worktree, re-invoke).
