# ShipLoop mechanism map, owner notes and late changes (main, HEAD 472919dfc)

Read only, canonical checkout, branch main, engine `skills/shiploop/scripts/`. Aliases: `notes` = shiploop_owner_notes.py,
`nav` = shiploop_navigator.py, `kh` = shiploop_knowledge_home.py, `ss` = shiploop_stage_spec.py. Symbols, never line numbers.
Extends ~/src/skill-craft/.claude/worktrees/shiploop-answers-603aa8/docs/experiments/ratchet-pilot-20261120/
shiploop-answers/mechanism-map.md (the "old map"). Its sections 1, 3, 6, 7 all hold on main; corrections and additions are marked NEW.
"not verified" = read in code but not run.

## PART A. Owner notes

### 1. Life of a note (old map section 1 holds; NEW points marked)
- Written by `notes.main` -> `notes.write` (`RUN/owner-notes/N<k>.md`, record `{id, written_at, text}`), no run lock. Reader `notes.notes`.
- State is derived, never stored per note. Three stores: the note files; `RUN/owner-notes/shown.json` (`notes.read_shown/_save_shown`:
  `{"action": id, "packet": [ids], "held": [ids]}`, ONE action only: `_shown_for` resets when the action id differs);
  `state.md` key `owner_notes` = `{N<k>: action id}` (`notes.delivered`, `notes.validate`, nav `_validate_current_state`).
- States: waiting (no print) -> shown (in `packet` or `held`) -> delivered (in `owner_notes`). `cited` is trace-only (`shiploop_trace.notes_model`).
- "Shown" (packet): `nav.emit` calls `notes.record_shown(root, current_action(state)["id"], printed)` only when
  `trace.ACTIVE and state["status"] == "active" and not state.get("active_improve")`. It regex-parses the print (`notes.quoted_ids`:
  quote lines between `HEADER` and `FOOTER[0]`). It records ids the text printed, not that the model read them. A failed write
  of shown.json returns [] (nothing recorded; the note is later held). `trace.ACTIVE` is set only by traced commands in
  `shiploop_protocol._main`; the `context` verb (prints `render` directly) records nothing.
- "Delivered": `notes.deliver(root, updated, action_id)`, called in `nav.dispatch` (the `complete` branch) right after
  `updated = apply(state, action_id, submitted)` when `updated != state`, before `accept_effects`. It reads ONLY `shown["packet"]`
  of that action, intersected with notes still undelivered in `updated`; writes `owner_notes[id] = action_id`. It reads no
  result text, no summary, no file change. `shown["held"]` is never read by `deliver`.
- NEW. So yes, a note is delivered by a step whose model wrote nothing about it. Every accepted outcome delivers: done, `blocked`
  (the same stage is reissued under a new action id; the note is then only in the "already delivered" line), `send-back`
  (the step-plan reruns with the note listed only as delivered), `add-work`, and `reconcile` is not a `complete`, so it does not.
- NEW. Improve stages: a producer `complete` of a stage that has an Improve checkpoint makes `apply` set `active_improve`
  (the seed result, accepted later) and returns a changed state, so `deliver` fires at the seed submission, BEFORE the review runs.
  The review's `complete` (Improve action id, `improve_import` branch) calls no `to_hold` and no `deliver`. The Improve packet
  (`nav.improve_packet`) prints no notes. A review may change `final_result`; the delivered mark stands.
- NEW. Delivered-step number in later packets comes from `history`; before an Improve import the action is not yet in history, so the
  line names the note without "(step N)".

### 2. The hold (nav.dispatch, branch `command in ("complete","check")`)
Condition, in code order, after `_submitted_result` has read the result file and before any gate:
`state["status"] == "active" and action_id not in state["accepted"]`, then
`held = notes.to_hold(root, state, action_id)` = undelivered notes whose id is in neither `shown["packet"]` nor `shown["held"]`
of THIS action, and `notes.mark_held(root, action_id, held)` returned True (shown.json written with the ids under `held`).
- `complete`: `raise NavigatorError subclass NotesHeld(notes.hold_text(held), ids)`. Caught first in `shiploop_protocol._main`:
  text to STDERR only, exit 2, nothing on stdout, no "ShipLoop navigator:" prefix and none of the "do not end the turn" lines. The
  trace marks the line `held`, not a refusal. Exact first line (single note): `ShipLoop held this callback once: an owner note
  this action's packet did not print in full (written after it was printed, or no room in its head).` then the quote (each
  note: `    N2 14:03Z  <first line>`, continuation lines indented 6), then `If it changes this step's work, change the work and the
  result first. Then run the same callback again in this turn; it is not held twice for the same note.` and `The summary says, by id,
  what you did about it.` Plural: `owner notes`, `If one changes this step's work`, `about each`.
