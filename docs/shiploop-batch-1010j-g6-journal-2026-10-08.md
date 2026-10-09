# Batch 1010, worktree J, group G6: journal (the ids refusal A1 and the count floor A5)

Living journal for the two candidates of group G6 in the round-2 analysis (A1, the `ids-missing` refusal; A5, the per-item count
floor). Basis: `origin/main` b73c30ba (skill-craft 1.25.0, ShipLoop 0.57.0). Each candidate is one commit with its tests and its
section here. Evidence of this group: `docs/experiments/batch-1010j-g6-ids-floors-20261008/`. The audited design and its audit (the
audit's corrections override the design) are exported to `design-audit.json` there, and the two round-2 analysis entries they answer
(candidates A1 and A5) to `round2-candidates-a1-a5.json`; every correction that changed the build is named below. A first
adversarial review of the two commits (2026-10-08) found one major and eight minor points; each one's outcome is in the section it
concerns, under "Review of the commit" (the major one, evidence kept only in the scratchpad, is the exports named above).

Status words: firm (hermetic tests plus a recorded-run recomputation), interim, exploratory, superseded.

## A1: the ids refusal says why an ID that is printed is still not shown (2026-10-08)

**Question.** In the r2 Checkers run the test-author probe was refused twice with "did not show TC-4, TC-6, ... running. Make the
command select those cases and print test names (for example --verbose)", although `node --test` had already printed
`✖ TC-4a initial position ...`. The listed ID counts only as its own word in a test's printed name (`shiploop_test_counts._id_pattern`:
not preceded by a word character or `-`, not followed by a word character), so `TC-4a` does not show `TC-4`. The hint named the wrong
cause, and the model made four source-reading calls to learn the rule (events.jsonl lines 385 and 411 are the refusals; the model's
submissions are the lines before).

**Built (status: firm for the hermetic tests and the recorded-output recomputation; seen in 1 of 6 recorded runs).**
- `shiploop_test_counts.named()` returns a third key, `inside`: each missing ID that some non-skip, non-announcement line holds at the
  start of a longer token, mapped to the first such line, cut to `INSIDE_CHARS` (100; display only, it decides nothing).
- `shiploop_test_loop.judge` copies it into the verdict as `ids_inside`, only when non-empty. `_explain` leads, for those IDs, with the
  rule, the quoted line and the rename example, and keeps the select-and-print remedy for IDs with no hit; one refusal names both when
  both causes occur.
- The rule is one constant, `shiploop_prompts.ID_WORD_RULE`, restated once in each packet that says a listed ID must be shown: the
  step-plan and test-author duties, `COUNT_RULE` (test-green, regression and the rerun stages) and the test-red lines. The step-plan
  duty also says "Declare the ids as the tests will be titled". Strict matching is unchanged (`TC-4` is still not shown by `TC-40`).
- Test setup: `TestLoopTests.setUp` now isolates Git configuration (`GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`) as
  `ReleaseVerifyReturnedResultTests` already did; it changes the setup of the 53 real-git tests of that class that existed before this
  branch (counted at b73c30ba; the audit's "about 80" was the suite's total of 81), which pass with it.

