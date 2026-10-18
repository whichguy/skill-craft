# Journal row: u6-gates, packet-review units U6 (gates stated) and U8 (stale lines) (2026-10-17)

**Consumer.** The integrator who merges `feat/pr-u6-gates-39d53a` into the integration branch and re-measures the head tables.
Plan: [docs/shiploop-packet-review-plan-2026-10-17.md](../../../shiploop-packet-review-plan-2026-10-17.md) section 2, U6 and U8,
with owner decision D4. Base: `03c5edbc`.

- date: 2026-10-17
- status: firm for the text, the gates and the tests (each refusal is submitted through the real `complete`); interim for the
  sizes (offline renders and synthetic runs, no model); not measured: a live run.
- question: can each refusal of the 2026-10-17 run, and the release-plan gate its model learned only by reading ShipLoop's
  scripts, be stated in the packet before the gate refuses, with a refusal that names the way out? And can the stale or
  platform-irrelevant lines the reviewers showed misled the run go?

## Change

| Finding (reviewer file) | Change | Symbols |
|---|---|---|
| Refusals 3 and 4: authority operation, then target, differ from the contract's (A1-1) | The authority's target and operation are the contract's: the templates leave them out, `_authority` fills them in; given, they must match, and the refusal says to leave them out | `shiploop_consumer_delivery._authority`, `_contract`, `template_assessment` |
| release-plan's delivery-necessity gate not in Checked-by, no template field; 34 source reads (E G33-1, C-2) | Checked-by names the gate while the contract is unsettled; the template carries the replacement contract (supersedes, correction, a required effect, identity and behavior row per missing kind; necessity, an unapproved status and the correction's reference are placeholders the gate refuses); release-plan's own `complete` and `--check-only` refuse an unsettled contract (before: only at the Improve import); the invalid-necessity and invalid-status refusals list the accepted values | `_unsettled`, `_settling_template`, `checked_lines`, `_require_settled`, `validate_settled`; navigator `_stage_gates`, `_check_submitted_delivery` |
| Refusal 1: `--notes` given text (A9-1) | `--notes FILE` help says it takes the path of a file; the refusal says "take the path ... not the text" and names the file the handoff names | `shiploop_protocol` `--notes`; navigator `_optional_text_file`, `improve_notes_path` |
| Refusal 5: "navigator result is unavailable" (D-8, D-9) | Verify duty 1: write the result to `RUN/inbox/<action>.md`, then run `--check-only`, which reads it; the refusal: `no result file at <path>: write the result there (the packet's Result template, filled in) ...` | `DUTIES["verify"]`; navigator `_submitted_result` |
| Refusal 2: a recorded command failed at verify (D-10, real defect) | No gate change: the test pins that check-only reports it first and that duty 1 routes through check-only | test only |
| release-verify Checked-by says "every recorded test command" but reruns release-plan's empty consumer_checks (F-14) | The outer reruns name their list and count: `reruns the N command(s) in <source>'s <field>`, or `reruns the commands in <source>'s <field>: none recorded, so none runs` (system-test too) | navigator `_check_text` |
| Pointer's "or you need the duties or the template" (AX-4, C-4) | Dropped | `shiploop_prompts.packet_pointer` |
| `# ShipLoop navigator result` template heading (D4; AX-5, DX-3, C-6, X-3) | Dropped from the template (and its too-large fallback); `results/*.md` records keep `store.dumps`'s heading | navigator `_compact_record`, `_result_contract_lines` |
| "ambitious, highly interactive" UI default against a request for a simple one (A8-1) | The UI takes the ambition the request states; rich is the default only when it states none (plan item 8, step-plan's interaction bullet, the Plan record guide) | `DUTIES["plan"]`, `_PLAN_RECORD_INTERACTIONS`, `references/plan-record.md` |
| Module format on a platform with none: filler written (A8-2) | Plan item 13 asks for the format only where the language has more than one | `DUTIES["plan"]` |
| Improve example for Claude Code on a Grok host (A5-1, D-17) | Host-neutral: the argument on its own line, then the host's skill call (the Skill tool, or /improve) or the card, on equal terms | navigator `improve_packet` (the three invocation lines only) |
| Rollback recipe with `git -C <checkout>` beside "never this run's absolute paths" (G33-3) | Plain `git` run from the repository root | `shiploop_workspace.rollback_lines` |
| "Deploy not to unblock a test" while 3 of 4 recorded commands deploy (G31-1) | "Add no deploy to unblock a test (a recorded command's own deploy step runs as recorded)" | `DUTIES["system-test"]` |

Not changed, on purpose (conservative, KISS): the MCP, async and service duties of discovery, research, spec and plan (A2-2,
AX-7). The reviewers showed them ignored or dead text, not misleading a run, and the run records no structured discovery
fact to gate them on. Spec item 8 already says to mark an inapplicable concern in one line.

Readers updated in the same commit: `skills/shiploop-run-review/scripts/export.py` (`IMPROVE_COMPACT_HANDOFF_RX` reads both
Improve-line forms), `test/shiploop_e2e/packet_anatomy.py` (callback rule), and the
`full-packet-pointer` row's description in `test/shiploop_e2e/packet_obligations.json`, whose anchors are unchanged. Docs:
`references/consumer-delivery.md`, `navigator.md`, `plan-record.md` and `workspace-lifecycle.md`. Change notes:
`changes/shiploop/packet-review-gates-stated.md` (minor) and `changes/shiploop-run-review/improve-packet-host-neutral-line.md` (patch).

## Fail-first record

The six new route tests were run with only the five ShipLoop script sources reverted to `03c5edbc` (`git checkout 03c5edbc --
shiploop_consumer_delivery.py shiploop_navigator.py shiploop_prompts.py shiploop_protocol.py shiploop_workspace.py`), then
restored from saved copies:

- `test/shiploop-callback-contract.test.py PacketReviewRefusalRouteTests` (5 tests): FAILED (failures=5, errors=2). The intake
  template still carried `'target': '...'`. Verify duty 1 lacked "write the result". The check-only test hit a ValueError, because
  duty 1 has no `1. **Run.**`. release-plan had no `delivery_assessment` in its template, an error. Each of the three outer-rerun lines
  read "reruns every recorded test command".
- `test/shiploop-actual-improve-cli.test.py -k test_notes_given_as_text`: FAILED, because the help printed `[--notes NOTES]`.

With the sources restored, all six pass.

## Suites (each once after its last relevant edit; counts are tests run, all OK on the final tree)

Batch 1: head-order 33, packet-recut 30, step-packets 9, packet-obligations 15, reference 8, reference-routing 4,
consumer-delivery 29, loops 51, quality 11, improve-schedule 33, e2e-packet-anatomy 29, keepalive 60, e2e-commit-counters
107, return-review 24, callback-contract 77, test-loop 143 (it pins verify duty 1).
Batch 2: packet-bounds 10, packet-completeness 62, delegation 59, navigator-contract 110, run-review 658, discovery 8,
navigator-v4 18, e2e-render-diff 43, actual-improve-cli 82. Batch 1 had also run packet-bounds, packet-completeness,
delegation, navigator-contract and run-review. They failed (1, 9, 19, 8 and 1) on pins of the old Improve invocation line
(`/improve ShipLoop Improve:`, `result.`). Those pins were updated, and the five suites, with discovery and navigator-v4 (same
pins) and e2e-render-diff (its table changed), were run once more, green.

Skipped: run-all and every group run (test economy: the integrator runs one `quick --changed-from`); live E2E; the other E2E
suites; the suites with no pin on the changed text (`git grep` of each changed string and symbol).

## Render sizes

Offline `node-fix-bug`, inline/83/96 (`packets.py --offline`, `render_diff.py --unit U6`), printed then whole, before to after:
step-plan 19,673 to 19,943 (+270: the 68 freed characters let its 338-character pause line into the head, which is still under
the 20,000 cut) and 24,327 to 24,259; test-spec 15,486 to 15,418; validate-existing 12,821 to 15,998 (its file fell under
PRINT_LIMIT, so it now prints whole: 16,040 to 15,972); implement 16,040 to 15,972; test 18,004 to 17,936; document 15,008 to
14,940; verify 18,393 to 18,433 (+40: duty 1); carry-forward 14,033 to 13,965. The offline Improve packets are unbound, so they
do not change.

The reference install (`test/shiploop_head_budget.py`, both routes) gives -68 on every inner producer print, +40 at verify, and
inline step-plan +270 (19,943). Every head is at or under 20,000. `head_table.json` and `packet_head_table.json` (all four
keys) are updated to these values, with the reason appended.

Outer stages, from a synthetic run through the real `next`, at this machine's paths: -68 at every outer stage except plan +82
(items 8 and 13), system-test +17 (its count line and item 2), release-verify -48 (its count line) and spec. spec's file fell
under PRINT_LIMIT, so it now prints whole: printed 12,355 to 15,974, file 16,016 to 15,948. With a delivery contract, intake
is -105 (no authority target or operation) and release-plan +1,390 (the settling template), 14,539 printed. The bound Improve
packet's invocation lines are +30.

## Key learning

The release-plan delivery gate did not run at release-plan's own `complete`. release-plan is an Improve checkpoint, so
`apply` parks the result and `validate_transition` runs only at the Improve import. A Checked-by line saying "at done
ShipLoop refuses" would have been false for it. The necessity and the authority are the stage's decision, not the review's,
so they are now refused at the stage's complete and check-only (`validate_settled`). The pre-update observations stay at the
import, because the reference lets the review refresh them. The second learning: the Improve invocation line had readers in
about 12 test files and the run-review export, all keyed on `/improve ShipLoop Improve:`. The host-neutral line is
`       ShipLoop Improve: <handoff>`, and readers now match the argument prefix at its indentation.
