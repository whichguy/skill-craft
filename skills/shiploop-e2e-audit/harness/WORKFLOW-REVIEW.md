# Review the workflow, not only the generated game

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
   resolve to the explicit `xhigh` default, not an unknown host default. Record
   operator overrides and any documented native equivalent separately. A native
   tool without an observable effort control is not proof of inherited `xhigh`.
2. Reconstruct accepted stages from durable Markdown and correlate each start,
   callback, and return with captured tool completion. Do not treat a command
   mention, compound-shell exit, or a completed-looking file as execution proof.
3. Compare the original platform/consumer requirements with discovery, research,
   spec, plan, implementation, deployment, hosted verification, and handoff.
   Find scope drift, assumptions that became facts, missing dependencies, or
   local adapters that conceal target-runtime incompatibility. For a full game
   case, inspect the configured MCP staging and guarded promotion receipts,
   `scriptId`, version/deployment identities, published `/exec` URL, and
   candidate-to-release linkage. A local fixture, `/dev` URL, model mock, or
   model prose cannot satisfy hosted delivery.
4. Reconcile every selected test with what ran. Check expected versus observed
   results, current-candidate identity, evidence paths, and all blocked/unrun/N/A
   cases. For `authorized-deployment` and `hosted-game-behavior`, inspect the
   candidate-bound observation, raw MCP receipts, and browser trace rather than
   accepting only a receipt schema pass. A later independent pass cannot
   retroactively justify an earlier ShipLoop completion that lacked the evidence.
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
