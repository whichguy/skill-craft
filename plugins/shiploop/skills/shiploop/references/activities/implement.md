# Per-step implement and Improve loop

Work only in the active step worktree named by the action packet. The session
checkout remains the eventual local merge target. Do not re-root the whole
session, edit the session checkout during a step, force-remove a worktree,
auto-resolve conflicts, or stage everything with git add -A.

## Implement

Implement only the active step's stored prompt and exact produces. Suppliers
and initial state are assumptions, not work to repeat. If evidence exposes a
broader defect, preserve it for review/post-inner rather than rewriting the
frozen DAG in place.

For every implementation pass:

1. Create or expand behavior/contract tests mapped to every produces value.
   When the step authors client–service communication, tests must cover the
   real client invocation path and its page-side conventions, not only a
   substitute exec of internal functions. See
   [Client–service invocation](../survey.md#client-service-invocation).
2. After each production edit, run all applicable lint: destination-writer
   lint/validation where available, repository-configured lint, and suitable
   existing syntax checks. Destination syntax rules win over generic rewrites.
3. Build an explicit manifest with a concrete lint entry and required test
   entries. Each produces value appears in a test acceptance list.
4. Run verify. A failing, timing-out, tree-changing, stale, or
   manifest-mismatched result is not evidence; fix and re-run.
5. Complete implement only after a fresh successful verification record and a
   test_review explain the coverage and limitations.

The script persists logs and failed attempts. Never put secrets in a command,
test output, result, or manifest; logs are evidence artifacts and exact output
may be retained.

## Improve iteration

Each iteration follows this fixed order:

1. **Review.** Run history for the active action. Read complete commit bodies
   for the latest seven commits or all available commits, using one full body
   page at a time when context is small. Review code, tests, regressions,
   declared acceptance, and prior learnings.
2. **Plan.** Write a concrete improvement plan covering every finding,
   necessary test changes, and prevention.
3. **Apply.** Implement the plan. Mark material truthfully: a material finding
   or application resets the trivial streak even when the textual diff is tiny.
4. **Verify.** Run fresh lint and every required test. If tests force another
   edit, lint and test again. A late file edit during verification is treated
   conservatively as material and restarts convergence.
5. **Commit.** Make one new primary commit at worktree HEAD. It is not a main
   branch commit and includes concrete Review, Changes, Validation, and Key
   learnings sections, ending with the exact ShipLoop iteration trailer.
   Include review learnings and apply learnings verbatim. An audit-only
   allow-empty commit is permitted but must still record real evidence.

Two fully recorded trivial-only iterations are necessary before final verify.
There is no maximum iteration count that becomes success. Final verify runs a
fresh manifest on the final tree. Post-inner then asks whether broader
dependencies, preparation, tests, or the plan need changing; only pending work
may be revised.

If a real defect appears after commit, final verification, post-inner, or merge
intent, use repair. It records the defect, resets convergence, and returns to
review. If the session checkout has advanced, integrate its current HEAD into
the worktree first, then repair and complete two new converged iterations; do
not merge a branch validated against an obsolete session baseline.
