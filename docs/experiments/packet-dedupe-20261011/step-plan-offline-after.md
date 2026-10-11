Continue in this context and execute the prompt.

Delegation: inline. Do this stage in this conversation, and submit its callback
yourself. Do not clear the context or hand the stage to Ask Agent or a native
worker; the host's own compaction manages the context. After lost context, run
the Recovery command and continue from the packet it reprints.


ShipLoop navigator | step-plan | revision 10
Callback for this stage (run once after its work, with the result written to the file it names): python3 shiploop complete --run-dir=<run> --action=nav-da87e77a6e0c4d46b60bc9e13470ad4b --result=<run>/inbox/nav-da87e77a6e0c4d46b60bc9e13470ad4b.md
Goal: Plan this item's concrete changes, checks and the facts they build on.
Done when: every exit condition in the /until-loop argument below holds; ShipLoop's gate checks the same list.
Checked by: when you report done, ShipLoop checks this stage's Until Loop receipt (its path must be in evidence_refs) against the contract it rebuilds from the run state, and refuses a loop that is still active or whose last report does not say the exit condition is satisfied; it also refuses no outcome or summary, an absolute evidence_refs path that does not exist, or an explicit credential pattern; test_commands, paths, criteria or steps that do not fit (a criterion no command names, a command naming an unlisted one, deps that are not earlier steps, a step without its criteria or paths, a step path the item does not declare, a criterion no step satisfies, a step that only changes test files); test_commands without a check command and without check_na; an expectation without a state, a check or a known step, an existing step path with no works or broken expectation, or a new step path with no absent one; a step skill whose locator does not exist; a change to HOME/ that loses an earlier requirement (R-<n>) or decision (AD-<n>) ID, or that looks like a credential.
Considerations for this stage:
- Develop: Name target files, interfaces and conventions; follow the house-style match contract.
- Test: Record the item's test commands; the test stage and verify run them exactly.
- Deploy: Note integration impact and any release prerequisite.
- Tools: ShipLoop records the item's lint base when the item starts; name the linters, type checks and build commands that cover the changed files.
References (each path is defined once, here; the packet names files by these symbols; a file marked "not written yet" does not exist yet):
HOME = <repo>/docs/shiploop: the repository's knowledge home
- HOME/spec.md: living spec, ## Requirements, ## Non-functional requirements, ## Retired (not written yet: spec writes it)
- HOME/environment.md: environment, ## Targets and runtimes, ## Commands, ## Skills, ## Access and accounts, ## Platform facts (not written yet: discovery writes it)
- HOME/architecture.md: architecture, ## Stack, ## Structure, ## Conventions, ## Interfaces and boundaries, ## Decisions, ## Superseded (not written yet: plan writes it)
- HOME/test-strategy.md: test strategy, ## Harnesses and suites, ## Commands, ## ID convention, ## Real-boundary checks (not written yet: test-strategy writes it)
- HOME/features/README.md (not written yet: ShipLoop writes it at its next knowledge commit)
FEATURE = HOME/features/in-this-node-js-project-paginate-872504: this run's feature folder
- FEATURE/spec.md: feature spec (not written yet: spec writes it)
- FEATURE/plan.md (not written yet: plan writes it)
- FEATURE/test-spec.md (not written yet: test-spec writes it)
- FEATURE/system-tests.md (not written yet: system-test-author writes it)
- FEATURE/release-plan.md (not written yet: release-plan writes it)
- FEATURE/outcome.md (not written yet: release-verify writes it)
RUN = <run>: this run's records (state.md, results/, loops/, tests/, expectations/)
WORKTREE = <repo>: the execution checkout, where product work happens
Consult at this stage (cite the headings you use and each R-<n> or AD-<n> you follow):
- HOME/spec.md ## Requirements, ## Non-functional requirements
- HOME/architecture.md ## Structure, ## Interfaces and boundaries, ## Conventions, ## Decisions
- HOME/environment.md ## Commands, ## Targets and runtimes, ## Skills
- HOME/test-strategy.md ## Harnesses and suites, ## ID convention
Results this stage builds on (earlier stages' products, each labelled <item> <stage> <product>; open each one whose content is not already in your context; report a conflict with one instead of silently choosing):
- spec stage result: RUN/results/nav-764a9553408c43079c30efef22ad031f.md
- test-strategy stage result: RUN/results/nav-68f7f2a308274c68be53db71ff4f1f80.md
- plan stage result: RUN/results/nav-8b27fc2e8612449bbe9c3625986aa02e.md
- prepare stage result: RUN/results/nav-cc5920fe921b42a78b93a9c9fae36059.md
Result template:
# ShipLoop navigator result

```shiploop-state
{
  "criteria": [
    {"id": "C1", "text": "<criterion>"},
    {"id": "C2", "text": "<criterion>"}
  ],
  "evidence_refs": ["<run>/loops/nav-da87e77a6e0c4d46b60bc9e13470ad4b-terminal.json"],
  "expectations": [
    {"check": "<read-only command, run from the repository root, that exits 0 when it holds>", "id": "E1", "paths": ["<existing file a step changes>"], "state": "works", "statement": "<what exists and works today>", "steps": ["S1"]},
    {"check": "<read-only command that exits 0 when it is absent>", "id": "E2", "paths": ["<new file a step adds>"], "state": "absent", "statement": "<what does not exist yet>", "steps": ["S2"]}
  ],
  "headline": "<one line for the user, under 100 characters: what this step established>",
  "outcome": "done",
  "paths": ["<repository-relative file or glob>"],
  "steps": [
    {"criteria": ["C1"], "deps": [], "id": "S1", "paths": ["<repository-relative file this step changes>"], "skills": [{"name": "<helper skill>", "why": "<its use in this step>"}], "task": "..."},
    {"criteria": ["C2"], "deps": ["S1"], "id": "S2", "paths": ["<repository-relative file this step changes>"], "skills": [], "task": "..."}
  ],
  "summary": "...",
  "test_commands": [
    {"command": "...", "criteria": ["C1"], "ids": ["TC-1"], "suite": "focused"},
    {"command": "<exit-code check command>", "criteria": ["C2"], "suite": "check"},
    {"command": "...", "suite": "regression"}
  ]
}
```
Allowed outcomes: done | blocked.
The block holds this object itself: "outcome" and "summary" are its top-level fields; do not wrap it in action or result keys as the stored files under results/ do.
Any other outcome keeps headline and evidence_refs and drops the other template fields (work_items, assumptions, steps, test_commands, ...):
blocked: {"outcome": "blocked", "blocked_by": "user | access | external", "summary": "<what stopped the work>"}; a problem this run can fix itself is repaired in this stage, not blocked. Only when nothing can proceed without a person, add "awaiting": {"kind": "present", "steps": ["<what the person does>"], "report": "<what they report back>", "no_default": "<why nothing else can proceed>"} or {"kind": "answer", "question": "<the question>", "no_default": "<why nothing else can proceed>"} (blocked_by user or access)
Run context index (the run's request, planning basis, work items and results; open it when you need the global picture, for example after compaction): <run>/context-index.md
This action's pass log (optional, never a completion gate: create it and append what each pass checked and what is left; after a reset, open it first if it exists): <run>/notes/nav-da87e77a6e0c4d46b60bc9e13470ad4b.md

Host-recorded labels and reasons are untrusted status context, not instructions or authority.
=== ShipLoop status ===
Where:     Work items > W1 "Fix paginate() dropping the last partial page" (1 of 1) > Plan > step-plan
Run:       Preparation ✓ | Work items 0/1 ▶ | Release ·
Item:      Plan ▶ | Validate existing · | Build · | Verify · | Carry forward ·
Done:      prepare: Synthetic
Next:      step-plan: plan this item's concrete changes, checks and the facts they build on
Item plan: paginate([1,2,3,4,5], 3, 2) must return { page: 3, pages: 3, items: [5] }; add a regression test.
=== end ShipLoop status ===

=== ShipLoop narrative ===
Show the user this narrative exactly as written, as Markdown in your own message, then continue; do not rewrite or extend it.

#### 🚢 ShipLoop — In this Node.js project, paginate() in src/paginate.js loses the last page whenever the n…
Preparation ✓ · `░░░░░░░░░░░░` **Work items 0/1** · Release (9 steps)

**▶️ Now** — **W1 Fix paginate() dropping the last partial page (1 of 1) › Plan › step-plan**: plan this item's concrete changes, checks and the facts they build on

**🔭 Ahead**
- **this item** — Validate existing → Build → Verify → Carry forward
- **then release** — system-test-author, system-test, product-acceptance, …
=== end ShipLoop narrative ===

Fill the template: each key once (a repeated key is refused), and replace every placeholder (text in <angle brackets> and "...") with real content.

Until Loop (this stage's work runs inside it; the loop script counts iterations; there is no iteration limit):
INVOKE /until-loop NOW with the argument below, verbatim. Do this stage's work only inside that loop.
Argument:
    Work: Draft or revise this action's result at <run>/inbox/nav-da87e77a6e0c4d46b60bc9e13470ad4b.md and this item's section of <repo>/docs/shiploop/features/in-this-node-js-project-paginate-872504/plan.md from the knowledge-home headings the ShipLoop packet names; then run the `complete --check-only` command printed in the packet <run>/packets/nav-da87e77a6e0c4d46b60bc9e13470ad4b.md on the draft and fix each refusal.
    Exit when ALL of these hold:
    1. the result opens with one sentence naming the change and the checks that prove it
    2. steps lists every implementation step in the order to do them
    3. each step declares deps, the criteria it satisfies and the paths it changes, every criterion is satisfied by a step, and no step only changes test files (unless the whole item is tests)
    4. test_commands records focused, regression and at least one check command (lint, type or build), with check_na giving the reason when there is no check command, or test_commands_na giving the reason there are no commands
    5. expectations record, for every existing path a step changes or relies on, a works or broken expectation, and for every new path an absent one, each with a read-only check command
    6. each step's skills list names a concrete use for each helper skill, or is empty
    7. the files the item will change are declared in paths
    Repeat while a check-only refusal remains or an exit condition above does not hold; there is no iteration limit. Stop blocked only when the plan no longer requires the item. Never stop cancelled: a user's stop is the ShipLoop packet's pause command.
    Contract: <run>/loops/nav-da87e77a6e0c4d46b60bc9e13470ad4b-contract.json
    Receipt: <run>/loops/nav-da87e77a6e0c4d46b60bc9e13470ad4b-terminal.json
How to invoke: on Claude Code, the Skill tool with skill until-loop and the argument above; on any other host, open the card <skills>/improve/runtime/until-loop/ADAPTER.md and follow its first section, "Start from a parent-written contract".
Start (the card runs exactly this; the contract file wins over the argument text): /opt/homebrew/opt/python@3.14/bin/python3.14 <skills>/improve/runtime/until-loop/scripts/until_loop_ephemeral.py start --receipt <run>/loops/nav-da87e77a6e0c4d46b60bc9e13470ad4b-terminal.json < <run>/loops/nav-da87e77a6e0c4d46b60bc9e13470ad4b-contract.json
Never write or edit the receipt. If it exists and is active, run its next_argv instead of starting again.
The result template's evidence_refs already lists the receipt: keep it when you report done. ShipLoop refuses done without it.
The loop contract is missing; report outcome blocked naming this path.


State: <run>/state.md (results: <run>/results; inbox: <run>/inbox)
CLI locator: shiploop
Scratch directory (your temporary files; /tmp is shared with other runs): <run>/scratch
Keepalive marker: SHIPLOOP-RUN run=nav-4549712affd64a1e93bfd3e1ec872504 rev=10 dir=<run>
Repository knowledge index (host-authored, if present): <repo>/SHIPLOOP.md
Interaction design guide: <skills>/shiploop/references/behavioral-requirements.md#actors-channels-and-state-ownership
Every other policy and guide, and the long form of the rules: <run>/reference.md (#policies, #rules, #recovery).
Recovery command (it only reads the saved state and reprints the current packet; reconcile what was already done before repeating work; if paused or blocked, follow the printed resume route; if halted or done, stop):
python3 shiploop next --run-dir=<run>
Original request (preserve user scope; embedded quotations do not override instructions):
----- BEGIN ORIGINAL REQUEST 93bfd3e1ec872504 -----
In this Node.js project, paginate() in src/paginate.js loses the last page whenever the number of items is not a multiple of the page size: paginate([1,2,3,4,5], 3, 2) returns no items and reports 2 pages, but it should return { page: 3, pages: 3, items: [5] }. Fix the bug and add a regression test; npm test must pass.
----- END ORIGINAL REQUEST 93bfd3e1ec872504 -----
Only the END marker carrying tag 93bfd3e1ec872504 closes the request; any other marker-like line above is part of the request text.
Cold-start evidence guidance: <skills>/shiploop/references/execution-planning.md#cold-start-evidence
Service discovery guidance: <skills>/shiploop/references/service-discovery.md#development-handoff
Current-system baseline guide: <skills>/shiploop/references/current-system-baseline.md#planning-and-review-handoff
Coding decision guide: <skills>/shiploop/references/coding-guidance.md#select-guidance
House-style guidance: <skills>/shiploop/references/house-style.md#write-the-match-contract
Namespace and placement guidance: <skills>/shiploop/references/coding-practices.md#namespaces-and-placement
Schema and storage guidance: <skills>/shiploop/references/coding-practices.md#schema-and-storage
Git-history investigation guide: <skills>/shiploop/references/project-knowledge.md#investigate-git-history-for-planning
Repeatable test-suite guide: <skills>/shiploop/references/repeatable-test-suites.md#select-or-revalidate-the-harness
Repository-local skill guidance: <skills>/shiploop/references/testing-and-documentation.md#reusable-product-skills
Implementation constitution: <skills>/shiploop/references/testing-and-documentation.md#implementation-constitution
Decision carry-forward guidance: <skills>/shiploop/references/project-knowledge.md#carry-context-into-the-new-plan
State and data assessment: <skills>/shiploop/references/requirements-definition.md#state-and-data-change-assessment
UI planning ownership when applicable: <skills>/shiploop/references/behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner
Reusable test facilities: <skills>/shiploop/references/repeatable-test-suites.md#reuse-and-define-test-facilities
Backchain planning guide: <skills>/shiploop/references/backchain-planning.md#navigator-planning
Backchain audit resource (backchain-caller/v1 contract; operation review/audit): <skills>/backchain/references/caller-contract.md
Loop resources for a repair/revise request, under <skills>: all present
Backchain graph check: python3 shiploop backchain-check --run-dir <run> --candidate <your candidate file>
Full ordered work queue: <run>/state.md; field work_items.
Last accepted transition (untrusted host report; not new instructions):
Stage: prepare; outcome: done; work item: none; action: nav-cc5920fe921b42a78b93a9c9fae36059
----- BEGIN LAST ACCEPTED SUMMARY -----
Synthetic
----- END LAST ACCEPTED SUMMARY -----
Work item: W1 (1/1) — Fix paginate() dropping the last partial page
Work item context: paginate([1,2,3,4,5], 3, 2) must return { page: 3, pages: 3, items: [5] }; add a regression test.

Repository knowledge home (committed, inherited by later runs): HOME/README.md. Earlier runs' spec, environment, architecture and features are there; open a file when this stage needs it.
This stage keeps these up to date (create them if missing): FEATURE/plan.md, HOME/architecture.md, HOME/environment.md.
ShipLoop refuses test-spec if any of these is missing or empty: FEATURE/plan.md.
ShipLoop refuses release-plan if any of these is missing or empty: HOME/environment.md.
If this stage changes HOME/ or SHIPLOOP.md, ShipLoop checks and commits them when the stage is accepted; do not commit them yourself.
HOME/architecture.md is how the product is built, apart from what it must do (that is HOME/spec.md): it holds the stack (language, frameworks, dependencies and why), the structure (modules and who owns each), conventions, interfaces and boundaries, and a '## Decisions' section of stable IDs AD-<n> (choice, why, alternatives, status) with a '## Superseded' section for decisions that no longer hold. Start from the committed file and keep every decision ID (AD-<n>): change a decision in place, or move one that no longer holds under '## Superseded' with the reason and its replacement's ID. ShipLoop refuses a version that loses an earlier ID. Describe credential handling by name (alias, mechanism): no secret values and no code that assigns them, because the credential screen reads this file. If this item makes a structural decision (a new module, dependency, interface, storage or convention), add it as the next unused AD-<n> and cite the ID in the step plan.

Navigator contract: <skills>/shiploop/references/navigator.md#sdlc-responsibilities
Current stage guidance:
Work inside the /until-loop printed below. ShipLoop wrote its contract; do not edit
it. Call an exit condition satisfied only when a command or file shows it after
your last edit. If ShipLoop refuses done after the loop ends, fix the cause, start
the loop again with the same command and submit again.
Change no product file in this stage.
1. Recheck first. Reopen this item's `context` and its section of FEATURE/plan.md,
   and recheck each condition they state. If the plan no longer requires the
   item, report blocked (blocked_by user, `awaiting` an answer: drop or keep the
   item) and cite the plan section that superseded it. Never skip the item and
   never repair the queue here. Keep the change inside this item: available APIs
   and other parts of the request do not widen it. A prerequisite outside the
   item gets its supplier route and the blocked disposition, not a future bullet.
   Reopen the current item's test decision and the run's test strategy (under
   "Results this stage builds on") and keep the prior decision locators and any
   justified revision in evidence_refs, saying which decisions are retained,
   refined or superseded.
2. `criteria`: `[{"id": "C1", "text": "..."}]`. Write each as `<condition>.
   Confirm by: <command, observation or inspection>; pass when <expected
   result>`, say whether it must be exercised or whether inspection suffices,
   and trace it to the R-<n> it serves. A docs or coverage criterion gets a
   command check, such as a search for the required terms. A condition that no
   command can confirm is not a criterion: list it in the summary as an open item
   (who does what, what they report back) and mark it in the plan note as
   `Confirm by: unconfirmable here — <what would confirm it>`. When the item
   adds or changes a public entry point, add a criterion that each such entry
   point checks its arguments and carries a contract docstring (Code craft 2-3),
   confirmed by its rejection tests and by inspecting the diff for each one.
3. `steps`: every implementation step, in the order to do them (one is fine);
   ShipLoop issues one implement packet per step.
   - Size: one behaviour-level change that a named check proves. Split a step
     that holds two behaviours each confirmable on its own, crosses a module or
     layer boundary (the interface first, then each side), needs "and" between
     two outcomes, or is too large to review in one pass. Merge a step that no
     check can confirm on its own (half a rename, scaffolding nothing uses yet)
     into the step it serves. A single bug fix or mechanical rename is one step.
   - Tests are not a step: the test stage writes them from the test spec after
     the last implement step. A step that only changes test files is refused
     unless the whole item is tests.
   - Each step declares `deps` (the earlier step IDs it truly needs, or []; list
     order alone is not a dependency), the `criteria` IDs it satisfies and the
     `paths` it changes (inside the item's paths). Every criterion is satisfied
     by some step.
   - `skills`: reread the host's skills and the repository's skill index now (an
     earlier item may have added one), and list `{"name", "why", "locator"}` for
     each skill with a concrete use in that step, or []. Prefer a repository-local
     skill reused unchanged. `locator` is optional; when given, it is the path of
     an existing SKILL.md or card. The implement packet prints these.
4. `test_commands`: `[{"command", "suite", "ids", "criteria"}]`, each run from
   the repository root. The test stage and verify run exactly these commands,
   and ShipLoop refuses a run that executed no test (a filter that matches
   nothing exits 0 in most runners).
   - focused: this item's cases, with the ids they will carry and a runner flag
     that prints test names (Jest `--verbose`, pytest `-v`, `node --test` with
     its default spec or the tap reporter; never dot or junit). A listed ID counts only as its own word in a test's printed name (for example, a test titled `TC-4a` does not show `TC-4`: title it `TC-4 (a)`).
     Add `min_tests` where a command must run at least that many.
   - regression: the retained suites the changed paths affect.
   - check: the lint, type and build commands HOME/environment.md records for
     these files, judged by exit code, with no ids or min_tests. With none, give
     `check_na` with the reason; with no command at all, `test_commands_na`.
   - Every criterion is named in some command's `criteria`, and a command names
     only listed criteria. A list too large for the test loop's contract is
     refused: shorten ids, drop duplicates or split the item.
   - Revalidate the testing systems and browser tools for the changed surfaces
     and place each case's harness and suite (Repeatable test-suite guide). Reuse
     the supported choices, or record a justified revision. A remote-resident
     case needs its framework and its authorized setup, invocation, result
     retrieval and teardown route. Reuse existing test facilities before
     defining the smallest missing one (Reusable test facilities guide); carry
     its locator and readiness gap into item context and the
     Improve child's context/notes.
5. `expectations`: each fact the steps build on, not a health check. Give each
   one `{"id", "state", "statement", "steps", "paths", "check", "from"}`.
   - Every existing path a step changes or relies on gets a works expectation (it
     works today) or a broken one (the request says it is broken). Every new path
     gets an absent one (its place is free).
   - `check` is one read-only command, run from the repository root, that exits 0
     while the state holds. For a broken expectation, the reported failure still
     reproduces: `! npm test -- -t TC-3` or
     `node cli.js 2>&1 | grep -q 'TypeError'`.
   - An open plan assumption that this item consumes becomes an expectation, and
     its `from` names that assumption.
   - ShipLoop runs every check on the unchanged item base at validate-existing.
6. `paths`: every file the item will change, as repository-relative files or
   globs, including the test files the test stage will write.
   - The item commit takes these files, the changed documentation and HOME/.
   - An item with no test command and only non-code paths skips the test stage.
   - An item whose diff touches no code or test path skips document.
7. Plan note, under this item's heading in FEATURE/plan.md. Record:
   - the outcome and the invariants kept;
   - the contracts and responsibilities that change;
   - each step's failure cases, and the diagnostics and errors it must produce;
   - the documentation to change;
   - the integration impact and the release prerequisites;
   - the readiness, completion and revalidation conditions.

   Use the Coding decision guide: identify the actual runtime and version, the
   artifact and the boundary, then read and link only the sections that match.
   - When the item adds or moves code or stored data:
     - name each file, module and public symbol with its environment, namespace,
       visibility and collision check;
     - name each stored field, key or table with its owner, its migration
       (unneeded, an earlier step, this step, or a deploy obligation) and its
       round-trip check.
     The Namespace and Schema guides cover both.
   - Label each pinned value that a check replays (fixed dice, seed data) as a
     source-check fixture, separate from the runtime control. Confirm that an
     external oracle (a golden file, fixture or snapshot) agrees with the task.
   - When interactions, UI or service state are affected, add a Design basis
     paragraph, or exact section links. Recheck the Interaction design guide's
     matching subsections (incoming/outgoing events, connection lifecycle,
     UI-specific planning), and for service work the Service discovery guidance,
     instead of copying the prior plan. The paragraph gives:
     - the baseline and the delta;
     - the actors, events, connections and state owner;
     - the planned recovery checks;
     - for UI: the component, interaction and skin premises, the design
       guidance's identity/version or digest (or the named fallback), and the
       rich interactions planned;
     - the locators of its sources and checks.
8. Knowledge.
   - Write a structural choice that HOME/architecture.md does not record yet as
     the next AD-<n> under ## Decisions, and cite it in the step.
   - Add a newly working command to HOME/environment.md ## Commands.
   - Keep every R-<n> and AD-<n>.
   - Write only the knowledge home, and do not commit it yourself.
9. evidence_refs: give absolute paths for the FEATURE/plan.md section, every
   planning file this stage wrote, and the requirement sections and test
   locators you used; an unrecorded conversation is not a planning handoff.
   Consolidate upstream material for a fresh context as supporting references,
   not a new assignment: Each reviewed step's task/ready/done criteria remain its sole execution directive.
Record no execution graph: an inline run issues the steps one at a time.


Optional: for a material prerequisite ambiguity or acceptance gap, request one
read-only Backchain review/audit (Backchain planning guide), then run the printed
`backchain-check` on your candidate and cite its receipt in evidence_refs.


Rules for every stage (the long form of each is in the run reference file: reference#rules, #requirements, #progress):
- Do only this stage, then run its callback and follow the packet it returns. ShipLoop owns the graph and the next
  step; preserve unrelated work.
- Unattended: nothing arrives on standard input. Take the default that best fits the request and the recorded
  knowledge, record it as an assumption (the alternatives and why this one) in the summary, and continue. Record a
  step only a person can do (a sign-in, a grant) as an open item (who does what, what they report back) and continue
  with the rest. Report blocked only when nothing can proceed without a person; a problem this run can fix, such as
  a documented command that does not run what it claims, is fixed here and rerun.
- Recheck notes, Git history and prior results against the repository before relying on them; base test, build and
  release claims on what you observed. A missing prerequisite, permission or trustworthy check is unresolved, never
  N/A; a justified N/A says what was assessed and why it does not apply.
- Requirements: read the accepted ones from HOME/spec.md and keep unaffected ones; never relax one to match code or
  tests. Current explicit user instructions supersede older clauses. Keep each requested runtime and entry point: a
  local fixture cannot stand in for a target capability. Put the requirement sections and test locators you used in
  evidence_refs; report a missing source instead of inventing one.
- Temporary files go in RUN/scratch, not /tmp (shared with other runs). Discover identity or access with supported
  non-mutating probes and sanitized evidence. Never read, decode, keep or report local authentication, session or
  credential-store contents.
- Keep each ShipLoop command in the foreground with its output unpiped, and never end the turn while one runs; a
  `complete` that reruns tests can take minutes. If a keepalive hook refuses to end the turn, run the command it names.
- Tell the user one line per stage (the item, the stage finished, the stage starting); paste a ShipLoop narrative as
  its first line says. A question about the run is not a stop. A request to stop, pause or not implement runs Pause.


Improve: Every step-plan result, including blocked, starts this action's Improve child. That review checks the result against the Done-when conditions above.
Pause without consuming the action: python3 shiploop pause --run-dir=<run> '--reason=<who asked and why>' (only when the user asks or a real blocker stops authorized work)
Halt (terminal and irreversible; only on an explicit user stop): python3 shiploop halt --run-dir=<run> '--reason=<why>'
