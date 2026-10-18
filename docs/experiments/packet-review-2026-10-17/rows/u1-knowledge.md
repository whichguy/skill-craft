# Row u1-knowledge: knowledge by locator (U1), the request by its file (D2), a slim Improve handoff (U2)

- Date: 2026-10-17. Status: **interim** (offline renders and hermetic suites only; the live run of plan section 3.3 is the
  firm measure).
- Branch `feat/pr-u1-knowledge-bdf42c`, base 03c5edbc. Plan: [shiploop-packet-review-plan-2026-10-17.md](../../../shiploop-packet-review-plan-2026-10-17.md)
  section 2 (U1, U2) and section 4 (D1, D2).

## Question

Can every packet name the knowledge files and the original request by locator, and every Improve handoff name the producer's
packet and result, without losing an obligation, while the packet text falls by at least 40% and the handoff to 12 KB?
Findings: A AX-1, AX-3; B BX-2, BX-3 (B1-4, B2-2); C X5 (C2-9, C2-16); E C-3; F X-2 (F-2, F-5, F-10, F-12).

## Change

- `shiploop_knowledge_home.outline` (new) and `shiploop_navigator.reads_lines` / `READS_HEAD`: each file a stage reads is
  listed by path, size and table of contents (every heading outside code fences; an entry that is a heading folds into its
  section by its heading text; list and table entries as ID ranges, `R-1..R-6`; at most 40 sections). No file text is
  quoted. `reads_pointer` (no caller) is gone.
- `_followed_lines`: every followed R-<n> / AD-<n> entry is quoted by value (the rows the stage follows; `step_scope` still
  cuts them to an implement step). The "quoted whole above" / "in the diff below" ID form and `_diff_printed_files` are gone.
- `_spec_diff_lines` / `_new_file_pointer` (and `_is_pointer_chunk`, folded in): a file new since the baseline is a pointer
  with its size and contents (or "its contents are listed above" when the same packet lists it), at every stage; a file that
  existed at the baseline keeps its hunks uncut. `SPEC_DIFF_NOTE` says so.
- D2, `_run_rules` via `_request_lines`: the request is quoted whole at `REQUEST_WHOLE_STAGES` (intake, spec, plan); every
  other packet prints `REQUEST_POINTER` (RUN/request.md). The Improve handoff adds
  `shiploop_consumer_delivery.exclusions_lines` (new) beside it; a producer packet does not (its delivery block prints it).
- U2, `improve_handoff_text` via `_reviewed_input_lines` (new) in place of `_consumer_lines`: the handoff names the
  producer's packet `RUN/packets/<action>.md` and result `RUN/inbox/<action>.md`, the knowledge files with their sizes and
  the hand-off keys; it keeps the handed criteria by value (C2-16); on a revisit (`_sent_back_results`) it names the previous
  accepted result and the revise result.
