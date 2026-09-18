# State and data obligations in initial planning

## Decision and scope

Make applicable state/data obligations visible when architecture, specifications
and NFRs become the initial plan. Use existing reference sections, work-item
context, evidence locators and standalone Improve handoffs. Do not add a graph
stage, result field, status ledger, parser for semantic completeness, external
integration, or automatic data/deployment action.

The guidance targets a concrete distinction: intended-user access cannot be
established by an assignment for any user, and valid local transitions do not
alone establish safe persistent writes. The [synthetic planning fixtures](../test/experiments/shiploop_state_planning/README.md)
exercise these boundaries, including a memory-only scope control. They are not
evidence of a live-org defect or a reason to add persistence to a memory-only app.

## Implementation plan

1. Reuse the requirements reference for a compact state/data applicability
   assessment and initial-plan reconciliation. Preserve accepted architecture
   and requirements; separate transition correctness from workload/scale NFRs.
2. Route selected sections into spec, test strategy, initial/step planning,
   carry-forward and release planning. Review the affected slice in the already
   assigned Improve invocation; preserve source/test locators for cold recovery.
3. Add an identity-specific negative example to existing behavior/dependency
   guidance. Keep authored files, applied state, actual records and observed
   consumer behavior separate. Require only real prerequisites.
4. Verify packet routing and recovery first, then run fresh planning sessions
   against synthetic repositories with a frozen separate rubric. Regenerate the
   plugin view through the repository script and run the hermetic aggregate.
5. Run the actual standalone Improve skill against this implementation, retaining
   its durable review evidence and two consecutive qualifying review cycles.

## Acceptance and boundaries

- Applicable architecture constraints, requirements, NFRs and mutations map to a
  responsible work item, prerequisites, tests and relevant release/recovery
  conditions, or remain explicitly excluded/unresolved with reasons.
- No persistent storage, new permissions, numerical SLA, deployment topology or
  platform capability is invented to complete a checklist.
- Scripts still supply one current action and retain navigation state. The model
  reasons about adequacy; successful routing cannot establish semantic coverage.
- Conditional migration/rollout criteria include target identity, compatibility,
  observable promotion/stop conditions and data/access rollback limits.
- All user checkout changes remain untouched; this implementation is isolated
  from concurrent consolidation and makes no Salesforce calls.

The experiment README defines the validation procedure; completed trial results
belong in the task's evidence and a separately identified result summary. Semantic
samples are bounded observations, not statistical reliability or live platform
verification.

## Experiment findings

Two fresh prompt-only drafts were scored against the separate frozen rubrics:
the memory utility met four of five obligations and the import projection met
four of six. These drafts did not execute the predecessor graph or Improve.
The misses remain in the experiment record; successful prompt routing did not
establish plan quality.

The actual standalone Improve skill then reviewed the import draft, using the
independently identified omissions as review leads. It inspected the previously
omitted test source and added explicit invalid-transition
coverage, completed two consecutive no-change reviews, and reached runtime
`done`. Independent rescoring against the unchanged rubric passed all six
obligations. This is evidence that Improve repaired this planning artifact,
not proof of implementation, workload performance, deployment, or general
reliability.

A separate reviewer audited the memory rubric without seeing planner outputs.
It found the mandatory empty-list test stronger than the literal-list request
requires; preserving existing label display remains a justified regression
obligation. Keep the original scores and disclose this calibration limit.
Future rubric versions should separate required behavior from recommended
robustness checks rather than revise a frozen rubric to fit an observed result.

The supporting run artifacts are retained locally outside the repository:
[first-draft scorecards](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/focused-judgments.md),
[Improve record](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/import-improved/improve-report.md),
[final import scorecard](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/import-improved-judgment.md),
and [rubric audit](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/rubric-boundary-review.md).
These local paths are audit locators, not portable runtime dependencies.

Both runtime pilots traversed intake, discovery, research, specification, test
strategy and initial planning, invoking and importing the actual standalone
Improve skill after each producer. Each exercised a cold Plan-to-Improve
recovery and stopped at the assigned, unexecuted `prepare` action. These are
bounded prelude walks, not completed product deliveries:
[memory pilot](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/memory-live/pilot-report.md),
[CRM pilot](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/crm-live/pilot-report.md).

Independent CRM scoring passed all five frozen obligations, including intended
staff identity, conditional entitlement authority, explicit staff/admin/denial
tests and the no-release-target boundary. The reviewer inspected the plan's
linked durable specification/test artifacts and excluded the later compatibility
clarification from this run's inputs.
[CRM scorecard](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/crm-live-judgment.md).

The completed memory plan still replaced the existing CLI label display while
preserving its internal helper. Independent final scoring remained four of five
raw obligations; the consumer regression is valid even after separating the
empty-list calibration issue. This motivated the short additive-change
compatibility clarification in Initial-plan reconciliation. Original request
and observable baseline behavior outrank an earlier agent's self-authored
acceptance. The clarification was applied only after both pilots finished;
their results do not validate that later wording.
[Final memory scorecard](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/memory-live-final-judgment.md).

A separate, lead-guided standalone Improve repair used the proposed clarification
and a copy of the original inputs. Its independently reviewed plan preserves the
default label command and adds `python3 minute_tally.py total`, with checks for
both consumer paths. The raw frozen score remains four of five solely because
it omits the overstrict empty-list case; the actual compatibility defect is
repaired. This is targeted plan-repair evidence, not a fresh full-prelude result
or a claim that default Improve always finds a regression. The linked report
and runtime record retain the completion evidence independently of this summary.
[Repaired plan scorecard](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/memory-repair-judgment.md),
[repair review record](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/memory-repair/improve-report.md).

## Verification record

The complete hermetic aggregate passed before the final compatibility paragraph.
After that reference-only clarification, the current seven guidance/recovery
tests, eight reference-routing tests, scoped Ruff, generated-package check and
diff whitespace checks passed. No runtime implementation, graph or schema changed.
The aggregate ran the earlier six-test guidance inventory; the added fixture
preflight is included in the separately passing seven-test run. Disposable
bytecode caches were removed; durable Improve records stay ignored and trial
artifacts remain outside the checkout.
[Aggregate receipt](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/aggregate-completion.json),
[current guidance results](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/final-guidance.log),
[current reference results](/Users/dadleet/Documents/Codex/experiments/shiploop-state-planning-implementation-20260918/final-references.log).
