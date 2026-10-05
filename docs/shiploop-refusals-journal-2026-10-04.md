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
   session's file; recorded as a recommendation, not done. **Done 2026-10-05** (63d4f50a; see the entry below).
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
   **Superseded 2026-10-05: the allowance was right; the comparison was not.** The 1.16.1 refusal listed whole contract fields
   (`context.request`, `scope`, `authority` carry ShipLoop's own wrapper text), not the sections' own bytes, so the 1,165-byte gap was that
   text. 112b239c (released in 1.21.0) already lists each section's own escaped bytes. See the entry below.
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


## 2026-10-05: four fixes the owner asked for ("fix all now")

Owner request. Fix the four open items of the entry above in the scripts' own language and the harness: the `check` suite defined where
system commands are recorded, the refusal for an uncounted command, the suspected contract allowance error, and the metric that recorded
a trailer instead of the refusal. Rules: no prose in SKILL.md or references, the refusal states the exact way out, a refusal's named exit is
submitted through the real gate in its test, the gate does not weaken, one commit per fix, harness-only changes need no change note. Base
`1411d5f1` (release 1.21.0, shiploop 0.53.0). Nothing was pushed, released or run; real runs under `/Users/dadleet/e2e-runs` were only read.

### Findings and what changed

| Commit | Fix | SPEC | Where |
|---|---|---|---|
| 9a8727f7 | `DUTIES['system-test-author']` defines the suite `check` (a command that is not a test runner, judged by its exit code) and what `focused` and `regression` need (a runner whose output ShipLoop can count) | S-2, S-6, S-8, S-9 | `shiploop_prompts.py`; note `system-test-author-defines-check` |
| 22fbba28 | the `uncounted` refusal names the exit the running stage has: at system-test and release-verify (commands recorded by system-test-author and release-plan), `replan` now with one corrective item that records the command as suite `check`; elsewhere ids and a runner flag, or `check` | S-2, S-6, S-9 | `shiploop_test_loop.py`: `_explain(run, stage)`, `verify`; note `uncounted-command-names-the-exit-its-stage-has` |
| bc67846c | the oversize-opening refusal says how its sizes and its room are counted (escaped like JSON); the allowance itself was right | S-6 | `shiploop_loop_contract.py`: `size_problem`; note `oversize-opening-says-how-its-room-is-counted` |
| 63d4f50a | the metric records a refusal by its own line, not by the trailer after it (harness only, no note) | S-9 (the evidence must name the refusal) | `test/shiploop_e2e/metrics.py`: `failure_line`, `REFUSAL_LINE`, `TRAILER_LINE` |

1. **Firm. The `uncounted` dead end cost one 1.19.0 run 73% of its extra cost.** In `v1190-hello-sonnet-2` (events.jsonl rows 360-361)
   system-test-author recorded a shell pipeline as suite `focused`; system-test refused it ("exited 0, but ShipLoop could not read how many tests
   it ran. Give the command ids and a runner flag ..."). The stage cannot edit a command another stage recorded, and the result field that
   records commands is accepted only from its owner, so the only exit was a replan (about 24 calls, $1.44 of the run's $1.96 extra cost;
   `test/shiploop_e2e/LEARNINGS.md`, which said to wait for a recurrence). Two defects, one cause each: the recording stage never said what
   `check` is (9a8727f7), and the refusal named an exit that did not exist at that stage and a code fix that could not help (22fbba28). The
   closing "Refused runs ...; after that ... (replan)" also made the exit look seven refusals away, although a replan is accepted at once: the
   new test submits it after the first refusal and the gate accepts it.
2. **Firm. The reply at system-test now reads:** "exited 0, but ShipLoop could not read how many tests it ran. system-test-author recorded this
   command and system-test cannot edit it. A command that is not a test runner (a shell pipeline, a grep, a probe) belongs in suite `check`,
   judged by its exit code. Report outcome replan now, with one corrective work item: a new id, a title, and a context that names this command
   and says to record it as suite check in system_commands. The outer stages then run again, and system-test-author records it." When every
   failing command is uncounted the closing line is "Report replan as named above, not done: no change to the code makes a recorded command
   countable. Refused runs for this action: N of 7; replan does not wait for them." A counted failure beside an uncounted command keeps "Fix the
   code so every command passes". At release-verify the recorder is release-plan and the field `consumer_checks`.
3. **Firm. The contract allowance was never wrong (finding 6 above is superseded).** Reproduced with a scratch run at HEAD: Luna-sized sections
   (2,993 + 891 + 1,057 + 4,172 = 9,113 bytes) give a 13,421-byte contract, 4,205 over its 9,216-byte budget; the listed sizes less the overage are
   4,908 and the stated allowance is 4,904, the four placeholder bytes of the minimal contract it is measured from. Sections totalling the
   allowance fit (9,212 bytes); the room ends 4 bytes above it (9,216 fits, 9,217 is refused). On 1.16.1 the refusal listed whole contract
   fields, so the numbers measured different things: the wrapper text in `request`, `scope` and `authority` is 1,087 bytes in the scratch run
   (short paths; the Luna paths were longer) and 1,161 to 1,165 as implied by Luna's three refusals (rows 661, 673, 4442 of
   `v1161-battleship-luna`). 112b239c, released in 1.21.0, already lists each section's own escaped bytes. What remained is a clause: the
   sentence now ends "counted as above: escaped like JSON, so a newline or a quote costs 2 bytes and a non-ASCII character 6, and a file's
   byte size undercounts it". Status: the clause is **inferred** to help (the second Luna try, 12,478 to 10,005, was still 789 over, which is
   what raw file bytes against escaped bytes would produce); no run shows it yet.
