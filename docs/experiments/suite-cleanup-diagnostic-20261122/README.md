# The "suite cleanup" line in the push check (2026-11-22)

Evidence for round 7 of `docs/local-validation-journal.md` (F27 to F30): what makes `test/test-groups.test.py` print
`suite cleanup: failure or uncertainty during bounded cleanup` now and then, how often, and whether a real suite run was
ever failed by the record behind it. The journal has the question, the results and the findings; this file says what each
script does and how to run it again.

Conditions: macOS (Darwin 27.2.0), Python 3.15.1, load average 5 to 8 from other sessions' work. Nothing here was run on Linux.

## Scripts

- `double_kill.py REPO TRIALS [DELAY_SECONDS]`. Each trial starts a leader and a child that both ignore SIGTERM, in a new
  session, with the runner's own process class (`run_suites._SuiteProcess` of `REPO/test`). It calls
  `_signal_group(SIGKILL)` twice, `DELAY_SECONDS` apart, and records what the exit probe and `killpg` answered the second
  time and whether the runner recorded a warning. Then it lets the runner reap the leader and records that too. It prints
  one line per distinct outcome, with its count and a first example. It changes nothing in `REPO`.

  ```sh
  python3 -B docs/experiments/suite-cleanup-diagnostic-20261122/double_kill.py "$PWD" 1000
  python3 -B docs/experiments/suite-cleanup-diagnostic-20261122/double_kill.py "$PWD" 250 0.0001
  ```

- `run_test41.sh REPO N OUT`. Runs the one test
  `SuiteGroupOwnershipTest.test_timeout_grace_interrupt_finishes_owned_group_before_escape` `N` times from `REPO`, writes
  one line per run to `OUT` (exit code, and whether the line was printed) and a last line with the counts. The first run
  that prints the line is kept whole in `OUT.first`. A run takes about 1.3 s.

  ```sh
  bash docs/experiments/suite-cleanup-diagnostic-20261122/run_test41.sh "$PWD" 150 /path/outside/the/checkout/out.txt
  ```

- `stop_named.py LISTING.json` (added the same evening, for the update at the end of round 7). Stops exactly the
  processes a listing names, each only if it is, at that moment, the process the listing describes: process id, start
  time, working folder, command, an optional text of its command line, no parent, no children. It is a copy of
  `docs/experiments/sdlc-structure-20261119/stop_named.py` with the expected command taken from the listing. It was used
  once, at the owner's word, on the five workers of F30. Do not run it on anything the owner has not named.

## Results (`results/`)

| file | what it holds |
| --- | --- |
| `double-kill.txt` | the nine runs of `double_kill.py` on the runner as it was: 1,000 trials back to back, then 250 at each of 20, 50, 100, 200 and 500 microseconds and 1, 2 and 5 ms |
| `test41-before.txt` | `run_test41.sh`, 150 runs on the runner as it was: 19 printed the line, 150 passed; the first run that printed it |
| `fail-first.txt` | the test with its new assertion on the runner as it was: 5 of 5 runs fail on that assertion |
| `test41-after.txt` | `run_test41.sh`, 150 runs with the runner changed: 0 printed the line, 150 passed |
| `test-groups-after.txt` | the whole of `test/test-groups.test.py` with the change: 78 tests, OK |
| `lint.txt` | `ruff` on the two changed files before and after (the same 92 findings), `ruff` and `shellcheck` on the two scripts |
| `record-search.txt` | the search of the Claude and Codex session records for a real run that printed the runner's record, and the one run that did |
| `stop-named-trial.txt` | `stop_named.py` tried on four throwaway processes: one described rightly is stopped, three described wrongly are left alone |
| `leftover-workers-stopped.txt` | the stop of the five workers of F30 at the owner's word: the listing, the checks before, the script's whole output, the checks after |

How to read a line of `double-kill.txt`: the count, then the second kill (`probe=` what the exit probe said just before
it, `killpg=` whether the kill was accepted or refused), then `WARNING` or `quiet` for what the runner recorded, then the
same for the reap that followed, then the first example (`group_states_after_second` is what `ps` showed for the group right
after a warned trial).

## Who did what

The main session designed the measurements and the change, wrote the two scripts as first run, read the results and
wrote the journal entry. An Opus worker made the change to `test/run_suites.py` and to the test, ran the fail-first check,
the 150 runs after and the lint, and made the two scripts lint-clean (four edits to `double_kill.py` that do not change
what it measures or prints; run again after them, 40 trials at 100 microseconds, it gave 40 warned of 40, as the 250 of
250 before). A read-only Opus agent read the two Codex records
and the log of the 2026-11-18 run for `record-search.txt`; its counts were checked against that log.
