---
Execute: ask
Scope: the ShipLoop E2E harness (test/shiploop_e2e/), its suites and how it is run
Reviewed at: origin/main 31933a73 (skill-craft 2.9.0, ShipLoop 1.9.0), in a detached scratch worktree
Evidence: docs/experiments/e2e-runner-review-20261024/
Status: plan; nothing implemented
---

# E2E runner review and improvement plan (2026-10-24)

## Status (updated 2026-10-24, evening)

- **The owner approved wave 1, items 1.1, 1.2 and 1.4**, on a branch, with 1.5 run after chess run 5 ended. All three are
  built on `feat/e2e-wave1-6e86ad` and recorded in LEARNINGS ("E2E runner review and wave 1"). Nothing is merged or
  pushed.
- **Deviations from the plan:**
  - 1.1 has no `--runs-root` flag. `$SHIPLOOP_E2E_RUNS_ROOT` and the grandparent default cover the layout, and a flag would
    have to be carried by every printed resume command.
  - 1.4 is opt-in (`--release-gate`), so the committed report pins are unchanged.
  - 1.2 reverses a recorded 2026-10-04 decision ("the Battleship checks are protocol checks"). That entry is now marked
    superseded, with E2b as its evidence: all 11 saved real deliveries pass and the audit server fails.
- **Chess run 5 ended BLOCKED** at W1 implement after about 1.5 h: the session guard blocked a deploy to `de`. Its regraded
  `result.json` shows 0 overlap, which is F2 in a live record. Its progress watcher outlived the run.
- **1.5 (the release gate) started** at about 19:10 from a clean origin/main worktree (`.claude/worktrees/e2e-gate-b60ed7`).
  - The version gate refuses marketplace runs from a branch with unpublished commits, so wave 1's code is not in these
    runs.
  - Their overlap and Battleship verdicts are re-read with the wave 1 readers after they end.
  - Results (LEARNINGS "Release gate on 2.9.0"): hello, seat-reservations and csv-report passed on Claude, and Codex
    hello passed after one resume. Battleship's FAIL was a harness false fail: a check deleted the product's `page.html`
    (E4); its fix awaits the owner.
  - The Grok hello is not run yet: other sessions' Grok runs were live throughout.
  - E5 found that the runs-root default gave suite cases only their day folder; fixed on the branch.

## Verdict

**As an instrument, the harness is sufficient and in places more than sufficient. As it is being run, it is not.**

- The measuring is strong. Grading binds to the run the invocation created (`shiploop-run.json`). A resume keeps its driver.
  Each run is isolated and version-gated. The platform guard and `fake_sf` cover the hosted cases. Refusals, dodges,
  fidelity, packets and commits are all recorded, and the hermetic suites cost 669 s summed over 20 files.
- **What fails is coverage, verdict validity and time to signal:**
  - No case has reached `done` from a marketplace release since 2026-10-10 (skill-craft 1.27.0, ShipLoop 0.59.0).
  - Two verdict paths can mislead.
  - One data point on the case the work iterates on takes 4-5 hours, and it ends STOPPED.

## Findings

