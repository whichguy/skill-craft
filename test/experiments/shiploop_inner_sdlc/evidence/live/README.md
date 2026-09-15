# Live pilot evidence

Archived after all workers stopped. `{TRIAL}` and `{SOURCE}` replace temporary
and source-worktree roots in prose, packets, results and diffs. These are
non-executable archival packets; do not submit their callbacks to a live run.
Action and commit identities are original. Earlier state transitions are
explicitly synthetic; `summary.json` separates them from the one real callback.

`before.json`, `reference.json`, and `after.json` are the reserved oracle results
against the seed, external calibration reference, and actual worker candidate.
The preserved `calibration-original.json` contains a redundant `after` alias
that meant the reference score. It is not a worker result. New preparation
outputs have removed that alias; no expected outcome changed.

Each `final/` contains the final fixture contents. Python files have an extra
`.txt` suffix to avoid accidental source-repository test discovery. To rerun,
copy one final directory to a scratch folder, remove only the `.txt` suffix
from its `*.py.txt` files, and run `python3 -B -m unittest discover -v` there.
Behavior can also be checked with the independent oracle, although its Git
observations require the original seed baseline (see `prepare.py`).

Unit logs here are independent post-run checks. Worker evidence and review
notes preserve their own reported pre-fix observations and convergence history;
they are not raw transcripts of every command. Semantic criteria are assessed
from that evidence plus actual code, tests, diffs, oracle and state inspection.
No runtime controller uses this archive or its grading.

`candidate-diff.json` preserves each exact unified diff as a JSON string so
blank context lines do not become whitespace errors in the enclosing Git diff.
