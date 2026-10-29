---
Execute: ask
---
# ShipLoop trims after the phase A round (plan, 2026-10-28)

The owner asked, after the phase A E2E round: what was redundant, inefficient or ineffective, and should be removed?
This plan drafts the trims. Evidence and run folders are in [the owed-outcome journal](shiploop-owed-outcome-journal.md)
(the arm B results, the owner-note run, the laptop sleep) and in `docs/shiploop-owed-outcome-evidence/`. Code
references are to `origin/main` 35ec5366.

## T1. Remove phase A's owed-text branches; keep its two correctness fixes

**Evidence.**
- In arm B, both stop texts made the loop report in 6 of 6 samples, with nothing redone. The owed-text
  continuations took more commands (median 15 vs 10).
- In 252 active minutes, arm A never stopped.
- The one real early stop of the round (owed 3, first try) came after implement was accepted, at the Improve packet.
  Replayed on that run, `hook-status` gives `loop: {}` and `_owed_report` gives `""`. So phase A's text would have
  printed the old "run `next`" sentence word for word.
- That old sentence is what arm B's `hook-generic` samples ran live, 3 of 3.

**Remove:**
- `shiploop_keepalive._owed_report`. `_continue_reason` goes back to the one generic ask; the background-task and
  host-cap sentences stay.
- In `shiploop_protocol.hook_status`: the `callback` field, `owed_action`, the `delegation` field (only the owed text
  read it), and the loop's `kind`, `status` and `next`.
- `navigator.complete_command`: hook-status was its only caller.

**Keep:**
- `progress` = `<revision>.<callback attempts>.<loop iteration>`, so a model that reports iterations is never
  released as idle. `_loop_receipt` shrinks to the iteration it reads.
- `STOP_MEMORY` on a re-bind of the same run, so running `next` no longer wipes the stop's memory
  (`rebind_repro.out`).

**Docs and tests:**
- `references/keepalive.md`: the hook-status row and the stop-table row lose the owed wording.
- `OwedReportTests` (3 tests) go.
- `shiploop-loops`, `test_the_stop_hook_names_the_loops_report_then_the_steps_own_callback`, becomes: on a real run,
  the stop asks for `next`, and each reported loop iteration moves `progress`.
- The progress and re-bind tests stay as they are.

**Change note.** shiploop 1.18.0 (release `6828acb9`, 16:40, after this plan was drafted) already shipped the owed
text and consumed its note. So T1 adds a new note, `changes/shiploop/stop-hook-asks-next.md`, `bump: minor`: it
removes `hook-status` fields.

## T2. Drop the per-field test-layer limits; keep the aggregate

**Evidence.** 6 refusals in two runs came from `shiploop_test_layers.FIELD_LIMITS` (code 60, harness 80, reason 160,
target 60, base_state_route 240). Examples: a 61-character target, a 176-character reason, a 293-character
base_state_route. Each one cost a rewrite and a resubmit.

The comment on `FIELD_LIMITS` says these limits keep the printed Test layers and Test targets lines inside the
step-plan head. The module already refuses those lines once they pass `TEXT_LIMIT` (1,200 characters together), and
that aggregate is the bound the head needs.

**Change:**
- Delete `FIELD_LIMITS`: its use in the row and target parsers, and its `__all__` entry.
- `TEXT_LIMIT` stays as it is.

**Tests:**
- A 300-character base_state_route is accepted while the lines fit within 1,200.
- The aggregate still refuses at 1,201.
- The status-card tests quote the old refusal only as sample text, so they are unaffected.

**Change note.** `changes/shiploop/test-layer-field-limits.md`, `bump: patch`.

**Not touched:**
- The step-level bounds (criteria, concern rows, decisions, context), which caused 5 refusals. The owner kept the step
  bound as shipped (35ec5366, E-SIZE1).
- `HEADLINE_LIMIT` (100; 2 refusals). It is a one-line display field.

## T3. The live packet check covers every print (harness only)

**Evidence.**
- `run_trace.checks` `packet_reprint` counts only identical reprints (same action, same hash). It was exercised once
  in 8 runs, by a `done` packet.
- The reprint a fresh session gets from `next` is a different text (+52 characters), so it is never checked.
- The Run Review page reads the kept copy of every print.

**Change:**
- Verify every packet event's kept copy (`file` exists and its text hashes to `sha`), and report prints and reprints.
- Rename `packet_reprint` to `packet_copies` in one commit everywhere: `run_trace.py`, `status_card.CHECK_LABELS`,
  `test/shiploop_e2e/README.md`, `shiploop-e2e-run-trace` and `shiploop-e2e-status-card` tests, and the journal
  (consistent-nomenclature rule).
- Tests: a missing or altered copy of a print that isn't a repeat fails.
- No change note: the change is in `test/` only.

## T4. Harness branch before it merges

On `feat/e2e-hook-text-232e69`:
- Drop the `hook-owed` and `hook-generic` resume conditions (`fd65120f`). After T1, both print the same text as
  `names-next`.
- Keep the seed guard (`b2a53912`) and a clear's release of the keepalive owner (`c8bcb464`).
- The round's evidence stays in the docs.

## Dropped after a closer look

- **Improve `--check-only` as a notice.** The refusal already prints the exact command to run next, so exiting 0
  would save no call; it would only change a metric.
- **Scaling Improve to the request's size.** hello took 8 reviews and 17 passes, and all the findings were in the
  run's own records. Battleship's reviews found a real contradiction in its spec. Whether to scale reviews to the
  request is the owner's design call, not a trim.

## Order and verification

1. **Finish the round first:** regrade arm A with main's `run.py --grade-only`, write the LEARNINGS entry, and commit
   the journal and evidence.
2. **One worktree from `origin/main`:** T1 and T2, each in its own commit with its change note and a verbose message
   that cites this plan and the evidence files. Then T3 and T4 on the harness branch, rebased.
3. **Tests:**
   - `shiploop-keepalive`, `shiploop-loops`, the suites over `shiploop_test_layers`, `shiploop-e2e-run-trace`,
     `shiploop-e2e-status-card` and `shiploop-e2e-slice`;
   - then `run-all.sh --group quick --changed-from <merge-base>`;
   - and lint on the changed files.
4. **No new E2E round.** T1 returns to the text arm B ran live. T2 removes refusals and adds no behaviour. This
   follows the "scale ceremony to measured gain" rule.
5. **Then the owner's release decision.** The next release ships T1's and T2's notes. The three phase A notes already
   shipped in 1.18.0.

Approved by the owner, 2026-10-28 ("Approve the plan").
