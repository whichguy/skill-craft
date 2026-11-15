<!-- verbatim answer, 2026-11-15; command: ask.sh opus ask --json --allow-tools --cwd <repo> "$(cat brief.txt)"; model_used=opus served_model=claude-opus-5-5 effort=xhigh profile=consult fallback=False exit=0 sandbox=None -->

# When native workers save wall-clock time: harness comparison and decision rules

**Sources and dates.** I couldn't run a web search, but I could fetch pages by URL. On 2026-11-15 I fetched the vendor pages listed below. Everything else comes from my training, which runs to mid-2026, and is tagged that way. After Parts A and B, I read your journal, your evidence, `host-capabilities.md` and Astra's review. I edited nothing.

Confidence tags: **H** = I'm sure and can cite it, **M** = I believe so, **L** = I may be wrong.

---

## Part A — How native workers work in each harness

### The three hosts you measured

| | Claude Code (docs as of 2026-11-15; you ran 2.1.325) | Codex CLI, app and IDE (docs 2026-11-15; you ran 0.169.0) | Grok Build (docs 2026-11-15; you ran 1.0.77) |
|---|---|---|---|
| **Spawn** | `Agent` tool (renamed from `Task` in 2.1.63; `Task` still works as an alias), with `subagent_type`, plus optional `model`, `effort`, `isolation`, `name` (**H**) | `spawn_agent` (`fork_turns`), `wait_agent`, plus send and close tools. Names come from your records and my memory; the docs page names no tools (**M**) | `spawn_subagent` (`background`, `cwd`), per your records. The docs don't name the tool (**M**) |
| **Blocking and waiting** | Background is the default. The result arrives as a completion notification in a later turn, so the parent is pushed, not polling (**H**) | Asynchronous spawn. The parent waits with `wait_agent` and a timeout, and every wait is a model call (**M**; you measured it) | Background. The parent collects with `get_command_or_subagent_output` or `wait_commands_or_subagents` (**M**, your E10) |
| **Context and what returns** | Fresh context: system prompt, the task message, CLAUDE.md, git status. A "fork" variant inherits the parent's history. Only the final report returns (**H**) | `fork_turns:"none"` gives a fresh context. Docs: "Return summaries" (**M**) | "Own context", returns a summary (**H**) |
| **Concurrency** | 20 running at once by default, set by `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. The next spawn **fails** with "Concurrent subagent limit reached"; it doesn't queue (**H**) | `agents.max_concurrent_threads_per_session` (old name `agents.max_threads`); the default is unstated (**H**). You saw 4 slots including the parent | unknown |
| **Nesting** | 3 layers by default; `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` turns nesting off (**H**) | unknown (your E10 child listed a spawn tool) | unknown (your E10 child had no spawn tool) |
| **Isolation and merging** | Shared checkout by default. `isolation: worktree` creates a temporary worktree branched from the **default branch**, not the parent's HEAD (**H**). Who merges: the parent or the user (**M**) | Inherits the parent's sandbox policy; worktrees aren't mentioned for subagents (**H**) | unknown |
| **Continue or cancel** | `SendMessage` to the agent's ID to continue it; `TaskStop` to cancel (**H**) | Ask the parent to steer, stop or close a thread; `/subagents` to switch threads (**H**) | `kill_command_or_subagent`, per your file (**M**) |
| **Vendor guidance** | A fresh worker "may need time to gather context"; use the main conversation when latency matters; workers count toward the same usage limits (**H**) | Uses "more tokens than comparable single-agent runs"; be "more careful with parallel write-heavy workflows" (**H**) | none published |

**Codex cloud** (**M**, as of mid-2025): each task runs in its own container built from the repository, and many tasks can run in parallel. Each produces a diff or PR, a task can request several attempts at once (best-of-N), and a human merges. It doesn't return results to a parent agent. The subagent docs don't mention cloud (**H**).

### Other harnesses (condensed)

| Harness | Spawn, waiting, context | Limits, isolation, merging | Source |
|---|---|---|---|
| Cursor | `Task` tool; several Task calls in one message run in parallel. Foreground, or background via `is_background`. Fresh context, final message returns, an agent ID allows resume | One level of nesting since 2.5. Shared checkout by default; optional local worktree or cloud VM with its own branch, "until the parent agent merges them". Docs advise "2-3 focused subagents", say 5 in parallel uses about 5× the tokens and "simple tasks" can be slower. No cancel documented | docs (**H**) |
| OpenCode | Current docs: a `subagent` tool, "always run in the background", fresh child session. Your tested 1.18.31 used `task(background=true)` and `task_id`, so the docs and your build differ | `general` "cannot launch more subagents"; concurrency and cancel unknown | docs (**M**) |
| Gemini CLI | Each subagent is exposed as a tool of the same name, or forced with `@name`; separate context loop; findings return | No nesting; `max_turns` 30 and `timeout_mins` 10 by default. Banner: replaced by Antigravity CLI for unpaid-tier and Google One users on 2026-06-18 | docs (**H**) |
| Amp | Task subagent with its own context, final summary returns; it accepts follow-up instructions mid-task | Workers "can't communicate with each other"; nesting and isolation unknown | docs (**M**) |
| Roo Code | Orchestrator `new_task`; the parent pauses until the child's `attempt_completion` summary arrives, so it is sequential | — | memory, 2025 (**M**) |
| Cline | `new_task` is a context hand-off, not parallel work | — | memory (**L**) |
| Kimi K2.5 Agent Swarm | The model orchestrates up to 100 sub-agents and 1,500 tool calls, trained with PARL; claims "up to 4.5x" faster on wide search, measured in "Critical Steps" | API shape unknown | blog, Jan 2026 (**H** that it claims this) |
| DeepSeek- and Qwen-based CLIs | unknown | unknown | — |
| LangChain Deep Agents | `task` tool, isolated by default or fork mode; final result returns as a tool result (structured if `response_format` is set). Several `task` calls in one turn run in parallel; async subagents exist for steering and cancelling | Isolated workers can nest; forked workers can't | docs (**H**) |
| OpenHands | Agent delegation plus a Docker sandbox per conversation | parallelism details unknown | memory (**L**) |
| GitHub Copilot coding agent | Cloud sandbox, Actions or a custom environment | "one branch at a time and … one pull request per task"; Actions sessions have a 59-minute limit; a human reviews | docs (**H**) |

### Which differences change wall-clock time

These change wall-clock time:
1. **Where the per-worker spawn cost sits**:
   - Claude: one model call issues all the spawns.
   - Codex: one model call per spawn.
   - Grok: one call, but the host starts the children one after another.

   This is the cost that grows with the number of workers.
2. **Push versus poll.** A poll adds up to one wait slice per round, and on Codex every poll is a model call.
3. **The capacity cap** decides how many rounds there are. Claude **fails** at its cap rather than queueing, so the scheduler has to own capacity.
4. **Cloud or VM isolation** adds minutes of startup and a human merge.
5. **Fork versus fresh context.** A fork skips the cold start but carries the parent's tokens.
6. **Per-worktree environment setup** (installing dependencies, building) on real repositories.

These change only convenience: tool names, wording, which subagent type gets picked, resume handles, transcript locations, the UI.

---

## Part B — My model of when fan-out pays

For one round with enough slots:

**saving ≈ Σtᵢ − max tᵢ − (S_spawn + C_cold + W_notice + M_merge + V_reverify + tail)**

With two tasks this becomes **min(t₁, t₂) − overhead**. **The shorter task pays for the fan-out.** Pairs of very different lengths usually lose.

### The costs, and what each one scales with

| Cost | Grows with | Note |
|---|---|---|
| Spawn | number of workers | Writing each worker's brief is output tokens: tens of seconds for a long brief |
| Cold context | repository and convention size, **not** task length | Small in a toy repository; large in a real one |
| Notice and wait | rounds × poll slice | |
| Merge | conflicts | Textual conflicts are cheap. Semantic conflicts are found late and can cost more than the saving |
| Re-verify | test-suite time | The **integrated** tree must pass again: one more suite run on the critical path |
| Straggler | spread and number of workers | The expected maximum sits about σ·√(2 ln k) above the mean; heavy tails hurt |
| Rate limits and usage windows | concurrency | Parallel streams run at full speed until RPM/TPM limits or a subscription window bind; back-off then creates stragglers (**M**) |
| Prompt cache | fresh contexts | Each fresh worker writes its own cache prefix and doesn't reuse the parent's warm one, which costs time to first token and dollars (**M**). Plausibly why Claude's dollar ratio is higher than its token ratio |
| Machine contention | parallel tool use | Concurrent test suites compete for CPU, ports, databases and locks; a sleep doesn't model this |
| Coupling | shared files and decisions | A shared file costs about one round each time. A shared, undecided decision (interface, naming, schema) needs the parent to decide it before fanning out, or else run the tasks serially |

### Thresholds I'd defend on these hosts (November 2026)

- **Read-only fan-out inside a step:** at least 2 independent questions, each about 30 s or more, with small, checkable outputs.
- **Write fan-out across steps:** the *shorter* task should take at least about 3× the real total overhead, which on a real repository means roughly 4–5 minutes. Other conditions:
  - disjoint declared **and** actually-changed paths;
  - no shared resource classes (lockfiles, migrations, generated files, ports);
  - script-run tests per task, plus a test run on the integrated tree.
- **Width:** 3–4 is where it pays well. 2 is marginal.

### Never fan out

- single-step plans and chains;
- tasks under about 20–30 s;
- debugging or exploration whose findings redirect the other tasks;
- tasks that share an undecided design choice;
- work whose only check is a model's judgement;
- runs near a rate or usage limit;
- runs where tokens matter more than time (your own ordering).

### Published evidence

**For speedups:**
- Anthropic's multi-agent research system: beat single-agent Opus by 90.2%, cut time by "up to 90%", used about 15× the tokens of chat. This is research work, and they say "most coding tasks involve fewer truly parallelizable tasks" (**H**; [link](https://www.anthropic.com/engineering/multi-agent-research-system)).
- Kimi Agent Swarm: up to 4.5×, on wide search, measured in critical steps rather than wall-clock with tool latency (**H** that it is claimed).
- LLMCompiler (2023): up to 3.7× lower latency from parallel function calls (**H**).
- Anthropic's parallel-Claude C compiler (Feb 2026): 16 agents worked well with a per-test oracle, but the effort collapsed when every agent hit the same kernel bug, until the work was re-split using GCC as an oracle (**M**).

**Against:**
- Cognition, "Don't Build Multi-Agents" (2025-06-12): actions carry implicit decisions, and parallel coders conflict (**H**; [link](https://cognition.com/blog/dont-build-multi-agents)).
- Kim et al., "Towards a Science of Scaling Agent Systems" (arXiv 2512.08296): from +80.8% on decomposable tasks to −70.0% on sequential planning; tool-heavy tasks pay overhead; errors spread more without central verification (**H**).
- The vendors' own cautions quoted in Part A.

**Gap in all of it:** none of this measures real multi-step coding plans against a serial run of equal quality.

---

## Part C — Critique of your measurements

### Weak points

1. **Your fixed cost is a toy cold start.** Your own F13 pilot on a real ShipLoop case found a fresh worker costs about 1.25 minutes and about 1.2M input tokens. In real runs that cost sits on the critical path once per round.
   - In your census only 28 plans have width 3 or more, so width 2 dominates.
   - For width 2, break-even ≈ host overhead + cold start ≈ 100 s or more, against a median step of 154 s. The gain is marginal exactly where most of the opportunity is.
2. **The settle dial is a sleep.** It uses no CPU, no tokens, no rate limit and no shared resources, and every task lasts the same time. So stragglers (97–99 s spread) and contention are invisible.
   - Your own memory notes port collisions and git `maintenance.lock` races.
   - Parallel test suites on one laptop can run slower than serial ones.
3. **The break-even formula assumes equal tasks.** Use Σ − max per round and subtract overhead in the census. Right now the census reports only the ideal bound.
   - My rough estimate: the 21 plans that save anything save about 490 s each (gated).
   - Subtracting about 100 s of overhead per round plus one re-verification leaves roughly **5–7% overall**. That is an estimate, not a measurement.
4. **Quality, your first priority, was only measured on toy oracles.** Fresh workers lose what the parent knew, which is Cognition's point. The toy tasks had no shared decisions to get wrong.
5. **Your priority order decides the default.** Fan-out cost 1.4–3.5× the dollars on Claude and about 1.6× the tokens on Codex. Under quality, then tokens, then time, that rules it out by default.
   - The fit saying long tasks get cheaper under fan-out (F29) is exploratory.
   - Your one real measurement (F13) found 2.9× the tokens.
   - Grok at about 1× is the only exception.
6. **The step lifecycle isn't modelled.** Concurrent steps need a merge, then tests and review on the *combined* tree, before commit.
7. **Correctness depended on capacity (F42).** The same plan conflicted on two hosts and didn't on the third. You need a conflict check that doesn't depend on scheduling: declared paths against the actual diff, before every merge.
8. **Independence is declared, not validated.** Your commit ledger already records which files each step really changed, so you can check this for free.
9. **Also unmeasured:** rate limits, the prompt cache, and Claude's enforceable depth limit (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`). At present a worker is stopped from spawning only by wording.

