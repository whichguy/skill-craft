# Script checks for the nine stages that end on the model's word — proposal, 2026-10-26 (awaiting the owner's decision)

Owner, 2026-10-26: "propose script checks for the nine stages whose exit is the model's judgement, product-acceptance
first, for my decision before building." Nothing here is built.

The owner's rules this keeps:
- the script confirms each step's exit, and the model only reports (memory `shiploop-purpose`);
- every exit is a confirmation condition (`shiploop-lint-exit-criteria-2026-09`);
- loops end on their criteria, never on a count (`shiploop-loops-unbounded`).

Evidence: `docs/experiments/judgement-stage-checks-20261026/` (the citation measurement and its script), and today's
saved runs `20261026/live-sonnet-battleship-01b9b3` (Sonnet 5.5, ShipLoop 1.15.0) and
`20261026/ds-flash-978478-battleship` (DeepSeek flash).

## 1. Where the nine stand today

The Run Review catalog (`skills/shiploop-run-review/defaults/stages.json`, `exitCheck`) calls nine stages "model
judgement": intake, discovery, research, prepare, product-acceptance, release-check, release, operations, handoff. It
reads only `complete_runs` and `improve` in the stage table (`shiploop_stage_spec.Stage`). A sweep of the navigator
shows that three of the nine have real gates when their result is submitted:

| stage | gate today, beyond the checks every stage gets | what no script checks |
|---|---|---|
| product-acceptance | `unverified` rows: exactly the seven fields, a current `R-<n>` in spec, a later `due_stage`; for a primary requirement, `lower_layer_check` must be a test that passed in ShipLoop's own `tests/<action>-verify<N>.md` (`shiploop_unverified.check_submitted`, `shiploop_primary.check_unverified`) | the other half of its done-when: that every request outcome *was observed by an executed check* |
| prepare | `harness_runs` for each prerequisite test layer, its output readable as a test run (`layers.check_harness_runs`, `layers.check_harness_output`); the knowledge close | the runners of the other planned checks |
| handoff | a verified, current workspace return (`shiploop_protocol.workspace_completion_guard`); the `unverified` restatement; the knowledge close | the per-area status and that its test status matches the last recorded run |
| release-check | the restatement rule only (marked delivery-contract runs add `_require_release_ready`) | the dry run and the confirm commands |
| release | the restatement rule only | the released identity and the grant |
| operations | the restatement rule only | monitoring, recovery and support |
| intake | none (`request_file.notices` prints a notice for an uncited request sentence, and the result is still accepted) | that every request sentence maps to an outcome, a boundary or an open question |
| discovery | none | that the baseline suite ran on the unchanged checkout |
| research | none | its unknowns and access needs |

Every stage gets: the result's shape (`_canonical_result`), that each `evidence_refs` path exists
(`_check_submitted_evidence`, existence only), a blocked result naming what it awaits, and add-work needing new item IDs.

The sweep also found three gaps that cut across stages:
- **X1. Open items due at a stage are not checked.** `assumptions.open_items` marks them settled as soon as that stage's
  done is accepted; nothing checks that the stage dealt with them.
- **X2. Research cannot record what its done-when asks for.** Research must record "each proven access need … as an
  open item", but `assumptions` is refused at research (`assumptions.STAGES` holds none of the nine).
- **X3. `prepare`'s `harness_runs` has no reader** after prepare.

## 2. The kinds of check

A check confirms a record. It never judges prose. There are three kinds:
- **Coverage:** every item in a list ShipLoop owns is answered. Example: every request sentence `S<n>` in
  `RUN/request.md`, which ShipLoop writes itself.
- **Evidence:** a cited test or command passed in a run ShipLoop recorded, on the tree being accepted.
- **Rerun:** ShipLoop runs, once, a recorded command that a plan marks read-only, and reads its result itself.

Where a check needs a fact, the result carries it in a small structured field rather than prose for the script to
parse. A failed check refuses done and names what is missing and the exit (fix it, list it in `unverified`, add-work),
as `complete_runs` do today. No count stops the loop.

## 3. product-acceptance (first)

Done-when today: "every request outcome was observed by an executed check, or is listed in unverified with its reason,
owner and due stage", and "missing product work is routed as add-work".

**What the two battleship runs show** (`pa-citations.txt`):

| run | request sentences | sentences the result cites | test IDs cited | in ShipLoop's verify records |
|---|---|---|---|---|
| Sonnet 5.5 | S1–S5 | S1–S5 | 14 | 14 |
| DeepSeek flash | S1–S5 | none (it numbered "(1)", "(2)") | 3 | 1 |

Two of DeepSeek's three cited IDs, `SYS-SUITE-1` and `SYS-UI-2`, appear only in files the model wrote: its results, its
Improve reviews and `environment.md`. No test or ShipLoop record names them. `SYS-UI-2` is described there as "three
manual procedures … not run at this stage". DeepSeek covered it by writing and running its own probe,
`RUN/scratch/acceptance/probe-ui.js`. So today's "every outcome observed" can rest on checks no script saw, and a
prose parser would find no sentence IDs at all on DeepSeek. Hence a structured field, not parsing.

**Proposed checks:**
- **PA1, coverage.** A new field, `observed`: one entry per request sentence, `{"sentence": "S3", "checks": ["TC-13",
  "TC-14"]}`, or `{"sentence": "S5", "deferred": "R-7"}` naming an `unverified` row. The script requires every `S<n>`
  from `RUN/request.md` exactly once, and every `deferred` requirement to have its `unverified` row. Refusal: "S4 is
  neither observed nor deferred".
