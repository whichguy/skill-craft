# Implementation conventions in the existing ShipLoop loop

## Outcome and boundary

Discover the implementation practices that fit the product and environment,
select them during planning, and apply the relevant subset in every inner work
item. Preserve host judgment, script-owned traversal, and the existing Improve
campaign boundaries. This is prompt guidance, not a new graph node, result
field, policy engine, package dependency or claim of model compliance.

Use the committed repository at `64255ed` as the isolated implementation base.
The original checkout also contains pending cross-run knowledge, environment and
workspace guidance. Do not absorb those changes or depend on their untracked
references. Integrate this addition with them without replacing their content.

## Prompt audit

### Q1 — Is discovery sufficient without an inner reminder?

**Info-gain: 0.9** — Resolves where the implementation decision survives a cold
context and a later work item.

**Evidence:** At base `64255ed`, `shiploop_navigator_prompts.py:225` discovers
repository/environment/skills; `:323` plans code, tests and skill reuse without an
explicit conventions selection. `shiploop_navigator.py:829` renders an existing
work-item `context`, and `:820` directs recovery from accepted records.

**Answer:** Discovery establishes evidence; planning selects applicable practices
and retains their locator; the inner prompt reads and revalidates them. Reuse
existing `context`, `evidence_refs`, project documents and accepted records.
Keep work-item context to a short locator/decision summary because the renderer
prints it verbatim. Missing or inaccessible locators require accepted-record and
canonical-source recovery, then targeted discovery for unresolved prerequisites.

### Q2 — Does consistency mean copying existing code?

**Info-gain: 0.8** — Prevents stale or unsafe precedent from becoming authority.

**Evidence:** The implementation constitution in
`references/testing-and-documentation.md` already prefers local conventions and
established tooling. It also preserves user requirements and behavior contracts.

**Answer:** Distinguish binding requirements, supported defaults and proposals.
Check product purpose, runtime/dependency versions, canonical code/test examples,
MCP/API contracts and selected skills. Retain source, scope, rationale and useful
checks. Record justified departures; investigate material conflicts. Tool or
skill availability does not require adding a product dependency or integration.

### Q3 — How much retained guidance is useful?

**Info-gain: 0.7** — Avoids a duplicated general coding manual in every packet.

**Answer:** Keep a concise section in an existing appropriate project document
or durable discovery/plan notes, linking authoritative examples. Create a focused
project document only when none fits and reuse warrants it. Load the relevant
subset; re-investigate changed assumptions rather than repeating all discovery.
The optional document belongs to the authorized target project; this change adds
no separate ShipLoop conventions guide or mandatory global policy file.
The [Anthropic context guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
supports focused references and canonical examples. The
[AGENTS.md evaluation](https://arxiv.org/abs/2602.11988) provides contrary evidence
to blanket context expansion; no token savings or behavioral benefit is assumed.

## Remediation and execution

1. Extend discovery/spec/plan duties: discover practices, preserve binding
   constraints, select conventions and retain locators in existing plan evidence
   and work-item context. Resolve material uncertainty proportionately.
2. Extend shared implementation-quality guidance and inner planning: read the
   relevant conventions, recover absent locators from accepted discovery/plan
   records, revalidate changed assumptions and carry decisions into delegated work.
3. Give existing Improve campaigns an explicit consistency/exception review
   question. Retain validated conventions during documentation and carry-forward.
   Update the navigator reference, constitution and skill contract without adding
   a separate normative guide or a new campaign.
4. Extend existing both-protocol traversal/cold-recovery tests with semantic
   assertions. Exercise existing conventions, a changed dependency and a
   conflicting convention through synthetic current-action packets and an
   independent interpretation check. A missing directive must fail its targeted
   check. Never compare whole prompt bytes or claim synthetic completion proves
   actual implementation quality.
5. Regenerate package views in the isolated worktree, run focused tests, lint,
   parity and the core group. Review the diff independently, then preserve
   unrelated pending work while committing, merging and pushing this scope.
   Verify the delivered SHA's complete CI result.

Observed commands: `python3 -B test/shiploop-navigator.test.py`,
`python3 -B test/shiploop-navigator-dry-run.test.py`,
`python3 -B skills/shiploop/scripts/shiploop graph-dry-run`,
`ruff check skills/shiploop/scripts/shiploop_navigator_prompts.py test/shiploop-navigator.test.py`,
`bash scripts/sync-plugin-views.sh --check`, and
`bash test/run-all.sh --group core` with a private `TMPDIR`. CI runs the full
ShipLoop group and the required aggregate. Do not change CI limits or test scope
to make this prompt change appear green.

## Learnings and limits

- A library/framework contract constrains product code; an MCP tool or skill
  often constrains how the agent obtains evidence or performs work. Keep these
  roles distinct and select only what the current task needs.
- Existing work-item context already survives cursor recovery. An absent locator
  should trigger targeted reading of accepted records, not invented practices.
- Published baseline and pending local guidance differ. Tests and delivery claims
  must identify which candidate was checked.
- Mechanical packet tests verify delivery and recovery. Independent fixture
  interpretations test a few decisions, not universal model adherence or a
  measured improvement in code quality.

## Verification record

The implemented candidate passed 27 navigator tests, including both protocols,
two work items, and cold `step-plan` recovery for existing, changed, conflicting
and absent convention locators. Four navigator dry-run tests, all eight simulated
graph routes, six related delivery-prompt checks, the core hermetic group, Ruff,
package parity and diff checks passed. A test-only in-memory removal of the
`Project conventions:` cue caused the intended assertions to fail in both
protocol subtests; it was not retained in the candidate.

Independent review found two handoff gaps and the implementation addressed both:
the shared cue now applies to the current assignment even without an active work
item; `plan-improve` explicitly preserves or updates convention locators when it
replaces the queue. No traversal code, state fields, result schema or Improve
convergence mechanism changed.

A fresh read-only agent also interpreted four fictional cold packets without the
separate grading oracle. It selected the existing unittest pattern, rejected an
obsolete dependency API in favor of the pinned interface, rejected full-state
logging that conflicted with current redaction requirements, and recovered an
omitted locator from accepted plan evidence. It proposed targeted checks and
kept implementation prerequisites distinct from planning blockers. These are
bounded observed choices, not a compliance rate, token benchmark, executed code
check or proof that durable decision notes were written. Fixtures and raw local
logs are retained under `/tmp/shiploop-conventions-evidence`; full remote CI is a
separate post-push delivery check.

## Concurrent-main reconciliation

The first normal push found remote `main` had advanced to `621534a` with
independent marketplace and CI work. Reconcile that committed work in the
isolated worktree and retain its test sharding and packaging changes. The remote
already used ShipLoop `0.10.3`, so the combined conventions package is `0.10.4`.
Recheck package parity, navigator tests and core checks on the combined candidate;
preserve unrelated local pending content during the final main integration.
