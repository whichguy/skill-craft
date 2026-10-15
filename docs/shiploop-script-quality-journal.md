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

## Improve-loop campaign, 2026-10-11 to 2026-10-15 (commits `3c1a7bd4`, `5ebf3851`, `02330e13`, `37a5d59f`)

Target: the same scripts, defect seed, autonomous, 4-cycle cap, quick tier as the test command. Status at exit:
`stopped (max-cycles)` with one open P1 (status: firm).

| Cycle | Item | Outcome | Evidence |
|---|---|---|---|
| 1 | `shiploop_quality.__all__` and docstring named seven objects the module no longer defines, so `import *` raised `AttributeError` | confirmed | quick tier exit 0 (19 suites) |
| 2 | six error messages named no file, limit or type | confirmed | quick tier exit 0 (27 suites) |
| 3 | document 45 private functions of 25+ lines | partial: 19 landed | quick tier PASS (42 suites) |
| 4 | the 26 rejected in cycle 3 | partial: 24 landed, 2 remain | quick tier exit 0 (45 suites) |

### Findings and learnings

1. **Pipeline for docstrings (firm).** Draft, two skeptics with different lenses, revise once, recheck. Agents write each
   draft straight to a JSON file so no text is retyped. Docstring-only proof: the syntax tree with docstrings stripped is
   identical to the previous commit in every changed file.
2. **A completeness lens that asks for exhaustiveness rejects nearly everything (firm).** Cycle 3 rejected 26 of 45; about
   5 objections each, almost all "does not say X", only a handful factual. Cycle 4 kept the accuracy lens strict and
   narrowed completeness to omissions that mislead a caller: 24 of 26 passed. The 2 that still failed were rejected for
   real precision errors the skeptic showed by running code (`_parent_fd` validates nothing, so "stays beneath base
   without following symlinks" holds only for pre-validated components; `_expected_dirty_source` writes temporary
   index files only for a non-empty patch or any extras). Both remain undocumented and are the open P1.
3. **`worktree-enter.js` moves the primary checkout's uncommitted work (firm).** It resolved the launch repo to the primary
   checkout of the shared git directory, carried 77 uncommitted paths into the campaign worktree and cleaned them
   from the primary. Restored from a tar backup of the carried paths and hash-verified (77 files, 0 mismatches) before
   deleting the worktree. Campaigns now run from an independent clone. Recorded in memory.
4. **External limits (exploratory).** Two workflow attempts hit the account's monthly spend limit (89 then 43 agents
   errored); resuming after the weekly reset replayed completed agents from cache. A background shell wrapper was killed
   (exit 144) while its test runner kept going; the verdict is the runner's own `run-all.sh: PASS` line, not the wrapper's exit code.
5. **Shell traps (firm).** Under zsh an unquoted newline-separated list is one argument; macOS bash 3.2 has no `mapfile`.
   An empty path list let `git add --` succeed and produced a commit with only the ledger deletion. Caught before any
   push by listing the commit's files; amended. Always check a commit's file list, and make an empty list fatal.

Open: 2 private functions to document (above); cyclomatic complexity of 85 functions (deferred, behaviour-risky);
unused parameters on test-pinned APIs (deferred, tests call them with the extra arguments).
