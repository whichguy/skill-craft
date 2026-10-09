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

### (b) One guarded group kill (firm)

Four group kills existed: `run.kill_group` (unguarded `killpg`, used by `run.launch` and `run.end_live_hosts`), the inline
`os.killpg` in `hosts.run_agent` (the review and fan-out agents; the brief called it `hosts.run_process`), G4's
`environment._signal_group` behind the probe's launch-time leader check, and G5's `quality.end_group` (not merged yet). Now one:
`listeners.end_group(leader: int) -> bool` (True when the SIGKILL was delivered).

The rule: signal only while the number is still the leader's. `os.waitid(P_PID, leader, WEXITED|WNOHANG|WNOWAIT)` (reaps
nothing) says whether the leader is this process's unreaped child: `ChildProcessError` means reaped already or never ours, and
nothing is sent. A running leader must also lead its group (`os.getpgid(leader) == leader`). An exited, unreaped leader (a
zombie) is signalled without the getpgid check, because **on macOS `os.getpgid` raises `ProcessLookupError` for a zombie while
`os.killpg` still reaches its group** (measured on this machine, Darwin 27.0.0: `sh -c 'sleep 30 & exit 0'` in a new session,
0.5 s later `getpgid` raised and `killpg(pgid, 0)` succeeded). A literal "only while `os.getpgid(pid) == pid`" guard would
therefore have stopped ending the group of a host whose leader exited a moment before the kill (the `launch` poll race) while
its workers lived. A group that holds only the zombie answers `EPERM` to `killpg` on macOS (measured too): reported as nothing
delivered, never raised.

Callers: `run.launch` and `run.end_live_hosts` call `listeners.end_group` (`run.kill_group` is deleted), `hosts.run_agent` on
its timeout, and the probe (`end_browser`, `end_live_probes`; `_signal_group` deleted; `_group_alive`, a signal-0 question, stays).
Behaviour kept for every path a test or a recorded run shows. The one change is the rule itself: a group whose leader was
already reaped is no longer signalled. In the probe that is the case "the leader exited and `poll()` reaped it while something
it started stayed in its group" (no fake-browser mode and no recorded run shows it; Chrome's leader lingers, G4 F6): the group
is then left, and `group_empty` reads false. G5's `quality.end_group` is to be pointed at `listeners.end_group` when G5 merges;
the source scan below fails until it is.

Tests (`test/shiploop-e2e-environment.test.py`, `GroupKillTest`, 7 tests, red before the function existed): a running leader's
group (with a member it started) is ended; an exited, unreaped leader's group is ended and the leader's own exit status is kept;
a reaped leader, a running child that does not lead its group and a process that is not this process's child are never
signalled (a wrapper records every non-zero `killpg`); no module of `test/shiploop_e2e/` other than `listeners.py` sends a group
signal (a source scan: only `killpg(..., 0)` outside it), `run.kill_group` and `environment._signal_group` are gone; and
`run.end_live_hosts` and `hosts.run_agent` end their groups through it. Mutants of `end_group` (each applied to the file, the
class run, the file restored): signalling after a reap, no leader check, skipping the zombie case: all red. Applying the getpgid
check to a zombie too survives, as an equivalent mutant (getpgid raises for it on macOS and the fallback re-checks).

### (c) The quick tier selects the whole E2E family (firm)

Before: `_PREFIX_SUITE_IDS["test/shiploop_e2e/"]` was `("shiploop-e2e",)` on G1 and G4 and `("shiploop-e2e",
"shiploop-e2e-reorientation")` on G2, so an edit of `metrics.py` or `fidelity.py` (names too common for the stem rule) ran
neither `shiploop-e2e-fidelity`, `-runrecord` nor `-environment` in the quick tier, although each reads those modules. Now the
prefix maps to `_E2E_FAMILY_IDS`, read from the catalog (every ShipLoop suite whose id is `shiploop-e2e` or starts with
`shiploop-e2e-`; the apparatus is another family), so G3's `-baseline` and G5's `-quality` are selected once their files are
registered, with no second list. Cost for a harness edit: about 182 s of catalog durations (shiploop-e2e 100, -environment 65,
-fidelity 9, -reorientation 7.7, -runrecord 0.2), each suite under `QUICK_MAX_SECONDS`.

Tests first (`test/test-groups.test.py`, `E2EFamilySelectionTest`, 3 tests): the pinned family (five suites on this branch)
equals the catalog's E2E suites, so a merged group that adds one must update the pin on purpose; an edit of `run.py`,
`metrics.py`, `fidelity.py`, `sessionlog.py` or `environment.py` selects the whole family through `targeted` and through
`quick` (red before: only shiploop-e2e and -reorientation); the apparatus is not selected. Pinned counts stay the real catalog:
73 ShipLoop suites, 114 in all (`test_audited_catalog_counts_and_fixed_commands`). test-groups: 24 OK.

## 3. Open items

- G3 and G5 are not merged. Their duplicates (span/overlap readers, the `--version` probe helper, G5's `quality.end_group`) are
  for the second half.
- `baseline_row` copies `result["termination"]`, so since G4 a baseline row's `termination` also carries `engine_blocked_by`,
  `engine_awaiting_kind` and `engine_awaiting_no_default` (G4 removed `outcome_class` from the row; these keys came in through
  `termination`, not through the merge). For the second half's row review (integration item 14); not changed here.
- The SPEC S-6 evidence line and the G2 owner finding stay as G2 left them (main session's item).
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
| after (b) (load about 4) | shiploop-e2e-environment | 132 OK, 62.3 s |
| | `python3 test/shiploop-e2e.test.py` | 404 OK, 108.2 s |
| after (c) | test-groups | 24 OK, 2.5 s |
| final head, before this journal commit (load 3.4 to 4.5) | shiploop-e2e / -environment / -fidelity / -reorientation / -runrecord | 404 OK 108.7 s / 132 OK 61.1 s / 142 OK 8.6 s / 118 OK 7.6 s / 6 OK |
| | test-groups / shiploop-run-review | 24 OK 2.2 s / 363 OK 22.2 s |
| | `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 33 of 33 suites, 645 s wall (the five E2E family suites selected; shiploop-e2e 103.8 s in the runner) |

`test/shiploop-e2e.test.py` stays at 404 tests and 108 to 111 s across the merges, against `QUICK_MAX_SECONDS` 120 (no test was
added to it; its catalog duration is 100.0).
