# Round 4 web research: published evidence

Written by a Claude Opus 5.5 research agent on 2026-11-20 from the brief at the end of this file. Model output: every
claim is the agent's reading of the page it names, not checked again by the session that commissioned it.

## 1. Sources (I opened every one. M = I read the number in the source. Abstract = only the abstract was readable.)

| # | Source (year) | URL | Key numbers | Models | Relevance |
|---|---|---|---|---|---|
| 1 | Olausson et al., Is Self-Repair a Silver Bullet? (ICLR 2024) | arxiv.org/html/2306.09896v5 | M: at equal budget, GPT-4/APPS repair is at most ~8% above resampling. 10 initial samples with 1 repair each beat 2 with 10 each (1.05x vs 0.97x). With GPT-4 feedback, Code Llama repair success rose from 9.1% to 39.3%. Human feedback took GPT-4 repair from 33.3% to 52.6%. | GPT-3.5, GPT-4, Code Llama | B, E |
| 2 | Debugging Decay Index (2025) | arxiv.org/html/2506.18403v2 | M: most models lose 60-80% of their debugging ability within 2-3 attempts. Clearing history and restarting fresh within a 6-attempt budget: llama3.1-8b +9.8 pts, deepseek-coder-v2-16b +7.9, strong models about ±1. | 18 models, mostly 7-24B; HumanEval | B, restart |
| 3 | How Many Tries Does It Take? (2026) | arxiv.org/html/2604.10508v1 | M: rounds 1-2 give 76-95% of the total gain. Repair success is ~77% for name errors and ~45% for assertion (logic) errors on HumanEval. Repair matched or beat resampling with 11-54% fewer tokens, except at 8B. | Llama 8B/70B, Llama 4, Qwen3-32B, Gemini 2.5 | B |
| 4 | Is Three the Magic Number? (2026) | huggingface.co/papers/2607.05197.md | M (qualitative only; tables not readable): repair iterations 1-3 or 1-4 give most of the gain, and gains are near zero after steps 5-7. How feedback is designed matters more than which model runs. | gpt-4o-mini, Qwen3.5-27B, Gemma-4-31B | B |
| 5 | Mathews & Nagappan, TDD for Code Generation (2024) | arxiv.org/html/2402.13521v2 | M: putting tests in the prompt raised GPT-4 from 69.7% to 82.5% on MBPP and 78.7% to 87.8% on HumanEval. Llama3-70B rose from 46.4% to 75.9% on MBPP. No problem was fixed on attempt 5. | GPT-4, Llama 3 70B | A |
| 6 | Tests as Prompt / WebApp1K (2025) | arxiv.org/html/2505.09027v1 | M: with tests as the prompt, pass@1 was gpt-4o 0.885 and qwen2.5-coder-32b 0.70. With two features and four tests, gpt-4o fell to 0.531 and o1-preview to 0.652. The cause is lost instructions in long prompts. | 20+ models | A (counter-evidence) |
| 7 | TDFlow (EACL 2026) | arxiv.org/html/2510.23761v2 | M: 94.3% on SWE-bench Verified with human-written tests, 68.0% with its own generated tests (4x the cost). Removing the debug sub-agent: 94.3% to 87.2%. Test hacking in 7 of 800 runs. | GPT-4.1, GPT-5, Claude 4 Sonnet | A, C (repository scale) |
| 8 | AgentCoder (2023/24) | arxiv.org/html/2312.13010v3 | M: programmer alone 61.0, with a test designer 64.0, full system 79.9 (HumanEval). Tests written in a separate agent vs the same conversation: test accuracy 87.8/89.9 vs 61.0/51.8. Iterations 1 to 5: +4 to +9 pts. | GPT-3.5, GPT-4 | A, C |
| 9 | MapCoder (ACL 2024) | arxiv.org/html/2405.11403v1 | M (text only): removing the debugging agent costs 17.5%; the average drop is 24.8% for debugging and 16.7% for planning. | ChatGPT | C |
| 10 | AlphaCodium (2024) | ar5iv.labs.arxiv.org/html/2401.08500 | M: GPT-4 CodeContests test pass@5 went from 12% to 29%, GPT-3.5 from 8% to 17%. No numbers for each stage separately. | GPT-3.5/4, DeepSeek-33B | C |
| 11 | LDB debugger (ACL Findings 2024) | arxiv.org/html/2402.16906v6 | M: block-level runtime traces beat Self-Debugging (GPT-3.5 HumanEval: 82.9 vs 81.1) and beat line-level or function-level traces at lower token cost. Self-Debugging stalls after ~2 iterations. | GPT-3.5, CodeLlama-34B, StarCoder | B, E |
| 12 | Property-Generated Solver (2025) | arxiv.org/html/2506.18315v1 | M: property feedback beat Self-Debugging (e.g. MBPP 69.6 vs 64.4). On the hard-to-fix subset, public tests alone corrected 46.6%; adding property feedback reached 75.9%. The shortest counterexample was the best feedback. | DeepSeek-Coder-V2, Qwen2.5-Coder, R1-32B | E |
| 13 | FeedbackEval (2025) | arxiv.org/html/2504.06939v2 | M: Repair@1 by feedback type: mixed 63.6, LLM-expert 62.9, test output 57.9, minimal 53.1, static analysis/compiler 49.2, weaker-LLM explanation 48.8. Plateau by round 3. | GPT-4o, Claude-3.5, R1, Qwen2.5, GLM-4 | E |
| 14 | Self-planning (TOSEM 2024) | arxiv.org/html/2303.06689v5 | M: HumanEval direct 48.1, self-plan 60.3, ground-truth plan 74.4. "Extremely concise plan" 61.5. A 13B model with its own plan scored 30.1 (below direct 34.0) and 44.9 with a stronger model's plan. Gains grow with problem complexity (+9% to +62% relative). | Codex-era OpenAI models | D |
| 15 | Plan-then-code fails on HumanEval+ (2026) | arxiv.org/html/2603.03406 | M: coder alone 78.0, with a reasoner's plan 75.6 (the plan broke 15 problems and fixed 14), reviewer after generation 87.8, plus a retry 90.2. | Qwen3-32B with Qwen2.5-Coder-14B | D |
| 16 | SWE-agent plan ablation (2026) | arxiv.org/html/2604.12147v1 | M: removing the plan newly solved 23-34 tasks per model. A cut-down plan "hurts more than no plan". Re-injecting the plan every 5 steps raised compliance and success. | GPT-5 mini, DeepSeek-V3/R1, Devstral | C, D |
| 17 | Rethinking agent-generated tests (2026) | arxiv.org/html/2602.07900v1 | M: discouraging tests cut API calls by 35% (Kimi) and 25% (DeepSeek) for −2.6 and −1.8 pts resolve rate. Encouraging tests in gpt-5.2: no change, +5.5% calls. 83% of outcomes unchanged. | 6 frontier and mid models | F |
| 18 | Large-scale SWE-bench trajectories (2026) | arxiv.org/html/2604.02547v1 | M: strong agents spend 35-37% of steps validating, weak ones 12-19% (correlation with resolve rate 0.50). Delaying the first edit correlates with success (0.68). 12.4% of compute goes to never-solved tasks. | 19 agents | F |

