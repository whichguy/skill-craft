# ShipLoop refusals and the callback contract: journal

Append-only. A claim that is later wrong is marked superseded with the date and the reason, never deleted. Evidence lives in the repo:
`docs/experiments/shiploop-refusals-20261004/refusals.json` (the 18 failed commands of two Luna runs, replies verbatim) and the test
`test/shiploop-callback-contract.test.py`. This is a topic journal on purpose: `test/shiploop_e2e/LEARNINGS.md` is the E2E session's journal
and was being edited on `main` when this was written, so appending there would conflict. Its earlier note on the 1.16.0 Luna refusals is the
"Batch 1003 - Luna max battleship final result" entry; this entry adds to its line "the model corrected it": it did, but the two
corrections took two refusals and a search of the scripts (finding 4).

## 2026-10-04: why the model hit refusals and what the script now says

Owner request. Investigate the ShipLoop refusals of the Luna 1.16.1 battleship run and fix them by changing the scripts' own language in two
places: the instruction the script prints about what to return, and the reply it gives when it refuses. No prose in SKILL.md or reference docs.
The script states the rule; the refusal gives the exact way out. Follow-up instruction the same day: every packet should say plainly how to
call back and in what shape.

### Question and method

Which of the 13 failed ShipLoop commands of `v1161-battleship-luna` (skill-craft 1.16.1, codex gpt-6-luna, max effort, blocked at system-test after
19.3 h) are refusals, what had the script told the model before each, did the refusal give an exact way out, and did the model recover on the
next call? Read: the run's `events.jsonl` (66 MB, 3,545 tool calls; every ShipLoop command with a non-zero exit, its output, and the calls that
followed), the three Codex rollouts for what the model wrote (patches to the result files), the run's `packets/` and `inbox/`, and the 1.16.1
plugin cache the run used. The same read was repeated on the earlier Luna run `battleship-luna` (1.16.0), whose 5 refusals are the case the
owner's brief describes. The metric (`test/shiploop_e2e/metrics.py`, `collect`) counts any tool call whose command names a ShipLoop verb and
whose exit code is not 0, and stores the first output line matching `error|refus|reject|required|must|invalid` that is not a keepalive marker.

### Findings

