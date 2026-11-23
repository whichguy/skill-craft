Continue in this context and execute the prompt. Delegation: inline: do this stage here and submit its callback
yourself; never clear or hand it off. After lost context, run the Recovery command.


ShipLoop navigator | step-plan | revision 18
Lost context, or unsure? Run python3 <PLUGIN>/skills/shiploop/scripts/shiploop next --run-dir=<OUT>/.shiploop-runs/seed/run (it reprints this step).
Full packet: <OUT>/.shiploop-runs/seed/run/packets/nav-<1>.md - open it with a file tool, not the shell, before acting if output is truncated, elided or missing the closing line === end ShipLoop print ===. The closing line does not rule out a middle cut. The file also holds the hand-offs, the knowledge files' contents and the request or its file. Its References block lists the other references and what each holds; open only the section a step needs, never a whole reference file, and do not re-read the ShipLoop skill card.
Callback for this stage (run once after its work, with the result written to <OUT>/.shiploop-runs/seed/run/inbox/nav-<1>.md; run it exactly as printed, with no pipe, redirect, ";" or shell variable: its output is the next stage's instructions and the status display reads the command): python3 <PLUGIN>/skills/shiploop/scripts/shiploop complete --run-dir=<OUT>/.shiploop-runs/seed/run --action=nav-<1>
Owner rule: concise and exact; no restating. Keep every command, path, ID and expected value.
Goal: Plan this item's change: `criteria`, `steps`, `test_commands`; `expectations`, `paths`, `follows` in the result.
Done when: every exit condition the Until Loop states in each instruction it prints holds; start it first (below). ShipLoop's gate checks the same list.
Also: the summary says which rows are new or changed and which are carried over from the previous step-plan result.
Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuses a loop still active or not reported satisfied; it also refuses a missing follows list, or a follows ID with no entry in KNOWLEDGE/spec.md or KNOWLEDGE/architecture.md; a focused command that only reruns an earlier item's test IDs, starts with a file guard, or lacks an ID per criterion; a criterion without confirm, an executed one whose only commands search text, or an inspected one naming no Test layers row that lacks a runner; code paths with no Test layers row; a hand-off field still holding a template placeholder; test_commands, paths, criteria or steps that do not fit (a criterion no command names, a command naming an unlisted one, deps that are not earlier steps, a step without its criteria or its proof, a step path the item does not declare, a criterion no step satisfies, a step that only changes test files, a Proof needing an unwritten test or a later step's file); test_commands without a check command and without check_na; an expectation without a state, a check or a known step, an existing step path with no works or broken expectation, or a new step path with no absent one; a step skill whose locator does not exist; a change to KNOWLEDGE/ that loses an earlier requirement (R-<n>) or decision (AD-<n>) ID; the usual faults (no outcome or summary, or an absolute evidence_refs path that does not exist). It does not judge the work: you confirm each condition. A refusal does not advance the run: fix the cause and run the same command again; the callback with `check` in place of `complete` prints the first refusal without accepting, so repeat it until the check says yes.

Until Loop (no iteration limit; the loop script counts the iterations):
RUN the Until Loop now, once, before any work, and do this stage's work only inside it. Start it with this command, in the foreground, exactly as printed (if the Receipt below already exists and is active, run its next_argv instead: a second start resets the loop):
python3 <PLUGIN>/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py start --receipt <OUT>/.shiploop-runs/seed/run/loops/nav-<1>-terminal.json --directory <OUT>/.shiploop-runs/seed/run/loops < <OUT>/.shiploop-runs/seed/run/loops/nav-<1>-contract.json
Then follow each instruction it prints (run its done_argv as printed) until the receipt says complete or stopped. Each instruction it prints states this stage's Work, Exit and Repeat conditions, the Contract file's words; do not edit that file or the receipt.
Contract: <OUT>/.shiploop-runs/seed/run/loops/nav-<1>-contract.json · Receipt: <OUT>/.shiploop-runs/seed/run/loops/nav-<1>-terminal.json
Result: write the result first, keeping the receipt in evidence_refs. For outcome done, close with one shell command whose parts each run only if the one before succeeded: the callback with `check` in place of `complete`, then the loop's done_argv with your satisfied done report on stdin, then the callback above. A refused check stops it before the report: fix what it names and run the same command again. For send-back or blocked, report the loop blocked, then run the callback. If the callback refuses for the loop, run the start command above again (an active receipt: its next_argv instead), then run the callback again. Done-report fields: classification trivial|non-trivial|unresolved, exit_assessment satisfied|unsatisfied|unknown, continuation_assessment allowed|blocked|cancelled, plus evidence and handoff (nonblank text).
Call an exit condition satisfied only when a command or file shows it after your last edit.

