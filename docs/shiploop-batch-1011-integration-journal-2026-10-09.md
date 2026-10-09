# Batch 1011 integration journal (2026-10-09)

Living journal of the integration branch `batch1011-integration-aaa47e` (worktree `.claude/worktrees/b1011z-aaa47e`) of the
harness batch planned in `docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md`. Base `30a3b40a`; groups merged one at a
time with `git merge --no-ff`, each conflict resolved so that both sides' behaviours and tests survive, then the duplicates the
group reviews found are unified, each with a failing test first. Harness only: nothing under `skills/`, `agents/` or `plugins/`
changes, so no change note and no release. Status words: firm (a test or a recomputed figure), interim, exploratory, superseded.

Group journals: G1 `docs/shiploop-batch-1011m-g1-fidelity-journal-2026-10-09.md`, G2
`docs/shiploop-batch-1011n-g2-reorientation-journal-2026-10-09.md`, G4 `docs/shiploop-batch-1011o-g4-environment-journal-2026-10-09.md`,
G3 `docs/shiploop-batch-1011q-g3-baseline-journal-2026-10-09.md`, G5 `docs/shiploop-batch-1011p-g5-quality-journal-2026-10-09.md`.
Run Review hand-off (generated): `docs/shiploop-batch-1011-run-review-handoff-2026-10-09.md`.

## 1. Merges

| Merge | Commit | Group head | Conflicting files (hunks) |
|---|---|---|---|
| G1 fidelity record | `cee214aa` (made before this journal) | `d46bdc9e` | none recorded here |
| G2 clear-context re-orientation | `6ff8ffb8` | `ceebbe17` | metrics.py (9), SPEC.md (1), README.md (1), LEARNINGS.md (1), suite_catalog.py (2); test-groups.test.py merged textually but wrong |
| G4 environment, product at stop, outcome class | `1c0a7c8d` | `35aef538` | run.py (3), metrics.py (1), runrecord.py (1), README.md (1), LEARNINGS.md (1), suite_catalog.py (2), test-groups.test.py (2) |
| G5 delivered quality | `a027227f` | `595982fe` | run.py (2), cases.json (2), SPEC.md (2), LEARNINGS.md (1), suite_catalog.py (2), test-groups.test.py (2) |
| G3 run identity and the baseline report | `63605571` | `64d9d1fa` | run.py (5), metrics.py (2), SPEC.md (2), README.md (1), LEARNINGS.md (1), suite_catalog.py (2), test-groups.test.py (2); hosts.py and test/shiploop-e2e.test.py merged textually |

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

