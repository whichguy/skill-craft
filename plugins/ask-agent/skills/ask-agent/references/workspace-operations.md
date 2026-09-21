# Workspace operations

**Helper-managed default only.** Use the packaged Git helper for helper-managed
repository delegation. It creates and verifies the worktree; native host tools
still launch and collect the worker. Prerequisites are Git and Python 3. Do not
install tools during delegation. An explicit prohibition on filesystem writes
also prohibits workspace setup. In that case do not prepare or dispatch a
repository worker; explain that the requested isolation requires creating a
worktree, branch and receipt. An ordinary code-review request permits isolated
setup and reports while leaving the reviewed inputs unchanged.

For a selected consumer-owned workspace, read
[Consumer-owned workspace](consumer-owned-workspace.md). It never uses this
reference's `prepare`, `inspect`, `check-context`, or `close` operations and
never receives a helper receipt. `identity --skill-card` is the sole helper
operation it may use, only as a read-only package identity check.

## Bind and verify the selected package

**Helper-managed default only, except for the read-only identity check noted
above.**

Obtain the absolute logical path of the selected, loaded `SKILL.md` from the
host's skill context. Its parent is `SKILL_ROOT`. Bind this again in every
independent shell call; it is not the task cwd or an assumed sibling checkout.
Do not select a package by searching `PATH`, the task cwd, a cache, or similarly
named installations.

```sh
SKILL_CARD="/absolute/path/to/the/selected/ask-agent/SKILL.md"
SKILL_ROOT="/absolute/path/to/the/selected/ask-agent"
WORKSPACE_HELPER="$SKILL_ROOT/scripts/ask_agent_workspace.py"
python3 "$WORKSPACE_HELPER" identity --skill-card "$SKILL_CARD"
```

Run `identity` before every new `prepare`, stop on a nonzero result, and retain its JSON result with the
pending job. It preserves the supplied logical card path, then returns the
resolved card and helper paths, the card's frontmatter version, and SHA-256 for
both files. It accepts host skill-directory or card symlinks only when they
resolve to the package containing the executing helper, and rejects a copied or
same-named card from another package. Give those exact identity fields to the
worker and repeat them in the worker and parent self-contained handoffs. The
command verifies a caller-supplied selection; it does not discover which skill
the host chose.

For consumer-owned selection, this same `identity --skill-card` output is
package identity only. It does not create or validate a consumer workspace,
receipt, delivery mode, or ownership record.

The paths below are placeholders. Substitute actual receipt values. Keep prompts
in native launch arguments; the helper's JSON files are Git/acceptance evidence,
not a prompt transport or another job queue.

## Prepare before dispatch

**Helper-managed default only.**

Coordinate active writers of the source checkout for the capture window after a
successful package identity check. The
caller must not begin independent edits until preparation returns. The helper's
race checks supplement this coordination; they cannot freeze external editors
or detect every change-and-restore race.

```sh
python3 "$WORKSPACE_HELPER" prepare \
  --source "/actual/caller/checkout" --label "pricing-review" \
  --writers-quiescent
```

The helper selects a unique path/branch outside the source working tree and
prints JSON containing `receipt`, `worktree`, `branch`, `baseline` and `status`.
The default store is under `XDG_STATE_HOME` (or `~/.local/state`), keeping
receipts and accepted reports outside operating-system temporary directories.
Use `--store /writable/owned/location` only when the default is unsuitable; keep
it outside the source checkout and host automatic-cleanup roots. Retain the
receipt path. Do not launch on a nonzero exit or unsuccessful preparation.

A same-attempt delivery retry can validate its existing preparation with
`prepare --receipt /actual/receipt.json --writers-quiescent`. A fresh delegation gets a fresh
preparation. Do not reuse a workspace by matching its task label.

```sh
python3 "$WORKSPACE_HELPER" inspect \
  --receipt "/actual/receipt.json" --phase prepared
```

