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

## Relationship to the ShipLoop preflight (2026-09-27, superseded 2026-09-27 by "One shared module")

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

## Design (2026-09-27, superseded 2026-09-27 by "One shared module": message format, `target` field and store grant changed)

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

### R4 — worker commit inside the Codex sandbox (2026-09-27, firm)

Same setup as R3, after a granted `prepare`, run with `codex sandbox` in
workspace-write mode:

- Grants `writable_roots=[store, toy/.git]`: the worker's `git add` + `git commit` in
  the prepared worktree succeeds (`6519542 work`).
- Grant `writable_roots=[store]` only: the commit fails, `Unable to create
  '.../toy/.git/worktrees/worktree/index.lock': Operation not permitted`, exit 128.

So the `.git` grant is needed by the worker itself, not only by `prepare`. A
worktree's index lives under the common directory's `worktrees/`.

### R5 — live Grok `--sandbox workspace` (2026-09-27, firm)

`grok -p` (default model) ran `preflight --source toy --store <exp>/store`
from `toy`: `STATUS=grant-needed EXIT=3`. The store parent lies outside cwd.
Side observation, not ask-agent: that Grok session's stop hook reported the
ShipLoop hook script missing at its path, and the stop hook re-prompted the model
several times.

### R6 — live Claude Code Bash sandbox (2026-09-27, firm; the block is resolved by R7 + R9)

`claude -p` with settings `sandbox.enabled=true, autoAllowBashIfSandboxed=true,
allowUnsandboxedCommands=false`, with and without `--add-dir <exp>`: the probe
never ran. `preflight` exited 2 with `refuses Git context environment overrides:
GIT_CONFIG_COUNT, GIT_CONFIG_KEY_0, GIT_CONFIG_KEY_1, GIT_CONFIG_PARAMETERS,
GIT_CONFIG_VALUE_0, GIT_CONFIG_VALUE_1`. A second session showed only
`GIT_CONFIG_PARAMETERS`. `git config --list --show-scope` there listed the
command-scope keys `http.proxyauthmethod` and
`credential.http://localhost:<port>.helper`: the sandbox's network proxy. The
same session without the sandbox has no `GIT_CONFIG_*`.

Consequence: under Claude's Bash sandbox every helper operation (prepare,
preflight, current-state, context checks) fails, whatever is granted. The
`/add-dir` advice is necessary but not sufficient there. This predates the
preflight (`853254fe` introduced the refusal).

Attempted fix, not applied: treat injected configuration made only of `http.*` and
`credential.*` keys, parsed exactly from both forms and failing closed on anything
unparseable, as not a context override. The helper's own Git calls already strip
these variables. The session's permission classifier denied the edit as weakening
a security check, so it needs the owner's decision. Documented instead as a known
limitation in `references/host-capabilities.md` (Claude Code) and the
workspace-operations grant table.

### ShipLoop preflight landed separately (2026-09-27, superseded 2026-09-27 by "One shared module")

Supersedes part of "Relationship to the ShipLoop preflight" above: branch
`worktree-shiploop-grant-preflight-a3f9c1` has since committed `70a174e6`,
adding `skills/shiploop/scripts/shiploop_grants.py` (`require`, `GrantError`,
`detect_host`, `report`, exit 3, `SHIPLOOP-GRANT-NEEDED`). There are now two
probes. Its report adds things the ask-agent block lacks: host detection with the
detected host's fix first; no-restart options (Claude `/add-dir`; Codex Full
access in `/permissions`); a `mkdir -p` line for grants that do not exist yet; the
exact rerun command; and an explicit "do not work around it" line for the agent.

The packages cannot import each other. The ask-agent helper must run as one file,
including under `python -I` (tested), which drops the script directory from
`sys.path`. The only in-repo precedent for cross-package reuse is Improve's vendored
Until Loop runtime, pinned by SHA-256 in a provenance manifest and checked by
`test/improve.test.sh`. Unifying the two needs a decision on the ShipLoop branch's
unmerged code; see Open.

### R7 — transport-only injected Git config (2026-09-27, firm)

Owner decision (2026-09-27): accept injected Git configuration made only of
`http.*` and `credential.*` keys. `_git_context_environment_overrides` now
parses `GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n` and `GIT_CONFIG_PARAMETERS` exactly.
It returns no override only when every present `GIT_CONFIG_*` variable belongs to
those forms, the indexed set matches the count exactly, and every key is
transport. Anything else, including unparseable quoting, a key beyond the count,
a non-numeric count or any other context variable, is still refused.
Test: `test_prepare_accepts_sandbox_injected_config_and_refuses_anything_wider`
(2 accepted forms, 6 refused cases). The earlier attempt was denied by the
permission classifier (R6); it was applied after the owner's explicit approval.

### R8 — Claude sandbox also injects `safe.directory` (2026-09-27, firm; the block is resolved by R9)

