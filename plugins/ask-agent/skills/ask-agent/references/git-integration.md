# Git integration for delegated work

**Helper-managed default only.** Apply this workspace and removal contract to
Ask Agent's helper-managed repository delegations, including research and
review. Apply synchronization and integration to code contributions. Use the
project's existing integration workflow; these instructions add ownership and
evidence, not an agent launcher or scheduler.

The explicit consumer-owned route has `delivery_mode: in-place`, no helper
receipt, and no patch/commit/report-only transfer. Read
[Consumer-owned workspace](consumer-owned-workspace.md) instead; do not apply
this reference's preparation, delivery enum, or removal procedures to a selected
consumer candidate.

## Agree on the contribution before dispatch

**Helper-managed default only.**

The parent names the repository and actual worker workspace, the requested
outcome and write ownership, the starting revision, the intended integration
target and the integrating owner. The target may be a local integration branch
with unpublished work, not necessarily a remote default branch. Record the
target's exact revision as well as its name. The starting point is the caller's
actual current checkout, including when it is already a linked worktree or is
detached; never substitute the primary checkout, default branch or remote tip.
Distinguish a starting revision from a task that must remain pinned to it. State
any task-specific synchronization or commit/history/publication restrictions;
the worker inherits existing authorization and need not ask again for actions
already within the assignment.

## Choose one delivery mode

**Helper-managed default only.** Every fresh helper-managed native worker
assignment declares exactly one delivery mode. This is a task-launch contract,
not a global system-prompt change. A native return brings back a result message
and references; it does not transfer worktree files or integrate a change by
itself.

- **`patch`** is the default for code work. The parent obtains the helper's
  immutable, baseline-relative contribution patch after the worker returns and
  verifies/applies it under the chosen integration policy. It is the required
  mode when the prepared caller snapshot has staged, unstaged, or untracked
  inherited inputs.
- **`commits`** is for an existing repository or user policy that specifically
  requires commit-based handoff. It is supported only when the prepared caller
  snapshot is clean. The worker stages only its named contribution files, never
  uses `git add -A`, and returns exact full contribution SHAs. The parent asks
  the helper to verify the complete, linear source-HEAD-to-worker-HEAD range
  and any residual staged, unstaged, or untracked paths before cherry-picking.
  A dirty inherited snapshot is a fail-closed reason to retain the workspace
  and use the declared `patch` mode; do not silently convert modes.
- **`report-only`** is for analysis, review, or findings whose repository-input
  changes are not a deliverable. The worker writes only the allowed result and
  scratch files, and the parent explicitly preserves the reports. The helper
  rejects unclassified contributions and edits to inherited inputs even when
  someone attempts to label them as artifacts or discard.

The parent identifies the integration target and the one owner that integrates.
It archives required reports before eligible cleanup. Commit SHAs, patches and
reports are distinct deliverables; reports are not smuggled into a code commit.
An ordinary code-change assignment includes automatic integration into that
target, followed by combined validation. The caller need not separately ask to
bring the result back. Explicit review-only or return-unmerged instructions take
precedence. Preserve dirty caller state: patch integration can legitimately remain
uncommitted, and a worker's success or private commit does not imply a target
commit. A delegated skill may require an authorized scoped private checkpoint in
its isolated worktree while delivery remains `patch` (for example, Improve). If
a selected new path must be staged first, use `git add -- <selected path>` only
for that path, then use `git commit --only -m "..." -- <explicit selected
paths>`. Never use `git add -A`: `--only` prevents unrelated inherited index
entries from entering the checkpoint. When a selected path overlaps dirty caller
content, that private commit naturally includes the inherited context. Record its
full SHA as `checkpointSHA` provenance only, separate from the helper's
contribution patch. Do not pass it to patch-mode `inspect` or cherry-pick/merge
it into the caller. Patch workers without that task-specific requirement follow
their own commit policy.

For dirty patch delivery, the parent rechecks the baseline-relative patch and
the current target, then uses plain `git apply --check --binary <patch>` followed
by plain `git apply --binary <patch>`; do not add `--index`. This preserves the
caller's HEAD and index while applying only the worker delta. Do not squash a
whole branch containing inherited caller changes. A single target commit is
eligible only under the existing commit/history policy and after verifying a
clean compatible target; integrate only the verified contribution range. The
existing `commits` delivery route still requires a clean inherited snapshot and
its verified exact range.

