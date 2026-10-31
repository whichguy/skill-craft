# Review the workflow, not only the generated application

The experiment's purpose is to find supported improvements to ShipLoop while
preserving one-shot behavior. After each trial, copy `workflow-review-template.json`
to its external evidence directory and complete it with cited observations. This
is an analyst's review artifact, not an automated certificate or additional DAG.
Freeze the completed review with the trial, skill, harness, candidate, and baseline
identities. A later interpretation or parser replay gets a separate artifact;
retain the original result and explain why the interpretation changed.

## Review procedure

1. Read the literal prompt and frozen selected package. Confirm which request,
   installed source, model, effort, budget, and repository the trial actually used.
   Separate requested settings from observable effective parent/child settings.
   Audit every model shell-out, including the outer operator, review-only
   sessions, and independent reviewers. ShipLoop's scripts must not start nested
   Grok, Claude, or Codex workers; record any such launch as a workflow deviation.
   Omitted effort in the external harness must
   resolve to the explicit `xhigh` default, not an unknown host default; a
   reviewer running on a Claude model defaults to `medium` instead. Record
   operator overrides and any documented native equivalent separately. A native
   tool without an observable effort control is not proof of the requested level.
2. Reconstruct accepted stages from durable Markdown and correlate each start,
   callback, and return with captured tool completion. Do not treat a command
   mention, compound-shell exit, or a completed-looking file as execution proof.
3. Compare the original platform/consumer requirements with discovery, research,
   spec, plan, implementation, deployment, hosted verification, and handoff.
   Find scope drift, assumptions that became facts, missing dependencies, or
   local adapters that conceal target-runtime incompatibility. For a full game
   case, inspect the platform-specific candidate-to-release and hosted evidence
   defined in [CASES.md](CASES.md). For GAS, inspect the configured MCP staging
   and guarded promotion receipts, `scriptId`, version/deployment identities,
   published `/exec` URL, and candidate-to-release linkage. For Salesforce,
   inspect the pinned target preflight, raw Salesforce DX deployment result,
   candidate-to-deployed metadata mapping, and authenticated Lightning route
   and behavior trace. A local fixture, GAS `/dev` URL, model mock, or model
   prose cannot satisfy hosted delivery.
4. Reconcile every selected test with what ran. Check expected versus observed
   results, current-candidate identity, evidence paths, and all blocked/unrun/N/A
   cases. For GAS `authorized-deployment` and `hosted-game-behavior`, inspect
   the candidate-bound observation, raw MCP receipts, and browser trace rather
   than accepting only a receipt schema pass. For Salesforce
   `salesforce-authorized-deployment`, `salesforce-source-candidate`, and
   `salesforce-hosted-lightning-behavior`, inspect the candidate-bound
   observation, raw DX deployment result, source mapping, and authenticated
   Lightning trace. A later independent pass cannot retroactively justify an
   earlier ShipLoop completion that lacked the evidence.
5. Inspect substantive Improve notes: current candidate, findings and material
   changes, check refresh, distinct qualifying reviews, independent reviewer
   availability/scope or fallback limitation. Do not infer review quality from
   a clean-review count or demand new script-owned review state.
6. Inspect recovery and output hygiene: failed starts, repeated commands without
   new evidence, loss of decisions across stages, leftover app variants, source
   return, and whether durable locators support a fresh context. For feature
   runs, inspect actual before/after hosted behavior, reachable source lineage,
   and reuse of the original Apps Script project instead of a replacement app.
7. Measure overhead from timestamped events and one terminal usage aggregate.
   Separate bootstrap, planning/review, implementation, verification, and return.
   Do not add streaming usage chunks or child durations to terminal totals.
   Identify useful material corrections before calling review time waste.

## Key questions for every run

Use these lenses while inspecting actual events and outcomes. Map answers onto
the existing dimensions below: cite evidence in their `notes`/`evidence`, or
retain `unverified`/`not-applicable` with a reason. Record findings only when
warranted; a checklist is not a novelty quota or an automated quality certificate.

