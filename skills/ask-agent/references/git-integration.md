# Git integration for delegated work

Apply this contract when workers change repository content. Research and review
tasks only return findings unless their assignment authorizes changes. Use the
project's existing integration workflow; these instructions add ownership and
evidence, not a dispatcher, scheduler or prescribed branching strategy.

## Agree on the contribution before dispatch

The parent names the repository and actual worker workspace, the requested
outcome and write ownership, the starting revision, the intended integration
target and the integrating owner. The target may be a local integration branch
with unpublished work, not necessarily a remote default branch. Record the
target's exact revision as well as its name. Carry forward relevant uncommitted
inputs explicitly: a new worktree from HEAD does not contain those edits.
Distinguish a starting revision from a task that must remain pinned to it. State
any task-specific synchronization or commit/history/publication restrictions;
the worker inherits existing authorization and need not ask again for actions
already within the assignment.

Choose the workspace from the task and available native facilities:

- **Isolated worktree or checkout:** identify the worker branch/revision and how
  its changes will be returned. Prefer native isolation where available; report
  the actual path and revision instead of assuming a fresh context isolates Git.
- **Shared checkout:** assign compatible file ownership and coordinate edits.
  Changes are already visible; there is no worker branch to merge. Serialize
  operations that change the shared index, branch or checkout through its
  designated owner. Workers must not independently pull, rebase, reset, stash
  or merge while other writers use that checkout.
- **Report only:** no Git mutation is needed. State integration is not applicable.

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
- Workspace topology and path, starting revision, worker branch and exact
  commit(s), or the agreed patch/artifact and its base when commits are not used.
- Integration target/ref and last checked target commit; synchronization method
  and result, conflicts encountered/resolved/remaining, and dirty state.
- Intended changed files and any exclusions; validation commands, outcomes and
  the revision or working-tree state checked; known gaps and shared interfaces.
- Integration state: not applicable, pending, ready against the named revision,
  blocked, or integrated with the actual resulting revision and validation state.
- Recommended next action, its owner, exact contribution/target references and
  any prerequisite or decision. Distinguish observed facts from recommendations.

For example: “Assigned: add CSV export. Implementation complete; integration
pending. Prepared against integration at <target SHA>; contribution <worker SHA>.
Next: parent recheck target, integrate this contribution and run the export flow
check. Details: <absolute report path> (temporary; retain until integration).”
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
commit range or patch includes; exclude unrelated changes, scratch reports and
runtime artifacts rather than copying an entire worktree. Check the resulting
shared behavior: a clean textual merge does not prove semantic compatibility.
Delegate localized repairs as useful, then review and revalidate affected scope.

Report worker completion separately from integration and combined validation.
Do not infer push, publication or deployment from a local merge. Retain reports,
branches and other recovery material while integration or decisions remain
outstanding; remove only owned temporary artifacts after their required use.
