# Batch 1011, group G1: the fidelity record (journal, 2026-10-09)

Branch `batch1011m-aaa47e`, base `30a3b40a`. Updated after two adversarial reviews of head `0bd77328` (lens A: correctness, robustness, test
validity; lens B: conformance, scope, honesty): the sections below describe the block as it stands now, and "Fix round" at the end lists
every review item with its disposition and commit. Design `F1-fidelity-scorecard` and its audit:
`docs/experiments/batch-1011-harness-design-audit-20261009/design-audit.json`; the plan row is in
`docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md`. Harness-only: no skill, so no change note and no release.

## The question

Rounds 1 to 3 of the bounded improvement loop spent 17 hand-mined lens reports on counts that the run's own records hold: which
accepted stages rest on a script-run record, whether the verify rows ran a test, which refusals came back unchanged, whether the model
edited files the scripts own. Can the harness record those counts from the run folder, without ever deciding anything about them?

Answer built: a `fidelity` block in `metrics.json` (not `result.json`, not a baseline row), made by `test/shiploop_e2e/fidelity.py`
and called once from `run._main` after `metrics.collect`, so a regrade (`--resume-run <dir> --grade-only`) adds it to a run that has none.
At most five `fidelity` lines print. Every part is independent and fails open; a part that cannot be read, and a figure nothing measured, is
null with its reason in the block's `unmeasured` map; the paths in the block are `<run>` and `~`, so it names no machine. It is a record, never a verdict (SPEC, rules for the harness itself, amended 2026-10-09 in `d72d11cc`).

## What was built, and the evidence

