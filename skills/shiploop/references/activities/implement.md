# Per-step execution planning, implement, and Improve loop

Work only in the active step worktree named by the action packet. The session
checkout remains the eventual local merge target. Do not re-root the whole
session, edit the session checkout during a step, force-remove a worktree,
auto-resolve conflicts, or stage everything with git add -A.

## Initial execution plan and implement

The first `implement`-phase action after scheduling is `step-plan`, not a
source edit. Draft the initial plan for the active step, then complete:

```text
step-plan → step-plan-review → step-plan-revise → step-plan-verify
→ step-plan-commit → (another review or step-plan-finalize) → implement
```

Every nested pass is evidence-backed and audit-only; two consecutive
trivial-only, checked, committed passes with no open findings permit the fresh
finalization check. `step-plan-finalize` releases only that exact candidate to
`implement`. Read [Execution-plan convergence](../execution-planning.md) for
the ten-dimensional rubric, bounded cold context, state paths, and
incorporated continuation policy.

Only after finalization, implement the active step's stored prompt and exact
`produces`. Suppliers and initial state are assumptions to validate, not work to
repeat. If evidence exposes a broader defect, preserve it for review/post-inner
rather than rewriting the frozen DAG in place.

Use [Test cases](../testing-and-documentation.md#test-cases),
[Documentation](../testing-and-documentation.md#documentation), and
[Iteration](../testing-and-documentation.md#iteration) for the canonical
host guidance. They use the current result fields and evidence flow; they do
not add a semantic-proof mechanism or a new result schema.

Read the active product flow/transition slice from the durable spec and linked
model, including adjacent affected paths. Apply
[Traceability and review](../behavioral-requirements.md#traceability-and-review):
carry requirement/flow/transition IDs into cases and concise documentation,
compare expected states and effects with actual evidence, and record changed
rules or a no-change reason each Improve cycle. Missing required behavior is a
material finding. Do not silently rewrite frozen acceptance to fit the code;
broader compatible work goes to pending-only replan and incompatible changes
require user direction.

For every source-editing implementation pass after the initial plan finalizes:

1. Create or expand behavior/contract tests mapped to every produces value.
   When the step authors client–service communication, tests must cover the
   real client invocation path and its page-side conventions, not only a
   substitute exec of internal functions. See
   [Client–service invocation](../survey.md#clientservice-invocation).
   Keep stable case IDs, exact criterion/output mappings, preconditions/input,
   selector/command, and expected observable outcomes in the applicable
   product test documentation; actual observation and evidence remain distinct.
2. After each production edit, run all applicable lint: destination-writer
   lint/validation where available, repository-configured lint, and suitable
   existing syntax checks. Destination syntax rules win over generic rewrites.
3. Build an explicit manifest with a concrete lint entry and required test
   entries. Each produces value appears in a test acceptance list. Select any
   browser/service/API check by risk and surface, not because every layer is
   mandatory.
4. Run verify. A failing, timing-out, tree-changing, stale, or
   manifest-mismatched result is not evidence; fix and re-run. A required case
   or environment-dependent check that is unavailable is blocked, never `N/A`
   or passed.
5. Complete implement only after a fresh successful verification record and a
   test_review explain the coverage, actual evidence, and limitations.

The script persists logs and failed attempts. Never put secrets in a command,
test output, result, or manifest; logs are evidence artifacts and exact output
may be retained.

Document changed public functions/interfaces and non-obvious boundaries with a
concise contract rather than restating types, signatures, or source code.
Review the product README in every Improve cycle: update it or record why it
is unchanged, then exercise changed runnable examples and validate relevant
links before verification. Product docs live in the product worktree and Git;
they must not contain ShipLoop session state. Use the existing `body`,
`test_review`, `test_changes`, and `summary` to link those durable decisions
and evidence rather than inventing fields.

## Improve iteration

Each iteration follows this fixed order. Its post-review plan is not applied
after one draft: it receives the same nested convergence gate as the initial
step plan.

1. **Review.** Fully page `context --section knowledge` for the active step and
   run history before completing the review, then record the matching
   `knowledge_read` revision, digest, and scope in the review result. Read
   complete commit bodies for the latest ten commits or all available commits,
   using one full body page at a time when context is small. If audit-only plan
   commits dominate that window, also inspect the relevant older implementation
   or decision commit through a scoped path/symbol investigation. Review code, tests,
   regressions, declared acceptance, case expected-versus-actual outcomes,
   documentation, product README, current obligations/blockers, and prior
   learnings. Supply the explicit `research_assessment` described in
   [Later discoveries](../research-loop.md#later-discoveries): do new conditions,
   contradictions or best-practice questions require investigation? Required or
   blocked research is material, not an empty/trivial review. A step tagged
   `activity: research` also supplies the full `research_review` rubric. The
   review opens `improve-plan`; it does not authorize product edits for its
   findings.
2. **Converge the Improve plan.** `improve-plan` drafts a concrete plan covering
   every finding, necessary test/documentation changes, prevention, and expected
   outcomes. Read the `enclosing_review` block within the `step-context`
   section and explicitly retain every
   printed `PARENT-…` finding ID in that draft. This proves the plan covers each
   parent review finding; it does not claim the product finding is resolved
   before `improve-apply`. Then complete:

   ```text
   improve-plan → step-plan-review → step-plan-revise → step-plan-verify
   → step-plan-commit → (another review or step-plan-finalize) → improve-apply
   ```

   Every `step-plan-review` re-inspects the actual implementation/diff,
   environment, direct dependencies and consumers, flows, edge conditions,
   second-order effects, implicit requirements, test strategy, and documentation
   with compact durable evidence. A plan can proceed only after two consecutive
   trivial-only nested passes, no open findings, and fresh planning checks with
   exact acceptance `step plan`. Nested plan passes do not count as Improve
   iterations or replace the later primary Improve commit.
3. **Apply.** Implement the finalized plan with its code, tests, contracts, and product
   documentation. Mark material truthfully: a material finding or application
   resets the trivial streak even when the textual diff is tiny. Resolve required
   research with durable answers and supporting evidence before verification;
   unresolved authority or unavailable required evidence needs a pause.
4. **Verify.** Run fresh lint and every required test. If tests force another
   edit, lint and test again. Verify changed examples/links where applicable.
   A late file edit during verification is treated conservatively as material
   and restarts convergence. Passing local checks do not prove a remote,
   deployed, or external effect.
5. **Carry forward.** After the successful verification record, complete the
   printed `carry-forward` action before any primary commit. Submit an explicit
   no-discovery result or bounded non-secret discoveries, using the current
   expected knowledge revision. A current-step repair returns to review; a
   pending replan retains a durable obligation; a pause cannot be bypassed by
   resume. See [Carry-forward checkpoint](../carry-forward.md).
6. **Commit.** Make one new primary commit at worktree HEAD. It is not a main
   branch commit and includes concrete Review, Changes, Validation, and Key
   learnings sections, ending with the exact ShipLoop iteration trailer.
   For an Improve-routed step plan, ShipLoop carries the deduplicated nested
   review/revise learnings into the enclosing iteration; include those plus the
   ordinary review, apply, and carry-forward learnings verbatim. An audit-only
   allow-empty commit is permitted but must still record real evidence.

Two fully recorded trivial-only iterations are necessary before final verify.
The nested plan passes that precede implementation or Improve application do
not count toward that streak. There is no maximum iteration count that becomes
success. Final verify runs a fresh manifest on the final tree. Post-inner then asks whether broader
dependencies, preparation, tests, the plan, or open carry-forward obligations
need changing. When pending-replan obligations exist, it must provide
`pending_obligation_map` entries whose nonempty step lists cover each affected
scope with newly added or actually changed pending DAG work. These entries only
schedule the work; ordinary execution and tests still prove it. Do not let a
later checkpoint or an outer replan silently clear an obligation.

When the outstanding obligation is research, create an explicit
`activity: research` report/decision producer and make affected pending consumers
depend on its result. That producer uses this same tested two-pass Improve loop;
it does not bypass tests because its output is Markdown. Record the question,
source/version or observation time, conclusion, applicability and revalidation
policy. A useful source recommendation is not authorization to change the
approved writer, requirements, permissions or external environment.

If a real defect appears after commit, final verification, or post-inner, use
repair before merge intent starts. It records the defect, resets convergence,
and returns to review. If the session checkout has advanced, integrate its
current HEAD into the worktree first, then repair and complete two new converged
iterations; do not merge a branch validated against an obsolete session baseline.
Once merge intent has been recorded, current repair rejects the request. Inspect
Git and the pending merge; do not rewrite the branch or promise repair is still
available. See the [known recovery gap](../../README.md#six-known-current-implementation-gaps).
