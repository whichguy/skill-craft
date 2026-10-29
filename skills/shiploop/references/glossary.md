# ShipLoop glossary

This is the one place a ShipLoop term is defined. A packet, duty, refusal, reference or test uses each term in the
meaning below. Where a term is being unified, the note says by which rename (R1-R4 of the run-5 batch). Changing a term
means changing every use in one commit, updating this file, and listing the old term below so a test refuses its
return (owner rule, 2026-10-24).

## Terms

| Term | Means | Where it lives | Not |
|---|---|---|---|
| stage | One position of ShipLoop's graph: intake through release-verify, and `improve`. A packet assigns one stage. | `stage` in state and results | a step |
| step | One implementation step of a step plan, `S<n>`. An inline run issues one implement packet per step. | step-plan `steps` | a stage |
| work item | One unit of the plan's queue, `W<n>`, built through the inner stages. | plan `work_items` | an open item; a duty item |
| packet | What ShipLoop prints for the current stage: its duties, inputs, result template and callback. Only ShipLoop's print is a packet: the Until Loop's record is its receipt, and what the runtime prints at each step is an instruction. | `RUN/packets/<action>.md` | a receipt; an Until Loop instruction |
| head | The printed part of a packet longer than the print limit. Every print, a head or a whole packet, ends with the line `=== end ShipLoop print ===` (the print marker); a print without it was cut. | `PRINT_LIMIT`, `HEAD_LIMIT`, `HEAD_END` | the whole packet file |
| field file | The whole text of a model-written field that a packet's required block prints cut, because it passes the block's print budget; the block names the file. No gate refuses a field for its length. | `RUN/fields/<action>-<field>.md`; `STEP_TASK_PRINT`, `STEP_PROOF_PRINT`, `STEP_CRITERIA_PRINT`, `concerns.ROWS_PRINT`, `layers.LINES_PRINT` | a refusal; a result file |
| callback | The one command a packet prints to submit the stage's result: `complete --run-dir … --action …`. A refusal says "run the same callback again". The CLI verb stays `complete`. | "Callback for this stage"; an Improve stage's `Next command (` or `2. When the improve skill has completed, run:` | the Until Loop's `next_argv` and `done_argv` |
| shiploop check | The verb `shiploop check`: would ShipLoop accept this result now? It runs the same gates as `complete`, accepts and counts nothing, and records one answer, yes or no with the reason, that `complete` takes while nothing it read has changed. | `RUN/checks/<action>.md`; "the check says yes" | `complete --check-only` (removed); the Until Loop's exit checks |
| outcome | `done`, `blocked`, `send-back` or `add-work`. | result `outcome` | |
| blocked | An outcome only a person or an outside service can end; it names its wait in `awaiting`. A missing tool or a broken command is repair work, never blocked. | `awaiting` (answer, present, service) | the Until Loop's `continuation_assessment` value |
| send-back | An outcome that returns the work item to the stage that wrote its plan (its destination); no count of send-backs stops it. | `send-back` | |
| requirement | A spec entry, `R-<n>`, in KNOWLEDGE/spec.md, holding its acceptance lines. | `follows`, a case's `requirement`, `unverified[].requirement` | a criterion |
| primary requirement | A requirement that carries one of the request's primary outcomes: what the user asked for directly. The spec stage records them once; a script cannot infer primacy. | spec `primary` | |
| suite requirement | A primary requirement that a recorded command's own run observes rather than one case: a test suite ("the tests run with node --test"), a deploy ("the project deploys to the org"), or a check ("no access token is committed"). At the last work item's test-spec, every primary requirement needs a case naming it in some item's current test-spec, or a `suite_requirements` row `{"requirement": "R-<n>", "command": "<a recorded test command>"}` (TS1). ShipLoop refuses a missing one, naming it, a row whose requirement has no current spec entry, and a command no step plan records. A run whose step plans record no test command is not asked. | test-spec `suite_requirements` | a case |
| lower-layer check | The executed check below the e2e layer that shows an unverified outcome's logic works: a unit or component test. For a primary requirement it is the ID of a test that ShipLoop ran and saw pass in a case for that requirement; otherwise it may be the reason none exists. | `unverified[].lower_layer_check` | a check row; the Proof |
| acceptance line | One condition inside a requirement: what must hold, how it is confirmed and where it is observed. An inline step's implement or document stage may add acceptance lines inside an existing requirement. | inside `R-<n>` in spec.md | a criterion |
| criterion | A step plan's completion condition, `C<n>`, with its `confirm`; a step's exit condition names the criteria assigned to it. | step-plan `criteria`, a case's `criterion` | a requirement; an acceptance line |
| confirm | How a criterion is confirmed: `executed` (a recorded command runs the behaviour; a text search does not), `searched` (a command searches text the item writes) or `inspected` (it names an unverified `test_layers` row by `code` and `layer`). | criterion `confirm` | the chain item statuses; Backchain's confirm levels |
| Proof | A step's own command, which ShipLoop runs at the step's done. | `steps[].proof` | a check row; an expectation check |
| check | A command judged by its exit code: an expectation's read-only check, a probed assumption's probe, the service-is-back check, and a `check` row of the recorded commands (lint, type and build in `test_commands`; an exit-code check in `system_commands` and `consumer_checks`). | `expectations[].check`, probed `assumptions[].check`, `awaiting.check`, suite `check` | the Proof; settle |
| test command suites | `focused` (this item's cases, by ID), `regression` (the retained suites the change affects), `check` (a command judged by its exit code, with no test IDs). | `test_commands[].suite`, `system_commands[].suite`, `consumer_checks[].suite` | |
| settle | What a person or a later stage does to close an open item or an unverified outcome, and what they report back. It is not a command ShipLoop runs. | open `assumptions[].settle`, `unverified[].settle` | a check |
| test layers | Which harness tests each part of the code at each layer. The rows are `{code, layer, harness, status, reason}`; the layers are `unit`, `component` and `e2e`; the statuses are `available`, `prerequisite` and `unverified`. All code has a unit or component row, and only an e2e row may be unverified. | test-strategy `test_layers` (`test_layers_na`) | a surface |
| harness run | Prepare's proof that a prerequisite harness runs: the command that ran one test, and its saved output. | prepare `harness_runs` | |
| surface | Where a requirement is observed: a public interface, a real boundary or a rendered UI. | "required surface", "checked surface" | the `test_layers` rows |
| target | A runtime place where the code is deployed or tested. A target that keeps state says how a test still fails on an item's base there. | test-strategy `targets` (`keeps_state`, `base_state_route`) | an NFR's bound; a send-back's destination |
| base run | ShipLoop's run of the focused and regression commands on the step's base, where every test ID new at this step must fail (RED). `red-check` runs it without counting it. | `base_check`, `red_na` | an expected failure |
| RED | The failure a new test must show on the item's base, because the behaviour is missing. | test-spec `red` | an expected failure |
| expected failure | A baseline failure that a repair is planned to fix. | test-strategy and discovery duties | RED |
| remote test | A test that runs against a deployed target (remote-resident), listed by a platform card under `## Remote tests`. The base run and the mutation check skip it and record why. It is one kind of real-boundary check. | `references/platforms/*.md` | |
| KNOWLEDGE | The committed knowledge home, `docs/shiploop/`: spec, environment and architecture. Later runs inherit it. | symbol `KNOWLEDGE/` | a private store |
| commit stage | The last part of a step's iteration, ShipLoop's own and no graph stage: in the call that accepts the step's document stage or its review, it commits the step's code, tests, docs, knowledge and review edits as one `feat(<item>/<step>)` commit on the step's base; the step advances only once that commit lands. | `RUN/iterations/<item>.json` (`pending`, `commit`) | the review's commits (none inside a step); verify (retired) |
| knowledge record | A document result's `knowledge`: each living file with what the step changed in it or why nothing. The step commit prints it as its Knowledge home section. | document `knowledge` | the knowledge home itself |
| private store | An authorized place outside the repository for sensitive locators. | intake duty 3 | KNOWLEDGE |
| open item | What is left for a person or a later stage: who does what and what they report back (`settle`). It is an open `assumptions` row where the result has that list, else a summary entry. | `assumptions`, or the summary | a work item |
| due stage | The later stage where an open item or an unverified outcome must be settled. | `assumptions[].due_stage`, `unverified[].due_stage` | a due item |
| due item | The work item that settles one of the plan's open assumptions (the plan has no later stage to name). | the plan's open `assumptions[].due_item` | a due stage |
| consumer | The person or system that uses what the run delivers: its entry, its checks and its delivery contract. | `consumer_checks`, `consumer_entry`, `consumer` in a delivery contract | an open item's due stage |
| Until Loop | The loop each inner stage, and each Improve child, runs until its exit conditions hold. Its record is the receipt. | `Contract:` and `Receipt:` lines | |
| receipt | The Until Loop runtime's record of one run, rewritten at every step and final when its status is complete or stopped: an inner stage's `loops/<action>-terminal.json`, an Improve child's `CHILD/packet.json`. Only the runtime writes it; ShipLoop checks it against the contract it wrote. What the runtime prints at each step is an instruction to follow. | `--receipt`, `Receipt:` | a packet |
| exit conditions | What must hold for a stage to be done, listed under "Done when". | `Done when:` | |
| Improve stage | The `improve` action, with its own id, that ShipLoop issues after a reviewed stage: a reviewed planning result (by `planning_review`), each step's accepted document stage (rule `item`: one review of the step's code, tests and docs before ShipLoop commits the step) and the last carry-forward. A result "starts an Improve stage". Its callback is `complete --action=<improve id>`. | stage `improve`, the Improve stage's id | the Improve review; the Improve child |
| regression test line | The `Regression test:` line of an end-of-work review (carry-forward) commit that changes code, not only tests: the test in the same commit that fails without the fix, or `none: <why no test can show it>`. improve-commit refuses the commit without it; step and planning reviews owe none. | the improve-commit message | a regression command; the Proof |
| Improve review | The work an Improve stage does: the improve skill's passes over the reviewed result, which end at the first trivial pass. | `review-<n>.md`, `checks.md` | the Improve child |
| owner note | What the run's owner writes to a running run with `note`, `N<k>`: one file, written once. Packets quote it until it is delivered. | `RUN/owner-notes/N<k>.md` | a reply to a blocked question (`RUN/decisions/`); the model's own notes (`RUN/notes/`) |
| held callback | A callback ShipLoop refuses once because an owner note its action's packet did not print whole is waiting. It prints the note; the same callback then goes through. It refuses nothing the model submitted and is counted apart from refusals. | `RUN/owner-notes/shown.json` (`held`) | a refusal |
| delivered | Said of an owner note: ShipLoop accepted a step whose packet showed the note whole. Only the script marks it; the step's summary says what was done about it. | state `owner_notes` | shown (printed, perhaps only by a held callback) |
| Improve child | The Until Loop child runtime an Improve stage runs its review in: its frozen contract (`start.json`), its live state and the folder the handoff names CHILD. ShipLoop binds and starts it at the transition; it is active, blocked, stopped or complete, and a stopped one restarts (or, the plan's, reconciles). | `active_improve`, CHILD (`.shiploop-improve/<stage>-<id>/`) | the Improve stage; the Improve review |

**Separate schemas.** These keep their own words and are not ShipLoop terms:
- Backchain's confirm levels (`execute`, `inspect`, `unconfirmable`) and its `repair`/`revise` passes;
- the Until Loop's own fields and file names (`continuation_assessment`, `repeat_condition`, `packet.json`), and the
  vendored runtime's text, which calls its record a packet;
- two records ShipLoop also calls a receipt: the Improve import record (`improve/<action>/receipt.md`) and the
  reconciliation receipt the model writes for `improve-reconcile`. The reconciliation's archive checks
  (`shiploop_planning_revision.py`) still say "terminal packet" for the archived child receipt, so that file is the one
  allowed to;
- the Run Review page's stored documents, whose unverified rows keep a `check` column for what ShipLoop names `settle`.

## Retired terms

`test/shiploop-retired-terms.test.py` reads the block below. A retired term may appear only in the files its `allow`
lists, such as the refusal that tells a model it is retired. `pattern` is a regular expression, searched in
`SKILL.md`, the references, the command cards, the scripts and the Improve skill's ShipLoop route files.

```json retired-terms
[
 {"retired": "expected-RED (a baseline repair)", "use": "expected failure", "since": "2026-10-24",
  "pattern": "expected[- ]RED", "allow": []},
 {"retired": "Revise (an outcome)", "use": "send-back", "since": "2026-10-18",
  "pattern": "\\*\\*Revise\\*\\*|report revise", "allow": []},
 {"retired": "repeat and replan (outcomes)", "use": "next reprints a packet; send-back or add-work", "since": "2026-10-18",
  "pattern": "`replan`|`repeat` or `blocked`", "allow": []},
 {"retired": "blocked_by", "use": "awaiting", "since": "2026-10-18",
  "pattern": "blocked_by", "allow": ["skills/shiploop/scripts/shiploop_navigator.py"]},
 {"retired": "org-bound test", "use": "remote test", "since": "2026-10-24",
  "pattern": "org-bound", "allow": []},
 {"retired": "authorized knowledge home (a private store)", "use": "authorized private store", "since": "2026-10-24",
  "pattern": "authori[sz]ed knowledge home", "allow": []},
 {"retired": "producer step (a stage)", "use": "producer stage", "since": "2026-10-24",
  "pattern": "producer step\\b|Rules for every step|Step result", "allow": []},
 {"retired": "HOME (the knowledge symbol)", "use": "KNOWLEDGE", "since": "2026-10-18",
  "pattern": "(^|[^$A-Za-z_{])HOME/", "allow": []},
 {"retired": "a step's check (its Proof)", "use": "proof", "since": "2026-10-24",
  "pattern": "step's check\\b|its check in the step plan|own `check`", "allow": []},
 {"retired": "an open item's or unverified outcome's check (how it is settled)", "use": "settle", "since": "2026-10-24",
  "pattern": "open item's `check`|`check` = who does what|the `check` its owner", "allow": []},
 {"retired": "acceptance criteria (inside a requirement)", "use": "acceptance lines", "since": "2026-10-24",
  "pattern": "(?i)acceptance criteri", "allow": []},
 {"retired": "a step's requirement (its criterion)", "use": "criterion", "since": "2026-10-24",
  "pattern": "requirement assigned to this step|requirements that have been stated|requirement's Confirm-by", "allow": []},
 {"retired": "an open item's consumer (where it is settled)", "use": "due_stage, or at plan due_item", "since": "2026-10-24",
  "pattern": "`consumer` = |\\bas `consumer`|consumer work item|open: `consumer`|an open assumption's `consumer`|whose consumer is", "allow": []},
 {"retired": "complete command (the callback)", "use": "callback", "since": "2026-10-24",
  "pattern": "(?i)same complete command|the complete command|callback command|completion call\\b", "allow": []},
 {"retired": "=== end ShipLoop head === (the print marker)", "use": "=== end ShipLoop print ===", "since": "2026-10-24",
  "pattern": "=== end ShipLoop head ===", "allow": []},
 {"retired": "terminal packet (the Until Loop's record)", "use": "receipt", "since": "2026-10-24",
  "pattern": "(?i)terminal packet|Until Loop packet|child packet", "allow": ["skills/shiploop/scripts/shiploop_planning_revision.py"]},
 {"retired": "Improve child (for the Improve stage or its review)", "use": "Improve stage; Improve review", "since": "2026-10-24",
  "pattern": "\\b(?:start|starts|starting|started) (?:an|no) (?:actual )?Improve\\s+child|Improve\\s+child(?:'s)? (?:reviews|applies|evaluates)|no Improve\\s+child (?:starts|runs|reviews)|Improve\\s+children", "allow": []}
]
```
