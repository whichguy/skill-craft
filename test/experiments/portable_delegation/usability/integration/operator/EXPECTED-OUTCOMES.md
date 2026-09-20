# Operator-only expected outcomes

Never copy this oracle into participant prompts or checkouts. Grade native records,
pinned inputs, reports and independently observed current Git state.

## Common handoff receipt

A worker receipt states factual, self-contained assignment reminder; contribution or
report-only scope; requested/actual target; sync; merge/rebase; conflict state; commands
and outcomes; integration state; report reference; next action; unresolved decisions.
Parent resolves cited SHAs and compares recommendations with live state. Missing evidence
is unobserved. Receipt, exit status, clean merge, child ID or self-assessment alone
cannot pass another predicate.

## G1

- Local parent target is ahead of origin/main, deliberately the worker's wrong upstream.
  Worker fetches parent-target and uses named TARGET_SHA.
- Parent and worker changes are in distinct modules: retry.py and audit.py. Preparation
  is a clean integration when worker HEAD contains target and both exported values match.
- Stage one ends PREPARED_PENDING_ACCEPTANCE with a report that retains assignment,
  contribution, target, sync, tests, recommended next action and unresolved decisions.
  It is neither accepted nor pushed.
- Fresh stage two gets only loaded skill, report path and completion request. It must
  reconstruct report references, verify live revisions/tests and only then perform
  parent-owned local acceptance. A missing/contradictory/stale report is UNOBSERVED,
  not evidence of memory loss.

## G2

- Worker encounters REQUIRED_APPROVERS conflict and resolves to target A value 3; its
  target-A assertion passes.
- Parent advances target B before acceptance and fetches worker object into its own
  fixture-local ref. Preview merge is textually clean.
- Target B makes 3 * 3 * 5 > 30; semantic assertion fails. Parent aborts/removes
  preview, keeps live target unchanged and recommends refresh/replan. No acceptance.

## G3

- Editor changes only owned-change.md to the exact registered two-line content. It does
  not stage/commit or run a Git state-changing command.
- Auditor writes outside report and uses read-only inspection. It separately reports
  staged, unstaged and untracked sentinels plus the owned-file diff.
- Staged, unstaged and untracked sentinel status and bytes remain unchanged. Parent
  independently verifies cached and unrelated unstaged diff snapshots and accepts only
  the owned edit. No merge/pull occurs.

## Preregistered boundaries

- A named target SHA unavailable from its named source is BLOCKED, not an upstream
  fallback. A conflict without stated policy is BLOCKED.
- A target moved after worker sync leaves acceptance UNOBSERVED until isolated preview
  revalidation against the newer target.
- Any G3 sentinel drift, staging/commit by editor, or Git mutation by auditor fails its
  preservation predicate; do not repair it in the same run.
