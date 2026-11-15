Tags: [V] official doc/source/paper, [S] secondary, [U] unverified; n/f = not found. Dates 2026. Web pages read via a summarizing fetcher.

**Superpowers** v7.0.2, 11-03 [V] (https://github.com/obra/superpowers)
- Plan: markdown tasks with Files and Interfaces (Consumes/Produces); no dependency or parallel fields. A controller model walks tasks serially and keeps the ledger; scripts build the workspace and review packages; a pre-flight table checks every task pair sharing a file or interface. One worktree per plan; parallel implementers are forbidden (conflicts).
- Fan-in: none, no concurrent workers. Per-task review, one whole-branch review and fix wave; for a local merge the finishing skill reruns tests on the merged result, and the human picks merge or PR. Parallel dispatch only for independent read/fix domains. Agent-teams request [#429](https://github.com/obra/superpowers/issues/429) still open.

**CCPM** [V] (https://github.com/automazeio/ccpm)
- Front matter `depends_on`, `parallel`, `conflicts_with`; per-issue streams list files. `next.sh` script computes ready (deps closed, no active conflict); model launches agents. One worktree per epic, shared by agents scoped by file pattern. Streams self-report; conflicts never auto-resolved (agents pause); epic merge: tests, then `--no-ff` to main, no retest. [#530](https://github.com/automazeio/ccpm/issues/530): parallel-worker agent did not code.

**Task Master** 0.43.1, 03-31 [V] (https://github.com/eyaltoledano/claude-task-master)
- `dependencies` id lists. `findNextTask` script returns one item; no claim or lock, and in-progress tasks stay eligible, so two sessions get the same task; `list --ready` added 01-15 for parallel sessions. Worktree plus tag per session. Autopilot design: serial script state machine (RED, GREEN, COMMIT). Fan-in n/f. [#1139](https://github.com/eyaltoledano/claude-task-master/issues/1139): orchestrator agents kill parallelism (subagents cannot spawn subagents).

**Spec Kit** v1.4.0, 11-10 [V] (https://github.com/github/spec-kit)
- `T012 [P] [US1]`: [P] = different files, no dependencies; no depends-on field ([#1934](https://github.com/github/spec-kit/issues/1934) closed stale 09-25). Model decides; same-file tasks sequential; no isolation or fan-in (worktree request [#1476](https://github.com/github/spec-kit/issues/1476) closed 04-14).

**BMAD** [V] (https://github.com/bmad-code-org/BMAD-METHOD)
- Sequential; maintainers say use worktrees and watch story dependencies (#1855); #2849 open: concurrent runs share worktree, sprint-status and commits. Community [BAD](https://github.com/stephenleo/bmad-autonomous-development): model coordinator, graph from sprint-status.yaml, 3 stories per batch in worktrees, PR each, optional sequential auto-merge (lowest number first), subagent resolves conflicts.

**Kiro** [V] (https://kiro.dev/changelog/ide/0-12/)
- 05-06: Run all tasks infers a dependency graph from tasks.md into waves; [blog](https://kiro.dev/blog/faster-smarter-specs/): "Tasks that touch the same files are never run in parallel." Isolated context per task; failures do not stop others; agent opens a PR at the end. Merger, conflicts, merged-result tests n/f. [Crew](https://kiro.dev/docs/crew/features/task-runner/) task runner: batches of 3, branch plus worktree per task, per-step tests, independent diff reviewer, revert on failure (reviewer errors pass).

**Beads / Gas Town** [V] (https://github.com/steveyegge/beads, https://github.com/steveyegge/gastown)
- Beads: edges blocks, parent-child, conditional-blocks, waits-for; `bd ready` script; `bd ready --claim` atomic; fan-in = merge node depending on all parts; `merge-slot` exclusive lock.
- Gas Town: user or Mayor (model) slings; daemon feeder (script) honors `blocks`; worktree per polecat; `gt done` pushes branch, files MR; single-threaded Refinery rebases batches (max 5), gates merged tip, bisects on red; conflict becomes a task under the merge slot; epics merge to an integration branch, landed as one merge commit. Limit [S]: ~175 commits/day vs 30-min build, queue past 100, Yegge stopped gating main ([essay page](https://yegge.ai/listings/the-shape-of-things-to-come.html), [critique](https://julien.danjou.info/blog/steve-yegge-deleted-the-wrong-thing)).

**Squad, Conductor, Vibe Kanban** [V]
- No plan graph; worktree per session; human merges ([Squad](https://github.com/smtg-ai/claude-squad)). [Conductor](https://www.conductor.build/docs/concepts/parallel-agents): separate workspaces for tasks that can land independently, one shared workspace otherwise; conflicts n/f. [Vibe Kanban](https://vibekanban.com/blog/shutdown): one-level sub-issues, no blocked-by, conflicts manual; company shut down 04-10, community-maintained.

**Cline Kanban and /team** [V]
- [Kanban](https://docs.cline.bot/kanban/core-workflow): dependency edges; trashing (finishing) an upstream card auto-starts linked cards; worktree per card; Commit merges into base, agent handles conflicts if base moved; research preview.
- [/team](https://github.com/cline/cline) (sdk/packages/shared/src/team/types.ts): tasks have `dependsOn`, computed `isReady`; `claimTask` throws while dependencies are open; run leases, heartbeats; text results merge as reviewed fragments; no worktrees or code merge.

**Augment Intent** [V, vendor claims]
- Coordinator (model) writes spec and waves; implementor per worktree; Verifier checks the spec; Coordinator reconciles file overlap at merge ([guide](https://www.augmentcode.com/guides/intent-walkthrough-prompt-to-merge)). Now [intentapp.dev](https://www.intentapp.dev/docs): `@@@task dependsOn= conflictsWith=`; readiness, conflict resolution n/f. A reviewer became the bottleneck on a 5-ticket epic [S].

**Factory Missions** [V] (https://factory.com/news/missions-architecture, 04-10)
- Features, milestones, validation contract; runner spawns one worker per feature in order. Serial by design: parallel writers conflict; only read-only work is parallel. Completion = handoff; milestone validators; fix features until pass; blocked halts. No dependency field.

**Devin** [V] ([03-19](https://cognition.com/blog/devin-can-now-manage-devins), [04-22](https://cognition.com/blog/multi-agents-working))
- Manager (model) spawns child Devins, own VM each, resolves conflicts and compiles results (mechanism n/f). April: parallel-writer swarms do not work; keep writes single-threaded; children assume shared state; merged-result verification not addressed.

**Cursor** [V] ([01-14](https://cursor.com/blog/scaling-agents), [02-05](https://cursor.com/blog/self-driving-codebases), [Projects 09-10](https://cursor.com/blog/projects))
- Locks: 20 agents performed like 2-3; optimistic concurrency: risk-averse. Final: planners assign, workers resolve conflicts and push to one branch; integrator removed; handoff to planner; steady error rate plus periodic green-branch fixup; no dependency graph. Projects: dependency, merge detail n/f.

Patterns: bare id-list edges with different-files or conflicts_with as the parallel gate; scripts compute ready sets only in tracker systems (Beads, CCPM, Task Master, Cline /team, Gas Town), prompt-only systems leave it to the model; worktree or VM per worker, merge by human PR, queue, or the worker; Factory, Cognition and Superpowers keep writes single-threaded.
Best fan-in (my judgment, no published comparisons): a script-owned serial merge queue onto one integration branch (Gas Town Refinery, Beads merge-slot, BAD) that rebases each worker branch on the tip, gates the merged result and returns conflicts or red to a worker as a new task; Cursor dropped its agent integrator; Yegge's gating broke at ~175 commits/day.
