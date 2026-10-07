# ShipLoop record register, 2026-10-07

One-time register of every record kind a ShipLoop run writes, taken from the code and checked against one real run.
Owner rule: ShipLoop never writes a document and abandons it, and never keeps two competing sources of truth for one
fact per worktree.

**Method.** Writers and readers come from `skills/shiploop/scripts` (grep plus reading the function). Each packet
instruction is quoted from the module that prints it. The real run is
`/Users/dadleet/e2e-runs/20261006/v1220-battleship-grok-medium-none` (Grok, Node Battleship, ShipLoop 1.22.0, two
work items, 52 accepted actions). Its host log is `events.jsonl`: 714 tool calls, 201 `read_file`, 146 `grep`, 169
terminal commands, and 5 `auto_compact_completed` events. "Opened" below means a `read_file`, `grep`, `list_dir` or
a terminal command naming that path; a record the model only listed in a callback is not counted. "Run dir" is
`<workspace>/.shiploop-runs/<id>/run`. "Unknown" means the log cannot tell.

**Classes.** AUTHORITATIVE: a script navigates or decides from it. DERIVED: a view regenerated from authoritative
state. RECOVERY AID: written so a cleared model can resume (main tenet, `skills/shiploop/README.md`); never proposed
for removal. INPUT: written by the host or a runtime for the script to consume. ARCHIVE: immutable copy with its
digest in state. SCRATCH: model-private. UNREAD: no script reader and no packet instruction.

## Table

Counts are files in the real run. "Opened" is from the host log.

