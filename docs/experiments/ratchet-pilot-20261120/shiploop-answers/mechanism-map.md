# ShipLoop route map for a "requester answers a default" mechanism

Checkout read: `.../scratchpad/defaults/merge-a5ac04` (`T`). Read-only; facts only. Engine = `T/skills/shiploop/scripts/`.
Module aliases: `navigator` = `shiploop_navigator.py`, `notes` = `shiploop_owner_notes.py`, `kh` = `shiploop_knowledge_home.py`,
`stage_spec` = `shiploop_stage_spec.py`. "not verified" marks an inference that was not read in code.

## 1. Owner notes

- CLI: `python3 "$CLI" note --run-dir RUN --text TEXT` or `--file PATH` (mutually exclusive, one required). Routed in
  `shiploop_protocol._main`: `if raw_argv[0] == "note": return shiploop_owner_notes.main(...)`. Implemented by `notes.main`.
- Refusals (exit 2, nothing written): symlinked run dir; no current `state.md`; run `done` or `halted`; text empty, over
  `NOTE_LIMIT = 2000` as quoted (each line indented), holding a control character, non-UTF-8, or `FORBIDDEN`
  (`SHIPLOOP-RUN`, `=== ShipLoop`, `=== end ShipLoop`). A `blocked` or `paused` run accepts a note (the CLI prints that the
  packet after `resume` quotes it). No run lock is taken.
- Storage: `RUN/owner-notes/N<k>.md` (`notes.DIR`), one file per note, written once by `notes.write` (temp file `os.link`ed
  into place). Record shape: `{id: "N<k>", written_at: "<UTC ISO>", text: <cleaned text>}` (`store.dumps(record, "ShipLoop owner note")`).
  Reader `notes.notes(root)`. Notes are not tied to a stage, requirement or action at write time.
- Script-only record `RUN/owner-notes/shown.json` (`notes.SHOWN_FILE`): `{"action": id, "packet": [ids a print quoted whole],
  "held": [ids a held callback printed]}`, for the current action only (`notes.read_shown`, `_save_shown`).
- Delivery record: `state.md` key `owner_notes` = `{N<k>: action id}` (`notes.delivered`, validated by `notes.validate`, called from
  `navigator._validate_current_state`: `_need("owner_notes" not in state or owner_notes.validate(...), "invalid owner notes record")`).
