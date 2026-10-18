---
template: step-plan
version: 1
consumer: The packet's reader is the model that plans one work item, in a fresh context, from this print alone, once per item (and again on a revise). The result's reader is ShipLoop's step-plan gate, which parses the Result form at `complete`; test-spec, validate-existing, implement, test and verify then read its accepted fields by value.
print_budget: 19500
flags:
| flag | source |
|---|---|
| loop_started | file exists: RUN/loops/<action>-terminal.json |
| revisit | state.revises[item] > 0 (the item came back from implement or test) |
| inline | state.delegation == "inline" (the ask-agent route also prints Method 10, the execution graph) |
slots:
| slot | kind | source | bound | over | pool |
|---|---|---|---|---|---|
| stage | scalar | const "step-plan" | 12 | refuse | - |
| revision | scalar | state.revision | 6 | refuse | - |
| action | scalar | state.current_action.id | 40 | refuse | - |
| next_command | cmd | cli next --run-dir=RUN | cli+run+24 | refuse | - |
| pause_command | cmd | cli pause --run-dir=RUN '--reason=<who asked and why>' | cli+run+56 | refuse | - |
| callback_command | cmd | cli complete --run-dir=RUN --action=<action> | cli+run+74 | refuse | - |
| keepalive_marker | scalar | "SHIPLOOP-RUN run=<run_id> rev=<revision> dir=<RUN>" | run+65 | refuse | - |
| loop_start_command | cmd | until-loop start --receipt <receipt> < <contract> | root+run+run+208 | refuse | - |
| receipt_abs | scalar | RUN/loops/<action>-terminal.json, absolute (evidence_refs entries must be absolute) | run+57 | refuse | - |
| packet_abs | scalar | RUN/packets/<action>.md, absolute (the loop runtime reprints the Work line without this packet's symbols) | run+48 | refuse | - |
| inbox_abs | scalar | RUN/inbox/<action>.md, absolute (same reason) | run+46 | refuse | - |
| progress | block | narrative partial at a milestone, else the one-line Where/Next status (shiploop_narrative) | 1100 | refuse | - |
| item_id | scalar | state.work_items[work_index].id | 12 | refuse | - |
| item_pos | scalar | "<work_index+1> of <len(work_items)>" | 12 | refuse | - |
| item_title | scalar | state.work_items[work_index].title | 240 | refuse | - |
| item_context | include | result:plan.work_items[id=<item_id>].context, whole (plan's gate refuses a context over this bound, so this slot never cuts) | 3500 | refuse | - |
| open_assumptions | block | result:plan.assumptions[disposition=open, consumer=<item_id>], row assumption | 1200 | excerpt | inputs |
| plan_concerns | block | result:plan.concerns[item=<item_id>], row concern (A1; plan's gate bounds the rows) | 1500 | refuse | - |
| spec_toc | include | home:spec.md#toc (R-<n> headings of ## Requirements and ## Non-functional requirements) | 600 | toc | inputs |
| arch_toc | include | home:architecture.md#toc (AD-<n>, Real-boundary checks and Procedures headings) | 700 | toc | inputs |
| env_commands | include | home:environment.md#Commands, code only: each command with its one-line label (G3; the prose stays in the file) | 1500 | excerpt | inputs |
| env_skills | include | home:environment.md#Skills | 300 | excerpt | inputs |
| platform_card | scalar | the card HOME/environment.md ## Targets and runtimes names (GUIDES/platforms/<card>.md) | 120 | refuse | - |
| platform_testing | include | guide:platforms/<card>.md#Testing (runner, reporter, deploy order; G1; needs a ## Testing heading in each card) | 1000 | excerpt | inputs |
| revisit_block | block | the item's revise result summary, whole and once (D3), and the rows it invalidates | 1500 | excerpt | inputs |
| last_summary | include | result:<previous stage>.summary | 600 | excerpt | inputs |
| run_dir | scalar | RUN (absolute) | run | refuse | - |
| guides_dir | scalar | GUIDES (absolute) | root+30 | refuse | - |
| worktree | scalar | WORKTREE (absolute) | run+5 | refuse | - |
| source_results | block | RUN/results/<action>.md of plan, prepare and test-strategy, row locator | 400 | refuse | - |
| last_accepted | block | history[-1]: stage, outcome, action | 160 | refuse | - |
pools:
| pool | size |
|---|---|
| inputs | rest>=1000 |
rows:
| row | format |
|---|---|
| assumption | `- {id}: {assumption} \| check: {check} \| reason: {reason}` |
| concern | `- {concern}: {applies}; {decision} ({anchor}; owner {owner_stage})` |
| locator | `{label}: {path}` |
result:
| key | type | rule (gate id) |
|---|---|---|
| outcome | enum done, blocked | sp-outcome |
| headline | string <= 100 | common-headline |
| summary | string; opens with one sentence naming the change and its checks | common-summary |
| criteria | list of {id C<n>, text} | sp-steps |
| steps | list of {id S<n>, deps, criteria, task, check, paths?, skills} | sp-steps, sp-step-paths, sp-skill-locator |
| test_commands | list of {command, suite focused, regression or check, ids?, criteria?, min_tests?}; or test_commands_na | sp-steps, sp-check-row, sp-criterion-paths |
| expectations | list of {id E<n>, state works, broken or absent, statement, steps, paths, check, from?} | sp-expectations |
| paths | list of exact repository-relative files | sp-step-paths |
| follows | list of R-<n>, AD-<n> | sp-follows |
| concerns | list of {concern, steps, check} or {concern, owner_stage} | sp-concerns |
| evidence_refs | list of absolute paths or https URLs; holds the receipt | common-evidence, loop-receipt |
---
{{> frame}}
Goal: Plan work item {{item_id}}: ordered steps, each proven by its own command, with the item's criteria, test commands, expectations, paths, follows and concern mapping.
Done when: every exit condition in the Until Loop argument below holds. Checked by: the Gates below, at `complete`.

{{> loop-invoke}}
----- BEGIN until-loop ARGUMENT -----
Work: Plan work item {{item_id}} by the Method in {{packet_abs}} and write the Result form to {{inbox_abs}}; then run the Callback command with `--check-only` added and fix each refusal.
Exit when ALL of these hold:
1. the result opens with one sentence naming the change and the checks that prove it
2. steps lists every implementation step in order; each declares deps, its criteria and a check that observes those criteria using only this step and accepted earlier steps; every criterion is satisfied by a step; no step only changes test files (unless the whole item is tests)
3. test_commands records focused, regression and check rows (or check_na / test_commands_na with the reason), and every row naming a criterion runs code on that criterion's paths
4. expectations give every existing path a step changes or relies on a works or broken row and every new path an absent row, each with a read-only check
5. every applies-yes concern row maps to the steps that carry it and the check that proves it, or to the later stage that owns it
6. paths declares every file the item changes, and each step's skills names a concrete use or is empty
Repeat while a check-only refusal remains or an exit condition above does not hold; there is no iteration limit. Stop blocked only when the plan no longer requires the item. Never stop cancelled: a user's stop is the packet's Pause command.
Contract: RUN/loops/{{action}}-contract.json
Receipt: RUN/loops/{{action}}-terminal.json
----- END until-loop ARGUMENT -----
{{> loop-result}}

{{progress}}

== Input, quoted by value from accepted records ==
Work item {{item_id}} ({{item_pos}}): {{item_title}}
Context (the plan's directive for this item, whole):
{{item_context}}
Concern rows the plan recorded for {{item_id}}:
{{plan_concerns}}
<!-- the elastic pool fills in this order: commands and the platform card first (G1, G3), then the rest -->
HOME/environment.md ## Commands (commands only):
{{env_commands}}
Platform card {{platform_card}}, testing: {{platform_testing}}
Open assumptions this item settles:
{{open_assumptions}}
Requirements and decisions (headings; open a section only when a step depends on its exact words):
{{spec_toc}}
{{arch_toc}}
HOME/environment.md ## Skills: {{env_skills}}
{{#if revisit}}Revisit (amend the accepted plan; keep each row the evidence below does not touch, with its ID):
{{revisit_block}}{{/if}}
Last accepted: {{last_summary}}

== Method, in order (change no product file in this stage) ==
<!-- DUTIES['step-plan'] 1 -->
1. Recheck the item against its Context. If the accepted plan no longer requires it, report blocked (`awaiting`: drop or keep) citing the result that supersedes it. A prerequisite outside the item goes in `summary` with its supplier.
<!-- DUTIES['step-plan'] 2, with C1 and G1 -->
2. Take the test route from ## Commands and the platform card. In `summary` say which recorded harness and commands you keep, refine or replace, and why. A command run against a remote copy (an org, a hosted service) sees only what was deployed: a focused row for such a target deploys the tree it judges first, or test-spec records `red_na` for its IDs.
<!-- DUTIES['step-plan'] 3 -->
3. `criteria`: `<condition>. Confirm by: <command, observation or inspection>; pass when <result>. Serves R-<n>.` A condition no command can confirm here is an open item in `summary` (who does what, what they report back). A new or changed public entry point adds a criterion that it rejects invalid arguments, confirmed by its rejection tests.
<!-- DUTIES['step-plan'] 4, rewritten: packets-audit.json duty_review.rewrites R1 (B1, B2) -->
4. `steps`, in order (one is fine); ShipLoop issues one implement packet per step. A step is one behaviour-level change its `check` proves: split at a second separately confirmable behaviour, a module or layer boundary (interface first) or an "and" between outcomes; fold scaffolding no check confirms alone into the step that uses it. Tests are not a step (the test stage writes them). Each step: `deps`, `criteria`, `task` (cites IDs, not their text), `check`, optional `paths`, `skills` (`{"name", "why", "locator"}` per concrete use, else []).
   `check`: the one command, from the repository root, that proves the step's criteria with only this step and accepted earlier ones; ShipLoop runs it at the step's done. It observes behaviour: matching the implementation's own text (a literal, a call shape) dictates form and proves nothing, and so does skipping a missing file. It needs no later step, unwritten test or release artifact. Behaviour that runs only on a remote target: deploy only this step's paths to the recorded development target, then run a read-only probe the run's authority covers.
<!-- DUTIES['step-plan'] 5 + ID_WORD_RULE; B2 -->
5. `test_commands` (test and verify run exactly these): focused rows carry this item's case IDs and a reporter that prints one pass or fail line per test name (platform card; never dot or junit); a listed ID counts only as its own word in a test name (`TC-4 (a)`, not `TC-4a`); `min_tests` where a command must run at least that many. regression: the retained suites the changed paths affect. check: the lint, type and build commands ## Commands records, judged by exit code and safe to repeat; none: `check_na`; no command at all: `test_commands_na`. A row naming a criterion runs code on that criterion's paths.
<!-- DUTIES['step-plan'] 6 -->
6. `expectations`: every existing path a step changes or relies on is `works` or `broken`; every new path is `absent`; each `check` is one read-only command that exits 0 while the state holds (`broken`: `! <the failing command>`). An open assumption this item settles becomes an expectation whose `from` names it. ShipLoop runs them on the unchanged item base at validate-existing.
<!-- DUTIES['step-plan'] 7, 8; E2 path rule -->
7. `paths`: every file the item changes, tests included, as exact repository-relative paths (a glob never matches across `/`). `follows`: every R-<n> and AD-<n> the steps follow.
<!-- replaces DUTIES['step-plan'] 9 (Plan record prose) with the A1 concern map -->
8. `concerns`: each applies-yes row above maps to the steps that carry it and the check that proves it, or to the later stage that owns it; a row with no decision is an open item in `summary` for the stage that must decide it.
<!-- DUTIES['step-plan'] 10; items 11 (inline: "record none") and 12 (evidence_refs: in the form) dropped -->
9. Knowledge: a structural choice HOME/architecture.md lacks is the next AD-<n> under ## Decisions, cited in its step; a newly working command goes under ## Commands. Keep every R-<n> and AD-<n>; write nothing else in HOME/.
{{#if !inline}}10. Execution graph: give each change that needs no other its own step (`deps` []), joined by a later step that needs both; put the graph's path and digest in `summary` and evidence_refs (Parallel-chain guide).{{/if}}

== Gates beyond the exit conditions (ShipLoop refuses at `complete`; `--check-only` shows the first) ==
<!-- the step-plan faults of today's Checked by line that the exit conditions do not already name, plus the E2 rules -->
- a follows ID with no entry in HOME/spec.md or HOME/architecture.md (an ID under ## Superseded or ## Retired counts as kept)  <!-- gate: sp-follows -->
- a step path outside the item's paths; a step skill locator that does not exist  <!-- gate: sp-step-paths, sp-skill-locator -->
- a placeholder left in the form; a change to HOME/ that loses an R-<n> or AD-<n>; an evidence_refs entry that is neither an existing absolute path nor an https URL  <!-- gate: common-placeholder, home-ids, common-evidence -->
ShipLoop checks structure, not the plan's quality: the Improve review that follows judges the substance.

{{> rules}}

== Result form (write it to the Callback's result file; ShipLoop parses the JSON block) ==
```shiploop-state
{
  "outcome": "done",
  "headline": "<under 100 characters: what this plan established>",
  "summary": "<one sentence naming the change and its checks; then harness choices, decisions, defaults, open items and owners>",
  "criteria": [{"id": "C1", "text": "<condition>. Confirm by: <command>; pass when <result>. Serves R-<n>."}],
  "steps": [{"id": "S1", "deps": [], "criteria": ["C1"], "task": "<outcome, citing C1>", "check": "<command>", "skills": []}],
  "test_commands": [{"command": "<focused>", "suite": "focused", "ids": ["<case ID>"], "criteria": ["C1"], "min_tests": 1},
                    {"command": "<regression>", "suite": "regression"}, {"command": "<lint, type or build>", "suite": "check"}],
  "expectations": [{"id": "E1", "state": "absent", "statement": "<fact>", "steps": ["S1"], "paths": ["<file>"], "check": "<read-only command>"}],
  "paths": ["<file>"],
  "follows": ["R-<n>", "AD-<n>"],
  "concerns": [{"concern": "<row>", "steps": ["S1"], "check": "<command or case ID>"}],
  "evidence_refs": ["{{receipt_abs}}"]
}
```
Allowed outcomes: done | blocked.
{{> result-rules}}

<!-- appendix: file only -->
{{> appendix}}
