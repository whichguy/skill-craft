# Current workspace

`workspace_route: current` runs a fresh native worker in the caller's own
checkout and branch. There is no helper-prepared worktree, snapshot, receipt,
patch, commit delivery or close. Use it for work that needs a separate context
but not a separate copy of the repository: digesting a long log or run state
into a short summary, answering a question about the code, or a small edit to a
declared set of files.

## Selection

Select this route only when the user or an invoking skill says so explicitly:
`workspace_route: current`, "in place", `--in-place`, or "just use the current
worktree". Never infer it from a request for speed, for fresh context, or from
an existing worktree. Orchestrated Git work (Plan Dispatcher, ShipLoop,
improve-agent) never selects it; those keep the helper-managed route and its
capability gate.

## Delivery modes

| Mode | Default | Worker may write | Parent before launch |
|---|---|---|---|
| `report-only` | yes | nothing tracked or untracked; the result returns inline | record a baseline |
| `in-place` | no | only the declared write set (relative paths, directories or globs) | record a baseline; refuse if the parent's own dirty paths overlap the write set |

Rules for both modes:

- The worker never commits, switches branches, stashes, resets or rebases. A
  moved HEAD or branch is drift, and the parent refuses the result.
- The parent does not edit the write set while the worker is pending, and runs
  at most one `in-place` worker at a time in one checkout.
- A `report-only` worker may launch its own native workers under the same
  rules and must collect them before returning. An `in-place` worker may not.
- Ignored files (build output, caches) are not fingerprinted. Test and build
  output there is not reported as drift.

Outside a Git repository `current-state` reports `status: not-git`. Only
`report-only` may proceed there, and the handoff says no drift check ran.

## Model and tools

Inherit the host's model and tools by default. When the user or the invoking
skill explicitly asks for a cheaper model or a read-only agent type, for
example for a status digest, honor it and name it in the handoff. The parent
never adds such a restriction on its own.

## Record the baseline and launch

Bind the helper from the selected card as in
[Workspace operations](workspace-operations.md#bind-and-verify-the-selected-package),
then from the caller's checkout:

```sh
python3 "$HELPER" current-state > "$BASELINE"
```

Keep `$BASELINE` in a temporary or scratch location outside the checkout. For
`in-place`, compare the baseline `entries` with the write set and refuse on
overlap.

Put these in the native launch prompt: the objective, `Route: current`, the
delivery mode, the absolute root, the write set for `in-place`, the current
learnings and approvals (see the skill card), and the return shape below. The
worker's first command checks its directory:

```sh
cd "$ROOT" && python3 "$HELPER" current-state --expect-root "$ROOT"
```

and it stops on a failure. Every later shell command begins with
`cd "$ROOT" &&`, and file tools use absolute paths.

Launch a fresh general-purpose native worker with no inherited history. A
digest or question runs in the foreground by default, because its result is
short and the parent needs it next; the user's request to run it in the
background takes precedence. Host recipes:

| Host | Launch |
|---|---|
| Claude Code | `Agent` without `isolation` (that creates another worktree) and without an invented `cwd`; `model` only when requested |
| Codex | native spawn with `fork_turns="none"`; `workdir` set to the root on every shell call |
| Grok | `spawn_subagent` with `cwd` set to the root and no `resume_from` |
| Cursor | native `Task`; explicit operation directories |
| OpenCode | `task` with no `task_id`; `workdir` set to the root |

Each recipe is a pilot: check the live tool schema, and do not claim support
from the helper-managed evidence in [Host capabilities](host-capabilities.md).

Claude Code evidence (2026-09-27, foreground `Agent`, general-purpose, `model:
sonnet`, scratch repository): a `report-only` digest of a 10 KB packet returned
an accurate three-bullet summary with verdict `unchanged`, and an `in-place`
worker limited to `summary/` returned `changed-within-write-set`; a parent edit
outside the write set was then reported as `drift`. Each spawn cost about
86,000 subagent tokens, almost all fixed startup, while the parent received
about 250. A separate context therefore pays off when the material is large or
must stay out of the parent's context, not for formatting a status line a
script can render.

## Return and acceptance

The worker returns inline:

- Task, and Status: SUCCEEDED, BLOCKED or FAILED
- `Route: current`, the delivery mode, root, branch, and HEAD before and after
- the result itself, or the blocker
- the paths it changed (none for `report-only`)
- the next action and its owner

The parent then runs:

```sh
python3 "$HELPER" current-state --baseline "$BASELINE" --write-set PATH ...
```

and reads `verdict`:

| Verdict | Meaning | Parent action |
|---|---|---|
| `unchanged` | no path or HEAD change | accept a `report-only` result |
| `changed-within-write-set` | only declared `in-place` paths changed | verify the edits, then accept |
| `drift` | HEAD or branch moved, or a path outside the write set changed | refuse; report `changed_paths`, `outside_write_set` and `head_moved` |

A parent edit made during the run also shows up as a change, so the parent
keeps its own writes off the checkout while the worker is pending. Report the
task, status, route, delivery mode, verdict and changed paths in the final
answer. There is nothing to close or clean up.