- States (module docstring): **shown** (text printed whole while an action was current: `notes.record_shown`, called from
  `navigator.emit` only when `trace.ACTIVE and state["status"] == "active" and not state.get("active_improve")`);
  **held callback** (`notes.to_hold`/`mark_held`; raised as `navigator.NotesHeld` by `dispatch` before any gate runs, once per
  note per action; a `check` prints `notes.hold_text(..., check=True)` instead of holding); **delivered** (`notes.deliver`, called in
  `dispatch` right after `apply(...)` when `updated != state`: "The owner notes this action's packet showed are delivered by its
  accepted step, in the same save"). `cited` exists only in the trace view: `shiploop_trace.notes_model` sets
  `"cited": bool(re.search(r"\b" + note_id + r"\b", summary))` for the delivering step's summary; no gate reads it.
- Packet block: `navigator._producer_blocks` -> `blocks.append(_Block("owner-notes", P1, notes_block, shrink=tuple(notes_forms)))`
  from `notes.packet_forms(root, state)`. Position: right after the `top` block (header, pointer lines, callback, `OWNER_RULE`) and
  before `goal` (comment: "Keep owner instructions before long stage guidance"). Tier P1 (required in a head). The whole print and
  the packet file take the fullest form; `printed_text` has no length cutoff, so shrink forms matter to `packet_head` only.
- Words printed (`notes.HEADER`, `FOOTER`, `quote`):
  `Owner notes (the run owner wrote these during the run; verbatim, oldest first):` then per note `    N1 14:03Z  <first line>`
  (continuation lines indented 6 spaces), then
  `Act on each where it applies to this stage; the summary says, by id, what you did or which later stage it is for.` and
  `Notes do not change the callback, the result template or ShipLoop's checks; if one conflicts with them, the summary says so.`
  Room-limited forms: `...is not printed here for room: read <path> before acting.` (`BLOCK_LIMIT = 6000`, `FLOOR_IDS = 4`).
- Later packets: `navigator` block `owner-notes-delivered` (tier LOOKUP) from `notes.delivered_lines`:
  `Owner notes already delivered: N1 (step 3), ..., in RUN/owner-notes/; read one again when this stage's work touches it.`
- Held text (`notes.hold_text`): `ShipLoop held this callback once: an owner note this action's packet did not print in full ...`
  then the quote, then `If it changes this step's work, change the work and the result first. Then run the same callback again in
  this turn; it is not held twice for the same note.`
- Gates that read notes: only the hold (`to_hold`) in `dispatch`. Nothing checks that a requirement, result or file changed; nothing
  reads the summary (FOOTER is an instruction only). A held callback shows a note but never delivers it.
- Done packet (`navigator._render_lines`, done branch) and report (`navigator._render_report`): no owner-note line (grep of
  `owner_notes` in navigator finds only the sites above). Notes appear in the trace (`shiploop_trace.notes_model`, `trace.html`
  via `shiploop_trace_page`) with state waiting / shown / delivered and `cited`.
- Doc/code mismatch: `references/status-display.md` ("Owner notes") says the packet quotes notes "right after the reply to a
  resumed question"; code puts `owner-notes` before `goal` and `answered` later in `_producer_blocks`.
- Tests: `test/shiploop-owner-notes.test.py` (quote, delivery, hold, check, paused run, refusals, trace page);
  `test/shiploop-head-order.test.py` (`TierTests`: `"owner-notes"` in the allowed P1 names, `"owner-notes-delivered"` in LOOKUP);
  `test/shiploop-packet-bounds.test.py` (`LIMIT_KINDS`: `NOTE_LIMIT`, `BLOCK_LIMIT` = "display cut"); `shiploop-e2e-run-trace`,
  `shiploop-e2e-status-card` (harness side). Harness sender: `test/shiploop_e2e/owner_note.py` (its TEXT asks the model to cite the id).
  Design: `docs/shiploop-owner-notes-design-2026-10.md`. Existing experiment sender: `docs/experiments/ratchet-pilot-20261120/
  shiploop-defaults/requester.py` (runs `$CLI note --run-dir ... --text <reply>` once, after the packet of `defaults.SHOWN_AT`).
- Recorded observation (DESIGN.md of that experiment, section 6, O1): of four sent replies, two made the next stage rewrite the
  requirement, one was confirmed, one was delivered and never acted on; "nothing in the script notices".

## 2. The living specification after the spec stage

- Which stages may edit `spec.md`: descriptive table `kh.STAGE_FILES` lists `spec.md` for `spec` and `document` only. It drives
  packet text (`kh.stage_lines`); no code gate refuses an edit of a file outside a stage's row (grep of `STAGE_FILES` finds
  only `kh.required_earlier`, `kh.stage_lines`, `navigator` ~6905 who-writes-this). Not verified beyond grep.
- Gates that do apply to any stage that changed `docs/shiploop/`:
  1. `kh.check` (via `navigator._knowledge_gate`, called in `_evaluate` and at the Improve import with command "improve"): refuses a
     drop of an `R-<n>` ID present in HEAD: `"Restore the lost R-<n> in <path> or move it under 'Retired', then run the same callback
     again."` (`_RETAINED`). Only drops are checked; rewording a clause is not. The printed gate list says so:
     `_stage_gates` -> `"a change to KNOWLEDGE/ that loses an earlier requirement (R-<n>) or decision (AD-<n>) ID"` for spec, plan, step-plan.
  2. `kh.step_spec_refusal` (via `navigator._step_spec_refusal`): applies only while an inline step is current. `_evaluate` runs it for
     `implement` and `document` done results, and `dispatch` runs it at the Improve import of `document`. Compares `spec.md` with HEAD:
     allowed = new lines inside an R-<n> entry HEAD already holds, each ending `(<item>/<step id>)`; refused = a changed or removed line,
     a line without the mark, or a line outside such an entry. Refusal text:
     `Restore <path>/spec.md to what HEAD holds plus this step's requirement lines, then run the same callback again; to change a
     requirement, report send-back naming it.`
  3. E2E metric `spec_writeback` (`test/shiploop_e2e/metrics.py`): `re.compile(r"Restore \S*spec\.md to what HEAD holds")`, i.e. it
     counts refusals of gate 2. Comment there: "The step plan's or run's written spec diverged from HEAD plus this step's acceptance lines".
  4. `kh.placement_notices`: a counted notice (never a refusal) when an entry is born under `Retired`.
