# ShipLoop E2E harness: defects and fixes journal

Started 2026-10-29. Living record of defects found in the E2E harness itself (grading, measurement, monitors) and their
fixes, one entry each, newest last. Edit in place; mark superseded claims with the date and the reason rather than
deleting them.

This is not the round journal. `test/shiploop_e2e/LEARNINGS.md` holds the E2E rounds, and the release preflight reads
any commit that touches it after a ShipLoop commit as an E2E round for that commit. A harness fix is not a round, so its
entry lives here, and no entry here vouches for a ShipLoop change.

## A model that abandons its first ShipLoop run left the output ungradable: one rule now picks the live run (2026-10-29) — status: firm for the defect and the fix; the sticky recorded identity is an open edge

**What was seen.** The brownfield session's R1 run (`~/e2e-runs-brownfield/20261029/bf-ds-r1-ticket-assignment`, DeepSeek
flash) intaken a request that shell quoting had mangled (S8 to S10 were lost). The model paused its own first run
(`work-20261029-142617-dad502`, `status_reason`: "Run intaken with a shell-mangled request … replaced by a fresh run") and
started a second (`work-20261029-142643-b5c43b`). With two runs under `.shiploop-runs/`: `run.grade_shiploop` found two
runs and nothing to tell them apart, so the verdict was `ambiguous` and the run could never pass, whatever the product did;
`metrics.run_dir_of` returned None, so stage times, the planning window and refusals went unmeasured; and the progress
monitor, taking the first `state.md` in path order, read "paused, rev 1, intake" for the whole run. The brownfield session
reported it and worked around it by hand (`record_run_identity` then `--grade-only`).

**What changed.** `test/shiploop_e2e/run_choice.py` is the one rule: the run `shiploop-run.json` records while its state
is readable; else the only run that was not there before the invocation; else, among several, the runs not paused or halted
(done and blocked stay in play), one of which is the run, several told apart only by the one the host's `--run-dir`
commands named; when every run is paused or halted, the one whose `state.md` changed strictly last. Anything left is a tie:
the verdict is `ambiguous` and lists only the tied runs, `run_dir_of` returns None, the monitor and the card say
`ambiguous`. Nothing is picked at random, and a run that was already there when the invocation started is never a
candidate. A choice that follows the runs' statuses is made again at every reading and is not recorded, because a model can
resume a run it paused. The runs not chosen are listed as `other_runs`. The same rule now serves `grade_shiploop`,
`metrics.run_dir_of`, `progress.py`, the owner-note watcher, the Live Run Card (`status_card.build_e2e`) and
`packets.find_run_dir` (the flow viewer, the packet report and the owner page). A folder with exactly one run grades with
the same keys in the same order as before.

**Evidence.** 21 new tests in `MultipleRunsTest` (`test/shiploop-e2e.test.py`), each asking the readers: 19 of 27 failed on
the unfixed source (the verdict `ambiguous`, `run_dir_of` None, the monitor on the paused run, an arbitrary first-in-path
pick for two live runs) and all pass after; mutation checks (newest wins among live runs, halted not set aside, blocked set
aside, always recording an identity, taking the first of a tied newest moment, ignoring the recorded identity) were each
killed by at least one test. On a copy of the real example's two `state.md` files and its `shiploop-run.json` (nothing was
written to the live folder) the verdict chose `work-20261029-142643-b5c43b` with the paused run in `other_runs`, and the
monitor read "active, rev 8, stage plan". A review found the Live Run Card and `packets.find_run_dir` still taking the first
run in path order; both now use the rule. A second review's `~nobody/run` finding (`Path.expanduser` raises `RuntimeError`
on an unresolvable `--run-dir`, which would crash the verdict and now the monitor) was reproduced by a fail-first test and
fixed.

**Open edges.**
- A recorded identity is sticky by design: when the only run present at one grade is recorded and the model abandons it for
  a second run in a later resumed session, the recorded run keeps winning. If a real run shows it, treat an identity whose
  basis is "the only new run" as soft (superseded when that run is paused or halted and exactly one other new run is in
  play).
- Run Review's exporter (`skills/shiploop-run-review/scripts/export.py`) may not import from `test/`: it takes the run
  `result.json` names, which the verdict wrote from this rule. Nothing reads `other_runs` to flag a model that started
  several runs; surfacing it in Run Review is a skill change and needs a release.
- Two live runs, or a finished run beside a live one, stay `ambiguous` even when one is newer; the 2026-10-16 audit control
  requires it.
