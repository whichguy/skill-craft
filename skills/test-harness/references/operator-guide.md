# How to read a test-harness run

Every run answers four questions.

Timeouts are deliberately two-layered. A monotonic process-group supervisor
encloses the complete lifecycle—from resolve/discovery through suite, audit,
report, worktree teardown, descendant cleanup, and supervisor exit—with a hard
maximum of 3,600 seconds. `--timeout-secs` selects an exact lower envelope;
`--full` defaults to a 3,600-second envelope. A default fast run uses a 1,200-second suite
budget beneath the one-hour failsafe. Five percent of the selected budget,
bounded to 1–60 seconds, is held back for finalization. Fix-loop rounds share
one real deadline and later rounds receive only the remaining seconds.
The worker consumes a supervisor-owned inherited pipe capability before it will
trust supervisor state, so ambient PID/deadline variables cannot skip wrapping.
`TEST_HARNESS_TIMEOUT` and `TEST_HARNESS_FULL_TIMEOUT` may lower their respective
budgets, but values above 3,600 fail before any workspace operation. A product
suite's own watchdogs are separate and cannot extend this boundary.

If a responsive suite exhausts its cooperative budget, the harness emits its
normal `STOPPED_TIMEOUT_BUDGET` evidence. If the audit, report, or teardown
itself hangs, the hard supervisor exits 124, kills the owned process group, and
writes `hard-timeout.json`; a missing chat-card in that emergency must not be
replaced with a hand-written result. That emergency file stores only the worker
executable basename and argument count, never the raw command or its arguments.
External INT, TERM, and HUP signals are
forwarded once through each owned supervisor boundary and receive cooperative
grace before escalation, so cancelling a nested participating suite reaps its
descendants. A deliberately unmanaged self-daemonizing session is not portable
process-group-owned and needs a suite-specific cleanup contract.

Restore behavior is ownership-aware. A once-mode run uses the caller's shared
working tree, so any failing round preserves every observed post state and
requires manual reconciliation; the harness cannot prove whether a write came
from the suite or concurrent WIP. Automatic reversion is limited to a
harness-owned disposable fix-loop worktree, uses worktree-only `git restore`,
and still preserves dirty-at-pre paths.

## 1. What was the final result?

- Greppable line: `test-harness RESULT=…`
- Chat-card **Final result** table + **Conclusion (supervisor)**
- HTML hero badge (green / amber / red)
- Supervisor also answers: *did the expected path hold, or are there unintended cues?*

## 2. What was attempted / unintended?

Chat-card and HTML **Supervisor** sections:

- **What was attempted** — command, case counts, suite header cues from stdout  
- **Unintended consequences** — blocking / suspicious / informational signals from
  stdout+stderr+FS+control (traceback, exceptions, live URLs on fast, loud stderr, …)  
- **Conclusion** — short supervisor verdict (`clean`, `pass_with_suspicion`, …)

Even on `PASS_CLEAN`, read **Unintended consequences** and **Struggles**:

- `TMPDIR_LEAK` — sandbox only, not repo dirt
- `stderr_noise_on_success` / `stderr_volume_on_success` — may hide real issues
- `IGNORED_WRITE` ambient `runs/` / `.worktrees` — notes by default
- Blocking items — product writes, failed cases, control forbids, non-zero suite exit

## 3. What ran and worked well?

- **What ran & was verified** (chat-card + HTML hero panel) — named cases, groups, verification claims  
- **Worked well (hygiene)** — exit 0, channel OK, material_delta=0 (not a substitute for the inventory)  
- Full case inventory + flat table in HTML / `results.md`  
- Control-channel evaluation (stdout/stderr status)  
- Module rollups (`PASS N … tests`) are filtered out of case counts

## 4. How do I dive in?

```bash
# $RUN_DIR/report.html            open this file in a browser (easiest)
less   $RUN_DIR/results.md       # full text
jq .   $RUN_DIR/report.json      # machine story + suite.cases
less   $RUN_DIR/round-1/stdout.log
less   $RUN_DIR/round-1/stderr.log
jq .   $RUN_DIR/round-1/side-effects.json
```

Agent should paste `chat-card.md` verbatim and mention the HTML path.
