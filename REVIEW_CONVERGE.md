# Review Converge: the TAP count reader (P5) and the verify-record scan (P9a) from the Grok chat review

**Target paths:** `skills/shiploop/scripts/shiploop_test_counts.py`, `skills/shiploop/references/testing-and-documentation.md`, `changes/shiploop/tap-count-reader.md`, `test/fixtures/shiploop-tap/`, `test/shiploop-test-counts.test.py`, `test/shiploop-test-loop.test.py`, `test/shiploop-domain-words.test.py`, `test/suite_catalog.py`, `test/shiploop_e2e/metrics.py`, `test/shiploop-e2e-analysis.test.py`, `docs/experiments/grok-chat-full-run-review-20261114/`
**Test command:** `python3 test/shiploop-test-counts.test.py && python3 test/shiploop-test-loop.test.py && python3 test/shiploop-domain-words.test.py && python3 test/shiploop-handoff.test.py && python3 test/shiploop-loophole-gates.test.py && python3 test/shiploop-e2e-fidelity.test.py && python3 test/shiploop-e2e-analysis.test.py && python3 test/shiploop-e2e-quality.test.py && python3 test/test-groups.test.py`
**Started:** 2026-11-15          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 1
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.claude/plans/async-beaming-hoare.md`
**Plan hash:** `3ee7aebe662f4463b44d372e6fce1ea16402ea8699d8a4f983e3ebded936acf7`
**Base ref:** `5b48232f0dd3295b545efc509f0760d8cd26a2ba`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-11-15
**Review:** 0 material, 7 minor
**Material findings:**
- none
**Deferred (minor/P2):**
- [ ] P2: the change note and the README list understate the tightening. A TAP `not ok` at exit 0 is now a masked failure for every row kind (a regression row without `min_tests`, an unlisted failing point, a `check` such as a linter that marks warnings `not ok` at exit 0). `1..0` was `passed-uncounted` or `passed`, not `uncounted`, for rows without `min_tests` — docs; no retained run hits it
- [ ] P2: a point indented by 2 spaces or a tab is neither nested nor a point, so it is dropped (`shiploop_test_counts.py` `_TAP_NESTED`). Treat any indented point or plan outside YAML as not flat (`None`) and add a control — edge; TAP 14 needs 4-space indents and nothing retained hits it
- [ ] P2: `_skip_line` applies the TAP directive rule to indented points (`^\s*`), where the plan said `^(not )?ok\b`. Record the deviation in the journal and pin one indented control — forward drift; 2,789 retained (output, ids) rows unchanged
- [ ] P2: test gaps. The YAML control's `1..3` is indented (ignored even without YAML skipping); no column-0 plan or `Bail out!` inside YAML is exercised; "first directive wins" is not asserted through `named` — coverage
- [ ] P2: two route tests substitute: the base-floor test writes a synthetic base record, and the reuse test exercises `_reused` rather than `take_check`. Note both in the journal — forward drift in a listed test; no TAP-specific logic on either path
- [ ] P2: replay method. The (e) series hold only newly counted rows (a floor is the maximum over all counted runs; including them still gives 0 falls); the script overwrites the manifest instead of verifying it; the evidence header reads base == HEAD; cut rows are only counted. Fix: every counted row in each series, verify against the manifest, rerun from HEAD against the true base — method
- [ ] P2: stale text. The READERS comment (mocha's TAP totals); the `_SKIP_LINE` comment (TAP's `# SKIP`); the `analysis/verify_readers.py` docstring (now a copy of the pre-fix version); the README Corrections bullet on `_RUN_ROWS` (mark it superseded, with the date); the reader commit's straddle framing (1.35.0 shipped without the reader, so the next release also straddles 1.35.0) — docs
**Git-history check:** reviewed the change 5b48232f..830a38f2 (92b55c80 the reader, 84f1a650 the replay, 830a38f2 the verify scan), which is the same diff as 17cd64b4..13aafcd3 before the rebase. It builds on c38f6887abfcc4a51fab616fddc7c3714d3f41e1 (the node reader: an unread summary is refused, not guessed), 9b4bc8ae7cf171ddcbdd451a3e1f84dfb029a0e0 (text and JSON readers agree on result rows) and a3b2f975487ebb7ede6987628c4a931941f9b057 (only a passing check is reused). This target has no earlier review-converge round; earlier round commits in this repository are other campaigns.
**Plan:** n/a (clean round)
**Plan review:** n/a (clean round)
**Implementation:** n/a (clean round)
**Lint:** n/a (clean round). The reviewer reports ruff E9/F/B clean on the changed files.
**Test result:** N/A (clean round)
**Outcome:** clean
**Error signature:** none
**Learnings:** The thesis was that the TAP reader and the string-aware verify scan honour Phase 1 of the plan with no regression, and the review established it. The reviewer re-derived the replay from HEAD read-only: 8,925 rows, 4,434 unique inputs, (a) 0, (b) 75 by tap, and the positive control flips. It re-derived fail-first against the 5b48232f reader (12 of 14, 4 of 5, 9 of 9). It ran an old-versus-new `count` over the 207 other text fixtures at exit 0, 1 and 5 and found no difference. It ran all eleven named suites green on 830a38f2. What it surfaced is breadth, not defects. The masked-failure rule now reaches every TAP row kind, which the change note should say. The flat-stream rule has an undercount edge (2-space indents) that is cheap to close. The replay's floor series could include rows the old reader already counted (it still gives 0 falls). Surprising: the rebase moved nothing the change reads. The reader, test loop, test layers, metrics and fidelity files are byte-identical across the two bases, so the evidence carries over.
**Anchor evidence:**
- Step 1 contract → `skills/shiploop/scripts/shiploop_test_counts.py` `_tap` (one plan first or last, numbering checked over the points seen, TAP 14 directives, YAML/comment/CRLF/version skipped, `1..0` → 0, unread shapes → None)
- `count()` order → probes match the base reader except the registered exit-5 case (`TapStreamTests.test_exit_status_5_with_a_tap_stream_reads_the_stream`)
- Known limits pinned → `TapStreamTests.test_known_limits_are_pinned`, `TapCountRouteTests.test_a_check_recorded_before_the_reader_is_reused_as_recorded`
- Replay (a)/(b)/(c)/(e) and the control → `docs/experiments/grok-chat-full-run-review-20261114/evidence/replay-counts.txt`
- Step 2 scan → `test/shiploop_e2e/metrics.py` `_RUN_ROWS`; 1,828 of 1,828 agree in `evidence/replay-rows.txt`; the new analysis test fails on the base version
**Consecutive clean rounds after this entry:** 1
**Committed:** yes
**Notes:** Reviewer: a fresh read-only general-purpose subagent, resumed once after a session restart with the rebased SHAs (`REVIEW_CONVERGE_REVIEWER` unset; an optional tool, not native). The ledger's Base ref moved from 17cd64b4 to 5b48232f with the rebase, before any round was logged.
