# U7 + U10: answerable person observation, Improve recovery after compaction

- Date: 2026-10-17
- Status: interim (offline: real-CLI route tests and renders; no live run yet; plan section 3 step 3 measures it live)
- Units: U7 (F8; reviewer F X-1, F-7, F-15, F-17, F-18, F-20) and U10 (F11; reviewer E step 30, G30-1), plus the
  coordinator's addition from `docs/shiploop-implement-step-fix-plan-2026-10-17.md` section 0.1 row 3 and section 4.2
  (consumer actor, entry route and access prerequisites established at prepare).

## Questions

1. U7: can a person-only check be asked so it is answerable, and does a reply that answers only some cases let
   release-verify finish (cases recorded not-run, carried to handoff) instead of blocking again on the same ask?
2. U10: after a compaction mid-review, does the reprinted Improve packet stop the model redoing a pass it already
   recorded?
3. Addition: are the consumer's entry route and access prerequisites probed read-only at prepare and again at
   release-check, with an unresolved one kept open with its owner and no grant created?

## Change

- `shiploop_prompts.DUTIES["release-verify"]` item 6: verify every other case first; record the case as an open item
  (who does what, where, what they report); ask once (`awaiting` kind `present`): step 1 reaches the consumer entry and
  says what to answer if it is missing or hidden; `report` is a fill-in list, one yes/no line per case with what to look
  for; the run's exclusions bind the run, not the person; on the reply recheck only the answered cases; an unanswered case
  is not-run, an open item for handoff quoting the reply, and the stage continues; block again only when the reply
  answers none, or a required delivery-contract behavior obligation still has no passed observation.
- `shiploop_prompts.DUTIES["prepare"]` new item 6 (old 6 is 7): the consumer's account or role, entry route and access
  needs, checked read-only with the platform guide's probe (GUIDES/platforms/), each prerequisite under
  HOME/environment.md ## Access and accounts, an unresolved one open there with its owner and the stage that needs it;
  no grant; it does not block prepare.
- `shiploop_prompts.DUTIES["release-check"]` item 2: rerun prepare's probe, save its output beside the dry run's; a gap
  the run may not fix stays open with who can grant it, for release-verify's step 1; no grant.
- `shiploop_navigator._answered_lines`: for a `present` wait, one more line: cases the reply leaves unanswered are
  recorded (an open item, consumer handoff, at an open-item stage; else not-run in `summary`) and the stage continues;
  block again only if the reply answers none (and, in a delivery-contract run, while a required delivery obligation has
  no passed observation). `Asked` and `Reply` are bounded (2,000 and 4,000 characters; the decision file is named).
- `shiploop_navigator._producer_blocks`: the reply is its own block `answered` (P1, after the duties) instead of part
  of the FILE_ONLY `deltas` block, so a head prints it (F-20: the resumed chess-run release-verify found it only in the
  packet file).
