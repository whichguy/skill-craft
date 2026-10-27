# ShipLoop E2E stash conflict review

This is a stash application, not a branch merge. In the captured index, stage 2 is **Updated upstream** (HEAD with the no-default-caps and stalled-resume policy); stage 3 is **Stashed changes** (the effort-schedule experiment). Stage 1 is their common base. The saved working snapshots are important because some effort hunks merged automatically and are missing elsewhere without conflict markers. I inspected these snapshots and related tests/source only; no tests were run.

## Minimal merge direction

Keep stage 2's default policy and stall protection, then reapply stage 3's effort schedule behavior. Do not use stage 3 wholesale: it restores finite defaults and removes the stage-2 stall logic. The present captured working `run.py` has both a stage-2-style resume loop and a second stage-3-style loop adjacent to one another; consolidate to one loop.

### `test/shiploop_e2e/run.py`

Keep the stage-3 additions for `effort`/`uuid`, `planned_session_id`, `either`, schedule argument and planner setup, planned Grok ID, effort-aware logging/invocation/result, boundary stop, resume prompt, and restart bookkeeping. Keep stage 2's `RESUME_STALL`, defaults of `None` for turn/budget/timeout/resume limits, optional serialization in `resume_command`, infinite/monotonic deadline behavior, and no-progress failure/stop classification.

The merged resume loop must satisfy all of these together:

- If `--max-resumes` is omitted, ordinary resumes remain unlimited; when supplied, only ordinary host-ended resumes consume that budget.
- An effort boundary restarts the session and updates effort but does not consume the ordinary resume budget (`restarts` bookkeeping).
- Repeated unchanged revisions still trigger stage 2's three-session stall stop, including when schedule boundaries are present. Count ordinary resumed sessions for stall detection without treating an effort restart as progress or accidentally suppressing the stall stop.
- Use `last_session_id(...) or planned_session_id(...)` when resuming, since a boundary or crash may precede Grok's first reported session ID.

Do not retain both `while` loops from the captured working snapshot: the first is the stage-2 resume/stall loop and the second the stash's effort-aware loop. Combine their conditions and bodies into one loop, with explicit ordinary-resume versus boundary accounting.

### `test/shiploop_e2e/slice.py`

Keep stage 2's no-limit defaults and monotonic active-time deadline, plus stage 3's planner, effort logging, planned Grok ID, and `reeffort` classification. The captured working snapshot has `drive()` able to set `process["status"] = "reeffort"`, but its outer loop has no `reeffort` branch: after the boundary the loop falls through and ends the slice. This can happen without any conflict marker. Restore the stage-3 reeffort branch: consume the planner boundary, select the next effort, and continue the same resumable host session (or start a fresh session for non-resumable hosts); don't increment `resumes` for this boundary.

The ordinary resume condition must allow `args.max_resumes is None` or `resumes < args.max_resumes`. Use monotonic time for the initial deadline and every clear, reeffort, and ordinary-resume check/timeout. The stash stage-3 version uses wall-clock deadline operations, which must not be reintroduced.

## Minimal missing cases and risks

1. **Unlimited default with schedule:** schedule runs should accept omitted `--timeout`/`--max-resumes`; no `None` comparison, `str(None)` CLI forwarding, or finite-default regression. Run resume forwarding must omit unspecified limits.
2. **Bounded ordinary resumes with effort boundaries:** with an explicit resume budget, boundaries must continue without spending it; actual host-ended resumes must spend it. A resumed Grok effort boundary must use reported or planned session ID. Keep stage-2 stalled-revision stopping active in the combined loop.
3. **Monotonic deadlines:** `run.py` and `slice.py` should use a consistent monotonic deadline across initial launch, user interruption, effort restart, and ordinary resume; use infinity when no timeout was specified.
4. **Slice boundary continuation:** the current captured `slice.py` recognizes `reeffort` but does not act on it in the outer driver. The schedule can be recorded while the stage slice terminates at its first class transition.
5. **Schedule evidence:** invocation/result identity effort is class D; individual launches and restarts record their actual effort. Preserve `effort.json` and session log semantics through resume/regrade.

## Relevant files and narrow verification

- `test/shiploop_e2e/effort.py`: schedule parser, class detection, planner boundary/launch records, and restart note.
- `test/shiploop_e2e/sessionlog.py`: shared launch record includes effort.
- `test/shiploop-e2e.test.py`: effort path around `EffortScheduleThroughMainTest` (~3663), run deadline/no-progress (~853, ~3818–3855), and CLI defaults/resume flags (~5583+).
- `test/shiploop-e2e-slice.test.py`: `EffortScheduleTests` (~1094), `EffortSliceTests` (~1376), plus clear/resume coverage.

After resolution, the narrow checks are:

```sh
python3 -B -m py_compile test/shiploop_e2e/run.py test/shiploop_e2e/slice.py test/shiploop_e2e/effort.py
python3 -B test/shiploop-e2e.test.py
python3 -B test/shiploop-e2e-slice.test.py
```