- `check` (`checking`): not raised. `print(notes.hold_text(held, check=True))` to STDOUT and `trace.SHOWN.extend(ids)`; first line:
  `ShipLoop check: an owner note this action's packet did not print in full (it shows the note now; the callback is not held for it):`
  then the quote, no instruction lines. The gates then run as usual: all pass -> exit 0, ending
  `ShipLoop check: the check says yes for <stage>: every script gate accepts this result now. Nothing was accepted, counted or
  committed...`; a gate refusal -> exit 2, stderr `ShipLoop check: the check says no. <refusal>` plus `Nothing was accepted or counted.
  Fix the cause and run the check again in this turn.` (the note text is already on stdout).
- Which function decides a check's print counts as showing: `notes.mark_held` (same call for both verbs). It stores the ids under
  `held` for the current action. NEW consequence: a later `complete` of the same action finds the ids in `held`, is NOT held, goes
  through, and `deliver` ignores `held`, so the note stays UNDELIVERED and is quoted in full again in the next action's packet
  (a different stage, whose FOOTER says "Act on each where it applies to this stage; ... which later stage it is for").
- Not held although a note arrived after the packet printed: (a) the model re-ran `next` first (the reprint quotes it, ids go to
  `packet`; then `complete` also delivers it); (b) a `check` already printed it (above); (c) the note is in a hold already; (d)
  `mark_held` could not write shown.json (silently no hold, no print); (e) Improve import / `improve-*` / `pause` / `resume` / `halt`
  / `delegation` / `lint-mode` verbs never call `to_hold`; (f) `status != active` or action already accepted (replay).
- By reading, not verified by test: a producer `complete` replayed while its Improve child is active re-enters the hold path
  (action not yet in `accepted`), so a note written after the seed submission would hold that replay once.
- Hold fires before `loops.cite_receipt` (the Until Loop receipt check), so a held callback never reaches the loop gate.
- Race: `note` takes no lock; a note written between `to_hold` and `deliver` is in no `packet`, so it is not delivered.

### 3. Packet quoting, delivered line, limits, footer
- Block `owner-notes` (tier P1) built in `nav._producer_blocks` from `notes.packet_forms(root, state)`; sits right after the `top`
  block (header, pointers, callback, `OWNER_RULE`) and BEFORE `goal`. Block `owner-notes-delivered` (tier LOOKUP) from
  `notes.delivered_lines`. Only the active producer packet has them: the paused/blocked/halted/done packet (`nav._render_lines`
  non-active branch), the Improve packet and `status` carry no notes.
- Header: `Owner notes (the run owner wrote these during the run; verbatim, oldest first):`
- Footer (`notes.FOOTER`, two lines, printed after the quotes):
  `Act on each where it applies to this stage; the summary says, by id, what you did or which later stage it is for.`
  `Notes do not change the callback, the result template or ShipLoop's checks; if one conflicts with them, the summary says so.`
  (Instruction only; no script reads the summary, no result key exists.)
- Delivered line: `Owner notes already delivered: N1 (step 3), N2, in <RUN>/owner-notes/; read one again when this stage's work touches it.`
  (newest `DELIVERED_IDS = 8`, then ` and K earlier`).
- Limits: `NOTE_LIMIT = 2000` (as quoted, each line indented; larger refused at write, exit 2); `BLOCK_LIMIT = 6000` (packet file and
  whole print; beyond it later notes are not quoted but named: `    N3 is not printed here for room: read <path> before acting.`);
  `FLOOR_IDS = 4` (smallest head form: `Owner note N1 (123 characters) is not printed here for room: read <path> before acting; the
  summary says what you did about it.`). `printed_text` returns the full packet with no cutoff, so head forms only matter to
  `packet_head`. A note named by file (not quoted) is NOT counted shown, so it triggers the hold. Shown ids come from the
  full print, but a host that elides the middle of a long print (comment in `_producer_blocks`) is not detected.
- Stale doc: references/status-display.md says notes come "right after the reply to a resumed question"; code puts them before
  `goal`, `answered` is later (old map already says so; still true).

