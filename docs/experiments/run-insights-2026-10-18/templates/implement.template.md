---
template: implement
version: 2
consumer: The packet's reader is the model that builds one step of one work item, in a fresh context, from this print alone, once per step (inline route; the ask-agent route builds every step in one action and keeps today's packet until its own template). The result's reader is ShipLoop's implement gate (loop receipt, lint gate, step Proof, the evidence and hand-off fields) at `complete`, then ShipLoop's step commit, then the step's Improve review, which receives the same Step and Anchors blocks.
print_budget: 19500
requires: criterion-evidence gate (`criterion_evidence` in _RESULT_KEYS; fix plan 3.3) · N2 step commits (learned, decisions, learned_from; the step commit; recent_commits) · N5 outcome names (send-back) · T-D2 producer bounds (step-plan: task 700, criteria 1200, check 600) · A1 concern rows (step_concerns) · A2 card selection (step_cards) · A0 port: the eight considerations and the implement-record gate, one name and shape for criterion evidence (this form follows fix plan 3.3; the branch's `evidence` has 6 fields) · N3 write-back at implement (an acceptance line in spec.md, marked with the step; the A0 guidance's "never edit spec.md here" yields to N3) · D3 per-step revisit · N5 awaiting kinds answer, present, service · decision 19 KNOWLEDGE symbol (reference_paths, symbolic, expand_result_roots, excerpt locators; HOME retired) · placeholder registry read from this form (navigator._placeholders) · loops Work cites the template's Method items (_duty_items counts them) · engine E3/E4 (plan 8.5) · lands with: obligation ledger rows, head-order tests, packet_view and counters repointed in the same commit
flags:
| flag | source |
|---|---|
| loop_started | file exists: RUN/loops/<action>-terminal.json |
| code_step | the step's paths (else the item's) hold a code path (item_scope.behavioural); prints the Code craft titles (decision 18) |
| revisit | this step ID has an earlier implement result in this item (D3) |
| worktree_run | the run has an isolated product checkout (execution mode navigator-worktree) |
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
| packet_abs | scalar | RUN/packets/<action>.md, absolute | run+48 | refuse | - |
| inbox_abs | scalar | RUN/inbox/<action>.md, absolute | run+46 | refuse | - |
| loop_start_command | cmd | until-loop start --receipt <receipt> < <contract> | root+run+run+208 | refuse | - |
| loop_argument | block | loops.contract(): the ARGUMENT block as loops.invoke_lines prints it (Work, Exit, Repeat, Contract, Receipt); ShipLoop-built from stage_spec, loops and the step's anchors | 3000 | refuse | - |
| receipt_abs | scalar | RUN/loops/<action>-terminal.json, absolute | run+57 | refuse | - |
| progress | block | narrative partial at a milestone, else the one-line Where/Next status | 900 | refuse | - |
| item_id | scalar | state.work_items[work_index].id | 12 | refuse | - |
| step_id | scalar | result:step-plan.steps[current].id | 8 | refuse | - |
| step_n | scalar | position of the current step, from 1 | 4 | refuse | - |
| step_total | scalar | len(result:step-plan.steps) | 4 | refuse | - |
| step_task | include | result:step-plan.steps[current].task (producer bound: step-plan gate, T-D2) | 700 | refuse | - |
| step_criteria | block | result:step-plan.criteria[id in step.criteria], row criterion (producer bound: step-plan gate, T-D2) | 1200 | refuse | - |
| step_check | include | result:step-plan.steps[current].check (producer bound: step-plan gate, T-D2; a longer probe is a script the check runs) | 600 | refuse | - |
| worktree | scalar | WORKTREE (absolute) | run+5 | refuse | - |
| step_deps | block | result:step-plan.steps[current].deps, each with its accepted result, row dep; "none" when empty | 300 | refuse | - |
| step_skills | block | result:step-plan.steps[current].skills, row skill; "none" when empty | 400 | refuse | - |
| accepted_steps | block | history: accepted implement results of earlier steps of this item with ShipLoop's step commit, row accepted (N2) | 600 | excerpt | - |
| later_steps | block | result:step-plan.steps[after current], row later (ID, its criteria, the task's first sentence cut at 160) | 800 | excerpt | - |
| plan_result | scalar | RUN/results/<step-plan action>.md | 120 | refuse | - |
| test_spec_result | scalar | RUN/results/<test-spec action>.md | 120 | refuse | - |
| step_cases | block | result:test-spec.test_cases[criterion in step.criteria], row case | 500 | excerpt | - |
| recent_commits | block | git log from this step's starting HEAD: the last two commits that are not ShipLoop bookkeeping (its knowledge-record and leftover commits); step and review commits count; subject and its Key learnings line, row commit (N2) | 900 | excerpt | - |
| step_requirements | include | home:spec.md#R-<n> for each R-<n> the step's criteria name (else the item's follows): heading and its first two sentences, 300 characters each | 2400 | excerpt | anchors |
| anchor_ids | scalar | every R-<n> the step's criteria name and every AD-<n> the item follows, so an excerpt or pointer below still names them all | 200 | refuse | - |
| item_other_reqs | scalar | the item's follows R-<n> not in step_requirements, joined ", ", or "no other requirement" | 200 | refuse | - |
| item_decisions | include | home:architecture.md#AD-<n> for each AD-<n> in the item's follows: heading and its Choice sentence, 200 characters each | 1600 | excerpt | anchors |
| arch_structure | include | home:architecture.md#Structure | 1000 | excerpt | anchors |
| env_commands | include | home:environment.md#Commands, code only: each command with its one-line label | 1000 | excerpt | anchors |
| step_concerns | block | result:step-plan.concerns[steps contains step_id], row concern (A1) | 600 | excerpt | anchors |
| step_cards | block | card locators selected for the step's concerns, row card (A2) | 600 | excerpt | anchors |
| revisit_block | block | D3: this step's previous result (locator, headline) and its step commit (N2), the send-back result (locator, summary cut at 600 as REVISIT_SUMMARY) and the upstream-change line | 1000 | excerpt | - |
| send_back_target | scalar | stage_spec send-back target for implement: "step-plan" | 20 | refuse | - |
| send_backs_left | scalar | "<MAX_REVISES - used> of <MAX_REVISES>" | 8 | refuse | - |
| done_next | scalar | the navigator's successor for this done step | 120 | refuse | - |
| stop_outcomes | scalar | stage_spec outcomes other than done, N5 names, joined " or " (implement: "blocked or send-back") | 40 | refuse | - |
| run_dir | scalar | RUN (absolute) | run | refuse | - |
| guides_dir | scalar | GUIDES (absolute) | root+30 | refuse | - |
| source_results | block | RUN/results/<action>.md of step-plan, test-spec, validate-existing, row locator | 400 | refuse | - |
| last_accepted | block | history[-1]: stage, outcome, action | 160 | refuse | - |
pools:
| pool | size |
|---|---|
| anchors | rest>=1000 |
rows:
| row | format |
|---|---|
| criterion | `  {id}: {text}` |
| dep | `{id} (accepted: RUN/results/{action}.md)` |
| skill | `{name}: {why} ({locator})` |
| accepted | `- {id} {commit}: {headline}` |
| later | `{id} ({criteria}): {task_first_sentence}` |
| case | `{id} ({criterion}, {requirement})` |
| commit | `- {short} {subject}: {learning}` |
| concern | `{concern} ({check})` |
| card | `{locator}` |
| locator | `{label}: {path}` |
gates:
| gate | refusal (code) | anchor in the print |
|---|---|---|
| loop-receipt | loops.check_terminal / check_loop_packet: complete reports done | keep the Receipt in evidence_refs and run the Callback |
| loop-stop | check_loop_packet: a stopped loop reports blocked or send-back | a stopped one blocked or send-back |
| loop-route | check_loop_packet: no run of this contract, or an active receipt | run the command the refusal names |
| lint-gate | navigator._lint_gate: an unwaived new finding on a changed line | an unwaived new finding on a line this step changed |
| lint-autofix | lint.gate: refused once after an auto-fix | once after it auto-fixes files |
| lint-waivers | _normalise_lint_waivers: exactly id and reason, done only | {"id", "reason"} each |
| step-proof | _step_proof_gate / test_loop.step_proof: exit, timeout, no tests | it must exit 0, and a runner that reports 0 tests fails it |
| scope | item_scope.scope_refusal | outside the item's declared paths |
| result-keys | navigator._canonical_result: unsupported fields | a key that neither the form nor the Method names |
| assumptions | navigator._canonical_result: assumptions not allowed at implement | this stage's form has none |
| placeholder | navigator._placeholders (exact strings this form prints) | replace every <...> placeholder |
| evidence | _check_submitted_evidence (absolute paths), expand_result_roots (unknown leading root) | an evidence_refs path that does not exist |
| home-ids | knowledge.check: an R-<n> or AD-<n> lost | loses an R-<n> or AD-<n> |
| not-covered | _handoff_gate: not_covered rows {behaviour, reason} or [] | "not_covered": [{"behaviour" |
| criterion-evidence | implement-record gate (A0; fix plan 3.3) | Answer each consideration in `considerations` |
| n2-fields | N2: learned and decisions required | "learned" |
| send-back-budget | _apply_result: no send-back left | with none left for this item |
| im-outcome | the outcome enum (N5) | - send-back: |
result:
| key | type | rule (gate id) |
|---|---|---|
| outcome | enum done, blocked, send-back | im-outcome |
| headline | string <= 100 | common-headline |
| summary | string; says per listed skill whether it was used | common-summary |
| considerations | map of consideration -> handling and anchor, or why untouched | criterion-evidence |
| criterion_evidence | list of {criterion, case, ran_or_inspected, observed, output, establishes, limits} | criterion-evidence |
| not_covered | list of {behaviour, reason}, may be empty | not-covered |
| learned | list of lines, or ["none"] | n2-fields |
| decisions | list of lines, or ["none"] | n2-fields |
| learned_from | list of {commit, contribution}, optional; each commit reachable from HEAD | n2-fields |
| lint_waivers | list of {id, reason}, optional | lint-waivers |
| evidence_refs | list of paths or https URLs; holds the receipt | evidence, loop-receipt |
---
{{> frame}}
Goal: Implement step {{step_id}} ({{step_n}} of {{step_total}}) of work item {{item_id}} in WORKTREE so its criteria hold; ShipLoop runs its Proof at done, then commits the step.
Done when: every exit condition in the Until Loop argument at the end of this packet holds. Checked by: the Gates below, at `complete`. Start that Until Loop before any work; everything before it is its material.

== Step {{step_id}}: the only work for this packet ==
Task: {{step_task}}
Serves (the step plan's words):
{{step_criteria}}
Proof (ShipLoop runs it at done with /bin/sh for at most 600 s; it must exit 0, and a runner that reports 0 tests fails it; run it the same way):
  cd {{worktree}} && {{step_check}}
Depends on: {{step_deps}} · Skills (use each; the summary says whether you did): {{step_skills}}
Accepted earlier steps (step, its commit, headline): {{accepted_steps}}
Later steps (ShipLoop issues each after this one; keep their work out of this change): {{later_steps}}
Test cases of these criteria (the test stage writes them; every case of the item is in {{test_spec_result}}): {{step_cases}}
Files: when it accepts done, ShipLoop commits this step's changes within the item's declared paths ({{plan_result}}); commit nothing yourself. A file this step needs outside those paths is a send-back.
{{#if revisit}}Revisit of {{step_id}} (amend that result; keep what this evidence does not touch):
{{revisit_block}}
{{/if}}Recent commits (the last two that are not ShipLoop bookkeeping; what earlier steps learned):
{{recent_commits}}

== Anchors, quoted by value (excerpts: open the named section when the work depends on its exact words; a conflict with them is a send-back, never a silent choice) ==
Anchored in {{anchor_ids}}. Requirements the criteria serve (KNOWLEDGE/spec.md, first sentences; the item also follows {{item_other_reqs}}, which must stay unbroken):
{{step_requirements}}
Decisions the item follows (KNOWLEDGE/architecture.md ## Decisions, choice lines):
{{item_decisions}}
Concerns this step carries (step plan): {{step_concerns}} · Cards: {{step_cards}}
KNOWLEDGE/architecture.md ## Structure: {{arch_structure}}
KNOWLEDGE/environment.md ## Commands (commands only):
{{env_commands}}

{{progress}}

== Method, in order ==
<!-- DUTIES['implement'] 2 and fix plan 3.2 Method 1-2; "they are complete" removed (review IM-06) -->
1. Read the Step and Anchors. Inspect what the step changes, what depends on it and what the platform already provides. Before relying on a platform behaviour a design choice rests on, check it with a one-line probe in RUN/scratch or its primary documentation.
<!-- _IMPLEMENT_SCOPE_INLINE; "start no later step" is said once, in the Step block (review IM-21) -->
2. Build only this step: meet its criteria, break none of the item's other requirements, write no tests, leave unrelated code as is. Existing tests, check scripts, fixtures and thresholds are checks: change one only when a criterion says so.
<!-- _IMPLEMENT_CHECK_INLINE + DUTIES['implement'] 3 tail; the lint_waivers shape printed (review IM gate map) -->
3. After each meaningful change run the Proof and `{{lint_command}}`; write each exit code in RUN/notes/{{action}}.md. Fix a failure by changing the work, never the Proof or what it expects. A lint finding that must stay goes in `lint_waivers` ({"id", "reason"} each). Install or fetch nothing.
<!-- DUTIES['implement'] 4, fix plan 3.3 evidence, N2 fields, N3 write-back -->
4. Answer each consideration in `considerations`. Record `criterion_evidence` (per assigned criterion: the case or justified inspection, what ran, what it showed, where the output is, what it establishes and its limits; a description of the change or a future check is not evidence), `not_covered` (each added behaviour no test case covers, and why), `learned` and `decisions` (one line each, or ["none"]), and `learned_from` for each earlier commit that helped. A learning that changes a stored document goes there now: an implicit requirement made explicit becomes an acceptance line under its R-<n> in KNOWLEDGE/spec.md marked with this step, a new structural decision the next AD-<n> under ## Decisions, a working command a line under ## Commands. Changing an existing R-<n> or AD-<n> is a send-back. ShipLoop commits these with the step.
<!-- DUTIES['implement'] 6, now the send-back and blocked outcomes below -->
5. When the plan cannot be met as written, send it back (Outcomes) instead of working around it; report blocked only when a person or an outside service must act.
{{> considerations-titles}}
{{#if code_step}}{{> code-craft-titles}}{{/if}}

== Gates beyond the exit conditions (ShipLoop refuses at `complete`; `--check-only` shows the first) ==
- lint: once after it auto-fixes files (rerun every check, then submit done again), and on an unwaived new finding on a line this step changed
- scope: a changed code, test or undeclared file outside the item's declared paths
- `assumptions`: this stage's form has none; state a default in `summary`
- a send-back with none left for this item

{{> rules}}

== Result form (write it to {{inbox_abs}}; ShipLoop parses the JSON block) ==
```shiploop-state
{
  "outcome": "done",
  "headline": "<under 100 characters: what this step established>",
  "summary": "<decisions and defaults only this result records; per listed skill, used or why not>",
  "considerations": {"<consideration number and name>": "<the concrete handling and its anchor, or why the step does not touch it>"},
  "criterion_evidence": [{"criterion": "<criterion ID>", "case": "<case ID or justified inspection>", "ran_or_inspected": "<command or file>", "observed": "<what it showed>", "output": "<path of the saved output>", "establishes": "<what it shows>", "limits": "<what it does not show>"}],
  "not_covered": [{"behaviour": "<behaviour this step added that no test case covers>", "reason": "<why no test case covers it>"}],
  "learned": ["<what this step taught a later step or run, or none>"],
  "decisions": ["<a choice this step made, and why, or none>"],
  "learned_from": [{"commit": "<short commit that helped>", "contribution": "<what it taught this step>"}],
  "evidence_refs": ["{{receipt_abs}}"]
}
```
`not_covered` and `learned_from` may be []; `learned` and `decisions` take ["none"] when there is nothing.
Outcomes:
{{> outcome-done}}
{{> outcome-blocked}}
{{> outcome-send-back}}
{{> result-rules}}

{{> loop-invoke}}
{{loop_argument}}
{{> loop-result}}

<!-- appendix: file only -->
{{> appendix}}
{{> considerations}}
{{> code-craft}}