- `shiploop_navigator._improve_recovery_lines` (new) and `improve_packet`: once the review has written a file, one line
  after the two instructions: which passes improve-pass recorded (`pass-<n>.json`), a review file written but not
  recorded, "do not redo a recorded pass", and one next command, improve-pass. Built from file names only (a render reads
  no host file: `shiploop-guidance`'s read guard refused the first version, which read the runtime receipt). improve-pass
  is safe in every state a compaction leaves: it reprints a recorded pass's runtime done when that has not run, and
  otherwise its refusal names the next step (the next review file, or the stage's complete).
- `references/platforms/salesforce.md`: new section "Consumer entry access (read-only probe)": the user's profile and
  permission set assignments at prepare; `PermissionSetTabSetting` for the tab and `SetupEntityAccess` (`TabSet`,
  `ApexClass`) at release-check; no row means hidden; grant nothing. `references/consumer-delivery.md`: the ask's shape
  and that a partial reply closes no required behavior obligation.

## Deviation from the plan text, and why

The plan says a partial reply "completes release-verify ... (handoff carries them)". That holds for a run without a
delivery contract. In a delivery-contract run (`--delivery-contract`; the chess run was one) `consumer_delivery.
validate_transition` refuses release-verify, operations and handoff done, and `validate_terminal` refuses the run's end,
while a required behavior obligation has no passed observation ("release-verify needs required behavior observations";
"handoff cannot discard a recorded pending requirement", references/consumer-delivery.md). Reviewer F-18's premise that
"a required observation still unrun is allowed at done" is wrong for such runs. The implement-step plan section 4.2 says
the same: a later-owned procedure "cannot ... close a required delivery observation". So in a delivery-contract run the
packet says to ask again for only the unanswered lines of that obligation; the gate was not weakened. Whether a person's
explicit "record those as not confirmed" may close a run with a required behavior obligation unpassed is a decision for
the owner (it would change the delivery contract's completion rule).

prepare's result has no `assumptions` field (`shiploop_assumptions.OPEN_ITEM_STAGES` excludes it), so the unresolved
access prerequisite is kept open in HOME/environment.md ## Access and accounts with its owner and the stage that needs it,
not as an `assumptions` row; release-check (also no `assumptions` field) keeps it there too, and release-verify's ask
starts from it.

## Fail-first (source reverted to 03c5edbc, tests kept, then restored byte-exact)

| Test | Without the change |
|---|---|
| callback-contract `PersonObservationRouteTests` (real CLI: blocked present, `resume --observed` partial reply, done with the open items, operations, the handoff packet lists them) | prompts and navigator reverted: fails on the ask's shape in the guidance; navigator alone reverted: fails, the reply is not in the printed text |
| consumer-delivery `test_a_partial_person_reply_closes_no_required_behavior_...` (done with the obligation unrun refused by the delivery gate; the ask again it names accepted) | fails: the resumed packet has no partial-reply line |
| actual-improve-cli `test_a_compaction_after_a_recorded_pass_...` (real CLI: pass 1 recorded, `next`, the named improve-pass reprints the done, done, `next` again, the refusal names complete, complete; one pass file, review file untouched) | fails: no review-progress line |
| actual-improve-cli `test_after_a_returned_pass_...` (pass 1 returned, refusal names review-2.md; review-2.md written, not recorded; the named command records pass 2) | fails: no review-progress line |
| guidance `test_consumer_access_is_probed_read_only_at_prepare_and_again_at_release_check` | wording pin (no gate exists for it) |

## Render sizes (characters, normal install: run directory 83, CLI path 96)

Offline inner loop (`packets.py --offline node-fix-bug`, both routes): every packet text byte-identical before and after
(`diff -r`, manifest aside); `render_diff.py` reports +0 for every stage. Its head-table FAILs (inline implement 16,040
over 16,022; ask-agent step-plan 19,790 over 19,673 and implement 17,494 over 17,476) are already there at 03c5edbc
(before == before gives the same FAILs). The Improve packets a review begins with are unchanged: the new line appears only
after the review has written a file.

Full two-item walk (`shiploop_head_plans.full_walk`, as shiploop-head-order renders it):

| stage | route | printed before | printed after | whole before | whole after |
|---|---|--:|--:|--:|--:|
| prepare | inline | 12,343 | 12,856 | 12,317 | 12,830 |
| release-check | inline | 13,349 | 13,684 | 13,323 | 13,658 |
| release-verify | inline | 15,440 | 15,930 | 15,414 | 15,904 |
| prepare | ask-agent | 12,559 | 13,072 | 12,533 | 13,046 |
| release-check | ask-agent | 13,565 | 13,900 | 13,539 | 13,874 |
| release-verify | ask-agent | 15,656 | 12,530 (head) | 15,630 | 16,120 |

ask-agent release-verify now passes the 16,000 print limit, so it prints a head (12,530) instead of the whole; a live
release-verify packet is far over the limit anyway (66-69 KB in the chess run). Every print stays under 20,000.

## Suites (each once, after the last edit)

All green, 1,584 tests in 23 suites (`SHIPLOOP_PROGRESS=off python3 -B test/<name>.test.py`):

- Pin suites: head-order 33, packet-recut 30, packet-bounds 10, packet-completeness 62, packet-obligations 15,
  step-packets 9, delegation 59, loops 51, navigator-contract 110, reference 8, reference-routing 4.
- Touched: callback-contract 73, consumer-delivery 30, guidance 64, actual-improve-cli 83 (run alone: the known
  load flake), domain-words 5.
- Callers of `improve_packet`, `_answered_lines` and `_improve_pass` (`git grep`): keepalive 60, e2e-commit-counters 107,
  e2e-packet-anatomy 29, improve-schedule 33, navigator-dry-run 34, rehydration 17, run-review 658.

An earlier run of the same list (before the receipt read was removed) failed 12 guidance tests on the render read guard
(`render read evidence: <workspace>/.shiploop-improve/<child>/packet.json`); the recovery line was rebuilt from file
names.

Skipped: test-loop and the loop-block suites (no change to the loop block, path notation or `shiploop_test_loop.py`);
the full tier, run-all.sh and live E2E (worker brief).

## Key learning

A reply that answers part of an ask is the normal case when the ask is prose; asking one yes/no line per case makes the
reply countable, and recording the unanswered lines not-run lets the run continue where nothing gates on them. Where a
required delivery obligation does gate on them, the honest route is a narrower second ask, not a waiver: the delivery
contract's completion rule is the owner's to change. A recovery line for a reset model must come from script-owned file
names, not from host files the render may not read, and the safest next command is the one whose refusals already name
every next step.