- No gate found for `test-strategy`, `plan`, `step-plan`, `test-spec`, `test`, `carry-forward` or the outer stages that edit a
  clause of `spec.md` without dropping an ID (inferred from reading `spec.md` references in `navigator`, `loops`, `expectations`,
  `item_scope`; not exhaustively verified). The recorded first real delivery shows `test-strategy` rewriting a clause after a note
  (DESIGN.md section 6; `defaults.py` docstring: "the next stage rewrote the clause and the product followed").
- Reference rule text (not code): `references/behavioral-requirements.md`: "If learning contradicts accepted scope/acceptance, stop
  and seek direction, not a silent spec edit. Future-queue revision cannot change accepted acceptance." and
  `references/requirements-definition.md`: "Do not silently revise accepted intent or create another ledger, phase, or review campaign."
  Spec duty text (`kh.stage_lines`, stage spec): "keep every requirement ID (R-<n>), change it in place, and move a dropped
  requirement under a 'Retired' heading with its reason."
- Entries: `kh._entries(text, prefix)` finds starts with `_ENTRY_START` (heading, list item or table row beginning with `R-<n>` or
  `AD-<n>`, outside code fences; a heading/list start outranks a table row, `_MARKED_START`) and cuts the span to the next heading
  of equal or higher level, or by indentation/lazy-continuation rules. `kh.entries(repo, "spec.md") -> Dict[str, Entry]`
  (files only, no Git). `class Entry(NamedTuple): text: str; retired: bool`. `retired` = some enclosing heading starts with `Retired`
  (`_ENTRY_FILES = {"R": ("spec.md", "retired"), "AD": (ARCHITECTURE, "superseded")}`).
- `kh.entries_after(state, stage, name)`: entries of `name` as this run's newest knowledge commit of `stage` holds them (commit
  subject `kh.knowledge_subject`: `docs(shiploop): record <run label> knowledge after spec`); `None` = cannot be told.
  `kh.entry_text(repo, ident)` returns one entry's whole text. `kh.requirement_ids(text)` is the one ID reader.
  `kh.spec_diff(root, state)` = diff of spec and architecture from the run baseline (`run-baseline.txt`,
  `run-starting-knowledge.json`); consumed by stages whose `navigator.CONSUMES` row has `spec_diff` (test-strategy, plan, document,
  carry-forward, product-acceptance, release-verify).
- Where a requirement ID is cited downstream (all read the live `spec.md`, not a copy): spec result `primary` (`shiploop_primary`
  `check_spec`), `defaults[].requirement` (`defaults.check_submitted`), step-plan `follows` (`_handoff_fault` refuses IDs with no entry;
  `handoff_sources` quotes `kh.entry_text` live into later packets), test-spec case `requirement`
  (`expectations.requirement_ids_text`), product-acceptance `unverified[].requirement`.

## 3. Routes that reopen or correct an earlier decision