- **G3 merge, `run.py` (5 hunks).** Imports: hashlib (G3) without importlib.util (G1 had dropped its last use); runrecord and
  sessionlog. Parser: G4's `--allow-host-change`/`--need` and G3's `--baseline-report`/`--runs`/`--json`. Launch record: G4's
  `needs`/`environment` and G3's `identity_unmeasured`. Result: G3's `prompt_sha256`/`host_build`/`span`/`identity_unmeasured`
  and G4's `outcome_class`/`outcome_basis`/`environment`. One semantic meeting fixed in the merge: G4 made a regrade's `recorded`
  the LAST launch record, while G3's regrade read the run's `host_build` (the FIRST launch's) from it; the run's build is now
  restated from the result, else invocation.json, and the regrade's own record restates the last launch's.
- **G3 merge, `metrics.py` (2 hunks).** Imports (runrecord, sessionlog) and `collect`'s return (G2's `fresh_starts` keys and
  G3's `span`). G3's session-count rule (Grok's `available_commands` is no session start; `unreported_sessions` null for a Grok
  stream, `unreported_sessions_at_least`) merged textually beside G2's feed bookkeeping; they read different events.
- **G3 merge, text.** The clauses table keeps G4's three rows and G3's S-12 identity row. The SPEC "Parallel work" paragraph had
  two authors and is now one paragraph naming two records, neither a verdict: G4's `environment.overlap` and G3's report count.
  The README's overlap paragraph likewise, keeping the phrases both suites pin. LEARNINGS: G3's entry after G4's (merge order).
- **G3 merge, tests.** Two G3 tests failed for the merge's reasons and were adapted: a `metrics.collect` stand-in that did not
  take G1's `tools=` (now `**kw` passed through), and a Grok run resumed on Codex that G4 refuses without `--allow-host-change`
  (now passed). G3's seven assertion edits in `test/shiploop-e2e.test.py` still hold. Counts: 74 ShipLoop suites, 115 in all;
  `E2EFamilySelectionTest.FAMILY` gained `shiploop-e2e-baseline`; `docs/experiments/baseline-spread-20261009/` now selects the
  baseline suite (`65f642c7`, test first).

- **G5 merge.** run.py: imports (quality, runrecord, sessionlog) and the launch record (G4's `needs`/`environment`, G5's
  `planning_review`/`improve_skill`, G3's `identity_unmeasured`); the phase wiring merged textually and still runs last, after
  the export and the baseline row. cases.json: battleship and checkers keep G4's `needs` and gain G5's `quality`
  declarations (the file parses). SPEC: G1's fidelity row and G5's quality row; G5's two rules after G1's and G2's. LEARNINGS:
  G5's entry last. Counts: 75 ShipLoop suites, 116 in all; `E2EFamilySelectionTest.FAMILY` gained `shiploop-e2e-quality` (the
  pin went red at the merge) and the quick tier selects all seven family suites for a run.py edit. The merge commit carries one
  known red test on purpose, `GroupKillTest.test_every_group_kill_in_the_harness_is_this_one` (quality.py's own killpg), fixed
  by the next commit.

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

### (d) One span reader and one interval rule (firm) — `9766e036`

`metrics.span(stamps) -> {"started", "ended"}` takes a timeline mapping or the path of a timeline.jsonl: the first and last
finite stamp in line order, None for both when none can be read, the first is after the last, or the file cannot be read.
`metrics.spans_overlap(a, b) -> bool`: each starts before the other ends (touching spans do not overlap, an instant inside the
other does, an unknown end is no overlap). G3's `metrics.span` (min/max: a NaN or infinity became the end, a backwards file
still had a span) and `run.span_overlaps`, and G4's `environment.span` (first and last parseable line) and its shared-time test,
read through these now; `environment.span` and `environment._stamp` are gone. The two predicates were shown equal on valid spans
before the swap, so no pinned figure moved. Outputs and populations stay each group's own (G4: siblings in the parent folder,
`runs[]`, `started_offset_seconds`, `siblings_read`, `siblings_unreadable`; G3: --runs roots plus file rows, `overlaps`,
`overlapped_by_span`, `not_seen_overlapping`, `unknown`). Recorded difference: a stamp is parsed by `metrics.timeline` like every
other reader of the timeline, so a line needs its `line` key, and a bool or numeric-string `t` reads as a number (G4's parser
refused those; the runner writes neither). Tests: `SpanAndPlanningTest` (2, red first).

### (e) One `--version` reader (firm) — `93de071b`

