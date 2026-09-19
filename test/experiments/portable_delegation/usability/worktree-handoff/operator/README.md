# W1 operator guard contracts

`verify-w1.py` is test apparatus, not an agent launcher or part of Ask Agent.
Every command has `--help`. Only `prepare` creates a fixture; no command removes
worktrees, repairs a participant result, polls or stops a host. Keep operator
evidence outside participant checkouts and durable agent-result inboxes.
Evidence destinations must be new files: existing files, including a supplied
SQLite database or earlier receipt, are never overwritten.

## Setup and launch preflight

Render the parent prompt for the intended absolute run paths before preparation.
Then call `prepare --run-dir <new-absolute-directory> --prompt <rendered-prompt>
--skill <frozen-SKILL.md> --reference <frozen-git-integration.md>`.
The run directory must not already exist. This creates `w1-primary`, the dirty
linked `w1-feature`, `w1-inbox`, `source-before.json` and `paths.json`. No workers
are created. Git identity, empty hooks directory and signing settings apply
only to this disposable repository; native host hooks remain host behavior.

`snapshot --source <checkout> --output <operator-file>` records the semantic
index, working content, nonignored inputs and ignored files for source-cleanliness
checks. This does not change the skill's separate decision about transferring
ignored/generated inputs to workers. Repeated snapshots must
use new evidence filenames when retaining history.
Git inspection disables optional index refresh and external diff/text conversion;
snapshotting must preserve the caller's index bytes as well as its staged content.
Per-file index entries also record Git's `ls-files -v` flags, so completion can
detect changed assume-unchanged or skip-worktree state on nonpricing inputs.
Earlier snapshots without those flags require a fresh baseline for these checks;
do not rewrite historical receipts. Legitimate pricing integration may update the
index, so completion compares nonpricing entries rather than all raw index bytes.

`preflight` takes `--source`, `--manifest` (the prepared `paths.json`),
`--parent-cwd`, `--launch` (JSON), and the actual `--prompt`, `--skill` and
`--reference` files. Required launch fields:

| Field | Meaning |
| --- | --- |
| `cwd` | Actual planned process working directory, equal to the source checkout. |
| `project_path` | Actual planned native project, equal to the source checkout. |
| `argv` | Exact executable/argument array. Project flags and OpenCode's positional project are checked for conflicts. |
| `argv_mode` | Set `cwd-only` only when this invocation relies on process cwd and supplies no project override. |
| `prompt_sha256`, `skill_sha256`, `reference_sha256` | Digests of the selected frozen inputs, matching the manifest and supplied files. |

`READY` requires the baseline snapshot schema and source-checkout identity to
match, plus all three frozen input digests, including the Git reference,
and checks the registered launch and current files. Separately observe the
actual native session cwd, selected inputs and effective model after launch.
This helper cannot prove that an operator executed the registered command.

## OpenCode public evidence

`public-opencode` takes `--db`, one native `--session`, `--output`, `--source`,
`--inbox`, and `--worktree` repeated for every worker path. Run it separately
for parent and child sessions. It uses a read-only SQLite connection and selects
allowlisted public fields in SQL. Actual OpenCode 1.18.31 message/part JSON
columns are supported; the scalar schema is a hermetic test fixture.
The database belongs to OpenCode; Ask Agent adds no database or file-backed
dispatch queue. This test command writes a separate JSON evidence file.

The result contains session identity/parent/cwd, message role/final/model/times,
visible text, tool status, and public task/command/path arguments. It preserves
task-ID presence separately from value. It does not select raw `data`, metadata,
reasoning parts, tool results, errors or outputs. Missing supported session,
message-role or public-part data yields `UNSUPPORTED`, not an empty pass.
Projection schema `ask-agent-w1.public-opencode.v2` keeps task arguments in
individual `task_calls` keyed by native part ID, with complete public `records`
retained. It replaces v1's misleading aggregate `assignment`, which could combine
an omitted-ID flag from one part with a resume ID from another. Historical v1
receipts remain historical evidence and are not rewritten.

## Completion evidence

`complete` takes `--source`, `--baseline` (the original `source-before.json`),
`--inbox`, `--observations` (normalized JSON), and optional `--output`.
The normalization is operator-owned public evidence, never a worker's unsupported
self-certification. Record native event/session locators alongside it. The
helper verifies consistency and filesystem state; it cannot authenticate an
invented observation.

Required top-level observation fields:

- `parent_state`: `completed` or `finished` only after a successful final result.
  A native `finish=stop` field by itself does not establish this.
- `parent_tool_states`: observed terminal tool states; pending/running disallow
  completion. Normalize terminal host errors to `failed` and retain the error
  separately in the native-conformance assessment.
- `registered_worktrees`: historical entries `{worker_id, path}` establishing
  which owned path belongs to each worker. Current registration is independently
  checked through Git.
- `workers`: exactly W1's two roles, `code` and `report`. This is a fixture shape,
  not a runtime agent-count limit.
- `events`: chronological native observations, described below.

Each worker entry contains `id`, `role`, `state`, `returned`, `tool_states`,
absolute `worktree`, worker-only `changed_files`, `inbox_prefix`,
`required_reports`, `handoff_index`, and `report_sha256`.
Report paths are relative to `inbox/inbox_prefix`; the index must be included
in the required list with at least one distinct detail file. `report_sha256` maps each required relative name
to its digest captured when archived. File names need not match a fixed naming
convention. Absolute/traversing paths and symlink escapes are rejected.

For each worker, events must establish `worker_terminal`, `worker_return`,
`reports_archived`, and `worktree_removed`, in that order, followed by the
parent's single successful `parent_final` (or `parent_finish`). Duplicate or
contradictory final events do not qualify. Each event uses `kind`, native
worker ID in `worker` when applicable, and a common-format `timestamp` when
available. Keep all events in observed order; that order handles missing
timestamps and breaks equal-timestamp ties. Known timestamps must still agree
across gaps. A terminal child with no return
delivery event does not qualify. Required files must still exist and hash-match.

The code worker's contribution is `pricing.json` only; report-worker changes
are under `reports/` without path traversal. The actual source must retain its
Git directory/common-directory identity, branch, index and
nonpricing content. Pricing-only descendant commits and unstaged pricing
integration are both accepted. Current worktree registration and path absence
must agree. A retained worker may supply `retention: {state, reason}` for honest
blocked/active recovery, but normal W1 is then `INCOMPLETE`.

`COMPLETE` proves only the checked fixture lifecycle. Score native task dispatch,
parent continuation, return wording, capabilities and remaining observation
limits separately using the frozen oracle. Exit zero is reserved for successful
commands; incomplete/unsupported results exit one and contract errors exit two.
The hermetic test's `_good_observations` is a runnable synthetic example.