## Reusable fresh-worker launch clause

**Helper-managed default only.** Fill this concise clause into every fresh native
worker prompt after `prepare`. Use real absolute values and task-specific allowed
writes; do not leave braces in a dispatched task.

```text
You are a fresh worker. Work only in {worktree}.
Verify receipt {receipt} and baseline {baseline}. From {worktree}, run python3 "{absolute helper path}" check-context --receipt "{receipt}" before task operations; stop on failure and return its actual output or tool locator.
Binding mode: {native cwd | explicit operations}. Shell rule for this host: {fill the exact supported workdir argument or cd prefix from the host recipe; apply to EVERY shell call including checks, tests, reports and retries}. Use absolute paths for other file tools, including reports. Do not create another worktree or assume git -C changes shell cwd.
Delivery mode: {patch | commits | report-only}.
Integration target: {target at exact revision}; integration owner: {parent or named owner}.
Allowed writes: {named contribution paths and allowed report/scratch paths}.
Preserve inherited state. Do not edit outside this worktree or use git add -A. Add a selected new path narrowly with git add -- <path> only when necessary.
Write required reports under {report paths}; they must be retained before cleanup.

For patch: leave the worker-only change in place and return its result paths. If a delegated skill requires an authorized private checkpoint, commit only the explicit selected paths with git commit --only -m "..." -- <paths> after any narrow add for selected new paths. Return its full checkpointSHA as provenance only, separately from the patch; do not pass it to patch inspect or cherry-pick/merge it into the caller.
For commits: commit only the named worker contribution, return every exact full contribution SHA in order, and list every residual staged, unstaged, or untracked deliverable.
For report-only: do not change repository inputs; return findings and report paths only.

Finish all writes/reports, then run the packaged helper inspect --phase returned with this receipt, declared delivery mode, named --artifact report paths, and required commit arguments only for commits mode. Patch inspection has no --commit-base or --commit arguments even when a checkpointSHA exists. Use its actual delivery values in the inline return; do not rewrite an inspected report merely to insert the generated patch path. The parent rechecks inspection after native completion. If inspection fails, return the blocker and retained worktree, not guessed delivery values.
Return the caller-facing handoff from Result handoff inline: task outcome/checks; absolute worktree and branch; delivery mode with exact patch path and any checkpointSHA marked provenance-only, or ordered full contribution SHAs; absolute target checkout and last checked HEAD; integration state; direct report paths; and a concrete next action for the integrating owner. Resolve helper state yourself; the caller must not need receipt/baseline JSON to use the result. For patch delivery, identify the worker-only patch against inherited contents, not a whole-branch merge. Do not invent paths or report readiness without inspection.
Returning a message does not integrate or transfer files. Leave this worktree intact. An ordinary code-change request authorizes the parent to verify, integrate and validate the contribution automatically. Explicit return-unmerged instructions or a concrete integration blocker require a retained code handoff instead. Review-only tasks require report consumption, not code integration. After integration/report consumption, the parent archives reports and decides whether close is eligible.
```

## Prepare an isolated copy of the current state

**Helper-managed default only.**

Call the bundled helper's `prepare` operation as described in
[Workspace operations](workspace-operations.md). The helper creates a uniquely
named worktree and worker branch from the caller's exact HEAD,
then carries over staged and unstaged changes before dispatch. A fresh worktree
from HEAD alone is insufficient. Include non-ignored untracked inputs, staged
additions/deletions, binary files, modes and symlinks as applicable; preserve
both layers when one file has staged and unstaged edits. Preserve the source
checkout and index without stashing, resetting, committing or switching them.
Record source path, branch/HEAD, staged and unstaged state and copied inputs;
do not silently skip files that cannot be copied faithfully. Ignored/generated
files and external/submodule state need an explicit task-dependent decision;
report unavailable required inputs instead of implying full reproduction.

