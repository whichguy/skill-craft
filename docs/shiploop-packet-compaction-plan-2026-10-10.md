---
Execute: ask
---

# ShipLoop packet compaction plan, 2026-10-10

Goal: every packet is a **card** that a model holding only that packet can act on (S-6): what the stage is for, what it
reads, what to do, what ShipLoop checks, what to write, how to recover; with no content that does not apply to the stage,
and with long material reached through short, symbolic, resolvable references. Input: `docs/shiploop-packet-review-2026-10-10.md`
(13 observed-harm defects, an information table, a size table, the plan-packet redesign) and its evidence.

Status: plan only; nothing implemented. A release is the owner's decision. Packet-text changes follow the batch process
(design, fail-first tests, adversarial review, change note).

## 1. What the evidence says the design must do

| Fact (checkers-1 unless noted) | Design consequence |
|---|---|
| The model read 3 of 46 packets whole; 43 visits used the printed head plus a `sed` of Goal-to-template or one grep | Everything normative must be in the first screen and in Done-when. The tail is for cold resume, not for obligations. |
| Refusals trace to a rule that is true but stated nowhere the model looked (gate omitted from "Checked by", receipt path at "Do step 3", `check` rows carry no ids) | Generate "Checked by", the gates and the allowed outcomes from the one stage table, so a sentence cannot name a gate the code does not run or omit one it does. |
| Mean packet 37.7 KB; 67% is frame shared by all stages; absolute paths are 23% of all bytes; 24 of 29 shell reads were slicing a packet or grepping a reference | Compress paths once (roots), gate blocks by script facts, and let the script print the one reference section a step needs. |
| S-6: repetition across packets is grounding; only repetition inside one packet is waste. Moving grounding into a file the packet merely names fails S-6 unless a clear-context probe shows no redone work | Every cut is one of: a within-packet duplicate, text irrelevant to the stage, or an explanation replaced by a one-line obligation plus a resolvable reference. Each group of cuts is gated by a probe (section 6). |
| Owner rules: Improve is named only where it is a directive; prompts concise but keep obligations; cite symbols, not line numbers; one supported version | No negatives about Improve; no compatibility shim for the old packet shape; docs cite functions and anchors. |

## 2. The packet anatomy (one order, all stages)

One renderer assembles every packet from the stage row. Sections, in print order; the first four fit one screen (the head).

| # | Section | Content | Source of truth |
|---|---|---|---|
| 1 | Stage line | `ShipLoop navigator | stage | revision` | state |
| 2 | Goal and Done-when | the stage goal and the bullets the result is judged by (and, for a reviewed stage, the Improve review focus, so the producer knows how it is reviewed) | stage row and `PLANNING_REVIEW_FOCUS` |
| 3 | Callback and result | exact `complete` command, result path, template, allowed outcomes and shapes | `_result_contract_lines` |
| 4 | Checked by | what ShipLoop verifies on done: the common gates plus this stage's `complete_runs`, assumption, recorded-command, knowledge-close, skill_na and unverified gates | generated from the stage table (`_checked_line`, `_stage_gates`), no free text |
| 5 | Do | the stage duty as short numbered obligations; each carries a reference symbol where the explanation lives; the delegation line is one line, below this section | `DUTIES[stage]` |
| 6 | Reads | the request (stages that need it), the results this stage builds on as `label ROOT/results/<id>`, the work item and step, and the knowledge files the stage writes, with the line "ShipLoop refuses `<close>` if missing" | `stage_spec.reads`, `knowledge.STAGE_FILES/CLOSES` |
| 7 | References | `ref symbol - one-line gist - open when ...`; no whole-file pointers | stage row `refs` |
| 8 | Run state | Where, Next, queue, last accepted (bounded); the long status block and narrative only when due | `_progress_lines`, `status_block` |
| 9 | Recovery | `next`, `pause`, `halt`, keepalive marker, the return commands only at the stages that may use them | literal commands |
| 10 | Roots | one legend line: `RUN`, `WT`, `SK`, `REF`, `PKT` expansions | run state |
| 11 | Gated blocks | printed only when a script fact holds (table in section 4) | stage row `blocks` |

Why this order helps: the model's observed slice (Goal to template) now also contains Checked by and the obligations; a cold
resume reads the whole file and finds the same text. The packet still restates how the stage operates and is checked (S-6).

## 3. Symbolic references (what saves tokens and what does not)

