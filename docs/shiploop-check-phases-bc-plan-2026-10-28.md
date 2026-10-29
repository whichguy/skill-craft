---
Execute: ask
---
# ShipLoop phases B and C: `shiploop check` and the loop that ends when the check says yes (plan, 2026-10-28)

Status: draft for the owner's approval. No code is written yet.

Sources: [the owed-outcome journal](shiploop-owed-outcome-journal.md): "Design v3", "Revised after Astra's v3
review" (the phases table and the owner's naming decision), the intent audit (I8, I9, I12, I13) and the 2026-10-28
round; [the trims plan](shiploop-trims-plan-2026-10-28.md) (T1-T4, all landed on main: `d09042f0`, `16a3279f`,
`aaad2113`, `b2e1acb7` and `f871c36c`; T1 and T2 shipped in 1.19.0). Code references are to symbols on `origin/main`
`917e0c2b` (ShipLoop 1.20.0).

## What the owner gets

- **Phase B.** `shiploop check` becomes its own verb and `complete --check-only` goes. Both commands run one
  evaluator, so the check and `complete` can no longer disagree (F15). The check records one answer, yes or no with
  its reason, tied to the action, contract, result draft, candidate tree, base run and floors. `complete` accepts a
  matching yes without running the tests again, and asks again if any of those changed.
- **Phase C.** Each inner stage's Until Loop gets one exit check: `shiploop check`. The loop ends only when the check
  says yes, or when the model reports the step blocked. Then three receipt exemptions and the packet prose that
  repeats the check, receipt and restart rules are deleted.
- **What the data predicts (new, below).** Neither phase should cut commands per inner step. The model already runs
  one dry run before every inner `complete`, and no inner `complete` was refused in the last full run. The real
  per-stage saving in the data is at the outer stages, where every `complete` was preceded by a dry run that the
  callback line invites. B can stop that invitation (decision D3); the slice batch the brief names does not reach
  outer stages, so the plan adds a small full-run measure for it.

## Facts the plan rests on

Each is from code at `917e0c2b` or from committed evidence.

