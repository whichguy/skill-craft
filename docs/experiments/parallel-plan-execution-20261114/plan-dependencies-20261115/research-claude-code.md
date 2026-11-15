Claude Code fan-out and fan-in, as of 2026-11-15. Sources were read on that date. Tags: [verified: official doc or source], [secondary source], [unverified], or "not found".

1. Plan representation and dependencies
- Task tools are TaskCreate, TaskGet, TaskList, TaskUpdate. TaskUpdate handles "status, dependencies, details, or deletes tasks." Exact dependency field names: not found. [verified: https://code.claude.com/docs/en/tools-reference.md]
- Tasks have three states (pending, in progress, completed). A task can depend on others and "shows as blocked" until they complete. [verified: https://code.claude.com/docs/en/agent-teams.md]
- Sharing: "set CLAUDE_CODE_TASK_LIST_ID to use a named directory in ~/.claude/tasks/". Tasks persist across compactions. [verified: https://code.claude.com/docs/en/interactive-mode.md]
- The task tools are on by default only for Opus 4.7, Sonnet 4.6, Haiku 4.5 and earlier. Other models need CLAUDE_CODE_ENABLE_TODO_TOOLS=1 or --allowedTools. [verified: https://code.claude.com/docs/en/tools-reference.md]
- Plan mode: plan files live in ~/.claude/plans/ or a configured plansDirectory. The docs do not describe plan steps or dependencies. [verified: https://code.claude.com/docs/en/permission-modes.md]

2. Readiness and claiming (agent teams, experimental)
- Enabled by CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1. Requires an interactive session; not available with -p. [verified: https://code.claude.com/docs/en/agent-teams.md]
- The lead assigns tasks, or a teammate self-claims the next unassigned, unblocked task. "Task claiming uses file locking to prevent race conditions." [verified: agent-teams.md]
- "Teammates don't self-claim a blocked task." [verified: agent-teams.md]
- "When a teammate completes a task that other tasks depend on, it unblocks the dependent tasks without any action from you." [verified: agent-teams.md]
- The docs say to avoid same-file edits and dependency-heavy work: "For sequential tasks, same-file edits, or work with many dependencies, a single session or subagents are more effective." [verified: agent-teams.md]

3. /batch
- Researches the codebase, splits the work into 5 to 30 independent units, and presents a plan. After approval it spawns one background subagent per unit in its own worktree. Each one implements, runs tests, and "opens a PR or reports what happened." Requires git or a WorktreeCreate hook. [verified: https://code.claude.com/docs/en/commands.md]
- Dependency handling and the merge of results: not found.

4. Subagent worktrees and merge-back
- isolation: worktree gives the subagent a temporary worktree. Its base is the default branch, or the current HEAD when worktree.baseRef is "head". It is removed automatically if it made no changes. [verified: https://code.claude.com/docs/en/worktrees.md; https://code.claude.com/docs/en/sub-agents.md]
- Changed worktrees stay until the periodic sweep (cleanupPeriodDays) can remove them without losing work. [verified: worktrees.md]
- No merge-back step is documented. Bringing a worktree branch into the integration branch is left to the user or the parent. [verified absence: worktrees.md; sub-agents.md]

5. Workflow tool (dynamic workflows)
- A JavaScript script calls agent(), pipeline() and parallel(). parallel() "runs a set of agent tasks at the same time and waits for all of them." [verified: https://code.claude.com/docs/en/workflows.md]
- Limits: 16 concurrent agents by default, 4,096 items per call, 1,000 agents per run. No mid-run user input. [verified: workflows.md]
- Resume is per session. A relaunch replays saved results. The first agent whose prompt changed reruns, and so does every agent after it. A Failed agent reruns, and so does every agent the script starts after it. [verified: workflows.md]
- An agent that stalls is restarted up to 5 times. Inside parallel() or pipeline() its slot becomes null. [verified: workflows.md]
- Availability: paid plans, API, Bedrock, Vertex and Foundry. Pro needs a setting in /config. [verified: workflows.md]

6. Fan-in hooks (verified from the hooks reference)
- TaskCreated: exit 2 rolls back the creation. TaskCompleted: exit 2 prevents the task being marked complete. TeammateIdle: exit 2 keeps the teammate working. SubagentStop: exit 2 keeps the subagent from stopping. [verified: https://code.claude.com/docs/en/hooks.md]
- WorktreeCreate: any non-zero exit fails creation, and stdout must be the path. WorktreeRemove fires only for hook-created worktrees. [verified: hooks.md]
- Input schemas were beyond the fetched text, so they are not described here. [not found in fetched text]

7. Completion and the integration branch
- Idle notifications go to the lead automatically and include the teammate's final answer. The lead synthesizes. [verified: agent-teams.md]
- No documented integration-branch owner or merge gate. In /batch and worktree flows, each unit lands in its own PR or branch. [not found]

8. Failure handling
- Teammates "may stop after encountering errors." The fix is to message them or spawn a replacement. A task can stay blocked if the teammate fails to mark it complete. In-process teammates are not restored after /resume. [verified: agent-teams.md]
- Workflow agents: see item 5. [verified: workflows.md]

9. Anthropic accounts
- C compiler post, dated Feb 5, 2026 by the fetched copy [verified: https://www.anthropic.com/engineering/building-c-compiler]. Agents claimed tasks with lock files in current_tasks/. Git sync stopped two agents taking the same task. Each agent cloned, pulled, merged, pushed, and removed its lock. Merge conflicts were "frequent." With 16 agents on one bug, "each was stuck solving the same task." The fix was GCC as an oracle. The author calls the verifier "nearly perfect" a requirement.
- Multi-agent research system, Jun 13, 2025. Poor fit for "domains that require all agents to share the same context" or "many dependencies between agents." Lead spawns "3-5 subagents in parallel." Multi-agent uses about 15x the tokens of chat. Recovery uses checkpoints and resuming from the failure point. [verified: https://www.anthropic.com/engineering/multi-agent-research-system]
- Claude blog, Jan 23, 2026. Parallel work pays off only with "context truly isolated." Sequential phases of one job are a poor split. "The primary benefit of parallelization is thoroughness, not speed." Costs are 3-10x tokens. [verified: https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them]

Bottom line for the harness question: Claude Code has no official dependency-aware scheduler that merges worktree branches back. Its own dependency blocking is in the experimental agent-teams task list. The Workflow tool supplies barriers and resume within one session. The integration step stays the harness's job. A useful reference point is that Anthropic's own docs send dependency-heavy and same-file work to a single session. Source searches did not surface any newer Anthropic engineering post on parallel-worker coordination. The docs and posts above are the basis for the claims.