| Kind | Mechanism | Estimate (checkers-1, from the frame report) | Risk |
|---|---|---|---|
| Roots | Section 10 defines `RUN`, `WT`, `SK`, `REF`; non-command paths are written `RUN/results/nav-xxxx.md`. Callback, recovery, pause, halt and every workspace command stay literal and copy-pasteable | 227 KB of 1.81 MB per run (292 KB if commands may use exported variables) | a model passes `RUN/...` unexpanded to a read tool; probe it (section 6) before shipping |
| Section resolver | new verb `shiploop ref REF/<file>#<anchor>` prints just that section, bounded (S-4 small interface, S-5 script does the lookup). Packets print `ref` symbols; the model runs one command instead of `grep`/`sed` | replaces most of the 29 shell reads per run; cost is one verb plus an anchor-resolution test | the anchor must resolve (existing test checks them); the verb prints nothing for an unknown anchor and says so |
| Constant locator table | one line `REF: a, b, c, ...` of file names plus the roots, instead of 26 absolute path lines; only the references the stage uses are listed with a gist, the rest one `REF/INDEX` away | 37 KB per run; existence-gated lines (`environment-lifecycle.md`, repository knowledge index) another 15 KB | none beyond the roots risk |
| Result ids | inputs as `label RUN/results/<id>.md`, the request kept verbatim where the stage needs it | in plan packet 1.4 KB instead of about 4.8 KB of source lines | the request must stay for planning stages |

Not proposed: a second naming layer of short codes for references (`R7`, `cp#ns`). It saves little beyond the roots and adds
an indirection the model must resolve after a clear. Reference names are already stable (`file#anchor`, checked by test).

## 4. Gating facts (all already known to the script unless marked)

| Block | Print only when |
|---|---|
| workspace, plan-return, review-return (2.4-2.7 KB) | stage is release-plan, release-check, release, handoff, or the run is blocked or paused; elsewhere one line "return is unavailable until release" |
| Backchain and Until Loop budget (2.9-5.2 KB) | `backchain_passes` allows a loop at this stage and the model asked (`shiploop backchain-start` prints the contract and the 9,216-byte budget); carry-forward only with a non-empty queue |
| interaction design and state lifecycle (3.1 KB) | the spec or discovery result carries `surfaces: ui | network | shared-state` (**new optional field, additive**); the five lines about owner, readers, concurrency, end of life and lightest channel stay in plan |
| Code craft (3.7 KB) | the stage edits code (not test-red, document, integrate) |
| lint block | static-checks and verify, named from `GATE_STAGES`; lint mode rendered, not assumed |
| skill_na clause | `skill_na` was recorded; names the observed skill surface |
| identity, runtime-entry paragraphs | preparation and release stages |
| Improve text | the stage has an Improve child, as a directive; none elsewhere |
| two "if present" locator lines | the file exists |
| delegation preamble | one line below the callback; never the first screen |

## 5. Per-packet re-cut

Columns: purpose (what the packet is for), what it keeps (refusal-bearing, in the first screen), what moves to a reference
symbol, what is gated or dropped, what is added (from the review). "Row n" is the observed-harm row of the review.