Record this prepared inspection immediately before native dispatch for every
receipt; stop on failure. It verifies that the inherited snapshot still matches
the baseline. The worker's later `check-context` verifies directory binding and
allows legitimate task edits; it does not replace this initial snapshot check.

Pass the returned workspace, inherited-state receipt and task policy directly
in the native launch prompt. Set native `cwd` when available. Otherwise require
explicit shell workdir and absolute file-operation paths. The worker verifies
the receipt, actual command cwd and Git root before operating on task files.
Reading a helper receipt does not change the native session cwd. Follow target
worktree project instructions and the host's actual permissions.

## Check the worker's operation context

**Helper-managed default only.** A consumer-owned worker verifies its explicit
per-operation cwd and Git root against the consumer contract instead; it does
not call `check-context` with an invented or consumer receipt.

Before task work, run this from the worker's actual assigned command directory:

```sh
cd "/actual/worker/worktree" && python3 "$WORKSPACE_HELPER" check-context \
  --receipt "/actual/receipt.json"
```

Bind `WORKSPACE_HELPER` from the selected package in the same independent tool
call, or substitute its absolute path. When the host has a shell `workdir`
argument, set that instead of the `cd` prefix. The check derives process cwd and
Git root itself and refuses the caller checkout, a different worktree, a nested
independent repository, or invalid receipt binding. It accepts subdirectories
of the assigned worktree and legitimate worker changes after preparation.

Keep its actual JSON/tool result as operation evidence. It proves that command's
context, not native agent startup cwd, future tool calls, or OS isolation. Set
directory scope for every subsequent shell command and use absolute paths for
other file tools. Recheck after directory changes or unexpected routing. A
nonzero check stops task writes; do not replace it with a reported path or with
`git -C`. The helper does not change the parent shell's directory.

## Snapshot limits

**Helper-managed default only.**

Preparation preserves the caller's staged and unstaged layers and non-ignored
untracked entries. Required ignored/generated inputs need an explicit task
decision; the helper does not promise installed dependencies or copy them
silently. Unsupported state produces a concrete failure, not a partial-success
workspace. Preserve the failure receipt/workspace for recovery when returned.
This version refuses submodules, conflicted/special index states (including
intent-to-add, assume-unchanged, skip-worktree and sparse checkout), and active
Git content filters. It also refuses returned index-only changes that its
working-content contribution patch cannot represent; retain those for manual
review rather than treating an empty patch as no contribution.

## Inspect after the worker returns

**Helper-managed default only.**

Collect native completion first. `inspect --phase returned` allows legitimate
worker changes and reports a complete workspace `fingerprint` and the paths
changed against inherited content. Declare result and disposable scratch paths
explicitly, for example:

```sh
python3 "$WORKSPACE_HELPER" inspect \
  --receipt "/actual/receipt.json" --phase returned --delivery-mode patch \
  --artifact "reports/handoff.md" --artifact "reports/checks.md"
```

Review contribution evidence against the inherited baseline. Integrate only the
worker's contribution under the existing Git integration policy; a raw whole-
branch diff may include the caller's pre-existing edits. Reports/scratch are not
code contribution. Revalidate after target movement or further worker edits.

For a worker handoff, declare the delivery mode selected in the fresh-worker
launch clause: `patch`, `commits`, or `report-only`. This is the supported
delivery workflow. Mode evidence is immutable and stored beside the inspection
under the helper-owned attempt directory, never in the removable worktree.

Inspection without a delivery mode is a state snapshot for integration and
cleanup rechecks. It supplies no mode-specific delivery evidence and does not
replace the worker handoff. Commit arguments require `--delivery-mode commits`.

For the default patch handoff, use the returned immutable patch rather than a
whole-worker-branch diff:

```sh
python3 "$WORKSPACE_HELPER" inspect \
  --receipt "/actual/receipt.json" --phase returned \
  --artifact "reports/handoff.md" \
  --delivery-mode patch
```