4. **Firm. The metric's `line` was the trailer for 8 of 13 because the refusal's own line has none of its words.** 14 of the 14 engine
   refusals of `docs/experiments/shiploop-refusals-20261004/refusals.json` begin "ShipLoop navigator: " and none matches
   `error|refus|reject|required|must|invalid` ("requires" is not "required"); only the 4 mistyped-path errors do. The skip list is pinned to the
   text of `shiploop_protocol.py` by a test, so a reworded trailer fails a test and does not hide the refusal again. No committed evidence was
   regenerated: earlier exports keep the line they had.

### Tests

Each was run against a git archive of the tip before its commit, with only the test files copied in.

- 9a8727f7: `test/shiploop-guidance.test.py::test_the_system_test_author_defines_check_and_says_what_focused_needs`; fails on the base, passes after.
  Guidance 38 tests OK (37 before), packet-bounds 8 OK, delegation 47 OK: no bound had to be raised.
- 22fbba28: `UncountedCommandRouteTests`, 6 tests through the real CLI (the refusal names replan and check; the exit is read from the reply, built
  into the packet's printed replan shape with one new-id item and accepted; the same pipeline as done, also sent with `system_commands`, is
  refused again; a pipeline recorded as a check and a counted focused command pass; a counted failure keeps its own reply; the step plan's
  stage keeps ids and a flag and adds check) and `test_an_uncounted_command_names_the_exit_its_stage_has` in `shiploop-test-loop` (both outer
  stages, three other stages, the mixed case). On the base 4 of the 6 route tests and the unit test fail; the other two (counted success,
  counted failure) are invariance guards and pass on both. callback-contract 24 tests OK (18 before), test-loop 45 OK (44 before).
- bc67846c: `OpeningAllowanceTests`, 1 test through the real CLI. Its arithmetic and boundary assertions pass on the base too (the allowance was
  right); the clause assertion fails there. callback-contract 25 OK, shiploop-actual-improve-cli 32 OK.
- 63d4f50a: three tests in `MetricsTest` (`test/shiploop-e2e.test.py`); two fail on the base, the "what it did before" guard passes on both. The
  whole file: 224 tests OK (about 6 minutes).
- `bash test/run-all.sh --group quick --changed-from origin/main`: 31 of 31 suites OK, exit 0. `scripts/check-release-boundary.py --base
  origin/main`: OK (three new notes).

### Known limits and held items (nothing here broke a normal run; each is a decision, not a defect found by a run)

- **The same dead end exists at the INNER stages.** The step plan recorded their commands and test-red, test-green, regression and the rerun
  stages cannot edit them either; their reply keeps ids and a runner flag and gains only the `check` alternative, as asked. Their exit is
  `revise`: the test gate does not hold it at test-red and the rerun stages (`_test_red_gate` and `_test_rerun_gate` act only on `done`), but at
  the loop stages it needs the loop's stopped packet or `MAX_REFUSED_RUNS` refused runs (`check_terminal`, `remedy_open`). Extending the system-test sentence to them with `revise` is the next
  step if a run shows it.
- **`ids-missing`, `no-tests` and `too-few-tests` at the outer stages** say "make the command select ..." about a command that stage cannot
  edit; for them a code or setup fix can be the answer, so they were left alone.
- **The packet text beside the commands** (`COUNT_RULE`, printed by `rerun_lines` at system-test and release-verify) still says a focused command
  "needs ids and a runner flag"; the refusal now gives the stage's real exit, so it was not touched.
- **`DUTIES['release-plan']`** says only "a `check` command is judged by its exit code" and does not say what belongs in `check`; a pipeline
  recorded there as `focused` would hit the same refusal at release-verify, which now names the exit. One sentence, the same pin, if wanted.
- **A better exit would be a graph change:** let system-test return to system-test-author without a corrective work item, which would avoid the
  select-work, step-plan and implement detour a replan takes. Not attempted: it changes the graph, and the owner's rule is scripts' language first.

### Not established

- That the clause in the allowance sentence prevents the second oversize refusal, and that the new replan sentence is followed at the first
  attempt: only a live run shows either (no run was started).
- That the model puts the corrective item's context into the next system-test-author record: the packet for that stage now carries the `check`
  definition (9a8727f7), which is the other half of the route.

Related: 112b239c (the listing fix), 9a8727f7, 22fbba28, bc67846c, 63d4f50a, 1411d5f1 (release 1.21.0), 7aff70aa, c895d921, and on this branch
dc3ce69a, 541ed116, afab1d5c, e8a26f58, 30eeb187, e0ce12a9 (the work this continues).