### The three measurements I'd run next, in order

1. **Re-score the census against a realistic overhead model. It costs nothing.**
   - Per plan: Σ − max per round, minus (host overhead + F13 cold start + one re-verification).
   - Add a sensitivity sweep.
   - Check actual changed files against declared paths, using the commit ledger.
   - If the net result is under about 5%, stop building step-level fan-out. This is the cheapest measurement that can change the decision.
2. **Replay 3–5 of the 21 plans that have a disjoint independent pair, in their real repositories.**
   - Compare one context against fan-out with a worktree per worker, n = 3 each.
   - Use real test suites, not sleeps, on one host (Claude or Grok).
   - Measure the whole run; quality (tests on the integrated tree, review findings, send-backs); tokens and dollars; and contention.
   - This covers semantic conflicts, the real cold start, contention and quality in one go.
3. **Read-only fan-out inside one real stage.** Your design E8 (planning against a hidden oracle) or a review stage, n = 3, measuring missed or invented findings, time and tokens. This is the most likely place for fan-out to land.

### Failure modes to design for before turning fan-out on by default

| Failure | What to build |
|---|---|
| Lost worker | A script lease with a heartbeat and expiry. On expiry, mark the task unknown, confirm the worker is stopped (`TaskStop` or `kill`), and retry from a clean base. Never run two writers on one task |
| Partial result | Only a script callback with evidence counts as done. A `partial` callback re-queues or escalates; a model's report alone is never accepted |
| Duplicated work | Claim before start (you have this). One worktree per attempt. Idempotent tasks |
| Context drift or stale base | Record each worker's base revision. If main moved under its declared area, re-test after rebase |
| Semantic conflict | The parent freezes shared interfaces in the briefs before fanning out. Test and review the integrated tree |
| Error amplification | Script-run tests per worker before merge, then a check on the integrated tree |
| Runaway cost or nesting | Set the depth limit to 1 on Claude; Codex has no known setting, so wording only. Spend should be **reported**. A cost cap counts as a ShipLoop loop limit, and your rule says you decide those, so I'm not proposing one |
| Hitting the capacity cap | The script owns capacity (Claude fails rather than queueing) |
| 429 rate-limit back-off | Treat it as retriable at the host level, and expect it to create stragglers |

### Where fan-out belongs, and its default

- **Inside one step, read-only** (investigation, review, gathering evidence for planning): offer it. Keep it **off by default until measurement 3** shows equal or better quality. After that, turn it on for the specific stages where it was measured to help. Workers are read-only and told not to spawn.
- **Across independent steps:** offer it only as an **opt-in per run**, behind a script predicate:
  - width of at least 2;
  - disjoint declared and historically-changed paths;
  - no shared resource classes;
  - predicted shorter task at least 3× the measured overhead;
  - a qualified host;
  - a re-verification on the integrated tree.

  Default **off**. If measurement 1 nets under about 5%, drop it altogether.
- **Never:** chains, single steps, and writes without isolation.