The JSON result includes `delivery.mode=patch`, the baseline-relative
`delivery.contribution_patch`, its contribution paths, and
`evidence.delivery` (also exposed as `delivery_evidence`). The parent verifies that patch against the current target
and applies it according to repository policy. This is the mode for a dirty
caller snapshot.

For a clean-snapshot commit handoff, pass the exact source HEAD from the receipt
and every full worker contribution SHA in linear order:

```sh
python3 "$WORKSPACE_HELPER" inspect \
  --receipt "/actual/receipt.json" --phase returned \
  --artifact "reports/handoff.md" \
  --delivery-mode commits \
  --commit-base "actual-source-head" \
  --commit "first-full-contribution-sha" \
  --commit "last-full-contribution-sha"
```

The helper rejects a dirty inherited baseline, an empty/incomplete/nonlinear
range, a final SHA other than worker HEAD, committed artifact/discard paths,
transient committed paths outside the final contribution, and unclassified
residual staged, unstaged, or untracked deliverables. It returns exact commits,
committed paths, per-commit paths, residual paths, and immutable
`evidence.delivery`/`delivery_evidence` paths.
Use patch mode when the caller snapshot is dirty; do not change the requested
mode silently.

For analysis-only work, classify report files and ask for a report-only proof:

```sh
python3 "$WORKSPACE_HELPER" inspect \
  --receipt "/actual/receipt.json" --phase returned \
  --artifact "reports/handoff.md" \
  --delivery-mode report-only
```

This succeeds only when every changed path is an explicit artifact/discard and
none is an inherited repository input. It does not authorize removal; use the
separate parent acceptance and `close` step after reports are consumed.

## Close after acceptance

**Helper-managed default only.** A consumer-owned workspace stays with its
consumer; Ask Agent does not call `close` or remove it.

Calling `close --receipt /actual/receipt.json` without acceptance retains work.
The parent may create an acceptance JSON file after reading the handoff,
verifying integration (or report consumption), and confirming all native workers
and consumers are finished. Keep that file outside the removable worktree.

```json
{
  "schema": "ask-agent.acceptance.v1",
  "inspection_fingerprint": "actual returned inspection fingerprint",
  "decision": "integrated",
  "workers_stopped": true,
  "completion_reference": "actual native return and stopped delegate evidence",
  "acceptance_reference": "actual target path, integrated diff or revision, and validation evidence",
  "artifacts": [
    {"path": "reports/handoff.md", "purpose": "accepted worker handoff"},
    {"path": "reports/checks.md", "purpose": "validation evidence"}
  ],
  "discard": []
}
```

Use `report-consumed` instead of `integrated` for report-only work; changes to
repository inputs prevent that close. `discard` identifies parent-reviewed,
disposable scratch. List paths relative to the worker worktree; do not approve
unknown files wholesale. Stop and acceptance fields are parent attestations,
not facts the helper independently learns from native hosts.
The inspection fingerprint binds the exact worker state and classified
contribution being accepted. The acceptance reference identifies where that
contribution was integrated and validated, or where the reports were consumed;
the helper does not independently verify semantic integration in the target.

```sh
python3 "$WORKSPACE_HELPER" close \
  --receipt "/actual/receipt.json" --acceptance "/actual/acceptance.json"
```

The helper rechecks identity and fingerprint, archives only approved artifacts
to its owned durable results root, verifies their bytes, and removes the eligible
worktree through Git. It leaves the branch and returns durable paths. Missing or
stale evidence, unsafe paths, new changes, missing files or absent stopped-worker
attestations retain work with a reason. It never merges code, deletes the source checkout, decides
semantic acceptance, polls agents or runs an age-based cleanup.

Read the actual outcome before reporting removal. Update final result links to
the retained paths; a removed worktree link is not a usable deliverable. Existing
dispatcher inbox/history and project deliverables remain their owner's durable
state; do not classify them as disposable worker scratch.