| Kind | Writer (module.function) | Script readers | Packet tells the model to open it? | Class | Files | Opened in run |
|---|---|---|---|---|---|---|
| `state.md` | navigator.save (store.transaction) | protocol dispatch, navigator.dispatch, validate, every verb via store.read_record | "State: <run>/state.md" locator (navigator._run_rules); packets say state.md holds the queue | AUTHORITATIVE | 1 (157 KB) | 0 (model reads it only through packets and CLI output) |
| `status.md` | navigator.save: status_block(state) | none in `scripts/` (tests and E2E review tooling read it) | none; the same block is printed inline in every packet and by `shiploop status` | DERIVED, UNREAD by script and packet | 1 | 0 |
| `timeline.json` | navigator.save: _updated_timeline | navigator.load_timeline (emit pace line, _updated_timeline), progress_data._decode_timeline | none | DERIVED display data; not regenerable from state (holds real accept times) | 1 | 0 |
| `report.html` | navigator.save: _render_report (done or halted only) | progress_data.build_snapshot (identity hash) | "Report: <run>/report.html" printed on done (navigator.render) | DERIVED | 1 | 0 |
| `progress.html` | progress.publish (progress_render.render from progress_data.build_snapshot) | none (browser) | "use this file to track changes during this ShipLoop run" (navigator.packet_head), addressed to the user | DERIVED | 1 | 0 |
| `progress-observer.json` | progress.observe | progress.observe, sample, running, start, ensure (its own heartbeat) | none | DERIVED process status | 1 | 0 |
| `context-index.md` | navigator.save: context_index.render | none | "open it when you need the global picture, for example after compaction" (navigator._context_index_lines) | DERIVED + RECOVERY AID | 1 (77 KB) | yes: 2 grep + 2 read_file, once, after compaction 4 |
| `callback-attempts` | protocol._count_callback_attempt | protocol._callback_attempts (status JSON `progress` counter for the keepalive hook) | none | AUTHORITATIVE for the keepalive counter only | 1 (value 60) | 0 |
| `packets/<action>.md` | navigator.emit (store.atomic_write_text) | none; `next` rewrites it | "Read the full packet before acting" (navigator.packet_head); recovery line "reprints this head and rewrites the full packet" | DERIVED + RECOVERY AID | 53 (2.1 MB) | 44 distinct files, 58 read_file + 55 grep; reopened within the first five calls after all 5 compactions (first call after 3 of them) |
| `results/<action>.md` | navigator.save: _new_result_records, _result_record | planning_context.collect (byte-compares to state.accepted), context_index.read_first (path only) | "open each one whose content is not already in your context" (navigator._context_index_lines, "Read first") | DERIVED (copy of state.accepted[action]) | 52 (224 KB) | 14 calls (5 read_file, 9 grep) |
| `inbox/<action>.md` | host writes; save adds `inbox/.keep` | navigator._submitted_result (via _result_input_path), idempotent replay compare | "the result file is named below" (navigator._first_callback_lines) | INPUT, consumed once | 55 + `.keep` (240 KB) | model wrote 56 times, read 3 |
| `inbox/<action>-improve-notes.md` | host writes | navigator.improve-complete (`_optional_text_file`) | notes path is in the improve-complete callback (navigator._render_improve) | INPUT | 3 | model wrote 3 |
| `notes/<action>.md` | host writes | progress_data.build_snapshot (draft preview); context_index.pass_log_path (path only) | "open it first after a reset" (navigator._context_index_lines); contract resource "append what each iteration checked" (quality.build_contract, test_loop.build_contract) | RECOVERY AID (model-authored) | 8 logs for 52 actions | 0 reads; 8 writes, each within 8 events of that action's result |
| `notes/environment-lifecycle.md` | host writes | none | "Environment lifecycle note (host-authored, if present)" (navigator._run_rules) | RECOVERY AID; designed to point at `docs/shiploop/environment.md` | 1 (535 B) | 0 reads, 1 write |
| `scratch/` | navigator.emit creates the dir; model writes | evidence_refs existence check only (navigator, "cite files that do not exist") | "Scratch directory (your temporary files; /tmp is shared with other runs)" (navigator._run_rules) | SCRATCH | 149 (952 KB; 54 named in results) | 24 calls on its own files |
| `lint/<id>.md`, `.gateN.md`, `.N.md` | lint.record_writes (on_transition, gate, main) | lint.render_lines, lint.gate, on_transition (prior pass), main `--show`, `_consumed` | "Read every part (lossless)" with `--show` commands (lint.render_lines) | AUTHORITATIVE for lint staleness and gate numbering; supporting, never exit evidence | 12 | 0 (blocks are inlined in the packet) |
| `lint/<id>-inventory.md` | lint.inventory_writes | lint.render_inventory_lines; quality contract resource | rows printed inline, heading names the record (lint.render_inventory_lines) | DERIVED snapshot of Git at entry | 2 | 0 |
| `lint/items/<item>.md` | lint.capture_base | lint.read_base | none | AUTHORITATIVE (item base tree) | 2 | 0 |
| `lint/logs/*.out`, `*.err` | lint._Invoker.run via _write_private | none (see Findings F1, F2) | none | UNREAD | 72 (36 .out, 36 .err; all 0 bytes) | 0 |
| `lint/tmp/` | lint._tool_env, snapshot index files | lint (deletes its own index files) | none | SCRATCH | 0 files (empty `cache/`) | 0 |
| `tests/<id>-contract.json` | test_loop.transition_writes | none (check_terminal compares with a contract rebuilt from state, not this file) | "Start: ..." command naming it (test_loop.render_lines) | INPUT to the Until Loop runtime | 4 | 1 read_file, 1 terminal |
| `tests/<id>-terminal.json` | Until Loop runtime (external) | test_loop.check_terminal -> quality.check_loop_packet; context_index.RECORD_GLOBS | "ShipLoop checks this file, so do not write or edit it" (quality.RECEIPT_LINE) | AUTHORITATIVE loop-terminal evidence | 4 | 1 terminal (`status` field) |
| `tests/<id>-verifyN.md` | test_loop.verify | test_loop._verify_count, refused_runs, latest_attempt_could_not_run, verify (prior run) | "Full output: <path>" (test_loop.verify refusal text) | AUTHORITATIVE (the file count is the refused-run counter) | 19 | 3 grep |
| `quality/<id>-contract.json` | quality.transition_writes | none (quality.check_terminal rebuilds it) | start command naming it (quality.render_lines) | INPUT | 2 | 1 grep, 1 terminal |
| `quality/<id>-terminal.json` | Until Loop runtime (external) | quality.check_terminal -> check_loop_packet; RECORD_GLOBS | quality.RECEIPT_LINE | AUTHORITATIVE | 2 | 0 |
| `quality/code-craft.md` | quality.transition_writes: guidance.CODE_CRAFT | none | contract resource "Code craft rubric the review applies" (quality.build_contract); the same text is also inline in the static-checks packet | DERIVED (frozen copy of a packaged constant) | 1 | 0 |
| `improve/<id>/receipt.md` | standalone_improve._complete_ephemeral, _settle_incomplete_ephemeral | planning_context._collect_improve_artifacts (chains), planning_revision.validate_archives (stopped children only) | "Improve receipt: <path>" (context_index._entry_lines; navigator.render done line) | ARCHIVE of state.improve_results[action] | 3 | 0 |
| `improve/<id>/terminal.json`, `evidence/` | same functions; _evidence_archives | same two readers | none | ARCHIVE (digests in state `identities`) | 3 + 7 | 0 |
| `improve/<id>-bind.md` | improve_changes.bind_writes | improve_changes.review_changes -> commit_refusal | none | AUTHORITATIVE (detects the review's own uncommitted edits) | 3 | 0 |
| `backchain/<id>/candidate-*.json`, `check-*.json` | backchain_graph.record (`backchain-check`) | evidence_refs existence check; record() byte compare on rewrite | "List the printed receipt path in evidence_refs" (prompts, Backchain stages) | EVIDENCE cited by results | 1 + 1 | check-*.json opened once (terminal, event 2922); candidate-*.json 0 |
| `until-loop/` | navigator._improve_start creates the dir; runtime writes | none (runtime `done --state`) | none; the runtime packet's `next_argv` resumes | RECOVERY AID owned by the runtime, transient | 0 (empty after finish) | `done --state` x5 by the model |
| `workspace.md` | workspace._prepare_locked, plan_return, _write_receipt | workspace._manifest, lint.fallback_base, protocol, navigator | "Workspace authority and original branch: <path>" (navigator.render) | AUTHORITATIVE (baseline, status) | 1 | 2 read_file |
| `return-plan.md` | workspace.plan_return, follow_up_knowledge_return | workspace.source_unchanged, return, navigator | "Review every return-plan disposition" (navigator.render) | AUTHORITATIVE | 1 | 2 read, 1 grep, 4 writes or edits |
| `return-receipt.md` | workspace._write_receipt | workspace._receipt, completed_receipt_snapshot; protocol handoff check | "Handoff completion requires a current script-verified return receipt" (navigator.render) | AUTHORITATIVE | 1 | 1 read, 2 grep |
| `docs/shiploop/{README,spec,environment,test-strategy}.md`, `SHIPLOOP.md` | model; committed by knowledge_home.commit | knowledge_home.check (presence, credentials, R-IDs), progress_data (previews) | "open a file when this stage needs it" (knowledge_home.stage_lines) | AUTHORITATIVE for cross-run knowledge (Git) | 4 + 1 | 34 read, 12 grep, 53 edits (docs); SHIPLOOP.md 5 reads |
| `docs/shiploop/features/<f>/*` (spec, plan, test-spec, system-tests, release-plan, outcome) | model; committed by knowledge_home.commit | knowledge_home.check (CLOSES), learnings (outcome.md sections), progress_data previews | stage_lines "keeps these up to date" | AUTHORITATIVE for this run's prose | 6 | included in the docs counts above |

Not in the user list but present: `.lock`, `.progress.lock` (locks), `<worktree>/.shiploop-improve/<run>/<id>/`
(runtime-owned live receipt `packet.json`, `start.json`, `opening.md`, `reviews/`; source of the `improve/` archive),
`lint/pending-<action>.patch` (transient fix journal, absent here), and `decisions/<action>.md` (only after
`resume --answer`, absent here).

## Recovery evidence

Five compactions happened (events 1681, 4279, 6917, 8659, 10303). After each, the model reopened the current packet
within its first five calls (first call after compactions 1, 4 and 5, fourth after 3, fifth after 2); after compaction
4 it also grepped and read `context-index.md`. It never opened a pass log. No pass log existed for the action in progress at any
compaction: each of the 8 logs was written once, at the end of its action, so the packet instruction "after each pass,
append what you checked" was followed as a closing summary on 8 of 52 actions. Whether a mid-stage log would have
helped is unknown. This is a conformance gap, not a reason to drop the recovery aid.

## Unread, but not proven dead (not findings)

- `status.md`: no reader in `scripts/`, never opened; documented human `cat` target and read by tests
  (`test/shiploop-status-display.test.py`) and E2E review tooling. Content equals the inline block and `shiploop status`.
- `improve/<id>/terminal.json` and `evidence/`: read only on the chain and stopped-child paths; none on this inline run.
- `quality/code-craft.md`: duplicates the inline packet text; the contract resource is the only pointer.
- `timeline.json`: labelled derived but holds the only copy of accept times.

## Findings

Proven dead writes (written, no script reader, no packet instruction, never opened):

- **F1. `lint/logs/*.err`.** Writer `lint._Invoker.run` stores `err_log` in the call dict, but `lint._call_lines` cites
  only `out_log` and never `err_log`; no module or test reads `*.err` (tests read only `logs/*.patch`). 36 of 36
  files are zero bytes and none was opened. Disposition: remove the write.
- **F2. `lint/logs/*.out`, conditionally.** `lint._call_lines` cites the byte-exact copy only when a call sets
  `stdout_note` (ruff fixed source, resolved ruff settings). In this run no call did: 36 of 36 files are zero bytes,
  the block prints "stdout: (empty)", none was opened. Disposition: remove the write unless `stdout_note` is set.

Related defect, a dead pointer rather than a dead write:

- **F3. `<action>-latest.json` in `context-index.md`.** `context_index._in_progress_lines` prints "Loop packets:
  .../tests|quality/<action>-latest.json (latest)". No module in `skills/` or `test/` writes that file. A cleared
  model following the recovery section is sent to a file that does not exist. Disposition: make the line point only at
  `-terminal.json` (written by the runtime), or at the real receipt.

Recovery aids confirmed in place and kept: `packets/`, `context-index.md`, `notes/<action>.md`,
`notes/environment-lifecycle.md`, `until-loop/`, `results/` ("Read first").

## Single source of truth

| Fact class | Authoritative | Derived, archived or competing |
|---|---|---|
| Graph position (stage, action, work item, status) | `state.md` (`stage`, `action`, `work_index`, `inner_loops`, `status`) via navigator.save | derived: `status.md`, `context-index.md` "In progress", `packets/<action>.md`, `progress.html`, `report.html`. `timeline.json` is time only; `callback-attempts` is only a keepalive counter. No competing copy found |
| Accepted results | `state.md` `accepted` + `history` | derived: `results/<action>.md` (byte-checked by planning_context.collect), `context-index.md` summaries, `report.html` rows. Input copy: `inbox/<action>.md` stays after acceptance and is read only for idempotent replay, so each accepted result exists three times on disk (240 KB inbox, 224 KB results, `state.md`). Improve records: `state.improve_results` is authoritative, `improve/<id>/receipt.md` is its archive (equality enforced by planning_context._collect_improve_artifacts) |
| Test commands | `state.md` accepted `step-plan` `test_commands` (also `system_commands`, `consumer_checks`), read by test_loop._step_plan and stage_commands | derived: `results/<step-plan>.md` (what contracts point at), `tests/<id>-contract.json`. Competing prose: `docs/shiploop/test-strategy.md` and `features/<f>/test-spec.md` also list commands; scripts check presence and credentials only, nothing enforces that they match the accepted commands |
| Loop progress | `state.md` (`inner_loops`, `revisions`, `active_improve`, `improve_results`) for position; `tests/<id>-verifyN.md` file count for the refused-run cap (no mirror in state); runtime-owned `tests|quality/<id>-terminal.json` and the live `.shiploop-improve/.../packet.json` for the Until Loop's own iteration state | derived: `context-index.md`, `progress.html`. Recovery: `notes/<action>.md`, `until-loop/` |
| Return state | `workspace.md` (status, baseline), `return-plan.md` (dispositions), `return-receipt.md` (script-verified receipt that handoff requires) | derived: `report.html` workspace section (read live from Git). No copy in `state.md` |
| Knowledge (spec, environment, test strategy, outcome) | `docs/shiploop/*` and `SHIPLOOP.md` in Git, committed by knowledge_home.commit; `worktree/` and `work/` hold the same commits after return | `state.md` holds summaries of the accepted `spec` and `plan` results, not the documents. `notes/environment-lifecycle.md` is a pointer to `environment.md` by design (535 B in this run) |
