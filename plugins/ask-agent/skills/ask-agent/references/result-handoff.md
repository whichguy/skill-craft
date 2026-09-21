# Result handoff and acceptance

Read before filling the worker assignment and again when collecting results.


Prefer compact handoffs without imposing fixed word, line, duration, concurrency
or delegation-depth limits. Let the task and the native harness determine how
much work, evidence and output are needed. Explicit user constraints still apply.

Every **helper-managed** fresh native worker assignment includes the filled
delivery clause from
[Git integration](git-integration.md#reusable-fresh-worker-launch-clause).
Do not imply that files follow a returned message automatically. In `patch`
mode the parent receives and verifies the helper's baseline-relative patch; in
`commits` mode it receives and verifies the named contribution SHAs; in
`report-only` mode it receives findings and retained artifacts. The parent
integrates the accepted patch or commits and archives required reports before
calling `close`. A dirty inherited caller snapshot requires the declared patch
mode; do not silently switch a requested commit handoff to another mode.

## Consumer-owned workspace handoff

For `workspace_route: consumer-owned` and `delivery_mode: in-place`, use the
complete [Consumer-owned workspace](consumer-owned-workspace.md) contract. Its
worker returns candidate identity, binding, scoped edits and evidence, terminal
receipt, review/check results, dirty-state preservation, stopped-owner evidence,
and the unchanged parent continuation. It never returns a helper receipt,
baseline-relative patch, commit-range delivery proof, or helper close result.
The parent verifies and records in-place acceptance; the consumer separately owns
final delivery to its original caller and any cleanup.

## Caller-facing handoff

**Helper-managed default only.**

Put a self-contained handoff in the final native return and keep it in the
parent's response after collection. Do not make the caller discover paths or
decode helper state. Resolve receipt/evidence and selected-package identity
fields inside Ask Agent; return ordinary Git paths, revisions, findings, and a
concrete next action. An absolute
patch path inside the helper's retained storage is usable directly; the caller
need not understand that storage layout. Link internal evidence separately for
audit or recovery. Do not expose private native handles when the host forbids it.

For an ordinary code-change request, the parent automatically integrates the
verified contribution into the designated target and validates it. Report the
actual integrated state, including whether the target changes are committed or
remain uncommitted. Retained work with integration still pending is an explicit
blocked outcome for the overall request, even if the worker succeeded. Use a
pending, caller-decides handoff only when the caller explicitly requests that
workflow or integration cannot safely proceed; do not make an extra merge request
a routine prerequisite. Review-only tasks have no code integration.

Use this shape, filling actual observed values and omitting inapplicable fields:

```text
Task / outcome: <assignment>; <SUCCEEDED | BLOCKED | FAILED>; <what was achieved or the blocker>.
Package identity: selected card <logical absolute SKILL.md>; resolved card <absolute path>; helper <absolute path>; Ask Agent <frontmatter version>; card SHA-256 <digest>; helper SHA-256 <digest>.
Changes / checks: <worker-only changed files>; <checks actually run and their results or gaps>.
Worktree: <absolute Git worktree root>; branch <actual name or detached HEAD>; <retained | removed>.
Delivery: <patch | commits | report-only>; <absolute contribution patch and changed paths | ordered full contribution SHAs and clean base | no code changes>.
Target: <absolute caller/integration checkout>; <branch or detached HEAD>; last checked HEAD <full SHA>.
Integration: <pending by request | ready against the checked target | blocked | integrated | not applicable>; <resulting commit or uncommitted target changes, plus actual validation>.
Results: <absolute usable report/artifact paths and their purpose; retained location if moved>.
Next action for <owner>: <specific review/apply/cherry-pick/read/repair instruction; concrete commands when ready, plus validation to run>.
Retention: <keep worktree for caller decision/blocker/consumer, or why removal is already complete>.
```

For pending **patch** delivery, include the actual immutable worker-only patch
path and the target path inline, then supply shell-quoted commands with real
values:

```sh
git -C "/actual/target checkout" apply --check --binary "/actual/contribution.patch"
git -C "/actual/target checkout" apply --binary "/actual/contribution.patch"
```

The second command is conditional on the first succeeding and the caller choosing
to integrate. Recheck the target's branch/HEAD and staged, unstaged and untracked
state before applying; a moved or concurrently edited target needs reassessment.
The patch is relative to the inherited working contents, which may include dirty
caller changes, **not just the named source commit**. Say this explicitly when
the baseline was dirty. Apply only to the intended compatible checkout, preserve
its index, and run the named validation afterward. Do not prescribe a whole-branch
merge, `git diff HEAD`, or copying the whole worktree to transfer uncommitted work.
If applicability fails, retain the worktree and report the conflict/reconciliation
action; do not silently stash, reset, force-apply, or claim readiness.

For **commits**, list every verified full contribution SHA in application order,
the clean base, and a filled `git -C "/actual/target" cherry-pick <SHA1> <SHA2>`
instruction for the caller's decision. Recheck target compatibility and ordinary
Git prerequisites first; identify residual deliverables separately. A branch name
or range requiring the caller to look up helper state is not sufficient. For
**report-only**, give the findings and direct result links, state “no code
integration,” and name the result-consumption action.

Do not auto-integrate or close code work returned for the caller to merge later.
Keep that worktree, branch, contribution and required reports accessible and
state that retention explicitly. When integration was already authorized and
completed, report the actual resulting state and checks; do not offer the same
apply/cherry-pick command again. If the worktree was removed, label its path as
historical and return surviving result locations. Never present it as a checkout
the caller can still open. After a successful `close`, populate Results from its
actual `archived_artifacts[].archive` values with their purposes; do not derive
archive paths or keep pre-close worktree report links. If close retains the
worktree, keep its still-usable paths and state the returned retention reason.
If inspection failed or no usable contribution exists,
state that blocker and provide a repair action instead of invented patch/commit
locations or unsafe integration commands. Distinguish task success from
integration and combined validation.

## Reports and native return

**Helper-managed default only.** Consumer-owned workers retain evidence in the
consumer candidate and follow their separate in-place return contract.

Use each worker's designated Git worktree for its in-progress work and result
files. Fresh attempts/retries and nested workers get distinct worktrees based
on their caller's current state; never reuse a path just because task labels
match. A follow-up to the same worker may retain its worktree while needed.
Give returned files identifiable paths inside that worktree, separate from the
intended code contribution. Do not create an additional temporary-folder layer.

Allow multiple result files as useful, with one small handoff/index file that
names each returned file's absolute path, purpose and temporary or durable status.
Distinguish in-progress scratch files from completed results. When the task is
otherwise read-only, authorize needed scratch/result writes in its worktree
without authorizing input edits. Honor an explicit no-write constraint: if it
also prohibits workspace setup, do not prepare or dispatch a repository worker;
explain the required worktree, branch and receipt writes.
Do not assume a local path is shared across hosts, sandboxes or worktrees. Use
native artifact transfer if available; otherwise disclose the boundary and use
a concise inline result. Tiny answers may stay inline without allocating files.

Tell the worker to put its findings and supporting evidence in these result files.
Begin with a self-contained handoff summary: the assignment and requested
outcome, what was completed, status, key totals or blocker, artifact locations,
and the recommended next action and responsible owner. Include the relevant
current state, checks and unresolved decisions so the parent can reincorporate
the result without remembering the launch conversation. For repository work,
include the Git receipt described in the integration reference. Locate detailed
evidence with headings or file references; do not copy conversation history.
Finish writing and collect any delegated work before returning. Prefer a concise
final native response with the task label and a brief assignment reminder,
SUCCEEDED/BLOCKED/FAILED,
the outcome or blocker, the recommended next action and owner,
the observed working directory and Git worktree root, and the handoff/index path
covering the result files (or explicitly no files). Verify the actual workspace;
do not merely echo the requested path. Identify multiple workspaces if used.
State the selected-package identity (logical card, resolved card/helper,
frontmatter version, and card/helper SHA-256 values), delivery mode, receipt and baseline, integration target and owner,
allowed-write boundary, and reports retained outside the worktree. For commit
mode, state the exact contribution SHAs and every residual dirty or untracked
deliverable; never use `git add -A` against inherited state. For patch mode,
state the returned baseline-relative patch and its paths. For report-only mode,
state that code integration is not applicable.
Include a parent lifecycle recommendation: integrate the declared patch or verified
commit range according to its delivery mode, then remove the worktree when eligible;
remove it after report-only use; or retain it for the named blocker/consumer/action.
Identify files that must be preserved
before removal. Do not bury workspace identity or the lifecycle reminder solely
in a report the parent might not open.
When there is no report, include the state and artifact/revision references
needed for that next action inline; say integration is not applicable when so.
Return enough detail to make the result useful; keep bulky evidence in the
files by default instead of duplicating it in parent-directed messages.
Finish normally so the harness delivers this receipt; do not create a separate
notifier or delete the returned files.
If the required report cannot be written, report that handoff failure honestly.

After native completion or collection, check the handoff/index and its required
returned files are available. Start with the summary/index, then read as much
supporting evidence as the next decision requires. Prefer selective reads and concise verification outputs to
avoid loading irrelevant detail; a full report read is appropriate when needed.
Use native follow-up for clarification when useful, and disclose any remaining
verification limit. Do not treat the worker's success label as verification.
Treat its next-action recommendation as a proposal: check it against current
instructions, workspace state and other contributions before acting. Preserve
pending actions and their artifact/revision references in the parent's existing
task record or retained handoff when they must survive context loss. Do not
delete the only record needed to finish integration or other outstanding work.
If a required report is missing, unreadable or inconsistent, report the collection
problem and use native
follow-up/collection where available; do not invent its contents or silently
replace it with a large inline dump. File existence is not a completion signal:
keep using native notifications/collection, never file polling.

**Helper-managed default only.** The parent owns integration and the decision to
remove a worktree; the bundled helper performs preservation and eligible removal.
Wait until the worker and any delegates using it have stopped and all required
use/verification is complete. For code changes, integrate and validate the
intended contribution before removal; for report-only work, finish consuming the
results first. Retain blocked, unaccepted or still-needed work and state the next
action. Preserve required deliverables, user files, dispatcher inbox/ledger/history
and recovery records outside the worktree before removing it. Inspect the returned
workspace, approve the explicit artifact/discard list and acceptance receipt, then
call `close` as described in Workspace operations. Missing acceptance retains the
workspace. The integration reference defines the ownership and Git removal checks.
Record integration/removal or retention in the parent task state. A deleted
worktree path is not a usable final reference. Deleting a file does not remove text
already read into the conversation, so selective reading is essential.
