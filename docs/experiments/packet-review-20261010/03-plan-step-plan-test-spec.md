# Packet review report: plan-step-plan-test-spec

Verbatim final report of one read-only reviewer (2026-10-10). Packets: checkers-1, battleship-1, s6-after-spec (ShipLoop 0.58.0, release 1.26.0) and older runs. Scratch analysis scripts were not kept; counts are the reviewer's.

STAGE REPORT: plan, prepare, get-next-work-item, step-plan, test-spec, and the Improve packets for plan, step-plan and test-spec. Read-only; nothing in any repo or run folder was changed.

Evidence base. I read the plan, prepare, get-next-work-item, step-plan and test-spec packets of checkers-1, and the stage-specific parts of the same five in battleship-1 and s6-after-spec. I read the plan packets of v1220-battleship-grok-medium-none, r3-battleship-grok-none and the Checkers/Battleship older runs, and the three Improve packets of checkers-1. I also read the engine source for the duty text, the "Checked by" line, the assumption checks, the knowledge-home close and the test-command checks. Across the 16 exported runs, every one of my stages was accepted done on its first try. The only exception is one Grok v1230 test-spec "revise". The refusals that touch my stages are:
- plan: `assumption A3 (open) needs exactly check, consumer, reason`, twice, in r2-checkers-sonnet.
- prepare: `Before prepare is done, write: .../features/create-hello...`, once, in s6-inside-implement.
- unknown stage: `a check command is judged by its exit code and takes no ids or min_tests`, in 4 runs (r2-battleship-grok-none, r3-checkers-sonnet, r3-checkers-quality-preview, checkers-1). In checkers-1 it was release-plan. The other three are unattributed because `callback-attempts/` is empty and the old run docs carry no stage.

Sufficiency here is therefore mostly shown by absence of refusals. The cost is bytes.

STAGE plan (packets read: 6, 53.6-58.3 KB; checkers-1 55,362 B)
- Accurate: issues. Wording is mostly right, but plan.md is a later gate the packet does not mention, and one printed path never exists.
- Grounded: yes. Ids, paths and the queue come from state, and every path I spot-checked exists except the notebook.
- Sufficient: both. Everything the model needs is there, but about 70% of the bytes are not plan-specific.

Only about 17 KB of the packet is unique to plan. About 22 KB appears in nearly every stage's packet.

P-plan-1 (medium). The open-assumption shape is printed but never described as exact.
- Evidence: plan packet template with `check, consumer, reason`; r2-checkers-sonnet was refused twice, line `assumption A3 (open) needs exactly check, consumer, reason`.
- Source: `shiploop_assumptions.canonical` rejects any extra key.
- Fix: add one sentence next to the template: "each disposition takes exactly these fields; extra keys are refused; consumer must be a work-item id in this plan". Put it in `_stage_gates` / the plan duty in `shiploop_prompts.py`.

P-plan-2 (medium). Plan.md is required at the prepare close, but the plan packet does not say so.
- Evidence: plan packet "keeps these up to date: plan.md, README.md"; "Checked by" has no knowledge gate. `shiploop_knowledge_home.CLOSES["prepare"]` requires plan.md, spec.md and others. Run evidence: the s6-inside-implement prepare refusal.
- Fix: in `knowledge_home.stage_lines`, for stages in `STAGE_FILES` that are not themselves a close, add "ShipLoop refuses `<close>` if this file is missing or empty".

P-plan-3 (medium). Contradictory review wording around the Backchain child, plus about 4.5 KB the model chose to skip.
- Evidence: lines 318-322 "Do not embed an Improve review campaign"; line 360 "submit ... to its mandatory actual Improve handoff ... Do not schedule an extra review"; lines 523-563 describe an Until Loop child with its own review/fix/check cycle; line 541 "your choice: nothing refuses a plan without it".
- Run evidence: checkers-1's summary says "no Backchain plan/draft child". The 4.5 KB `_BACKCHAIN_PLAN_CALL` + `_PLAN_GATE_ONE` block is printed in every default run.
- Fix: print the loop text only on request (see redesign).

P-plan-4 (low). The "Planning investigation notebook" path is printed as an existing source, but no code creates it.
- Evidence: `.shiploop-improve/nav-bd4.../planning-investigation.md` is absent in checkers-1. Source: `shiploop_navigator.py:3287` builds the path only.
- Fix: label it "optional; create it if you use it", as the pass log already is.

