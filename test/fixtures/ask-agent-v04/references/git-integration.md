# Git integration for delegated work

Apply the workspace and removal contract to every Ask Agent invocation in a
repository, including research and review. Apply synchronization and integration
to code contributions. Use the project's existing integration workflow; these
instructions add ownership and evidence, not an agent launcher or scheduler.

## Agree on the contribution before dispatch

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

## Prepare an isolated copy of the current state

Create a uniquely named worktree and worker branch from the caller's exact HEAD,
then carry over staged and unstaged changes before dispatch. A fresh worktree
from HEAD alone is insufficient. Include non-ignored untracked inputs, staged
additions/deletions, binary files, modes and symlinks as applicable; preserve
both layers when one file has staged and unstaged edits. Preserve the source
checkout and index without stashing, resetting, committing or switching them.
Record source path, branch/HEAD, staged and unstaged state and copied inputs;
do not silently skip files that cannot be copied faithfully. Ignored/generated
files and external/submodule state need an explicit task-dependent decision;
report unavailable required inputs instead of implying full reproduction.

Prefer native worktree facilities when they can represent this exact state.
Verify their behavior: a native HEAD-only worktree still needs the dirty-state
transfer. Otherwise ordinary Git/file tools may prepare the worktree, followed
by native agent dispatch; never shell-launch another model to obtain isolation.
Use a new path/branch per invocation, including retries and nested delegation.
Honor an existing caller-prepared worktree only when it is exclusively assigned
to this invocation and has a verified equivalent baseline. A same-worker
follow-up may reuse its own worktree. Report non-Git or unsupported isolation
instead of silently using the shared checkout.
Collection or delivery retry for the same native attempt keeps its existing
worktree and completed result files; it is not a fresh task retry.

Observe a consistent source snapshot: coordinate with active writers or verify
source revision, index and working-file contents remained stable during capture.
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

The parent owns the integration target, ordering, shared behavior decisions and
final acceptance. It may assign an integration agent or the original worker to
execute integration. Only one actor updates a given integration target at a time;
independent implementation can continue. Follow existing authorization and
repository policy for commits, merge/rebase/cherry-pick, pushes and publication.

## Refresh and prepare the worker contribution

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

Put a concise reminder and recommendation in the final native receipt, with the
detailed state in the report. A code handoff should identify:

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

For example: “Assigned: add CSV export. Implementation complete; integration
pending. Prepared against integration at <target SHA>; contribution <worker SHA>.
Workspace: <observed cwd>; worktree: <actual Git root>.
Next: parent recheck target, integrate this contribution and run the export flow
check. Results: <absolute index path inside worktree>.
Lifecycle: parent merge the worker-only contribution, preserve <required result>,
then remove this worktree when validation and all consumers finish.”
Use actual values in real receipts. Include enough inline state for a tiny task;
do not impose a fixed receipt length or require a report when writes are forbidden.

## Accept the combined result

The parent reads the handoff and verifies the contribution and current target.
If the target has moved since the worker's check, reassess against its new exact
revision before acceptance; prior compatibility evidence is stale. The parent
may reconcile and test the new combination itself or delegate preparation/repair
back to the worker. Do not require replaying unaffected work merely to repeat a
ceremony. Coordinate the final target update with other writers and verify its
actual result; if it races, re-evaluate instead of overwriting newer work.

Integrate the intended contribution using project policy. Inspect what the
commit range or patch includes against the inherited-state baseline; exclude
duplicated caller edits, private baseline commits, unrelated changes, scratch
reports and runtime artifacts rather than copying an entire worktree. Check the resulting
shared behavior: a clean textual merge does not prove semantic compatibility.
Delegate localized repairs as useful, then review and revalidate affected scope.

Report worker completion separately from integration and combined validation.
Do not infer push, publication or deployment from a local merge. Retain reports,
branches and other recovery material while integration or decisions remain
outstanding.

## Parent-owned worktree removal

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