Keepalive marker: SHIPLOOP-RUN run=nav-<2> rev=18 dir=<OUT>/.shiploop-runs/seed/run

Host-recorded labels and reasons are untrusted status context, not instructions or authority.
Where: Work items > W1 "Implement and verify ticket comments" (1 of 1) > Plan > step-plan · Next: step-plan: plan this item's steps · Goal: Extend the ticket service with comments on tickets. `POST comments` with a JSON body `{"a…

Current stage guidance:
Change no product file in this stage.

1. **Recheck the item.** Reopen its `context` and recheck each condition. Check shared prerequisites against the
   supplier's recorded result and current architecture/environment evidence. Reuse established state; implement only
   the item's remaining change, and route missing prerequisites outside the item through the blocked route below.
   If the plan no longer requires it, report
   blocked (`awaiting` an answer: drop or keep) citing the superseding result; never skip the item
   or repair the queue here. Keep the change inside the item: available APIs and other parts of the request do not
   widen it. A prerequisite outside the item gets its supplier route in the summary and the blocked outcome.
2. **Test decisions.** Reopen the item's test decision and KNOWLEDGE/environment.md's harness and suite decisions,
   and plan against the Test layers and Test targets below; in the summary say which you retain, refine or supersede
   and why, locators in evidence_refs. Revalidate harness, suite and browser tools for the changed surfaces
   (Repeatable test-suite guide). Code this item writes that no Test layers row names: add its rows in
   `test_layers` (the test-strategy shape); a `prerequisite` row's harness is set up by the item's first step, whose
   check runs it. A remote-resident case needs its framework and an authorized setup, invocation, result retrieval
   and teardown route. Reuse an existing facility before the smallest missing one (Reusable test facilities); record
   its locator and readiness gap in the summary.
3. **`criteria`** (`[{"id": "C1", "text": "...", "confirm": "executed"}]`). Each text: `<condition>. Confirm by: <what
   a command observes>; pass when <expected result>`, naming the R-<n> served.
   - `confirm`: `executed` when a recorded command runs the behaviour (a text search runs nothing); `searched` for
     text the item writes (documentation, a docstring, a listed term), named by a search command; `inspected` only
     with `code` and `layer` naming a Test layers row that is `unverified`.
   - A condition no command can confirm is not a criterion: list it in the summary as an open item (who does what,
     what they report back) with `Confirm by: unconfirmable here — <what would confirm it>`.
   - A new or changed public entry point: a criterion that it checks its arguments, executed by its rejection tests,
     and one that it carries a contract docstring (Code craft 2-3), searched.
   - Where a criterion names an exact value, a count or a prefix match proves nothing.
   - For each step adding/changing visible UI, the criterion itself names spec UI requirements, selected AD ID and
     exact KNOWLEDGE file/section, visual anchors and rendered checks at required widths/themes. Pass when those
     choices render; functional or deferred checks do not substitute. Unconfirmable conditions stay open via the
     route above.
