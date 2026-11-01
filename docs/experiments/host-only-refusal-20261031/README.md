# Host-only label send-backs: replay and fix, 2026-10-31

Journal for one change. It starts from item S2 of the stage-prompt review
(`docs/experiments/prompt-template-review-20261031/reviews/E-close.md`, "The default suite gets marked
`host_dependent`") and ends in a code change to `default_suite_drift` in `skills/shiploop/scripts/shiploop_test_loop.py`.

## Question

3 of 3 Salesforce runs on Codex Terra 6.1 high marked the org-native test command `host_dependent: true` at
system-test-author. The same command string was a step-plan row flagged `regression: true`. At system-test,
`default_suite_drift` (added in ba908889db845f7dbccf8091071f2e7f2561e205) ran that command, saw a marked ID in its output,
and refused with `host-dependent-in-default-suite`. Each refusal became a send-back loop of 1.3 to 4.1 minutes and 4 to 7
packets (E-close.md, item 1). Two runs then dropped the mark; one kept it and demoted the native suite from `focused` to
`check`, so ShipLoop stopped counting its ten IDs. How do we stop the loop without losing the record that the suite needs
the org?

## Owner decision and what the evidence did to it

2026-10-31: the owner approved "the small Salesforce fix (no model calls)", which was S2 part (b) of E-close.md: at
system-test-author `complete`, refuse a `host_dependent` row whose command equals a step-plan regression command, naming
two exits (drop the mark, or give the host-only cases their own opt-in command).

Reading the three runs and 06a7473d910bc8b75c0ff247ce0dd6f0a27dbc5c before writing it, (b) does not meet that commit's
owner_review item D1: "Preserve truthful classification, native proof and the existing optional-host-tool isolation gate."
For an org-native default suite there is no opt-in command to split the cases into, so (b) leaves one exit, dropping the
mark, which is what two of the three runs already did when system-test offered the same two exits. (b) moves the loss
earlier and saves packets; it does not keep the record. Status: interim (a reading of three runs, not a measurement).

Decision, confirmed by the owner on 2026-10-31 when shown both ("Ship the safer version instead of the one you approved?",
answer "Ship safer one"): leave the mark alone and stop the check from treating a hosted-runtime command as drift. `default_suite_drift` skips a regression command that
`_remote_base` recognises as testing a hosted runtime: a row `target` that the test strategy lists as keeping state, or a
command a platform card lists under Remote tests. Those are the two existing, generic definitions of "tests a deployed
target" that the base-run mutation gate already uses; no platform knowledge enters the code. The optional-host-tool
isolation gate is unchanged for every command that runs on the machine.

## Replay (no model calls)

`replay.py` reads every archived system-test verify record under `~/e2e-runs*` that ran the drift check (a run with
`host_dependent_ids_shown`) and asks `_remote_base`, with that run's own test-strategy targets, whether the command tests a
hosted runtime. Output: `replay-output.txt`. The corpus grows as other sessions finish runs: 2,920 records at 17:15 and
2,929 at 17:22; the counts below are from the saved output.

| measure | value |
|---|---|
| archived test records scanned | 2,929 |
| records that ran the drift check | 23 |
| drift runs (regression commands checked) | 27 |
| refusals (`host-dependent-in-default-suite`) | 6, all `sf apex run test` |
| refusals the exemption removes | 6 of 6 (1 by platform card, 5 by state-keeping target) |
| refusals left on any other command | 0 |
| clean hosted-runtime runs now skipped | 3 |
| clean runs of other commands, still run | 18 |

Findings:

- F1, firm for this corpus: every archived refusal was a hosted-runtime command, and the exemption removes all of them.
  The corpus is the owner's own E2E runs, so it carries their subject mix (Salesforce, browser and API products).
- F2, firm: nothing else changes. The 18 runs of other commands are still run and read.
- F3, interim: the saving (one loop of 1.3 to 4.1 minutes, 4 to 7 packets, per Salesforce run, and the counted IDs) is
  predicted from E-close.md, not measured after the change; no live run has used it.
- F4, unobserved: the check's intended case (a marked browser case reaching the default suite) appears in none of the
  27 archived runs; only unit tests exercise it, so the archive cannot show the countercase still fires.

## Tests

`HostDependentDriftTests` in `test/shiploop-test-counts.test.py`. Run against the unchanged code (a scratch copy of HEAD,
17:25), exactly these three fail, 3 of the class's 8 tests; the other 5 pass:

- a regression command on a target that keeps state is neither run nor read at the drift check;
- a platform card's Remote tests command (`sf apex run test ...`) is neither run nor read;
- a local default suite beside a hosted one is still run, and a marked ID in its output is still refused (the
  optional-browser countercase 06a7473d asked for).

The file runs 49 tests, all passing; the lint check (`ruff --select F,E9`) is clean before and after.

Suites, quick and prompt groups (31 suites, `--changed-from 240594c9922c42ac0a761717671f93f220e31743`, 8 at a time):
the first run, on the tree before the two wording edits below, passed 30 and failed 1. `shiploop-test-loop` alone took
527 s on a busy machine (its catalog estimate is 94 s). The failure was `shiploop-domain-words`:
`test_generic_text_names_no_domain_word` found the platform words `sf` and `Apex` in the new `default_suite_drift`
docstring, which named the platform's test command as evidence (finding F5, firm: the repo keeps platform detail in
`references/platforms/`, so the evidence belongs in this journal and the commit message, not in generic code). The docstring
now says "all against one hosted platform's test runner", and `references/testing-and-documentation.md` gained one sentence
describing the exception. After those two edits every suite that reads either file was run again and passes:
domain-words 5 tests, guidance 79, reference-routing 4, e2e-packet-anatomy 30, retired-terms 6, test-counts 49,
stage-spec 12, packet-bounds 21. The whole tier was not repeated on the final tree (the edits are a code comment and one
reference sentence); CI runs the quick tier on the pushed tree.