Use the packaged helper for the shared snapshot contract, followed by native
agent dispatch. Prefer native worker cwd binding to the returned path when
available. A native worktree creation facility is a separate qualified integration:
verify its starting state and retention before substituting it for preparation.
Never shell-launch another model to obtain isolation.
Use a new path/branch per invocation, including retries and nested delegation.
An existing caller worktree is the source for a fresh preparation, not a reason
to skip snapshot replay or reuse that worktree for a new worker. A same-worker
follow-up may reuse its own receipt and worktree. Report non-Git or unsupported isolation
instead of silently using the shared checkout.
Collection or delivery retry for the same native attempt keeps its existing
worktree and completed result files; it is not a fresh task retry.

Observe a consistent source snapshot: coordinate active writers for the capture
window and verify source revision, index and working-file contents remained stable.
If they changed, reconcile/repeat the capture before dispatch; do not run on a
mixed snapshot. Validate the child contents against that snapshot. Configure
the native worker's cwd/isolation where supported; otherwise pass the absolute
worktree and require every task command/file operation to use it. Record the
observed command cwd and Git root. A path mentioned in a prompt alone is not
proof the worker used it.
Compare native cwd/isolation metadata with command evidence where available.
If the host exposes no independent metadata, disclose that verification limit;
do not describe a worker-reported path alone as independently verified.

Record the inherited dirty snapshot separately from the worker's contribution.
Keep original staging information in the baseline receipt. An isolated private
baseline commit is one option when allowed, after verifying the copy; it must
not change source history or be presented as worker-authored changes. Otherwise
retain equivalent content/patch evidence in the worktree. Return changes against
that baseline, not a whole-branch diff from the original HEAD that accidentally
includes the caller's existing edits. Store scratch and result files inside the
worker worktree under clearly identified paths, excluded from the contribution;
no separate temporary-folder mechanism is needed.

For report-only work, creating the isolated workspace is still required, but
integration is not applicable. Do not mutate repository inputs merely to review.
Classifying a modified inherited input as an artifact or discard never makes it
report-only-safe.

The parent owns the integration target, ordering, shared behavior decisions and
final acceptance. It may assign an integration agent or the original worker to
execute integration. Only one actor updates a given integration target at a time;
independent implementation can continue. Follow existing authorization and
repository policy for commits, merge/rebase/cherry-pick, pushes and publication.

## Refresh and prepare the worker contribution

**Helper-managed default only.**

Before handing back isolated code changes, check the latest designated target.
For an explicitly pinned assignment, report target movement without changing
the pinned input. Otherwise refresh within the assigned integration policy.
If a remote is authoritative, fetch that named remote/ref and resolve its exact
commit. If the target is local, inspect the current local target revision,
including accepted unpublished contributions. Do not substitute the worker's
configured upstream for this target. Plain `git pull` fetches and integrates the
current branch's upstream; use it only when that upstream and its integration
mode are verified to match the assignment. Prefer explicit fetch and the chosen
merge/rebase operation against the recorded target commit.

Preserve unrelated staged, unstaged and untracked work. Do not use automatic
stash/reset or broad staging to make synchronization proceed. Establish a
reviewable contribution using the authorized commit or patch workflow before
reconciliation. If synchronization is unavailable, fails, or would disturb
unrelated work, preserve the contribution and report the actual blocker; do not
call it up to date or conflict-free. An absent remote is normal for a local target.

Reconcile against the selected target in the isolated workspace using project
policy. Resolve conflicts within the assignment, preserving both sides' intended
behavior, then rerun affected checks. Bring cross-task or requirement conflicts
to the parent with a proposed resolution; do not silently choose one worker's
behavior. Record clean synchronization, resolved conflicts, remaining conflicts
or an unperformed check separately. A failed fetch is not a merge conflict.
Use native follow-up for repair of the same assignment when supported, or send
a fresh worker the self-contained repair handoff. No shell agent relauncher is
needed. A new assignment still follows the skill's fresh-context rule.

## Return enough state to resume integration

**Helper-managed default only.**