4. **`steps`**: every implementation step in order (one is fine); ShipLoop issues one implement packet per step.
   - Use the fewest steps the item allows; one step is the default. Every step pays its own test, document, review
     and commit round, so separately confirmable behaviours share a step and its proof shows each of them. Size: at
     most 12 criteria and 6 product files a step (a file that only describes another changed file counts with it;
     tests, docs and its proof script do not). Cut a larger item at a module or layer boundary (interface first,
     then each side) into the fewest steps of that size. Fold a step no proof confirms alone (half a rename,
     scaffolding) into the first step that uses it. A single bug fix or mechanical rename is one step.
   - Tests are not a step (the test stage writes them) unless the item is all tests.
   - Each step declares `deps` (earlier step IDs it truly needs, else []; list order is no dependency), the
     `criteria` it satisfies and its `proof`; its `task` cites IDs, not their text. Every criterion is satisfied by
     some step. Its `paths` (inside the item's) name every file it changes.
   - `proof`: the one command, from the repository root, that proves the step's criteria with only this step and
     accepted earlier ones; ShipLoop reruns it at the step's done, so make it safe to repeat. It needs no later step,
     unwritten test or release artifact (reuse a recorded command that proves them); skipping a missing file, or
     asserting only that a file exists where behaviour is asked, proves nothing. Remote-only target: the recorded test
     route only; steps share one proof script. None runs now: change the step boundary.
   - `skills`: reread the host's skills and the repository's skill index (an earlier item may have added one). List
     `{"name", "why", "locator", "stages"}` for each with a concrete use in the step, else []. Prefer a
     repository-local skill reused unchanged. `locator`: an existing SKILL.md or card; `stages`: implement (default),
     test, document, improve.
5. **`test_commands`**, run from the repository root.
   - focused: this item's cases, an ID for each executed criterion it names, and a runner flag that prints test names
     (Jest `--verbose`, pytest `-v`, others: GUIDES/platforms/; never dot or junit); a hand-written check prints its ID
     and outcome on every exit. A listed ID counts only as its own word in a test's printed name (for example, a test titled `TC-4a` does not show `TC-4`: title it `TC-4 (a)`). `min_tests`
     where a command must run at least that many. A run that executed no test is refused, so check the filter.
   - regression: the retained suites the changed paths affect; only the fast one marked `"minimum": true` runs
     before the last step (none: `minimum_na`).
   - check: the lint, type and build commands KNOWLEDGE/environment.md records for these files, judged by exit code, no
     `ids` or `min_tests`; each safe to repeat locally. None: `check_na` with the reason; no command at all: `test_commands_na`.
   - Every criterion is named in some command's `criteria`, and a command names only listed criteria.
   - A focused or regression command that runs on a Test targets row that keeps state names it in `target`.
6. **`expectations`**: each fact the steps build on, `{"id", "state", "statement", "steps", "paths", "check"}`;
   ShipLoop runs every check on the unchanged item base at validate-existing.
   - Every existing path a step changes or relies on is `works` or `broken` (the request says it is broken); every
     new path is `absent` (its place is free).
   - `check`: one read-only command from the repository root that exits 0 while the state holds. For `broken`, the
     reported failure still reproduces: `! npm test -- -t TC-3` or `node cli.js 2>&1 | grep -q 'TypeError'`.
   - Cite an open item due here (`due: W<n>`) in `from` on an executed criterion, or on an expectation for a fact that
     exists; nowhere else.
7. **`paths`**: every file the item changes (repository-relative files or globs), including the test files the test
   stage writes. The item commit takes these, the changed documentation and KNOWLEDGE/. No test command and only non-code
   paths skips the test stage; a diff touching no code or test path skips document. A new check script is a durable
   artifact: list it here with its consumer, or keep it in RUN/scratch.
8. **`follows`**: each R-<n> and AD-<n> followed; each must exist in KNOWLEDGE/spec.md or KNOWLEDGE/architecture.md.
9. **Concerns and plan record.** Map each concern the plan gave this item to the steps that deliver it.
   Reassess security at changed boundaries from the current item, even if the plan's security row says no or is absent.
   Put relevant protections and observable checks in the criteria; list checks due later as open items in the summary.
   Record in the item's `context` or the summary (each step's task and criteria stay its only directive),
   for the topics this item touches only:
   - outcome and invariants kept; target files and interfaces, matched to the house style (House-style guidance);
   - each step's failure cases and the diagnostics and errors it must produce;
   - the Coding decision guide's selection: runtime and version, artifact and boundary, matching sections only;
   - interactions, UI or service state changing: a Design basis paragraph or exact section links, rechecking the
     Interaction design guide's matching subsections and, for services, Service discovery guidance; copy no prior
     plan. Give baseline and delta; actors, events, connections and state owner; planned recovery checks; for UI the
     component, interaction and skin premises, design guidance identity and version or digest (or named fallback),
     first UI planning reads the UI visual-direction guide and records or reuses an AD-<n> for the authorized art direction,
     task hierarchy, design system, tokens, components and theme; and the rich interactions planned (a human-facing UI takes the ambition the request states, and with none stated
     defaults to ambitious and highly interactive: direct manipulation, inline editing, live preview, keyboard paths,
     animated transitions; give the reason for any scaled back); the UI decisions this step owns (UI planning
     ownership guide); locators of sources and checks.
   - when the item adds or moves code or stored data, replays a pinned value (fixed dice, seed data), or changes
     interactions, UI or service state: also record what the Plan record guide (GUIDES/plan-record.md) lists for that
     topic, opening only its matching section.