| Existing dimension | Questions to critique |
| --- | --- |
| `literal-request-and-selected-source` | Did the actual skill/source honour the intent? What unexpected expectation, discovery or contrary evidence could materially change our position? Separate a missed requirement from a proposed new requirement. |
| `platform-and-consumer-contract-preserved` | Did planning surface assumptions, risks, dependencies and usable acceptance criteria? Was scope and decomposition appropriate, and did implementation follow authorised intent? |
| `dag-execution-and-callback-attribution` | Did skill instructions, script inputs/results and returned prompt templates fit together? Were output purpose and callbacks clear? Would a changed stage, gate or template address an observed cause without weakening a guarantee? |
| `planned-tests-reconciled-with-observations` | Were the checks discriminating, negative cases meaningful and claimed methods actually executed? Did required real-runtime or UI evidence exist, and did passing checks cover all frozen obligations? |
| `improve-evidence-and-reviewer-scope` | Did review improve a material outcome? Which stage or gate caught useful defects, missed them or caused avoidable rework? Compare smaller alternatives before proposing a new or removed gate. |
| `recovery-return-and-context-hygiene` | Could a fresh context continue the same action from durable evidence? Did recovery preserve decisions and avoid replaying work, especially when `done` was missing? |
| `incremental-behavior-and-source-lineage` | Was the implementation correct, maintainable and verified on its actual target? Were prior behaviour, tests, knowledge and source lineage retained? |
| `performance-and-model-settings-observable` | Where did planning, implementation, review, verification and handoff spend resources? Could a change improve quality first, then measured cost/time, without shifting cost elsewhere or hiding useful work? Distinguish measured rework from an estimate. |

At campaign level also ask: **What task family or failure mode remains materially
unobserved, and which repeatable case would distinguish it? Can the test be
repeated safely with verified cleanup?** Record these in the existing campaign
inventory/coverage plan and `harness_reflection`, not new dimension IDs.

## Reflect on the harness

After the workflow findings, answer three questions about the harness and
record them in `harness_reflection`, each with an evidence-based answer and
concrete proposals (possibly none):

- **Learning retention:** should the harness retain key learnings or keep state
  in a different way (for example what a later pass or a fresh operator could
  not reconstruct from this trial's retained files)?
- **Further learning:** is there something more we could learn from during
  subsequent passes (a signal captured but unused, a comparison not made, a
  variable not held fixed)?
- **Evaluation criteria:** are more evaluation criteria needed to re-evaluate
  ShipLoop's efficacy (a behavior this run showed matters that no check or
  dimension measures)?

Keep these separate from ShipLoop findings: they change how the next trial is
run and judged, not the skill under test.

## Findings and follow-up experiments

For each finding record the concrete trigger, observed behavior, supporting
artifact/line, ownership (ShipLoop, model, host, observer, or product), consequence,
confidence, contrary evidence, smallest proposed change, and the next falsifiable
test. Include failures and interrupted attempts in the campaign denominator;
partial smoke and full product runs answer different questions.

Prefer correcting a proven script defect or a focused prompt/reference rule.
Preserve Markdown authority and the fixed SDLC traversal. A new gate, state model,
integration, or removed stage needs evidence that a smaller change is inadequate.
Do not inject workspace flags, callback calls, verifier advice, or repairs into
the model run. An opt-in contract or altered prompt is a separately labeled
campaign, not a silent improvement to the baseline experiment.

Pilot changes individually against the same literal request, comparable initial
repo, skill snapshot, host settings, and budget. Check quality first, then tokens
and elapsed time. Repeat enough times to distinguish a stable improvement from
model variation; use the reserved holdout only after the proposed change is fixed.
Retain a partial-suite regression for the earliest affected stage and a full
create/feature regression when the claim concerns delivered behavior or lineage.

`result.json` remains the runner's catalog/structural verdict. Report the manual
workflow finding summary alongside it; an automatic `passed` is not a claim that
ShipLoop's review decisions or evidence were flawless. Suite summaries are the
execution-time snapshot; a later independent `grade` updates the individual
trial. Consult its current `result.json` and preserve the prior snapshot.