Put a concise reminder and recommendation in the final native receipt, with the
detailed state in the report. Use the self-contained
[caller-facing handoff](result-handoff.md#caller-facing-handoff); no helper state
file is required to interpret the outcome or follow its integration directive.
A code handoff should identify:

- The original assignment, requested outcome, completed work and pending work.
- Observed working directory and Git worktree root, workspace topology, starting
  revision, worker branch and exact
  commit(s), or the agreed patch/artifact and its base when commits are not used.
- Integration target/ref and last checked target commit; synchronization method
  and result, conflicts encountered/resolved/remaining, and dirty state.
- Intended changed files and any exclusions; validation commands, outcomes and
  the revision or working-tree state checked; known gaps and shared interfaces.
- Integration state: not applicable, pending, ready against the named revision,
  blocked, or integrated with the actual resulting revision and validation state.
- Recommended next action, its owner, exact contribution/target references and
  any prerequisite or decision. Distinguish observed facts from recommendations.
- Source checkout/HEAD and inherited snapshot baseline, plus the worker-only
  contribution relative to it; identify inherited changes excluded from transfer.
- Handoff/index and result-file references inside the worktree,
  with retention reasons and the parent merge/removal reminder. Keep dispatcher
  receipts/history and deliverables distinct from disposable scratch/evidence.
- Delivery mode and its helper evidence: baseline-relative patch and paths for
  `patch`, plus any private `checkpointSHA` explicitly marked provenance-only;
  exact full SHAs, verified base, committed paths and residual paths for
  `commits`; or explicit no-code-integration and retained report paths for
  `report-only`.

For example: “Assigned: add CSV export. Implementation complete; integration
pending. Prepared against integration at <target SHA>; contribution <worker SHA>.
Workspace: <observed cwd>; worktree: <actual Git root>.
Next: parent recheck target, integrate this contribution and run the export flow
check. Results: <absolute index path inside worktree>.
Lifecycle: parent integrate the declared patch or verified commit range according
to its delivery mode, preserve <required result>, then remove this worktree when
validation and all consumers finish.”
Use actual values in real receipts. Include enough inline state for a tiny task;
do not impose a fixed receipt length or require a report when writes are forbidden.

## Accept the combined result

**Helper-managed default only.**

The parent reads the handoff and verifies the contribution and current target.
If the target has moved since the worker's check, reassess against its new exact
revision before acceptance; prior compatibility evidence is stale. The parent
may reconcile and test the new combination itself or delegate preparation/repair
back to the worker. Do not require replaying unaffected work merely to repeat a
ceremony. Coordinate the final target update with other writers and verify its
actual result; if it races, re-evaluate instead of overwriting newer work.

Integrate the intended contribution using project policy. Inspect what the
commit range or patch includes against the inherited-state baseline; exclude
duplicated caller edits, private baseline or checkpoint commits, unrelated
changes, scratch reports and runtime artifacts rather than copying an entire
worktree. Check the resulting
shared behavior: a clean textual merge does not prove semantic compatibility.
Delegate localized repairs as useful, then review and revalidate affected scope.

Report worker completion separately from integration and combined validation.
Do not infer push, publication or deployment from a local merge. Retain reports,
branches and other recovery material while integration or decisions remain
outstanding.

## Parent-owned worktree removal

**Helper-managed default only.**

The parent decides eligibility; the bundled helper performs approved preservation
and removal through `close`. Its default without acceptance is retention. See
[Workspace operations](workspace-operations.md) for inspection and the explicit
parent acceptance/artifact manifest. Native stop and semantic acceptance remain
parent assertions; the helper validates Git/filesystem facts, not those decisions.

The worker leaves its worktree and returned files intact. Its final native
receipt names the absolute worktree path and recommends one of: parent integrate
the contribution then remove when ready; parent remove after report-only results
are consumed; or parent retain for a named blocker, review or consumer.
Completion alone never authorizes discarding an unaccepted contribution.

Before removal the parent confirms all users of the worktree, including nested
workers, have stopped; verifies the intended contribution is integrated and
validated (or integration is not applicable); and preserves required results
and recovery references outside it. Recheck actual dirty/untracked state: no
unknown edits, files or outstanding consumers may be silently discarded.
Use Git/native worktree removal, not a blind recursive directory deletion.
If removal refuses because of leftover files, classify/preserve them first;
force removal is appropriate only after verifying everything remaining is owned
and disposable. Never force-delete an unmerged contribution merely to clean up.
Branch deletion is a separate ownership decision; preserve needed recovery refs.
Record the removed path, integrated revision or no-integration reason, retained
artifacts and any leftover branch. Replace moved result links so final references
remain usable. Dispatcher inbox/ledger/history are durable consumer state, not
worker scratch to delete with the worktree.