| # | Fact | Source |
|---|---|---|
| P1 | `complete --check-only` is a branch inside `shiploop_navigator.dispatch`: a `check_only` flag threads through `_check_submitted_evidence`, `_inner_gates`, `_lint_gate` (report-only), `_test_loop_gate` (`red_check`, then a non-counting `loop_run` and `mutation_check`), `_test_rerun_gate`, `_step_proof_gate`, and `owner_notes.hold_text`. It skips `loops.check_terminal` and `loops.open_send_back`, prints "ShipLoop check-only: every script gate ... accepts", and returns before `apply`. | code |
| P2 | The divergence (F15): the check's candidate run is held to floors from the latest *counted* base record (`test_loop.floor_detail` reads `_latest_base(passed=True)`), while the check's own base run goes to `tests/<action>-red-check.md`, which sets no floor. At `complete`, `base_check` writes a counted base record, the floor rises, and `_reused` refuses the check's run. Pinned by `test_a_check_only_run_below_the_floor_the_base_run_sets_at_complete_is_run_again_not_taken`. | code, test |
| P3 | `complete` already takes some of a passing check's work when the tree is unchanged: the candidate run (`test_loop._reused`, owner decision D5 2026-10-17) and the step Proof (`test_loop.step_proof` matching). It reruns the base run, the mutation check, lint and validate-existing's reruns. | code |
| P4 | The Until Loop 0.8.0 runtime supports frozen `exit_checks` `{id, clause, command}`. The runtime never runs a check: the model runs the packet's `verify_script` in its own shell, which pipes each check's exit code to `until_loop_ephemeral.py record`. `_transition` refuses `satisfied` without a fresh recorded run, or after the workspace tree changed, and completes only when every check passed. A model may change a check's command through `check_repairs` (at most `MAX_REPAIRS_PER_CHECK` = 2 per check, an existing runtime limit). | `skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py` (`_verify_script`, `record`, `_transition`) |
| P5 | ShipLoop's stage contracts carry no `exit_checks` (F8; `shiploop_loop_contract.contract` has no such field). `check_loop_packet` compares none of `exit_checks`, `last_check_results` or `check_repairs` (F16). | code |
| P6 | Three of `check_terminal`'s four routes around the receipt exist only because the gates run after the loop ended (F13): the `loops/<action>-send-back-open` marker (`open_send_back`), `_remedy_open` (a test run that could not run) and `_verify_refused`. | code |
| P7 | No live ShipLoop run has ever executed a `verify_script`: 0 `UNTIL-LOOP-RECORDED` lines in arm A's and arm B's event streams. | `events.jsonl` of `pa-ds-battleship-4ed4e3`, `pb-hook-owed-1-232e69` |
| P8 | Dry runs per stage, read from the run traces ([trace_check_pairs.py](shiploop-owed-outcome-evidence/trace_check_pairs.py), [output](shiploop-owed-outcome-evidence/trace_check_pairs.out)). Arm A (battleship, 372 min): inner stages 55 dry runs (35 yes, 20 no) and 35 `complete`s, **all accepted**; outer stages 29 dry runs (20 yes, 9 no) and 29 `complete`s (23 accepted, 6 refused); Improve 6 dry runs, all refused (no draft to check) and 16 `complete`s. Owner-note hello run: inner 7 dry runs and 7 `complete`s, all accepted; outer 17 and 17; Improve 2 refused dry runs. Arm B slices: about one dry run per inner `complete`. | traces, firm counts |
| P9 | A `complete` refused right after a passing dry run on the same action: 5 times. Four were in the two full runs, all at outer stages (intake, system-test, release-plan, system-test-author); the gates named there run the same way in both modes, so a draft edit between the calls is the likely cause (the trace cannot show it). One was inner, in arm B owed 1 at test-spec: the dry run passed, then `complete` refused 15 s later with "test-spec accepts only done, blocked, send-back". That rule lives in `loops.check_terminal`, which the dry run skips, so a dry run cannot catch an outcome the stage does not allow. | same output; owed 1's `run/trace.jsonl` |
| P10 | The callback line itself invites the dry run: `shiploop_prompts.CALLBACK_REASON` reads "run it exactly as printed, adding only --check-only to test before it accepts". The inner Work texts add it again (`shiploop_loops._CHECK_ONLY` in WORK and REPEAT for step-plan, test-spec and test), and so does `_checked_line` ("repeat it until it accepts"). | code |
| P11 | Keepalive binds a session to a run from `--run-dir` on a driving verb (`shiploop_keepalive.COMMAND_RUN_DIR`), where `complete --check-only` matches `complete`; the protocol counts it as a callback attempt (`CALLBACK_VERBS`), which is part of the stop hook's progress. | code |
| P12 | Default run directories are outside the repository (`<repo-parent>/.shiploop-runs/...`), so files ShipLoop writes there do not change the Until Loop's workspace tree. | `shiploop_protocol` `--run-dir` help, `_workspace_tree` |