- **improve-reconcile** (`navigator.reconcile`, verb in `shiploop_protocol.CALLBACK_VERBS`). Trigger: the initial plan Improve child
  ends `runtime_phase == "stopped"` (cancelled) with a receipt `{summary, target, evidence_refs}` (`_reconcile_receipt`), target in
  `planning_revision.RECONCILIATION_TARGETS = PLANNING_STAGES[:4]` = discovery, research, spec, test-strategy.
  `_reconciliation_permitted`: run active, `stage == "plan"`, `work_index == 0`, no completed items, bound plan child, "reconciliation is
  allowed only before prepare or work execution". Effect: records a `reconcile` result (`_canonical_result` accepts it only as the exact plan
  result), appends `planning_reconciliations`, sets `stage` to the target with a new action; `planning_revision.current_actions`
  then drops the accepted `done` results of the target and every later planning stage, so `spec` reruns (and `defaults.recorded` reads the
  new spec result). It edits nothing itself; the rerun stage edits `spec.md` under gate 1 above. Absent when `planning_review: none`
  (references/navigator.md). Text: "reconcile requires improve-reconcile, never normal apply" / "...never finish_improve".
  Tests: `shiploop-improve-schedule`, `shiploop-navigator-contract`, `shiploop-navigator-v4`, `shiploop-keepalive`.
- **send-back, inner** (`stage_spec._finish`: added to `test-spec` through `document` by position). Target `stage_spec.SEND_BACK_TO =
  "step-plan"`. Apply: `navigator._apply_result` increments `revisions[<item>]`, `_replace_inner_action(updated, "step-plan")`. The step
  plan is resubmitted whole ("Submit the whole amended plan"); `planning_revision.current_actions` drops that item's results from step-plan
  on. `navigator._upstream_line`: "a send-back reruns no planning stage". Changes steps, criteria, expectations, commands, `follows`,
  paths; not a spec requirement (no spec stage reruns). Gate: `_STAGE_SEND_BACK_FIELDS` (`validate-existing` needs `failed_expectations`).
  Trigger text: "the item's step plan or test spec is wrong or unachievable". Also opened by gates 2 (`loops.open_send_back`).
- **send-back, outer**: `stage_spec.OUTER_SEND_BACK_TO = {"system-test": "system-test-author", "release-verify": "release-plan"}`;
  `send_back_target(stage)`; the target stage reruns with the result as evidence, then every stage after it. Count in `revisions[target]`.
