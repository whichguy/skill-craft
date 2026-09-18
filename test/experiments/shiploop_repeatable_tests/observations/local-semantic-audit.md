# Bounded semantic audit

Scope: read-only inspection of the three supplied trial fixtures (excluding
GUIDANCE, observer records, and requests). All executions and mutations were
performed only against sibling disposable copies in this audit directory.

## Trial 01 — price-format

- **Oracles and coverage: verified.** `SPEC.md:3-6` is implemented with literal
  arithmetic, invalid-input, exact-string, precision, and recovery assertions in
  `test_pricing.py:24-122`; no oracle calls production to derive an expected
  value. A deliberately removed dollar prefix made the copied full suite fail.
- **Reachability and lifecycle: verified.** `run_tests.py:18-31` discovers full
  tests independently of tags. Audit execution selected focused/full 9 and smoke
  4; all baseline focused, smoke, and reverse/repeated full runs passed. The
  stateless contract needs no resource cleanup; interleaving/rejection recovery
  is asserted at `test_pricing.py:96-122`.
- **Improve: verified complete.** The authoritative result is `complete` with
  verifier `ok` in `.until-loop/state.json:110-115`; its two distinct completed
  reviews and no-change streak are recorded at `.until-loop/working.md:103-140`.

## Trial 02 — price-format

- **Oracles and coverage: verified.** Literal unit tests cover products,
  exact formatting, invalid types, booleans, and stateless recovery; mutating
  type checks to `isinstance` made the copied full suite fail on bool inputs.
  Audit execution selected focused 8, smoke 5, full 12 and passed all baseline
  routes, including reversed/repeated full.
- **Reachability and lifecycle: verified.** Full discovery remains independent
  of tags (`run_tests.py:18-31`), and the documented stateless no-setup model is
  exercised by cross-call recovery tests (`test_pricing.py:66-101`).
- **Finding: Improve is blocked, not complete.** The required authoring commit
  could not stage because `.git/index.lock` was read-only; the work record says
  no completed converged reviews and streak 0 (`.until-loop/working.md:28-44`),
  and the authoritative result is `blocked` (`.until-loop/state.json:101-114`).
  Do not report the two-review/commit completion condition for this trial.

## Trial 04 — sqlite-catalog

- **Oracles and coverage: verified.** Exact row/value expectations, invalid-input
  state preservation, duplicate recovery, sorting, reopening, delay ordering,
  isolation, and close semantics are exercised in `test_catalog.py:14-152`.
  No production-derived expected values or production mutation by tests was
  found. A copied no-op `Catalog.close` made the full suite fail at both release
  and partial-setup assertions.
- **Reachability and mutable lifecycle: verified.** Audit execution selected
  focused/full 11 and smoke 5; baseline focused, smoke, and reverse/repeated
  full passed. Per-test temporary database ownership is explicit
  (`test_support.py:17-20`), connections are tracked and finally closed
  (`test_support.py:23-38`), and partial setup exposes the acquired handle before
  fallback cleanup (`test_support.py:52-60`). The close/partial assertions occur
  before that fallback (`test_catalog.py:120-128`, `142-152`). The review helper
  additionally proves body-failure propagation and fallback closure
  (`.until-loop/checks/review-2-assets.py:25-48`).
- **Improve: verified complete, self-review limitation disclosed.** State records
  `complete` and verifier success (`.until-loop/state.json:123-128`), with two
  distinct no-change reviews (`.until-loop/working.md:48-66`, `102-143`).

Residual limits: mutation checks were representative, not exhaustive; the two
price APIs specify no resource lifecycle, and neither price fixture supplies
cleanup-failure behavior to verify.

## Trial 03 — sqlite-catalog

- **Finding: TC-13 is a valid contract discovery, not an invalid test.** The
  public contract accepts a positive `int` without a maximum (`SPEC.md:5-7`),
  and `2**63` therefore belongs to the accepted domain. The test's independent
  success oracle (`test_catalog.py:67-74`) is correct; copied targeted and full
  execution reproduce a single `OverflowError` at `catalog.py:33`, while
  `2**63 - 1` passes. This is a legitimate expected production RED.
- **Calibration qualification.** The retained starter covers only seeds
  (`test_starter.py:4-8`), so it cannot establish the unbounded accepted-input
  claim. Treat its prior omission of the SQLite boundary as incomplete initial
  coverage, not a hidden storage-limit interpretation. Current `TESTING.md`
  explicitly exposes the gap and does not calibrate it away (`110-124`).
- **Reachability, lifecycle, Improve: verified with limits.** `--list` includes
  TC-13 in focused/full (not smoke), fresh temporary catalogs and pre-fallback
  connection assertions are used (`test_support.py:17-58`; `test_catalog.py:94-116`).
  Improve is correctly **blocked**, not complete: its material TC-13 change reset
  the streak and the required commit failed (`.until-loop/working.md:103-139`,
  `159-167`; `.until-loop/state.json:107-127`).

## Trial 05 — expected-red

- **Oracles and expected RED: verified.** Literal SPEC-backed tests cover ASCII
  conversion, digits, separator runs, boundaries, non-ASCII separation, empty
  results and type rejection (`test_slug_contract.py:12-86`). The copied current
  full suite remains red as documented; replacing only copied production with the
  supplied conforming reference makes all eight tests pass. The public calibration
  itself also passes against reference and fails against its mutant.
- **Reachability and lifecycle: verified.** Discovery reaches focused/full 8 and
  smoke 4; pure-function tests have no mutable resources. Improve completion is
  supported: two distinct no-change reviews, a sensitivity control, state phase
  `done`, and decision `complete` (`.until-loop/working.md:61-79`, `130-177`;
  `.until-loop/state.json:60-103`). Self-review is disclosed.

