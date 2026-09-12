# Execution-plan convergence

## Loop contract

Plan before the first implementation and before every Improve application. A
step is not ready to code merely because its dependency DAG node is ready, and
an improvement plan is not ready merely because one LLM pass produced it.

```mermaid
flowchart TD
  D[Draft the step or improvement plan] --> R[Review current evidence and plan]
  R --> A[Revise the plan and resolve findings]
  A --> V[Run plan lint and tests]
  V --> C[Record a verbose audit commit]
  C --> G{Two trivial passes and no open gaps?}
  G -->|No| R
  G -->|Yes| F[Fresh checks then implementation or Improve apply]
```

`step-plan` drafts the initial implementation plan. `improve-plan` drafts the
plan for one existing Improve iteration. Each uses `step-plan-review`,
`step-plan-revise`, `step-plan-verify`, `step-plan-commit`, and
`step-plan-finalize`; these are stored stages in
phase `implement`, not new dependency DAG steps. Research, behavior and spec
retain their own upstream loops. Initial `sequence` is a generic objective
candidate with the same receipt-derived two-trivial-pass and fresh-final-check
discipline; it is not a dependency DAG step or evidence that product code passed.

The incorporated until-loop policy computes **readiness**, not success, from
unique completed, verified and audited passes in the current repair epoch.
Material findings or revisions reset the trivial streak. Any exact candidate
byte change, including whitespace-only changes, is conservatively material.
Only retaining the exact persisted candidate can be a trivial Apply. This may
require extra passes because ShipLoop has no semantic-equivalence oracle; it is
a safety rule, not a claim that every byte change changes product meaning. Two
consecutive trivial-only passes, with all trivial fixes applied and no open findings, permit
fresh final checks. A failed, blocked, timed-out or stale check cannot advance.
Neither an LLM `done` claim nor a cycle budget is an alternate success route.
Finalization releases only the exact checked plan for its designated next action.

## Local microplan and backchain

The global DAG orders delivery steps. Within the selected step, draft a compact
**execution microplan** in the existing Markdown `body`: local ID, work and
observable output, prerequisite/source, evidence reference, and planned case or
check. Order rows by their actual dependencies, not merely file order. One row
is sufficient for simple work; a no-change Improve plan can name inspection and
fresh checks with its no-change reason. Do not invent edits or recursive subtasks.
Retain the required sequence of code, post-code test refinement, lint/tests and
documentation; a no-change plan still needs the mandatory fresh checks.
If a required lint/test check has no established permitted command, retain a
readiness blocker and investigate within scope. Do not waive mandatory lint or
substitute a syntax/import probe for it; new tools or access need authorization.

Before coding, reverse-walk **each required output and its verification needs**:

1. **Claim and needs:** what must become true, and what must exist to implement
   and verify it? Include fixtures, interfaces, authorized environment, failure
   paths, and relevant downstream consumers.
2. **Supply:** cite an inspected current fact or an earlier local row that will
   produce inspectable evidence. Check selected-step Ready criteria, global
   supplier artifacts and initial facts against current evidence. A criterion,
   prior claim, installed tool, or planned check is not proof of readiness,
   authorized access, a populated fixture, or a passing result.
3. **Resolve:** reuse the actual supplier; clarify its local output; add only
   necessary in-scope local work; otherwise retain a material unresolved finding.
   Never close a need with an assumption, a circular dependency, or future work
   that has not run. Then walk forward once to check that each row can execute
   using established facts and earlier outputs and that the required outcomes
   and cases are covered.

Repeat this check in the existing plan-review loop after each revision. Record
conclusions and safe evidence in `coverage_review.dependencies` and
`context_evidence.dependencies`; use existing findings for gaps. A missing
current prerequisite blocks application. If it needs a new global producer,
changed contract, writer or permission, pause for broader-plan direction rather
than finishing the active step to reach post-inner. Future-only compatible
impacts can use carry-forward/pending replan. Never rewrite the global DAG here.

Rows are planning content, **not** a second scheduler, schema, per-row completion
cursor, or external retry authorization. Do not invoke standalone Backchain or
until-loop. The script binds the complete Markdown candidate and gates the
enclosing action; the host judges dependency meaning and supplies meaningful
checks. No parser proves row completeness or dependency sufficiency. Recover the
accepted plan through `context --section step-plan`; on interruption inspect
actual files and external-operation evidence before continuing, never replay a
mutating row merely because it lacks a checkbox. Unknown outcomes need a pause.

## Contract disposition

A material `scope` or `behavior` finding routes to paused
`step-plan-disposition`. A plain `resume` only unlocks that action; it does not
resolve the finding or release the plan. If inspection demonstrates that the
finding was a false-positive contract-change diagnosis, complete the action with
exactly `summary`, `disposition: "no-contract-change"`, and
`resolutions: [{id, evidence}]` for every and only the listed contract blockers.
Explain concretely why the existing approved contract already permits the
required behavior. Do not change the candidate, product, DAG, or frozen contract
in this action.

