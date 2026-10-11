# ShipLoop packet review, 2026-10-10

Owner question: is each packet that the Run Review draft links to **accurate**, **grounded**, and **necessary and sufficient**?
And specifically: the plan packet is too long and not conclusive; keep it compact, grounded in references that can be
looked up.

Status: **findings, not yet implemented.** Nothing in `skills/` changed. Raw reports: `docs/experiments/packet-review-20261010/`
(six read-only reviewers, one per stage group; each read the real packets of checkers-1, battleship-1 and s6-after-spec
plus older runs, the engine source and SPEC S-1..S-15). Counts below are the reviewers', not re-measured by me.

## Verdict

| Question | Answer |
|---|---|
| Accurate | Mostly. About 20 statements are wrong or stale (a gate omitted from "Checked by", a sentence about another stage, a path that is never created). None is fatal; five matched a refusal. |
| Grounded | Yes. Every anchor checked (52 + 38 + more) resolves; ids, paths, commands and callbacks match the CLI parser. The exceptions are optional paths the packet prints as sources (planning notebook, `SHIPLOOP.md`). |
| Necessary and sufficient | **Sufficient to pass, not lean, and thin in about ten places.** Every stage ended `done` in almost every run; the evidence of insufficiency is the refusals (below), not failures. Mean producer packet is 37.7 KB; 67% is frame shared with every stage; the model's own slice (head, callback, goal, done-when, template) is about 3.1 KB. |

How the packets are actually used (checkers-1): of 1.82 MB on disk the model read **3** packets whole (intake and one Improve
packet). It worked 43 of 46 visits from the printed head plus a `sed` of Goal-to-template or one grep. The head says "read the
full packet before acting"; it does not happen. Consequence: an obligation that is in neither the head nor Done-when is
usually unread, and any duty printed only at the tail is missed (the models grepped four times for "keeps these up to date",
"improve-commit", the binding line and `until_loop_ephemeral`). A cold resume (s6-after-spec) does read the whole 38 KB file.
Repeating run rules across packets is grounding under the main tenet (S-6) and is **not** counted as waste here; only
irrelevant content inside one packet is.

## Fix first: observed harm (refusals, contract breaks)

Each row names an observed failure. Order is by count of runs hit, then by breach of a SPEC clause.

