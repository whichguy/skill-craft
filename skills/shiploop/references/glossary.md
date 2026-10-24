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
| packet | What ShipLoop prints for the current stage: its duties, inputs, result template and callback. | `RUN/packets/<action>.md` | the Until Loop's `packet.json` |
| head | The printed part of a packet longer than the print limit; it ends with the head marker. | `PRINT_LIMIT`, `HEAD_LIMIT` | the whole packet file |
| callback | The one command a packet prints to submit the stage's result: `complete --run-dir … --action …`. R4 unifies the refusals' "complete command". | "Callback for this stage" | |
| outcome | `done`, `blocked`, `send-back` or `add-work`. | result `outcome` | |
| blocked | An outcome only a person or an outside service can end; it names its wait in `awaiting`. A missing tool or a broken command is repair work, never blocked. | `awaiting` (answer, present, service) | the Until Loop's `continuation_assessment` value |
| send-back | An outcome that returns the work item to the stage that wrote its plan (its destination), at most twice per destination. | `send-back` | |
| requirement | A spec entry, `R-<n>`, in KNOWLEDGE/spec.md. R2 makes requirement and criterion one meaning each. | `follows`, a case's `requirement` | a criterion |
| criterion | A step plan's completion condition, `C<n>`, with its `confirm`. | step-plan `criteria` | a requirement |
| confirm | How a criterion is confirmed: `executed` (a recorded command runs the behaviour; a text search does not), `searched` (a command searches text the item writes) or `inspected` (it names an unverified `test_layers` row by `code` and `layer`). | criterion `confirm` | the chain item statuses; Backchain's confirm levels |
| Proof | A step's own command, which ShipLoop runs at the step's done. | `steps[].proof` | a check row; an expectation check |
| check | A command judged by its exit code: an expectation's read-only check, a probed assumption's probe, the service-is-back check, and a `check` row of the recorded commands (lint, type and build in `test_commands`; an exit-code check in `system_commands` and `consumer_checks`). | `expectations[].check`, probed `assumptions[].check`, `awaiting.check`, suite `check` | the Proof; settle |
| test command suites | `focused` (this item's cases, by ID), `regression` (the retained suites the change affects), `check` (a command judged by its exit code, with no test IDs). | `test_commands[].suite`, `system_commands[].suite`, `consumer_checks[].suite` | |
| settle | What a person or a later stage does to close an open item or an unverified outcome, and what they report back. It is not a command ShipLoop runs. | open `assumptions[].settle`, `unverified[].settle` | a check |
| test layers | Which harness tests each part of the code at each layer. The rows are `{code, layer, harness, status, reason}`; the layers are `unit`, `component` and `e2e`; the statuses are `available`, `prerequisite` and `unverified`. All code has a unit or component row, and only an e2e row may be unverified. | test-strategy `test_layers` (`test_layers_na`) | a surface |
| harness run | Prepare's proof that a prerequisite harness runs: the command that ran one test, and its saved output. | prepare `harness_runs` | |
| surface | Where a requirement is observed: a public interface, a real boundary or a rendered UI. | "required surface", "checked surface" | the `test_layers` rows |
| target | A runtime place where the code is deployed or tested. A target that keeps state says how a test still fails on an item's base there. | test-strategy `targets` (`keeps_state`, `base_state_route`) | an NFR's bound; a send-back's destination |
| base run | ShipLoop's run of the focused and regression commands on the item's base, which must fail there (RED). `red-check` runs it without counting it. | `base_check`, `red_na` | an expected failure |
| RED | The failure a new test must show on the item's base, because the behaviour is missing. | test-spec `red` | an expected failure |
| expected failure | A baseline failure that a repair is planned to fix. | test-strategy and discovery duties | RED |
| remote test | A test that runs against a deployed target (remote-resident), listed by a platform card under `## Remote tests`. The base run and the mutation check skip it and record why. It is one kind of real-boundary check. | `references/platforms/*.md` | |
| KNOWLEDGE | The committed knowledge home, `docs/shiploop/`: spec, environment and architecture. Later runs inherit it. | symbol `KNOWLEDGE/` | a private store |
| private store | An authorized place outside the repository for sensitive locators. | intake duty 3 | KNOWLEDGE |
| open item | What is left for a person or a later stage: who does what and what they report back. It is an open `assumptions` row where the result has that list (with its due stage; R3 renames `consumer` to `due_stage`), else a summary entry. | `assumptions`, or the summary | a work item |
| due stage | The later stage where an open item or an unverified outcome must be settled. | `unverified[].due_stage`; `assumptions[].consumer` until R3 | |
| Until Loop | The loop each inner stage runs until its exit conditions hold. Its terminal record is the receipt. | `Contract:` and `Receipt:` lines | |
| exit conditions | What must hold for a stage to be done, listed under "Done when". | `Done when:` | |
| Improve stage | The `improve` action ShipLoop issues after a reviewed stage. R4 settles stage, review and child. | stage `improve` | |
| Improve review | The work an Improve stage does: the improve skill's passes over the reviewed result. | `review-<n>.md` | verify's review gate |

**Separate schemas.** These keep their own words and are not ShipLoop terms:
- the ask-agent chain worker's item statuses (`confirmed`, `inspected`, `failed`, `not_run`, `unconfirmable`);
- Backchain's confirm levels (`execute`, `inspect`, `unconfirmable`) and its `repair`/`revise` passes;
- the Until Loop's own fields (`continuation_assessment`, `repeat_condition`);
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
  "pattern": "open item's `check`|`check` = who does what|the `check` its owner", "allow": []}
]
```