## Known gap and remaining unknowns

- A browser case inside a command aimed at a state-keeping target is no longer refused by this check. The archive has no
  such run. Left unguarded on purpose (fix what breaks a normal run, document the rest); a run that does it would show as
  a Chrome failure on a machine without Chrome.
- Whether a live Salesforce run now passes system-test without the send-back is untested. The next one is the test: its
  trace should show no `host-dependent-in-default-suite`, the command in the system rows still marked, and the native
  suite still `focused` with its IDs counted.
  Update 2026-10-31: two live runs did not reach the fixed path (see Live check); the next one that does is the test.
- S2 part (a), the item 6 wording of system-test-author, is not changed. It would tell the author a case the default
  command already runs is never `host_dependent`, which drops the truthful mark; it is not needed once the check is
  correct, and it still needs the 40-call side test.

## Evidence

- `replay.py`, `replay-output.txt` (this directory).
- 06a7473d910bc8b75c0ff247ce0dd6f0a27dbc5c (D1), ba908889db845f7dbccf8091071f2e7f2561e205 (the check),
  227f6ce0d5a2af1afacab619d25d65bfc83fbdb0 and `reviews/E-close.md` (the finding).

## Shipped

Added after publication, 2026-10-31. The findings above keep their status: F1, F2 and F5 firm, F3 interim, F4 unobserved.

| what | value |
|---|---|
| fix commit | 7ca88df48f63631f55c8d9b16b27885f667b15a6, pushed to main at 17:41; rebased first onto four documentation commits that landed while the suites ran |
| release | 5de751eebfc58d049032c873365e18e3621c1c7a: skill-craft 2.27.1 and shiploop 1.26.1, published at 17:43 by `scripts/release-push.py` after four checks (sync-plugin-views, marketplace packages, release boundary against the fix commit, test-groups). Another session had published 2.27.0 and 1.26.0 first |
| hosts | Claude and Grok updated from 2.27.0 to 2.27.1, Codex marketplace upgraded; each installed copy of shiploop_test_loop.py was checked for the new docstring: Claude cache 2.27.1, Codex (codex plugin list shows skill-craft@whichguy 2.27.1) and Grok installed plugin all hold it; Cursor not refreshed (its app) |
| CI on main | both passed. The fix commit's run 41257845999 passed plan, release-boundary and the quick tests (the quick job took about 11 minutes); the release commit's run 41257977788 passed the full tier (core, shiploop-1, shiploop-2, shiploop-3, e2e-apparatus), release-boundary and plan |
| live check | open: the next live Salesforce run, which needs the owner's go to deploy to the org |

## Live check

