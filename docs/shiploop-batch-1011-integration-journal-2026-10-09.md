# Batch 1011 integration journal (2026-10-09)

Living journal of the integration branch `batch1011-integration-aaa47e` (worktree `.claude/worktrees/b1011z-aaa47e`) of the
harness batch planned in `docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md`. Base `30a3b40a`; groups merged one at a
time with `git merge --no-ff`, each conflict resolved so that both sides' behaviours and tests survive, then the duplicates the
group reviews found are unified, each with a failing test first. Harness only: nothing under `skills/`, `agents/` or `plugins/`
changes, so no change note and no release. Status words: firm (a test or a recomputed figure), interim, exploratory, superseded.

Group journals: G1 `docs/shiploop-batch-1011m-g1-fidelity-journal-2026-10-09.md`, G2
`docs/shiploop-batch-1011n-g2-reorientation-journal-2026-10-09.md`, G4 `docs/shiploop-batch-1011o-g4-environment-journal-2026-10-09.md`
(G3 and G5 not merged yet).

## 1. Merges

| Merge | Commit | Group head | Conflicting files (hunks) |
|---|---|---|---|
| G1 fidelity record | `cee214aa` (made before this journal) | `d46bdc9e` | none recorded here |
| G2 clear-context re-orientation | `6ff8ffb8` | `ceebbe17` | metrics.py (9), SPEC.md (1), README.md (1), LEARNINGS.md (1), suite_catalog.py (2); test-groups.test.py merged textually but wrong |
| G4 environment, product at stop, outcome class | `1c0a7c8d` | `35aef538` | run.py (3), metrics.py (1), runrecord.py (1), README.md (1), LEARNINGS.md (1), suite_catalog.py (2), test-groups.test.py (2) |

### What was kept, per hunk class (firm: every suite of the family green after each merge, section 4)

- **`metrics.py`, the tool-call reader (G1 against G2, 9 hunks).** G1 added an `event=` argument to `ToolLog.call` and
  `ToolLog.result`, `ToolLog.sequence`, `ToolLog.failure_events`, `target_paths`, `within`, `NOT_APPLICABLE` and
  `collect(..., tools=)` (fidelity.py fills its own log through it). G2 extracted `ToolLog.feed`, `tool_call_events`,
  `cancelled_update` and `call_target`, made `call` return its key, and added `failure_of`, `answered` and the windows
  (`reorientation`, `fresh_starts`, `call_kind`, `_grounding`). Kept: **one feed path**, `ToolLog.feed(event, t, number=None)`,
  which passes `event=number` to `call` and `result`; `collect` calls `tools.feed(event, t, number)` and keeps G1's `tools=`; the
  windows call `tools.feed(seen, t, line)`. G1's inline call/result branches in `collect` are gone (G2's extraction covers them),
  and `collect` uses `cancelled_update`. **One target reader**: `call_target(arg)` returns the first of G1's `target_paths(arg)`
  (target_file, file_path, path, then Codex's `paths`), so a call's `file` in `ToolLog.calls` and G2's `written_paths` cannot
  differ. `within`, `call_kind` and `_grounding` each exist once (no side had a duplicate).
- **`metrics.py` (ours against G4, 1 hunk), `runrecord.py` (1 hunk).** Two functions added at one place each (`engine_position`
  and `blocked_detail`; `launch_epochs` and `unreadable`): both kept.
- **`run.py` (ours against G4, 3 hunks).** Imports: environment, fidelity, runrecord, sessionlog all kept, alphabetical. G2's
  `events_line_count` and G4's `resume_identity`, `launch_stamp`, `display_held`, `declared_needs` added at one place: all kept.
  Read through the textually merged rest: G2's `session()` bracket (sessions.jsonl) wraps the launch whose record and prompt file
  G4 names with `launch_stamp`; G4's start record is taken before it; neither reads the other's state.
- **SPEC.md, README.md, LEARNINGS.md.** Every hunk was "added in both places" with an empty base: both kept, in group order
  (G1, G2, G4); the SPEC rules stay one list, and G4's SPEC rows and amendments merged textually into the clauses table, the
  Parallel work section and the rules list (read in the merged diff).
- **`suite_catalog.py`.** Both sides' suite paths and durations kept (fidelity 9.0, reorientation 7.7, environment 65.0; G4's
  entry had no comment and got one from its journal).
- **`test-groups.test.py` pinned counts.** Each branch made the identical 70->71 / 111->112 edit, so the G2 merge was textually
  clean and wrong. The pinned numbers are the real catalog, computed from `suite_catalog` after each merge: 72/113 after G2,
  73/114 after G4.

## 2. Unified readers

### (a) One blocked-detail reader (firm)

`metrics.blocked_detail(state: dict) -> {"blocked_by", "awaiting_kind", "awaiting_no_default"}` (G4) is the one reader. G1's
`fidelity.end_state` read the same fields through a private `_blocked_reading(last)` with no status guard, so a block that was
answered (engine `active`, last history entry `blocked`) read the old result's `blocked_by` (`user`). `end_state` now calls
`metrics.blocked_detail` and maps it to its own shape (`blocked_by`; `awaiting` = `{kind, no_default}` when
`awaiting_no_default` is not None, else None); `_blocked_reading` is deleted; `status`, `stage`, `unaccepted_stage`,
`status_reason` and `unverified` are unchanged.

- Tests first, both red before the change: `EndStateTest.test_an_answered_block_reads_as_no_block` (was `('active', 'user',
  {'kind': 'answer', 'no_default': True})`) and `test_the_blocked_fields_come_from_the_one_shared_reader` (no
  `_blocked_reading`; a patched `metrics.blocked_detail` drives `end_state`). After: fidelity suite 142 OK.
- The saved v1230 and r1 Grok runs still read `blocked_by: access` (`test_a_blocked_run_records_blocked_by_awaiting_...`), and
  over every `state.md` under `test/fixtures/` the old and the new reading agree (4 blocked states, all `access`; no fixture
  holds an answered block).
- README `end_state` sentence and the G1 journal (marked superseded) updated in the same commit.

## 3. Open items

- G3 and G5 are not merged. Their duplicates (span/overlap readers, the `--version` probe helper, G5's `quality.end_group`) are
  for the second half.
- `runrecord.launch_epochs` (G2) reads the second in a resume record's name; G4's `launch_stamp` can bump that number past the
  real second when two launches share one. It is read only for runs without `sessions.jsonl` (runs from before 2026-10-09), so
  no new run is affected; recorded, not changed.

## 4. Verification

All runs with `SHIPLOOP_PROGRESS=off` and no exported `GIT_CONFIG_*` variable.

| When | Suite | Result |
|---|---|---|
| after the G2 merge (load about 5.3) | `python3 test/shiploop-e2e.test.py` | 404 OK, 110.4 s |
| | shiploop-e2e-fidelity / -reorientation / -runrecord | 140 OK 8.5 s / 118 OK 7.7 s / 6 OK |
| | test-groups / shiploop-run-review | 21 OK 4.3 s / 363 OK 22.5 s |
| after the G4 merge (load 4 to 6.6) | `python3 test/shiploop-e2e.test.py` | 404 OK, 111.0 s |
| | shiploop-e2e-environment / -fidelity / -reorientation / -runrecord | 125 OK 58.5 s / 140 OK 8.4 s / 118 OK 7.6 s / 6 OK |
| | test-groups / shiploop-run-review | 21 OK 5.5 s / 363 OK 22.4 s |
| after (a) | shiploop-e2e-fidelity | 142 OK, 8.3 s |
