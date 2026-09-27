# Ask Agent write-grant preflight — journal

Living record for the write-grant preflight in
`skills/ask-agent/scripts/ask_agent_workspace.py`. Edit entries in place; mark a
superseded claim with the date and the reason rather than deleting it.

## Problem (2026-09-27, firm)

`prepare` creates the worker worktree under the store (default
`$XDG_STATE_HOME/ask-agent/workspaces/<digest>`, else `~/.local/state/...`) and
the worker commits into the source repository's Git common directory. Host
sandboxes deny those writes:

- Codex `workspace-write`: writes cwd, `--add-dir` roots and temp; `.git` stays
  read-only. Needs `-c 'sandbox_workspace_write.writable_roots=["<git-common-dir>"]'`.
- Grok `--sandbox workspace|strict`: writes cwd, `~/.grok` (strict: `~/.grok/sessions`)
  and temp only (`~/.grok/docs/user-guide/18-sandbox.md`). Custom profiles in
  `~/.grok/sandbox.toml` take `extends` + `read_write`.
- Claude Code: prompts for or denies writes outside its working directories;
  `/add-dir` or `permissions.additionalDirectories` grants them.
- Native subagents inherit the parent's grants.

Before this change the failure surfaced mid-`prepare` (or later, at the worker's
first commit) as a generic exit-2 error, with no statement of which path to grant.

## Relationship to the ShipLoop preflight (2026-09-27, interim)

The task named ShipLoop's `_probe_writable` / `SHIPLOOP-GRANT-NEEDED` in
`skills/shiploop/scripts/shiploop_workspace.py` and
`docs/shiploop-grant-preflight-journal.md` on branch
`worktree-shiploop-grant-preflight-a3f9c1` as the pattern to reuse. At
`01a9a1f1` that branch has no commits: its worktree holds only an untracked
experiment harness (`test/experiments/shiploop_write_grants/{probe.py,run.sh,setup.sh}`),
and neither the function nor the journal exists. There was nothing to share yet.

Decision: implement the probe once, here, and expose it as the helper's
`preflight` subcommand. ShipLoop already runs this helper through its frozen
binding (`shiploop_chain._ask_agent_workspace`), so ShipLoop can probe its own
directories (for example `.shiploop-runs`) with
`preflight --source <repo> --path <dir>` instead of reimplementing the probe.
This journal is a separate file so it does not collide with the ShipLoop
branch's journal when that lands.

Follow-up for the ShipLoop branch: call `preflight` (or read `status:
grant-needed` / exit 3 from `prepare`) rather than adding a second `_probe_writable`.
ShipLoop surfaces `error[:1600]`; long absolute paths can push the block past
that, so ShipLoop should prefer the structured `blocked` rows. The helper does not
yet declare a `write-grant-preflight` capability; add it together with the
ShipLoop code that requires it, since ShipLoop's contract tests pin the set.

## Design (2026-09-27, firm)

- Probe = create and delete one `tempfile.mkstemp` file. It tests the store, or
  its nearest existing ancestor when the store does not exist yet, and
  `git rev-parse --path-format=absolute --git-common-dir`. It runs before
  `_resolve_store` creates any directory, and also on `prepare --receipt`.
- On any failure: create nothing, print a block delimited by
  `==== ASK-AGENT-GRANT-NEEDED ====` / `==== END ASK-AGENT-GRANT-NEEDED ====` to
  stderr, emit `{"status":"grant-needed","blocked":[{role,path,target,reason}],"error":<block>}`,
  exit **3** (exit 2 remains every other failure). The block lists every blocked
  path at once, states the intention (grant exactly these paths, rerun the same
  prepare), and gives the Claude, Codex and Grok grants with the paths filled in.
- When the probed ancestor differs from the intended store, the block names the
  target and suggests `mkdir -p <target>` outside the sandbox for a narrower grant
  (the nearest existing ancestor of a fresh default store can be as broad as `~`).

## Results

### R1 — hermetic tests (2026-09-27, firm)

`test/ask-agent-workspace.test.py`, python3.14 on macOS, real Git, `chmod 0555`
simulating a sandbox denial:

| Test | Asserts |
| --- | --- |
| `test_prepare_refuses_a_read_only_store_parent_before_creating_anything` | exit 3, marked block, host fixes, store left empty, branches and worktrees unchanged |
| `test_prepare_refuses_a_missing_store_under_a_read_only_parent` | probes the nearest existing ancestor; reports `target`; nothing created |
| `test_prepare_refuses_a_read_only_default_state_home` | default store under `XDG_STATE_HOME`; nothing created |
| `test_prepare_refuses_a_read_only_git_common_dir` | linked caller's common dir is `primary/.git`; Codex `writable_roots` fix; store not created |
| `test_prepare_reports_every_blocked_path_at_once` | both roles in one result |
| `test_preflight_reports_grants_without_creating_anything` | `granted` with three roles, nothing created; `caller-path` blocked → exit 3 |

Full file: 70 tests OK (132 s). Change-selected quick suites
(`test/run_suites.py --group quick --changed-from main`): see R2.

### R2 — change-selected quick suites (2026-09-27)

`python3 test/run_suites.py --group quick --changed-from main`: **28/28 suites
PASS** (`run-all.sh: PASS`), covering the four ask-agent suites, `skill-frontmatter`,
`test-groups`, `ci-policy`, 20 ShipLoop suites that bind this helper, and
`shiploop-mock-replay` (35 tests, 0 model calls). This run started before the
final note-placement edit (R3); `test/ask-agent-workspace.test.py` was rerun on
the final code afterwards: 70 tests OK.

### R3 — live Codex sandbox (2026-09-27, firm for Codex)

Question: does the probe catch a real sandbox denial, and are the suggested
grants sufficient? Setup: toy repo at `~/ask-agent-grant-exp-24cb4f/toy`
(outside every temp directory, which sandboxes allow), store
`~/ask-agent-grant-exp-24cb4f/store`. Host: `codex sandbox -c 'sandbox_mode="workspace-write"'`
(Codex CLI, macOS Seatbelt; no model call).

- Plain `workspace-write`, `preflight`: exit 3, both roles blocked with
  `PermissionError: Operation not permitted` (Seatbelt EPERM, not the EACCES
  that `chmod` gives; the probe treats both the same).
- Adding `-c 'sandbox_workspace_write.writable_roots=["<exp dir>","<toy>/.git"]'`,
  `prepare`: exit 0; `git worktree list` shows the registered
  `ask-agent/worker-*` worktree under the store. The grants the block suggests
  are sufficient for `prepare` on Codex.
- The experiment directory was deleted afterwards.

After R3 the "does not exist yet" note moved directly under its own row (it
printed after the `.git` row, which misattributed it).

## Open

- Grok and Claude live confirmation (exploratory): not run here because both need a
  model call. The ShipLoop branch's `test/experiments/shiploop_write_grants/run.sh`
  variants (`grok-workspace`, `grok-strict`, `claude-sandbox`) are the natural
  harness once committed.
- The worker's own first commit inside the granted Codex sandbox was not exercised;
  R3 covers `prepare` (worktree add writes to the same common directory).