| # | Stage | Defect | Evidence | Fix |
|---|---|---|---|---|
| 1 | release-verify | "Checked by" and Done-when omit the `outcome.md` gate (`_checked_line` returns early for `complete_runs`, so the `knowledge.CLOSES` gate is never printed) | refused in 4 runs, then a second refusal for its sections | append `_stage_gates` to the `complete_runs` text; add a Done-when line |
| 2 | system-test-author, release-plan | a `check` row must carry no ids or min_tests; the packet shows ids only on a focused row and does not say it | 4+ refusals in 4 runs (stage known for 1) | one sentence in both duties (`shiploop_prompts.py`, `normalise_commands` rule) |
| 3 | test-green, regression, static-checks | the receipt must be in `evidence_refs` (stated only at "Do step 3", about line 263 of 370); exit condition (one complete iteration after the last edit, all exit 0, nothing changed) is paraphrased; Start/Receipt/commands sit after Code craft | receipt refused 3x; status active 1x; "loop has not run" 1x; "not complete" 1x | prefill `evidence_refs` with the terminal packet path in the template; print exit and repeat conditions and the Start/Receipt lines directly under the callback |
| 4 | document, integrate | model commits undeclared docs itself; "ShipLoop commits declared paths, do not commit" and "commit the ones the product needs" contradict; the packet shows neither list | checkers-1 commit 365ab7f (user-authored); 2+ more runs quote it; breaks S-4/S-5 | script commits docs-class files in `item_scope.commit_item`; integrate prints "changed, declared / changed, undeclared" and one consistent sentence |
| 5 | system-test-author, system-test | "report blocked" contradicts the unattended rule (S-14: record an open item); person-only rule applies only if discovery says no route, not when the route fails at run time | both Grok BLOCKED runs (r1 TC-16 browser; v1230 `about:blank`) | open-item route in system-test-author; demote `blocked` to "nothing else can proceed"; extend system-test to "or the route fails" |
| 6 | step-plan | template carries a README example that real outputs copy | checkers-1 and battleship-1 both added README work nobody asked for; hello did not | neutral placeholders in the template |
| 7 | step-plan, test-spec | id contract inverted: step-plan asks for ids "of the test-spec cases" but test-spec runs after; test-spec never says to title cases with the declared ids; duty lists suites without `check`; test-spec never says where cases go | test-author refusals with ids-missing (below) | step-plan: "ids you will title the cases with (TC-n)"; test-spec: "title each case with the ids in the step plan's `test_commands`; one entry per case in `test-spec.md`: id, setup, action, independent oracle, RED, GREEN"; add `check` |
| 8 | test-author | packet prints no command list or ids; duty says "or a failing test" but a failing run must also show every id | 2 ids-missing refusals (r2-checkers-sonnet) | add a probe listing (commands, ids, min_tests, ID word rule) to `shiploop_test_loop`; reword |
| 9 | spec, test-strategy | the producer packet says the Improve child "checks against Done-when"; the child applies the planning review focus (concrete values, stand-ins, commands run once, dropped ids, unsourced claims) | Improve changed the spec in 9 of 9 Sonnet stage-mode runs, test-strategy in 6 of 9 | copy the review-focus bullets into both duties (S-6: the producer packet says how it is reviewed) |
| 10 | test-strategy | whole-word ID rule not stated although `shiploop_test_counts` enforces it; UI cases: either a browser case or a recorded unverified outcome is required but the packet allows both silently | Improve added "require TC ids in titles" in checkers-1; Sonnet decided "no browser needed" in 5 of 9 UI runs | add the ID word rule; state the either/or with owner and due stage |
| 11 | plan, prepare | assumption fields are exact (`check, consumer, reason`; extra keys refused; `consumer` a work-item id) but the packet does not say so; `plan.md` is required at the prepare close and no earlier packet says so; prepare lists five files as "this stage's" that were due earlier | assumption refused twice (r2-checkers-sonnet); prepare refused once | one sentence each; split the prepare file line into "written earlier, prepare refuses if missing" and "yours" |
| 12 | Improve (all stages) | the commit command and the exact commit-message path sit at about byte 30 K of 47 K, below `improve-start`; planning-stage Improve (release-plan) says "Improve may perform deployments" against S-3 | battleship-1 wrote the wrong file name and was refused; checkers-1 grepped for the command | move the commit paragraph beside `improve-start`; restrict the deployment sentence to the release stage |
| 13 | implement | on steps 2..N the progress snapshot lists implement as accepted-done while "Current: implement" | seen in 3 checkers-1 packets | render "in progress (k of N accepted)" |

## Then: information the model needs and does not get

| Stage | Missing | Fix |
|---|---|---|
| discovery | the investigation allowance has no size (default 15 active minutes, 64 host actions, 3 experiments); the notebook path is printed as a source but never created | name the numbers and the `#budget-stopping-and-convergence` anchor; "create it if a plan trigger applies" |
| research | duty says to list load-bearing assumptions in the decision note; no `STAGE_FILES` entry, no Done-when item, 0 of 3 results had a list | name the decision-note file; add a Done-when item |
| spec | output path and the "keep every R-id" rule are not in the head; "Checked by" omits the credential screen and dropped-R-id gate | add both to `packet_head` and `_stage_gates` |
| test-strategy | `discovery` not in `reads` although the duty says "consume the observed baseline"; "Last accepted" shows the pre-Improve summary (R-1..R-14, spec had R-15); `test-strategy.md` gate not named | add the read; append changed files and commit ids at `improve-complete`; name the gate |
| baseline | does not list the commands to run or the discovery baseline | print `stage_commands` and the discovery result path (checkers-1 accepted shell-loop error output as evidence) |
| implement | exit criteria C1..Cn are item-level and not printed; the report-level-per-criterion instruction was ignored in 4 of 4 and nothing checks it | print the criteria; step-scoped exit wording |
| verify | the criteria and the criterion-to-command tie are not printed; no routing for a failed confirmable criterion | print them; "product defect: fix and rerun; wrong criterion: revise" |
| integration-verify | "shared interfaces are checked" names no interfaces; two caps (3 attempts / 7 refused runs) for one outcome | add the step plan to `reads`; one rule |
| carry-forward | Done-when says "recorded outside run notes"; no destination named, no gate; `work_items` shape missing from the template | name `environment.md` or `outcome.md`; reuse replan's shape line |
| skill-assess, skill-validate | 24 packets of about 31 KB, 12 of 12 runs ended no-skill/N/A; script cannot skip validate after an N/A assess | add a structured `skill_change` field so the script records validate as N/A (S-5); default `skill_na` for small items |
| release-plan, release | delivery authority has no inline rule and no gate; who authorizes the return is not said; rollback recipes printed at release-plan and release-check but not at release where the return happens | two lines of authority text; print recipes at release |
| handoff | `reads` lacks release-plan and release, so no rollback, kept branch/worktree or final HEAD; still prints "After review and authorization" when the return is verified; "Checked by" omits the receipt gate | add reads and a duty line; branch on a verified return |

