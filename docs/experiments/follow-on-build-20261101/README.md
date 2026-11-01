# Follow-on list: the live round of the build (2026-11-01)

Consumer: the owner, who asked for the build, and the release preflight (a ShipLoop change needs an E2E round after it). Later: the
session that measures the list on the owner's own features (design M3) or builds the chain (design 4.7).

Status words as in the journal: firm (read from the run folders), exploratory (four runs, one reader).

Journal: [Round 5](../../shiploop-follow-on-run-journal.md). Design: [the follow-on design note](../../shiploop-follow-on-run-design-2026-10-31.md).

## What was tested

The feature commit `826c951ccfdecb8f48e406f8fbdacb6a69daabbc` (the handoff's `follow_on` list, its gate, the request file, the
report section and the done-packet lines), on origin/main `d06e18a56ee43db8d04dc872e680d4efdd33f076` (skill-craft 2.28.1,
ShipLoop 1.27.0). The runs started from `2da2d4f3d11b0f468c14ff48e6158a7bb334e8ee`, the plan commit above it (journal Round 5,
committed before any run), whose skill files are the feature's. Every run loaded plugin tree `bf3be9d89072`
(`plugin_sha256` in the four baseline rows). The tree that will be released also holds `ba3297d707329a6500ac036577d3f211b2e6a352`
(one `except` clause in `source_repo`, for a workspace record that is missing, which a real isolated run always has), test-only
commits and the focused-ID step-plan rule of 2.29.0 (b8d320335c81151a99e7d168b684d79fd0e81352, 4515368495e2b2e50ea07f7599146875188449f9, released in 4224161b095792825befe2a384075fab5660ae05); the four runs did not run those (corrected 2026-11-01, Round 8: the rule was missing from this list).

## Runs

`python3 test/shiploop_e2e/run.py --case <case> --host codex --model gpt-6.1-terra --effort xhigh --source checkout --timeout 5400
--output <folder>`, four at once, planning review `stage`, output under `/Users/dadleet/e2e-runs/2026-11-01/follow-on-live-436258/`
(outside the repository). The machine was busy with other sessions' work (load 51 at the start and 60 to 87 at the ends, on 18 CPUs; each
run overlapped five others: its three siblings and two of another session's calibration runs); durations are not comparable with the saved
baselines'.

| Run | Verdicts | Turns | Minutes | ShipLoop command failures | Handoff `complete` attempts (exit) | `follow_on` | Handoff packet, characters (whole / printed) |
|---|---|---|---|---|---|---|---|
| hello-1 | all pass (2 of 2 checks) | 143 | 12.4 | 0 | 1 (0) | `[]` | 20,653 / 16,850 |
| csv-report-1 | all pass (5 of 5) | 178 | 17.5 | 0 | 1 (0) | 1 note | 20,762 / 17,068 |
| csv-report-2 | all pass (5 of 5) | 185 | 18.9 | 1 | 1 (0) | 1 note | 20,855 / 17,101 |
| seat-reservations-1 | all pass (4 of 4) | 216 | 20.0 | 5 | 1 (0) | `[]` | 21,245 / 17,462 |

The ShipLoop command failures are `shiploop check` refusals at earlier stages (a step proof written over several lines, a test command's
IDs, an open plan assumption due at the item, surviving mutants); none is at the handoff and none names `follow_on`.

## The rules of the plan, scored

- R1, the gate holds: yes. All four runs reached `done` with every verdict passing (invoked, plugin, process, shiploop, committed, checks).
- R2, first-try shape: yes. Every handoff was accepted on its first `complete` (4 attempts, 4 exits of 0), so 0 refusals naming
  `follow_on` per run against the limit of a mean of 1 and none above 3.
- R3, support: yes, n = 2. Both entries are supported by the record they cite (below).
- R4, no inflation, no silence: entries per run 0, 1, 1, 0. One flag: seat-reservations-1 filed `[]` while its release-verify
  `lessons.open_next` reads "None for this request; revalidate transaction and tests if schema or deployment environment changes." and
  its considerations say the server listens on all interfaces and has no authentication. That is a revalidation condition, a `note` by the
  duty's own words ("knowledge for a later change; nothing is open"), so a flag and not a defect; the run's summary says "no follow-on is
  required". hello-1 (`open_next` "None.") has no flag.
- R5, the recommendation: not exercised. No run filed a `gap` or a `decision`, so no run wrote `follow-on-request.md` or printed the start
  command; that path is covered by the hermetic route tests and not yet by a live run.