Also opened, cited only lightly:
- Overthinking (arxiv.org/abs/2502.08235, abstract): choosing the run with less overthinking was about 30% better and 43% cheaper.
- TiCoder (arxiv.org/abs/2404.10100, abstract): clarifying intent through tests gave +46 pts pass@1 within 5 interactions, but with a simulated user, so it is an upper bound.
- COPE (arxiv.org/html/2506.11578v3): does not isolate the effect of plans on code.
- SWT-bench (arxiv.org/abs/2406.12952, abstract): using generated tests as a filter "doubled SWE-Agent precision".

**Transfer warning:** sources 1-6 and 8-15 use single-function benchmarks (HumanEval, MBPP, APPS). Only 7 and 16-18 are repository-scale. The "GPT-4" of 2023 is roughly today's mid-tier.

## 2. What the evidence says

**A. Tests first vs tests after.** Executable tests that the coder can see before it writes code reliably raise first-attempt correctness: +9 to +13 pts for GPT-4 and +13 to +30 for Llama-70B (source 5). The ceiling is set by test quality: 94% with human-written tests vs 68% with self-generated ones (source 7). Tests written in a separate context from the code are far more accurate than tests written in the same conversation (source 8). Counter-evidence: more or longer tests degraded every model (source 6), and TDFlow cannot recover from a wrong test. I found no measurement of prose test cases written before code, which is what this harness's test-spec stage produces.