| Group (stages) | Purpose | Keeps | To a reference symbol | Gated or dropped | Added |
|---|---|---|---|---|---|
| intake | record the request, scope, access and route | request, counts, clean-main return route | testing guide sections | return block, planning handoff, Improve clauses, "last 1 commit messages" plural | what README.md holds, or drop it from intake |
| discovery, research | establish the system and resolve unknowns within one allowance | allowance numbers (15 active minutes, 64 host actions, 3 experiments), the decision-note file, assumption list item in Done-when | `research-loop.md#budget-stopping-and-convergence`, interaction design | interaction block, service/cache/async paragraphs unless `surfaces`; stage itself listed as a source | notebook "create if a plan trigger applies" (rows P-discovery, P-research) |
| spec | reconcile the request with requirements; verifiable criteria | output path, "keep every R-id", credential screen and dropped-R-id gate in Checked by, review-focus bullets (row 9), the spec-level Backchain sentence | backchain repair/revise machinery | Backchain budget text, Improve negatives | pointer to the audit route |
| test-strategy | map requirements to observable checks | whole-word ID rule (row 10), browser-case-or-unverified decision with owner and due stage, `discovery` in reads, the `test-strategy.md` gate | repeatable test-suite guide section (once, not whole file and section) | facility and baseline paragraphs unless relevant | the pre-Improve summary corrected at `improve-complete` |
| plan | provisional dependency plan and work queue | the 11-12 KB form in the review: head, inputs, exact result rules (assumption fields, `work_items`, headline, `evidence_refs`), eight-item checklist | namespaces, schema, dependency audit, facilities, delivery authority sections | Backchain loop text, workspace text, interaction block, planning experiments guide unless the plan child runs | `plan.md` required at prepare close (row 11) |
| prepare | ready the environment | what the stage writes vs what earlier stages wrote | planning handoff | planning-pass paragraph | where readiness is recorded (row 11) |
| get-next-work-item | revalidate the next item | item, queue, prerequisites, revalidation checklist | everything else | the 30 KB frame reduced to head, item context, checklist, callback | none |
| step-plan | turn the item into steps, commands, criteria | neutral template (row 6), ids declared as titles (row 7), `check` suite, paths declared, criteria | interaction block, test-facility handoff | README example, repeated interaction block | none |
| test-spec, test-author | specify and write the failing tests | case entry format (row 7), command list, ids, ID word rule, min_tests, "a failing test that shows every id" (row 8), `red_na` line | test facility paragraph | replan from inner outcomes, Code craft in test-red | probe listing in `shiploop_test_loop` |
| baseline, test-red, test-green, test-refine, regression, static-checks | run, record and tighten tests | receipt prefilled in `evidence_refs`, exit and repeat conditions, Start/Receipt/commands under the callback (row 3), commands and discovery baseline (baseline) | the 18.9 KB adapter read: print `report_schema` and `done_argv` from the first runtime packet | RED contract stated once, Code craft in test-red, workspace block | "each key once; replace the placeholders" |
| implement | one step of the item | step, criteria it covers, step-scoped exit wording, progress as "in progress k of N", lint command next to the callback | constitution and Code craft overlap: one | delegation chains text, service changes text | criteria printed (row 13) |
| document, integrate, integration-verify, carry-forward | docs, assembly, interface check, learnings | declared vs undeclared changed files and one commit sentence (row 4), step plan in `reads`, one cap rule, named destination for learnings and the `work_items` shape | Backchain block | Code craft in document and integrate, the Goal word "working branch", empty-queue Backchain block | script commits docs-class files |
| skill-assess, skill-validate | decide whether a skill is produced and validate it | the structured `skill_change` field | test-decision and requirements paragraphs | script records validate as N/A when false | `skill_na` default for small items |
| verify | confirm every criterion | the criteria and the criterion-to-command tie, failure routing, lint advisory once | lint block | stale "only implement" sentence | none |
| system-test-author, system-test, product-acceptance | system-level cases and acceptance | `check` rows carry no ids (row 2), the open-item route for a case that cannot run or fails to run (row 5), person-only rule | consumer delivery pointers | Backchain block at product-acceptance, plan/review-return | none |
| release-plan, release-check, release, release-verify, operations, handoff | plan, confirm, perform and verify the return; hand off | authority text, outcome.md gate in Checked by and Done-when (row 1), rollback recipes at release, receipt gate, `reads` with release-plan and release | delivery authority, consumer delivery | Salesforce-only examples labelled as examples | rollback, kept branch and final HEAD at handoff (rows P-h, P-r) |
| Improve parents (all reviewed stages) | review the producer's result against the stage's own focus | commit command and exact message path beside `improve-start`, producer-packet path, the stage's review focus | UI, skill, state paragraphs | content duplicated from the producer packet, deployment sentence outside release | pass-count rule: one `review-<n>.md` per pass |

Target sizes are **hypotheses to measure, not caps** (the repository rule is to raise a bound rather than trim guidance):
the plan packet 11-12 KB, a mid-loop stage 15-20 KB, get-next-work-item and operations under 12 KB, Improve parents about
25 KB. Phase 0 measures the current figure per section so each cut shows its saving.

## 6. Phases, order and gates