- R6, size: the handoff head printed 16,850 to 17,462 characters, under the 20,000 cut. The same case in a saved Codex run on the
  published build (2026-11-01, `shiploop-hello-codex-floor-2c31ea`) printed 15,375 of 18,957: hello-1 is +1,475 printed and +1,696 whole.

## The predictions, scored

P1 (all four runs done with every verdict, 80%) held. P2 (mean refusals at most 1, none above 3, 65%) held. P3 (at least 3 of 4 file an
entry, hello none or one, 60%) missed: 2 of 4 filed one, and hello filed none. P4 (a csv-report run files a `decision` about numeric
forms or arguments, 40%) missed: neither did. P5 (no `gap`, 85%) held. P6 (at least 90% of entries supported, 70%) held, on 2 entries.
Four of six held.

## What the models wrote

Both csv-report runs filed the same `note` about plan assumption A2 (a default the request left open, which the run implemented):

| Run | class | source | statement | needs | cited record |
|---|---|---|---|---|---|
| csv-report-1 | note | `assumption:A2` | "Half-even aggregate rounding and first-record header behavior were implemented and verified." | "No action required; retain the stated default if extending the CLI." | A2, "Decimal half-even aggregate rounding and first CSV record as header", disposition `open`, reason "Request does not specify tie rule or malformed headers" |
| csv-report-2 | note | `assumption:A2` | "Input headers are assumed to be as specified; half-even tie handling is a documented default." | "A future change would define different header or rounding policy if desired." | A2, "Decimal ties use half-even and specified headers are present", disposition `open`, reason "Request does not specify tie rule or malformed header behavior" |

The ledger never updates a disposition, so A2 still reads `open` in both runs' records; the `note` is where the run says the default
stands. hello-1 and seat-reservations-1 had the same kind of open A2 and did not file it: their handoff summaries say a passing test
settled it ("its stated check was performed and passed"; "resolved by test_invalid_requests ... and test_encoded_ids_and_large_values").
The replay's `decision` rows for csv-report (design Round 4) did not recur: both runs took the default and recorded it, which is the
unattended behaviour SPEC S-14 asks for, so the list shows what the model chose to call a leftover and not what a reader might.

## What this does and does not show

It shows that the mechanics hold on a real model: the template and the duty were enough for four first-try acceptances, the cited
sources were real, the two entries were supported, the packet fits, and nothing about the handoff cost a refusal. It does not show that
the list finds leftovers a person would want. The four requests are small and fully specified, so little was left over, and no run
recommended a follow-on run. Not measured: any recommended run live (the request file, the start command from a model-written list,
intake's handling of a request that quotes findings, design U2); agreement between readers entry by entry (U11); the owner's own
features; the Claude and Grok hosts; efforts other than xhigh; the port-lease cases (`user-listing`, `ticket-*`); cost (Codex does not
report it). Four lists are an existence check, not a rate.

## Reproduce

```sh
python3 extract_follow_on.py <output folder> ... [--json]     # lists, handoff attempts, packet sizes, request file, report section
python3 read_records.py <output folder> ...                   # each entry beside the record its source names
```

Both only read. `runs.json` is the first one's `--json` output for the four runs, `readings.txt` the second one's output, and
`verdicts.txt` the verdict blocks of the four runner outputs (the full output and `result.json` stay in the run folders). The four
baseline rows the runs appended are in `test/shiploop_e2e/baselines.jsonl` (`local_head` `2da2d4f3d11b0f468c14ff48e6158a7bb334e8ee`).

## The published build (after the release)

After the release (skill-craft 2.30.0 and ShipLoop 1.29.0, release commit `41ee3d89d580fb715fc90994b2361348550698c7`) one more run used the marketplace
build instead of the checkout: `run.py --case hello --host codex --source marketplace --timeout 5400` (published plugin tree `3efc9db89059`, `local_head` the
release commit; Codex gpt-6.1-terra at xhigh). It passed every verdict, and its `versions` line names skill-craft 2.30.0 and ShipLoop 1.29.0. 199 turns,
14.9 minutes at a load of 150 to 189 on 18 CPUs. The handoff was accepted on its first `complete` with `follow_on: []`, and the report has the Follow-on
section ("none listed"). Its one ShipLoop command failure was a `shiploop check` at an Improve checkpoint that named a result path other than the current
generated one; none is at the handoff. This is the check of the exact released tree that the feature's live round (which ran the checkout) could not make.
Verdict lines: `published-hello-verdicts.txt`; the run's baseline row is in `test/shiploop_e2e/baselines.jsonl`. It is one hello run: it shows the published
build starts and finishes, and nothing about what the list finds.