The script records the disposition, archives the interrupted pass, resets
convergence in a new repair epoch, and returns to `step-plan-review`. Repair
cannot evade unresolved contract blockers; it returns to disposition. If the
contract really must change, halt this run and obtain the needed direction for
an explicitly replanned/new run. This gate does not implement in-place approval
of changed requirements, credentials, writers, or shared configuration.

## Cold-start evidence

At every pass assume the preceding LLM context is gone. Use `next`, then page
the current `step-context`, `step-plan`, `iteration`, and `knowledge` sections
as selected by the packet. Use the current step's prompt/produces, accepted
spec/behavior slice, frozen environment plus current knowledge overlay, and
direct suppliers/consumers. Follow references only as needed to inspect
transitive impacts. Do not load every archived pass or the whole repository.

For a cold `implement`, `improve-apply`, or `review`, page `context --section
step-plan` for the accepted criteria and `context --section step-context` for
the active step. When present, the latter includes a digest-bound read-only
`implementation_test_record`: accepted action, `summary`, and `test_review` from
`results/{implementation_check_action}.md`. It is a historical host-reported
note, not current code/test proof. Reinspect the actual diff and dependencies,
then run fresh required checks before relying on it.

For an Improve plan, the `step-context` section also carries `enclosing_review`
with the product findings, test review, learnings and research assessment.
Retain every printed `PARENT-…` finding ID in the candidate and explain the planned
response, expected outcome and check. Refine those planned responses throughout
the nested loop; do not confuse closing a **plan** gap with proving the product
finding fixed. Product application and verification have not happened yet.

Run current action-bound Git history and read the latest ten full bodies (or
all available) in pages. Audit-only planning commits can occupy those pages;
also retrieve relevant older implementation/decision commits using a scoped
path or symbol investigation when needed. Do not mistake ten recent audit
messages for the complete history of the code being changed.
Inspect the actual worktree: relevant functions,
interfaces, call sites, tests, configuration and diff. An initial step may have
no implementation yet; distinguish existing foundations from intended new work.
Do not claim to have inspected future files. Prior commits explain decisions;
they are not proof that current code or environment still matches them.

Record compact evidence references and conclusions, not raw source dumps:
`path:symbol`, test selector, stable requirement/case ID, non-secret probe record
or source/version/observation time. Distinguish observed, inferred, planned and
unknown. The script binds local artifacts; it cannot hash the live external
world. Recheck relevant remote readiness safely when needed, and pause if a
required observation or authority is unavailable. Never include secrets or
credential-bearing output.

Current implementation, context bindings, candidate and finding ledger cannot
change unnoticed between review and handoff. A changed assumption needs a new
review, not a retained clean streak. An environment observation does not grant
permission to change an approved writer, credential, shared setting or requirement.

## Review rubric

Every `step-plan-review` supplies a complete `coverage_review` object. Each value
must explain evidence, a concrete decision, or a justified inapplicability—not
just “reviewed.” The result also retains `context_evidence` for the actual
step, implementation, environment and dependency inspection.

| Key | Question to answer on every pass |
|---|---|
| `step_scope` | What exact stored prompt, outputs and acceptance does this plan implement? Which changes are explicitly out of scope? |
| `current_implementation` | What does the real code/configuration/diff do now, where will the change land, and which call sites or tests contradict the proposed approach? |
| `environment` | Are runtime, permitted writer, invocation conventions, deployment target, test fixtures and non-secret access assumptions valid now? Which observation needs revalidation? |
| `dependencies` | Reverse-check every microplan output and verification need to current evidence or an earlier local producer, then walk the forward order. Do Ready criteria and global supplier artifacts actually establish the needed state? Identify unresolved prerequisites, cycles, compatibility, shared resources and affected consumers; never treat a claim as evidence. |
| `flows` | Trace a concrete input through state, guards, calls and observable output. Do the normal, alternate and recovery flows agree with the approved requirement/transition model? |
| `edge_conditions` | Examine relevant invalid/empty/boundary/stale/duplicate input, timeout, cancellation, partial failure, retries, concurrency and recovery. Which cases are missing? |
| `second_order_effects` | What changes indirectly for consumers, persisted data, caches, permissions, resource use, deployment/rollback, observability or documentation? Which cross-step effects need a broader plan change? |
| `implicit_requirements` | What prerequisite or behavioral assumption is necessary but unstated? Identify its source and confidence. Do not silently convert an assumption into user-approved scope. |
| `test_strategy` | Before source code, map every exact `produces`/transition to a stable case ID and contract `T-` criterion, inputs, expected state/output/side effects, planned test path/selector, check ID, environment/fixture, and revalidation trigger. Decide unit/integration/end-to-end scope and mock/fake strategy separately from browser/service/API surfaces; each is selected, not applicable with a reason, or required but blocked with cause. A mock/fake cannot prove a required real boundary. Order readiness before checks and inspect check side effects/fixture isolation, including generated files and shared mutable state. |
| `documentation` | Which concise function/interface contracts, expected-outcome test records, README instructions, runnable examples and links must change—or why are they unchanged? |

