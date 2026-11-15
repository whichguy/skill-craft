<!-- verbatim final report of a research sub-agent, 2026-11-15, web research done by the agent: Cursor, OpenCode, Gemini CLI, Amp, Cline, Roo, Aider, OpenHands, Deep Agents. A model report: its claims are the agent's, tagged by it; the ones I spot-checked are listed in README.md. -->

Unless tagged [secondary] or [unverified], every claim is [verified] from the official doc, changelog or source at the URL shown (fetched raw 2026-11-15). "Not found" means absent from those pages.

**Cursor** (https://cursor.com/docs/subagents)
- Spawn: Task tool (several calls in one message = parallel) or `/name`; files `.cursor/agents/*.md` (also `.claude/agents`, `.codex/agents`) with `name, description, model, readonly, is_background`; `/multitask`; the Agent SDK uses a `task` tool.
- No numeric cap stated (docs suggest 2-3); nesting capped at two levels; async since 2.5 (2026-02-17). Child starts clean; parent gets only the final message plus a resumable agent ID.
- Shared checkout by default; on request each subagent gets its own branch in a git worktree or cloud VM, "until the parent agent merges". `/best-of-n` never merges (https://cursor.com/docs/configuration/worktrees). Cloud Agents (ex-Background) = VM + branch + PR (https://cursor.com/docs/cloud-agent).
- Planner/worker research: https://cursor.com/blog/scaling-agents (2026-01-14: hundreds of workers push to one branch, integrator dropped), https://cursor.com/blog/self-driving-codebases (02-05: root planner, subplanners, workers; own repo copy, one handoff report up; peak ~1,000 commits/hour), https://cursor.com/blog/agent-swarm-model-economics (07-20: frontier planners, cheap workers, own VCS, neutral merge-conflict agent), https://cursor.com/blog/projects (09-10 beta: coordinator writes no code, delegates to cloud subagents).

**OpenCode** (V2 current: https://opencode.ai/docs/agents/; V1: https://opencode.ai/v1/docs/agents/)
- V2 `subagent` tool (`agent, description, prompt, model, sessionID`); agents are `.opencode/agents/*.md` with `mode: subagent`; permission action `subagent`. V1 used `task`, `permission.task` and `@general ...` mentions; V2 `@` attaches files, subagent @-mention not found.
- Always background and concurrent since v2.3.0 (2026-11-13, https://opencode.ai/changelog/v2.3.0); no cap found; nesting depth 1 (`experimental.subagent_depth`, source `packages/core/src/tool/plugin/subagent.ts`).
- Fresh child session; parent receives a `<subagent>` message whenever the child idles. No per-subagent worktree or merge step documented.

**Gemini CLI** (https://geminicli.com/docs/core/subagents/)
- Docs banner: Antigravity CLI replaced it for unpaid and Google One users on 2026-06-18; API-key and enterprise users keep it (https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/); v0.64.0 shipped 2026-10-13.
- Each subagent is a tool of its own name; auto-delegation or leading `@name`; `.gemini/agents/*.md` fields `name, description, kind, tools, mcpServers, model, max_turns` (30), `timeout_mins` (10); nav marks it experimental.
- Parallel supported but the 2026-04-15 post warns about conflicting edits (https://developers.googleblog.com/subagents-have-arrived-in-gemini-cli/); no cap stated. Own context, summary returns, subagents cannot call subagents. Worktrees are per session (`experimental.worktrees`), not per subagent; no merge step.
- Antigravity: `invoke_subagent`, workspace `inherit|branch|share`, depth 10 (https://antigravity.google/docs/subagents).

**Amp** (https://ampcode.com/docs/models-and-subagents)
- `Task` tool plus Read Thread; Oracle, Librarian, Finder are now Task roles; plugins `@amp/oracle|librarian|finder` restore them as tools (oracle advises, never edits). Custom agents: plugin `amp.createAgent` (25 workers, 2026-06-19).
- Independent work may split across several subagents; no cap stated. Own context, no cross-talk; parent gets the final summary and can re-task a child.
- Task-subagent worktree isolation not documented. Orb threads get their own machine and working copy (https://ampcode.com/docs/orbs/agent-to-agent); orb starts burst 20, then one per five minutes (https://ampcode.com/docs/orbs); default Ship rebases and pushes to trunk (https://ampcode.com/docs/orbs/shipping).

**Cline** (https://docs.cline.bot/features/subagents)
- `spawn_agent`, CLI and Desktop only; "several" run at once, no cap; separate context; Act-mode children can edit, get no MCP, may spawn children; one approval covers all; the final reply returns. `/newtask` is only a context handoff.
- `/team` coordinator tools `team_spawn_teammate`, `team_task`, `team_run_task` (https://docs.cline.bot/cli/agent-teams). Kanban preview: one ephemeral git worktree per card; Commit/Open PR has the agent merge (https://docs.cline.bot/usage/kanban).

**Roo Code**
- Shut down 2026-05-15, repo archived (https://github.com/RooCodeInc/Roo-Code); announced 2026-04-21 [secondary]. Last design (https://docs.roocode.com/features/boomerang-tasks): Orchestrator mode calls `new_task` (`mode`, `message`, `todos`); parent pauses, so one task runs at a time; isolated history; only the `attempt_completion` result returns; no worktrees; sequential-queue PR #12335 closed unmerged.

**Aider**
- No subagents found; only sequential architect then editor models (https://aider.chat/docs/usage/modes.html); upstream last pushed 2026-05-22. Fork cecli: `Delegate` tool, `/spawn-agent` (https://github.com/cecli-dev/cecli).

**OpenHands** (https://docs.openhands.dev/sdk/guides/task-tool-set)
- `TaskToolSet`: `task(prompt, subagent_type, description, resume)`; synchronous; parallel only via parent `tool_concurrency_limit` (default 1, experimental); `WorkflowToolSet` `wf.map_agents(max_concurrency)`; old `DelegateTool` deprecated v1.60.0 (source).
- Child shares the parent's working dir (source `task/manager.py`); returns `TaskObservation`; Agent Canvas can give each conversation its own Docker container; Software Factory watchdog merges on passing statuses.

**Deep Agents** (https://docs.langchain.com/oss/python/deepagents/subagents)
- `task(subagent_type, description)`; `create_deep_agent(subagents=[...])`; default `general-purpose`; several calls per turn run in parallel but block; `mode` isolated (default, may nest) or fork (cannot call `task`); returns last message or `response_format` JSON.
- Async (v0.5, 2026-04-07): `start_async_task`, `check_async_task`, `update_async_task`, `cancel_async_task` on Agent Protocol servers (https://docs.langchain.com/oss/python/deepagents/async-subagents). State backend shared; no worktrees or merge step.