**Correction from the audit that changed the build (the design's prototype was wrong).** The prototype took the first line holding the
ID as a plain substring, so an ID that merely starts another ID got a false hit: `TC-1` listed, `TC-10` and `TC-13` printed, refusal
"TC-1 appears only inside: ✔ TC-10 ... Title each test so its listed ID stands alone", with the correct remedy dropped. The prototype's
own test pinned that as right. The relation is now a whole-token one: the ID must start a token (same left edge as the whole-word rule)
and the next character must begin a new run, a letter or `_` after an ID that ends in a digit, a digit or `_` after one that ends in a
letter (`TC-4a`, `TC-4_a`, `TC-A1` are inside; `TC-40`, `TC-AB` are other IDs). This is a character-class rule over the ID's last
character, not a threshold.

**Evidence.** `docs/experiments/batch-1010j-g6-ids-floors-20261008/a1_replay.py` replays the recorded ids-missing output of the r2
Checkers test-author probe (the 6000-character tails ShipLoop stored, so the earliest titles TC-4a to TC-9a are cut): the raw
substring reports 4 IDs inside (TC-10, TC-11, TC-1, TC-13), the whole-token relation 3 (TC-10 as `TC-10c`, TC-11 as `TC-11a`,
TC-13 as `TC-13a`), and the raw match's extra hit is exactly the audit's false one, `TC-1` "inside" `✖ TC-13a oversized and garbage
bodies ...`. Output: `a1-replay-output.txt`. Fail-first, measured by running the new tests against the unchanged source: all 8 new tests in
`test/shiploop-test-counts.test.py` error (`KeyError: 'inside'`) and 5 of the 7 new ones in `test/shiploop-test-loop.test.py` fail or
error (the refusal text, `ids_inside`, `ID_WORD_RULE`); the other two are guards that pass on the unchanged tree (a missing ID that starts another ID keeps its remedy; an ID no line holds keeps it). Thirteen mutants, each caught:
raw substring, skip lines counted, digit and letter classes widened, the left edge dropped, the cut dropped, `ids_inside` not carried,
the `--verbose` remedy kept for an inside ID, and the rule removed from the refusal, `COUNT_RULE`, the red lines and each duty, plus
the four the review added (below); `mutate.py a1`, output `mutation-a1-output.txt`, in the same commit.

**Review of the commit (2026-10-08).** Four findings concern A1: the two below, the test-class count in the test-setup bullet above
(53, counted, not the audit's "about 80"), and the mutation evidence, which the reviewed commit claimed but shipped in the A5 commit and now
sits in this one.
- *A longer token that is itself a listed ID is not "inside" the shorter one.* With `TC-4` and `TC-4a` both listed and only `TC-4a`
  printed, the first build reported `TC-4` as inside `✔ TC-4a ...`, so the refusal said "Title each test so its listed ID stands alone"
  and dropped the select-and-print remedy for a test that is simply missing: the audit's `TC-1` against `TC-10` error in a rarer form
  (a letter or underscore after a digit, a digit or underscore after a letter). `named()` now takes the whole longer token
  (`_inside_pattern` group 1) and counts a line only when some token on it is not one of the listed IDs. Tests: counts
  `test_a_longer_token_that_is_itself_a_listed_id_does_not_hold_the_shorter_id_inside` (three id schemes; failed first on the assertion,
  the `inside` entry), `test_a_line_with_a_listed_longer_token_and_another_longer_token_still_holds_the_id_inside`; loop
  `test_a_longer_token_that_is_itself_a_listed_id_leaves_the_shorter_one_a_missing_test` (judge and refusal; failed first on
  `ids_inside`). The refusal that quotes the first of several inside IDs is now pinned
  (`test_the_refusal_quotes_the_first_listed_id_that_is_inside_a_longer_token`), and so are an underscore after a letter-ending ID
  (`TC-A_x`) and a line holding both a listed and an unlisted longer token. The review's two A1 survivors (the last ID quoted, the
  underscore class) are mutants A1-16 and A1-15; A1-14 (a listed longer token counted) and A1-17 (only the first token of a line read)
  cover the new rule; all four are caught.
- *The cost of `named()` on a very large output.* The review measured 1.37 s at b73c30ba against 3.52 s for 100,000 lines and 30
  missing IDs, and put it down to `_id_pattern(test_id)` being compiled once per line. `named_bench.py` (output
  `named-bench-output.txt`, best of 3) shows that hoisting that pattern alone recovers little (3.6 s to 3.4 s in the session's
  trial, not kept); the cost is the added second pass over the lines for each missing ID, which is the feature. So the pattern is
  hoisted, the skip and announcement tests run only on a line the cheap regex already matched, and the second pass is skipped for an ID
  that is not a substring of the output at all (`test_id not in text`, one C-speed scan). Result for 30 missing IDs on 100,000 lines:
  1.4 s at b73c30ba, 3.5 s in the reviewed commit (4fa5fff5, rewritten since; the ref is only a label in the output file), 1.5 s now for IDs the runner never printed, and 0.01 s for IDs that all show
  (unchanged). IDs that are a prefix of printed ones (`TC-1` against `TC-100`...) still cost the second pass (3.1 s), which is the
  inside search doing its work on a refusal path, not a normal run. The prefilter is a timing change only; removing it is an
  equivalent mutant, listed as such in `mutate.py`.

**Not done, and why.**
- The outer stages (`system-test`, `release-verify`) cannot retitle a test or edit a command, so "Title each test so its listed ID
  stands alone" has no exit there. That is the existing limit of every `ids-missing` refusal at those stages
  (`docs/shiploop-refusals-journal-2026-10-04.md`); this change does not widen it, and no outer-stage text was added.
- With several missing IDs the one quoted line belongs to the first ID that has a hit, not to the most relevant one.
- Left edge: an ID in the middle of a token (`XTC-4a`) is not "inside"; the plain remedy applies.

## A5: a run may not run fewer tests than the most an accepted run of the same command ran (2026-10-08)

**Question.** The model's `min_tests` is only its first guess: in the recorded round-1 and round-2 runs it sat at 26 to 94 percent of
what the command actually ran (18 of the 39 commands that named a minimum; Checkers 12 and 8 against 27 and 16 to 17, Battleship 4
against 5). Nothing stopped a later stage, or an Improve-style edit, from removing or skipping a test and still passing the
recorded command. SPEC S-9 says a check "that ran nothing" is not a pass and S-5 says reruns of recorded checks belong to the script;
"ran less than before" is not in S-9, so this closes a latent gap rather than a failure seen in a run. It is built because the owner's
own rule for such gaps is to act on recurrence, and the gap recurs in every run (the minimum is always below the count).

**Built (status: interim; hermetic tests and the replay are firm, the live effect is unmeasured).**
- `shiploop_test_loop.accepted_counts(root, state, work_item)` returns, per command, the highest `counts.ran` of any run ShipLoop
  accepted for the item: `passed` records only, runs with status `passed` (or `red` at the expected-RED and probe runs) and an integer
  count, from the actions in the history after the item's latest accepted step plan, or from its latest accepted `test-refine` on when
  that came later. The first number is the test-author probe (a `passed` record whose run status is `red`, with the same counts as
  test-red). No state key: it is derived from `tests/<action>-verify<N>.md`, as `navigator.implement_progress` derives its count.
- `verify()` converts an otherwise accepted run below the floor to `too-few-tests` (a product failure, so it counts toward the 7-refused
  run limit) and records `accepted_ran` on every run that had a floor. Not applied at `test-refine`, the outer stages
  (`system-test`, `release-verify`) or the end-of-work review.
- `_explain` names both numbers and the stage's real exit; `RATCHET_RULE` is printed in the test-red lines, the test-green and
  regression loop packets and the rerun packets (static-checks, verify, integration-verify), `REFINE_RULE` in test-refine's, none in
  the outer stages'. The test-author duty says what the probe count becomes. SKILL.md, the module docstring and the record register
  say the same, with the known limits.
- Not built from the design: filling a floor into the recorded commands; a floor at the outer stages or the end-of-work review (no
  revise to lower it; a union across items would dead-end a legitimate consolidation); a run-wide key.

**Corrections from the audit that changed the build.**
1. *"Report revise" was false at three stages.* The design's refusal and `RATCHET_RULE` said "report revise" unconditionally. Through
   the real gate on the prototype a revise right after a floor refusal at `test-green` is refused ("a complete test loop reports
   outcome done"), and at `static-checks` ("a complete quality loop reports outcome done"); it opens after 7 refused runs
   (`remedy_open`) or with a stopped loop packet. It is free at test-author, test-red, test-refine, verify and integration-verify.
   The `too-few-tests` branch now follows `_has_loop_packet(stage)` (the condition `verify` already used for its could-not-run text):
   at the loop stages it says revise "accepts it once the refused runs below reach the limit or the loop stops as blocked (at once when
   no Improve card is bound)", elsewhere
   "report revise naming what was removed and why". `RATCHET_RULE` no longer promises revise; it says the refusal states when the
   stage accepts it. Tests drive both exits through the gate: test-red revise accepted at once; test-green and static-checks revise
   refused with the loop message, then accepted after the 7th refused run; verify revise accepted at once.
2. *`test-refine`.* Its duty says "explain every removed or narrowed case", and a floor there would have made a full item redo (one of
   `MAX_REVISES`=2) the only exit for what the duty allows. Decision (the audit's smallest fix, no new state key): the floor is not
   applied at `test-refine`, and the count restarts from the item's latest accepted `test-refine`, so later stages are held to the
   count it accepted. The test-refine packet carries `REFINE_RULE` instead of `RATCHET_RULE`, so it never says both. Cost, stated:
   `test-refine` can lower the count without a revise; the reconciliation is the stage's duty and its result, not a gate.
3. *Evidence wording.* The design said "counts only ever grew, 0 false refusals". True for what was replayed, but every recorded run is
   greenfield (the repository was empty; tests are only added), so it says nothing about brownfield items that remove or replace
   tests. The first number is taken before `implement`, which may edit tests, so a legitimate removal or replacement there lands as a
   refusal at test-green after a whole Until Loop, with the slow exit above. This is **unmeasured for brownfield**; it is written into
   SKILL.md, the module docstring and this entry. The smaller alternative the audit named (take the first number at the first accepted
   post-implement run and call the test-author to test-red window a known limit) was not chosen: the probe is the only accepted
   observation at the stage that may edit tests, and excluding it leaves test-author to test-red removals unseen. If the owner prefers
   fewer possible false refusals for a case never seen, it is a one-line stage filter in `accepted_counts`.
4. *Tests that survived mutation.* The audit's mutant removing `+ [action]` passed all 16 tests, because the branch only matters when
   the current action already has a passed record (a later gate refused the same done). The branch is dropped: the floor reads
   accepted actions only, so a pass whose action ShipLoop has not accepted sets no floor (pinned by a test). The new mutants that first
   survived (refused records counted; an uncounted run read as a count) drove two stronger tests, and one design mutant (the earliest
   step plan row instead of the latest) is equivalent, because a plan action has one history row, and was dropped.
5. *Housekeeping.* The duration pin for `test/shiploop-test-loop.test.py` is 94.0 s at 115 tests (see `test/suite_catalog.py`); the
   known-limits text adds state-dependent selection flags (last-failed, changed-only) beside generated cases and host-dependent skips.
   The refusal text of the Checkers case is events.jsonl lines 385 and 411; lines 384 and 410 are the model's submissions.

**Review of the commit (2026-10-08).** Four findings concern A5.
- *An unreadable count after a counted one passes.* A focused command whose `ids` all show but whose reporter the counter does not
  read has no number to be held to; the review confirmed it with a probe (`accepted_ran` 5, status `passed`, `counts` null) and found
  the `run["counts"] and` guard untested. Decision (KISS: it needs a model to change reporter, never seen, and refusing an uncounted
  pass would be a new refusal for the outer-stage-style "cannot be counted" case): keep the behaviour, pin it
  (`test_an_uncounted_pass_after_a_counted_one_is_accepted_and_records_the_floor_it_was_not_held_to`), and state it with the other
  known limits in SKILL.md and the module docstring. Mutant A5-25 (the guard removed) is caught.
- *The loop-stage wording understated the unbound case.* `check_terminal` asks for a loop packet only when an Improve card is bound, so
  with none, `revise` at `test-green`, `regression` or `static-checks` is accepted at once (the review called it). The sentence now
  ends "(at once when no Improve card is bound)"; the loop-packet wording stays for the bound case. The new
  `test_with_no_bound_improve_card_a_floor_refusal_says_revise_is_accepted_at_once_and_it_is` drives it through the gate: it failed
  first on the missing clause, then passes with revise accepted at the first refusal. Mutant A5-26 (the clause removed) is caught.
- *Mutants the review kept alive.* The restart ignoring the work item (another item's `test-refine` row after this item's step plan
  restarting this item's count) and the earliest rather than the latest `test-refine` restarting it. Two tests now pin them
  (`test_another_items_test_refine_does_not_restart_this_items_count`, `test_the_latest_test_refine_restarts_the_count`); the mutants
  are A5-23 and A5-24, both caught. The review's other two survivors (the quoted ID order, the underscore class) are A1-15 and A1-16.
- *Optional, not built: the floor in the implement packet, and "(an accepted run ran N)" in the command listings.* The implement
  stage is the one most likely to remove or replace a test in a brownfield repository, and its fresh-context packet learns of the
  floor only from a refusal at test-green after the whole Until Loop. Not built, for these reasons: the implement duty already says
  existing tests belong to the checks and may change only when a criterion says so; and the exposure is unmeasured for brownfield
  (see below), so the round-3 brownfield item should decide with evidence whether a sentence there earns its place. The
  number-in-the-listing variant would add a record read to every command listing for the same unmeasured gain. Both stay recorded
  under "Open".

**Evidence.** `docs/experiments/batch-1010j-g6-ids-floors-20261008/`: `a5_export.py` reads the 20 recorded runs that have test
records under `/Users/dadleet/e2e-runs` and writes `a5-recorded-runs.json` (history rows, step-plan commands, per-record statuses and
counts; no prompts or output); `a5_replay.py` rebuilds each run's records and calls `accepted_counts` at every action. Result
(`a5-replay-output.txt`): 20 runs, 225 test records, 199 recorded runs held to a floor, 0 would be refused. Five of the 20 runs (the 10-03 and
10-05 Luna Battleship runs, the 10-06 audit run and both v1220 Battleship runs) hold no floor: none of their 231 passed or red runs
has a count, because `node --test` output could not be counted before the node reader (c38f6887). Fail-first, measured by running the new tests against the commit-1
source: 15 of the 21 new tests fail or error and 6 are guards that pass on it (the equal count, a refused record, an unaccepted pass,
another item, a run refused for another reason, the outer stages). Twenty-five mutants of the floor, its wording, its scope and its
packet text are all caught (`mutate.py a5`, output `mutation-a5-output.txt`; the 21 of the first build and the four the review added,
A5-23 to A5-26; a 22nd of the first set, the earliest step-plan row, is equivalent and left out). Fail-first of the review's four new
A5 tests: one fails on the unchanged source (the unbound-card wording), three pin behaviour the source already had and are checked by
the mutants A5-23 to A5-25.

**Suites run on the final tree (serial, no Git environment override in the shell, `SHIPLOOP_PROGRESS=off`).** Quick tier
`bash test/run-all.sh --group quick --changed-from origin/main`: PASS, 31 suites (7 min 41 s), among them `shiploop-test-loop` 115 tests
in 94.0 s, `shiploop-test-counts` 33, `shiploop-status-display`, `shiploop-packet-completeness`, `shiploop-guidance`,
`shiploop-delegation`, `shiploop-stage-spec`, `shiploop-callback-contract`, `shiploop-keepalive`, `test-groups`. Outside the quick tier,
because they read the changed modules or the test records, each run alone with `python3 test/<suite>.test.py`: `shiploop-e2e` 350,
`shiploop-run-review` 363 (not edited here), `shiploop-workspace` 77, `shiploop-chain` 42, `shiploop-chain-git` 17,
`shiploop-chain-handoff` 16, `shiploop-full-runtime` 2, `shiploop-consumer-delivery` 27, `shiploop-consumer-delivery-cli` 5,
`shiploop-knowledge` 25, `shiploop-rehydration` 12, `shiploop-revise` 14, `shiploop-improve-changes` 4, `shiploop-discovery` 8 and
`improve-runtime` 12. `improve-runtime` failed once in its first run of this batch (one failing test; its output was not kept, and
nothing under `skills/improve/runtime` or its test was touched) and passed in each of 32 reruns afterwards (8 serial, 24 six at a time),
so the one failure is an unexplained flake, not a finding. The kept-head window is unchanged: the status block ends at 7971 of 8000
over all 574 dry-run packets, before and after, at the 62-character checkout path. `shiploop-test-loop` (115) and
`shiploop-test-counts` (33) also pass with `GIT_CONFIG_NOSYSTEM=1` and a global Git configuration that marks a `git-lfs` filter
required for every file (`git-lfs` itself absent): the `setUp` isolation keeps the real-git tests off that configuration.

**Open, for the next rounds.**
- Round-3 acceptance criterion (5) must read: every inner rerun is refused below the highest count accepted since the item's latest
  step plan or test-refine, with both numbers; consumer and outer commands are not floored (a known limit). It must not say that
  every regression and consumer command carries a floor.
- Add one round-3 item that legitimately removes tests (brownfield), to measure the revise cost; read `too-few-tests` records with
  `accepted_ran` directly, and `callback-attempts` for a revise submitted right after a floor refusal at a loop stage (a wasted round
  trip each), so whether a model told about revise over-uses it is observed.
- Optional, tenet-aligned, not built: the packets state the rule but not the number, so a model learns it only by being refused.
  `rerun_lines` and `render_lines` could append "(an accepted run ran N)" to each listed command, which would make the check
  observable before done. The implement packet, where a brownfield test is most likely to be removed, does not state the floor at
  all. Both wait for the round-3 brownfield item (see "Review of the commit" above).
- Outer stages and the end-of-work review stay unfloored (owner decision needed); tests removed before the first accepted run (the
  baseline stage's counts are model-recorded, not script-run) are not seen.