Live `claude -p` with the Bash sandbox, printing key names only:
`GIT_CONFIG_PARAMETERS` carries `http.proxyAuthMethod` and
`credential.http://localhost:<port>.helper`; `GIT_CONFIG_COUNT=2` carries
`safe.directory` twice, with values `<cwd>` and `<cwd>/*`. This held for plain,
piped and `cd &&` command shapes. An inline `python3 -c` dump in one session
showed no COUNT form; the file-based probe showed it in every shape. After R7 the
helper still refuses because `safe.directory` is not transport. It is a trust
setting (it waives Git's ownership check for those paths), not a repository
redirect. Whether to accept it is the owner's call; until then Claude's Bash
sandbox remains a documented limitation.

### One shared module (2026-09-27, firm)

Owner decision (2026-09-27): one probe, vendored. ShipLoop's preflight shipped to
main (`70a174e6`, `1c92ca7d`, release `355aa513`). Its `shiploop_grants.py` was
generalized into `host_write_grants.py`: `Product(marker, outcome, profile,
workarounds)` parameterizes `report()`. The module is vendored byte-identically as
`skills/ask-agent/scripts/host_write_grants.py` and
`skills/shiploop/scripts/host_write_grants.py`; `test/host-write-grants.test.py`
(new core suite, groups ask-agent + quick) fails when they differ.
`shiploop_grants.py` keeps only ShipLoop's wording.

Integrity: the ask-agent helper was single-file. ShipLoop freezes an explicit
ask-agent file list (`_MANAGED_ASK_AGENT_FILES`) and the helper's `identity`
binds one helper hash. So `scripts/host_write_grants.py` joined the frozen list,
and a chain bound earlier is refused and must bind again (one supported
version). The helper loads the module by path with `compile`/`exec`, not
import. That works under `python -I` (covered by the copied-package test) and
writes no bytecode into the package.

Lessons adopted from the ShipLoop session (cross-session note, 2026-09-27):
- Grant only refused paths. The default store grants the stable
  `<state>/ask-agent` base, so one grant covers every repository.
- Recheck on every write path: `prepare --receipt`, `inspect`, `close` and
  `check-context` probe before `_attempt_lock` (which itself writes a lock file).
  Test: `test_existing_attempt_commands_recheck_grants_before_writing`.
- Detect the innermost host first (Codex, then Grok, then Claude) and list its fix
  first. Test: `test_grant_report_names_the_detected_host_first`.
- An explicit agent stop line forbidding workarounds (another `--store`, the
  source checkout, another route).

Live (codex sandbox, workspace-write): exit 3; `Detected host: codex` with
Codex's fix first; grants = store + `.git`; `mkdir -p` for the missing store;
nothing created.

### R9 — cwd-scoped `safe.directory`; Claude sandbox works end to end (2026-09-27, firm)

Owner decision (2026-09-27): accept `safe.directory` only when every value is
the process's current directory or `<cwd>/*`, compared after `realpath`.
`*`, any other path, a subdirectory and an empty value are refused. The ShipLoop
session noted that its Git runners strip all injected `GIT_CONFIG_*`, which is why
ShipLoop was never blocked. The owner chose the narrower acceptance for ask-agent,
because a worker inherits the environment.
Test: `test_prepare_accepts_sandbox_injected_config_and_refuses_anything_wider`
(3 accepted forms including Claude's exact combination; 10 refused cases).

Live `claude -p`, Bash sandbox on (`enabled`, `autoAllowBashIfSandboxed`,
`allowUnsandboxedCommands=false`), full `prepare`:
- No grant: `grant-needed`, blocked `['workspace-store']` only. `.git` of the repo
  in cwd is writable under Claude's sandbox, as ShipLoop measured.
- `--add-dir <store>` with the store not yet created: still `grant-needed`.
  `/add-dir` of a missing directory does not grant it, so the message's
  `mkdir -p` line matters.
- `mkdir -p <store>` then `--add-dir <store>`: `STATUS=prepared`,
  `ask-agent/worker-048e471a8123`, worktree registered under the store.

### R10 — suites after the shared module (2026-09-27, firm)

- `test/run_suites.py --group quick --group ask-agent --changed-from main`:
  37/37 PASS, including `host-write-grants`, `shiploop-workspace` (57),
  `shiploop-chain-planning-context`, `test-groups` (core 39, total 102 suites)
  and `ci-policy`.
- `test/shiploop-chain-lifecycle.test.py` run directly (the selection missed it
  although it pins the frozen ask-agent file set): 51 tests OK, 1360 s.
- After R9's helper change: `--group ask-agent` 10/10 PASS.

## Open

- Grok stop hook reports a missing ShipLoop hook script (R5 side observation;
  filed as a separate task).
- Not exercised live: a Claude native subagent (rather than `claude -p`) inheriting
  the parent's `/add-dir` grant.