Each status follows the journal convention: firm, interim or exploratory.

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | **The release gate has not run on any 2.x release.** The last marketplace pass per case: battleship 2026-09-26, battleship-scoring and csv-report and seat-reservations 2026-09-27, hello and checkers 2026-10-10. The two later off-Salesforce passes (battleship 10-11 and 10-16) were `--source checkout`, which SPEC says is never evidence about a release. Since 10-17, every full run has been a Salesforce case on Grok (8 folders), and none reached `done`. No Codex run has ever written a `result.json`. SPEC's rules on breadth, promotion, smoke first and rotating probes are therefore not being met. | firm | [d1-staleness.json](experiments/e2e-runner-review-20261024/d1-staleness.json); `~/e2e-runs/202610*/*/result.json` |
| F2 | **The overlap record misses concurrent runs in other folders.** `environment.overlap` reads only sibling folders under the same parent. During chess run 5's first 87 minutes, 16 other runs (the E6 R1 Grok slices under `~/e2e-runs/e6-r1-20261024/`) overlapped it, for 4.24 hours summed, and the record sees 0. Runs 3 and 4 had no overlap anywhere. So the run-5 report's timing comparison with runs 3 and 4 is confounded, and run 5's own record will say otherwise. | firm (E1) | [e1-overlap.json](experiments/e2e-runner-review-20261024/e1-overlap.json), [overlap_probe.py](experiments/e2e-runner-review-20261024/overlap_probe.py) |
| F3 | **The Battleship checks pass a broken product.** On 2.9.0, all 4 checks still pass the 2026-10-16 audit fixture: no fleet, `gameOver` true from the start, and one placeholder test. That backlog item has been deferred since 10-16. Checkers, by contrast, has a held-out acceptance check (`checks/checkers_accept.py`). Battleship is the most-run web case. | firm (E2) | [e2-oracle.json](experiments/e2e-runner-review-20261024/e2-oracle.json), [oracle_probe.py](experiments/e2e-runner-review-20261024/oracle_probe.py) |
| F4 | **An unfinished run leaves nothing to compare against.** `run._main` writes a baseline row only for a run that was not resumed, seeded or unfinished. Chess runs 3 and 4 were STOPPED and have no row. Their comparison with run 5 comes from an 819-line generator (`chess5-report/collect.py`, `render.py`) in another session's scratchpad. That generator is lost when the session ends, and it duplicates readers that `metrics.py` already has. | firm | `run._main` (`baseline_file = ... if not (resumed or seeded or unfinished)`); scratchpad `8acf399b-…/chess5-report/` |
| F5 | **The automated review loop is maintained but unused.** No retained run folder holds a `review.json`. `review.py` and `iterate.py` still receive fixes (the validity fix of 10-16), but the loop actually in use is a coordinator session, journals, Run Review and advisors. | firm for the count | `find ~/e2e-runs -name review.json` returns 0 |
| F6 | **Grok sessions churn.** In run 5, sessions 2 and 4 ended after 22 s and 47 s with no accepted action. Run 3 had one such session; run 4 had none. Each one costs a resume and a re-orientation. This is an engine or host behaviour, and `sessions.jsonl` and `fresh_starts` already record it. | interim (3 runs) | `sessions.jsonl` of the three chess runs |
| F7 | **The harness code has grown fast; its output has not bloated.** The Python grew from 2.8K lines (09-28) to 12.2K (10-12) to 21.3K (10-24). `run.py` is 4,674 lines, with a 956-line `_main`. The harness took 135 commits in 12 days, and the README is 1,814 lines. **But E3 shows the outputs are used:** 25 of the 33 `metrics.json` blocks have a reader, and the 8 without one total 981 bytes. So pruning outputs is not the lever; the cost is in the code and the docs. | firm for the counts, interim for the cost | [e3-consumers.json](experiments/e2e-runner-review-20261024/e3-consumers.json) |

**Already sufficient, keep as is:**
- grading identity;
- resume and driver identity;
- isolation and the version gate;
- the platform guard and its coverage record;
- the release slice (`--seed-at release-plan`) and the step slices;
- dodge counters and refusal gates;
- test selection. The defect where any file under `test/shiploop_e2e/` pulled all 15 suites is fixed: `LEARNINGS.md` and `baselines.jsonl` now map to specific suites in `test/suite_catalog.py`.

## Constraints on when to act