## Size and frame

Mean producer 37.7 KB: 67% frame, 33% stage-specific. Absolute paths are 23% of all packet bytes. The frame report estimates
**about 400 KB of 1.81 MB per run (22%)** can go without removing an obligation:

| Change | Per run |
|---|---|
| state run, worktree, work and plugin roots once ("Roots:"), commands stay literal | 227 KB (292 KB with exported variables) |
| gate the workspace/plan-return/review-return block (2.4-2.7 KB, 36 stages) to release-plan, release-check, release, handoff and blocked/paused packets | 92 KB |
| one constant locator table after the roots; existence-gate the two "if present" lines | 37 + 15 KB |
| drop the duplicate tail callback | 16 KB |
| gate the identity and runtime-entry paragraphs to preparation and release | 22 KB |
| optional and riskier (S-6): snapshot in the file reduced to Where and Next | 60 KB |

Other byte findings, all gating by a script fact: Code craft (3.7 KB) in test-red, document and integrate; the Backchain
and Until Loop block (2.9 to 5.2 KB) in product-acceptance, carry-forward with an empty queue (13 of 14 runs) and spec;
the interaction-design and lifecycle block (3.1 KB) in discovery, research, spec, plan and step-plan for a one-page game;
the Improve packets repeat 40 to 44% of their producer packet (about 22 KB), with several UI/skill/state paragraphs that do
not fit the stage. A reviewer has no pointer to the producer packet; add one line.

Order of the frame: for 24 of 46 packets the first screen is a delegation preamble and ends before the first Done-when
bullet; the three inline Improve packets show only the preamble. Put stage line, Goal, Done-when bullets, callback first and
fold the preamble to one line.

## The plan packet (55 KB to about 12 KB)