- Wording that described the old form: `shiploop_prompts.packet_pointer` ("it also holds the hand-offs, the knowledge files'
  contents and the request or its file"), `shiploop_request` docstring and `RUN/request.md` intro, SKILL.md print-order
  sentence, docstrings. `test/shiploop_e2e/metrics.py` (QUOTE_START, QUOTE_FILE, QUOTE_STOPS) and `packet_anatomy.py` read
  the new lines.

## Fail-first (sources reverted to 03c5edbc, tests kept)

| suite (selection) | without the change | with it |
|---|---|---|
| shiploop-handoff (ContentsTests, SameBlockDuplicateTests, RequestAndReviewedInputTests, StepScope U2 test, QuotedBelow test-strategy, WalkedBlockTests; 20 tests) | 46 failures, 16 errors | OK |
| shiploop-consumer-delivery `test_a_packet_that_names_the_request_by_its_file_keeps_the_exclusions_line_once` | error (no `exclusions_lines`) | OK |
| improve-route `test_what_is_the_same_in_every_review_left_the_handoff_for_the_route` | 18 errors | OK |
| shiploop-e2e-efficiency (long-home sizes, metrics quote regions) | 1 failure, 1 error | OK |
| shiploop-packet-recut (OwnerLines, pointer pins) | 40 failures, 1 error | OK |
| shiploop-navigator-contract `test_platform_testing_contract_routes_to_every_test_stage` | 1 failure | OK |

## Suites run once after the last edit

improve-route 17, shiploop-consumer-delivery 30, shiploop-e2e-efficiency 75, shiploop-handoff 98, shiploop-navigator-contract
110, shiploop-packet-recut 30, shiploop-e2e-packet-anatomy 29, shiploop-knowledge 135, shiploop-head-order 33,
shiploop-packet-bounds 10, shiploop-packet-completeness 62, shiploop-packet-obligations 15, shiploop-step-packets 9,
shiploop-delegation 59, shiploop-loops 51, shiploop-reference 8, shiploop-reference-routing 4, shiploop-discovery 8,
shiploop-guidance 63, shiploop-improve-schedule 33, shiploop-navigator-v4 18, shiploop-quality 11, shiploop-rehydration 17,
shiploop-v4-consumers 5, shiploop-keepalive 60, shiploop-actual-improve-cli 81: all OK.
shiploop-e2e-render-diff 43: 1 failure, `test_the_cli_path_has_exactly_the_stated_length_and_the_default_prints_the_bare_name`
(the inline step-plan head carries 2 CLI commands, not 3: its pause line is past the head); it fails the same way at
03c5edbc, and this change leaves that head byte-identical.

Skipped: shiploop-callback-contract and shiploop-test-loop (no loop block, path notation or `shiploop_test_loop.py` change);
run-all, the full tier and live E2E (test economy policy; plan section 3.3 is the live check).

## Render sizes (packets.py --offline node-fix-bug, run dir 83, CLI 96; render_diff.py)

The node case has an empty knowledge home, so only D2 (about 406 characters per producer packet) applies to it.

| stage (inline) | printed before | printed after | whole before | whole after |
|---|--:|--:|--:|--:|
| step-plan | 19,673 | 19,673 | 24,327 | 23,921 |
| test-spec | 15,486 | 15,080 | 15,460 | 15,054 |
| validate-existing | 12,821 (head) | 15,660 (whole) | 16,040 | 15,634 |
| implement | 16,040 | 16,062 | 19,087 | 18,681 |
| test | 18,004 | 18,026 | 20,759 | 20,353 |
| document | 15,008 | 14,602 | 14,982 | 14,576 |
| verify | 18,393 | 18,415 | 21,137 | 20,731 |
| carry-forward | 14,033 | 14,033 | 18,708 | 18,280 |

ask-agent/83/96 heads: +22 where the knowledge block is printed (its head line, 128 characters for 107), step-plan 19,790
and carry-forward 15,299 unchanged; wholes -406 to -428. Tightest head at 163/96: inline step-plan 19,886 (unchanged).
Every head is below 20,000 at the reference install (shiploop-packet-recut, test/shiploop_head_budget.py).
render_diff with this row's allowlist ([u1-knowledge-allowlist.json](u1-knowledge-allowlist.json), `--unit PR-U1 --changes`;
`packet_changes.json` holds the efficiency plan's U1..U35 only and its test pins that): every added line is allowlisted but
`- none` (6 characters, under the 8-character prefix minimum) in validate-existing inline/83/96, which now prints whole; the
head-table check fails only at step-plan ask-agent/83, inline/163 and ask-agent/163, whose values predate 603a709c (+117
unjournaled there) and which this change does not move.

Packet text by walk (`len`; measure script in the session scratchpad):

| walk | producer text before | after | change | Improve handoffs before | after |
|---|--:|--:|--:|--:|--:|
| node-fix-bug, empty home | 150,500 | 147,230 | -2.2% | 15.8-21.2 KB | 15.3-20.8 KB |
| node-fix-bug, long home (16/14/6 KB, first run with a baseline) | 390,748 | 155,744 | **-60.1%** | 42.2-56.3 KB | 15.2-20.7 KB |
| dry-run delivery graph, long home (home_fixtures) | 836,944 | 408,792 | **-51.2%** | max 60.3 KB, sum 373 KB | max 22.3 KB, sum 168 KB |

The printed heads of the long-home walks grow (+8.5%, +10.9%): the knowledge contents and the hand-offs now fit the head
(BX-2: before, the step's own criteria fell out with the quoted files), bounded by HEAD_LIMIT.

Handoff floor (node implement, after): opening 1.4 KB, review focus 2.3, commit 0.85, Code craft 3.7 (D3 keeps it), what the
stage worked from 4.9, the review rules 7.5. The 12 KB exit needs the review rules or Code craft cut, outside U2.

## Exit items

- Packet text down at least 40%: **met** on both long-home walks (-60.1%, -51.2%); **not met** on the empty-home node case
  (-2.2%: it has no knowledge file to stop quoting).
- Improve handoff at most 12 KB: **not met** (15.2-22.3 KB); the "worked from" part fell from 21-66 KB to 4.3-5.6 KB.
- packet-obligations green: met (15 OK; no obligation row names a knowledge quote or the request).
- Every head at most 20,000 at the reference install: met (largest 19,886).

## Key learning

The knowledge quotes were most of every long-home packet and handoff; a table of contents plus the followed entries by value
keeps what a cleared stage needs to choose what to open, at about 1.5 KB for the recorded run's three files (56.8 KB whole).
The handoff's remaining size is its own review rules, not the producer's sources.