Actively try to disprove the plan: reverse-trace the microplan outcomes to their prerequisites,
walk a failure/recovery trace, inspect an adjacent consumer, and challenge an
implicit assumption with evidence. Rotate the emphasis between passes while
retaining the full rubric. Rephrasing the same approval is not a new inspection.

Use stable finding IDs. All known unresolved findings remain in the ledger;
omission cannot close them or downgrade material severity. A missing required
test, transition, prerequisite or significant downstream effect is material,
regardless of textual diff size. Trivial means non-semantic polish. A genuinely
clean review may return no findings but still needs evidence, checks and audit.

Reserve material `scope` and `behavior` findings for a conflict with, or a needed
change to, the approved contract. A missing plan step for already-approved
behavior is normally an `implementation`, `flow`, or `edge-condition` finding.
Do not erase a contract conflict by renaming its category or finding ID. Keep
its original evidence until the explicit recovery path has recorded a disposition;
plain resume is not permission to change the contract.

## Revise and verify

Revise the **plan**, not product source. Explain how every open finding will be
addressed, then import the complete corrected candidate with resolution evidence.
Before code, keep a compact criteria matrix in the existing `body`/`plan`, not a
new catalog: stable case ID, mapped contract `T-` ID, exact `produces`,
inputs/preconditions, expected outcome, path/selector, check ID,
environment/fixture, and scope/surface decision.
Keep a concrete ordered edit/test/documentation sequence, target symbols,
expected outcomes, prerequisites, risk controls and revalidation triggers. An
empty finding set needs an explicit no-fix decision; do not invent work to fill
the loop.
Retain the complete execution microplan and backward dependency conclusions
through revision, including unresolved gaps and any changed evidence. A changed
prerequisite/order/output needs renewed review, not an inherited clean streak.

Required investigation must establish the facts needed to choose an executable
plan. If an unknown is intentionally a future research producer, consumers must
depend on its checked output. A plan to “figure out permissions later” is not
resolution of an execution-blocking authority gap. Pause for incompatible scope,
acceptance, writer or permission changes. Compatible broader work is recorded for
the existing carry-forward/post-inner pending-only revision path.

Run the printed `planning-verify` command with a Markdown manifest containing a
concrete lint check and tests mapped to exact acceptance **`step plan`**. Checks
should exercise real plan properties: complete output/case mappings, ordered
prerequisites, known interface names, expected-state records, example/diagram
syntax or consistency rules that the chosen representation can express. A file
existence check or an always-green command is not semantic validation.
For a microplan, checks can detect duplicate IDs, missing cited artifacts,
forward/circular local references and unmapped required cases. A reference to
a future producer is planned evidence, not a file that must already exist.
Do not substitute a heading-presence test for review of prerequisite truth.

Keep plan check helpers under the run inbox or otherwise outside product source;
creating them inside the worktree would change the plan's implementation baseline.
This gate validates the plan artifact—not the future implementation, nor a remote
environment. Product lint/tests remain mandatory after the later source edits.
Verify that the chosen tool invocation really preserves the bound worktree;
apparently read-only syntax/test commands can create caches or generated files.
Prefer non-mutating checks or explicitly isolated outputs instead of assuming a
flag suppresses all writes. Test fixtures must not leak state between cases.
Where two components could drift together, consider an independent assertion of
their approved interface contract: a passing integration path can still agree
on the wrong request shape or observable behavior. Select such checks by risk;
do not replace real integration coverage with mocks.

At `implement` or `improve-apply`, code comes before post-code test refinement:
inspect the actual diff, dependencies, and code learnings, then author or refine
tests from the pre-code matrix. A TDD or reused test needs evidence and an
adequacy rationale; do not manufacture an edit. In initial `implement`, a
correction's reason, before/after oracle, independent requirement/contract source,
and retained/added coverage belong in `test_review`. In Improve work, use
`test_changes` for application deltas, `learnings` for discoveries, and later
`test_review` for adequacy. Do not rewrite acceptance to fit a bug. Required
unavailable, failed, blocked, or unrun checks remain unfinished; passing evidence
still does not prove semantic test adequacy.
Follow the accepted microplan's dependency order within that one action. Record
actual local outputs/evidence and deviations in existing result `summary` and
`learnings`, not a separate progress ledger. Newly discovered execution-blocking
gaps require recovery/review or a pause, never silently expanding the plan.