**B. Repair rounds.** Returns are front-loaded: rounds 1-2 give 76-95% of the gain (3), the decay index shows 60-80% loss of debugging ability by attempts 2-3 (2), and TGen fixed nothing on attempt 5. Logic and assertion failures, the harness's "moderately correct" case, repair at only ~45%. Restarting fresh after about 2 failed rounds helped 7-24B models by 4-10 pts and did nothing for strong models (2). Counter-evidence: self-repair beats resampling on tokens for models of 70B and up (3), and trace-guided debugging keeps improving up to 10-20 iterations (11).

**C. Multi-stage flows.** The ablations consistently find that executing tests and debugging on the result is the load-bearing stage: debugging is the largest in MapCoder, the test designer plus executor is the largest in AgentCoder, and the debug sub-agent is worth 7 pts in TDFlow. Planning comes second (MapCoder 16.7%). AlphaCodium publishes no per-stage numbers. Counter-evidence: in SWE-agent, prescribed phases that do not match a model's own strategy cost performance, and dropping the plan solved new tasks (16).

**D. Planning granularity.** Plans help, more on complex problems, and a correct plan is worth far more than a self-generated one (74.4 vs 60.3). A concise plan did as well as or better than a detailed one. Weaker models plan badly for themselves (13B: 30.1 vs direct 34.0) but benefit from a stronger model's plan (44.9). Counter-evidence: a reasoner's plan given to a code specialist lowered its score by 2.4 pts, while the same strong model used as a post-hoc reviewer added 9.8-12.2 pts (15).

**E. Feedback type.** Raw test output beats static or compiler output and beats explanations written by a weaker LLM (13). Explanations from a strong expert model or a human beat raw output (1, 13). Minimal counterexamples from property checks lifted hard logic fixes from 46.6% to 75.9% (12). Block-level runtime variable traces beat both whole-function and per-line traces (11). I found no measurement of putting lint or type checks before tests as a separate gate.

**F. Where time goes.** Validation is 35-37% of steps in strong agents and correlates with success, so validation is not simply waste. Telling agents to write fewer tests cut calls by 25-35% for about −2 pts (17). I found no published measured wall-clock speed-up from restructuring a loop. The closest are token savings: repair vs resampling (11-54%) and fresh restarts (2).

## 3. Worth testing in this harness

1. **Turn test-spec output into executable assertions with concrete input/output pairs that the implement stage runs** (sources 5, 7). It is refuted if the first-pass green rate in implement does not rise, or if held-out acceptance failures increase.
2. **Write the executable tests in a context that never saw the implementation**, from the spec and the test-spec only (source 8). It is refuted if mutant kill rate and caught-bug rate do not differ from tests written after the code.
3. **Allow at most 2 repair rounds in the same context, then restart fresh** from the spec, the failing assertions and a one-line note on what was tried (sources 2, 3). It is refuted if rounds 3 and later supply more than 25% of the eventual fixes, or if restarts take longer to reach green.
4. **Shape the feedback: give the failing assertion plus the smallest failing input plus variable values at block boundaries**, not the full log (sources 11, 12, 13). It is refuted if the median number of rounds to green is unchanged.
5. **For logic-heavy steps, add a property-based test or counterexample check** (source 12). It is refuted if it catches nothing the red check and mutant sampling do not already catch.
6. **Replace the detailed step plan with a concise one**: criteria plus files, without pre-scripted commands (sources 14, 16). It is refuted if step correctness or exit-criteria hit rate falls.
7. **For a mid-tier implementer, compare a strong model planning beforehand with a strong model reviewing after the first green run** (sources 14, 15). It is refuted if planning beforehand wins on equal tokens.
8. **The harness already reruns everything itself, so have the model run only the targeted tests** (sources 17, 18). It is refuted if final correctness drops by more than 2 pts or wall-clock time is not reduced.

## 4. Ideas I found no measured support for