P-plan-5 (low). The same rule is stated three or more times.
- Evidence: "supplied work_items replaces the whole queue" appears at lines 62, 196 and 436-439; "retain compact locators in context / evidence_refs" at least four times.

P-plan-6 (medium, bytes). The workspace-return block is irrelevant to plan.
- Evidence: lines 171-183, 2.6 KB (`workspace plan-return`, the keep/exclude flags, "return operation is unavailable here").
- Fix: show it only at release-plan, release-verify and handoff.

STAGE prepare (packets read: 5, 30.9-34.9 KB; checkers-1 31,851 B)
- Accurate: issues. It mislabels the knowledge files as this stage's and carries planning-pass text that does not apply.
- Grounded: yes.
- Sufficient: both. Only about 4.4 KB is unique.

P-prepare-1 (medium). Six files are listed as "This stage keeps these up to date (create them if missing)", but five were due from earlier stages.
- Evidence: the packet lists README.md, spec.md, environment.md, test-strategy.md and `{feature}/spec.md`, `{feature}/plan.md`. `CLOSES["prepare"]` refuses on any of them. The s6-inside-implement refusal is `Before prepare is done, write: ...`; the truncated line leaves it unclear which file was missing.
- Fix: split the line into "written by earlier stages; ShipLoop will refuse prepare if missing" and "yours: environment.md".

P-prepare-2 (low). The "Preserve this planning pass's ... At plan and step-plan, consolidate" paragraph is printed in prepare.
- Evidence: `_PLANNING_HANDOFF` is attached to every PRELUDE stage by `prompt()`.
- Fix: attach it only to plan, spec and test-strategy.

P-prepare-3 (low). Done-when says "readiness is recorded" but names no location.
- Evidence: checkers-1 used environment.md plus a scratch file.
- Fix: say "record readiness in docs/shiploop/environment.md and cite the runner output file in evidence_refs".

STAGE get-next-work-item (packets read: 5, 29.5-33.5 KB; checkers-1 30,137 B)
- Accurate: yes. The duty, "Delegation: inline" and "Improve: advances directly" all match `stage_spec`.
- Grounded: yes. The item, queue and prerequisites are real.
- Sufficient: excessive. The duty is 8 lines (about 0.7 KB); unique-to-stage bytes are 2.6 KB.

P-gnwi-1 (medium, bytes). 30 KB for a revalidation, made up of:
- COMMON 6.5 KB
- locator and policy block 9.6 KB
- PROGRESS_REPORTING 2.5 KB
- status and narrative 2.3 KB
- planning sources and test-strategy source 3.0 KB

It never failed in 16 runs, so the fix is a compact variant: the head, the item context, the revalidation checklist and the callback.

STAGE step-plan (packets read: 6, 51.3-57.5 KB; checkers-1 53,407 B)
- Accurate: issues. An inverted dependency on test ids, a template example that leaks, and a stale suite list.
- Grounded: yes.
- Sufficient: both. About 14.7 KB is unique and well aimed; the rest is boilerplate and a repeated interaction block.

P-step-1 (medium). The result template carries concrete content that real outputs copy.
- Evidence: template criterion `"README documents ..."` and command `grep -q '...' README.md`. Neither the Checkers nor the Battleship request asks for a README, yet checkers-1 produced S4 "Write README.md" and criterion C4, and battleship-1 produced a "README documents running the server and tests" criterion. s6-after-spec (hello) did not.
- Source: the template builder in `shiploop_navigator.py` (the step-plan sample).
- Fix: use neutral placeholders (`"<criterion>"`, `"<exit-code check command>"`).

P-step-2 (medium). The duty asks step-plan to give `ids` of "the test-spec cases", but test-spec runs after step-plan.
- Evidence: step-plan duty (`shiploop_prompts.py` ~1160): "Give each focused command the ids of the test-spec cases it must run". The test-spec duty (`DUTIES["test-spec"]`, lines 1267-1283) never says to keep those ids. The test-author gate refuses unless every listed id is shown.
- Fix: step-plan: "ids you will title the cases with (from test-strategy TC-n)"; test-spec: "title each case with the ids declared in the step plan's test_commands".