Every completed plan pass has its own verbose audit-only direct-child commit,
with `Review:`, `Changes:`, `Validation:`, `Key learnings:` and the exact printed
iteration trailer. Preserve staged and uncommitted product changes using
`git commit --allow-empty --only`; never stage the run records. Include recorded
review/revision learnings verbatim and reference the candidate/check evidence.
The enclosing Improve iteration still needs its **separate primary commit** after
product application, lint/tests and carry-forward. Plan audits do not count as
trivial implementation iterations. Finalization carries the nested review/revise
learnings into the enclosing iteration's `plan_learnings`; include each verbatim
in that primary commit as well as the ordinary review/apply/carry-forward learnings.

### Example trace

Hypothetical input: “Add cancellation without changing completed jobs.” The
first plan pass inspects the actual handler and finds that its proposed write
could overwrite a completed result. It records material finding `F-CANCEL-01`,
the existing terminal-state guard, the affected notification consumer and an
expected-outcome case: cancelling an already completed job leaves its state and
notifications unchanged. The revised plan orders the guard and regression case
before the call-site update. Plan checks and an audit commit record that pass;
the material finding resets the streak even though the fix is one line of prose.

A fresh context then reviews the corrected candidate and current evidence. Two
subsequent genuinely trivial-only checked/audited passes, followed by fresh final
checks, release the implementation plan. A source or environment-record change
in between invalidates that path and needs repair/review. The planning test does
not claim that cancellation works yet: implementation and its product tests are
still the next activity.

## Phase-specific emphasis

The same risk questions recur without making every phase recursively contain
another planning loop. Read only the packet-selected section for the current action.

| Phase activity | Required emphasis |
|---|---|
| Research/behavior/spec review and planning | Current evidence, environmental applicability, requirement/transition breadth, dependencies and implicit assumptions; resolve contradictions before accepting the candidate. |
| Dependency sequence | Forward draft plus backward prerequisite audit, consumer effects, case/README work and preparation placement; its generic-objective candidate follows the two-trivial-pass and fresh-final-check gate. Do not invent producers. |
| Step plan / Improve plan | All ten rubric dimensions, actual code/diff/environment evidence, repeated plan refinement and checks before product edits. |
| Implementation / Improve apply | Follow the accepted scoped plan, preserve writer constraints, implement cases and concise docs, and route new material facts back through review/repair. |
| Product review / verify | Compare actual versus expected behavior, reassess adjacent consumers and test surfaces, and rerun lint/tests after edits. |
| Carry-forward / post-inner / outer quality | Persist cross-step observations, review downstream and second-order impacts, revise compatible pending work, and journal generic ShipLoop improvements separately. |

## Until-loop incorporation and limits

The user explicitly selected incorporation rather than a separate dispatcher.
`scripts/shiploop_until.py` adapts the standalone **until-loop 0.1.3**
repeat/verify/continue decision into a pure internal policy. The inspected local
source was `scripts/until-loop` at commit
`7fb7057056552438fa39ccf11b70fa7c63f80077`, declaring MIT in its skill card. No
remote or separate LICENSE file was present. This provenance identifies the
design source; it is not a runtime dependency or a multi-host execution claim.

Intentional changes from the standalone script:

- No `.until-loop/state.json`, independent lock, Git-exclude mutation or second
  CLI. ShipLoop's existing Markdown transaction remains the only state owner.
- The stop predicate is derived from unique checked/audited pass receipts,
  not a host's `--done` claim; finalization additionally requires fresh evidence.
- Replayed action results are idempotent, and cold continuation uses ShipLoop
  `next`, not a new standalone run.
- Cycle/budget exhaustion is unfinished; it cannot stand in for quality.

This is an incorporated adaptation, **not** execution of the unmodified external
until-loop skill. The installed standalone skill is left unchanged. The shared
receipt-derived policy now serves every current converging family: research,
behavior, and specification planning; generic approach/survey/sequence,
`preparation-readiness` (authorized observation/readiness, not an external-effect
loop), post-inner, coverage, and quality objectives; step-plan readiness; and
Improve iterations. Their candidates, checks, and completion effects differ, but
none may substitute a host claim, cycle budget, or mock-only result for its
required evidence.

Repeated review improves the opportunity to find gaps, not a proof of
exhaustiveness. The [planning self-critique study](https://arxiv.org/abs/2310.08118)
reports failures of unaided self-verification in evaluated planning tasks; that
motivates current-code inspection, meaningful checks and retained counterevidence.
The two-trivial threshold is the user's operational choice. The host remains
responsible for evidence quality, test adequacy and truthful classifications.