- **Prose test cases written before code improve the code.** No study measures this; every measured gain came from executable tests the coder could see.
- **More repair rounds beyond 3-5 help**, except with trace-guided debugging (11).
- **A model's own natural-language explanation of a failure helps.** Explanations from a weaker LLM were the weakest feedback measured (48.8). Only strong-expert or human explanations helped.
- **More tests in the prompt always help.** Measured degradation in source 6.
- **Lint or type checks as a separate stage before tests.** Not measured; compiler feedback was the weakest repair signal in source 13.
- **Plans help regardless of quality or model.** Plans that were wrong or mismatched to the model hurt (15, 16).
- **Agents writing more tests resolves more issues.** Test volume did not change outcomes (17).

---

## The brief the agent was given

You are doing web research for an engineering study. Read-only: do not edit any files, do not run code beyond what you need to fetch pages. Use web search and page fetches. PRIVACY: put only generic topic words in search queries and URLs; never include any person's name, email, local file path or private project name from this brief.

## Context (what the study is about)
A script-driven software delivery harness hands a coding model one stage "packet" at a time. Per work item the order is:
1. step-plan: list steps, files, completion criteria, and the shell commands that will confirm each criterion.
2. test-spec: write prose test cases (one per criterion) BEFORE any code.
3. implement: write the product code for one step, inside a loop that repeats until that stage's exit conditions hold.
4. test: write the executable tests AFTER the code, run them, and fix the product code until all pass; the harness then checks that each new test fails on the pre-change tree (red check), samples mutants, and reruns everything itself.
5. document, then a second-model review of the step, then commit.
Planning before this is: spec -> test strategy -> plan. After all steps: system tests, acceptance, release.

Observed problem: the first implementation is "moderately correct"; only when real tests are executed do logic gaps show, and the model then iterates test-run -> fix -> rerun to tune it. That iteration is slow. The harness will be driven by mid-tier models (roughly GPT "medium reasoning", Claude Sonnet-class at high effort, Grok at high effort), not the strongest ones. We want to know whether the ordering (plan -> prose test cases -> code -> executable tests -> fix loop) and the per-step exit criteria are the right design, or whether some stages are unnecessary or mis-ordered.

## Your job: PUBLISHED, MEASURED evidence (papers, benchmarks, technical reports with numbers)
Find what has actually been measured about these questions for LLM coding systems. For each, prefer 2023-2026 work, and prefer results that report mid-tier or weaker models separately:
A. Tests-first vs tests-after: does giving the model executable tests (or writing them) before the implementation raise first-attempt correctness or cut repair iterations? (e.g. work on test-driven development with LLMs, TDD benchmarks, "tests as specification", test-driven interactive code generation.)
B. Iterative repair on execution feedback: how much does each extra repair round buy, and when does it stop paying (e.g. studies of self-repair vs resampling at equal budget, "debugging decay", self-debugging, Reflexion-style loops, step-by-step debugger-style verification)? Any evidence on fresh restart vs continued repair in the same context.
C. Multi-stage flows that reason about the problem and generate extra tests before coding (e.g. test-based multi-stage code-generation flows, planning-then-search methods, multi-agent plan/code/debug pipelines): which stages did their ablations show to matter, and which did not?
D. Up-front planning granularity: evidence that detailed plans/specs help or hurt, by model strength (does planning help weaker models more or less?). Plan-with-strong / execute-with-weak splits.
E. What kind of feedback shortens the loop: failing test output vs. execution traces vs. explanations; concrete input/output examples in the spec vs. prose criteria; property-based tests; type/lint checks before tests.
F. Evidence about where agent time goes in real agentic coding runs (share spent in test-run/fix loops, redundant verification, re-reading), and measured speed-ups from changing loop structure.

## What to return (your final message is the whole deliverable; keep it under 1,400 words)
1. A table or list of the 10-16 most relevant sources: title, year, URL you actually opened, the key measured number(s), the models tested, and one line on relevance. Mark each claim MEASURED (you read the number in the source) or SECONDHAND (reported by someone else). Do not cite anything you did not open; if a paper is paywalled say what you could verify.
2. "What the evidence says" for A-F: 2-4 sentences each, with the strongest counter-evidence stated.
3. "Worth testing in a harness like this": up to 8 concrete, falsifiable changes to stage order or exit criteria that the evidence suggests, each with the source that motivates it and what result would refute it.
4. "Not supported": popular ideas you found no measured support for.
Be skeptical: benchmark tasks (single-function problems) differ from multi-file delivery work; say where a result may not transfer.