Status words: firm (read in the run's own record), inferred (stated as inference), held (not changed, reason given).

1. **Firm. 13 failed commands in `v1161-battleship-luna`: 9 engine refusals and 4 mistyped paths.** The 4 paths (two argparse
   "unrecognized arguments", two "no ShipLoop run directory") exit 2 as a refusal does but no gate ran; each was repaired by the next call. They
   are the callback-typo finding of `docs/shiploop-callback-typos-plan-2026-10-04.md` (a space inserted after `20261003/`; a resumed session);
   nothing here changes that decision (defer the engine change, reopen on R1 or R2).
2. **Firm. The metric's stored `line` is the trailer for 8 of the 13** ("Read the current packet with next; the rejected request did not advance
   the graph."), because the trailer contains "rejected". The export therefore cannot say which refusal it was; the replies had to be read from
   the events. A harness fix (skip the two fixed trailer lines) is a one-line change in `metrics.py`, which is outside this change and the E2E
   session's file; recorded as a recommendation, not done.
3. **Firm. Three of the 9 refusals were one check, "result requires outcome and summary", and the reply named neither the missing field nor the
   wrapper.** Twice (step-plan, baseline) the model submitted the stored-record shape (`action`, `navigator_protocol_version`, `result`: the shape
   of the files under `results/` that the packet tells it to open under "Results this stage builds on"); once (system-test) a hand-built blocked
   result had no `summary`. After the first refusal the model made 15 tool calls (about two minutes, rows 1403 to 1418) reading the 1.16.1
   navigator source before it found the wrapper, then made the same mistake again 90 minutes later at baseline, after context compactions
   (the Codex rollouts show 15 compactions in the first session). Inference: it copied the wrapper from `results/*.md`, because it had parsed
   `d["result"]` of those files minutes before the first refusal. The script's reply is the only memory a run has across a compaction.
4. **Firm. The 1.16.0 run shows the sibling.** A blocked plan result still held the done template's `work_items` and `assumptions`; it was
   refused twice, one field per call ("work_items require done or replan", then "assumptions are allowed only on a done plan result"), and the
   model grepped the scripts for the first message between them. Both come from editing the one printed template (done) by hand.
5. **Firm. The opening heading refusal recurred in both Luna runs** ("opening needs non-empty sections: ## Environment"): the heading was written
   as "## Expected checks and environment" (1.16.1) and "## Environment and validation" (1.16.0). The reply did not say it was a renamed heading.
6. **Firm, held. The contract-size refusal (3 of 9) gives the overage, the section sizes and a stated allowance.** Two of the three recovered at
   once; one needed a second try (12,478 to 10,005 bytes, still 789 over). Inference: the model measured the file in bytes while the contract
   counts JSON-escaped text (a newline costs 2 bytes). The stated allowance ("about 4,686 bytes in all") is about 1,165 bytes below what the
   refusal's own arithmetic implies (sections 9,113 bytes, contract 12,478, over by 3,262, so about 5,851 allowed); unverified, because
   `improve_opening_allowance` sits beside `improve_start_contract`, which the E2E session is editing. Not changed.
7. **Firm. Two refusals were the gate working with an exact way out:** `evidence_refs` citing a file that does not exist (write it or remove the
   reference; recovered in 4 calls), and a wait without `no_default` (S-14; it names `awaiting.no_default`, but the model had put `no_default`
   beside `awaiting`; the run then ended blocked at system-test on two person-only browser cases, which release 1.20.0's a13 change addresses in
   the packet text).
8. **Found by the route test, not by a run. The refusal for a loop that never ran named a dead end.** At test-green, regression and static-checks
   a done result before the Until Loop ran was told to cite the loop's terminal packet, a file that does not exist; citing it was refused again.
   The command that creates it is printed only in the full packet. No recorded run hit it; labelled as a defect found by the test.

### What changed (commits on branch rrr-edc892, all local)

| Commit | What | Where |
|---|---|---|
| d412a45d | refusal replies name the correction: wrapper, missing field, done-only fields on another outcome (all named at once), unsupported fields, awaiting without `no_default` (beside or absent, with `AWAITING_SHAPE`), renamed opening heading | `shiploop_navigator.py`: `_result_shape_problem`, `_canonical_result`, `_check_submitted_awaiting`, `_opening_sections` |
| f14f90c7 | packet head prints the exact shape of every outcome the stage allows, and that the block holds the result itself; release-plan template carries `consumer_entry`; the improve-start line names the four opening headings | `_outcome_shape_lines`, `_result_contract_lines`, `_result_template`, `_first_callback_lines` |
| c2d8d78a | the refusal for a loop that never ran names the start command (one definition shared with the packet) | `shiploop_quality.py`: `start_command`, `check_loop_packet`; `shiploop_test_loop.py` |
| ba019cf5 | route tests: every stage walked through the real CLI, every printed outcome shape accepted | `test/shiploop-callback-contract.test.py` |
| 556f428f | the shape refusals keep "result requires outcome and summary" as their lead (the e2e-audit apparatus oracle `dag_replay.py` pins it; found by the targeted selection, not by the focused suites); the lint test's blocked case follows the new reply | `_result_shape_problem`; `test/shiploop-lint.test.py` |
| 307b508b | the assumptions test follows the reply for a repeat result carrying `assumptions` | `test/shiploop-assumptions.test.py` |

Rule and remedy are defined once where both are printed: `AWAITING_SHAPE`, `BLOCKED_BY` and `OPENING_SECTIONS` are used by the packet and by the
refusals, `quality.start_command` by the packet and the loop refusal. No gate was loosened and no verb added.

Held, with the reason: `shiploop_prompts.py` (the E2E session's planning text) was not edited; nothing here needed it. The contract-size
allowance (finding 6); the two audited packet gaps with no recorded failure (Backchain's `backchain-check` line only in the full packet at plan,
and an already-started Improve child's recovery only in the full packet; the second has an exact refusal).

### Tests

`test/shiploop-callback-contract.test.py`, 18 tests, real CLI. Each refusal test derives the correction from the refusal's own text (the keys to
delete, the fields named, the heading to rename), submits the same printed command again and requires acceptance. Each fails on a git archive of
the base `c2c4b63e`. The two table tests walk all 34 stages: the first follows only printed commands, filling each printed template with minimum
content and following the exits the refusals name (knowledge files at prepare, test-spec, release-plan, release-verify; the loop at test-green,
regression, static-checks); the second submits every printed outcome shape (86 stage and outcome pairs). Pinned existing text, updated deliberately: the
quality test's expectation for a done with no loop; the lint test's blocked case (556f428f); the suite counts in `test/test-groups.test.py`
(66 to 67 and 106 to 107). The apparatus oracle in `skills/shiploop-e2e-audit` was left alone by keeping the old lead phrase.

Targeted selection, `bash test/run-all.sh --group quick --changed-from c2c4b63e` at 556f428f: 28 of 28 suites passed (exit 0), including
shiploop-mock-replay (35 tests), shiploop-lint (81), shiploop-keepalive (57), shiploop-actual-improve-cli (32), shiploop-callback-contract (18).
Its first run (before 556f428f) failed shiploop-lint and shiploop-mock-replay, which is how the two pins were found. A hand-run batch of
packet-consuming suites found a third (307b508b: `test/shiploop-assumptions.test.py` expected the old per-field sentence for a repeat result).
After it, all three ShipLoop shards pass on this tree (`--group shiploop-1`, `-2`, `-3`: 1, 32 and 34 suites, exit 0), so no other test pins a
reply these commits changed. The file-name selection missed two pins; the full shard run is what closed it.

### Not established

- Whether the next Luna run hits fewer refusals. This change is a prediction until a run shows it: the three `result requires outcome and
  summary` refusals and the two done-field refusals should not recur, the renamed-heading refusal should be rarer, and a model that does hit
  one should recover on the next call. Only a live run can confirm it (batch discipline: no run was started here).
- Why the model wraps its result. Inference only (finding 3).
- The cause of the path typos (session age against run name); see the callback-typos plan.
- `shiploop-status-display` fails one test, `test_packet_carries_block_early_and_status_file_matches_cli`, on the base archive as well as on
  this branch (progress files appear in the run directory); it is not touched by this change and was not investigated.

Related: 6a59012c (a refusal's named route must be one the gate accepts), 7aff70aa (release 1.20.0), c895d921, c7ee64ba (a13),
`docs/shiploop-callback-typos-plan-2026-10-04.md`.
