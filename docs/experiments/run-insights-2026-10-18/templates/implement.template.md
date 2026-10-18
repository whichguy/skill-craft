---
template: implement
version: 1
consumer: The packet's reader is the model that builds one step of one work item, in a fresh context, from this print alone, once per step (inline route). The result's reader is ShipLoop's implement gate (loop receipt, lint gate, step Proof) at `complete`, then the step's Improve review, which receives the same Step and Anchors blocks.
print_budget: 19500
flags:
| flag | source |
|---|---|
| loop_started | file exists: RUN/loops/<action>-terminal.json |
| code_step | the step's paths (else the item's) hold a code path (item_scope.behavioural); prints Code craft (titles; owner decision T-D1) |
| revisit | this step ID has an earlier implement result in this item (D3) |
slots:
| slot | kind | source | bound | over | pool |
|---|---|---|---|---|---|
| stage | scalar | const "implement" | 12 | refuse | - |
| revision | scalar | state.revision | 6 | refuse | - |
| action | scalar | state.current_action.id | 40 | refuse | - |
| next_command | cmd | cli next --run-dir=RUN | cli+run+24 | refuse | - |
| pause_command | cmd | cli pause --run-dir=RUN '--reason=<who asked and why>' | cli+run+56 | refuse | - |
| callback_command | cmd | cli complete --run-dir=RUN --action=<action> | cli+run+74 | refuse | - |
| lint_command | cmd | cli lint --run-dir=RUN --action=<action> | cli+run+70 | refuse | - |
| keepalive_marker | scalar | "SHIPLOOP-RUN run=<run_id> rev=<revision> dir=<RUN>" | run+65 | refuse | - |
| loop_start_command | cmd | until-loop start --receipt <receipt> < <contract> | root+run+run+208 | refuse | - |
| receipt_abs | scalar | RUN/loops/<action>-terminal.json, absolute (evidence_refs entries must be absolute) | run+57 | refuse | - |
| packet_abs | scalar | RUN/packets/<action>.md, absolute (the loop runtime reprints the Work line without this packet's symbols) | run+48 | refuse | - |
| progress | block | narrative partial at a milestone, else the one-line Where/Next status | 1100 | refuse | - |
| item_id | scalar | state.work_items[work_index].id | 12 | refuse | - |
| step_id | scalar | result:step-plan.steps[current].id | 8 | refuse | - |
| step_n | scalar | position of the current step, from 1 | 4 | refuse | - |
| step_total | scalar | len(result:step-plan.steps) | 4 | refuse | - |
| step_task | include | result:step-plan.steps[current].task (step-plan's gate refuses a task over this bound) | 1200 | refuse | - |
| step_criteria | block | result:step-plan.criteria[id in step.criteria], row criterion | 2000 | refuse | - |
| step_criteria_ids | scalar | result:step-plan.steps[current].criteria joined ", " | 80 | refuse | - |
| step_check | include | result:step-plan.steps[current].check (step-plan's gate refuses a check over this bound: a longer probe goes in a file the check runs) | 1000 | refuse | - |
| worktree | scalar | WORKTREE (absolute) | run+5 | refuse | - |
| step_deps | block | result:step-plan.steps[current].deps with each accepted result locator, row dep; "none" when empty | 300 | refuse | - |
| step_skills | block | result:step-plan.steps[current].skills, row skill; "none" when empty | 400 | refuse | - |
| accepted_steps | block | history: accepted implement results of earlier steps of this item, row accepted (headline only) | 600 | excerpt | steps |
| later_steps | block | result:step-plan.steps[after current], row later (ID and first sentence of the task, cut at 120) | 600 | excerpt | steps |
| plan_result | scalar | RUN/results/<step-plan action>.md | 120 | refuse | - |
| step_cases | block | result:test-spec.test_cases[criterion in step.criteria], row case (ID and procedure locator, no oracle) | 500 | excerpt | steps |
| step_requirements | include | home:spec.md#R-<n> for each R-<n> named by the step's criteria texts (else the item's follows): heading and its first two sentences (300 characters each), no Acceptance bullets | 2600 | excerpt | anchors |
| item_decisions | include | home:architecture.md#AD-<n> for each AD-<n> in the item's follows: heading and its Choice sentence (200 characters each) | 1600 | excerpt | anchors |
| arch_structure | include | home:architecture.md#Structure | 1000 | excerpt | anchors |
| env_commands | include | home:environment.md#Commands, code only: each command with its one-line label | 1000 | excerpt | anchors |
| step_concerns | block | result:step-plan.concerns[steps contains step_id], row concern | 600 | excerpt | anchors |
| step_cards | block | card locators selected for the step's concerns (A2), row card; first section by value when a card is selected | 1500 | excerpt | anchors |
| revisit_block | block | previous implement result for this step ID, and the revise evidence that touched it (D3) | 1000 | excerpt | steps |
| fix_attempts | scalar | stage_spec.GENUINE_FIX_ATTEMPTS | 2 | refuse | - |
| revises_left | scalar | "<MAX_REVISES - used> of <MAX_REVISES>" | 8 | refuse | - |
| run_dir | scalar | RUN (absolute) | run | refuse | - |
| guides_dir | scalar | GUIDES (absolute) | root+30 | refuse | - |
| source_results | block | RUN/results/<action>.md of step-plan, test-spec, validate-existing, row locator | 400 | refuse | - |
| last_accepted | block | history[-1]: stage, outcome, action | 160 | refuse | - |
pools:
| pool | size |
|---|---|
| anchors | rest>=1000 |
| steps | 900 |
rows:
| row | format |
|---|---|
| criterion | `  {id}: {text}` |
| dep | `{id} (accepted: RUN/results/{action}.md)` |
| skill | `{name}: {why} ({locator})` |
| accepted | `- {id}: {headline}` |
| later | `{id} {task_first_sentence}` |
| case | `{id} (procedure: HOME/architecture.md ## Procedures ### {id})` |
| concern | `{concern} ({check})` |
| card | `{locator}` |
| locator | `{label}: {path}` |
result:
| key | type | rule (gate id) |
|---|---|---|
| outcome | enum done, blocked, revise | im-outcome |
| headline | string <= 100 | common-headline |
| summary | string; says per listed skill whether it was used | common-summary |
| criterion_evidence | list of {criterion, ran_or_inspected, observed, output} | im-evidence (fix plan 3.3) |
| not_covered | list of {behaviour, reason}, may be empty | im-not-covered |
| lint_waivers | list of {id, reason}, optional | lint-gate |
| evidence_refs | list of absolute paths or https URLs; holds the receipt | common-evidence, loop-receipt |
---
{{> frame}}
Goal: Implement step {{step_id}} ({{step_n}} of {{step_total}}) of work item {{item_id}} in WORKTREE so its criteria hold; ShipLoop runs its Proof at done.
Done when: every exit condition in the Until Loop argument at the end of this packet holds. Checked by: the Gates below, at `complete`. Do the work inside that Until Loop; everything before it is its material.

== Step {{step_id}}: the only work for this packet ==
Task: {{step_task}}
Serves (the step plan's words):
{{step_criteria}}
Proof (ShipLoop runs it at done; it must exit 0; run it the same way):
  cd {{worktree}} && {{step_check}}
Depends on: {{step_deps}} · Skills (use each; the summary says whether you did): {{step_skills}}
Accepted earlier steps: {{accepted_steps}}
Later steps (ShipLoop issues each after this one; do not start them): {{later_steps}}
Test cases of these criteria (the test stage writes them later): {{step_cases}}
Files: ShipLoop commits the item's declared paths ({{plan_result}}); a file this step needs outside them is a revise.
{{#if revisit}}Revisit of {{step_id}}:
{{revisit_block}}{{/if}}

== Anchors, quoted by value (a conflict with them is a revise, never a silent choice) ==
Requirements the criteria serve (HOME/spec.md; their Acceptance bullets belong to the test stage):
{{step_requirements}}
Decisions the item follows (HOME/architecture.md ## Decisions):
{{item_decisions}}
Concerns this step carries (step plan): {{step_concerns}} · Cards: {{step_cards}}
HOME/architecture.md ## Structure: {{arch_structure}}
HOME/environment.md ## Commands (commands only):
{{env_commands}}

{{progress}}

== Method, in order ==
<!-- DUTIES['implement'] 2 and fix plan 3.2 Method 1-2, shortened; B4 -->
1. Read the Step and Anchors; they are complete for this step. Inspect what the step changes, what depends on it and what the platform already provides. Before relying on a platform behaviour a design choice rests on, check it with a one-line probe in RUN/scratch or its primary documentation.
<!-- _IMPLEMENT_SCOPE_INLINE -->
2. Build only this step: meet its criteria, break none of the item's other requirements, write no tests, start no later step, leave unrelated code as is. Existing tests, check scripts, fixtures and thresholds are checks: change one only when a criterion says so.
<!-- _IMPLEMENT_CHECK_INLINE + DUTIES['implement'] 3 tail -->
3. After each meaningful change run the Proof and `{{lint_command}}`; write each exit code in RUN/notes/{{action}}.md. Fix a failure by changing the work, never the Proof or what it expects; a lint finding that must stay goes in `lint_waivers`. Install or fetch nothing.
<!-- DUTIES['implement'] 4 and fix plan 3.2 Evidence / Write back, shortened -->
4. Record `criterion_evidence` (per criterion: what ran, what it showed, where the output is; a description of the change is not evidence) and `not_covered` (each added behaviour no test case covers). A new structural decision that fits every R-<n> and AD-<n> is the next AD-<n> under ## Decisions; a change to an R-<n> or AD-<n> is a revise. A command that now works goes under ## Commands.
<!-- DUTIES['implement'] 6; item 5 (Services) folded into the Anchors and Code craft 11 -->
5. Report revise, naming the criterion or command, when a criterion contradicts another criterion, the item or a protected file; when confirming it needs an absent tool, access or authority; when it would exceed the item; when the change invalidates a recorded command; or when the same check still fails after {{fix_attempts}} genuine fix attempts. Report blocked only when a person, an access grant or an outside dependency must resolve it.
{{#if code_step}}{{> code-craft-titles}}{{/if}}

== Gates beyond the exit conditions (ShipLoop refuses at `complete`; `--check-only` shows the first) ==
- the Proof is rerun by ShipLoop before it imports an Improve review that changed the step  <!-- gate: step-proof -->
- a placeholder left in the form; an evidence_refs entry that is neither an existing absolute path nor an https URL  <!-- gate: common-placeholder, common-evidence -->

{{> rules}}

== Result form (write it to the Callback's result file; ShipLoop parses the JSON block) ==
```shiploop-state
{
  "outcome": "done",
  "headline": "<under 100 characters: what this step established>",
  "summary": "<decisions and defaults only this result records; per listed skill, used or why not>",
  "criterion_evidence": [{"criterion": "C1", "ran_or_inspected": "<command or file>", "observed": "<what it showed>", "output": "<locator>"}],
  "not_covered": [],
  "evidence_refs": ["{{receipt_abs}}"]
}
```
Allowed outcomes: done | blocked | revise ({{revises_left}} left for this item: it returns to step-plan with this result as evidence). revise: {"outcome": "revise", "summary": "<what in the step plan or test spec is wrong, with the evidence>"}
{{> result-rules}}

{{> loop-invoke}}
----- BEGIN until-loop ARGUMENT -----
Work: Implement step {{step_id}} of work item {{item_id}} by the Method in {{packet_abs}}, anchored in its criteria and the quoted requirements and decisions, until each criterion assigned to this step holds and none of the item's other requirements is broken. Write no tests and start no later step.
Exit when ALL of these hold:
1. each criterion assigned to this step holds and none of the others is broken, shown by a command or file after the last edit, and no later step's work is in the change (assigned: {{step_criteria_ids}})
2. after the last edit, the step's Proof exited 0
3. after the last edit, the lint gate reports no unwaived new finding on a line this step changed
4. the result gives criterion_evidence for each assigned criterion, lists each behaviour no test case covers (or none), and says whether each step skill was used
Repeat while an exit condition is unmet and a justified fix remains; there is no iteration limit. Stop blocked and report revise, with the blocker and the attempts made, when no justified next action remains or Method 5 applies. Never stop cancelled: a user's stop is the packet's Pause command.
Contract: RUN/loops/{{action}}-contract.json
Receipt: RUN/loops/{{action}}-terminal.json
----- END until-loop ARGUMENT -----
{{> loop-result}}

<!-- appendix: file only -->
{{> appendix}}
