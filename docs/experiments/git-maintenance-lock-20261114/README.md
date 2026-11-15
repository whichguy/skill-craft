# git's detached auto-maintenance and `objects/maintenance.lock` (2026-11-14)

**Question.** Why did `full / shiploop-2` fail on the release commit `9710190f` (run 43669277848, job 132675527691), and does
`-c maintenance.auto=false` on the fixture commit remove the cause?

**Where the result is read.** `docs/local-validation-journal.md`, Round 5 (F21 and F22). This folder holds the evidence it cites.

| File | What it is |
| --- | --- |
| `ci-failure-excerpt.txt` | The failing test's traceback from the job log, timestamps kept. |
| `ci-attempt2-failure-excerpt.txt` | The rerun (attempt 2) of the failed job on the same commit: the Grok-chat suite passed, and the shard failed on a different suite (`shiploop-e2e-ticket-comments`). |
| `lockprobe.py` | After `git commit --allow-empty` returns, how often `.git/objects/maintenance.lock` is still there (fresh repo, with and without the flag). |
| `trace2probe.py` | How many `git maintenance run --auto --quiet --detach` child launches Trace2 records over fixture-shaped commits, with and without the flag. |
| `globalconfigprobe.py` | Whether the CI step `git config --global maintenance.auto false` stops the detached launch for a fixture commit, made directly and by a child that `run_process` starts. |
| `envroute_probe.py` | What the runner-environment route would do: the three suites that commit `78594ebb` protected, run through `run_process` with the `GIT_CONFIG_*` variables stripped (as now) and reaching the suite (as proposed). |
| `results.txt` | What the probes and the other local checks printed, with the commands, on git 2.54.0 (Apple Git-157). |

Run the probes from any directory (each makes its own temporary repositories under the directory you name):

```sh
python3 -I docs/experiments/git-maintenance-lock-20261114/lockprobe.py 300 <scratch dir>
python3 -I docs/experiments/git-maintenance-lock-20261114/trace2probe.py <scratch dir> 40
python3 -I docs/experiments/git-maintenance-lock-20261114/globalconfigprobe.py <checkout> <scratch dir> 40
python3 -I docs/experiments/git-maintenance-lock-20261114/envroute_probe.py <checkout> <output dir>
```

`envroute_probe.py` runs three suites, one of them for about four minutes, and it needs the checkout it is given (it imports its `test/run_suites.py`).

The lock is a timing window, so `lockprobe.py` finding none says only that this machine's git closes it before the next
command can look. `trace2probe.py` is the deterministic measurement: whether the launch happens at all.