Measured on checkers-1 (1.26.0, 55,362 B; the owner's 1.22.0 packet is 55,225 B, so four releases changed nothing in size).
About 17 KB is unique to plan, about 22 KB is in nearly every packet. The owner's pasted packet matches.

| Current block | Bytes |
|---|---|
| Plan duty (core 2.9 K, reconciliation, namespaces, work items 5.8 K) | 8.6 K |
| COMMON stage guidance (same in every stage) | 6.5 K |
| Planning sources, experiments, last accepted, test-strategy source | 4.8 K |
| Backchain native route and Until Loop budget (`backchain_passes` only) | 4.5 K |
| 14 policy locators + 12 guidance locators + state/CLI locators | 7.5 K |
| Interaction design + state lifecycle | 3.1 K |
| Workspace/return text | 2.6 K |
| Status snapshot, block, narrative | 2.4 K |
| Result template and outcome shapes | 2.0 K |
| Progress rules | 2.5 K |
| The rest (request 1.4 K, head 1.9 K, context 1.6 K, handoffs 1.8 K, tail 1.4 K) | 8.5 K |

**Proposed shape** (what a cleared context needs, and nothing else):

| Block | Target |
|---|---|
| Head: stage, revision, goal, three Done-when lines, exact callback, result path, "Roots: RUN, WT, SK" | 1.8 K |
| Inputs as ids (intake, discovery, research, spec, test-strategy results; `docs/shiploop/{spec,test-strategy,environment}.md`) and the original request verbatim | 2.7 K |
| Result contract with one line per refusal rule: exact assumption fields; `consumer` a queue work-item id; `work_items` the complete ordered queue (`{id,title,context}`, id like `W1`); headline at most 100 characters and not a placeholder; `evidence_refs` absolute and existing | 1.7 K |
| Eight-item checklist, one obligation each, each with a `reference#section` locator that names the artifact it produces (for example "Namespace and data map in `plan.md`") | 2.8 K |
| Gated stubs: UI (one line plus `behavioral-requirements.md#ui-specific-planning`), Backchain (three lines plus `shiploop backchain-start`, which prints the 4.5 K contract and the 9,216-byte budget when asked), workspace (absent at plan) | 0.3-0.9 K |
| Condensed COMMON (unattended rule, blocked shape, scratch, "open a locator only when its case applies") | 1.3 K |
| Tail: Improve line, pause, halt, recovery, one-line status | 1.0 K |
| **Total** | **about 11-12 K** |

Checklist: (1) every R-id and criterion has one owning work item; (2) supplier-to-consumer dependencies with ready and
done conditions per item (`backchain-planning.md#dependency-audit`); (3) environment and architecture: where code and data
live, namespaces, data map, module format and test seam per item (`coding-practices.md#namespaces-and-placement`,
`#schema-and-storage`); (4) state ownership and lifecycle, lightest channel first (five lines stay in the packet because the
text exists in no reference today; add it to `behavioral-requirements.md`); (5) test-facility prerequisites as their own
work item (`repeatable-test-suites.md#reuse-and-define-test-facilities`) and the initial baseline; (6) delivery authority and
environment work; (7) carry the test-strategy source and TC ids into each item's `context`; (8) write `plan.md` and
`README.md`, and say `plan.md` is required at the prepare close.

**Must not move to a reference** (a refusal depends on it): assumption exact fields and `consumer`; the `work_items` shape;
the headline and `evidence_refs` rules; `plan.md` and `README.md` written; credential screening of `docs/shiploop`; no
dropped requirement id; "omitting `work_items` is refused" in the plan Improve packet; the 9,216-byte start-contract budget
and the `Backchain passes: one` marker (must appear in the `backchain-start` output).

Where: `shiploop_prompts.py` (`prompt()`, `COMMON`, `DUTIES["plan"]`, `INTERACTION_DESIGN`, `WORK_ITEM_CONTEXT`,
`_PLANNING_HANDOFF`, `TEST_FACILITY_HANDOFF`, `_backchain_guidance`, `PROGRESS_REPORTING`), `shiploop_navigator.py`
(locator and workspace builders, `_checked_line`, `_stage_gates`, the template sample builder, a path-rendering helper),
`shiploop_knowledge_home.stage_lines`. The interaction block can be gated only if discovery or spec results carry an optional
`surfaces: ui|network|shared-state` field; the script does not know that structurally today.

Main-tenet check: after a clear the compact packet still has the goal, Done-when, request, input ids, the exact result
contract, the decision checklist, and the recovery and callback commands. Risk: a model skips a locator it needs. Mitigation:
each checklist item names the artifact the locator produces, so the Improve child sees the missing artifact.

## Other observations

- The model wraps `complete` in a helper script 33 times; defaulting `--result` to the printed inbox path would remove it (S-5).
- Two reading rules conflict: the head says "never a whole reference file, do not re-read skill cards", loop stages say
  "read the Until Loop card in full once per context", Improve says "whole-skill-subcall section". Pick one.
- Commit ownership is worded three ways (30 packets, 4 packets, integrate). One constant (S-12).
- `choices.skill_required` (accepted at document) has no reader that the reviewer found: a candidate for the one-supported-version clean-up.
- Examples that are single-platform (Salesforce in release-plan and release-check; Node `--verbose` and TAP in the count rule): label as examples (S-8).

## Not answerable from the exports

- Whether the unread 90% would change a result: no run varied it. Runs show it was skipped and passed, not that it was unnecessary.
- Grok packet reads (no `toolUse.packets`); whether a brownfield repo makes the unread discovery text insufficient (all 14 runs are greenfield).
- The `improve-bind` packet is overwritten by `improve-start` (same file name) and the Improve child's own packets are written by the runtime; neither could be reviewed.
- Stage of the 4 `check command ... exit code` refusals in 3 runs and 4 older credential refusals (`callback-attempts/` empty; old run docs carry no stage).

## Recommended order

1. Rows 1, 2, 3, 12 (one-sentence or template changes; each removes an observed refusal class).
2. Rows 4, 5, 9 (script changes that restore S-4/S-5/S-14 and the review contract).
3. Rows 6, 7, 8, 10, 11 (planning contracts), then the information table.
4. The plan packet redesign and the frame changes together, since they share the path-rendering helper and the gating
   helpers, with the shiploop-delegation test and a head test ("the first screen carries stage, goal, Done-when, callback,
   keeps-up-to-date line") as the gate.

Any prompt change here follows the repository rule: a verbose commit message with the learning, its evidence and the
related commits; the journal entry in `docs/shiploop-run-review-journal.md` points here.