P-step-3 (low/medium). The duty lists suites as `"focused" | "regression"` and omits `check`.
- Evidence: duty line 347 against `SUITES = ("focused","regression","check")`. The refusal `a check command ... takes no ids or min_tests` occurred in 4 runs (stage known only for checkers-1, where it was release-plan).
- Fix: in the duty add "`check` (judged by exit code; no ids or min_tests)".

P-step-4 (medium, bytes). The interaction-design and state-lifecycle block (3.1 KB) is identical to the plan packet's, for a one-page game. See the redesign.

STAGE test-spec (packets read: 5, 34.2-39.9 KB; checkers-1 35,353 B)
- Accurate: yes. "revise (... 2 of 2 left for this item)" matches `MAX_REVISES=2`, and "On done ShipLoop checks these files" matches `CLOSES["test-spec"]`.
- Grounded: yes.
- Sufficient: insufficient on output format, excessive on bytes.

P-ts-1 (medium). The packet never says where or in what shape the cases go.
- Evidence: the duty says "Map the item to ... assertions"; only the knowledge line names `test-spec.md`. The result template has no case list, and test-author later depends on case ids and an oracle per case.
- Fix: one sentence: "write one entry per case in test-spec.md: id, setup, action, independent oracle, RED, GREEN".

P-ts-2 (low). It carries the Reusable-test-facilities paragraph (about 0.9 KB) and the generic planning handoff that apply only when a facility is missing.

IMPROVE PACKETS (plan 57.6 KB, step-plan 52.8 KB, test-spec 47.0 KB)
- Accurate: issues. The review-focus bullet does not fit step-plan or test-spec.
- Grounded: yes. The embedded result is real, and the receipt, opening and scratch paths are consistent with `improve-start`.
- Sufficient: excessive. 25.1, 22.3 and 20.3 KB of lines are byte-identical to the producer packet; the embedded result is only 2.5, 3.2 and 0.5 KB.

P-imp-1 (medium). The shared "Planning review focus" bullet says "run it once and record the exit code and the cases it executes".
- Evidence: the same text appears in all three packets (source `PLANNING_REVIEW_FOCUS`, `shiploop_prompts.py:2507`). At step-plan and test-spec the tests do not exist yet (RED comes after test-author), so the command cannot run to a meaningful result.
- Fix: parameterise: "run it once if its test files exist; otherwise check the path and runner flags only".

P-imp-2 (medium, bytes). Each Improve packet repeats the policy locator list, workspace text, planning sources, PROGRESS_REPORTING (2.5 KB) and queue text from the producer.
- Evidence: the identical-line counts above.
- Fix: the Improve packet should be the review head, the result and the child protocol, citing the producer packet by path.

P-imp-3 (low). The plan Improve packet's "Last accepted transition" is test-strategy, not the plan under review. It is true but confusing.

TOP FIVE TO FIX FIRST
1. Plan packet redesign (below): about 55 KB to about 12 KB, with the Backchain loop and interaction blocks behind lookups.
2. Remove the README leak from the step-plan template (P-step-1). It changes product scope in 2 of 2 full real runs.
3. Fix the step-plan <-> test-spec id contract (P-step-2, P-ts-1, P-step-3).
4. State the exact assumption fields and the plan.md prepare-close gate in the plan packet (P-plan-1, P-plan-2, P-prepare-1). These are the only refusals I could tie to my stages.
5. Slim the Improve packets and fix the review-focus bullet (P-imp-1, P-imp-2).

Unanswered:
- Which stage raised the `check command` refusal in three of the four runs (`callback-attempts/` is empty).
- Which file the s6-inside-implement prepare refusal named (the exported line is truncated).
- Whether the Backchain loop child was ever used in the 16 runs (only the summaries could say; none I read used it).

PLAN PACKET REDESIGN

(1) Measured breakdown of the CURRENT plan packet.
The 1.22.0 packet (55,225 B) and the 1.26.0 packet (55,362 B) have the same shape, so four releases changed nothing in size. Measured on 1.26.0 checkers-1; the sizes are approximate +-100 B because some blocks share lines.

