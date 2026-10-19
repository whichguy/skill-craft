---
template: step-plan
version: 2
consumer: The packet's reader is the model that plans one work item, in a fresh context, from this print alone, once per item (and again after a send-back). The result's reader is ShipLoop's step-plan gate, which parses the Result form at `complete`; test-spec, validate-existing, implement, test and verify then read its accepted fields by value.
print_budget: 19500
shrink: last_summary, env_skills, arch_toc, spec_toc, env_commands, platform_testing, recent_commits, revisit_block
requires: A1 concern map (plan.concerns rows; `concerns` in _RESULT_KEYS and its gate) · T-D2 producer bounds (plan: work item context 2500, concern rows 1200, open assumptions 1200) · N2 commit look-back (recent_commits) · N5 outcome names · C6/G1 platform card `## Testing` section and the environment-to-card mapping · N5 awaiting kinds answer, present, service · decision 19 KNOWLEDGE symbol (reference_paths, symbolic, expand_result_roots, excerpt locators; HOME retired) · placeholder registry read from this form (navigator._placeholders) · loops Work cites the template's Method items (_duty_items counts them) · engine E3/E4 (plan 8.5) · E5: a test pins that the runtime's printed start, next and done packets (stdout, not the receipt) carry the contract's Work, Exit and Repeat (decision 20; U-up keeps them) · E6: shiploop_narrative caps the progress block at 900 · lands with: obligation ledger rows (the until-loop row rewritten for decision 20), head-order tests, packet_view and counters repointed in the same commit
flags:
| flag | source |
|---|---|
| loop_started | file exists: RUN/loops/<action>-terminal.json |
| loop_unavailable | loops.contract or loops.runtime raised (today's invoke_lines prints the same line) |
| revisit | state.revisions[item] > 0 (the item came back by send-back; navigator _sent_back_results) |
| inline | state.delegation == "inline" (the ask-agent route also prints Method 10, the execution graph) |
| worktree_run | the run has an isolated product checkout (execution mode navigator-worktree) |
slots:
| slot | kind | source | bound | over | pool |
|---|---|---|---|---|---|
| stage | scalar | const "step-plan" | 12 | refuse | - |
| revision | scalar | state.revision | 6 | refuse | - |
| action | scalar | state.current_action.id | 40 | refuse | - |
| next_command | cmd | cli next --run-dir=RUN | cli+run+24 | refuse | - |
| pause_command | cmd | cli pause --run-dir=RUN '--reason=<who asked and why>' | cli+run+56 | refuse | - |
| callback_command | cmd | cli complete --run-dir=RUN --action=<action> | cli+run+74 | refuse | - |
| keepalive_marker | scalar | "SHIPLOOP-RUN run=<run_id> rev=<revision> dir=<RUN>" (revision up to six digits) | run+72 | refuse | - |
| packet_abs | scalar | RUN/packets/<action>.md, absolute | run+48 | refuse | - |
| inbox_abs | scalar | RUN/inbox/<action>.md, absolute | run+46 | refuse | - |
| loop_start_command | cmd | until-loop start --receipt <receipt> < <contract> | root+run+run+208 | refuse | - |
| loop_error | scalar | the LoopError text when the loop cannot be built | 300 | excerpt | - |
| contract_abs | scalar | RUN/loops/<action>-contract.json, absolute | run+57 | refuse | - |
| receipt_abs | scalar | RUN/loops/<action>-terminal.json, absolute | run+57 | refuse | - |
| progress | block | narrative partial at a milestone, else the one-line Where/Next status (producer bound: shiploop_narrative caps it at 900, E6) | 900 | refuse | - |
| item_id | scalar | state.work_items[work_index].id | 12 | refuse | - |
| item_pos | scalar | "<work_index+1> of <len(work_items)>" | 12 | refuse | - |
| item_title | scalar | state.work_items[work_index].title | 240 | refuse | - |
| item_context | include | result:plan.work_items[id=<item_id>].context, whole (producer bound: plan gate, T-D2) | 2500 | refuse | - |
| open_assumptions | block | result:plan.assumptions[disposition=open, consumer=<item_id>], row assumption (producer bound: plan gate, T-D2) | 1200 | refuse | - |
| plan_concerns | block | result:plan.concerns[item=<item_id>, applies=yes], row concern (only the rows Method 8 maps; producer bound: plan gate, A1 + T-D2) | 1200 | refuse | - |
| revisit_block | block | D3: the accepted step-plan result to amend (locator), the send-back result (locator, headline, summary cut at 600 as REVISIT_SUMMARY) and the IDs it invalidates; its pointer names both locators | 1000 | excerpt | - |
| recent_commits | block | git log from the item's starting HEAD: the last two commits that are not ShipLoop bookkeeping (its knowledge-record and leftover commits); step and review commits count; subject and its Key learnings line, row commit (N2) | 900 | excerpt | - |
| env_commands | include | home:environment.md#Commands, code only: each command with its one-line label (G3) | 1500 | excerpt | inputs |
| platform_card | scalar | the card KNOWLEDGE/environment.md ## Targets and runtimes names (GUIDES/platforms/<card>.md), or "none" for a target without a card | 120 | refuse | - |
| platform_testing | include | guide:platforms/<card>.md#Testing (runner, reporter, deploy order; G1, C6) | 1000 | excerpt | inputs |
| spec_toc | include | home:spec.md#toc (R-<n> headings) | 600 | toc | inputs |
| arch_toc | include | home:architecture.md#toc (AD-<n>, Real-boundary checks and Procedures headings) | 700 | toc | inputs |
| env_skills | include | home:environment.md#Skills | 300 | excerpt | inputs |
| last_summary | include | result:<previous stage>.summary | 600 | excerpt | inputs |
| done_next | scalar | the navigator's successor for a done step-plan | 80 | refuse | - |
| stop_outcomes | scalar | stage_spec outcomes other than done, N5 names, joined " or " (step-plan: "blocked") | 40 | refuse | - |
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
| commit | `- {short} {subject}: {learning}` |
| locator | `{label}: {path}` |
gates:
| gate | refusal (code) | anchor in the print |
|---|---|---|
| loop-receipt | loops.check_terminal / check_loop_packet | keep the Receipt in evidence_refs and run the Callback |
| loop-route | check_loop_packet: no run of this contract, or an active receipt | run the command the refusal names |
| result-keys | navigator._canonical_result: unsupported fields | a key that neither the form nor the Method names |
| placeholder | navigator._placeholders (exact strings this form prints) | replace every <...> placeholder |
| evidence | _check_submitted_evidence (absolute paths), expand_result_roots (unknown leading root) | an evidence_refs path that does not exist |
| home-ids | knowledge.check: an R-<n> or AD-<n> lost | loses an R-<n> or AD-<n> |
| sp-follows | follows ID with no entry | each with an entry in KNOWLEDGE/spec.md or architecture.md |
| sp-step-paths | a step path outside the item's paths | Every step path is inside them |
| sp-skill-locator | a step skill locator that does not exist | with a locator that exists |
| sp-deps | _normalise_steps: deps must name earlier steps | earlier step IDs only |
| sp-step-criteria | _check_step_sizing: a step names criteria the result does not list | IDs from `criteria` |
| sp-criteria-covered | _normalise_criteria: every criterion needs a test command | every criterion is named by at least one row's `criteria` |
| sp-criteria-known | _normalise_criteria: test_commands name criteria not listed | every name is a listed criterion |
| sp-commands-na | _normalise_criteria: test_commands_na with criteria | `test_commands_na` only for an item with no criteria |
| sp-check-suite | expectations._check_check_suite | never both |
| sp-check-row | test_loop.normalise_commands: a check row takes no ids or min_tests | no `ids`, no `min_tests` |
| sp-ids | test_loop.normalise_commands: ids without spaces, unique | no spaces, each once |
| sp-paths | item_scope.normalise_paths: nonblank, inside the repository, unique | each once, repository-relative |
| sp-expectations | expectations.check_step_plan: states, checks, path coverage | is `works` or `broken`; every new path is `absent` |
| sp-expectation-steps | expectations.check_step_plan: an expectation names steps the result does not list | names steps that exist |
| sp-assumption-from | expectations.check_step_plan: an open assumption with no expectation `from` | becomes an expectation whose `from` names it |
| sp-concerns | A1 gate: an applies-yes concern row unmapped | `concerns`: each applies-yes concern row |
| sp-outcome | the outcome enum (N5) | - blocked: |
result:
| key | type | rule (gate id) |
|---|---|---|
| outcome | enum done, blocked | sp-outcome |
| headline | string <= 100 | common-headline |
| summary | string; opens with one sentence naming the change and its checks | common-summary |
| criteria | list of {id C<n>, text} | sp-criteria-covered, sp-criteria-known |
| steps | list of {id S<n>, deps, criteria, task, check, paths?, skills} | sp-deps, sp-step-criteria, sp-step-paths, sp-skill-locator |
| test_commands | list of {command, suite, ids?, criteria?, min_tests?}; or test_commands_na; check_na | sp-check-suite, sp-check-row, sp-ids, sp-commands-na |
| expectations | list of {id E<n>, state, statement, steps, paths, check, from?} | sp-expectations, sp-expectation-steps, sp-assumption-from |
| paths | list of repository-relative paths | sp-paths, sp-step-paths |
| follows | list of R-<n>, AD-<n> | sp-follows |
| concerns | list of {concern, steps, check} or {concern, owner_stage} | sp-concerns |
| evidence_refs | list of paths or https URLs; holds the receipt | evidence, loop-receipt |
---
{{> frame}}
Goal: Plan work item {{item_id}}: ordered steps, each proven by its own command, with the item's criteria, test commands, expectations, paths, follows and concern mapping.
Done when: every exit condition of this stage's Until Loop holds (the loop prints them when it starts). Checked at `complete` by the rules in the Method and the form; `--check-only` shows the first refusal.

{{> loop-invoke}}
{{> loop-result}}

{{progress}}

== Input, quoted by value from accepted records ==
Work item {{item_id}} ({{item_pos}}): {{item_title}}
Context (the plan's directive for this item, whole):
{{item_context}}
Open assumptions this item settles:
{{open_assumptions}}
Concern rows the plan marked applies-yes for {{item_id}}:
{{plan_concerns}}
{{#if revisit}}Send-back to amend (open the accepted plan and the send-back result named below, amend the plan and submit it whole; keep every row the evidence does not touch, with its ID):
{{revisit_block}}
{{/if}}Recent commits (the last two that are not ShipLoop bookkeeping; what earlier work learned):
{{recent_commits}}
<!-- the elastic pool fills in body order from here: the platform card's testing section, then ## Commands (G1, G3) -->
Platform card {{platform_card}}, testing: {{platform_testing}}
KNOWLEDGE/environment.md ## Commands (commands only):
{{env_commands}}
Requirements and decisions (headings; open a section only when a step depends on its exact words):
{{spec_toc}}
{{arch_toc}}
KNOWLEDGE/environment.md ## Skills: {{env_skills}}
Last accepted: {{last_summary}}

== Method, in order (change no product file in this stage) ==
<!-- DUTIES['step-plan'] 1 -->
1. Recheck the item against its Context. If the accepted plan no longer requires it, report blocked with a decision (drop or keep), citing the result that supersedes it. A prerequisite outside the item goes in `summary` with its supplier.
<!-- DUTIES['step-plan'] 2, with C1 and G1; red_na belongs to the test stage (review SP-11) -->
2. Take the test route from ## Commands and the platform card. In `summary` say which recorded harness and commands you keep, refine or replace, and why. A command run against a remote copy (an org, a hosted service) sees only what was deployed: a focused row for such a target deploys the tree it judges first, or the test stage records `red_na` for its IDs.
<!-- DUTIES['step-plan'] 3 -->
3. `criteria`: `<condition>. Confirm by: <command, observation or inspection>; pass when <result>. Serves R-<n>.` A condition no command can confirm here is an open item in `summary` (who does what, what they report back). A new or changed public entry point adds a criterion that it rejects invalid arguments, confirmed by its rejection tests.
<!-- DUTIES['step-plan'] 4 (rewrite R1, B1, B2); deps rule stated (review SP-13) -->
4. `steps`, in order (one is fine); ShipLoop issues one implement packet per step. A step is one behaviour-level change its `check` proves: split at a second separately confirmable behaviour, a module or layer boundary (interface first) or an "and" between outcomes; fold scaffolding no check confirms alone into the step that uses it. Tests are not a step unless the whole item is tests (the test stage writes them); every criterion is in some step's `criteria`. Each step: `deps` (earlier step IDs only), `criteria` (IDs from `criteria`), `task` (cites IDs, not their text), `check`, optional `paths`, `skills` (`{"name", "why", "locator"}` per concrete use with a locator that exists, else []).
   `check`: one command from the repository root; ShipLoop runs it at the step's done. It observes behaviour: matching the implementation's own text (a literal, a call shape) or skipping a missing file proves nothing. It needs no later step, unwritten test or release artifact. Behaviour that runs only on a remote target: deploy only this step's paths to the recorded development target, then run a read-only probe the run's authority covers. A probe longer than one line is a script, inside the item's paths, that the check runs.
<!-- DUTIES['step-plan'] 5 + ID_WORD_RULE; the coverage, check-row and id rules the gates apply (review SP-4) -->
5. `test_commands` (test and verify run exactly these): every criterion is named by at least one row's `criteria`, and every name is a listed criterion. Focused rows carry this item's case IDs (no spaces, each once) and a reporter printing one pass or fail line per test name (platform card; never dot or junit); an ID counts only as its own word in a test name (`TC-4 (a)`, not `TC-4a`); `min_tests` where a command must run at least that many. Regression rows: the retained suites the changed paths affect. Check rows: the lint, type and build commands ## Commands records, judged by exit code alone (no `ids`, no `min_tests`) and safe to repeat; with none, `check_na` with the reason, never both. `test_commands_na` only for an item with no criteria. A row naming a criterion runs code on that criterion's paths.
<!-- DUTIES['step-plan'] 6 -->
6. `expectations`: every existing path a step changes or relies on is `works` or `broken`; every new path is `absent`. Each names steps that exist and one read-only `check` that exits 0 while the state holds (`broken`: `! <the failing command>`). Each open assumption above becomes an expectation whose `from` names it. ShipLoop runs them on the unchanged item base at validate-existing.
<!-- DUTIES['step-plan'] 7, 8; the glob statement corrected (review SP-12) -->
7. `paths`: every file the item changes, tests included, each once, repository-relative; prefer exact paths (a glob's `*` also matches across `/`). Every step path is inside them. `follows`: every R-<n> and AD-<n> the steps follow, each with an entry in KNOWLEDGE/spec.md or architecture.md (one under ## Superseded or ## Retired counts).
<!-- A1 concern map (replaces DUTIES['step-plan'] 9) -->
8. `concerns`: each applies-yes concern row above maps to the steps that carry it and the check that proves it, or to the later stage that owns it; a row with no decision is an open item in `summary` for the stage that must decide it.
<!-- DUTIES['step-plan'] 10, symbol KNOWLEDGE (decision 19) -->
9. Knowledge: a structural choice KNOWLEDGE/architecture.md lacks is the next AD-<n> under ## Decisions, cited in its step; a newly working command goes under ## Commands with its one-line label. Keep every R-<n> and AD-<n>; write nothing else in KNOWLEDGE/.
{{#if !inline}}10. Execution graph: give each change that needs no other its own step (`deps` []), joined by a later step that needs both; put the graph's path and digest in `summary` and evidence_refs (Parallel-chain guide).{{/if}}

{{> rules}}

== Result form (write it to {{inbox_abs}}; ShipLoop parses the JSON block) ==
```shiploop-state
{
  "outcome": "done",
  "headline": "<under 100 characters: what this plan established>",
  "summary": "<one sentence naming the change and its checks; then harness choices, decisions, defaults, open items and owners>",
  "criteria": [{"id": "C1", "text": "<condition>. Confirm by: <command>; pass when <result>. Serves R-<n>."}],
  "steps": [{"id": "S1", "deps": [], "criteria": ["C1"], "task": "<the step's outcome, citing C1>", "check": "<the command that proves C1>", "skills": []}],
  "test_commands": [{"command": "<focused command>", "suite": "focused", "ids": ["<case ID>"], "criteria": ["C1"], "min_tests": 1},
                    {"command": "<regression command>", "suite": "regression"}, {"command": "<lint, type or build command>", "suite": "check"}],
  "expectations": [{"id": "E1", "state": "absent", "statement": "<fact>", "steps": ["S1"], "paths": ["<file>"], "check": "<read-only command>"}],
  "paths": ["<repository-relative file>"],
  "follows": ["<R-<n> or AD-<n> this item follows>"],
  "concerns": [{"concern": "<concern row>", "steps": ["S1"], "check": "<command or case ID>"}],
  "evidence_refs": ["{{receipt_abs}}"]
}
```
Outcomes:
{{> outcome-done}}
{{> outcome-blocked}}
{{> result-rules}}

<!-- appendix: file only -->
{{> appendix}}
