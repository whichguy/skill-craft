# ShipLoop sandbox write-grant preflight — journal

## Question (2026-09-27)

ShipLoop's isolated run creates its worktree and run state beside the repo
(`<repo-parent>/.shiploop-runs/…`) and commits through the repo's shared Git
directory. Do host harnesses refuse those writes, and should ShipLoop check at
start and stop with a clear repair instead of failing mid-run?

## Research (web, 2026-09-27) — status: firm for the cited versions

No useful Reddit threads were found; GitHub issues and vendor docs were specific:

- Codex `workspace-write` re-mounts `.git` read-only even inside cwd, and a
  linked worktree's gitdir lives in the main repo's `.git/worktrees/`, so
  worktree commits fail ([openai/codex#48717](https://github.com/openai/codex/issues/48717),
  [#27418](https://github.com/openai/codex/issues/27418),
  [codex-plugin-cc#765](https://github.com/openai/codex-plugin-cc/issues/765),
  [writable_roots fix](https://gallon.me/letting-codex-agents-commit-making-git-writable-in-the-workspace-write-sandbox.html)).
  Mid-session: `/permissions` ([docs](https://developers.openai.com/codex/concepts/sandboxing)).
- Claude Code: file access is the start directory plus `--add-dir` /
  `additionalDirectories`; `/add-dir` works mid-session
  ([permissions](https://code.claude.com/docs/en/permissions)). `isolation: worktree`
  subagents in `.claude/worktrees/` hit a `.claude/**` write deny
  ([#47134](https://github.com/anthropics/claude-code/issues/47134)).
- Grok Build: sandbox off by default; `workspace`/`strict` write only cwd,
  `~/.grok`, temp; custom profiles in `~/.grok/sandbox.toml`
  (`extends`, `read_write`); a sandbox cannot be relaxed mid-session
  ([docs](https://docs.x.ai/build/features/sandbox),
  [user guide](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/18-sandbox.md)).

## Experiment 1 — per-host probe (firm)

Harness: `test/experiments/shiploop_write_grants/` (`setup.sh`, `probe.py`,
`run.sh`), toy repo under `$HOME` so temp-dir allowances cannot hide a refusal.
Hosts: codex-cli 0.157.1 (direct `codex sandbox` and model-driven `codex exec`,
default model), grok 1.0.41 (default model), Claude Code 2.1.283 (`-p`,
bypassPermissions to isolate the sandbox). Results:
`test/experiments/shiploop_write_grants/results-2026-09-27.md`.

Findings:

1. Codex default mode refuses both the sibling parent and `.git`; granting both
   via `sandbox_workspace_write.writable_roots` fixes worktree add and commit.
2. Claude's Bash sandbox and Grok's `workspace` profile refuse only the sibling
   parent; `.git` is writable because the repo is cwd. `--add-dir` fixes Claude.
3. Claude and Grok defaults (no sandbox) allow everything, which is why failures
   looked intermittent: they depend on mode, not layout.
4. A child (in-repo) worktree would not fix Codex (`.git` stays read-only) and
   under `.claude/worktrees/` breaks Claude subagents — keep the sibling layout.
5. Host env inherits through nesting (a Codex shell launched from Claude still
   has `CLAUDECODE=1`), so detection checks Codex, then Grok, then Claude.

## Change (this branch)

- `skills/shiploop/scripts/shiploop_grants.py`: one real create/delete probe per
  target; `GrantError`; host detection; the `SHIPLOOP-GRANT-NEEDED` report with
  blocked paths, repair intent, host-first fixes, rerun command, and an explicit
  "do not work around it" line for the agent.
- `workspace start` probes the root's parent and the Git common directory before
  its first write; exit 3. `--workspace-root` is optional, defaulting to a new
  `<repo-parent>/.shiploop-runs/<repo>-<stamp>` so one grant covers later runs.
- Every run-bound verb (and `plan-return`/`return`) re-probes run dir, worktree
  and Git dir, catching a harness restarted without grants.
- Tests: `test/shiploop-workspace.test.py` (read-only parent, read-only `.git`,
  default root, lost grant on resume, host-first report).

## Experiment 2 — acceptance (firm)

`run.sh shiploop-codex`: exit 3 with the block, nothing created.
`run.sh shiploop-codex-grant`: exit 0, first packet. See results file.

## Open

- Claude mid-session `/add-dir` extending Bash-sandbox write roots is inferred
  from docs plus the `--add-dir` run, not observed interactively. (interim)
- Codex `/permissions` → Full access is from docs, not observed. (interim)
- ask-agent `prepare` needs the same check (to-do filed).
- Grok global keepalive hook points at a retired plugin dir (to-do filed).
