# ShipLoop script quality journal

Living record of the 2026-10-11 review of `skills/shiploop/scripts` (code quality: portability, argument
checks, error context, comments, naming). Commit `9a3c2a5b` landed the fixes.

## Question and method

Do the 41 ShipLoop scripts (about 32,000 lines) meet a high bar for portability, argument validation,
error context, comments and naming? Method: ruff (`F,B,S,BLE,TRY,ARG,ANN,PL,SIM`), an AST pass for docstring
coverage, swallowed handlers and terse raises, and a read of every flagged site. Tests: all 60
`test/shiploop-*.test.py` suites before and after (baseline, then the rebased tree).

## Findings (status: firm unless noted)

| Finding | Action | Evidence |
|---|---|---|
| Dead variables, `assert` as control flow, unused import, closure over loop variables, missing `check=` | Fixed | ruff `F,B,S101,PLW1510` clean at `--target-version py39` |
| 8 re-raises dropped their cause; 13 raises carried no value or position | `from exc`; context added | commit `9a3c2a5b` |
| Transition hooks caught `BaseException` and discarded it | `Exception` plus a stderr note for unexpected types; `SHIPLOOP_DEBUG` for the status hook | `_hook_failed` in `shiploop_navigator.py` |
| `--max-sessions`, `--session-timeout`, `--part`, `--rerun`, `--gate` accepted out-of-range values | argparse range types | `_positive_int`, `_natural_number` |
| About half the definitions had no docstring | All public definitions and the largest private ones documented | nodoc scan: 0 public gaps |
| Locking is POSIX-only (`fcntl.flock`, `O_NOFOLLOW`, `os.killpg`, `/bin/sh`) | Left as is by owner decision (lock-free redesign out of scope); already documented in `references/host-matrix.md` | owner message 2026-10-11 |
| Four modules of 2,600 to 4,500 lines | Not split (behaviour-risky refactor) | deferred |

## Regressions I introduced, caught by the test suites (learnings)

1. A half-finished variable rename (`quote` to `reads_quote`, 3 of 5 uses) crashed packet rendering and
   failed 32 suites. ruff could not see it because `quote` is also an imported name. Check: an
   undefined-name scan plus the suites.
2. `zip(..., strict=...)` (added to satisfy B905) fails on the macOS system Python 3.9.6 that the CLI shebang
   resolves to (`TypeError: zip() takes no keyword arguments`). ShipLoop scripts must stay Python 3.9
   compatible: lint with `--target-version py39` (B905 is then not raised) and smoke-import every module with
   `/usr/bin/python3`.

## Test-suite timing (exploratory)

Under load average 14 to 27 (other sessions), `shiploop-chain` took 544 s (recorded CI baseline 191 s) and
`shiploop-chain-lifecycle` 1692 s (baseline 803 s). Per-process cost was about 0.13 s unloaded and 1.7 s loaded.
Two chain tests make 68 and 80 CLI launches each; eight lifecycle scenarios take 80 to 122 s each. CLI start-up
is 0.17 s, of which 0.117 s is imports; the navigator pulls in lint (28 ms) and about 20 modules. Lazy imports
would save roughly 15 percent per launch for 63 call sites of change, so were not done. Option left open:
shard `shiploop-chain-lifecycle` (single class, 52 tests) in `test/suite_catalog.py`.

## Baseline failures before this work

`shiploop-cross-run` and `shiploop-status-display` failed at `HEAD` before any edit (progress-file side
effects); `shiploop-chain-lifecycle` timed out at 1200 s under load and passed alone. Upstream moved 26
commits during the work (ShipLoop 1.3.0); the rebased tree passed the quick tier (53 suites, exit 0).
