Legend: [IM] academic measurement; † authors test their own method; [VC] vendor claim. arXiv IDs confirmed at arxiv.org/abs/<id> (YYMM = first-submission month); Li et al. = 2610.10263. Figures were read via a summarising fetch tool; CAID, Li et al. and Mieczkowski were cross-checked twice.

**Decomposition**
- CAID 2603.21489 (v2 2026-07) [IM†]: LLM manager builds a dependency graph, delegates a unit only once its dependencies are merged, gives coupled files to one engineer, one git worktree each. Heuristic delegation: minitorch scored 8.7% or 34.3% depending on whether one critical file was assigned.
- Co-Coder 2606.00953 [IM†]: LLM interface blueprint → import graph → hubs isolated → community detection → one owner per file group; greedy ready-list scheduler. Gain tracks edge density (r=0.65, 16 projects); full coupling collapses to sequential.
- CodePlan 2309.12499 [IM†]: impact analysis grows an adaptive plan graph but executes one node at a time; 5/6 repos valid vs 0/6 baselines. LLMCompiler 2312.04511 [IM†]: LLM-planned DAG, ready calls run concurrently; up to 3.7x latency, 6.7x cost vs ReAct on QA/tool tasks; no coding test.
- Predicting parallelism: no validated predictor found. Kim et al. 2512.08296 [IM]: sequential tasks lose (PlanCraft −39% to −70%), decomposable gain (Finance +80.8%), SWE-bench Verified −2% to −15%; negative above ~45% single-agent accuracy. Specification Gap 2603.24284 [IM]: two-agent integration 58→25% as specs thin (single agent 89→56%). Test-first study: not found.

**Scheduling**
- Li et al. 2610.10263 (2026-10) [IM]: of 804 failure instances, load imbalance 166, wrong start/join timing 166.
- Mieczkowski 2603.12229 [IM]: pre-assigned beat self-claiming teams (median 1.36x vs 0.88x; 4 vs 19 median test failures); even 90%-parallel work stayed below Amdahl's bound.

**Fan-in and merging**
- CAID: manager merges each branch when its engineer finishes; the engineer of a conflicting commit pulls main, resolves, resubmits; pre-commit tests cover touched files; post-merge re-test unstated. Failures: shared workspace 55.5 vs single agent 57.2 (worktrees 63.3, PaperBench); 8 engineers worse than 4; authors say merge conflicts remain a primary failure mode.
- Li et al.: shared-state/merge failures 267 of 804 (concurrent writes 213). STORM 2605.20563 [IM†]: per-file versions; a write is rejected if any file the agent read changed; manager sole committer. Its git-worktree baseline (CAID not named) fell below single agent on Commit0-Lite macro score for 3/3 models (e.g. 57.4 vs 75.3), unlike CAID's reported gains; STORM +18.7 pp over it.
- AgentRoom 2608.23740 [IM†]: advisory file claims + CRDT (converges bytes, not semantics); stub-and-exit abandonment 31→5%. Claim Plane 2608.00947 [IM†]: 360 CooperBench runs; pre-write admission lifted pair pass 23.3→50.0%, integration 65.6→96.7%, but serialised 96.7%; dynamic mode failed closed on undeclared scope in 46/90.
- Anthropic C compiler 2026-02-05 [VC]: 16 agents, ~$20k, frequent conflicts self-resolved; a monolithic kernel task made agents collide until split with a GCC oracle.
- Classical [VC]: Zuul tests each change on the speculative merge of those ahead; failure drops it and restarts those behind; window 20, +1 per merge, halved per failure. GitLab trains and GitHub queue are alike. Uber SubmitQueue (EuroSys 2019, via Colyer's summary): mainline green 52% of one week; 40% problem chance at 16 concurrent conflicting changes; build-target analyzer lands disjoint changes in parallel. Stacked PRs: no controlled study found. Implication: land in plan-topological order, verify on the merged state, rerun dependents on failure, size the window by failure rate.

**Conflicts and verification**
- CooperBench 2601.13295 [IM]: 652 two-feature tasks; cooperation ~30% below solo; merge success 8.6% naive → 17.6% after LLM resolver; messaging no help (17.6 vs 17.1%); 2→4 agents 68.6→30.0% (46 tasks).
- Textual base rates: AgenticFlict 2604.03551 [IM]: 27.67% of 107,026 agent PRs conflict; Xu et al. 2607.04697: 41.7% cross-agent vs 19.8% same-agent pairs.
- Semantic: Passes Alone 2609.25396 [IM]: constructed Django breaks 97% despite clean merges; mined PR pairs 1/834 (not prevalence); completion message recovered 82%. ParallACT 2611.00314 [IM]: contradictory tasks single-agent 62%, parallel 16%, post-hoc reconciliation ≤16%, sequential hand-off 54% at 1.18x cost, gold tests 38%.
- LLM resolution: ConGra 2409.14121 (2024); Merge-Bench 2605.25890: best <60% correct; Shen 2607.27674: ~55% vs 36.7% best classical tool; its LLM judge accepted 4/5 structurally failing fixes. Generated-test detection 2507.06762: hard on complex systems.

**Measured speedups**
- No gain: Li et al. slower in 14/15 cells, faster on 27.9% of 366 co-solved tasks, tokens 1.41–3.31x; SWE-bench Verified Claude 59 vs 83, Kimi 59 vs 77, Codex 71 vs 71 (one run per cell). CAID slower in 6/6 rows (+15–154%), cost 1.7–4.3x; abstract's +25.6/+14.7 pp are MiniMax rows (Claude ≈ +6). AgentRoom 561 vs 550 s solo, 2x compute.
- Gain: Co-Coder (gpt-5-mini, 28 greenfield Python tasks) 1.81x/2.10x, pass +11.3/+14.0 pp, cost −28/−35%. DeLM 2606.10662 [IM†]: up to 2.49x on 10 Terminal-Bench tasks ($30 vs $20/task), coupled edits untested. Mieczkowski: Claude 3.35x at 5 agents, 90%-parallel.

Non-arXiv URLs (docs read 2026-11-15): anthropic.com/engineering/building-c-compiler; zuul-ci.org/docs/zuul/latest/gating.html; docs.gitlab.com/ci/pipelines/merge_trains; docs.github.com (managing a merge queue); blog.acolyer.org/2019/04/18/keeping-master-green-at-scale.

**Summary**
- Supported: parallelism pays only for large, weakly coupled, file-disjoint work with an executable oracle; best cases 1.8–3.4x (unreplicated) at 1.4–4x cost; every merge needs verification on the merged tree.
- Not supported: parallel plan steps being generally faster (CAID, Li, STORM, AgentRoom: slower or flat); CAID's accuracy gains replicating; reliable LLM merges or declared scopes; messaging during parallel work fixing semantic conflicts.
- Unknown: a plan-DAG harness with merge gate on real SDLC work; a validated parallelisability predictor; test-first or stacked-PR evidence; real semantic-conflict prevalence (1/834 mined vs 97% constructed).