Added 2026-10-31 after the owner's go (answer "3": run the live check, and apply the three defaults), and extended after the
owner's second "3" (both: investigate run 2, and a third run). Three full runs on the published plugin (skill-craft 2.27.1,
ShipLoop 1.26.1; Codex gpt-6.1-terra, xhigh), each launched from a detached checkout of origin/main with its own platform
prefix in org `de`. The org lease is exclusive, so they ran one after the other, and all three cleanups were verified.
Output: `live-check-output.txt`. Scripts: `live_check.py` (the four signals from a run's records) and `counterfactual.py`
(the replays in L2; `--as-recorded` uses the run's own marks).

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| case and prefix | battleship-salesforce, SLBtlHo9a87 | battleship-salesforce-ui, SLNvHo250f | battleship-salesforce-ui, SLNvHo5c20 |
| time | 27.6 minutes | 25.2 minutes | 27.9 minutes |
| ShipLoop start | `workspace start` | `init` with its own run folder | `workspace start` |
| harness verdict | pass | fail on `committed` only (L3) | pass |
| org checks, cleanup | pass, pass | pass, pass | pass, pass |
| test strategy declares the org as keeping state | yes (`de org`) | yes (`Salesforce de org`) | yes (`Salesforce org de and authenticated browser`) |
| step plan lists the org test command as a regression command | yes, in the second plan, after a test-stage send-back | no, both test rows are focused | yes, and it stayed through a re-plan |
| system-test author marks the org command `host_dependent` | no (four rows, none marked) | yes, and the browser check too | yes, and the browser check too |
| system test | passed first time | passed first time | passed first time |
| anything for the drift check to do | no: nothing marked | no: no regression command | yes: a marked org command that is also the regression command |

- L1, firm: runs 1 and 2 did not reach the fixed path. Each met one of the two preconditions (a regression row for the org
  command, and a mark on it) and not the other, so the old check would have passed both. Run 3 met both, the joint case, live:
  the check skipped the org regression command, system test passed first time, and the org-native row stayed `focused` and
  `host_dependent` with all three of its IDs found (`ids_missing` empty) in a passing system-test record. No row was refused.
  This is the live confirmation of the fix.
- L2, firm (offline): the recorded state given to each version's `default_suite_drift`. Run 3, rows as recorded: plugin 2.27.0
  asks to run the org command and refuses `host-dependent-in-default-suite` (shown ids controllerFullGame, fleetGeometry,
  seedDeterminism); plugin 2.27.1 asks to run nothing and refuses nothing. Run 1, with the mark added (it had none): 2.27.0
  refuses (TC_ENGINE, TC_CONTROLLER), 2.27.1 does not. The inputs are real; the output the stub returns for the org command is
  invented, so a replay shows what the check asks to run and refuses, not what the org prints. Run 3 on 2.27.1 is the live
  half and the replay on 2.27.0 is the other half; they are not a paired run, so the saving (F3) stays predicted.
- L3, interim, unrelated to the fix: run 2 failed the harness's `committed` verdict. Cause as far as the records show: its
  model ran `init --repo <work> --run-dir <output>/battleship-run`, where the other two ran `workspace start --repo <work>`.
  The skill card's start section prescribes `workspace start` for an empty folder ("An empty starting directory needs no setup:
  `workspace start` makes it a Git repository on `main` with one empty baseline commit") and keeps `init` for "an explicitly
  selected in-place/non-Git run". Its lead-in reads "For new work in an existing Git repository, use the isolated entry below",
  which an empty, non-Git folder does not match, so that lead-in is the likely trap; the transcript holds no stated reason.
  With `init` the harness's `work` folder never became a git repository, so the product copied into it was never committed.
  Frequency: of 454 earlier event streams since 2026-10-24 the first start was `workspace start` in 160 and `init` in 8; 286
  could not be read that way (resumed or seeded runs, other forms). Of these three runs, one used `init`. Not acted on: a
  change to the card's text needs a change note and a measurement, and is the owner's call. The run's `mismatch.md` is left
  unfilled and `test/shiploop_e2e/LEARNINGS.md` untouched on purpose: the release preflight reads that file's commit order, and
  these runs are not an E2E round that vouches for the release.
- Context, exploratory: of 9 earlier unseeded Salesforce runs (final system-test-author result), the Terra runs marked some row
  `host_dependent` in 3 of 4 and Grok in 0 of 5, so the author's choice varies; the step plan's `regression` flag varied across
  these three runs too. The joint case took three runs to see.

What stays open: the saving per avoided loop (1.3 to 4.1 minutes and 4 to 7 packets in E-close.md) is still predicted from
earlier runs; the card's start lead-in (L3) is unexamined beyond reading it and counting starts.