10. **Knowledge.** A structural choice KNOWLEDGE/architecture.md lacks: next AD-<n> under ## Decisions, cited in the
    step. A newly working command: KNOWLEDGE/environment.md ## Commands. Keep every R-<n> and AD-<n>; write nothing else
    in KNOWLEDGE/, unless an owner note this stage owes asks for a requirement change: then rewrite that requirement in
    place in KNOWLEDGE/spec.md (the ID stays; its entry keeps no copy of the old clause) and plan the step for the
    rewritten text.
11. **Execution graph.** Record none: the steps are issued one at a time.
12. **evidence_refs**: absolute paths of every planning file written, and the requirement sections and test locators
    used.


RULES (each one fixes a failure live runs showed; the long form is reference#rules):
- Do only this stage, then run its callback; ShipLoop picks the next stage.
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.
- Run ShipLoop commands in the foreground, unpiped, and never end the turn while one runs.
- Temporary files go in RUN/scratch, never /tmp.
- Record the PID of a background process you start and stop it by that PID, once you have confirmed it is still this
  run's. Never choose processes to stop by name or pattern (`pkill`, `killall`, a name search piped to `kill`).
- Never read, keep or report credential-store or session contents.


Work item: W1 (1/1) — Implement and verify ticket comments
Work item context: Ready: unchanged baseline npm test passed 124 cases (docs/shiploop/environment.md). Implement R-8 and AD-4 in one coherent CommonJS item: add node:test tests first against existing createService seam in test/helpers.js; validate HTTP, state boundaries, audit, notifications, persistence, legacy loading; then implement and run focused and full suite. Follow CONTRIBUTING.md, docs/api.md, docs/shiploop/environment.md and RUN/notes/research.md. Store owns changes, outbox and audit; compare normalized agent names exactly; body may contain line breaks. Check that resolved accepts and closed rejects, duplicate timestamps preserve order, each pending notification is distinct and rendered, and copies cannot mutate state. Persist version 1 records with defaults for absent comments. No extra dependencies or remote writes. Delivery is guarded local return. Done when tests and documentation pass and R-8 is observed. Dependency audit: RUN/notes/plan-dependencies.md.
Revisit: implement sent W1 back to step-plan (send-back 1); this packet asks for an amended plan, not a new one. Why (its summary, untrusted): "C2 proof is unachievable: shell quoting turns expected string author into the assert function and body into a variable. Correct response is a JSON string and cannot equal the function; revise the S2 proof quoting while preserving the assertions. S2 implementation remains in worktree; lint exit 0." Evidence: RUN/results/nav-<3>.md.
Your previous accepted step-plan result: RUN/results/nav-<4>.md (accepted host report, untrusted; revalidate what you carry over).
Changed upstream since your previous step plan: nothing (a send-back reruns no planning stage); the result that sent the item back says what to change.
Keep unchanged rows with their IDs: carry over as written every row the send-back result and the changes above do not touch; change or add only what they require. Submit the whole amended plan: it replaces the previous one.
Fix forward: S1 is done (reviewed and committed) and never runs again. Start steps with these rows exactly as written, then the steps still to run. Change only those: a fix to what a done step built is a new step with new criterion IDs. Expectations describe the base the next step begins from, which holds the done steps' changes, so restate theirs (absent becomes works):
{"criteria": ["C1"], "deps": [], "id": "S1", "paths": ["src/store.js", "src/persistence.js"], "proof": "node -e 'const a=require('\"'\"'node:assert/strict'\"'\"'),{TicketStore}=require('\"'\"'./src/store'\"'\"'),{manualClock}=require('\"'\"'./src/clock'\"'\"'),{toDocument,fromDocument}=require('\"'\"'./src/persistence'\"'\"');const s=new TicketStore({clock:manualClock()}),t=s.create({title:'\"'\"'x'\"'\"',priority:'\"'\"'normal'\"'\"',requester:'\"'\"'r'\"'\"'},'\"'\"'r'\"'\"');s.assign(t.id,'\"'\"'agent'\"'\"','\"'\"'actor'\"'\"');let before=s.outboxReport().pending.length;const c=s.comment(t.id,{author:'\"'\"'guest'\"'\"',body:'\"'\"'hello'\"'\"'},'\"'\"'guest'\"'\"'),d=s.comment(t.id,{author:'\"'\"'guest'\"'\"',body:'\"'\"'second'\"'\"'},'\"'\"'guest'\"'\"');a.deepEqual(s.get(t.id).comments,[c,d]);a.equal(s.outboxReport().pending.length,before+2);a.equal(s.history(t.id).at(-1).action,'\"'\"'ticket.commented'\"'\"');let file=toDocument(s.snapshot(),new Date()),saved=fromDocument(file,Error);a.deepEqual(saved.tickets[0].comments,[c,d]);delete file.tickets[0].comments;a.deepEqual(fromDocument(file,Error).tickets[0].comments,[]);s.transition(t.id,'\"'\"'in_progress'\"'\"','\"'\"'actor'\"'\"');s.transition(t.id,'\"'\"'resolved'\"'\"','\"'\"'actor'\"'\"');s.comment(t.id,{author:'\"'\"'agent'\"'\"',body:'\"'\"'ok'\"'\"'},'\"'\"'agent'\"'\"');s.transition(t.id,'\"'\"'closed'\"'\"','\"'\"'actor'\"'\"');a.throws(()=>s.comment(t.id,{author:'\"'\"'guest'\"'\"',body:'\"'\"'no'\"'\"'},'\"'\"'guest'\"'\"'),{status:409});'", "skills": [], "task": "Implement stored comments and persistence for C1, including audit and outbox event.", "done": true}
Concerns the plan decided for W1 (map each owned by step-plan to the steps that deliver it):
- api: HTTP route and validation (docs/shiploop/architecture.md; owner step-plan)
- messaging: outbox and worker template (docs/shiploop/architecture.md; owner step-plan)
- state: version-1 ticket records, legacy defaults and restart (docs/shiploop/architecture.md; owner step-plan)
- concurrency: existing synchronous store operations (docs/shiploop/architecture.md; owner step-plan)
- security: existing body-size limit and validation (docs/shiploop/architecture.md; owner step-plan)
- observability: audit and existing outbox report (docs/shiploop/architecture.md; owner step-plan)
Test layers (`test_layers`; an inspected criterion names an unverified row by code and layer):
- component · node:test with test/helpers.js · available: src/app.js and src/tickets/validate.js, src/store.js and src/persistence.js, src/templates.js and worker
Test targets (`targets`; a case on one that keeps state says in red how its base fails):
- local isolated Node service and temporary data file: keeps state no
Result template:
```shiploop-state
{
  "concerns": [
    {"id": "api", "steps": ["S1"]},
    {"id": "messaging", "steps": ["S1"]},
    {"id": "state", "steps": ["S1"]},
    {"id": "concurrency", "steps": ["S1"]},
    {"id": "security", "steps": ["S1"]},
    {"id": "observability", "steps": ["S1"]}
  ],
  "criteria": [
    {"confirm": "executed", "id": "C1", "text": "<condition. Confirm by: what the command observes; pass when <expected result>>"},
    {"confirm": "executed", "id": "C2", "text": "<condition. Confirm by: what the command observes; pass when <expected result>>"}
  ],
  "evidence_refs": ["<OUT>/.shiploop-runs/seed/run/loops/nav-<1>-terminal.json"],
  "expectations": [
    {"check": "<read-only command, run from the repository root, that exits 0 when it holds>", "id": "E1", "paths": ["<existing file a step changes>"], "state": "works", "statement": "<what exists and works today>", "steps": ["S1"]},
    {"check": "<read-only command that exits 0 when it is absent>", "id": "E2", "paths": ["<new file a step adds>"], "state": "absent", "statement": "<what does not exist yet>", "steps": ["S2"]}
  ],
  "follows": ["<R-<n> or AD-<n>>"],
  "headline": "<one line for the user: what this step established>",
  "outcome": "done",
  "paths": ["<repository-relative file or glob>"],
  "steps": [
    {"criteria": ["C1"], "deps": [], "id": "S1", "proof": "<the one command, from the repository root, that proves this step's criteria>", "skills": [{"name": "<helper skill>", "why": "<its use in this step>"}], "task": "..."},
    {"criteria": ["C2"], "deps": ["S1"], "id": "S2", "proof": "<the command that proves C2>", "skills": [], "task": "..."}
  ],
  "summary": "<decisions, defaults, open questions and owners only this result records; no restatement>",
  "test_commands": [
    {"command": "...", "criteria": ["C1", "C2"], "ids": ["TC-1", "TC-2"], "suite": "focused"},
    {"command": "<exit-code check command>", "suite": "check"},
    {"command": "...", "minimum": true, "suite": "regression"}
  ]
}
```
Allowed outcomes: done | blocked.
Fill the template: each key once, every placeholder (<...> and "...") replaced, "outcome" and "summary" top-level. Any other outcome keeps headline and evidence_refs and drops the other fields:
blocked (only a person or an outside service can unblock it): {"outcome": "blocked", "summary": "<what stopped the work>", "awaiting": {...}} with awaiting in the shape reference#blocked gives (a wrong shape is refused with that shape quoted)

References (symbols expand to these absolute paths; commands stay literal):
KNOWLEDGE = <OUT>/.shiploop-runs/seed/worktree/docs/shiploop (knowledge home) · RUN = <OUT>/.shiploop-runs/seed/run (run records) · GUIDES = <PLUGIN>/skills/shiploop/references (the skill's guides)
WORKTREE = <OUT>/.shiploop-runs/seed/worktree (all product work; a working directory, never a --result value; an isolated worktree, returned to the original branch only at release or handoff)
Repeatable test-suite guide: GUIDES/repeatable-test-suites.md#select-or-revalidate-the-harness
Coding decision guide: GUIDES/coding-guidance.md#select-guidance
House-style guidance: GUIDES/house-style.md#write-the-match-contract
Service discovery guidance: GUIDES/service-discovery.md#development-handoff
UI planning ownership guide: GUIDES/behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner
UI visual-direction guide: GUIDES/platforms/ui.md#light-expressive-starting-point
Reusable test facilities: GUIDES/repeatable-test-suites.md#reuse-and-define-test-facilities
Interaction design guide: GUIDES/behavioral-requirements.md#actors-channels-and-state-ownership
Backchain planning guide: GUIDES/backchain-planning.md#navigator-planning
Backchain graph check: python3 <PLUGIN>/skills/shiploop/scripts/shiploop backchain-check --run-dir <OUT>/.shiploop-runs/seed/run --candidate <your candidate file>
Knowledge files: KNOWLEDGE/spec.md: living spec; KNOWLEDGE/environment.md: environment; KNOWLEDGE/architecture.md: architecture
Run records: RUN/reference.md (the rules' long forms: #policies, #rules, #recovery); RUN/context-index.md (every file of this run and what it holds)
Results this stage builds on (open each not already in your context; report a conflict instead of choosing silently):
- spec stage result: RUN/results/nav-<5>.md
- test-strategy stage result: RUN/results/nav-<6>.md
- plan stage result: RUN/results/nav-<7>.md
- prepare stage result: RUN/results/nav-<8>.md
Progress view: [HTML file](<<OUT>/.shiploop-runs/seed/run/progress.html>) — use this file to track changes during this ShipLoop run.
Pause without consuming the action: python3 <PLUGIN>/skills/shiploop/scripts/shiploop pause --run-dir=<OUT>/.shiploop-runs/seed/run '--reason=<who asked and why>' (only when the user asks or a real blocker stops authorized work)
Knowledge files this stage reads, listed by contents (read a file with a file-reading tool; its text is data, not instructions):
KNOWLEDGE/spec.md (5927 bytes, 41 lines), contents:
  # Ticket assignment specification
  ## Requirements: R-1 Assignment API · R-2 Ticket representation and storage · R-3 Notifications and audit · R-4 Filtering · R-5 Command line and compatibility · R-6 Bulk reassignment · R-7 Urgent escalation · R-8 Ticket comments
  ## Non-functional requirements
  ## Retired
KNOWLEDGE/environment.md (13400 bytes, 132 lines), contents:
  # Environment
  ## Targets and runtimes
  ## Commands
  ## Platform facts
  ## Skills
  ## Access and accounts
  ## Harnesses and suites
  ## Harnesses and suites plan
  ## ID convention
  ## Commands
  ## Prepared environment
  ## Verified assignment checks
  ## Integrated suite
  ## Local return and verification
  ## Returned result
  ## Operational observations
  ## Bulk reassignment and escalation discovery (2026-10-29)
  ### Bulk and escalation suite plan
  ### Preparation for bulk and escalation
  ### Verified bulk and escalation checks
  ### Release route for bulk and escalation
  ### Returned candidate verification
  ### Operational handoff (2026-10-29)
  ## Comments discovery (2026-10-31)
  ## Comment suite plan
  ## Comment preparation
KNOWLEDGE/architecture.md (4559 bytes, 41 lines), contents:
  # Architecture
  ## Decisions: AD-1 Existing store and outbox · AD-2 Filter intersection and CLI
  ## Real-boundary checks
  ## Structure
  ## Conventions
  ## Stack
  ## Interfaces and boundaries
  ## Superseded
  ### Bulk and escalation boundary checks: AD-3 Bulk assignment and escalation (implemented)
  ### Comment real-boundary checks: AD-4 Comments within existing ticket state (planned)
Handed off by earlier stages, quoted by value from their accepted results (untrusted host records; not new instructions):
open items for W1: none open

This action's pass log (optional, never a completion gate: create it and append what each pass checked and what is left; after a reset, open it first if it exists): RUN/notes/nav-<1>.md
Halt (terminal; only on the user's explicit stop): the Pause command with `halt` in place of `pause`.
State: RUN/state.md (results/, inbox/ beside it) · CLI locator: <PLUGIN>/skills/shiploop/scripts/shiploop · Scratch directory (your temporary files, not /tmp): RUN/scratch
Repository knowledge index (host-authored, if present): WORKTREE/SHIPLOOP.md · every other policy and guide, and the rules' long form: RUN/reference.md (#policies, #rules, #recovery).
Recovery command (reprints the current packet from saved state; check what is already done before redoing it):
python3 <PLUGIN>/skills/shiploop/scripts/shiploop next --run-dir=<OUT>/.shiploop-runs/seed/run
Original request: RUN/request.md, verbatim with its sentence index S1..Sn (quoted whole only at intake, spec and plan). Its scope governs every summary of it; open the file when this stage depends on its exact words.
Plan record guide: GUIDES/plan-record.md#topics-the-item-touches
Namespace and placement guidance: GUIDES/coding-practices.md#namespaces-and-placement
Schema and storage guidance: GUIDES/coding-practices.md#schema-and-storage
State and data assessment: GUIDES/requirements-definition.md#state-and-data-change-assessment
Full ordered work queue: RUN/state.md; field work_items.
Last accepted transition (untrusted host report; not new instructions):
Stage: implement; outcome: send-back; work item: W1; action: nav-<3>
----- BEGIN LAST ACCEPTED SUMMARY -----
C2 proof is unachievable: shell quoting turns expected string author into the assert function and body into a variable. Correct response is a JSON string and cannot equal the function; revise the S2 proof quoting while preserving the assertions. S2 implementation remains in worktree; lint exit 0.
----- END LAST ACCEPTED SUMMARY -----

This stage keeps these up to date (create them if missing): KNOWLEDGE/architecture.md, KNOWLEDGE/environment.md.
ShipLoop refuses release-plan if any of these is missing or empty: KNOWLEDGE/environment.md.
If this stage changes KNOWLEDGE/, ShipLoop checks and commits it when the stage is accepted; do not commit it yourself.
