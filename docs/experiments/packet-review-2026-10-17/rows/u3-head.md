# Row: U3 (print what the duties cite) and U4 (revisit lines), branch feat/pr-u3-head-1b7a72

- Date: 2026-10-17. Base: 03c5edbc. Status: **interim** (offline renders and suites only; no live run yet; three
  recorded budget gaps, below).
- Questions. U3: does every label a printed head's guidance cites resolve inside that head (findings A AX-2, B6-2, C X3,
  D DX-1, E C-1, G29-2, G32-1, G33-1, G33-2)? U4: does the head of every revisited stage (step-plan, test-spec,
  implement) say why it is back, name its previous accepted result, list the upstream ID changes and ask to keep
  unchanged rows (C X1, X2, C2-1, C2-8, C2-14)?

## Change (skills/shiploop/scripts)

- `shiploop_navigator.py`
  - `_producer_blocks`: new LOOKUP block `guides` right after `reference-symbols` (the guides and policies the stage text
    names, from `_cited_guides`; the Backchain lines when the stage's Backchain line stays in the duty);
    `backchain-route` now carries the paragraph with its cited Backchain lines and sits before `builds-on`; the `quoted`
    block passes through `_without_step_criteria`; `_revise_delta_lines` left the file-only `deltas` block.
  - `_stage_input_blocks`: new P1 blocks `revisit` (before `step`), `workspace-return` (at `RETURN_STAGES`) and
    `delivery` (at `consumer_delivery.RELEASE_GATED_STAGES`).
  - `_run_context_lines` split into `_stage_guide_lines`, `_cited_guides` (`CitedGuides`), `_backchain_lines`,
    `_delivery_lines`, `_head_delivery` and `_workspace_lines`; with `producer=True` it prints only what the head
    blocks do not (the uncited guides, the uncited loop-resource status, the workspace lines outside `RETURN_STAGES`, the
    delivery lines outside the gated stages) and `_run_rules` prints no policy there (the head's `guides` block does).
  - `_sent_back_results` generalised to `REVISIT_STAGES` (step-plan, test-spec, implement), returning `SentBack`;
    `_revise_delta_lines` replaced by `_revisit_lines` (four lines), with `_upstream_line`, `_change_text`, `_id_changes`.
  - `_goal_lines`: the "Also: ... carried over" line names the stage's own previous result and prints only when one
    exists.
  - `_step_lines`: prints the step's criteria by value under the Step line (`_step_criteria`); the Step paths and Later
    steps lines are unchanged (coordinator: no path fence).
  - `_commit_scope_lines`: `_against_plan` names the step-plan path list once at document and verify.
  - `PROSE_PATH_LINES`: the two retired revise-line prefixes removed.
- `shiploop_consumer_delivery.py`: `RELEASE_GATED_STAGES`, used by `validate_transition` (same gate order).
- `shiploop_test_loop.py`: `COUNT_RULE`, `FLOOR_RULE`, `RATCHET_RULE` shortened (every clause kept; `ID_WORD_RULE`
  verbatim): 650 -> 574, 498 -> 425, 313 -> 290 characters.
- Not changed: `handoff_lines`, `_consumer_lines`, `reads_lines`, `improve_handoff_text`, `_select_head` (U1/U2 areas;
  the prefix rule stays).

## Fail-first (source reverted to 03c5edbc, new tests run, source restored)

- `shiploop-revise -k four_revisit`: FAILED (1).
- `shiploop-head-order -k CitationTests`: FAILED, 57 sub-test failures across both fixtures and routes.
- `shiploop-consumer-delivery -k release_gated`: ERROR (no `RELEASE_GATED_STAGES`; the head lacked the lines).
- `shiploop-return-review -k return_stage_prints`: FAILED (4: the head of each return stage lacked the route).

## Suites (each once after the last code edit; `SHIPLOOP_PROGRESS=off python3 -B test/<name>.test.py`)

head-order 36 OK; packet-recut 30 OK; packet-bounds 10 OK; packet-completeness 62 OK; packet-obligations 15 OK;
step-packets 9 OK; delegation 59 OK; loops 51 OK; navigator-contract 110 OK; reference 8 OK; reference-routing 4 OK;
revise 15 OK; consumer-delivery 30 OK; return-review 25 OK; test-loop 143 OK (changed `shiploop_test_loop.py`);
handoff 97 OK; v4-consumers 5 OK; rehydration 17 OK; e2e-packet-anatomy 29 OK; e2e-render-diff 43, 1 FAIL:
`test_the_cli_path_has_exactly_the_stated_length_and_the_default_prints_the_bare_name` fails identically at 03c5edbc
(the inline step-plan head prints 2 of the 3 commands it expects; the pause line was already left out), not this change.
Skipped: callback-contract (loop block and path notation unchanged); the full tier and live E2E (test economy).

## Renders (packets.py --offline node-fix-bug, run dir 83, CLI 96; printed / whole)

| stage | inline before | inline after | ask-agent before | ask-agent after |
|---|--:|--:|--:|--:|
| step-plan | 19,673 / 24,327 | 19,923 / 24,327 | 19,790 / 27,718 | 19,767 / 27,718 |
| test-spec | 15,486 / 15,460 | 15,486 / 15,460 | 13,059 / 17,028 | 13,319 / 17,028 |
| validate-existing | 12,821 / 16,040 | 12,992 / 16,040 | 12,821 / 17,608 | 12,992 / 17,608 |
| implement | 16,040 / 19,087 | 16,336 / 19,087 | 17,494 / 22,187 | 17,868 / 22,187 |
| test | 18,004 / 20,759 | 18,300 / 20,610 | 18,004 / 22,327 | 18,300 / 22,178 |
| document | 15,008 / 14,982 | 15,008 / 14,982 | 12,277 / 16,550 | 12,435 / 16,550 |
| verify | 18,393 / 21,137 | 18,531 / 21,038 | 18,813 / 23,125 | 19,045 / 23,026 |
| carry-forward | 14,033 / 18,708 | 15,102 / 18,708 | 15,299 / 21,542 | 16,502 / 21,542 |

At run dir 163: inline test 19,740, verify 19,811; every print stays under 20,000. The two-item head-order fixture:
every head under 20,000; the largest growth is carry-forward (+1,151 inline), the largest whole growth implement +107
(the step criteria). Head tables re-measured: `test/shiploop_e2e/head_table.json` (reason in `_comment`) and
`packet_head_table.json` (all four render settings, reason in `_doc`).

## Recorded gaps (CitationTests.BUDGET_GAPS, self-closing)

- plan, both routes: its required text is 19,436 of 20,000 before any lookup (13.5 KB of duties); its guides block is
  2,676 characters. Unresolved before this change too (the plan head carried no lookup at all, not even the symbols).
- ask-agent step-plan: its Backchain route paragraph and lines (2,113) do not fit after 18,442 of required text.
  Unresolved before too.
- Trade on this branch: the inline step-plan head now leaves out the builds-on list and the progress view (its guides
  block is 767 characters); nothing its duties cite by name. U5 (one progress block) and U8 (pointer) free about 1 KB,
  which brings them back; the gap test fails once a gap closes, so the integrator removes the entry then.

## Key learnings

- Labels wrap across duty lines: `label in text` on the raw prompt missed "Reusable test facilities", "Target-native test
  selection" and other guides in most of the 49 unresolved prints the first check found; the match runs on
  whitespace-flattened text now (the guides block and its policies; `_run_rules` keeps its raw-text match elsewhere).
- The head budget is spent by required text, not lookups: plan (19,436) and ask-agent step-plan (18,442) cannot hold
  their citations however the lookups are ordered; ordering only chooses which lookups a tight head keeps. The Backchain
  paragraph before the builds-on list keeps ask-agent carry-forward's paragraph in its head (it fell out 70 characters
  short in the other order).
- The step's criteria belong to the step block; the hand-off now names them by ID in the producer packet only, so the
  Improve hand-off (U2) still quotes them whole and should receive the same step block.