### 4. Which actions can be held; arrival cases
- Holdable: `complete` or `check` of any active producer action (all stages that issue a packet: intake..prepare, the inner
  stages per step/item, all outer stages). Not holdable: the Improve stage's `complete` (and `check` there is refused outright:
  "`shiploop check` asks about a producer stage's draft result; the Improve stage has no draft to check..."), `improve-*`,
  control verbs. validate-existing recorded by script and left-out stages (`_record_not_applicable`) issue no packet and no hold.
  Inner loop: the hold precedes the loop receipt gate; the loop does not change delivery.
- Arrives during an Improve review: allowed (CLI prints `...an Improve stage is reviewing it, and the producer packet after it
  quotes the note`). Not shown to the review. First quoted in the packet printed after the import (next stage or next item's
  step), where it counts as that stage's note.
- Arrives while blocked/paused: allowed (CLI says the packet after `resume` quotes it; for blocked: `The run is blocked on:
  <question> Answer it with `resume --answer`; the packet after the resume quotes this note.`). The reissued action is new, so the
  note is quoted there. Notes shown in the pre-block packet were already delivered by the `blocked` result.
- After the last stage: status `done` or `halted` -> `note` exits 2, stderr `ShipLoop note: the run is done; no later step would
  read a note, so nothing was written.` A note written before the final `complete` but not shown is held once at the handoff
  callback; if it was only shown by a hold/check it ends undelivered. No script lists undelivered notes at done.

### 5. What the requester sees at the end
- Done packet (`nav._render_lines` done branch) and `nav._render_report`: NO owner-note line. Lines there are "It's all complete.",
  `Report: <run>/report.html`, `defaults.done_lines`, `follow_on.done_lines`, "This is agent-declared completion...".