## Campaign checkpoint

These are operator instructions for an explicitly authorised improvement
campaign; the reviewer supplies evidence and proposals, not edits or launches.
Use the existing campaign inventory/AUDIT and linked learning, coverage and Git
records. Keep durable locators for a fresh operator; append interpretations
instead of overwriting prior trials. The repository harness's normative counterpart
is its `SPEC.md` Rules for the harness itself; packages do not require that checkout.

1. **Reconcile and plan together.** Before planning the next trial or change,
   search recent and older Git history by affected behaviour, paths and
   referenced decisions. Read full relevant messages, including failed,
   reverted and empty learning commits, and the full scoped learning backlog.
   Group related observations by causal hypothesis and existing learning ID;
   combine reviewer feedback into one prioritised plan with dependencies,
   alternatives and disagreements. Keep ShipLoop, product, host and evaluator
   causes distinct. One qualified candidate addresses one learning record;
   do not bundle unrelated fixes to obtain an attractive aggregate score.
2. **Test a falsifiable claim.** Before an experiment, state the observation,
   hypothesis, expected change, refuting result, protected quality/fidelity,
   governing cost metric, tolerance/budget and control/candidate identities.
   Use a focused slice, replay or isolated experiment first when it can cheaply
   distinguish explanations. Reject only the claim that evidence actually
   refutes; a weak proxy result is inconclusive. Narrow probes cannot qualify
   end-to-end benefit. Before adoption use the selected harness's existing
   strict comparison gate (`promotion/5` in the repository harness); if absent,
   keep the result a pilot, not a qualified win. Keep only measured cost/benefit
   wins with quality protected; rejected/undecided changes restore the baseline
   and retain verbose learning without rewriting original evidence.
3. **Choose coverage deliberately.** Start with the exposing case and include
   a generality case of another style for qualification, or explicitly narrow
   the claim when that coverage is unavailable. Record observed/unobserved
   families and why each next case adds useful evidence. Add or modify a
   repeatable case for a material blind spot, saturation or realistic failure
   mode: freeze intent, initial state, checks/negative controls and cleanup.
   Calibrate it before use. Case/evaluator changes take effect between
   comparisons; never regrade an old result into a win. Domain/UI behaviour
   belongs in case adapters. No fixed all-case or novelty quota applies.
4. **Verify repeatability.** Declare owned local and remote resources before
   launch. After all owned work/deployments end, verify applicable cleanup of
   processes, ports, scratch, records, schema and deployed artifacts, including
   on failure/interruption. Preserve other apps, user data, raw evidence and
   verified incremental predecessors. Missing safe cleanup support is a limit,
   not permission for broad deletion. Unknown cleanup blocks target reuse;
   fresh context/folders do not establish deployed-state restoration.
5. **Continue or report the real stop.** Continue within recorded campaign
   authority while a material actionable idea or coverage gap has a useful
   investigation. A script stop ends that invocation. Respect explicit limits,
   budgets and deployment permissions; do not evade them or blindly retry, and
   do not request permission again for covered work. A cap, non-promotion streak,
   empty findings or invalid/missing measurements is not convergence. Inspect
   the full backlog, including material deferred/owner items, not only a
   truncated prompt excerpt. Report blocked, budget-limited or awaiting-owner
   work with its reopening condition. Converge only within a named scope after
   a complete critique, justified coverage, evidence-backed dispositions, no
   material actionable investigation, and completed required checks/cleanup.

For every completed run or bounded experiment, follow the card's **Learning
commits and history** rule: retain reproducible failure scenarios, measurements,
contrary evidence, unknowns and full influential hashes with their contribution.
An unqualified or rolled-back candidate restores the baseline and leaves a
verbose empty learning commit, preserving original commits and raw external
evidence. Keep rejected candidate/journal files out of the source repository.
For retained wins, use the authorised main/CI, release, refresh and published
build verification path before the next iteration. A green application,
harness repair, passing unit suite or accepted idea alone is not a ShipLoop
improvement.
