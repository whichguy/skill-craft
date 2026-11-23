# Is the Salesforce card's "refused as unread" still true? (2026-11-22)

Read on the canonical checkout at `472919dfcc81ec1933293f836d4c7ee8d54286d4` (main, clean under
`skills/shiploop/scripts`). No model called, no run started, the card not edited. The behaviour was checked by
feeding the current judge two real samples: `judge_formats_probe.py`, output `judge-formats-probe.txt`.

## The card's sentence

`skills/shiploop/references/platforms/salesforce.md`, `## Testing`:

> ShipLoop judges a focused Apex test from the runner's own pass or fail mark on the line that names it, so record
> the command with a reporter it can read: `sf apex run test ... --result-format tap` prints an `ok` or `not ok` line
> per test, while the default table and `--result-format human` put the outcome word after the test name, which
> ShipLoop does not read, so a focused command that uses them is refused as unread.

## What the code does today

**The command never reaches the judge that has an `unread` status.** `unread` exists only in `_judge_base`
(`shiploop_test_loop.py`), the test stage's base run: a focused command whose new test ID is named in the output but
on no line with a pass or fail mark (`shiploop_test_counts.outcomes` gives `shown`) gets status `unread`, which is
not in `BASE_GOOD` and so is refused. But before that, `_remote_base` asks `shiploop_mutation.remote_card` whether the
command contains a prefix some card lists under `## Remote tests`; the Salesforce card lists `sf apex run test`, so
the row becomes `remote` (in `BASE_GOOD`) and is not run on the base at all. Checked: for
`sf apex run test ... --result-format human` with two IDs, `_remote_base` returns `remote`; `_judge_base` on the human
sample would return `unread`, but is not called.

**The candidate run passes it.** `judge` (`shiploop_test_loop.py`) on a focused row:

1. `counts.count` reads no summary from the human table (`None`): none of `READERS`, `_tap` or pytest matches
   "Tests Ran 4". The tap sample is counted (`ran 4`, by `_tap`, the TAP reader added in `92b55c803`, 2026-11-15).
2. Exit not 0: `failed` (or `no-tests` when a count of 0 was read).
3. Exit 0, count `None`: `too-few-tests` and `no-tests` need a count, so they cannot apply. A listed ID not on any
   non-skip line as a whole word (`counts.named`): `ids-missing`, refused.
4. Every listed ID shown: the branch `elif tally is not None or ids` gives **`passed`**. The outcome word is never
   needed.
5. No IDs and no count: `uncounted`, refused ("ShipLoop could not read how many tests it ran", `_explain`); a
   regression row with no `ids` and no `min_tests` instead gets `passed-uncounted`.

So the exact conditions under which a human or default-format `sf apex run test` is refused today are: a non-zero
exit; a listed ID absent from the output; or (focused, or regression with `min_tests`) no IDs listed at all. The last
is the only refusal tied to the format, and it is about the count, not the outcome word: it applies to any runner
whose summary ShipLoop cannot read. One more refusal exists outside the test loop: prepare's `harness_runs` evidence
is refused when `count` reads no test from it (`check_harness_output` in `shiploop_test_layers.py`), which a saved
human-format Apex output would be.

**What the format does change: two guards go quiet.** With the human table, (a) a failure hidden behind exit 0 (a
wrapper that swallows the CLI's exit code) passes, because `outcomes` sees no failure mark and `count` no failed
tally; the same case in TAP is refused `failed` (probe, last line of each block); (b) no count is recorded, so the
count floor in `verify` (`run["counts"] and run["counts"]["ran"] < floor`) is skipped and a test removed from the
class but not named in `ids` goes unseen.

**What the saved runs show agrees.** Over the Apex test records of every saved run under `~/e2e-runs*` (my count
today): 137 focused human-format rows with IDs got `passed`, none `unread`; every row, TAP ones too, had
`counts: null`, which fits those runs (2026-10-24 to 11-05) predating the TAP reader; the records were judged by the
ShipLoop each run installed, not by today's code.

## Verdict

**False as written** for the case it names, a focused command with listed IDs (the way a step plan records one):
it is passed, not refused. True only in a narrower and different sense: a focused command **without IDs** is refused
for an unread count, whatever the runner. The card's advice (use `--result-format tap`) is still right, for reasons
it does not give: TAP keeps the masked-failure guard and the count floor, and is accepted as harness evidence.

**How it drifted.** The sentence came in `c700eb29aae866050bb6d83ab858de33f921e460` (2026-10-17), whose message says
the base run refused 11 shown-but-unmarked IDs as `unread` in a live chess run. That was true then. Seven days later
`e074ccd3bcbf081b0591588b9cdab244efe508aa` (2026-10-24) stopped running remote commands on the base, which removed the
only path to `unread`. The guarding test,
`test_the_salesforce_card_names_the_reporter_shiploop_reads_and_the_remote_test_route` in
`test/shiploop-guidance.test.py`, asserts the phrase `"refused as unread"` is in the card, and its docstring cites
`e074ccd3`. A test that pins a sentence's words keeps a stale sentence in place: it fails if the claim is corrected and
passes when the behaviour changes.

## What check would have caught it

A behaviour test for each claim a card makes about ShipLoop's own judging, run on fixtures instead of on words:
keep one saved sample of every output format the card names (`human`, the default, `tap`, `json`) and route each,
as a recorded step-plan row, through the same functions a run uses (`_remote_base`, then `_judge_base` or `judge`),
asserting the outcome the card states (`refused`, `passed`). `judge_formats_probe.py` is the core of such a test. It
would have failed on `e074ccd3`, at the commit that changed the behaviour, and named the card sentence to fix. A
cheaper partial guard: tag card sentences that state a ShipLoop verdict, and make changes to `judge`, `_judge_base`
or `_remote_base` list those tagged sentences for review.
