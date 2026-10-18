# Row: W2-C (valid acceptance procedures), branch feat/pr-w2-procedure-f8a399

- Date: 2026-10-17. Base: e6a86587 (wave 1 merged). Status: **interim**: offline renders, fixtures and suites only.
  Whether a model reviewer reading the new focus asks for the revision is a live qualification (the reviewer pilot of
  T25), not run and not proven here.
- Spec: [implement-step fix plan](/Users/dadleet/src/skill-craft/docs/shiploop-implement-step-fix-plan-2026-10-17.md)
  §0.1 row 2, §4.2, T25, T26, T29, T34; disposition W2-C in
  [the packet-review plan](../../../shiploop-packet-review-plan-2026-10-17.md) section 5.
- Question: does one procedure-validity condition, added once to the shared review focus, reach every stage where an
  acceptance procedure is written (spec and test-strategy duties, test-spec's own cases) and every planning review,
  without growing the test-case schema, while a procedure's locator rides with its case or open item to the stages
  that consume it?

## The live case (chess run, retained)

The release-verify packet of `/Users/dadleet/e2e-runs/20261017/salesforce-chess-int-802e29` carried test-strategy's
"Browser procedure (opt-in ...)" from `HOME/architecture.md` (its Real-boundary checks), step 4: "Fool's mate clicks
... Status `checkmate`. One more destination click leaves that FEN in place." After checkmate the side to move has no
legal move, so the procedure asked for a move the state forbids (fix plan §0.1 row 2: an acceptance sequence
requested an impossible state transition and survived repeated review handoffs). F-release.json records how it
reached the person: step 3, F-13 (the same click sequence quoted 8 times across the release-verify open items) and
F-15 (the person-only case), and step 4 (the person answered with a summary, not per case). Its only probe was
test-strategy's file stand-in (`run/notes/test-strategy-probes.md`), which proves the browser tool, not the procedure.
From the plan packet (08) on, 25 of the run's packets, handoffs and results carry it by value
(`scratchpad/pkt-review/in/*`, `grep -c "One more destination click"`), six of them planning Improve handoffs (plan
09, step-plan 12 and 18, test-spec 14 and 20, system-test-author 30); none flagged it. The planning focus then had
no condition on whether the actions can happen in order: "cannot be replayed exactly" asks for concrete inputs, and
this procedure had them.

## Change

- `skills/shiploop/scripts/shiploop_prompts.py`
  - new `PROCEDURE_WALK` (the walk's one wording) and `_PROCEDURE_ITEM`, added as the second entry of
    `_REVIEW_FOCUS_ITEMS`: so `REVIEW_FOCUS_CONDITIONS`, `PLANNING_REVIEW_FOCUS` (every planning Improve handoff) and
    `_duty_focus` (spec duty 10, test-strategy duty 13) carry it. `_duty_focus` and `_focus_list` are unchanged.
  - new `_TEST_SPEC_PROCEDURE`: `DUTIES["test-spec"]` item 4 applies the walk to the stage's own cases, routes an
    unreachable start to an open item, keeps a forbidden action as its own failure case, names where a procedure's
    locator rides (`oracle`, or the open item's `check`) and says a setup change makes an earlier observation stale;
    items 4-7 became 5-8.
  - `DUTIES["test-strategy"]` item 12: a consumer interface case is written under ## Real-boundary checks as an
    ordered procedure from its start (actor, entry route, initial state), with an ID later stages cite (the pinned
    phrase of `packet-completeness` kept word for word).
  - `IMPROVE_SCOPES["test-spec"]`, `["test-strategy"]`: "their procedures" named in the review scope.
- `skills/shiploop/scripts/shiploop_stage_spec.py`: the test-spec row's `done_when` (its Until Loop exits) gains
  "each case's procedure can happen as written from its stated start, or its unreachable start is an open item".
- `skills/shiploop/references/testing-and-documentation.md` (## Test cases, the Test-case planning guidance): a
  **Procedure validity** paragraph with the six facts (start, actions, oracle, observation, ownership, evidence),
  validity kept apart from execution, a stand-in probe proving only a capability, and three generic faults.
- Not changed: the six-field case schema (`expectations.TEST_CASE_KEYS`, `normalise_test_cases`), the focused-ID gate
  (`check_test_cases`), `CONSUMES` and the navigator, the implement and step-plan duties, `_step_lines`,
  `shiploop_loops.py`, `shiploop_test_loop.py` and the outer duties (system-test 5, release-check 6 and release-verify 9
  already say a material change invalidates the observations it affects; the new test pins them as the consumer half).

## Fixtures (T25): `test/fixtures/procedure-validity/procedures.json`

Generic, one requirement (a key/value store with a page that shows a status line and controls). Each fault is written
as an automated six-field case or check row and as an opt-in `### RB-n` architecture check, plus a replayable form and
a fixed form: an impossible transition (update after delete expected to succeed), an invisible observation (the
store's revision asserted on a page that shows only status and controls), an existence-guarded pass
(`test ! -e build/app || ./run-tests`). `ProcedureFixtureTests` (shiploop-guidance) checks the deterministic part:
replayed against an independent reference model each fault shows at its stated step and each fixed form holds; the
guarded command exits 0 having run nothing while the unguarded one fails honestly and both pass once the artifact
exists; the six-field gate accepts both faulty cases (only a review can see the fault) and refuses a `procedure` key;
the focus text that owns each fault is in `PLANNING_REVIEW_FOCUS` (the guard is owned by the existing "run it once and
record the exit code and the cases it executes") and the guide names all three.

## Tests (new)

- shiploop-guidance `GuidanceTests.test_the_procedure_condition_reaches_where_procedures_originate_and_every_planning_review`
  (T34): a cold walk of the whole graph; the condition is inside the spec and test-strategy duty items, in the
  test-spec duty with its own phrases and the new loop exit, once in each of the 7 planning Improve handoffs, and in
  no other Improve handoff.
- shiploop-guidance `GuidanceTests.test_a_procedure_locator_reaches_every_stage_that_consumes_its_case_or_open_item`
  (T26, T29), both routes: a locator in TC-1's `oracle` reaches the cold implement, test, verify and
  system-test-author packets; the implement Improve handoff names the producer packet that quotes `test_cases`; an
  open item's locator reaches release-verify and the item stays open (planned, observer unresolved) until then;
  system-test, release-check and release-verify print their invalidation rule.
- shiploop-guidance `ProcedureFixtureTests` (4 tests, T25, above).
- shiploop-handoff `CaseRowCliTests.test_a_procedure_key_and_an_opt_in_check_as_a_case_are_refused_and_their_named_exits_accepted`
  (T34, test the route): through the real CLI, a case with a `procedure` key is refused naming the six fields; the
  opt-in check written as a case row is refused (`Not listed by a focused command of W1: RB-1.`); the named exits
  (six fields; the opt-in check as an open item naming its locator) pass `--check-only` and the real `complete`.
- Pins edited: shiploop-loops `WorkTextTests.DUTY_ITEMS["test-spec"]` 7 -> 8 (the duty gained item 4).

## Fail-first

- Source reverted to e6a86587 (prompts, stage spec, guide), new tests run, source restored byte-identical:
  `procedure_condition` and `review_text_that_owns_each_fault` ERROR (no `PROCEDURE_WALK`); the locator test, the
  replay, guard and six-field fixture tests and the CLI schema test pass on the base: by design, they pin data flow
  and the unchanged schema (T34 "still refuses"), which this unit must not change.
- Mutation (constant kept; the item removed from `_REVIEW_FOCUS_ITEMS`, item 4 from the test-spec duty and the loop
  exit from the stage row): the same two tests FAIL by assertion, 12 failures (spec and test-strategy producers on
  both checks, each planning handoff, the test-spec phrases, the guide-owner check).

## Suites (each once after the last edit; `SHIPLOOP_PROGRESS=off python3 -B test/<name>.test.py`)

guidance 70 OK; handoff 99, 1 ERROR; head-order 36 OK; packet-recut 30 OK; packet-bounds 10 OK; packet-completeness 62
OK; packet-obligations 15 OK; step-packets 9 OK; delegation 59 OK; loops 51 OK; navigator-contract 110 OK; reference 8
OK; reference-routing 4 OK; stage-spec 14, 1 FAIL; improve-route 17 OK; domain-words 5, 1 FAIL; planning-handoff 7 OK;
e2e-render-diff 43, 1 FAIL; e2e-packet-anatomy 30 OK.

The four failures fail identically on a detached worktree of e6a86587 (made for this check, then removed), so they
are not this change:
- handoff `test_a_revisited_stages_handoff_names_the_previous_accepted_result_and_the_revise_result`: `ValueError: too
  many values to unpack` in `navigator._reviewed_input_lines` (U2's three-value unpack of U4's `SentBack`).
- stage-spec `test_the_several_steps_wording_is_a_pair_of_the_goal_and_each_condition_of_one_row`: the implement
  exit wording of 603a709c ("every check command on the Step lines") against the pin.
- domain-words: `skills/shiploop/scripts/shiploop_knowledge_home.py:615: castling`.
- e2e-render-diff `test_the_cli_path_has_exactly_the_stated_length_and_the_default_prints_the_bare_name` (recorded
  in u3-head.md as failing at 03c5edbc).

Skipped: callback-contract and test-loop (no loop block, path notation or `shiploop_test_loop.py` change); revise
(test-spec revisit lines unchanged); the full tier and live E2E (test economy; no reviewer pilot authorized).

## Renders

`packets.py --offline node-fix-bug` (run dir 83, CLI 96; printed / whole): only test-spec changes.

| stage | inline before | inline after | ask-agent before | ask-agent after |
|---|--:|--:|--:|--:|
| test-spec | 14,828 / 14,802 | 15,577 / 15,551 | 13,001 / 16,370 | 13,750 / 17,119 |

At run dir 163 test-spec prints 15,030 on both routes (table 14,281). Every other stage is byte-identical. render_diff
exits 1 only because the added lines have no allowlist unit (`packet_changes.json` has U1-U35 keys only; no W2 key
was added); the head table check passes with the new values. Head tables: `head_table.json` test-spec inline 14,714
-> 15,463 (whole), ask-agent head 13,001 -> 13,750, whole 16,282 -> 17,031; `packet_head_table.json` test-spec at all
four settings +749; reasons appended to `_comment` / `_doc`.

The two-item full walk of the head-order fixture (printed / whole, inline): spec 13,355 / 16,221 -> 13,900 / 16,766;
test-strategy 14,313 / 16,813 -> 15,007 / 17,507; W1 test-spec 15,533 / 15,507 -> 14,424 / 16,256 (it now passes
PRINT_LIMIT and prints a head, which leaves out chrome lines only: the duty, loop and quoted hand-offs stay); W2
test-spec 14,875 -> 15,624 (whole). The longest print of the walk is 19,959; every head fits 20,000 and the 19,500
required-text bound (head-order OK). Against the fix plan's 16,000 head target (measured, not a gate): inline test-spec
on node-fix-bug 15,577; spec and test-strategy heads 13,900 and 15,007. `PLANNING_REVIEW_FOCUS` grows 1,161 -> 1,690
characters in each planning Improve handoff; the test-spec duty 1,680 -> 2,318.

## Key learning

The planning focus checked a procedure's inputs ("cannot be replayed exactly") but not its sequence, so a procedure
with exact clicks and an impossible step passed six planning reviews and reached a person at release. The fix is one
condition in the one shared list, which each producer already restates as "Before you submit" and each planning
review prints: no new stage, field or registry. The deterministic half (the fault exists; the shape gate cannot see
it; the text that owns it is printed where the procedure is written) is now tested; the semantic half (a reviewer
finds it) is not provable offline and stays for the reviewer pilot.
