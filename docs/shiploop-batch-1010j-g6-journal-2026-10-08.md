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