## Trial 06 — expected-red

- **Oracles and expected RED: verified.** Broader literal separator, boundary,
  Unicode, empty-result and type coverage is present (`test_slug_contract.py:10-87`).
  Copied current full remains red; the supplied conforming reference passes all
  ten tests, and the public calibration passes reference/fails mutant.
- **Reachability and lifecycle: verified.** Discovery reaches full 10, focused 4
  and smoke 4. Tests are stateless and contain no cleanup surface.
- **Improve: correctly blocked.** The original test assets remain uncommitted
  after `git add` cannot create `.git/index.lock`; no review streak is claimed.
  The authoritative state is `blocked`/`paused` (`.until-loop/working.md:22-44`,
  `.until-loop/state.json:68-128`).

## Separate follow-up — price-candidate-no-commit

- **Runner fixes: verified.** The new disposable-fixture regressions assert
  nonzero exits for empty execution, discovery/import errors in listing and every
  suite, assertion failures, and full/subset reverse-repeat registration
  (`test_run_tests.py:25-101`). Copied execution passed all four. Their temporary
  directories register cleanup before fixture writes (`test_run_tests.py:25-37`).
- **Original coverage retained: verified.** Copied `--list` reports 17 full IDs;
  an exact set comparison confirms all original 12 remain, with only four runner
  cases plus TC-12 added. This is a separate no-commit follow-up, not a revised
  finding about either original price trial.
- **TC-12 RED: valid and retained.** `SPEC.md:4-6` has no size cap on valid
  nonnegative integers. The literal oracle for `format_price(10**5000)` derives
  the expected string without integer-to-decimal conversion (`test_pricing.py:128-131`).
  Copied full execution ran 17 tests: 16 passed, TC-12 raised the Python
  4300-digit conversion-limit `ValueError`, exit 1. This is an immutable-production
  contract RED, not an oracle error or a reason to change interpreter settings.
- **Improve: correctly paused at cycle 1, not complete.** The no-commit policy
  was honored; pause is due to immutable production and failed current full checks,
  with streak 0 (`.until-loop/state.json:76-145`; `.until-loop/working.md:37-61`).
  A historical 16-test verifier is explicitly stale for the current 17-test
  candidate and must not be reported as success.

## Follow-up status observed in this pass

- **red-candidate-no-commit: completed.** Current state is `done`, cycle 3,
  decision `complete`; its product RED remains an explicit expected outcome.
- **sqlite-candidate-no-commit: not final.** Current state remains `active`,
  cycle 0 with no assessment; no completion claim is supportable yet.

## Separate follow-up — red-candidate-no-commit (final)

- **Original contract retention: verified.** An exact copied `--list` comparison
  confirms all original ten product IDs remain in full; the only additions are
  four runner-regression IDs. The original literal assertions remain in
  `test_slug_contract.py:10-87` and the starter is retained separately.
- **Expected RED is genuine.** Copied current production runs 14 tests and fails
  68 subtests, exit 1; all four runner tests pass. Replacing *only* copied
  `slug.py` with a conforming ASCII-run implementation makes all 14 tests pass,
  exit 0. This supports the product failures as SPEC-backed rather than an
  oracle/harness artifact (`SPEC.md:3-6`; `test_slug_contract.py:23-87`).
- **Runner repairs and lifecycle: verified.** Four isolated subprocess fixture
  tests cover empty full/subset selections, discovery-error reporting in listing
  and every suite, and reverse/repeat selection (`test_run_tests.py:28-75`).
  Each owns a temporary directory and subprocess lifecycle (`29-37`).
- **Improve: verified done with disclosed self-review fallback.** Cycle 1 made
  the material runner repair; cycles 2 and 3 are distinct no-change reviews with
  streak 0 -> 1 -> 2 (`.until-loop/working.md:21-33`, `35-49`, `51-69`). State is
  `done`, cycle 3, decision `complete`; independent review is explicitly marked
  unavailable rather than claimed (`.until-loop/state.json:60-103`).

### Minimal reproducible generated sample

Retain exactly these source/test/instruction files; exclude `.git/`,
`.until-loop/`, raw GUIDANCE, `PRIOR_RUN.md`, and raw result/evidence transcripts:

```text
SPEC.md
TESTING.md
slug.py
run_tests.py
test_support.py
test_starter.py
test_slug_contract.py
test_run_tests.py
```

## Separate follow-up — sqlite-candidate-no-commit (final)

- **Runner correction: verified.** `--list` now returns after reporting discovery,
  even when `--suite` is present (`run_tests.py:46-49`). Copied
  `--list --suite smoke` printed only the selector JSON and exited 0. TC-14 uses
  a nonempty tagged test body with a file-write sentinel to verify that guarantee
  (`test_runner.py:66-90`); TC-15 separately verifies reverse/repeat order and
  aggregate failure retention (`92-116`).
- **Retention and lifecycle: verified.** The original catalog behavior cases and
  independent TC-13 success oracle remain intact (`test_catalog.py:67-74`).
  Copied runner suite passed all six tests. Its temporary child directories are
  registered for cleanup before test work (`test_runner.py:10-24`).
- **Expected RED and Improve: verified paused.** Copied full suite ran 15 tests
  with 14 passes and only TC-13's `2**63` SQLite-binding error; smoke remains 3
  passes. The bound state is `blocked`/`paused`, cycle 1, because immutable
  production prevents the valid TC-13 success contract from passing; no qualifying
  clean-review streak is claimed (`.until-loop/state.json:60-103`,
  `.until-loop/working.md:54-65`).