Block | Bytes | Gated on a run fact?
Head, callback, goal/done/checked, considerations | 1,900 | no (stage)
Result template + outcome shapes | 1,960 | no
Context index, pass log, "builds on" ids | 1,640 | no
Status snapshot + status block + narrative | 2,360 | no (the packet says "do not reprint")
State / records / CLI / skill-card / recovery locators | 1,430 | no
14 policy and guide locator lines | 3,850 | per-stage list only
Original request | 1,360 | no
12 guidance locators (delivery ... test facilities) | 2,170 | per-stage list only
Workspace / return text | 2,620 | no (printed at every stage)
Backchain resources + graph check + queue note | 2,300 | partly (backchain_passes mode)
Planning sources, experiments, last accepted, test-strategy source | 4,780 | no
Knowledge-home lines | 770 | per-stage
COMMON stage guidance | 6,470 | no (varies only by planning_review swaps)
Plan duty, core | 2,860 | stage
Plan duty, reconciliation, namespaces, work items | 5,750 | stage
INTERACTION_DESIGN + state lifecycle / channel | 3,100 | stage only; text says "when applicable"
WORK_ITEM_CONTEXT + planning handoff | 920 | stage
TEST_FACILITY_HANDOFF | 880 | stage
Backchain native-route + Until Loop contract budget | 4,540 | backchain_passes and planning_review only
PROGRESS_REPORTING | 2,450 | no
Callback, Improve, pause, halt tail | 1,400 | planning_review swap

Of the 55 KB, 85 lines (16.3 KB) carry an absolute path. The run root occurs 96 times (4.2 KB) and the plugin prefix 47 times (3.6 KB).
- The script already knows these gates: `delegation`, `planning_review`, `backchain_passes`, the stage, the provisional queue, whether `workspace.md` exists, and whether a knowledge home exists.
- It does not know structurally: whether there is a UI, whether new code or stored data is added, or whether a delivery target exists. The plan stage decides the final number of work items, so "more than one item" cannot gate anything at plan.

(2) Proposal: a compact plan packet that still stands alone.

Head (about 1.8 KB), literal and copy-pasteable:
- stage, revision, goal, 3 done-when lines, the exact callback command, and the result path.
- One line: "Roots: RUN=<run dir>; WT=<worktree>; SK=<plugin skills dir>. Paths below are relative to these."
- Callback and recovery commands stay absolute, since they must run unchanged.

Inputs as ids (about 1.4 KB):
- One block "Read first", one line per input: `intake RUN/results/nav-0b35...md`, and likewise for discovery, research, spec and test-strategy.
- Then `WT/docs/shiploop/{spec,test-strategy,environment}.md`.
- Then the original request verbatim, with its tag marker (about 1.3 KB). The request is the one thing a cleared context cannot rebuild, so it stays.

Result contract (about 1.7 KB):
- Keep the template with assumptions, work_items, headline and evidence_refs.
- Add one line per refusal rule: "assumption fields are exact per disposition; open -> check, reason, consumer (a work-item id in your queue); done needs the assumptions list (empty allowed); work_items is the complete ordered queue, each {id, title, context}, id like `W1`; headline <=100 characters and not a placeholder; evidence_refs absolute and existing; other outcomes are one line".

Planning checklist (about 2.8 KB), 8 items, each one obligation plus a locator:
- Outcomes -> owning work item. Every R-id and criterion has exactly one owner.
- Supplier -> consumer dependencies, with ready and done conditions per item. Split by prerequisite or independent checkability. Locator: `backchain-planning.md#dependency-audit`.
- Environment and architecture. For each environment the work touches, record where code and data live, the home namespace, visibility and collision check, and the data map. Locators: `coding-practices.md#namespaces-and-placement` and `#schema-and-storage`. Record it as a "Namespace and data map" in plan.md, copy each item's entry into its `context`, and name the module format and loadable test seam per item.
- State ownership and lifecycle. Per piece of state: owner, who may read, concurrent-change rule, end of life, quotas. Choose the lightest channel (request/response before polling before push) and the simplest placement. Keep 5 lines of this in the packet, because it appears in no reference today (see below).
- Test-facility prerequisites as their own work item. Locator: `repeatable-test-suites.md#reuse-and-define-test-facilities`. Initial baseline: `execution-planning.md#initial-repository-baseline`.
- Delivery authority and environment work. Locators: `delivery-authority.md#ask-at-the-first-concrete-boundary` and `environment-lifecycle.md`.
- Carry the test-strategy source and TC ids into each item's `context`.
- Files to write: `plan.md` and `README.md` under the feature dir. State that plan.md is required at the prepare close and that docs/shiploop is committed by ShipLoop.