- **PA2, evidence.** Each ID in `checks` must have passed in a run ShipLoop recorded. That reuses the reader
  `shiploop_primary.check_unverified` already uses (`passed_cases`, from the verify records), widened to the records
  that hold system tests (decision D4). Refusal: "SYS-UI-2 passed in no run ShipLoop recorded: run it through a recorded
  command, or list S3 in unverified."
- **PA3, the tree being accepted.** The passing records must be for the candidate tree: no product file changed since
  the run that recorded them. To confirm before building: whether the verify records carry the tree or commit they ran
  on. If not, they need to.
- **PA4, probes run at this stage.** A check product-acceptance runs itself, like DeepSeek's `probe-ui.js`, counts only
  as a recorded run. It goes in `harness_runs`, which today is allowed only at prepare, with its command and an output
  ShipLoop can read (`layers.check_harness_output`), or ShipLoop reruns it once (decision D3).

**What stays the model's judgement:** whether the cited checks really observe what the sentence asks for. That remains
for Improve or a person to judge.

**Predicted effect:** Sonnet's result passes unchanged apart from the new field. DeepSeek's is refused until `SYS-UI-2`
runs through a recorded command or `S3` is deferred. That is the intended catch.

## 4. The other eight

Ranked by value. Each line gives its kind and what it needs.

| id | stage | check | kind | needs |
|---|---|---|---|---|
| RL1 | release | The released identity exists. For a source return, it equals the identity in the script-written return receipt (or the template prefills it). For another target, a read-only identity command from release-plan confirms it. | evidence / rerun | release-plan to name an identity command for non-source targets (to confirm) |
| RL2 | release | The grant: the result cites a grant record (an `Access and accounts` entry in `KNOWLEDGE/environment.md` naming this target, or intake's boundary when the request names the target), or a not-applicable with reason when release-plan planned no release | coverage | a `grant` field |
| RC1 | release-check | ShipLoop runs each post-release confirm command once on the source checkout and on the candidate. The source must show "not there yet" and the candidate must pass. Sonnet's model did exactly this by hand ("exit 1 in the source checkout, exit 0 in the candidate"). | rerun | release-plan's confirm commands as a list (to confirm) |
| RC2 | release-check | Each release precondition release-plan names is observed, with evidence | coverage | release-plan's preconditions as a list |
| X1 | every stage | A stage with open items due must answer each by ID: settled with evidence, or carried with a reason | coverage | an `open_items` answer field, or reuse of `assumptions` |
| IN1 | intake | Turn the existing notice into a refusal: every request sentence `S<n>` is cited. Both runs already cite all five. | coverage | nothing new (`request_file.notices` computes it) |
| DI1 | discovery | The baseline: the cited baseline output must show a test run ShipLoop can read, with "missing coverage" allowed when no suite exists (Sonnet: `node --test` exited 0 with 0 tests). Or ShipLoop reruns the baseline command once on the unchanged checkout. | evidence / rerun | the baseline command and output as a `harness_runs`-style row |
| HO1 | handoff | Source, test, release and consumer status each present, each with evidence | coverage | a `status` field with four keys |
| HO2 | handoff | The test status matches the last recorded run. For example, Sonnet's "56 tests, 54 pass, 2 skipped" must equal what the records show (`test_loop.observed_lines`). | evidence | HO1's test entry |
| PR1 | prepare | Widen `harness_runs` from the prerequisite layers to every planned check's runner ("each planned check's runner starts") | evidence | nothing new |
| X2 | research | Allow research to record access needs as open items, which its done-when requires | (fix) | `assumptions.STAGES` |
| OP1 | operations | Monitoring, recovery and support each confirmed (a command and output ShipLoop can read) or not-applicable with reason. A rollback recipe's target commit exists. ShipLoop runs no recovery command itself. | coverage / evidence | an `operations` field with three keys |
| RE1 | research | `RUN/notes/research.md` exists and lists each unknown discovery kept open, with its resolution or owner | coverage | discovery's unknowns as a list |

What stays judgement: whether a precondition, an open question or a support channel is the *right* one. The checks
confirm that each is answered and evidenced, not that the answer is wise.

**One catalog fix**, whatever is chosen: the Run Review catalog's `exitCheck` should show a fourth kind, "submit gate",
for prepare, handoff and product-acceptance's `unverified`. Today it calls them model judgement.

## 5. Decisions for the owner

- **D1. The principle.** Checks confirm records and never judge prose. Agree, or name where judgement should stay.
- **D2. Small structured fields** (`observed`, `grant`, `status`, `operations`, open-item answers) instead of parsing the
  summary. DeepSeek's result shows that parsing fails. Recommended.
- **D3. Reruns.** May ShipLoop itself run commands a plan marks read-only (release confirm commands, a baseline, a
  probe)? Recommended for confirm commands and baselines. Probes are recorded rather than rerun.
- **D4. Which records count as "executed and passed"** for PA2: the verify records only, or also system-test and
  release-verify runs. Recommended: every test record ShipLoop wrote itself, never a file the model wrote.
- **D5. Build order.** Recommended phases:
  - phase 1: IN1, PA1–PA3, X1;
  - phase 2: RL1, RL2, RC1, DI1, HO1, HO2;
  - phase 3: PA4, PR1, X2, OP1, RE1.

  Each check gets a fail-first test and a replay on today's four saved runs (Sonnet and DeepSeek, hello and
  battleship): honest results are accepted, and DeepSeek's acceptance is refused as predicted.
- **D6. Placement.** The checks run at `complete`, like `complete_runs`, so the Until Loop's terminal check and the
  refusal text carry them. A new `complete_runs` name per check (`coverage`, `observed-evidence`, …) makes them visible
  in the stage table and the catalog.
