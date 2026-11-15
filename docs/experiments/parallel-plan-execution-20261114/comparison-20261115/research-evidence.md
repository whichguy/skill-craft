<!-- verbatim final report of a research sub-agent, 2026-11-15, web research done by the agent: Published evidence on multi-agent and parallel coding speedups and failures. A model report: its claims are the agent's, tagged by it; the ones I spot-checked are listed in README.md. -->

1) Anthropic
Research system, 13 Jun 2025, anthropic.com/engineering/multi-agent-research-system [vendor claim]: agents ~4x, multi-agent ~15x chat tokens; +90.2% over single Opus 4 on an internal research eval; token usage alone explains 80% of BrowseComp variance; parallel calls cut research time "up to 90%". Says "most coding tasks involve fewer truly parallelizable tasks" than research; shared-context or many-dependency work fits poorly. Failures: 50 subagents for simple queries, duplicate searches, lead blocked by slowest subagent.
23 Jan 2026, claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them [vendor claim]: 3-10x tokens vs one agent; "primary benefit of parallelization is thoroughness, not speed"; often slower overall; planner/implementer/tester/reviewer split spent more tokens coordinating than working.

2) Cognition
12 Jun 2025, cognition.com/blog/dont-build-multi-agents [opinion]: no measurements; parallel subagents built mismatched Flappy Bird parts; advises one linear agent. 22 Apr 2026, cognition.com/blog/multi-agents-working [vendor claim]: parallel-writer swarms still don't work; one writer plus read-only contributors does (clean-context review ~2 bugs/PR, ~58% severe; manager-child Devins). No speed figures.

3) Google/MIT, arxiv.org/abs/2512.08296, 17 Dec 2025 [independent measurement]: 180 configs, 3 model families, matched token budgets; Finance-Agent (financial reasoning), BrowseComp-Plus (web navigation), PlanCraft (planning), Workbench (tool use); no SWE benchmark. Centralized ~+81% on Finance-Agent; every multi-agent variant -39% to -70% on sequential PlanCraft. Error amplification 17.2x independent vs 4.4x centralized (not significant after controls). Returns diminish above ~45% single-agent baseline. Authors' own out-of-sample check only.

4) Cursor [vendor claim]
cursor.com/blog/scaling-agents, 14 Jan 2026: lock file: "Twenty agents would slow down to the effective throughput of two or three"; flat peers avoided hard work; planner/worker/judge fixed most; browser ~1M lines, no quality metrics. cursor.com/blog/self-driving-codebases, 5 Feb 2026: integrator role bottlenecked; demanding 100% correct commits serialized work.
cursor.com/blog/agent-swarm-model-economics, 20 Jul 2026: SQLite in Rust: old swarm >70,000 merge conflicts (hottest file 7,771; 1,173 agents) vs new <1,000; 4-hour scores 73-85% vs 11-77%; cost $1,339-$10,565; agent count, wall-clock unstated; one benchmark.

5) Kimi K2.5, kimi.com/blog/kimi-k2-5 (undated, ~Jan 2026), arxiv.org/abs/2602.02276 [vendor claim]: critical steps = per stage, main-agent steps plus slowest subagent's steps; PARL rewards counter "serial collapse" and "spurious parallelism". BrowseComp 60.6→78.4%; WideSearch F1 72.7→79.0; up to 4.5x less time to a target F1. Search tasks; no coding-swarm evaluation.

6) 2026 wall-clock evidence
Geng & Neubig (CMU), arxiv.org/abs/2603.21489, 23 Mar 2026 [independent measurement]: own CAID method, manager plus 2-4 worktree engineers, beat one agent on Commit0-Lite/PaperBench (library build, paper reproduction; Sonnet 4.5 53.1→59.1) yet "wall-clock runtime is not substantially reduced": Commit0-Lite 692.6→1583.2 s, cost 4.3x; 8 engineers worse than 4.
STORM, arxiv.org/abs/2605.20563, 19 May 2026 [independent measurement]: plain 4-agent worktrees cut Commit0-Lite macro score for all three models (Qwen 75.3→57.4, DeepSeek 65.2→44.0, Sonnet 66.4→63.8); PaperBench time per score point doubled (Sonnet). Authors propose a rival method.
Co-Coder, arxiv.org/abs/2606.00953, 31 May 2026 [independent measurement]: 28 Python repo-generation tasks, gpt-5-mini; Claude Code Agent Teams 1.49x and 4.05x faster than sequential but lower pass rate (54.1 vs 56.8; 16.3 vs 20.1); file-per-agent 0.99x on DevEval, +44% cost. Authors propose a rival method.
Mieczkowski et al., arxiv.org/abs/2603.12229, 12 Mar 2026 [independent measurement]: 20 function-writing subtasks, preset dependencies; Sonnet 4.6, 5 agents: 3.35x, 1.30x, 0.79x at 90/50/20% parallel fraction (Amdahl bounds 3.57x/1.67x/1.19x, my arithmetic); self-coordinating teams median 0.88x vs 1.36x preassigned.
LogRocket, 13 Mar 2026, blog.logrocket.com/splitting-across-ai-agents [independent measurement]: n=1; solo 29m50s vs Agent Teams 16m05s; tests 61 vs 18.
Carlini, 5 Feb 2026, anthropic.com/engineering/building-c-compiler [vendor claim]: 16 agents, ~$20,000; all hit one kernel bug and overwrote each other until a GCC oracle split the work; no single-agent baseline.
METR, 24 Feb 2026, metr.org/blog/2026-02-24-uplift-update/ [independent measurement]: time data "unreliable" for concurrent-agent developers. Electric, 19 Feb 2026, electric.ax/blog/2026/02/19/amdahls-law-for-ai-agents [opinion]: speedup at most 1/H (human-judgment share); illustrative arithmetic. No independent Codex measurement found.

7) Conflicts, duplication, drift
CooperBench, arxiv.org/abs/2601.13295, 26 Jan 2026 [independent measurement]: 652 tasks, 12 repos; two agents on separate features ~30% below solo; 2/3/4 agents 68.6/46.5/30.0% (46 tasks); work overlap 33.2%, divergent architecture 29.7%, repetition 14.7% of failures; messaging cut textual conflicts, net merge success -0.5 points.
AgenticFlict, arxiv.org/abs/2604.03551, 12 May 2026: 107,026 agent PRs, 27.67% textual conflicts (Codex 31.85%, Claude Code 25.93%). Xu et al., arxiv.org/abs/2607.04697, 6 Jul 2026: cross-agent PR pairs 41.7% vs same-agent 19.8% [both independent measurement; textual only].
"Passes Alone, Fails Together," arxiv.org/abs/2609.25396, 21 Sep 2026 [independent measurement]: constructed tasks 97% interference; mined Django pairs 1 of 834; a message recovered 82%; not real-world rates.
Drift: only qualitative (Cursor fresh starts, Anthropic "telephone game"); no rate found.

Supports: wall-clock gains need pre-split, independent subtasks (3.35x of a 3.57x bound at 90% parallel; vendor 4.5x/90% only on search/research), at 3-10x tokens.
Supports: sequential, coupled or same-file work loses (-39% to -70%; 0.79x; runtime 2.3x; two agents ~30% below solo); duplicated and divergent work top CooperBench failures.
Does not support: quality-neutral speedups from parallel code writers, replication of Cursor/Kimi results, or Codex and drift numbers (not found).
