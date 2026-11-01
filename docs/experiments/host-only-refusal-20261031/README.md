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
- S2 part (a), the item 6 wording of system-test-author, is not changed. It would tell the author a case the default
  command already runs is never `host_dependent`, which drops the truthful mark; it is not needed once the check is
  correct, and it still needs the 40-call side test.

## Evidence

- `replay.py`, `replay-output.txt` (this directory).
- 06a7473d910bc8b75c0ff247ce0dd6f0a27dbc5c (D1), ba908889db845f7dbccf8091071f2e7f2561e205 (the check),
  227f6ce0d5a2af1afacab619d25d65bfc83fbdb0 and `reviews/E-close.md` (the finding).