| Phase | Work | Gate before the next phase |
|---|---|---|
| 0 Baseline | extend the no-model walk with a per-section byte table (anatomy sections above) and a per-run packet-read tally; freeze today's packets of checkers-1 and battleship-1 as the comparison | table committed under `docs/experiments/`; baseline runs exist in Run Review |
| 1 Observed-harm fixes (review rows 1-13) | one-sentence, template and small script changes; each with a fail-first test through the real refusal route (the named exit is submitted through the real gate) | tests green; one Checkers/Sonnet run shows the refused classes gone; **release A** |
| 2 Anatomy | split `render()` out of `shiploop_navigator.py` into a packet module; the stage row gains `reads`, `writes`, `refs`, `blocks`; "Checked by" fully generated; head order; Improve negatives deleted | head test, gate-equality test, no-Improve-word test, completeness test (existing) green |
| 3 Symbols | roots, `shiploop ref`, constant locator table, existence-gated lines | a clear-context probe on Sonnet and Grok shows no read of a literal `RUN/...`; anchor test for every `refs` entry |
| 4 Re-cut by group | the table in section 5, group by group, plan packet and Improve parents first | each group: S-6 probe (below), size table, adversarial review |
| 5 Verification and **release B** | one no-model walk, S-6 probes, one Checkers/Sonnet and one Battleship/Grok run, not concurrent | compared with the frozen baselines in Run Review |

Two releases, not one: Phase 1 changes correctness (refusals) and Phase 2-4 change size; a single release would confound the
two in the comparison. Within each batch, no engine change mid-batch.

**S-6 probe** (existing recipe, README "A fresh context (S-6)"): clear the context after a stage boundary and inside a stage
on the stages most changed (plan, test-author, test-green, release-verify); pass if the model re-grounds from the packet
within a few calls and redoes no work. **Decision rule** for the live runs (eval-decision-priority): a material quality
difference decides; if equal, fewer tokens, then less time. Measured: refusals by stage (`fidelity.refusals.byStage`),
calls, packet reads, tokens, minutes, Improve changes.

## 7. Work streams and coordination

| Stream | Files | Notes |
|---|---|---|
| A fixes (Phase 1) | `shiploop_prompts.py`, `shiploop_navigator.py` (`_checked_line`, `_stage_gates`, template builder), `shiploop_item_scope.py`, `shiploop_test_loop.py`, `shiploop_knowledge_home.py` | rows are independent; one worktree per three rows |
| B anatomy and symbols (Phases 2-3) | new packet module, `shiploop_stage_spec.py`, `shiploop` CLI verb `ref`, `references/*.md` anchors | foundation; sequential |
| C re-cut (Phase 4) | `DUTIES`, per-stage `refs`/`blocks`, `behavioral-requirements.md` (the lifecycle text that today lives only in the prompt) | after B |

Conflicts to resolve first: the canonical checkout has uncommitted edits to `shiploop_navigator.py`, `shiploop_protocol.py`,
`shiploop_store.py`, `shiploop` and `state-files.md` (the script-state audit work, another session), and a commit and
spec-lifecycle plan is in progress that adds text to Improve and delivery commit packets. Base on `origin/main`
after those land, or agree an order with those sessions; do the renderer split before either adds more text to
`render()`. Every skill change carries a note `changes/shiploop/<slug>.md` (minor for Phase 2-4, patch for Phase 1).

## 8. Risks

| Risk | Mitigation |
|---|---|
| a cut removes grounding a cleared model needs (S-6) | each cut is a within-packet duplicate, irrelevant text or an explanation replaced by an obligation plus resolvable reference; S-6 probes at boundary and inside a stage; revert the group on redone work |
| unexpanded roots in tool calls | commands stay literal; probe on both hosts; fall back to absolute paths in the head only |
| generated "Checked by" drifts from the gate | one table feeds both; the existing route tests pair each named fault with its refusal |
| references moved but model never opens them | the checklist names the artifact each reference produces, so the Improve child sees the missing artifact |
| size drops but quality does not move | that is acceptable by the decision rule (tokens and time are tie-breakers), and the refusal counts are the quality signal |

## 9. Decisions for the owner

1. Roots as aliases (recommended; saves the most) or absolute paths kept and only blocks gated.
2. Keep the verbatim request in inner-stage packets, or reach it through the work-item context (recommended: keep in planning stages only; probe inner stages).
3. Two releases (recommended) or one.
4. The additive `surfaces` field on discovery and spec results, so the interaction block can be gated.
5. Order against the script-state audit and the commit/spec-lifecycle plan.

Unknowns the work resolves: whether the unread 90% changes any result (no run varied it); Grok packet-read behaviour
(no `toolUse.packets`); brownfield discovery text (all runs are greenfield); the `improve-bind` packet (overwritten by
`improve-start`, never reviewed): save it under a distinct name in Phase 0 so it can be reviewed.