- **Chess run 5 is in flight** under a 5 h cap, and its report compares timings with runs 3 and 4. Under the batch rule
  (the owner's rule: a batch runs to completion), no engine change lands mid-batch. Starting more live runs now would add to the overlap in
  F2, and SPEC says runs compared on wall time run one after the other. So live runs wait until run 5 ends.
- **The E-EFF1 and E6 sessions hash `run.py` and `slice.py` in their manifests.** Harness changes therefore land on a
  branch from origin/main, and those sessions are told before the changes reach main.
- **The canonical checkout is 25 commits behind origin/main**, with another session's uncommitted harness edits
  (`run.py`, `slice.py`, `sessionlog.py` and two test files). This plan's commits go on a branch, not into that tree.

## Plan

Items are ranked by gain. Each one names its anchor, its change, its test and the condition for adopting it, per SPEC Change admission.

### Wave 0: now, no code (does not disturb run 5)

**0.1 Caveat the run-5 timing comparison.**
- Anchor: "Runs compared on wall time or per-call cost run one after the other".
- Change: put E1's figures in the run-5 report and in F12, next to every minutes comparison with runs 3 and 4. Rerun
  `overlap_probe.py` when run 5 ends, so the final overlap is recorded.
- Consumer: the run-5 report session (`8acf399b`) and the owner.
- Size: one paragraph.

### Wave 1: after run 5 ends (harness only, one branch, one release)

**1.1 Make the overlap record see every concurrent run (F2).**
- Anchors: "Concurrency must not change a verdict"; SPEC's "Known limit: a baseline row carries no overlap field".
- Change:
  - `environment.overlap` scans a runs root recursively for `timeline.jsonl`, skipping files whose mtime is before this
    run's start, so the scan stays cheap. The root is `--runs-root`, defaulting to the output's grandparent.
  - The baseline row gains `overlapped_runs` (a count, or null with a reason).
  - At launch, the harness prints the live `.harness-lock` folders it finds under the root. It prints and never refuses.
  - SPEC's overlap basis text is amended in the same commit.
- Test: a fixture with a sibling run in another parent folder, plus a replay of E1 on compact timeline extracts. The
  replay must give 16 for run 5 and 0 for runs 3 and 4.
- Adopt when: the replay matches E1, and the scan of `~/e2e-runs` takes under 1 s. Without the mtime filter, reading
  all 462 timelines there took 2.9 s, so the filter is required.
- Not done: excluding overlapped rows. The record stays a record.
- Size: S.

**1.2 Give Battleship a game-progression check (F3).**
- Anchor: S-9 (a passing script-run check is the evidence).
- Change: add `checks/battleship_accept.py`, modelled on `checkers_accept.py`. Through the public API it checks:
  - a fresh game is not over;
  - firing at every cell produces at least one hit and one `sunk`;
  - `gameOver` turns true only once the fleet is sunk;
  - a shot after the game is over is refused or changes nothing.

  It replaces the shallow fire check in `battleship`'s `checks`. battleship-scoring inherits it.
- Adopt when: it rejects the audit fixture, and a `--grade-only` regrade accepts the saved passing deliveries
  (`20261010/battleship-1`, `20261011/battleship-probe-28191c5b`, `20261016/battleship-e2eaudit-4dd3b4b4`). If one of those
  fails, that is a finding about the run, recorded as such, not a reason to weaken the check.
- Open: should this be a verdict, or a held-out record as for Checkers? Recommended: a verdict, because `checks` is the
  claim that the product works.
- Size: S.

**1.3 Commit the cross-run comparison (F4).**
- Anchors: S-11 (knowledge retained in the repository) and S-12 (one implementation per mechanism); the rule that
  evidence is kept in the repo, never only in a scratchpad.
- Change: once the run-5 report is published, move `collect.py` and `render.py` into
  `test/shiploop_e2e/compare_runs.py <run>... --out figures.json [--html page.html]`. It reads run folders directly, and
  only through the `metrics.py` helpers, so it works on STOPPED runs without changing any baseline rule. Its fixture is
  compact extracts of runs 3 and 4. Register the suite in `test/suite_catalog.py` (new suites are registered there).
- Adopt when: it reproduces the published run-3, run-4 and run-5 figures cell for cell. That includes the known fix to
  run 3's "W1 full cycle" (51.8 min, not 52.0).
- Not done: writing baseline rows for unfinished runs. Reading the run folders directly answers the need without
  touching `matching_rows`.
- Size: M.

**1.4 Make a stale release gate visible (F1).**
- Anchors: SPEC "Promotion"; "Choose the verification runs from a coverage map".
- Change: `run.py --baseline-report` prints one line per suite style: its last marketplace pass (date, plugin, ShipLoop
  version, driver) against the version origin/main's catalog publishes, and how many ShipLoop releases lie between.
  This is a record, not a gate.
- Test: a fixture `baselines.jsonl`.
- Size: S.

**1.5 Run the release gate on 2.9.0.** This is a run, not code, and it comes after 1.1 so its overlap is recorded.
- Anchor: SPEC "Batch changes, then verify the batch ... smallest first".
- Runs, one after the other, on Claude Sonnet from the marketplace:
  1. `--suite batch`: the `hello` gate first, then seat-reservations, battleship and battleship-scoring;
  2. `csv-report`, to complete breadth;
  3. one `hello` on Codex (`--effort xhigh`);
  4. one `hello` on Grok.
- Estimate: about 1.5-2 h of wall time and about $40-80. This extrapolates from the medians of the last passing Claude
  rows (hello 11 min / $3.69, battleship 13 min / $6.11, checkers 16 min / $4.18) and the 10-16 run (274 turns, $5.46).
  It is not a measurement: 2.x has more gates.
- The owner's standing rule allows launching verification runs without asking (owner, 2026-10-07).
- Result: the first marketplace `done` on 2.x, or the first evidence that 2.x breaks a style that chess does not exercise.
  Either way it is the evidence the renames R1-R4 (check→proof, criterion/requirement, consumer→due_stage, the Improve
  callbacks) need outside one Salesforce case.
- Size: runs.

### Wave 2: owner decisions

Each of these changes what the harness is for, so each is the owner's call.

**2.1 The review loop (F5).**
- Recommended: retire `iterate.py`, `review.py` and the README flowchart (the owner's rule: one supported version).
  Outside its own tests, nothing calls `review.py`. `skills/shiploop-run-review/SKILL.md` names `iterate.py` as one of
  `export.py`'s callers, so that line changes in the same commit.
- The alternative: adopt the loop, with the review-brief compaction that has been deferred since 10-16 (96% of the
  95K-character review prompt is SPEC text).

**2.2 Codex as a driver.**
- Option A: keep Codex in `hosts.HOSTS` and give it one smoke run per release (1.5 above).
- Option B: remove it. Today "the driver is a parameter" is untested live for Codex.

**2.3 How often the hosted case runs in full.**
- Proposed: every release gets the gate (1.5), one step slice and one release slice (`--seed-at release-plan`).
- The 5 h chess run then happens only when a change touches cross-item flow or the outer stages, or when the owner asks
  for a report.
- This turns a 5 h, n=1 signal into roughly 1 h of signal per release, with the full run as confirmation.

### Wave 3: only when touched (no project of its own)

**3.1** Split `run._main` into launch, grade and record functions, but only in a commit that already changes it. Add no
new `metrics.json` block without a named reader (the owner's rule: every output names its consumer). E3 says the existing ones are read; keep
them.

**3.2 Session churn (F6).**
- The record is already there. If the Grok keepalive work needs a figure, add `sessions.no_progress` (sessions that
  ended with no accepted action) to `metrics.json`.
- Otherwise, leave it.

## Rejected after the experiments

- **Pruning `metrics.json` blocks.** E3 found that 25 of 33 have readers, and the unread 8 total 981 bytes. Pruning gains
  nothing.
- **A new verdict class for weak oracles.** One stronger check per case, where a fixture proves it is too weak, is
  enough (the owner's KISS rule for findings).
- **Overlap as an exclusion rule.** It stays a record; the serial rule is the discipline.

## Order and dependencies

```
0.1 ─────────────────────────────── now
run 5 ends ─► 1.1 ─┬─► 1.5 (live, serial) ─► LEARNINGS + journal entry
                   │
        1.2, 1.4 ──┘   (parallel with 1.1, same branch)
run-5 report done ─► 1.3
2.x decisions ─► whenever the owner answers; 2.3 shapes the next batch's coverage map
```

1.1, 1.2 and 1.4 touch disjoint files (`environment.py`; `checks/` and `cases.json`; `run.baseline_report`) and can be
built in parallel. 1.5 needs 1.1, so its own overlap is recorded, and 1.2, so Battleship's verdict means something. 1.3
waits for the run-5 report, so its cell-for-cell test has a published target.