What P8 means for the brief's hypothesis. At an inner stage today a model runs: start the loop, work, `complete
--check-only`, the loop's `done`, `complete`. After C it runs: start the loop, work, the loop's `verify_script`
(which runs the check), the loop's `done`, `complete`. The dry run becomes the `verify_script`, so the count stays
the same. C removes the tail where `complete` is refused after the loop ended, but arm A had none. A step that passes
without a dry run today gets one more command after C, because the check becomes mandatory. The saving the data shows
is at the outer stages: 29 of 29 outer `complete`s in arm A and 17 of 17 in the hello run followed a dry run, and when
the dry run says yes, the `complete` after it repeats the same gates.

## Phase B: one evaluator, `shiploop check`

### Design

- **One question, one code path.** The gate sequence that `dispatch` runs for `complete` moves into one function,
  `shiploop_navigator._evaluate(core, root, state, action_id, submitted, *, count)`. It returns an answer: yes or
  no, the reason (the first refusal, as today), the `Gates:` lines and the preparatory paths. `count` decides only
  where records go and whether they count: `check` writes the check records and counts nothing; `complete` writes
  the numbered records as today. Every gate keeps its order and its text.
- **The stage's allowed outcomes are part of the question (P9).** The rule "`<stage>` accepts only ..." moves from
  `loops.check_terminal` into `_evaluate`, so the check refuses an outcome the stage does not allow. Only the receipt
  comparison stays outside the check, because the receipt does not exist while the loop runs.
- **The base and the floors come from the same run (fixes F15).** `test_loop.floor_detail` takes the base record the
  evaluation just made, so the check's candidate run is held to the floor that `complete` would set. The check's base
  run is the real `_base_run`, written to `tests/<action>-base-check.md`; `red_check`'s own record goes.
- **One answer record.** `checks/<action>.md` (stored record) holds: the answer, the reason, the gate lines, the
  paths of the records the check made, and the key: state revision, ShipLoop build version, the contract's sha256
  (inner stages), the draft file's sha256, the candidate tree (`test_loop._tree`), the base (the item's lint base tree,
  `preparatory_base` and the base command list), a hash of the floors (`floor_detail`) and the lint mode. A new check
  replaces the record.
- **`complete` accepts a matching yes.** After its unchanged steps (wrong-action check, result read, owner-note hold,
  inner receipt check and `cite_receipt`), `complete` computes the key now. A yes with an equal key is taken: its base,
  candidate, mutation and Proof records are written as the next numbered records with `reused` naming the check
  record, as `_reused` does today for the candidate. Otherwise `complete` runs `_evaluate(count=True)`, exactly as
  today. So a matching yes cannot be refused, and any change since the check means the gates run again.
- **Lint in fix mode (decision D2).** The check never edits product files. If the lint pass would change a file,
  the check says no and names a new `shiploop lint --fix --run-dir R --action A`, which applies the same fix the gate
  applies today. A matching yes then leaves `complete` nothing to fix. A `complete` without a matching yes keeps
  today's fix-and-refuse-once.
- **Where the check is offered (decision D3).** The verb works on every producer stage, as `--check-only` does.
  Packets print the check command only at inner stages, as the step's way to ask before its loop's `done`. At outer
  stages the callback line stops inviting a dry run: `complete` already refuses without changing anything. The
  Improve stage refuses `check` (no draft), as it refuses `--check-only` today.
- **Names.** "the check says yes" and "the check says no" in printed text; `checks/` and the `-check` suffix for
  records (`tests/<action>-check.md`, `-step-proof-check.md`, `-mutation-check.md`, `-base-check.md`). Following the
  consistent-nomenclature rule, the rename lands everywhere in B's commit: code, references, glossary, tests and the
  harness readers.
- **Exit codes.** 0 on yes; 2 (`EXIT_BLOCKED`, as a refusal today) on no. Phase C relies on this: an Until Loop check
  passes only on exit 0.

### Files and symbols (B)

| File | Symbols | Change |
|---|---|---|
| `skills/shiploop/scripts/shiploop_check.py` (new) | `answer_path`, `answer_key`, `record_answer`, `matching_yes` | The answer record and its key; imports no navigator code. |
| `skills/shiploop/scripts/shiploop_navigator.py` | `dispatch`, new `_evaluate`, `_inner_gates`, `_test_loop_gate`, `_test_rerun_gate`, `_step_proof_gate`, `_lint_gate`, `_check_submitted_evidence`, `_checked_line`, `_loop_lines`, `_submitted_result` (comment), the Improve-stage refusal in `dispatch` | `check` joins the supported verbs; the `check_only` flag becomes `count`; the check-only print block goes; `complete` takes a matching yes. |
| `skills/shiploop/scripts/shiploop_test_loop.py` | `check_only_path`→`check_path`, `step_proof_check_only_path`→`step_proof_check_path`, `mutation_check_only_path`→`mutation_check_path`, new `base_check_path`, `base_check(count=)`, `floor_detail(base=)`, `_reused`→`take_check`, `red_check`, `reuse_note` (deleted), `verify`, `loop_run`, `step_proof`, `_proof_records`, `__all__` | One base run for both; floors from that run; `complete` takes the check's records. |
| `skills/shiploop/scripts/shiploop_mutation.py` | `mutation_check(count=)`, the record path and the "does not count" tail | Renamed path; `complete` takes the check's record. |
| `skills/shiploop/scripts/shiploop_expectations.py` | `check_complete(tag=)` | Tag `check`. |
| `skills/shiploop/scripts/shiploop_lint.py` | `main` (advisory verb), `gate` | `--fix` on the advisory verb (D2); `gate` unchanged. |
| `skills/shiploop/scripts/shiploop_protocol.py` | the subparser table, `CALLBACK_VERBS`, the `complete` subparser | New `check` (`--run-dir`, `--action`, `--result`); `--check-only` removed; `check` counted as a callback attempt (P11 parity). |
| `skills/shiploop/scripts/shiploop_keepalive.py` | `COMMAND_RUN_DIR` | `check` binds a session to its run, as `complete --check-only` did. `DRIVING_COMMAND` unchanged: `check` prints no packet. |
| `skills/shiploop/scripts/shiploop_trace.py`, `shiploop_trace_page.py` | the command event's `check_only` field, `checks_failed`, the refusal filter, the event text | The check is the `check` verb; a failed check is a check, not a refusal. |
| `skills/shiploop/scripts/shiploop_owner_notes.py` | `hold_text(check_only=)`→`hold_text(check=)` | Text "ShipLoop check:". |
| `skills/shiploop/scripts/shiploop_prompts.py` | `CALLBACK_REASON`, the test duty's item 1, the verify duty's run item | The callback line stops inviting a dry run (D3); inner duties name the printed check command. |
| `skills/shiploop/scripts/shiploop_loops.py` | `_CHECK_ONLY` and its uses in `WORK` and `REPEAT`; `check_terminal` | Name the check command and "the check says no" (C rewrites these again); the allowed-outcome rule moves to `_evaluate`. |
| `skills/shiploop/scripts/shiploop_consumer_delivery.py` | `validate_settled` docstring | Wording. |
| `skills/shiploop/references/` | `inner-loop.md`, `state-files.md` (`tests/` row, new `checks/` row), `status-display.md`, `glossary.md` (callback row; new rows "check", "the check says yes"), `test-loop.md` | Wording and the record table. |
| `skills/shiploop/README.md` | the check-only sentence | Wording. |
| `changes/shiploop/shiploop-check-verb.md` (new) | — | `bump: minor` (a flag is removed, a verb added; D5). |

`SKILL.md` (at its 30,500-byte bound) does not mention the flag and is not touched.

Harness readers (test/ only, no change note): `test/shiploop_e2e/run_trace.py`, `flow.py`, `status_card.py`,
`metrics.py`, `fidelity.py` read a check from the `check` verb, and still from `check_only` for runs made before B
(committed evidence predates the rename). Also `README.md`, `packet_obligations.json` and `packet_changes.json`
there, and `test/fixtures/shiploop-card-ledger.json`.

### Removed by B

- The `--check-only` flag and every `check_only` parameter (one supported version: no alias).
- The divergence F15: the separate red-check record for the check, and floors read from an older base.
- The divergence P9: a dry run that skipped the stage's allowed-outcome rule.
- `test_loop.reuse_note` and the "That complete takes this test run ..." sentences: a yes is taken whole.
- The base run, mutation check, lint pass and validate-existing reruns that `complete` repeats after a passing
  check on unchanged files.
- At outer stages, the printed invitation to dry-run every callback (D3).

### Tests that prove B

New suite `test/shiploop-check.test.py`, registered in `test/suite_catalog.py`:

- `test_the_check_and_complete_agree_on_the_floor_the_base_run_sets`: F15's fixture, inverted. On main the check
  says yes and `complete` refuses; after B both say no. **Fail-first** on main.
- `test_complete_takes_a_matching_yes_without_running_a_command`: a counting runner stub sees zero commands at
  `complete`; the numbered records name the check record under `reused`.
- `test_each_change_to_the_key_makes_complete_ask_again`: one subtest each for the draft, a one-byte tree edit, the
  contract, the base commit, a floor (a counted run of another action) and the revision; each runs the gates.
- `test_the_check_changes_nothing_the_run_counts`: `refused_runs`, floors, state, revision and Git are unchanged after
  a no and after a yes.
- `test_the_check_refuses_an_outcome_the_stage_does_not_allow`: owed 1's case (P9). **Fail-first** on main, where
  the dry run passes.
- `test_the_check_exits_zero_only_on_yes`, `test_complete_check_only_is_a_usage_error`,
  `test_check_on_an_improve_stage_is_refused_with_the_complete_command`.
- `test_in_fix_mode_a_yes_leaves_complete_nothing_to_fix` and
  `test_a_finding_the_fix_would_remove_is_a_no_naming_lint_fix` (D2; settles U1 below).
- `test_outer_packets_do_not_invite_a_dry_run_and_inner_packets_print_the_check` (D3).

Existing tests that change with the rename or the new behaviour: `shiploop-test-loop` (49 references, including the
F15 test, `test_complete_after_a_passing_check_only_on_an_unchanged_tree_takes_that_run_and_says_so` and
`test_check_only_runs_the_mutation_check_without_counting`), `shiploop-handoff` (23), `shiploop-callback-contract`
(19), `shiploop-loops` (13), `shiploop-navigator-contract` (8, including
`test_complete_check_only_runs_the_gates_and_accepts_nothing`), `shiploop-owner-notes` (4),
`shiploop-actual-improve-cli` (4), `shiploop-trace` (2), `shiploop-head-order` (2),
`shiploop-packet-completeness` (1), `shiploop-keepalive` (binding and attempts), and the harness suites
`shiploop-e2e-run-trace`, `shiploop-e2e-status-card`, `shiploop-e2e-efficiency`, `shiploop-e2e-release-slice`,
`shiploop-e2e-packet-anatomy`, `shiploop-e2e-dodges`. The `shiploop-lint` "check only" hits are the lint catalog's
own term for linters run without fixing, unrelated; they stay.

## Phase C: the loop ends when the check says yes

### Design

- **The exit check.** `shiploop_loops._build` adds one entry to every inner contract:
  `{"id": "shiploop-check", "clause": "ShipLoop accepts this step as done now: shiploop check says yes on the current
  files and result draft", "command": "python3 <RUN>/shiploop check --run-dir <RUN> --action <ACTION> --outcome done"}`.
  `--outcome done` makes a draft with another outcome a no, so a yes always means "done would be accepted". To stop
  blocked or send back, the model reports `continuation_assessment: blocked` to the loop, as today.
- **The launcher.** Contracts name no install path (`shiploop_loops` module docstring). `<RUN>/shiploop` is a
  symlink to the entrypoint that last drove the run. `init` creates it, and every command that takes the run lock
  replaces it atomically, so a plugin update repoints it at the next `next`. The entrypoint resolves its real path,
  so imports work (checked in Astra's v3 review). The `python3 <path>/shiploop <verb>` form keeps the command
  readable by `COMMAND_RUN_DIR`, the status hook and the trace.
- **The receipt proves the check said yes (F16).** `check_loop_packet` also requires: `exit_checks` equal to the
  rebuilt contract's; an empty `check_repairs`, because repairing ShipLoop's check is refused, with the reason
  printed; and, for `complete`, one `last_check_results` entry `shiploop-check` with `passed: true`. Independently,
  `complete` takes the yes only from ShipLoop's own `checks/<action>.md` with a matching key (B), so a doctored
  receipt still meets the gates.
- **The exemptions go.** A gate that fails inside the loop is now a no from the exit check. The model fixes the
  work, or stops the loop blocked; a stopped receipt then supports `blocked` or `send-back`. So `check_terminal`
  keeps only "blocked before the loop started" and loses the `send-back-open` marker, `_remedy_open` and
  `_verify_refused`.
- **The packet says each mechanic once (S4, I12).** The loop's own instructions already carry the report schema, the
  `verify_script` and the exit clause each iteration. Packet lines that repeat them, or that describe a dry run or a
  restart after a post-loop refusal, are cut. The `Checked by` line becomes one sentence: the loop's exit check runs
  every gate.
- **Kept on purpose.** The step's per-edit checks (`shiploop_prompts._IMPLEMENT_CHECK_INLINE`); the second command
  at the step's end (`complete`); `delegation: ask-agent`; S2 (the outcome read from the loop's end), which stays a
  separate later decision (D7).

### Files and symbols (C)

| File | Symbols | Change |
|---|---|---|
| `skills/shiploop/scripts/shiploop_loop_contract.py` | `contract` | New required `exit_checks` field; the Improve child's contract (`shiploop_navigator.improve_start_contract`) passes `[]`. |
| `skills/shiploop/scripts/shiploop_loops.py` | `_build`, new `EXIT_CHECK_ID` and `exit_check`, `check_loop_packet`, `check_terminal`, `WORK`, `REPEAT`, `REPEAT_STEP`, `_CHECK_ONLY` (deleted), `RESULT_LINE`, `RESUME_RESULT_LINE`, `_RESULT_HEAD`, `RECEIPT_REF_LINE`, `REPORT_FIELDS`, `LOOP_RULE`, `invoke_lines`, the module docstring, `__all__` | The exit check in every contract; the receipt checks; the prose cut. |
| same | `open_send_back`, `send_back_open_path`, `_remedy_open`, `_verify_refused` | Deleted. |
| `skills/shiploop/scripts/shiploop_protocol.py` (or the `shiploop` core) | new `LAUNCHER`, its write at `init` and its refresh under the run lock | The per-run launcher. |
| `skills/shiploop/scripts/shiploop_navigator.py` | `dispatch` (the `open_send_back` call), `_test_loop_gate` and `_step_proof_gate` (refusal texts: a no inside the loop, with no restart), `_checked_line`, `_loop_lines`, `_check_submitted_evidence`, the check's `--outcome` handling | Exemption caller and prose. |
| `skills/shiploop/scripts/shiploop_test_loop.py` | `remedy_open`, `latest_attempt_could_not_run` (deleted if no caller remains), `base_check` refusal text, `_remedy`, `_remedy_sentence`, `_has_loop_packet`, `loop_lines` (the red-check line, D4), the module docstring | No restart after the loop. |
| `skills/shiploop/scripts/shiploop_prompts.py` | the test and verify duties' run items, any packet line naming the dry run | One route: the loop's `verify_script`. |
| `skills/shiploop/references/` | `inner-loop.md` (the exit check), `state-files.md` (`loops/` row loses the send-back marker; the launcher row), `test-loop.md`, `glossary.md` | Wording. |
| `test/shiploop_e2e/head_table.json`, `packet_head_table.json`, `packet_obligations.json`, `packet_changes.json`, `test/fixtures/shiploop-card-ledger.json` | — | New head sizes and obligations. |
| `changes/shiploop/loop-exits-on-check.md` (new) | — | `bump: minor`. |

### Removed by C

- The three receipt exemptions, the marker file `loops/<action>-send-back-open` and four functions (above).
- The fix-after-the-loop path: a gate refusal at `complete` after a complete receipt, then a loop restart.
- The `_CHECK_ONLY` clause in three Work texts, "a check-only refusal" in two Repeat texts, the result line's
  "If that refuses for the loop, run the start command above again", the "repeat it until it accepts" sentence and
  the duplicated report-field and receipt lines (F12 counted the receipt 8-10 times and the callback 5-7 times per
  inner packet).
- With D4 approved: the `red-check` verb, `navigator.red_check_command` and `test_loop.red_check`, since the exit
  check runs the base run.

### Tests that prove C

- `shiploop-loops`: `test_every_inner_contract_carries_the_shiploop_check_as_its_one_exit_check`;
  `test_a_receipt_whose_exit_check_was_changed_or_repaired_is_refused` (F16; **fail-first** on main);
  `test_a_complete_receipt_without_a_passing_recorded_check_is_refused`;
  `test_the_real_runtime_completes_only_after_the_check_says_yes` (the vendored runtime, a real run directory: a
  satisfied report without a recorded `verify_script` run is refused, a no keeps the loop active, a yes completes it);
  `test_a_gate_no_inside_the_loop_stops_blocked_and_send_back_is_accepted_from_the_receipt` (replaces the exemption
  tests).
- `shiploop-navigator-contract`: `test_the_launcher_points_at_the_running_entrypoint_and_is_repointed_after_a_move`.
- `shiploop-keepalive`: `test_the_check_inside_a_verify_script_binds_the_session_to_its_run` (the hook sees the
  heredoc's command text, I11).
- Deleted with the exemptions: `test_a_failed_run_does_not_open_send_back_before_the_cap_and_a_complete_loop_still_needs_done`
  (`shiploop-test-loop`), the `remedy_open` assertions there and in `shiploop-workspace`, and the loops exemption tests.
- Packet size: rerun [packet_position.py](shiploop-owed-outcome-evidence/packet_position.py) on
  `graph-dry-run --scenario delivery`; every inner head shrinks, and the check, receipt and callback are each named
  once in the head.

## Measure of success

### Harness addition (test/ only)

`docs/shiploop-owed-outcome-evidence/arm_b_metrics.py` gains `--per-stage`. It splits the host's commands
(`events.jsonl`) at each accepted `complete` in the run trace. For each inner action and its Improve child it reports:
commands to accept, ShipLoop calls by verb (`complete`, a dry run as either `complete --check-only` or `check`, the
loop's `start`, `done` and `verify_script`), refused `complete`s, seconds, and the accepted `complete`'s own
duration (`ms` in the trace). `measure` stays as it is, so the continuation numbers stay comparable with arm B.

### The batch

Run the same way as arm B: node-fix-bug, Claude host, DeepSeek v4.1 flash (`deepseek-v4.1-flash:1017-cloud`) on
Ollama, seed at step-plan, clear at `implement:inside`, `--resume-prompt names-next` (T4 removed the hook-text
conditions), no timeout, permission mode auto. Each arm builds from its own ref, so one checkout serves all three:

```bash
python3 test/shiploop_e2e/slice.py --case node-fix-bug --host claude --backend ollama --model deepseek-v4.1-flash:1017-cloud --seed-at step-plan --clear-at implement:inside --resume-prompt names-next --ref <arm sha> --output ~/e2e-runs/<date>/bc-<arm>-<n>-<hex>
```

| Arm | Ref | Samples |
|---|---|---|
| before | main when the plan is approved | 3 |
| B | B's last commit | 3 |
| C pilot | C's last commit | 1, before C's batch |
| C | C's last commit (after any pilot fix) | 3 |

### Pre-registered predictions and pass rules

| # | Measure | Prediction | Pass rule |
|---|---|---|---|
| M1 | Commands to accept per inner action (median per stage, and overall) | Unchanged within ±1 after B and after C (P8) | Not worse than before by more than 1 at any stage, overall median not above before |
| M2 | Duration of the accepted `complete` at the test and validate-existing stages | Falls after B: no base run, mutation check or rerun at `complete` | Lower median than before |
| M3 | A refused `complete` right after a yes with nothing changed | 0 after B, by construction | 0 |
| M4 | A refused `complete` after a complete receipt (the post-loop path) | 0 after C (already 0 in arm A) | 0 |
| M5 | Inner packet head size (dry-run scenario) | Smaller after C | Every inner head smaller |
| M6 | Verdicts (`process`, `inner_loop`, `no_overshoot`, `assembled`, `checks`, `no_redo`) | Unchanged | Every sample passes |
| M7 | C pilot: every inner loop completes through a recorded `verify_script` run; the runtime's refusals of a missing or stale run, per stage | Unknown (P7) | The pilot passes; if the model cannot run the script unchanged, stop and report before the batch |
| M8 | Outer-stage dry runs (only with D3): on one hello full run after B, against the owner-note run's 17 dry runs before 17 outer `complete`s | Near 0 dry runs, with outer refusals not above that run's | Observational, n = 1 |

Stop rules: any M6 failure, or M1 worse than its rule, stops the next phase until the cause is found and recorded in
the journal. n = 3 is interim evidence for one case on one model, as arm B was.

## Order and verification

1. **Start.** A worktree with a random suffix from the freshly verified `origin/main`. Rebase it on `origin/main` after
   each landed step.
2. **Before arm.** Add `--per-stage` (one commit, harness only). Launch the before batch from main's ref as a
   background task while B is built; journal the launch.
3. **B.** Build in this order: `_evaluate` with the fail-first F15 test; the answer record and `complete` taking a
   matching yes; the verb, the flag's removal and the rename; lint `--fix` (D2); the prompt lines (D3). Lint the
   changed files. Run the touched suites, then `test/run-all.sh --group quick --changed-from <merge-base>`.
   Commits: one per part, each verbose (the learning, the evidence file, the related commits), prompt commits state
   what they change and why (P8, P10). The change note goes in the first B commit.
4. **B round.** The B batch (and M8's hello run if D3 is approved), the results in the journal and a
   `test/shiploop_e2e/LEARNINGS.md` entry. This satisfies the release preflight for B's commits.
5. **C.** Build: the contract field and launcher; `check_loop_packet` with the fail-first F16 test; the exemptions'
   removal; the prose cut with the head table. Same checks and commit rules; its change note in the first C commit.
6. **C pilot, then C round.** One slice; then the batch; then the journal and a LEARNINGS entry.
7. **The owner's release decision.** One release with both notes, or B alone if C fails its rules. No push without
   the owner's go.

## Cost

- **Code.** B: one new module of about 200-300 lines; `dispatch` loses its check-only branches (about 60 lines) and
  gains `_evaluate` (about 100 lines moved, not new); renames across about 12 source files. C: about 40 lines added
  (exit check, launcher, receipt checks) and about 120 deleted (four functions, exemption branches, prose
  constants). Tests: about 15 new tests; updates in about 20 test files, mostly the rename.
- **Live runs.** 10 slices at 13-30 min each (arm B's slices took 13-30 min without the sleep), about 3.5-5 hours
  of wall time run one or two at a time, plus one hello full run (about 106 active min) if D3 is approved. DeepSeek
  flash on the paid Ollama subscription: no per-token charge.
- **Session time.** B about one working session; C about one; each round about half a session of analysis.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| DeepSeek flash does not run the `verify_script` unchanged (P7) | Loops never complete; C fails live | The C pilot (M7) before the batch; the runtime's refusals name the fix; stop and report if it fails |
| The key misses an input that changes a gate's answer | `complete` accepts a yes that a fresh run would refuse | The key holds every input the gates read; the per-input subtests; `_evaluate` stays the only gate code; the build version is in the key |
| The key holds an input that changes for no reason (a timestamp in the tree, a test that writes files) | `complete` runs the gates again; no saving but no harm | M2 shows it; record which input moved |
| Lint fix mode: report mode may not flag every file the fix pass would change (U1) | A yes, then `complete` edits files and refuses once | The two D2 tests settle it before the rest of B; else `complete` takes the yes only in report mode |
| The launcher dangles after a plugin update and before the next `next` | The check fails with exit 127, a no | The check's no names `next`; a test moves the entrypoint and checks the repoint |
| A model repairs ShipLoop's check through `check_repairs` | The loop completes on a weakened check | `check_loop_packet` refuses any repair, and `complete` needs ShipLoop's own matching yes |
| The check runs longer than a host shell tool's timeout (Claude: 10 min at most) | The script is cut and no result is recorded | The same exposure as `complete` today; unchanged; noted for the owner |
| The `verify_script` unsets the host session variables | A check that needs the session id misbehaves | ShipLoop's gates read none (checked when building); a test runs the check with them unset |
| Removing the dry-run invitation at outer stages (D3) raises outer refusals | Commands move from dry runs to refusals | M8 compares outer refusals; revert D3's text if refusals rise |
| The tail C removes (P6) never occurred in arm A | C's live gain is simplicity and smaller packets, not commands | Stated as M1's prediction; the owner decides C's value on M4, M5 and I13 |

Unknowns to settle while building: **U1** (lint, above); **U2** whether `test_loop.remedy_open` has a reader outside
the exemption (none found on main); **U3** whether `shiploop_status_hook._verb` needs `check` for its status line.

Limits: this plan adds none. It meets one existing limit, the runtime's `MAX_REPAIRS_PER_CHECK = 2` (P4), which
ShipLoop's check never reaches because any repair of it is refused. The owner asked to be consulted before limits
change; none changes.

## Decisions for the owner

- **D1.** Approve B as designed: one evaluator, the answer record and its key, `complete` accepting a matching yes,
  and the flag removed with no alias.
- **D2.** Lint fix mode: the check says no and names `shiploop lint --fix` (recommended), or the check applies the fix
  itself (it then edits files, against "change nothing").
- **D3.** Print the check only at inner stages and stop inviting a dry run in the callback line (recommended; P8 and
  P10: 29 and 17 outer dry runs in the two full runs), or keep offering it at every stage.
- **D4.** Remove the `red-check` verb in C (recommended; the exit check runs the base run), or keep it as a cheaper
  base-only probe.
- **D5.** Both change notes `bump: minor`, or B `major` because a flag is removed.
- **D6.** The measurement as above: three arms of three slices, a C pilot, and M8's hello run if D3 is approved.
- **D7.** Keep S2 (the outcome read from the loop's end) and the hand-back return command out of this change.
- **D8.** Accept that M1 is predicted not to move at inner stages; judge C on M3-M5 and the deletions, or drop C after B.

## Out of scope

S2 and the hand-back return command (D7); S6 (Improve as an ordinary step); I11 (ShipLoop running recorded test
commands inside `complete`, which neither phase changes); Hermes, which is excluded.
