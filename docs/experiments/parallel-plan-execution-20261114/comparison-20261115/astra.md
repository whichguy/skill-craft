<!-- verbatim answer, 2026-11-15; command: ask.sh astra ask --json --effort max --profile consult --cwd <repo> "$(cat brief.txt)"; model_used=gpt-6-astra served_model=None effort=max profile=consult fallback=False exit=0 sandbox=read-only -->

**A. Harness comparison**

I formed the initial A/B analysis before inspecting the appendix files, then checked vendor sources. Web access was available; sources below were checked **2026-11-15**. No files were changed.

**[High]** means directly supported; **[Med]** means reasoned inference; **[Low]** means tentative. Tags apply to the whole row or paragraph. **Unknown** means unverified, not necessarily unavailable. Unversioned documentation describes its November 15 snapshot, not every installed build.

| Harness | Spawn, execution and waiting | Context, isolation and integration | Capacity, nesting, cancellation and continuation | Vendor cost/latency guidance |
|---|---|---|---|---|
| **[High] Claude Code**, current 2.1.x docs | `Agent` receives a task prompt and agent type. Background completion pushes a notification; foreground waiting depends on mode. | Non-fork workers start fresh and return summaries; forks inherit conversation. Shared checkout unless worktree isolation is selected; integration remains separate. | Normally 20 running subagents; excess spawns fail rather than queue. Configurable nesting defaults to three layers. `TaskStop` stops; `SendMessage` continues eligible workers. `TaskOutput` was removed in 2.1.277. | Additional usage; fresh context can make quick tasks slower. [Subagents](https://code.claude.com/docs/en/sub-agents), [tools](https://code.claude.com/docs/en/tools-reference). |
| **[High] Codex CLI 0.169.0**, v2 tools exposed here | `spawn_agent({task_name,message,fork_turns:"none"})`; asynchronous messages/results. `wait_agent({timeout_ms:…})` waits for mailbox activity and returns early. | `"none"` starts fresh; `"all"` inherits history. Shared filesystem here; no implicit worker worktree. Parent owns integration. | This session exposes four active slots including the parent; that is not a universal product limit. Nesting is supported; universal depth/queue policy unknown. `interrupt_agent` interrupts; `followup_task` continues. | OpenAI warns of additional tokens and recommends starting with read-heavy parallelism. [Versioned tool source](https://raw.githubusercontent.com/openai/codex/rust-v0.169.0/codex-rs/core/src/tools/handlers/multi_agents_spec.rs), [guidance](https://developers.openai.com/codex/subagents). |
| **[High] Codex Cloud**, November docs | Submit remote tasks through the product UI; native parent-spawn API for separate cloud tasks **unknown**. | Each task has its own workspace and continues remotely. User reviews changes and can request follow-ups or open a PR. This is distinct from a local child conversation. | Universal concurrency, queueing, nesting and programmatic cancellation contract **unknown**. | Published environments reuse setup; no quantitative worker-speed guarantee established. [Cloud documentation](https://developers.openai.com/codex/cloud). |
| **[High] Grok Build**, published source/docs | `spawn_subagent`; public source maps the background parameter to `background`, while the guide calls it `run_in_background`. Completion pushes notifications; `get_command_or_subagent_output` supports snapshots or timed waits. | Fresh context, summary return; shared workspace or explicit worktree. Parent integrates isolated changes. | Guide specifies one worker layer; concurrent cap/queue policy **unknown**. `kill_command_or_subagent` stops; `resume_from` continues completed context. | Avoid work whose context setup exceeds its parallel benefit. [API mapping](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-agent/src/config.rs), [subagents](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/16-subagents.md), [lifecycle](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/20-background-tasks.md). |
| **[High] Cursor**, November docs | Multiple `Task` calls can launch together. Foreground blocks; background returns immediately. Parent can inspect background output files. | Fresh context and final report. Shared checkout by default; optional isolated worktree/cloud branch, merged by parent. | Since 2.5, two worker layers are supported. Capacity/queue policy **unknown**. Resume supported; exact cancellation API **unknown**. | Explicitly warns about startup, extra tokens and slower simple tasks. [Documentation](https://cursor.com/docs/subagents). |
| **[High] OpenCode**, November docs | Current docs name `subagent`, returning `sessionID` immediately; parent receives reports when the child becomes idle. | Fresh child session. Automatic filesystem isolation **unknown**; separate worktree tools exist. Integration must be assigned explicitly. | Default nesting depth one; configurable. Reuse `sessionID` to continue. Capacity, queueing and cancellation API **unknown**. | Quantified cost/latency guidance **unknown**. These current APIs should not be substituted into older `task` recipes. [Tools](https://opencode.ai/docs/tools/), [agents](https://opencode.ai/docs/agents/). |
| **[High] LangChain Deep Agents**, November docs; notifications require ≥0.7.26 | `task` blocks the supervisor, although several tasks can execute concurrently. `start_async_task` returns immediately; Agent Server can notify, otherwise use `check_async_task`. | Isolated context by default; fork available. Context separation does not establish filesystem isolation; backend and integration are application responsibilities. | Deployment worker slots control concurrency and queueing; nesting limit **unknown**. `update_async_task` continues/steers; `cancel_async_task` cancels. | Intended for substantial independent work. An undersized server worker pool queues launches. [Synchronous](https://docs.langchain.com/oss/python/deepagents/subagents), [asynchronous](https://docs.langchain.com/oss/python/deepagents/async-subagents) documentation. |

**[Med]** Actual overlap, dispatch serialization, capacity, context reconstruction, checkout provisioning and integration affect elapsed time. Tool names and status panels chiefly affect convenience. Push versus polling affects performance when polling invokes the model or delays collection. A blocking parent can still have concurrent children; “background” alone does not prove parallel execution.

**B. When fan-out pays**

For comparable accepted quality, use:

\[
T_{\rm serial}=\sum t_i+V_0,\qquad
T_{\rm parallel}=D+M_c(G,\tilde t)+I+V_p+R
\]

Here \(D\) is non-overlapped orchestration, \(M_c\) the dependency graph’s makespan with \(c\) usable workers, \(I\) integration, \(V\) verification, and \(R\) rework. Worker durations \(\tilde t\) include their context gathering and tool work.

The makespan cannot beat the longest dependency path, longest worker, or total worker work divided by capacity. Waiting for every worker adds a straggler barrier; release successors when their actual dependencies finish.

For equal independent tasks, the simplified break-even condition is:

\[
(n-\lceil n/c\rceil)t>H
\]

It requires **all incremental costs** in \(H\) and unchanged task durations. For two unequal tasks, maximum overlap saves the **shorter** task’s duration—not the average.

**[Med]** Spawn calls, prompt construction and parent bookkeeping add overhead. Repeated repository discovery, larger reports, semantic reconciliation and verification can grow with task size. Provider rate limits, shared CPU/test resources and tool startup can reduce effective concurrency. Measure cached versus uncached input: a fresh conversation does not necessarily mean every prefix is uncached.

My defensible **pilot thresholds**, not universal constants:

- Below **30 seconds**, ordinarily stay single-agent; batch independent tool calls where possible.
- **30–120 seconds** needs measured low overhead.
- Start experiments with **2–4 independent tasks of 2–5 minutes**, requiring predicted critical-path savings comfortably above overhead—initially, roughly twice it.
- Never fan out a dependency chain, unresolved shared interface decisions, unsafe simultaneous writes, or irreversible actions without exclusive ownership.

**[High]** The closest controlled coding study I found is [Li et al., October 2026](https://arxiv.org/html/2610.10263v1): 354 tasks, 2,124 executions, using July configurations of Codex/GPT-5.4, Claude Code/Opus 5 and Kimi Code/K3. Concurrency increased mean runtime in **14 of 15** agent/benchmark groups. Among 366 paired cases solved both ways, **27.9%** were faster concurrently; **12.6%** were at least 20% faster. Some long-task quality gains occurred. This preprint evaluates native dynamic policies, not a fixed scheduler or the owner’s November builds.

**[High]** Positive vendor evidence needs scope discipline: [Kimi K2.5’s January 2026 report](https://www.kimi.com/en/blog/kimi-k2-5) claims up to 4.5× speedup with up to 100 workers; it does not establish equivalent coding speedups in arbitrary Kimi-backed harnesses. [Anthropic’s June 2025 research system](https://www.anthropic.com/engineering/multi-agent-research-system) reports 90.2% better research evaluation performance, not coding latency; its 15× token comparison is against chat. [Cursor’s January 2026 coding experiments](https://cursor.com/blog/scaling-agents) demonstrate scale and coordination difficulties, without a controlled equal-quality speedup estimate.

**C. Critique and recommendation after reading the appendix**

The following concerns the November 14 fixtures: Claude Code 2.1.325/Sonnet 5.5 high, Codex 0.169.0/Sol 6.1 medium, and Grok Build 1.0.77/Grok 4.6 xhigh.

1. **[High] The settle dial adds sleep, not longer reasoning.** Its implementation is `time.sleep`. **[Med]** It demonstrates overlap of external waits, but cannot establish token scaling, sustained inference contention or long-task context costs. Include a single-agent baseline that overlaps independent tool operations. [dagkit.py — settle implementation](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:469).

2. **[High] The advertised break-even numbers are not reliable task thresholds.** The phase code puts later Codex spawns *inside* “work”; outside-work overhead therefore misses some dispatch cost. The claimed 13.3-second threshold is below the 14.5-second pilot average that nevertheless lost. **[Med]** Fit whole-run differences around the crossover and model actual scheduling, rather than dividing one phase subtotal. [phases.py — overlapping dispatch](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/phases.py:19), [journal — threshold claim](/Users/dadleet/src/skill-craft/docs/shiploop-parallel-execution-journal.md:375).

3. **[High] The census denominator matters.** The 11.6% bound covers **323 timed plans**, only 75 multistep; family reweighting gives about **1.7%**. The 51% overlap figure concerns same-level pairs; all independent pairs give **61%**. The 154-second window includes testing, documentation and review. **[Med]** These are workload-sensitive upper bounds, not expected whole-delivery savings. [Census — definitions and denominators](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/census/README.md:25).

4. **[High] “0.73× parent context” is still a misleading description.** It is cumulative input across model calls. Peak recorded parent input was **45,035 under A3 versus 40,247 under A0**, approximately 12% larger. Fewer cumulative tokens and a smaller resident context are different benefits. [A3 context evidence](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/evidence/r1h-claude-a3/context.json:1), [A0 evidence](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/evidence/r1h-claude-a0/context.json:1).

5. **[High] The write fixture can mask errors.** Its join repairs the package registry, potentially repairing a lost concurrent write. The journal also discloses an orphan consuming CPU throughout E13. **[Med]** Tiny-file merges and one successful retry do not establish semantic compatibility, recovery reliability or stable overhead. Cross-host rankings also confound models and reasoning efforts. [Journal — write-fixture limitations](/Users/dadleet/src/skill-craft/docs/shiploop-parallel-execution-journal.md:433).

I would run these three measurements next:

| Order | Measurement | Decision it resolves |
|---|---|---|
| **1** | Representative real-repository crossover: optimized single parent, sequential fresh workers, parallel fresh workers; randomized order, at least five repetitions per selected task. Blind quality assessment; record total tokens and time through accepted verification. | Whether useful parallel reasoning improves the owner’s quality/tokens/time ordering. |
| **2** | Vary active reasoning length separately from external waits; test widths 1/2/4/8 where supported, warm/cold conditions, and unequal task lengths. Record dispatch, queue delay, cache usage and stragglers. | Actual crossover and useful capacity—not theoretical slots. |
| **3** | Exercise the real step lifecycle with semantic conflicts, lost workers, duplicated completion, parent restart, rate limiting and late writes. Measure recovery time, token waste and final correctness. | Whether unattended execution is dependable enough to offer broadly. |

Before default enablement, I would require durable task/attempt identities, leases preventing duplicate acceptance, persisted handles, and explicit terminal states distinguishing partial output from success. Bind artifacts and verification to their base revision and input hashes. Confirm cancellation—including descendant processes—before reassignment. Preserve unfinished work, reconcile missed notifications, reserve integration time, and bound retries, delegation depth and aggregate expenditure. Independently verify combined behavior; worker summaries are evidence, not acceptance authority.

**[Med — recommendation] Pilot fan-out inside one step’s analysis or review; keep serial execution as the default.** Use narrow independent questions and one integration owner. Defer concurrent build steps until real lifecycle and semantic-conflict evidence exists. Single-step plans may still contain useful internal parallelism, so the census does not rule that out.

Under a strict **quality → tokens → time** ordering, a speedup purchased with more tokens at equal quality is not a win. Enable it automatically only where measured quality and token results justify it; any deliberate token-for-time trade should be an explicit owner policy.
