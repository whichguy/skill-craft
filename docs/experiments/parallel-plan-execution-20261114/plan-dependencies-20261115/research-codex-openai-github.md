Scope: Codex docs moved (developers.openai.com/codex/* 308-redirects to learn.chatgpt.com/docs/*); openai.com returned 403 to my fetcher. [verified] = official doc, source (openai/codex main, 2026-11-15) or paper read directly.

1. Codex plan tool
- Statuses only: update_plan steps are {step, status: pending|in_progress|completed}, extra fields rejected, at most one in_progress. Plan mode (markdown) and goals (one objective plus budget) carry no dependencies either. [verified] github.com/openai/codex/blob/main/codex-rs/core/src/tools/handlers/plan_spec.rs, codex-rs/protocol/src/plan_tool.rs

2. Codex subagents
- The model decides, only after an explicit user or AGENTS.md request (V2: proactive at Ultra effort). Tool text: split critical-path from sidecar work, give delegates disjoint write sets, wait sparingly, then review and integrate. [verified] codex-rs/core/src/tools/handlers/multi_agents_spec.rs
- Completion: V1 wait_agent returns final statuses; V2 wait_agent blocks on any mailbox update, final answers go to the parent. Caps: V1 6 threads, depth 1; V2 4 concurrent, depth cap ignored. [verified] core/src/config/mod.rs
- Same files: children inherit the parent's cwd; no locks or worktrees; worker-role text only says to assign file ownership and warn workers that others edit too; docs warn of conflicts. [verified] core/src/agent/child_config.rs, role.rs; learn.chatgpt.com/docs/agent-configuration/subagents

3. Codex app
- Threads can run in git worktrees (detached HEAD, 15 newest kept); Handoff moves a thread and code between Local and a worktree, or create a branch there then commit, push, PR. Conflict handling: not found. [verified] learn.chatgpt.com/docs/environments/git-worktrees

4. Codex cloud
- Each task has its own workspace; commit or open a PR when ready; Linear docs on dependencies: not found. [verified] learn.chatgpt.com/docs/cloud.md, /docs/third-party/linear
- Best-of-N: codex cloud exec --attempts 1-4; you pick via apply --attempt N, which runs git apply --3way after a --check preflight and lists conflicted paths. [verified] codex-rs/cloud-tasks/src/cli.rs, git-utils/src/apply.rs
- Official best-of-N doc, one-PR-per-task rule, cross-task conflict handling: not found.

5. Symphony exists: github.com/openai/symphony (Apache-2.0, Draft v1 SPEC.md plus Elixir reference, last commit 2026-09-15) [verified]; announced 27-28 Apr 2026 [secondary] helpnetsecurity.com/2026/04/28/openai-symphony-codex-orchestration-linear/
- Blockers: issues carry best-effort blocked_by plus an adapter-computed dispatchable flag. The Linear adapter blocks a Todo issue while any blocking issue is non-terminal; agents create follow-ups with blockedBy. [verified] SPEC.md; elixir/lib/symphony_elixir/linear/client.ex; elixir/WORKFLOW.md
- Readiness is script-owned: active state, dispatchable, labels, unclaimed, free slot (default 10); humans move Backlog to Todo. One reused directory per issue (reference hook: git clone, no worktrees). Each tick: kill stalled runs (300 s), stop and clean terminal issues, retry with backoff. [verified]
- Merge: Symphony never merges. Agent opens PR, human sets Merging, land skill merges main, fixes conflicts, waits for CI, squashes; Done then clears blockers. No cross-PR integration step. [verified] .codex/skills/land/SKILL.md

6. Agents SDK and Responses API
- LLM-driven (agents-as-tools, handoffs) or code-driven (asyncio.gather etc.); fan-in example: three parallel runs, then a picker agent. No dependency model; your code is the DAG. Cap: tool_execution.max_function_tool_concurrency, default None (all tool calls in a turn start together). [verified] openai.github.io/openai-agents-python/multi_agent/; openai-agents-python/src/agents/run_config.py
- Hosted multi-agent beta: max_concurrent_subagents default 3, no depth or total cap, mailbox wait_agent, root synthesizes; guide advises against it for dependent steps or contended mutable state. [verified] developers.openai.com/api/docs/guides/responses-multi-agent.md

7. GitHub
- /fleet (1 Apr 2026): decomposes work into items with dependencies, dispatches independent ones, polls, dispatches the next wave, verifies and synthesizes. Shared filesystem, no locking: "the last one to finish wins—silently" (GitHub's words). [verified] github.blog/ai-and-ml/github-copilot/run-multiple-agents-at-once-with-fleet-in-copilot-cli/
- Plan store: SQL todos and todo_deps; ready = pending with no unfinished dependency; agents claim one todo, end done or blocked; avoid overlapping files unless the parent reconciles. [verified] docs.github.com/en/copilot/how-tos/copilot-sdk/features/fleet-mode
- Cloud agent: one branch at a time, one PR per task. Agent HQ: assign an issue to Claude, Codex, Copilot or all three; overlap and sequencing are the human's job. [verified] docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent, github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/, github.blog/ai-and-ml/github-copilot/how-to-orchestrate-agents-using-mission-control/
- Agent Merge (28 Oct 2026): watches one PR, fixes failed Actions and/or conflicts; does not merge (auto-merge is separate); no stacked or fork PRs; CI re-run not stated. [verified] docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/watch-and-fix-pull-requests

8. Known problems
- Codex: in one thread, a drained weekly quota and 1,218 descendants from a bounded task under V2 (#35463); ~731 GiB of logs from 2,393 subagent files (#34061); chats and subagents overwriting one Local checkout (#37226). [secondary] github.com/openai/codex/issues/{35463,34061,37226}
- Copilot: PR went stale (agent works from a snapshot), fixed by a 26 Mar 2026 conflict-resolution changelog; a fleet saturated one host (#4688). [secondary] github.com/orgs/community/discussions/185521, github.com/github/copilot-cli/issues/4688
- Measured (abstracts): co-active agent PRs conflict 19.8% (same agent) vs 41.7% (cross-agent); a claim log cut duplicate work 78% to 0%. [verified] arxiv.org/abs/2607.04697, arxiv.org/abs/2606.19616. Codex/Copilot-specific duplicate-work reports: not found.

Net: only /fleet (todo_deps) and Symphony (tracker blocks) store dependencies as data; Codex relies on model judgment; none lock files.