All figures below were recomputed from the saved run folders (the design's prose numbers were claims to verify). The committed extracts
under `test/fixtures/fidelity/` (cut by `test/fixtures/fidelity/extract.py`) give the same figures as the full folders on every pinned
item (a throwaway comparison script found no difference for the eleven Claude and Grok runs, and one refusal fewer in the Codex extract, see "Deviations", Fixtures).

Status vocabulary: firm = reproduced from the saved runs and pinned by a test; interim = measured once, precision unknown.

### (a) Evidence class per accepted action (`evidence`) — firm

Classes: `skipped` (the engine's own `Not applicable to this item`, `metrics.NOT_APPLICABLE`, pinned to `shiploop_item_scope.NOT_APPLICABLE`), `script`,
`loop`, `file`, `note`, `sentence`, `unclassified` (a history entry with no accepted result). `records` lists every kind found. Counts of `evidence.counts`
(the fix round moved one row: v1230-battleship-sonnet's skill-validate cites the result of another action, which is a cited file, not "its own": file 9 -> 10,
sentence 3 -> 2):

| run | script | loop | file | note | sentence | skipped | rows |
|---|---|---|---|---|---|---|---|
| r1-battleship-sonnet | 15 | 7 | 1 | 12 | 0 | 2 | 37 |
| r2-battleship-sonnet | 13 | 8 | 7 | 3 | 3 | 2 | 36 |
| r3-battleship-sonnet | 14 | 7 | 8 | 4 | 3 | 0 | 36 |
| r1-checkers-sonnet | 13 | 8 | 13 | 2 | 0 | 0 | 36 |
| r2-checkers-sonnet | 16 | 6 | 12 | 3 | 0 | 0 | 37 |
| r3-checkers-sonnet | 16 | 7 | 8 | 7 | 0 | 0 | 38 |
| r1-battleship-grok-none | 12 | 1 | 11 | 1 | 0 | 2 | 27 |
| r2-battleship-grok-none (Grok, finished by Claude) | 21 | 2 | 23 | 2 | 0 | 4 | 52 |
| r3-battleship-grok-none (stopped, engine active) | 4 | 0 | 10 | 1 | 0 | 0 | 15 |
| v1230-battleship-sonnet | 16 | 7 | 10 | 3 | 2 | 0 | 38 |
| v1230-battleship-grok-none (blocked) | 19 | 2 | 23 | 3 | 0 | 0 | 47 |
| v1210-battleship-luna-xhigh (Codex, 1.21.0) | 8 | 5 | 9 | 1 | 0 | 0 | 23 |

- The audit's correction holds: `file` hid notes. In r1-battleship-sonnet 12 of the 13 file-like rows cite only model-authored notes
  (`run/notes`, `run/evidence`, `run/scratch`, Improve reviews, by the harness's own `MODEL_INPUT`). The design's r3-battleship-sonnet figures
  (14 / 7 / 12 / 3) are reproduced once `file` (8) and `note` (4) are added.
- The Codex row reproduces the audit's 8 / 5 / 10 (file 9 plus note 1).
- Precedence `script > loop` hides a review loop: in r3-battleship-sonnet 8 actions have an Improve child but only 7 read `loop`, because the
  carry-forward also carries a verify record. The block lists `records` per row and the printed line prints the record totals.
- `declared` per row comes from the run's own stage table through the exporter's `stage_catalog` and `effective_exit_check`. Each row also has `needs`
  (the record kinds the stage's declared runs leave: `lint-gate` -> lint gate record, `test-loop`, `test-probe`, `test-red`, `test-rerun` -> verify record,
  `quality-terminal` -> quality record; no lint kind when the run's lint option is `off`) and `lacks`; `declared_script_run_without_record` lists a done,
  not skipped stage that lacks any needed kind, so one script's record no longer stands in for another's (review A1, below). It is empty on all eleven runs
  (a blocked system-test has no record by design and is not a done stage). A run the harness has no record kind for makes `needs` None (`unmapped_runs`).
- An incompatible stage table is unmeasured, not an error: the 1.21.0 table (installed in the v1210 Codex profile) has no
  `PLANNING_CHOICE_STAGES`, so `exporter.stage_catalog` raises `AttributeError`; the block records
  `unmeasured["declared"]` with that reason and still classifies the rows (verified on the real v1210 folder; the test uses a stub table built
  from the engine's table with the planning stages left out, because the real file is 30 KB).
- `refs` are `{own, note, outside}` counts. `missing` (whether a cited path still exists) is not asked: the refs are paths of the machine
  that ran, a moved folder would read all missing, and the engine already checked existence at the callback (audit missed-unknown 3).
- `file` is satisfied by citing any file: a reading aid, never a target (SPEC rule 5).

### (b) Verify-record audit (`validation`) — firm

Read as JSON from `tests/*-verify*.md` with the same `rglob` the regex reader uses. Fields: `records`, `unread` (not `shiploop-test-loop/v1`
or not JSON), `runs`, `distinct_commands`, `passed`, `could_not_run`, `red`, `schemas`, `by_suite` (`runs`, `counted`, `counts_null`, `zero_ran`, which is
null for a suite with no counted row), `tests_ran_unmeasured`, `accepted_ran {runs, stages}` (null when no row carries the key), `release_verify
{where, kind, passed}` (the latest record by `created_at` then record number, with that record's own `passed`).

- r3-battleship-sonnet: 11 records, 33 runs, 5 distinct commands, 2 red, `accepted_ran` at 6 stages (integration-verify, regression, static-checks,
  test-green, test-red, verify); focused 19 runs, regression 6, check 8 of which 7 have null counts and 1 is counted. This reproduces the design's
  FE-19 line (11 / 33 / 5 / 2 / 6) and corrects the design's `data_shape` example (focused 19 runs with 19 counted; the example's "5 regression" and
  "9 check, 4 static" were not this run's).
- The null-count audit of 2026-10-06 reproduces from the committed v1220 record heads: v1220-battleship-sonnet 27 focused + 7 regression =
  **34 of 34** rows with `counts: null`; v1220-battleship-grok-medium-none 18 + 12 = **30 of 30**. Such a row is `tests_ran_unmeasured`, listed in
  `unmeasured["validation.counts"]` with the S-9 reason, never a pass. The eleven runs from v1230 on have none: their focused and regression rows are counted.
  Their check rows carry null counts by design (a check is judged by its exit code), so those are not counted as unmeasured tests.
- The old regex reader (`metrics.verifications`) and the JSON reader agree on all eleven saved runs and on both v1220 runs: records, passed,
  red, could_not_run, and regex `commands` equals JSON `runs` (pinned by `test_the_regex_reader_and_the_json_reader_agree_on_all_eleven_saved_runs_and_the_two_v1220_runs`).
  Agreement was also checked on the full folders (not only the extracts), where stdout is present; it holds there too. `fidelity.build` now makes the same
  comparison on the live folder and names a difference with both values in `unmeasured["validation.readers"]` (none on the saved runs).
- `accepted_ran` is null with `unmeasured["validation.accepted_ran"]` on 8 of the 11 runs (the engines that wrote them do not write the key; r3-battleship-sonnet
  and r3-checkers-sonnet have it at 6 stages) and on both v1220 runs; `zero_ran` is null on every v1220 suite (0 of 42 and 0 of 41 rows counted) and the printed line
  reads "zero-ran n of m counted" or "zero-ran unmeasured (no row counted)".
- Not built (the plan row does not list it): per-check `static_only` (the reader-tool list the audit said must be written and pinned); `ids_shown`/`ids_missing` per suite.

### (c) Edits, kills, commits (`edits`) — firm on the saved runs; a list to confirm in general

Listed facts with the `event` (the 0-based line index of `events.jsonl`, as `metrics.events` counts). The new detectors unwrap a leading
`sh|bash|zsh -c|-lc "<script>"` (read by the shell's own rules, so concatenated quoting unwraps: all 1356 wrapped commands of the 1.21.0 Codex run do), expand the
variables the command assigns, drop heredoc bodies but keep the marker line, and leave quoted text out of what they match; `metrics.glue_reasons` is frozen and does
none of this. The owned set is anchored (the run directory, `.shiploop`, `.shiploop-improve`, the three workspace files), not the frozen `SHIPLOOP_OWNED`.

- Script-owned edits in the eleven runs: exactly two, both `sed -i` on `return-plan.md`: **r1-battleship-sonnet event 493** and **r1-checkers-sonnet event 414**. No false positive.
  (A first reading flagged `sed -i` on `$R/scratch/...` because the sed script word held an expanded `$R`; the script operand of an in-place sed or perl is now not a file.)
- Known miss, pinned: the python heredoc that rewrote `return-plan.md` at **r1-battleship-sonnet event 487** (`open(p, "w")`) is not seen.
- Name-pattern kills: **five**, the set the audit verified (the design prototype and the audit list exactly these; the plan row names no count), all reproduced. r2-checkers-sonnet 571, r3-checkers-sonnet 548 and r2-battleship-grok-none 2838
  are `pkill -f "node server.js"`; r3-battleship-grok-none 858 is `pkill -f "http-probe.mjs"` and r3-battleship-grok-none 7711 is
  `pkill -f "socketserver.TCPServer"`. The last two are a pattern kill of the model's own probe server by a distinctive name; they are listed as
  facts like the others, and whether they could hit a sibling run is not claimed. A numeric-pid kill (`kill 67975`, v1230 Grok) is out of scope and not listed.
  The first prototype missed 7711 because its regular expression lacked multi-line anchoring; the production pattern has it. The fix round added the `ps | grep ... | xargs kill`
  and `ps ... | while read p; do kill "$p"` forms (review A6), which finds a sixth in a run outside the eleven: v1220-battleship-grok-medium-none event 8493
  (`ps aux | rg 'battleship-chrome' | ... | while read p; do kill "$p"`); kill by port (`lsof ... | xargs kill`, after 7711's pkill) stays out of scope.
- Model `git commit`/`add` commands (per call, `forms` lists add and commit): r1-battleship-sonnet 1 call (463), r2-battleship-sonnet 1, r3-battleship-sonnet 2,
  r1-checkers-sonnet 2, r2-battleship-grok-none 10 (the Claude half of that mixed-host run), v1230-battleship-sonnet 1, v1230-battleship-grok-none 1; none in
  r2-checkers, r3-checkers, r1-battleship-grok-none, r3-battleship-grok-none. The count per run equals the frozen `model_glue` entries with the reason
  "git commit/add by the model" on all eleven runs (pinned), so there is one meaning of a model commit command.
- Codex: the Codex glue count is **not comparable** with the fidelity lists (review B6 corrected "a known undercount": the undercount direction is shown on a constructed
  string only). On the 1.21.0 Luna run unwrapping changes the glue answer on exactly three calls, events 731, 776 and 779, each REMOVING a commit that was prose in a heredoc
  body ("; git diff --check passed. Scoped commit"); the unwrapped detectors list 0 commit commands. The real command strings of events 82 and 731 are pinned in a `subTest`. The one script-owned edit on that run is the
  Codex `file_change` on `.../backchain/<action>/until-loop-start-contract.json` at event 1012, listed once although `target_file` and `paths[0]` name it twice.
- The Codex glue-reason difference apart, model commit commands are labelled by the git subcommand (add or commit only; `git worktree add`, `git remote add`,
  `git log --grep add` and the like are none), found at a command position after then, do, else, `(`, env, xargs or an assignment.
- Heuristic rows need `tool_calls_seen > 0`: with a missing or empty `events.jsonl`, `edits` and `refusals` are unmeasured (test), not 0 and not a pass.
- Nothing in the detectors can signal a process (test patches `os.kill`, `os.killpg` and `subprocess` to fail); no test starts one.

### (d) Refusals (`refusals`) — firm

One row per ShipLoop refusal from the same list as `shiploop_failures` (`count == len(shiploop_failures)` on every run, asserted), with `event`, `verb`,
`exit`, `stage` (the `stage_windows` join `per_stage` uses; null without a timeline), `line` (the 200-character line, as `shiploop_failures` has it) and `repeat_of`
(index of the refusal just before it when the **whole** first line is equal and the stage is the same and known). `ToolLog.failure_events` keeps the whole first line
beside the cut one; `shiploop_failures` keeps its exact shape (three tests compare it whole).

- The four repeats reproduce exactly: r1-battleship-sonnet 447/449 (release-plan, the knowledge-home refusal), r2-checkers-sonnet 237/239 (plan, assumption A3) and
  384/410 (test-author), r3-battleship-grok-none 1291/1325 (spec, the credential screen). No other run has a repeat. A second pair of refusals that differ only after the
  200th character is not a repeat (test), and with stage null nothing is flagged.
- On the Codex v1210 run (not part of the eleven) one repeat is flagged at event 1464 (plan); it is not pinned.
- The count includes failures found through the nonzero-exit arm without a refusal line (r2-battleship-sonnet has one of its one).
- `repeated` is null (and `unmeasured["refusals.repeated"]` says so) when no refusal could be given a stage, as with no `timeline.jsonl`; a partly staged list
  notes `refusals.stage`. The part has `limits` and the printed line says "(heuristic, no repeat flagged is not proof)".

### (f) End state (`end_state`) — firm

`status`, `stage`, `unaccepted_stage`, `status_reason` (cut at 200 characters), `blocked_by`, `awaiting {kind, no_default}` (whether the result states why no default
would do) and `unverified {entries, owners}` or null. v1230-battleship-grok-none: blocked at system-test, `blocked_by: access`, `awaiting {kind: present, no_default: true}`;
r1-battleship-grok-none: blocked at system-test-author, `access`, `awaiting {kind: answer, no_default: true}`; r3-battleship-grok-none: `active`, `unaccepted_stage: implement`,
nothing claimed. `unverified`: r2-battleship-sonnet and r3-battleship-sonnet carry entries owned by `user`, r2-checkers-sonnet, r3-checkers-sonnet and r2-battleship-grok-none
carry an empty list (every outcome observed), the other six runs have no such key and the block says so (`unmeasured["end_state.unverified"]`), never 0.

### Improve-packet five questions (`improve_packets`) — firm

The exporter does not record Improve-packet labels: `export.py` scores `carried` for producer packets only (`CARRIED`, `carried_markers`) and writes the `-improve.md`
packet as a text document. So a small table (`fidelity.IMPROVE_QUESTIONS`: goal, done when, checked by, output, recovery) is the harness's own, anchored to the
engine's strings (a test pins each prefix against `shiploop_navigator.py`) and to be deleted if the exporter owns it (S-12). A test fails if the exporter's source
starts to carry the Improve wording.

- 63 `-improve.md` files in the eleven runs: **35 carry all five, 28 lack goal and done when** (r1-battleship-sonnet 8, r1-checkers-sonnet 8, v1230-battleship-sonnet 8,
  r1-battleship-grok-none 2, v1230-battleship-grok-none 2; r2 and r3 of Sonnet 8 each and r2-battleship-grok-none 3 carry all five; r3-battleship-grok-none ran no
  Improve child). The design's "40" and "16 of 16" were wrong, as the audit said.
- A run with no Improve child has `read: 0` (r3-battleship-grok-none: a measured none, review B16). A run of the old packet layout (ShipLoop 1.22.0 and earlier: the
  v1210 Codex run, whose producer files hold the child's packet, marked by "Current action: Improve the completed", pinned equal to the exporter's `IMPROVE_PACKET`) is
  unmeasured, and so are children that left no `-improve.md` file. The table is TEMPORARY (SPEC row, README): the Run Review owner is asked to adopt it.
- The five patterns are tested against a real packet with each label's line dropped, and with it turned into a mid-line mention (review A5: the extract keeps only the
  lines the patterns match, so a pattern that matches everything survived the replay).
- The block stores label booleans only, never packet text.

### Printing

`run._main` prints at most five lines after the `metrics` lines, each saying what it counts and, for the heuristic ones, that no hit is not proof (the phrase "lower bound" is
reserved by the report's cost note). Real output for the r1-battleship-sonnet extract:

    fidelity  evidence 37 accepted: script 15, loop 7, file 1, note 12, sentence 0, skipped 2, unclassified 0 (records: verify 10, lint 6, quality 1, backchain 1, improve 8); declared script-run without a record: none
    fidelity  validation 10 records / 29 runs / 6 commands: test counts unmeasured 0, zero-ran 0 of 23 counted, red 2; release-verify record: returned-result, passed true
    fidelity  edits (heuristic, no hit is not proof): script-owned edits 1, name-pattern kills 0, model commit commands 1
    fidelity  refusals (heuristic, no repeat flagged is not proof) 5, repeated 1: "ShipLoop navigator: ShipLoop keeps this run's planning knowledge in the repository so later runs inh"
    fidelity  end state done; Improve packets 8: all five 0, lacking 8

## Deviations from the design, and why

- **Not built, by the plan row**: the eight-row clauses table and every pass/fail or S-15 narrative vocabulary (audit corrections 1 to 4: S-10 false-fails 2 of 11 runs
  because a work item's first carry-forward has no Improve child by design, S-9 would pass null counts, S-4 would pass beside wrapper scripts, S-15 says narratives are not a verdict);
  producer-packet scoring (the exporter's `carried` stays the one reader, correction 7); the authors histogram and the `WORKSPACE_IDENTITY` regex (correction 13); the `result.json` copy
  (correction 9: the planning-block precedent and its test); part (i) baseline summary and part (j) claim counts (needs another run); wrapper-script counts as S-4 evidence
  (`tool_use.scratch_scripts` already lists them for Claude).
- **Where the block is built**: `run._main`, not `metrics.collect`. `collect` takes an optional `tools` ToolLog to fill (`metrics.collect(out, run_dir, tools=log)`), so fidelity reads the same
  classified calls (S-12: one classifier) without `metrics` importing `fidelity`. `progress.py` and `shared_tmp_writes` call `collect` as before and get no `fidelity` key.
- **`metrics.py` additions** (named in the SPEC non-regression list, review B12): `call(..., event=None)` and `result(..., event=None)` take the line number; `ToolLog.sequence` keeps
  every call in order (the `calls` dict keeps one per id, and Codex numbers its calls again in each session, so a scan of `calls` would lose earlier ones); `ToolLog.failure_events`
  runs in step with `failures`; `failure_line(shown, limit=200)` can return the whole line; `metrics.target_paths(arg)` is the single reader of `target_file`/`file_path`/`path`/`paths`
  and de-duplicates Codex's repeat (a call's target is now its first path); `metrics.NOT_APPLICABLE` is the one constant of the engine's prefix and `metrics.within` the one stage-window rule.
- **No host in the block** (reviews B9, A13): the header carries no `hosts` or `mixed_host`; `runrecord` is the one reader and group G4's environment block records them.
- **Portable block** (review A9): the run folder is written `<run>` and the home folder `~` in every string.
- **One exporter loader** (review B18): `fidelity.load_exporter`, used by `run.review_export` and the stage-table reader.
- **The Improve table is kept** (the exporter has no Improve labels). The plan row does not list it; the audit's `safer_alternative` allows it only as a temporary table, deleted when the exporter owns it. It is marked TEMPORARY in the SPEC row and the README, and the Run Review owner is asked to adopt it (hand-off below).
- **Fixtures**: events keep their original line numbers (the unselected events are blank lines), so `event 493` is the 0-based line index 493 of the saved stream (line 494 in an editor). Heredoc bodies over 600 characters
  are cut except one whose prose matters; a cut body can drop a ShipLoop verb that only the body named, so the Codex extract has 9 of the full run's 10 refusals.
- **A stage table stub** built from the engine's table (`stage_table.json`, frozen by the extractor) replaces the engine's live table in the tests, so a later change to the
  engine's table cannot move a saved run's declared checks.
- **Disagreement**: none with the audit's corrections.

## Known limits (also in the README and pinned where a test can)

- Pinned by a test: an edit of a script-owned file by interpreter code (event 487), a shell `apply_patch` or `git apply`, a numeric-pid kill, a relative path after `cd` for any
  file but the three workspace files (matched by name; a product file of that name would be listed), a ShipLoop verb hidden by a model's wrapper script (the refusal is still
  read from the result text, with the verb `unknown`). Listed in the README, not pinned: a kill by port, `install`, `truncate`, `cp -t`, `find -exec sed -i`, `xargs sed -i`, a
  redirect written without a space, and a quoted `>` word read as a redirect by the edit detector.
- The Codex glue count is not comparable with the fidelity lists (corrected from "a known undercount", see (c)).
- The round-3 loop criterion (2) was author-based and is measurable only on Claude on a machine with no configured git identity: the block reads no authors.
- The first call after a Grok compaction (the one script measure of S-6 in action) is group G2's `fresh_starts`; not built here.
- `left_behind` (listener leaks) is absent from `facts.md`, `metrics.json` and the export (round-3 R3-11); it lives in `result.json` only. Noted for the Run Review session.
- Stage windows are whole seconds, so a refusal next to a stage boundary can be assigned to the neighbouring stage; `stage` is best effort.

## Hand-off to the Run Review session: exact shapes (`metrics.json["fidelity"]`)

Absent from `result.json`. Null parts have a reason string in `unmeasured` (keys: a part name, `declared`, `declared.runs`, `validation.counts`, `validation.unread`,
`validation.accepted_ran`, `validation.readers`, `refusals.repeated`, `refusals.stage`, `end_state.unverified`). A block whose builder raised is the **error block**
`{"schema": "shiploop-e2e-fidelity/v1", "error": "ExceptionName: one line"}` (and one printed `fidelity  skipped: ...` line): a reader of `fidelity["evidence"]` must check for
`error` first. The block names no host (`runrecord.hosts_used` is the one reader) and no machine (the run folder is `<run>`, the home folder `~`). Real block of r1-battleship-sonnet
(its extract; lists cut to a few rows, marked `...`):

    {"schema": "shiploop-e2e-fidelity/v1", "tool_calls_seen": 109,
     "unmeasured": {"validation.accepted_ran": "no verify row carries accepted_ran (an engine that does not write it, or no row had a floor), so the rows that ran at least their floor are not known",
                    "end_state.unverified": "no accepted result carries an unverified key, and a result without the key says nothing (it is not an empty list)"},
     "evidence": {"counts": {"script": 15, "loop": 7, "file": 1, "note": 12, "sentence": 0, "skipped": 2, "unclassified": 0},
                  "records": {"verify": 10, "lint": 6, "quality": 1, "backchain": 1, "improve": 8},
                  "declared_script_run_without_record": [],            // null when "declared" is unmeasured
                  "unmapped_runs": [],
                  "stages": [{"action": "nav-b5efb9ac...", "stage": "intake", "work_item": null, "outcome": "done", "declared": "model judgement", "needs": [], "lacks": [],
                              "class": "note", "records": [], "refs": {"own": 0, "note": 1, "outside": 0}},
                             {"action": "nav-118d02ad...", "stage": "test-green", "work_item": "W1", "outcome": "done", "declared": "script-run", "needs": ["lint", "verify"], "lacks": [],
                              "class": "script", "records": ["verify", "lint"], "refs": {"own": 0, "note": 0, "outside": 1}}, ...]},
     "validation": {"records": 10, "unread": 0, "runs": 29, "distinct_commands": 6, "passed": 10, "could_not_run": 0, "red": 2,
                    "schemas": ["shiploop-test-loop/v1"],
                    "by_suite": {"check": {"runs": 6, "counted": 0, "counts_null": 6, "zero_ran": null},
                                 "focused": {"runs": 17, "counted": 17, "counts_null": 0, "zero_ran": 0},
                                 "regression": {"runs": 6, "counted": 6, "counts_null": 0, "zero_ran": 0}},
                    "tests_ran_unmeasured": 0, "accepted_ran": null,
                    "release_verify": {"where": "returned-result", "kind": "fast-forward-merge", "passed": true}},
     "edits": {"script_owned": [{"event": 493, "tool": "Bash", "form": "sed -i", "target": "/runs/r1-battleship-sonnet/.shiploop-runs/work-1/return-plan.md"}],   // "<run>/..." in a live block
               "name_kills": [],      // e.g. {"event": 571, "tool": "Bash", "form": "pkill -f \"node server.js\""} in r2-checkers-sonnet
               "model_commits": [{"event": 463, "tool": "Bash", "forms": ["git add", "git commit"]}],
               "limits": "a list to confirm: no hit is not proof (an edit by interpreter code such as a python3 heredoc, a shell apply_patch or git apply, a kill by numeric pid or by port, ...) and a hit can be quoted text read as a command ..."},
     "refusals": {"count": 5, "repeated": 1, "unstaged": 0, "limits": "a repeat needs a known stage (the stage join is whole seconds and needs timeline.jsonl) and the same whole first line as the refusal just before it; ...",
                  "items": [{"event": 449, "verb": "complete", "exit": null, "stage": "release-plan", "line": "ShipLoop navigator: ShipLoop keeps this run's planning knowledge ...", "repeat_of": 1},
                            {"event": 472, "verb": "workspace", "exit": null, "stage": "release", "line": "ShipLoop workspace blocked: return plan has unresolved path dispositions", "repeat_of": null}, ...]},
     "end_state": {"status": "done", "stage": "done", "unaccepted_stage": null, "status_reason": null, "blocked_by": null, "awaiting": null, "unverified": null},
     "improve_packets": {"read": 8, "carried": {"goal": 0, "done_when": 0, "checked_by": 8, "output": 8, "recovery": 8},
                         "missing": [{"action": "nav-01d66d66...", "stage": "test-spec", "labels": ["goal", "done_when"]}, ...]}}

`exit` is null for a refusal behind a pipe (the host showed no exit). `repeated`, `accepted_ran` and a suite's `zero_ran` are null when unmeasured. A blocked run adds, for example,
`"end_state": {"status": "blocked", "stage": "system-test", "blocked_by": "access", "awaiting": {"kind": "present", "no_default": true}, "status_reason": "access: ...", ...}`
(v1230-battleship-grok-none). A page could show per stage `evidence.stages[]` joined to `stages[]` by `action` (the block carries the action id, no positional match): `class`,
`records`, `declared`, `lacks`, and a chip "declared script-run, no record" where the stage is in `declared_script_run_without_record`. `refusals.items[].repeat_of` can mark the stage
card. `edits.limits`, `refusals.limits` and the word "heuristic" mark the lists to confirm. **Please adopt the five-question Improve table** (`fidelity.IMPROVE_QUESTIONS`, goal, done
when, checked by, output, recovery, anchored to `shiploop_navigator.py`) into the exporter as `stages[].carriedImprove`; the harness then deletes its copy (the part is TEMPORARY, S-12).
Contract names the harness reads from the exporter (it degrades to `unmeasured` if they move): `stage_catalog`, `load_stage_spec`, `effective_exit_check`.

## Fix round (reviews A and B of head 0bd77328)

Both reviews found no saved run that triggers a blocker (the saved runs list the same facts as before), but two were the S-9 blind spot in another form or a verdict word. Commits, in
order: `59fed52f` docs (SPEC, README, journal and LEARNINGS first), `352eefb2` fixtures, `d7ca6232` metrics helpers, `89526a38` declared kinds and evidence, `29fee8b4` release-verify and
nulls, `9c32c6f7` refusals, Improve packets, header, `5bea5955` detectors, `63feec5a` portable block, wiring and loader, `55b204e8` limits wording and catalog. Each item below: fixed
(where, test) or documented; none rejected.

| # | review | disposition |
|---|---|---|
| 1 | A1 | **Fixed** (`89526a38`): `needs`/`lacks` from the stage table's declared runs (`RUN_KIND`), listed when ANY needed kind lacks its record; lint option `off` needs no lint gate; unknown runs named. Test `test_a_stage_declaring_two_scripts_is_listed_when_one_of_them_left_no_record` (the review's exact deletion on r3 and r1 extracts); saved runs still list none. |
| 2 | A2=B1 | **Fixed** (`29fee8b4`): `release_verify` `{where, kind, passed}` from the latest record by `created_at` then number; printed "release-verify record: <where>, passed true\|false\|unknown". Tests for a failed and a null record, verify10 vs verify2, the whole line (M45). |
| 3 | A3 | **Fixed** (`9c32c6f7`): `repeated` null + `unmeasured["refusals.repeated"]` when no refusal has a stage; `refusals.stage` note when partly staged; the old test changed to assert null. |
| 4 | B2 | **Fixed** (`29fee8b4`): `accepted_ran` null + note when no row carries the key (8 of 11 runs, both v1220); `zero_ran` null per suite with no counted row; line "zero-ran n of m counted" / "unmeasured". |
| 5 | B3 | **Fixed** (`29fee8b4`): `build` compares `metrics.verifications` with the JSON reader on the live folder (`unmeasured["validation.readers"]`, both values); `metrics.verifications` untouched; extract agreement test kept. |
| 6 | B4 | **Documented and pinned** (`59fed52f`, `5bea5955`): README/SPEC say `model_glue`'s write reason is frozen and narrower (no `sed -i`, `perl -i`, workspace names; reads `mkdir`); a test pins that every glue write hit that is a real write to an owned path is also listed (7 constructed commands; the saved runs add none). |
| 7 | A6 | **Fixed** (`5bea5955`): `ps\|grep\|xargs kill`, `while read p; do kill`, `timeout`, `{`, `!`, `xargs pkill` prefixes; quoted text blanked (the three false positives pinned as none); kill by port documented. The five kills stay; **8493 now appears** (v1220-battleship-grok-medium-none). |
| 8 | A7 | **Fixed** (`5bea5955`): fallback dropped; only add/commit subcommands; then/do/else/(/env/xargs/assignment prefixes. Tests for the review's five false forms. |
| 9 | A8 | **Fixed** (`5bea5955`): anchored `OWNED` (product `start.json`, `packet.json`, `run-terminal.json`, `until-loop.md` not listed); heredoc marker line kept (`cat <<'EOF' > owned`, `<<EOF \| tee owned` found); `(echo x > owned)` target; `perl -0pi`. Rest documented in the README. |
| 10 | A4 | **Fixed** (`63feec5a`): through-main tests give the fake plugin a stage table and assert tool_calls_seen > 0, edits and refusals measured, `declared` measured. M28, M29 red. |
| 11 | A5 | **Fixed** (`9c32c6f7`): real packet with each label dropped / mentioned mid-line, for all five labels. M25, M26, M27 and anywhere-in-line variants red. |
| 12 | A9 | **Fixed** (`352eefb2`, `63feec5a`): extracts keep every call naming `.shiploop-runs/`, `.shiploop-improve`, `until-loop`, kill or git (see size below); block strips the run and home folders; test renamed and narrowed; limits in the test docstring. |
| 13 | B5/A14 | **Fixed** (`5bea5955`): pins for `git apply`, `apply_patch`, a relative path after cd (also a redirect), a wrapper-hidden verb (counted with verb `unknown`), port and pid kills. |
| 14 | B6 | **Fixed** (`59fed52f`): SPEC, README and `unwrap_shell` say the Codex glue count is not comparable: on the 1.21.0 run unwrapping changes the glue answer on 731, 776, 779 only, each removing a heredoc-prose commit; the undercount direction is shown on a constructed string only. |
| 15 | B7 | **Fixed** (`59fed52f`): journal and LEARNINGS say the five kills are the set the audit verified, all reproduced; the plan row names no count. (Commit messages `0e60619e` and `d72d11cc` cannot be amended.) |
| 16 | B8/B16 | **Fixed** (`59fed52f`, `9c32c6f7`): attribution corrected (audit `safer_alternative`, not the plan row), TEMPORARY in the SPEC row and README, hand-off item above; `read: 0` for a run with no Improve child, unmeasured only for the 1.22.0-and-earlier layout or children without files. |
| 17 | B9+A13 | **Fixed** (`9c32c6f7`): `hosts`, `mixed_host` dropped from the header (tests, README, journal); `unclassified` printed. |
| 18 | B10 | **Fixed** (`9c32c6f7`, `55b204e8`): `refusals.limits` and the printed qualifier; "lower bound" kept out of the printed report; `edits.limits` reworded to "a list to confirm". |
| 19 | B11 | **Fixed** (`d7ca6232`): `ToolLog.call` target is `target_paths(arg)[0]`. |
| 20 | B12 | **Fixed** (`59fed52f`): SPEC non-regression names `ToolLog.sequence`, `ToolLog.failure_events`, `metrics.target_paths` (this journal's deviations list names them plus `metrics.NOT_APPLICABLE` and `metrics.within`). |
| 21 | B13+A10 | **Fixed**: printed example regenerated (lint 6, no "lower bound" claim), suite_catalog says 140 tests / 9.0 s, "0-based line index", v1230 carry-forward reads script. |
| 22 | B14 | **Documented**: error block in the README and the hand-off above. |
| 23 | B15 | **Fixed** (`59fed52f`): README says the class comes from the records that exist, never from `declared`. |
| 24 | A10 | **Pinned** (`89526a38`, `29fee8b4`, `9c32c6f7`, `d7ca6232`): M11, M12, M13, M18, M22, M23, M30, M31 each fail without the line they name (list below). |
| 25 | A11 | **Fixed** (`5bea5955`): `unwrap_shell` via shlex (3 words), pattern fallback; on the full 1.21.0 run all 1356 wrapped commands unwrap; segments that fall back to whitespace splitting fall from 242 to 2 commands because a separator inside quotes no longer splits (the earlier "30" was a different count). README sentence corrected. |
| 26 | A12 | **Fixed** (`89526a38`): a ref is the row's own only when it names the row's action. One saved row moves (v1230-battleship-sonnet skill-validate: sentence -> file). |
| 27 | A15 | **Fixed** (`352eefb2`): 60 advisory-lint placeholders removed, macOS temp id rewritten, `extract.py` takes the input folder and derives the user name. |
| 28 | B17 | **Fixed** (`352eefb2`): the size assertion is a tripwire at about 4 times the largest block (15 KB), and the extract limits are in the test docstring. |
| 29 | B18 | **Fixed** (`d7ca6232`, `63feec5a`): `metrics.NOT_APPLICABLE`, `metrics.within`, `fidelity.load_exporter` (used by `run.review_export`). |

Real figures re-run on the saved runs after the fix round: evidence classes unchanged on ten of the eleven runs (only v1230-battleship-sonnet moved, above); script-owned edits still exactly two
(493, 414); kills 571, 548, 2838, 858, 7711 plus 8493 in v1220-battleship-grok-medium-none; `declared_script_run_without_record` empty on all eleven; the review's deletion test lists test-green,
regression and static-checks on both extracts. The v1220 Grok run also lists two `search_replace` edits of its `return-plan.md` (events 10847, 10849), the round-1 hand edit. New fixture size:
2.8 MB in 468 files (before: 1.2 MB in 520 files). Deferred to the coordinator, not done: wiring `end_state` to group G4's shared blocked-detail helper (the blocked reading is one private function,
`_blocked_reading`, with its guard unchanged).

Mutants of the review (its labels; its literal patterns changed with the code, so equivalent mutants of the new lines were applied, each red): M11 skipped row not exempt, M12 advisory lint counted, M13
quality record dropped, M18 release taken without `where`, M22 first `unverified` list, M23 `no_default` always true, M25, M26, M27 (and their anywhere-in-line variants), M28 no ToolLog,
M29 no engine scripts, M30 inbox not the row's own, M31 stage-window boundary swapped (in `metrics.within` and in `stage_of`), M45 release text dropped from the printed line.

## Review of my own detectors, and what it changed

Each of these was found by rereading the detectors against the saved commands, and each has a case that failed without the change:

- The first `sed -i` reading took the sed script word as a file (`r1-checkers-sonnet` event 130 held an expanded `$R/scratch/...` inside the script text); the script operand
  (the word after `-e`, else the first operand) and BSD sed's empty suffix are no longer files.
- The first kill pattern had no multi-line anchoring, so it found 858 and missed 7711 (`r3-battleship-grok-none`); it also missed a `pkill` after `then`, `do` or `else`.
- A commit's form was the last word `add` or `commit` of the matched text, so `git -C /x/add-dir commit -m "add x"` read as `git add`; it is now the git subcommand.
- The lint evidence is the gate (`lint/<action>.gate<N>.md`) only: an advisory lint pass says it is "not exit-criteria evidence" (v1230-battleship-sonnet's carry-forward has two advisory
  passes and no gate; it reads `script` through its verify record, with `improve` in its records). No saved run's class changes between the variants.
- The extractor paired a result with the last call that had its id, so Codex's repeated `item_N` ids lost earlier calls from the extract (event 1012 was missing); results now belong to the
  latest call with the id, and one Claude message with several `tool_use` blocks keeps them all. Refusal text was joined to its prefix on one line, which hid the refusal line from the
  `^ShipLoop` anchor; and a heredoc cut at the end of a Codex wrapper string needed the closing quote in its terminator pattern.
- The first printed edits line said "a lower bound", which `ReportedCostThroughMainTest.test_a_session_the_run_killed_is_named_beside_the_cost_and_is_not_a_baseline_key` (a whole-report
  `assertNotIn("lower bound", printed)` on a clean run) rejected; the printed line now says "no hit is not proof" and the existing test is unchanged.
- The fix round's own finding: the extractor's heredoc cut unbalances a Codex wrapper's quoting (21 wrapped commands of the extract), so the unwrap test asserts the uncut ones; the uncut run
  folder unwraps all 1356.

## Tests and verification

`test/shiploop-e2e-fidelity.test.py`: 140 tests (ToolLog additions 9, shared helpers 5, shell unwrap 7, evidence 30, validation 17, edits 21, refusals 12, end state 8, Improve packets 13, workspace
names 1, block and lines 8, through `run._main` 9), registered in `test/suite_catalog.py` (9.0 s; 8.1 s measured under load) with the pinned counts in `test/test-groups.test.py` raised to 71 and 112.
Mutation checks (a mutant of the implementation run against the file) turned tests red for every item listed above and, in the first round: class precedence swapped, note folded into file, skipped
prefix dropped, null counts counted, `MODEL_INPUT` exclusion dropped, the shell unwrap dropped, the workspace-name match dropped, multi-line kill anchoring dropped, a repeat judged on the cut line or
without the stage, the sed script read as a file, a standalone redirect's target read as an operand, the per-part fail-open handler narrowed, the no-tool-call guard dropped, the unmeasured notes dropped,
the Improve receipt or the `improve_results` route dropped, the unclassified branch dropped, the call sequence keyed by id, the whole-line field cut, and the `metrics.json` key renamed.

Commands run in the worktree at the final head, real results: `python3 test/shiploop-e2e-fidelity.test.py` 140 tests OK in 8.4 s; `python3 test/shiploop-e2e.test.py` 404 tests OK in 109.2 s (no test of that file was edited or added); `python3 test/shiploop-e2e-runrecord.test.py` 6 OK;
`python3 test/test-groups.test.py` 21 OK; `python3 test/shiploop-run-review.test.py` 363 OK in 22.7 s; `bash test/run-all.sh --group quick --changed-from 30a3b40a` PASS, with shiploop-e2e, shiploop-e2e-runrecord,
shiploop-e2e-fidelity, shiploop-run-review and test-groups among its suites. The machine was loaded by sibling worktrees' suites; no `GIT_CONFIG_*` variable was exported (the real-git tests isolate their own).

## Open risks and what was not verified

- No live run: every figure is from saved runs. The Codex figures are one run of the old layout (1.21.0); a Codex run of the current layout would show whether the unwrap holds on every command
  shape (all 1356 commands of the 1.21.0 run unwrap, and 2 of its commands fall back to whitespace splitting inside a segment).
- The edit and kill detectors are heuristics over command strings: a quoted `>` word reads as a redirect, a product file named like a workspace file is listed, a kill by port is not seen. They list
  facts for a reviewer and never decide anything; precision is known only on the saved runs (every listed hit read: 2 of 2 edits and 5 of 5 kills true, plus 8493 and the two v1220 Grok edits).
- Coupling: the exporter's `stage_catalog`, `load_stage_spec`, `effective_exit_check` (unwritten contract with the session that owns it; the block degrades to `unmeasured`), the engine's record file
  names (`tests/*-verify*.md`, `lint/*.gate*.md`, `quality/*-terminal.json`, `backchain/*/check-*.json`, `improve/*/receipt.md`, `packets/*-improve.md`), the stage table's `completeRuns` names
  (`RUN_KIND`) and the Improve packet wording (pinned by a test against `shiploop_navigator.py`). `test/shiploop-e2e-fidelity.test.py` also imports `test/shiploop-e2e.test.py` for its fake hosts
  (`PrintedCase`, `isolate_git`).
- Merge: `metrics.py` (`ToolLog.call`/`result`/`collect` signatures; group G2's `ToolLog.feed` extraction should pass `event=number` and keep `collect(..., tools=)`; `NOT_APPLICABLE`, `within`),
  `run.py` (`_main` around the `metrics.collect` call and the printing loop, the import lines, `review_export`'s loader, the docstring), `suite_catalog.py`, `test-groups.test.py`, `SPEC.md`, `README.md`,
  `LEARNINGS.md`. Group G4's `hosts_used`/`mixed_host` (runrecord) and its blocked-detail helper (`end_state._blocked_reading`) meet this block there.
- The fixtures are 2.8 MB in 468 small files: every call that names a run, Improve or Until Loop directory, a kill or git is kept (results only for refused or failed ShipLoop calls).
