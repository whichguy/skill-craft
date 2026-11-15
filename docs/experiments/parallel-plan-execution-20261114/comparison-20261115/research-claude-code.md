<!-- verbatim final report of a research sub-agent, 2026-11-15, web research done by the agent: Claude Code sub-agents and worker features (claude-code-guide agent). A model report: its claims are the agent's, tagged by it; the ones I spot-checked are listed in README.md. -->

Claude Code sub-agents and worker features, as documented on 2026-11-15. Every claim is tagged [verified: official doc] unless noted. Each URL was fetched by me; where a page was truncated, I say so.

1. Spawn tool and agent types
- The spawn tool is `Agent`, renamed from `Task` in v2.1.63; old `Task(...)` references still work as aliases. Documented arguments: `subagent_type`, `model` (alias only), `effort`, `name`, `isolation`, plus a prompt string. [verified: https://code.claude.com/docs/en/sub-agents.md]
- Custom agents are markdown files in `.claude/agents/` with frontmatter (`name` and `description` required; also `tools`, `model`, `isolation`, `background`, `maxTurns`, `hooks`, `skills`, and others). [verified: sub-agents.md]
- Built-in types: Explore (read-only), Plan (read-only), general-purpose (all tools), plus `claude`, `statusline-setup`, `claude-code-guide`. [verified: sub-agents.md]
- A `run_in_background` argument is not documented in the sub-agents page I read; the agent-teams page refers to a teammate's `run_in_background: true` request. The exact schema: not found.

2. Foreground, background and concurrency
- Foreground subagents block the parent; background subagents run concurrently. With nothing configured, subagents Claude spawns start in the background. Ctrl+B moves a running one to the background. [verified: sub-agents.md]
- Several can run from one turn. The default cap is 20 running subagents; spawning a 21st fails with `Concurrent subagent limit reached` and is rejected, not queued. Raise it with `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. [verified: sub-agents.md]
- Dynamic workflows default to 16 concurrent agents, 1,000 agents per run, and 4,096 items per `parallel()` or `pipeline()` call. [verified: https://code.claude.com/docs/en/workflows.md]

3. Context model
- A non-fork subagent starts with a fresh context and does not see the parent's history. A fork (`/subtask`, or Claude starting one under fork mode) inherits the full conversation. [verified: sub-agents.md]
- Only the subagent's final message returns; intermediate tool calls stay out of the parent. [verified: https://code.claude.com/docs/en/agents.md and the SDK subagents page https://code.claude.com/docs/en/agent-sdk/subagents.md]
- A non-fork subagent inherits CLAUDE.md (except Explore and Plan), git status, its listed skills, and tools. It also inherits the parent's MCP servers and permission mode (unless `permissionMode` is set), and settings-level hooks. The model follows a fixed order: per-call `model`, then frontmatter, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the parent's model. Effort comes from frontmatter or the per-call value. Not inherited: output style, auto memory, the parent's conversation. [verified: sub-agents.md]

4. Worktree isolation
- `isolation: worktree` (frontmatter or per call) runs the subagent in a temporary git worktree. It branches from the default branch unless `worktree.baseRef` is `"head"`. If the subagent changes nothing, the worktree is removed; otherwise a periodic sweep keeps it. [verified: sub-agents.md; https://code.claude.com/docs/en/worktrees.md]
- Who merges the worktree's changes back: not found. The pages describe creation and cleanup only.

5. Agent teams (experimental, off by default)
- Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. The lead spawns teammates. Each teammate is a full session with its own context. Teammates share a task list (with file locking to claim tasks) and message each other through JSON mailboxes. [verified: https://code.claude.com/docs/en/agent-teams.md]
- Differences from subagents: teammates message each other directly, while subagents only report to the caller. Teams cost more tokens. Teammates cannot spawn teammates, and there is one team per session. Teams require an interactive session; in `-p` mode a named subagent runs as a plain subagent. [verified: agent-teams.md]
- Docs say to start with 3 to 5 teammates and to avoid two teammates editing the same file. [verified: agent-teams.md]

6. Agent SDK equivalents
- Define agents with the `agents` option (`AgentDefinition`: description, prompt, tools, model, `maxTurns`, `background`, `effort`, and others). Claude calls them through the `Agent` tool. [verified: https://code.claude.com/docs/en/agent-sdk/subagents.md]
- Depth, concurrency and spend are bounded by `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (default 3), `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20), and `maxBudgetUsd` / `max_budget_usd`. [verified: agent-sdk/subagents.md]
- For programmatic fan-out at scale the SDK points to the `Workflow` tool (dynamic workflows). [verified: agent-sdk/subagents.md]

7. Cost, latency and when to use
- Each subagent spends its own tokens and counts toward the same limits. Many subagents returning detailed results can use a lot of context. A non-fork subagent may take time to gather context. Route cheap work to Haiku. [verified: sub-agents.md]
- Agent teams: token usage scales with the number of active teammates; the costs page says teams use "approximately 7x more tokens than standard sessions when teammates run in plan mode." [verified: https://code.claude.com/docs/en/costs.md]
- Use subagents for focused work where only the result matters, and when a side task would flood the main context. Use teams when teammates must share findings and challenge each other. Use the main session for sequential or same-file work. [verified: https://code.claude.com/docs/en/agents.md; agent-teams.md]
- Enterprise average: about $13 per developer per active day, $150 to $250 per month (no source for this figure beyond the costs page). [verified: costs.md]

8. Anthropic multi-agent research system write-up
- Source: https://www.anthropic.com/engineering/multi-agent-research-system (I read it through the fetch tool; I did not record a publication date, so: not found).
- Token multiples: "agents typically use about 4× more tokens than chat interactions," and "multi-agent systems use about 15× more tokens than chats." [verified: the blog post]
- Results: an Opus 4 lead with Sonnet 4 subagents "outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval." Token usage alone "explains 80% of the variance" on BrowseComp. [verified: the blog post]
- Speedup: parallel subagents (3 to 5 spawned at once, tools run in parallel) "cut research time by up to 90% for complex queries." [verified: the blog post]
- Conditions: suited to "breadth-first queries that involve pursuing multiple independent directions simultaneously," heavy parallel work, information beyond one context window, and many complex tools. Unsuited where "the value of the task" cannot pay for the extra cost, where agents must share the same context, and for most coding tasks, which "involve fewer truly parallelizable tasks than research." [verified: the blog post]