- Status hook / progress view / `status`: none. Only `trace` (`shiploop_trace.notes_summary`, `trace.html`) shows notes:
  `Notes:    2 owner notes · N1 delivered #3 (cited) · N2 delivered #5 (not cited in its summary) · N3 shown, not delivered yet · N4 waiting for a packet`.
  `#3` = history step number of the delivering action; "cited" = regex `\bN<k>\b` in that action's accepted summary (a display check,
  no gate). Trace events: `wrote owner note N1`, `delivered owner note N1`, `printed owner note(s) ...` (a check's hold),
  `held for owner note(s) ...`. Facts shown: delivering step and citation only; never what changed.

### 6. Result keys and validation
- No result key says what a stage did with a note. `_RESULT_KEYS` (frozenset in nav) has no note key; `_canonical_result` raises
  `result has unsupported fields: <k>. Delete them and run the same callback again; a result carries only: <sorted keys>`.
  Not loose: unknown keys are refused. What is loose is the STORED SHAPE of each registered list key (`defaults`, `follow_on`,
  `unverified`, `primary`): `canonical` checks shape only, exact checks live at the CLI gates, because
  `_validate_current_state` re-canonicalises every accepted result on load and requires `canonical == accepted` ("accepted
  navigator result is not canonical"). A new key needs: `_RESULT_KEYS`, `_DONE_ONLY_FIELDS` (else a blocked/send-back/add-work result
  carrying it is refused: "a <outcome> result does not carry ... those fields belong to a done result"), a branch in
  `_canonical_result`, and a self-reproducing canonical form. A new state key needs `_STATE_KEYS` (and, if optional, the exemption set at
  `missing = sorted(allowed - {"status_reason", "delivery_contract_version", "delegation_hold", "owner_notes"} - keys)`).
- The summary is free text (`_text`, placeholder check against `_summary_placeholders`).

## PART B. Adding or changing work after the plan binds

### 7. carry-forward (last INNER stage per item; Improve rule `last-item`; outcomes done, blocked, send-back)
- Packet duties (`shiploop_prompts`, stage "carry-forward"): 1 Knowledge home (update in place; for spec: "KNOWLEDGE/spec.md: each
  R-<n> this item satisfied; an open gap under its R-<n>, an unresolved state or data change included (State and data
  assessment). Keep unaffected clauses, and never relax one to fit the code or tests."); 2 Queue; 3 Skill decision; 4 "Commit nothing."
- Duty 2 verbatim contract: "To change the queue give `work_items`: the whole future queue, rows `{"id", "title", "follows",
  "context"}` in prerequisite order, no completed or current ID, keeping unrelated pending work and each primary requirement in some
  item's `follows` (a completed or current item counts). Explain each removal, merge or supersession in the summary. Omit
  `work_items` to keep the queue." Packet lines (`nav._queue_lines`): "Omit work_items to retain the future queue. Supplied
  work_items replaces the entire future queue after the current item; it does not append." and "An empty array removes all future work".
- Result template (`nav._result_template`): `outcome, headline, summary, evidence_refs` plus `skill` `{decision, reason, path, evidence,
  index}`; `work_items` is optional and not in the template. Other keys valid at carry-forward: `assumptions` (open items; a carry-
  forward is an `OPEN_ITEM_STAGE`, so `assumptions` is REQUIRED: "Add assumptions to {result}"), `unverified`/`settled` only when
  restated. `lint_waivers` no.
- Can change: ADD a work item, DROP a future item, REORDER, rewrite `title`/`follows`/`context`, all by replacing the whole future
  queue (`nav._apply_result` -> `_replace_future_work_items`: keeps `work_items[:work_index+1]`, refuses an id equal to a completed or current id:
  "carry-forward work item repeats completed or current ID"; shape via `_normalise_work_items`: keys within id/title/follows/context,
  ids unique and safe, `follows` = list of R-/AD- ids each once). Not changeable: completed/current items.
- Script checks on a queue replacement (`nav._check_submitted_primary` -> `primary.check_queue`, stage in `QUEUE_STAGES = (plan, carry-forward)`,
  done only, only when `work_items` present): every `follows` id must have an entry in spec.md (R-) or architecture.md (AD-)
  ("work_items follows names X, with no entry (a line that starts with the ID) in <spec> (R-) or <arch> (AD-): cite only IDs with an entry,
  or write the entry first"); every primary requirement (the spec result's `primary`) must be in some item's `follows` of the queue
  left (completed + current + given). NEW: `follows` itself is OPTIONAL per item, so a new item need not follow any requirement;
  only primary coverage is enforced. If no spec result recorded `primary`, nothing is enforced.
- A requirement entry or AD decision in the living files: carry-forward may edit `docs/shiploop/spec.md` and architecture.md by
  prompt (`kh.STAGE_FILES["carry-forward"]` = architecture.md, environment.md; spec.md is NOT in that table but the duty says to
  edit it). Script: only `kh.check` via `nav._knowledge_gate` on a done result when the home changed: refuses a drop of any `R-<n>`
  (spec.md) or `AD-<n>` (architecture.md) present in HEAD: "Restore the lost R-<n> in <path> or move it under 'Retired', then run the
  same callback again." (AD: "...or move it under 'Superseded'..."). Rewording or relaxing a clause is NOT checked. The "knowledge" commit
  (`kh.knowledge_subject`) follows acceptance. Improve import re-runs `_knowledge_gate(..., "improve")`.
- reference text (references/carry-forward.md): "Incompatible findings. A changed requirement, permission, invocation contract or
  completed-work assumption is not a queue edit: report `blocked` or pause for direction." (prompt only; no script detects it).

### 8. Every route that adds work or goes back after planning
| Route | Stage that may use it | Key/outcome | What the script does | Limits |
|---|---|---|---|---|
| plan queue | `plan` only | done + `work_items` | `_replace_plan_work_items`: replaces whole queue | only while `stage=="plan"`, `work_index==0`, nothing completed: "plan work items can only be replaced before execution" |
| carry-forward queue | `carry-forward` | done + `work_items` | `_replace_future_work_items` (above) | future items only; `primary.check_queue` |
| add-work | every OUTER stage: system-test-author, system-test, product-acceptance, release-plan, release-check, release, release-verify, operations, handoff | outcome `add-work` + `work_items` `[{id,title,context}]` (`ss.ADD_WORK_SHAPE`) | `_apply_result`: ids must be new ("corrective work IDs must be new"), rows appended, `stage="inner-loop"`, `_begin_inner_loop` on the first new item; outer stages accepted before the last add-work are reopened (`nav._accepted_done`), so the run resumes at system-test-author after the new items; delta lines `_replan_delta_lines` when corrective items touched only non-code paths | no count cap (owner: no run caps); `follows` optional and `primary.check_queue` does NOT run (done-only); no spec edit in the route. Packet text: "add-work (product work is missing: corrective work_items [{id, title, context}] whose IDs are not already in state.md work_items; they run through INNER, then the run resumes at system-test-author)"; refusal "add-work requires corrective work_items at an outer stage" |
| send-back (inner) | test-spec .. document (`ss._finish`) | outcome `send-back` | `revisions[<item>]+=1`, `_replace_inner_action(updated,"step-plan")`; `planning_revision.current_actions` drops the item's results from step-plan on | changes steps/criteria/tests, not spec; `validate-existing` needs `failed_expectations` |
| send-back (outer) | system-test -> system-test-author; release-verify -> release-plan (`ss.OUTER_SEND_BACK_TO`) | outcome `send-back` | run goes back to the target stage and every later stage reruns | count in `revisions`, no cap |
| reconcile | only the initial plan's Improve child, stopped, via `improve-reconcile` (`nav._reconciliation_permitted`) | receipt `{summary,target,evidence_refs}`, target in `planning_revision.RECONCILIATION_TARGETS` = discovery, research, spec, test-strategy | records `reconcile`, `stage` = target with new action, drops accepted done results of target and later planning stages | "reconciliation is allowed only before prepare or work execution"; absent when `planning_review: none`; a plain `complete` of a reconcile result is refused ("reconcile requires improve-reconcile, never normal apply") |
| replan / revise / repeat | retired | `_canonical_result`: "revise, replan and repeat are retired" | - | - |
| blocked | any stage | outcome `blocked` + `awaiting` (kinds answer/present/service) | `status=blocked`, new action same stage; `resume --answer/--observed` writes `decisions/<action>.md`, packet block `answered` | needs `awaiting.no_default` (S-14) |
| Improve review edits | the six Improve stages | `final_result` on the import | review may change the result (e.g. the queue) before import; gates re-run at import | `final_result` must list the whole queue at plan/carry-forward |
Hold/delivery has no part in any of these routes.

### 9. Inside one work item (spec edits)
- `kh.step_spec_refusal` via `nav._step_spec_refusal`: runs in `_evaluate` for a done `implement` or `document` of an inline step
  (when `step_view` finds a step), and at the Improve import of `document`. It compares working-tree spec.md with HEAD. Allowed: new
  lines INSIDE an R-<n> entry HEAD already holds (non-retired), each ending `(<item>/<step id>)` (trailing `.`/`;` after the mark ok).
  Refused: a changed or removed line ("changed or removed"), an added line without the mark ("without the step's mark"), an added line
  outside an existing entry ("outside an R-<n> entry the committed spec holds", which includes a new requirement). Exact refusal first
  sentence: "Restore <path>/docs/shiploop/spec.md to what HEAD holds plus this step's requirement lines, then run the same callback
  again; to change a requirement, report send-back naming it." On refusal with `count` it opens the send-back route (`loops.open_send_back`).
- So `implement` and `document` MAY add marked acceptance lines inside an existing requirement (prompts: implement duty 4, document duty 3:
  "Add lines only; a requirement whose intent moved is no edit: report send-back naming the R-<n>."). The old map's claim holds.
- `step-plan`, `test-spec`, `validate-existing`, `test`: no spec-specific gate; only `kh.check` (ID retention) when the home changed.
  `kh.STAGE_FILES` lists spec.md only for `spec` and `document`; it is descriptive, no gate refuses an edit outside a stage's row.
- Gate order in `_evaluate` for those two stages: knowledge gate -> handoff gate -> ... -> `item_scope.scope_refusal` (implement) ->
  `_step_spec_refusal`.

### 10. Open items
- Live in the `assumptions` list of a done result (`shiploop_assumptions`): row `{id, assumption, disposition:"open", settle, reason,
  due_stage (or due_item at plan), owner?}`. Producers: plan (due_item = a work item) and the `OPEN_ITEM_STAGES` (test-spec, document,
  carry-forward, system-test-author, system-test, release-plan, release-verify; their `assumptions` key is required, `[]` if none:
  `_handoff_fault` "Add assumptions to {result}"). Allowed due stages: `assumptions.allowed_due_stages` (a later outer stage, or the
  same item's carry-forward from test-spec/document); else "Fix the due stages in {result}".
- Settled by `assumptions.open_items`/`_settled`: a row stops being open when a done result of its due stage that is current was
  accepted after the row's result ("A due stage with no assumptions field settles by its done result"). No check that the due stage
  addressed it. The plan's rows (due_item) are never auto-settled in the ledger; instead the step-plan of that item is refused
  unless it settles each with a criterion or expectation `from` the id (`expectations` check: "open plan assumptions ... name <W> as
  due_item; settle each here...").
- No end-of-run gate: nothing refuses `handoff` for an open item left. They are listed in the report ("Open items" table,
  `nav._handoff_sections`, "None open." otherwise), quoted in every later packet of the stages in `_EVERY_OPEN_ITEM` (carry-forward,
  product-acceptance, handoff), seeded into the unverified list at product-acceptance (plan rows only), written into the release-verify
  lessons commit (`_lessons_open_items`), and citable by `follow_on` source `assumption:<id>`. The literal phrase "recorded as open item"
  is model-authored prose; not found in script text.

## PART C

### 11. Stage order (`ss._ROWS`, `ss.STAGES`; `_check_table` requires 23)
- Prelude (planning, one per run): intake, discovery, research, spec, test-strategy, plan, prepare. (`planning_revision.PLANNING_STAGES` =
  discovery..prepare; reconcile targets only the first four of them; intake is before them.)
- Inner (per work item; implement/test/document repeat per step): step-plan, test-spec, validate-existing, implement, test, document,
  carry-forward.
- Outer / release: system-test-author, system-test, product-acceptance, release-plan, release-check, release, release-verify,
  operations, handoff. (Release stages proper: release-plan, release-check, release, release-verify; operations and handoff follow.)
- Improve rules (`ss.IMPROVE_RULES`): always = spec, test-strategy, plan, system-test-author, release-plan; first-item = step-plan; item
  (per step) = document; last-item = carry-forward. `planning_review: none` drops spec, test-strategy, plan, step-plan.

### 12. How a refusal is built, and the model for a list gate
- No literal "Refused:" prefix exists. `nav._evaluate(core, root, state, action_id, stage, workitem, submitted, *, count)` runs the gates in
  order and raises `NavigatorError(<message>)` for the first failure; `complete` prints it via `shiploop_protocol._main`:
  stderr `ShipLoop navigator: <message>`, `Read the current packet with next; the rejected request did not advance the graph.`, `The run
  is still active: fix the result and resubmit in this turn; do not end the turn over a refused callback.`, exit 2. `check` prints
  `ShipLoop check: the check says no. <message>` + `Nothing was accepted or counted. Fix the cause and run the check again in this turn.`, exit 2.
  Module-level gate functions raise their own error class; `nav._check_submitted_*` wrappers re-raise as NavigatorError.
- Model gate, the `defaults` list (shiploop_defaults.py; ShipLoop 2.6.0): registered in `nav._RESULT_KEYS` and `_DONE_ONLY_FIELDS`;
  shape-only `defaults.canonical` called from `_canonical_result` (`if "defaults" in value:` stage/outcome check first); template row in
  `_result_template`; CLI gate `defaults.check_submitted(repo, stage, result)` wrapped by `nav._check_submitted_defaults(state, stage,
  result)`, called at three sites: `_evaluate`, `dispatch` matching-yes reuse path, and `dispatch` Improve import branch; gate words in
  `_stage_gates` ("a missing defaults list, an entry that is incomplete or still holds a template placeholder, or a requirement with no
  current entry in KNOWLEDGE/spec.md"); Improve handoff line in `_render_improve`; packet block via `_stage_input_blocks`/`defaults.packet_lines`;
  done packet `defaults.done_lines`; report `defaults.html_section`. Sibling models: `shiploop_follow_on.py` (`STAGES={"handoff"}`, `FIELDS`,
  `TEMPLATE_ROW`, `check_submitted`, `done_lines`), `shiploop_unverified.py`, `shiploop_primary.py`. Tests that pin a new gate:
  test/shiploop-packet-completeness.test.py (`GATE_WORDS`), shiploop-packet-bounds.test.py (limit constants need a `LIMIT_KINDS` row).

## Where main differs from or adds to the old map
1. NEW: `check` that prints a note records it as `held`, lets the later `complete` through with no hold, and never delivers it (the
   old map says a check prints the text instead of holding; it does not say the consequence).
2. NEW: delivery happens at the producer's seed submission when the stage has an Improve checkpoint; the review's import neither holds
   nor delivers, and the review packet never prints notes.
3. NEW: `blocked`, `send-back` and `add-work` results deliver the notes their packet showed (the old map says only "an accepted step").
4. NEW: carry-forward's required `assumptions`; `follows` optional on new items; `primary.check_queue` does not run on add-work.
5. NEW: carry-forward's duty edits spec.md although `kh.STAGE_FILES["carry-forward"]` omits it (table is descriptive only).
6. Old map section 2 item "no gate for carry-forward edits" is confirmed: only `kh.check` ID retention.
7. Nothing in the old map's sections 1, 3, 6, 7 was found wrong on main; its `defaults` section 4 matches main (the pilot module is on main).