Gated blocks:
- UI: one line plus `behavioral-requirements.md#ui-specific-planning`.
- Backchain loop: a 3-line stub plus `shiploop backchain-start --run-dir ...`, which prints the 4.5 KB contract text and the 9,216-byte budget only when asked. Rule in the stub: "request the child only if you draft >=2 items with cross-item dependencies".
- Workspace / return text: absent at plan.
- Interaction block: absent unless the spec or discovery result sets `surfaces: ui|network|shared-state`. This needs a small optional structured field in those result schemas.

Fixed text (about 1.3 KB), condensed from COMMON:
- Unattended rule: take the default, record an assumption, continue; blocked only if nothing proceeds.
- Blocked / awaiting shape.
- Scratch directory.
- "Open a locator only when its case applies; an unopened locator is not a gap."

Tail (about 1.0 KB): the Improve line, pause, halt, recovery, and a one-line status (Phase, Done, Next). The full status block and the narrative stay only when the narrative is due.

(3) Byte budget and engine places.

Block | Target bytes
Head + roots + callback | 1,800
Inputs and original request | 2,700
Result contract | 1,700
Checklist (8 items with locators) | 2,800
Gated stubs (UI, Backchain, workspace) | 300-900
Condensed COMMON | 1,300
Tail | 1,000
Total | about 11-12 KB, roughly 78% smaller

Where to change:
- `shiploop_prompts.py`:
  - `prompt()` (line 2450): assemble the compact variant.
  - `COMMON` (406): split into a short core plus a section in `navigator.md#sdlc-responsibilities`.
  - `DUTIES["plan"]` (992): rewrite as the checklist.
  - `INTERACTION_DESIGN` (500), `WORK_ITEM_CONTEXT` (542), `_PLANNING_HANDOFF` (2287) and `TEST_FACILITY_HANDOFF` (1888): gate or shorten.
  - `_backchain_guidance` (2145): move `_BACKCHAIN_PLAN_CALL` and `_PLAN_GATE_ONE` behind the new command.
  - `PROGRESS_REPORTING` (373): condense.
- `shiploop_navigator.py`:
  - The locator, policy and workspace builders (about 3100-3300), the planning-sources and last-accepted lines, `_checked_line` (3624), `_stage_gates` and the template sample builder.
  - A path-rendering helper (a "Roots:" substitution) used by all of them.
- `shiploop_narrative.py` and the status inclusion: print the status block and narrative once.
- `shiploop_knowledge_home.stage_lines`: the P-plan-2 sentence.
- `behavioral-requirements.md`: add the state-and-lifecycle and lightest-channel text. Today it lives only in the prompt, so it cannot be moved to a reference until it is added there.

Obligations that must NOT move to a reference, because a refusal at plan depends on them:
- Assumption exact fields; `consumer` must be a queue work-item id; the `assumptions` list is required for done (`shiploop_assumptions.canonical` / `check_consumers`).
- `work_items` shape: id regex, no extra keys, complete queue (`_normalise_work_items`).
- Headline <=100 characters and not a placeholder; `evidence_refs` absolute and existing.
- plan.md and README.md written; credential screening of docs/shiploop (refusals `These knowledge lines look like credentials` in r1-checkers, r2-battleship-grok-none and r3-battleship-grok-none, at stages I could not attribute); no spec requirement id dropped.
- At improve-complete: "omitting work_items is refused" must stay in the plan Improve packet (`navigator.py:2069`).
- If the loop is requested: the 9,216-byte start-contract budget and the `Backchain passes: one` marker. The `backchain-start` output must carry them.

Main-tenet check. After a context clear the compact packet still has the goal, done-when, original request, input ids, exact result contract, the decision checklist, recovery and callback commands. Everything it moves out is a rule the model opens at a named `reference#section` when that case applies. The one risk is that the model skips a locator it needs. The mitigation is that the checklist item names the artifact each locator produces (for example "Namespace and data map in plan.md"), so the missing artifact is visible to the Improve child.
