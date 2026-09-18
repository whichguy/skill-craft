# Observational runnable samples

These are byte-preserved public source, helper, test, runner, and `SPEC.md`
assets from six original local trials and one audited follow-up. They are
observational records, not a repository-wide CI contract: `trial-03`,
`trial-05`, `trial-06`, and `red-followup` deliberately return a nonzero code
from the full suite because they retain valid RED behavior. Do not change their
production modules merely to make this directory green.

Each sample is self-contained. From a sample directory, use:

```sh
python3 -B run_tests.py --list
python3 -B run_tests.py --suite focused
python3 -B run_tests.py --suite smoke
python3 -B run_tests.py --suite full
```

The final command has the expected outcome below. The manifest binds every
retained file to its source locator and SHA-256. It deliberately omits Git
state, private runtime state, prompts, prior-run notes, guidance, raw logs,
and `TESTING.md` files that can contain private paths.

| Sample | Full tests | Expected full result | Original Improve outcome |
| --- | ---: | --- | --- |
| `trial-01` | 9 | green, exit 0 | baseline: done, cycle 2 |
| `trial-02` | 12 | green, exit 0 | candidate: paused, cycle 0; scoped commit blocked |
| `trial-03` | 13 | valid RED, exit 1: SQLite overflows at `2**63` under the unbounded public contract | candidate: paused, cycle 1; scoped commit blocked |
| `trial-04` | 11 | green, exit 0 | baseline: done, cycle 2 |
| `trial-05` | 8 | expected RED, exit 1 | baseline: done, cycle 2 |
| `trial-06` | 10 | expected RED, exit 1 | candidate: paused, cycle 0; scoped commit blocked |
| `red-followup` | 14 | expected RED, exit 1 with 68 product subtest failures | audited no-commit follow-up: done, cycle 3; original 10 IDs retained plus four runner regressions |

`trial-03` remains a valid RED and a reference-calibration gap; its original
blocked Improve outcome is preserved. `red-followup` passed all 14 tests against
an independent conforming reference while the checked-in production remains
intentionally RED.

For the observed campaign interpretation, see [RESULTS.md](../RESULTS.md),
[local originals](../observations/local-originals.json), and the [semantic
audit](../observations/local-semantic-audit.md). The retained samples do not
include the private records behind those summaries.