- **add-work** (outcome allowed on all OUTER stages, `stage_spec._finish`: system-test-author, system-test, product-acceptance,
  release-plan, release-check, release, release-verify, operations, handoff). `_canonical_result`: needs `work_items` ("add-work requires
  corrective work_items at an outer stage"); `_apply_result`: IDs must be new ("corrective work IDs must be new"), rows appended to
  `state["work_items"]`, `stage = "inner-loop"`, `_begin_inner_loop`; the run resumes at system-test-author (outcome text in
  `_allowed_outcome_lines`). Shape: `stage_spec.ADD_WORK_SHAPE`. Adds items only; it carries no spec edit (the item's own steps may add
  marked lines to existing R entries under gate 2). Also the exit named by `primary.check_unverified` refusals.
- **revise**: retired as an outcome (`glossary.md` retired term `Revise (an outcome)` -> `send-back`, since 2026-10-18; `_canonical_result`
  message "revise, replan and repeat are retired"). Equivalents that exist: an Improve review's edits before import (`improve-commit`,
  then import re-runs `_knowledge_gate`, `_check_submitted_defaults` etc.); `carry-forward` `work_items` replaces the entire future
  queue (`_replace_future_work_items`; references/carry-forward.md: "Incompatible findings ... A changed requirement, permission, invocation
  contract or completed-work assumption is not a queue edit: report `blocked` or pause for direction").
- Plan queue replacement: `_replace_plan_work_items` only while `stage == "plan"`, `work_index == 0`, nothing completed
  ("plan work items can only be replaced before execution").
- Existing route that already rewrites the spec on an owner note: none in code. What exists is an unchecked behaviour (section 1/2):
  a note is quoted to the next stage, which may rewrite the clause (observed, not enforced).
  `defaults.py` docstring: "no script route replaces an accepted specification and what was planned from it".

## 4. The `defaults` list pattern (`shiploop_defaults.py`)

- Constants: `STAGES = {"spec"}`; `FIELD = "defaults"`; `SHOWN_AT = "test-strategy"`; `FIELDS` = requirement, question, default,
  alternative, why; `TEMPLATE_ROW`; `WHAT`, `SHAPE`, `EMPTY`; `HEADING = "Decided for you"`; `ROWS_PRINT = 2_400`; `CHANGED`.
- `canonical(value)`: shape-only canonicalisation (list of str->str maps, stripped); used by `navigator._canonical_result`
  (`if "defaults" in value: _need(stage in defaults.STAGES and outcome == "done", ...)`), so a saved result always loads.
- `recorded(state)`: list of the current accepted done spec result (`planning_revision.current_actions(state).get((None, "spec"))`), or
  `None` (unmeasured, not zero).
- `check_submitted(repo, stage, result)`: CLI-gate checks (missing list, unknown/missing fields, empty text, template placeholder,
  `requirement` not `^R-\d+$`, requirement without a current non-retired entry via `knowledge.entries`). Wrapper
  `navigator._check_submitted_defaults(state, stage, result)` (re-raises as `NavigatorError`). Three call sites, all in `navigator`:
  (1) `_evaluate` (the gates of `complete`/`check`, with `_check_submitted_primary`); (2) `dispatch`, the reuse path that takes a
  matching `shiploop_check.matching_yes` ("Recheck cheap admission in evaluator order before consuming a yes"); (3) `dispatch`, the Improve
  import branch, on `child["seed_result"] if final_result is None else final_result`.
- Packet block: `navigator._stage_input_blocks`: `if stage == defaults.SHOWN_AT: blocks.append(_Block("defaults", P1,
  defaults.packet_lines(state, root, stage, _default_rows(state).lines)))`. `_Block(name, tier, lines, head=None, shrink=())`
  with tiers `P0, P1, LOOKUP, CHROME, QUOTED, FILE_ONLY = "P0","P1","lookup","chrome","quoted","file"`; `HEAD_REQUIRED = {P0, P1}`.
- `packet_lines(state, root, stage, rows)`: head line `Defaults the spec recorded: N answers it chose where the request does not say
  (<RUN>/results/<spec action>.md, `defaults`). In this stage's progress line tell the user there are N and name each in a few words;
  ask nothing and wait for no answer:` then the rows. Empty if `shows` is false.
- `shows(state, stage)`: `stage == SHOWN_AT` and active and no `active_improve`. `row_lines(entries, marked)`: numbered rows
  `N. R-x [(changed after the spec stage)] <question> Decided: <default> Otherwise: <alternative>`.
- `done_lines(state)`: used in `navigator._render_lines` done branch (`*defaults.done_lines(state)`): `Decided for you: N answers ...
  In your last message tell the user each ...`, then rows, `_stale_note`, and `To change one, start a new run on this project with a
  sentence that says what you want instead.`
- `html_section(state)`: used in `navigator._render_report` right after "Original request": `<h2>Decided for you</h2>` + table (values
  `html.escape`d); distinguishes "not recorded" from "none".
- `changed(state)`: set of requirements whose spec-stage lines (`kh.entries_after(state, "spec", "spec.md")`) are missing from the
  working-tree entry (`kh.entries`), retired or gone; `None` = cannot tell. Added lines are not a rewrite. Words-only comparison (`_lines`).
- Spill: `navigator._default_rows(state)` -> `fields.block(lines, len("\n".join(lines)), defaults.ROWS_PRINT, action, "defaults")`
  returns `fields.Shown(lines, file)`. `fields.block(lines, size, budget, action, field, indent="", header=0)`: whole while `size <= budget`; else
  leading lines that fit plus `(N more lines not printed here: RUN/fields/<action>-<field>.md holds all M whole)`. `navigator.field_files(state)`
  collects spilled files (`if defaults.shows(...): shown.append(_default_rows(state))`); `emit` writes each before printing.
- Other hooks: result template `_result_template` (`result["defaults"] = [dict(defaults.TEMPLATE_ROW)]`); gate words `_stage_gates`
  ("a missing defaults list, ..."); Improve handoff text in `_render_improve` ("Defaults list: final_result.defaults lists each choice the
  reviewed spec makes ..."); spec duty 4 and `SUMMARY_PLACEHOLDER["spec"]` in `shiploop_prompts.py`; `navigator._DONE_ONLY_FIELDS`,
  `_RESULT_KEYS`. Sibling with the same shape: `shiploop_primary.py` (`canonical`, `check_spec`, `packet_lines`).
- Tests: `test/shiploop-defaults.test.py` (ShapeTests, RouteTests via the real CLI); `shiploop-packet-completeness.test.py`
  (`GATE_WORDS["defaults"] = {"spec"}`); `shiploop-packet-bounds.test.py` (`"shiploop_defaults.ROWS_PRINT": "print budget"`).

## 5. Stage order and the window

- `stage_spec.STAGES` (23, `_check_table`): PRELUDE intake, discovery, research, spec, test-strategy, plan, prepare; INNER (per work item)
  step-plan, test-spec, validate-existing, implement, test, document, carry-forward; OUTER system-test-author, system-test,
  product-acceptance, release-plan, release-check, release, release-verify, operations, handoff.
- Improve stages (`improve` rule, run with `planning_review: stage`): spec, test-strategy, plan = "always"; step-plan = "first-item";
  document = "item" (per step); carry-forward = "last-item"; system-test-author and release-plan = "always".
  `planning_review: none` skips spec, test-strategy, plan, step-plan (`PLANNING_CHOICE_STAGES`).
- Outcomes: `done, blocked` everywhere; `send-back` test-spec..document, system-test, release-verify; `add-work` all outer stages.
- Where the plan binds the build: `plan` done with `work_items` -> `_replace_plan_work_items` creates the queue
  (`state["work_items"]`); `primary.check_queue` requires every primary R in some item's `follows` (plan and carry-forward); `prepare`
  requires current planning sources (`_planning_sources_current`: discovery..plan results); the per-item `step-plan` result creates
  `follows`, `criteria`, `steps`, `test_commands`, `expectations`; `test-spec` creates `test_cases` naming `requirement`; the run then walks
  steps (`implement` -> `test` -> `document`, step commit).
- Stages after spec that can still change a clause without a script route: see section 2 (no gate other than ID retention, and gate 2
  inside implement/document steps). Cheap/expensive is not stated in code; the facts are: reconcile reaches spec only until `prepare`;
  send-back never reaches spec; add-work only appends items.

## 6. Waiting on a person

- Outcome `blocked` needs `awaiting` (`navigator.AWAITING_KINDS = ("answer", "present", "service")`, shape `AWAITING_SHAPE`,
  `BLOCKED_RULE`). Allowed at every stage (`stage_spec.OUTCOMES`). `_check_submitted_awaiting` (S-14): refuses a wait without
  `awaiting.no_default`: "ShipLoop runs unattended: take a stated default, record it as an assumption and continue, ... Prompt the user
  (awaiting) only when nothing further can proceed without them, and say why in awaiting.no_default."
- Sets: `_apply_result` for `blocked`: `status = "blocked"`, `status_reason = "<kind>: <summary>"`, a new action for the same stage.
  Derived accessor `navigator.awaiting(state)` = the last history action's accepted `awaiting` when `status == "blocked"`.
  Display: `WAITING_ON_YOU = "Waiting on you"`, `WAITING_ON_SERVICE`, `_status_next`.
- Clears: `navigator.control(state, "resume", answer=, observed=)`: kind `answer` needs `--answer`, `present`/`service` need `--observed`;
  a bare "continue" is refused (`_NOT_AN_ANSWER`). `dispatch` then writes `RUN/decisions/<blocked action>.md` (`decision_path`; fields
  action, kind, asked, reply, recorded_at). The reissued stage's packet has block `answered` (tier P1, `_answered_lines`): `The user's
  reply to the question this stage waited on (<path>): Asked: ... Reply: ... Act on this reply; it is the user's decision, recorded verbatim.`
- `references/keepalive.md`: a `blocked` run waiting on the user "stays stopped until the user's reply resumes it"; `pause`/`resume` are
  separate (`status paused`).
- `asked_user`, `awaiting_kind`, `blocked_by` (retired): no live use found (`blocked_by` only in the refusal text; glossary retired term).
- Unattended rule, verbatim sources:
  - `shiploop_prompts.STAGE_RULES`: "Unattended: take the best default and record it as an assumption; a person-only step is an open
    item; report blocked only when nothing can proceed without a person."
  - `shiploop_prompts.COMMON`: "ShipLoop runs unattended: no one is watching and nothing arrives on standard input. When a decision is
    open, take the default that best fits the request and the recorded knowledge, record it as an assumption ... Only when nothing further
    can proceed without a person or an outside service, report blocked with `awaiting`: ..."
  - `README.md` section 7: "ShipLoop runs unattended: it records a default and continues, and it asks only when nothing else can proceed."
  - `test/shiploop_e2e/SPEC.md` S-14 (above): "It never blocks on standard input and never asks as a first resort (owner, 2026-09-27)."
  - `defaults.packet_lines`: "ask nothing and wait for no answer"; `defaults.py`: "Nothing here asks a question, waits for an answer,
    adds a limit or blocks a stage".
- Note CLI on a blocked run: prints the recorded question and "Answer it with `resume --answer`; the packet after the resume quotes this note."

## 7. Result keys and canonicalisation

- Register a done-only key: add to `navigator._RESULT_KEYS` (unsupported keys are refused: "result has unsupported fields: ...") and to
  `_DONE_ONLY_FIELDS` (a blocked/send-back/add-work result carrying it is refused: "a <outcome> result does not carry ... those fields
  belong to a done result"). Shape-check inside `_canonical_result` (pattern: `if "defaults" in value:` ...). Stage-owned keys are listed
  in `_result_template` and `_stage_gates`; hand-off keys in `HANDOFF_FIELDS` (own mechanism).
- `_canonical_result(value, *, stage, delivery_contract=False, spec_hint="")` returns a new dict; unknown keys are not dropped, they
  raise. Stored shape of `defaults` is loose (`canonical` returns any text rows), exact checks only at CLI gates
  (`_check_submitted_defaults`), so a saved run always loads (`test_a_saved_result_whose_entries_are_any_text_loads_while_the_gate_refuses_it`).
- On load: `_validate_current_state` calls `canonical = _canonical_result(accepted[entry_action], stage=entry_stage, ...)` and
  `_need(canonical == accepted[entry_action], "accepted navigator result is not canonical")`, and the history outcome/summary must match.
  So a new key's canonical form must reproduce itself exactly; a new state key must be in `_STATE_KEYS` (e.g. `"owner_notes"` is, and is
  exempt from the "missing" check: `allowed - {"status_reason", "delivery_contract_version", "delegation_hold", "owner_notes"}`).
- Size/order tests: `test/shiploop-packet-bounds.test.py`: `numeric_limits()` scans every `shiploop_*.py` module-level constant >= 20 whose
  name matches `LIMIT|CAP|MAX|PRINT|SHOWN|CHARS|BYTES|BUDGET|ROWS|LINES|...` and requires a row in `LIMIT_KINDS` ("print budget",
  "display cut", "guard"), and flags stale rows; `INLINE_LENGTH_CHECKS` pins `len(x) > N` literals >= 80. `test/shiploop-head-order.test.py`:
  `TierTests` pins each block's tier (P0 set, `LOOKUP`, `CHROME`, `FILE`) and that P1 block names are within an allowed set for the stages
  tested (implement, test, document, carry-forward, validate-existing, step-plan), and that tiers print in the order P0/P1, lookup, chrome,
  quoted. A new P1 block on a stage not in that list (as `defaults` and `primary` are) is not hit by that set. Head limits:
  `navigator.HEAD_LIMIT = 20_000`, `HEAD_REQUIRED_END = 19_500`, `PRINT_LIMIT = 16_000` (legacy; whole print is complete).
  `shiploop-packet-completeness` (`GATE_WORDS`), `shiploop-callback-contract`, `shiploop-loophole-gates` also exercise gate words/refusals.
- Docs touched when a key is added: `references/navigator.md` (result fields, `spec` also lists `defaults`), `references/glossary.md`
  (term rows; S-16 one term per concept), `changes/<leaf>/*.md` note (AGENTS.md).