`hosts.probe_version(binary, env=None) -> (first stdout line, None) | (None, reason)` with the one ceiling
`hosts.VERSION_TIMEOUT_SECONDS = 20` and G3's reasons (`probe failed: not found | non-zero exit N | silent | hung (still running
after 20 s)`). Host CLIs pass the launch's isolated environment; G4's tool reads (node, python3, git) and the browser version
pass None (the harness's environment). `environment.browser_version` and `environment.TOOL_TIMEOUT` (10 s) are gone; G4's
shapes stay (`tools`/`unread`, `version`/`version_unread`), with "not found on PATH" when no binary is found. Tests: one wiring
test (red first) and G4's hang/fail test under the one ceiling and reasons.

### (f) The baseline row keeps no record of the ending (firm) — `dc9ee8a7`

`run.ROW_EXCLUDED_TERMINATION` (derived from `metrics.blocked_detail`'s keys) and `run.row_termination`: the row's termination
leaves out `engine_blocked_by`, `engine_awaiting_kind`, `engine_awaiting_no_default` and the regrade's `engine_stage_at_regrade`,
`engine_status_reason_at_regrade` and blocked `*_at_regrade` keys; `result.json` keeps them. Row key diff against the G4 merge:
those eight termination keys removed; nothing else. The row keeps every pre-batch termination key (with `engine_status`, which
`row_reached_done` reads, and `engine_status_at_regrade`), G3's identity keys and `identity_unmeasured`; `outcome_class`,
`outcome_basis`, `environment` and `quality` are pinned absent. Two existing assertions that equated the row's termination with
the result's now compare with `run.row_termination(t)`.

### (g) One host_build contract (firm) — `ea09ef4f`

`runrecord.host_build(record) -> (build, None) | (None, reason)` reads one launch record: a recorded build; else Claude's "Claude:
read from the init event after the run"; else the reason the launch recorded (`identity_unmeasured.host_build`); else "launch
predates the field"; else "no reason recorded". Users: the report's folder reader, `_main`'s regrade and resume branches (the
result keeps "first launch predates the field" and "resumed on another host: see the launch records", which are about the run),
and `environment.launch_environments`, whose entries now use the launch record's key names: `host_build` and
`identity_unmeasured` ({"host_build": reason} or {}). G4's `host_build_reason` and `_host_build_reason` are gone (a failed
probe's recorded reason used to read as "returned none"). Test: a through-main Grok run with a versioned first launch and a silent
resume probe reads back exactly what each launch record wrote.

### (h) G3's prompt hash and G5's planning-review sentence (note, for the G5 merge)

When G5 merges, `masked_prompt_digest` must hash the case prompt BEFORE any appended "Start ShipLoop with the run option
--planning-review none and --improve-skill <abs path>." sentence (G5 appends nothing for `stage`; only `none` appends), so a `none`
run of a named case hashes like the case's other `none` runs whatever `--plugin-dir` is (the mode is a key of its own).

### (i) The quality phase's group kill (firm) — `5d949f72`

`quality.end_group(proc) -> bool` keeps its contract (end the group, reap the leader once signalled or exited, say whether
a signal was sent) and signals through `listeners.end_group(proc.pid)`; `quality.exited(proc)` asks `listeners.unreaped(pid)`
(renamed from `_unreaped`). quality.py holds no `os.killpg`, `os.waitid` or `signal` import. Tests: the source scan (red at the
merge) and a new wiring test; G5's process-safety tests (whole group with its child, non-leader untouched, registration,
end_live_hosts, a helper left by a run that exits 0, the zombie leader, the reaped leader with getpgid mocked) unchanged.

### (j) The prompt hash and the planning-review sentence (firm) — `5e4e810a`

`run.case_prompt(prompt, improve_skill) -> str` strips the exact trailing sentence `planning_review_sentence(improve_skill)`;
result.json's `prompt_sha256` (fresh and resumed) and the report's folder reader hash it. Measured before: two `none` runs of
hello with two plugin builds hashed 5afa6a617bf2 and d35e3ba3d3b7. Test: those two hash equal, `stage` equals no option, the
`none` hash is the case prompt's, and the report reading prompt.txt agrees.

### (k) The row and result.json key sets (firm, no change needed) — verified at `5e4e810a`

A fake hello run through `run.main` (Claude, Grok, Grok stopped) at the merged head: result.json top level is case, host,
model, effort, pass, invoked, plugin, versions, prompt_sha256 (G3), host_build (G3), span (G3), identity_unmeasured (G3),
process, termination (+ blocked detail, G4), outcome_class (G4), outcome_basis (G4), environment (G4), left_behind, keepalive,
shiploop, committed, checks, cli, follow_on, resumed_run, seeded, chain, recovery, budget, expectations, product_at_stop (G4,
when not passed), metrics, output, quality (G5); `fidelity` is in metrics.json only. The row's tail is G3's seven identity keys
and identity_unmeasured; no quality, outcome_class or blocked detail; its planning_review is the engine's (state.md). The table
with groups is section 1 of the hand-off.

### (l) Leftovers (firm) — `8a0d19ce`

`quality.memory_writes` reads tool calls through `metrics.tool_call_events` (test first); `hosts.Host.cli_version` returns
`runrecord.CLAUDE_BUILD`. compileall and `python3 -W error` imports of every harness module are clean; the replaced names occur
only in tests asserting their absence or in docs naming the replacement. One implementation each: `metrics.span` /
`metrics.spans_overlap`, `hosts.probe_version`, `metrics.blocked_detail`, `runrecord.host_build`, `listeners.end_group` (with
`listeners.unreaped`), `metrics.tool_call_events` / `ToolLog.feed`. Pre-batch readers left alone: run.shiploop_cli_ran and the
truncation reader in run.py.

### (m) The Run Review hand-off (generated) — `c9869792`

`docs/experiments/batch-1011-run-review-handoff-20261009/generate.py` writes the hand-off and `shapes.json`, from seven saved
runs read only (no file under them changed), fake-host runs through `run.main`, G2's reconstructed sessions fixture and G5's
committed quality block.

## 3. Open items

- ~~G5 is not merged ...~~ Done: (i), (j), and FAMILY in the G5 merge.
- ~~`baseline_row` copies `result["termination"]` ...~~ Superseded 2026-10-09 by (f).
- ~~`hosts.ClaudeHost.cli_version` returns a literal copy of `runrecord.CLAUDE_BUILD`~~ Done in (l).
- G5's mutant list (`docs/experiments/batch-1011p-g5-quality-20261009/mutants.py`) patches the text of the old `quality.end_group`;
  it is G5's round's evidence and was not re-run against the delegating version.
- The real-browser calibration (G4 F6) and live runs of the merged harness are the main session's.
- The quick tier for this branch selects 71 suites (1104 s), not 33: G3's compact run folders keep copies of the CLI entry at
  `test/fixtures/baseline-spread/runs/<run>/build/plugins/skill-craft/skills/shiploop/scripts/shiploop` (19 files), whose stem
  `shiploop` selects every `shiploop-*` suite by the name rule. A selection cost, not a failure; a fixture-path exclusion in
  `suite_catalog.targeted` would fix it and is left to the coordinator.
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

| after the G3 merge (load 1.7 to 2.4) | shiploop-e2e / -baseline / -environment / -fidelity / -reorientation / -runrecord | 404 OK 108.6 s / 139 OK 22.9 s / 132 OK 57.9 s / 142 OK 9.0 s / 118 OK 7.9 s / 6 OK |
| | test-groups / shiploop-run-review | 24 OK / 363 OK 22.2 s |
| after (d) (load about 2.2) | shiploop-e2e / -baseline / -environment / -fidelity / -reorientation / -runrecord / test-groups / run-review | 404 OK 108.5 s / 141 OK 24.0 s / 132 OK 59.7 s / 142 OK 8.6 s / 118 OK 7.6 s / 6 OK / 25 OK / 363 OK 21.7 s |
| after (e) (load about 2) | the same list | 404 OK 108.1 s / 141 OK 23.9 s / 133 OK 59.7 s / 142 OK 8.7 s / 118 OK 7.6 s / 6 OK / 25 OK / 363 OK 21.6 s |
| after (f) | the same list | 404 OK 110.1 s / 142 OK 24.1 s / 133 OK 62.3 s / 142 OK 8.6 s / 118 OK 7.6 s / 6 OK / 25 OK / 363 OK 21.5 s |
| after (g) | the same list | 404 OK 108.3 s / 143 OK 25.0 s / 133 OK 62.2 s / 142 OK 8.6 s / 118 OK 7.7 s / 6 OK / 25 OK / 363 OK 21.6 s |
| after (g), G3 part done | `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 71 of 71 suites, 1104 s wall (see the open item on the fixture CLI copies) |
| after the G5 merge (load 1.2 to 1.8) | the same list plus -quality | 404 OK 110.2 s / -quality 125 OK 42.2 s / -baseline 143 OK / -environment 133, 1 failure (the planned red scan) / others OK |
| after (i) | the same list | 404 OK 108.6 s / -quality 126 OK 41.9 s / -environment 133 OK 62.6 s / all OK |
| after (j) | the same list | 404 OK 107.2 s / -quality 127 OK 42.7 s / all OK |
| after (l) | the same list | 404 OK 110.2 s / -quality 128 OK 43.2 s / all OK |
| final head `c9869792` + this journal (load 2.9 to 4.9) | shiploop-e2e / -environment / -quality / -baseline / -fidelity / -reorientation / -runrecord / test-groups / run-review | 404 OK 108.3 s / 133 OK 62.1 s / 128 OK 42.6 s / 143 OK 25.6 s / 142 OK 8.7 s / 118 OK 7.7 s / 6 OK / 25 OK 2.2 s / 363 OK 22.0 s |
| | `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 72 of 72 suites, 1145 s wall (the seven family suites among them) |

`test/shiploop-e2e.test.py` stays at 404 tests and 107 to 111 s across all five merges and every unification, against `QUICK_MAX_SECONDS` 120 (no test was
added to it; its catalog duration is 100.0).
