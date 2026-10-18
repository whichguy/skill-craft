# U5 (u5-progress): one progress block per packet

- **Date:** 2026-10-17. **Status:** firm (offline renders and suites); a live run still has to show it on a host.
- **Base:** 03c5edbc (branch `feat/pr-u5-progress-0a2c5d`).
- **Finding:** F6 of [the plan](../../../shiploop-packet-review-plan-2026-10-17.md#1-what-the-review-found), from
  [X-status-narrative.md](../X-status-narrative.md), [E-system-test.json](../E-system-test.json) C-5 and
  [F-release.json](../F-release.json) X-4.

## Question

The chess run's packets carried the status block and the narrative side by side in 28 of 36 packets. They repeat each
other: Where is Now, Done is Achieved, Next is Ahead. 8 of the 11 Improve packets also carried a narrative, although the
reference says narratives appear only at milestones. Why did the Improve packets carry one, and can each packet carry one
progress block while the Claude CLI hook still shows a two-line summary?

## Cause of the Improve narratives

`narrative_facts` decides a milestone from the last accepted step (`state["history"][-1]`). An Improve child does not
change that step: the result it reviews is accepted only when the child completes. So an Improve packet always met the
same milestone test as the producer packet before it and repeated its narrative. In the run, 05, 07, 09, 12, 23, 28, 30
and 34 repeated the narrative of 04, 06, 08, 11, 22, 27, 29 and 33. The other producer packets without a narrative (13,
17, 19, 24, 25) were right: none of them followed a milestone step.

## Change

- `shiploop_navigator.narrative_facts`: an active run with a parked Improve child is not a milestone. A stopped run is
  one, child or not.
- `shiploop_navigator.progress_lines` (new): the narrative at a milestone, else `status_line`. It replaces
  `status_block(state), "", *narrative_lines(...)` in `_producer_blocks` (the "status" block) and in `_render_lines`
  (paused, blocked, halted and done packets, which are all milestones).
- `shiploop_navigator.status_line` (new): `Where: <where> · Next: <next>`, the status block's own Where and Next rows.
  `status_block` is refactored onto the shared helpers `_status_phase`, `_status_item_name`, `_status_where` and
  `_status_next`, and its output is byte-identical (the status-display block pins pass unchanged). `status.md` and
  `shiploop status` still print the full block.
- `shiploop_navigator.improve_packet`: the untrusted-text line, the status block and the narrative are gone. The
  Keepalive marker stays.
- `shiploop_navigator._last_accepted_lines`: the summary prints even when it is as short as a headline. U13 left it out
  because the packet's Done row repeated it, and that row is no longer in the packet. This is file-only text in a
  producer packet.
- `shiploop_status_hook`: `LINE` (new), `packet_progress` (new: the one narrative or status line inside `WINDOW`; none
  when there are two), `progress` (replaces `status_block(payload)`: the block for `status`, else `packet_progress`),
  `compact` (also reads the status line) and `status_message` (narrative text at a milestone, else `compact`).
  `shiploop-status-hook`: the shell gate passes on `ShipLoop navigator | ` or `=== ShipLoop status ===`. Before, it
  passed only on the status block, so a narrative-only packet would never have reached Python.
- `shiploop_prompts.PROGRESS_REPORTING` (reference#progress), `SKILL.md`, `references/status-display.md` and
  `references/navigator.md` now describe one progress block.
- E2E harness: `counters.head_or_why` measures a head by its closing line without needing a status block. Before, it
  returned "ends before the closing line" for every head of the new layout, so `head_bytes` would have been null in
  every run. `packet_anatomy` classifies the status line as `status-block`.
- Ledger: the `keepalive-status` row keeps the keepalive marker for producer and Improve packets. A new `progress` row
  (producer) requires the narrative or the status line. The reason is in both rows.

## Fail-first record

Each new or changed test was run with only its source piece reverted, then with the piece restored:

| Reverted source | Test | Result with the revert |
|---|---|---|
| the whole change (base source, new tests) | shiploop-status-display, shiploop-narrative | 4 errors; 2 failures + 1 error |
| the `active_improve` milestone condition | narrative `test_an_improve_stage_is_never_a_milestone_and_its_packet_carries_no_progress` | FAIL `True is not false` |
| the shell gate (status block only) | status-display `real_calls`, `payload_shapes` | 7 errors (the narrative and status-line packets show nothing) |
| the improve_packet blocks restored | the narrative Improve test; status-display `every_dry_run_packet...` | FAIL (status block in the Improve packet; inline delivery 5, 7, 9, …) |
| producer packets print status block + narrative | shiploop-packet-obligations | 3 FAIL (the `progress` row's token is missing from the non-milestone packets) |
| the anatomy status-line rule | packet-anatomy `status_line...` | FAIL `'unclassified' != 'status-block'` |
| `counters.head_or_why` unchanged, new packets | commit-counters `a_head_printed_by_this_layout...` | FAIL on every head (`the reply ends before the head's closing line`) |

## Offline render (node-fix-bug, `packets.py --offline --text-dir`, run dir 83, CLI path 96)

Progress blocks per packet. Before: 12 status blocks and 8 narratives in 12 packets, so 0 of 8 producer packets had
exactly one block and 0 of 4 Improve packets had none. After: 0 status blocks, 5 narratives and 3 status lines, so 8 of 8
producer packets have exactly one block (found by `packet_progress`) and 4 of 4 Improve packets have none. The same
holds at run dir 163 and on the ask-agent route.

Printed text (head, or whole when it fits 16,000) and whole text at the reference install (`shiploop_head_budget`,
inline / ask-agent):

| stage | printed before → after (inline) | whole before → after (inline) | printed before → after (ask-agent) |
|---|--:|--:|--:|
| step-plan | 19,673 → 19,965 (head) | 24,239 → 23,852 | 19,790 → 19,315 |
| step-plan Improve | 2,384 → 1,045 | 2,384 → 1,045 | 2,384 → 1,045 |
| test-spec | 15,372 → 15,188 (whole) | 15,372 → 15,188 | 13,059 → 12,787 |
| test-spec Improve | 1,616 → 1,045 | 1,616 → 1,045 | 1,616 → 1,045 |
| validate-existing | 15,952 → 15,597 (whole) | 15,952 → 15,597 | 12,821 → 12,378 |
| implement | 16,040 → 15,642 (head) | 18,999 → 18,689 | 17,494 → 17,096 |
| implement Improve | 2,325 → 1,045 | 2,325 → 1,045 | 2,325 → 1,045 |
| test | 18,004 → 17,732 (head) | 20,671 → 20,487 | 18,004 → 17,732 |
| document | 14,894 → 14,737 (whole) | 14,894 → 14,737 | 12,277 → 12,032 |
| verify | 18,393 → 18,001 (head) | 21,049 → 20,745 | 18,813 → 18,421 |
| carry-forward | 14,033 → 13,615 (head) | 18,620 → 18,290 | 15,299 → 14,881 |
| carry-forward Improve | 2,313 → 1,049 | 2,313 → 1,049 | 2,313 → 1,049 |

All printed text in the text-dir render: inline 139,748 → 136,493, ask-agent 137,839 → 130,305. Whole text: inline
160,704 → 153,874, ask-agent 178,289 → 171,459.

The inline step-plan head rises by 292 to 19,965, 35 under the 20,000 cut. `_select_head` fills the room the progress
block freed with the next optional blocks (the quoted knowledge stubs, the hand-off line and the pause line). In the
text-dir render, validate-existing inline (15,685 whole) now fits the 16,000 print limit and prints whole. `head_table.json`
and `packet_head_table.json` take the new values, with the reason in `_comment` and `_doc`.

`render_diff.py OLD NEW --unit U5` lists the changed lines: the status block lines removed, the `Where: … · Next: …`
line and the last-accepted summary lines added, and the print-form lines from the two heads that changed shape. It
exits 1 because `packet_changes.json` has keys only for the efficiency plan's units, and this unit added no key, to avoid
a conflict with the other packet-review units. The integrator decides whether the review units get allowlist keys.

## Suites (each once after the last edit, `SHIPLOOP_PROGRESS=off python3 -B test/<name>.test.py`)

All OK: status-display 16, narrative 12, keepalive 60, head-order 33, packet-recut 30, packet-bounds 10,
packet-completeness 62, packet-obligations 15, step-packets 9, delegation 59, loops 51, navigator-contract 110, reference
8, reference-routing 4, test-loop 143, e2e-commit-counters 107, e2e-packet-anatomy 30, handoff 97, e2e-render-diff 43.
head-order and step-packets failed their first run: head-order's `hooks_still_read` pinned `hook.BEGIN`, and
step-packets pinned an Improve packet naming the item, which it did only in its status block. Both suites passed when
rerun once after the fix.

Skipped: `shiploop-callback-contract` (it reads only the hook's `_verb`, which did not change; the loop block, path
notation and `shiploop_test_loop.py` did not change). `shiploop-e2e` (no reader of `counters.head_or_why` or the status
block; its narrative fixture reads `metrics.NARRATIVE`, which did not change). `shiploop-progress-render` and
progress-data (`status_block` output is byte-identical; `narrative_facts["milestone"]` is not read there). No
`run-all.sh`, no live run.

## Key learning

A milestone test that reads "the last accepted step" counts every packet issued before the next acceptance, Improve
packets included. That is why the reference and the run disagreed. A display rule needs a test on the packets
themselves: exactly one progress block, and none in an Improve packet, over the dry-run graph walk. A test on the
facts function alone was not enough. Two readers of the old block would have broken silently: the hook's shell gate
(it would have shown nothing at a narrative-only milestone on the Claude CLI) and the E2E head counter (it would have
recorded `head_bytes` null for every head).
