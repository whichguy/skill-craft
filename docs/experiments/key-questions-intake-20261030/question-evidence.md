# Does asking or answering key questions about a software request, before planning or coding, improve agent outcomes?

Research report for the skill-craft / ShipLoop harness question. Compiled 2026-10-30.
Scope: papers, benchmarks and credible engineering write-ups, 2023 to 2026 (older foundational work noted where it is the only source).

## How to read this report

Every source below was opened in this session (abstract page, HTML or PDF text) unless it carries a tag:

- `[snippet]` seen only as a search-result summary, not opened. Treat numbers as unverified.
- `[blocked]` the page returned 403 or a redirect I could not follow. Numbers (if any) come from elsewhere and are labelled.
- `[abstract-only]` I read the abstract page but not the body, so any detail beyond the abstract is not claimed.

Evidence-strength grades used per area:

- **A** controlled comparison on repository-level coding agents (SWE-bench style), several models or a significance test. Where the answerer is an LLM-simulated user or a test oracle rather than a real requester, the table says "(oracle)".
- **B** controlled comparison, but on function-level or competitive-programming benchmarks, a single model, or a small sample (an oracle answerer is again flagged).
- **C** descriptive or observational (trajectory studies, failure taxonomies), or a small human study.
- **D** practitioner or vendor guidance, or a qualitative assessment, with no measurement.
- **E** searched for and not found, or could not be verified.

"Opened" means text extracted through the fetch tool. Full text (HTML or PDF) was extracted for: ClarifyGPT, TiCoder, HumanEvalComm, ClarifyCoder, Ambig-SWE, Ask or Assume, CLARITI, SWE-RPG, ClarifyCodeBench, ClarEval, Orchid, SpecFix, REA-Coder, AlphaCodium, Agentless, SWE-agent, SpecRover, MetaGPT, TGen, Rethinking Agent-Generated Tests, and the harness-design study. Everything else, including every item in Section 3.1, was read at abstract-page level, so any figure quoted for it is one the abstract states. Dialogue SWE-Bench was read through an alphaXiv summary page (`[abstract-level via alphaXiv]`).

A recurring caveat that shapes everything: almost all "asking helps" results use an **answerer that holds the ground truth** (a simulated user given the full issue, a test oracle, or a recruited human who can see the reference tests). That is exactly what an unattended harness lacks. Section 2.4 and Section 9 deal with what survives when no such answerer exists.

---

## 0. Bottom line

1. **With an answerer that knows the intent, asking before coding is the best-replicated positive result in this literature.** On underspecified SWE-bench Verified: 54.8% resolved with no asking, 69.4% to 70.4% with asking, versus 70.8% for the fully specified issue (Ask or Assume, Claude Sonnet 4.5, OpenHands). Interaction gains of up to 74% over non-interactive in Ambig-SWE (ICLR 2026). 22.4% to 36.8% resolved, against 41.6% for the full issue, in CLARITI (ICML 2026). ClarifyGPT with human answers: GPT-4 Pass@1 70.96 to 80.80 on MBPP-sanitized. Grade A for the SWE-level results, B for function-level.
2. **Without an answerer, the evidence is thinner and the gains are smaller.** LLM-only repair or self-QA loops give +4.3% average Pass@1 (SpecFix) or +7.9% to +30% relative on competitive-programming sets at roughly 26 times the tokens (REA-Coder). Models do not reliably find their own ambiguities (Orchid: detection precision about 50%, localization at most 23%), and extra reasoning did not improve clarification (ClarifyCodeBench). I found **no study** that measures hallucinated self-answers, or the effect of recording assumptions, on outcomes. Grade B at best, E for the assumption-recording question.
3. **Understanding the request is the largest single failure component for autonomous agents in the studies that measured it.** SWE-RPG (163 tasks, Claude Code, Codex, OpenCode, six backends, no user): requirement-stage failure is the largest failure component, 24.5% to 46.0% depending on configuration. SpecRover: 51.7% of the 207 unresolved SWE-bench Lite tasks carry the "ambiguous issue description" label. SWE-agent: 52.0% of unresolved trajectories were incorrect or over-specific implementations. Grade C, consistent across three independent studies.
4. **Whether to ask about repo-derivable facts depends on the model.** In Ambig-SWE, acquiring file-location hints lifted Claude 3.5 Haiku by 12.2 points and Claude 3.5 Sonnet by 21.6 points, Claude Sonnet 4 by 6.4, and made Qwen 3 Coder worse (55.4 to 52.4). Stronger models explore and reproduce the error themselves. No study cleanly splits "gain from asking" from "gain from self-research".
5. **Over-asking and ritual asking cost real accuracy.** Okanagan (HumanEvalComm) asked questions on clear problems and fell to 27.45% Pass@1 against the 65.58% of its base ChatGPT on the original tasks. ClarifyGPT's consistency-triggered asking gained 13.9% relative against 4.0% for an always-ask baseline. A forced single question round recovered 70.4% for Sonnet 4.5 but only 47.2% (full-spec 72.8%) for Kimi K2.6, so it is not model-independent.
6. **Who decides to ask matters.** Moving the "should I ask?" decision out of the coding agent into a separate step raised resolve rate from 61.2% to 69.4% (UA-Single vs UA-Multi). Cost per task was $3.50 for UA-Multi, against $2.03 for UA-Single and $1.63 for the fully specified baseline.
7. **Executable evidence helps; LLM self-critique and LLM-written tests are weak.** Self-critique without an external check degrades (Huang et al. ICLR 2024; Stechly et al. ICLR 2025). Agentless: adding generated reproduction tests to patch selection lifted SWE-bench Lite from 81 (27.0%, regression tests only) to 96 (32.0%) resolved issues, about $0.25 per issue extra. But encouraging or suppressing agent-written tests moved resolve rates by at most 2.6 points across four models (Rethinking the Value of Agent-Generated Tests), and generated reproduction tests can mislead (SWE-Doctor).
8. **Planning and ceremony pay for weak models and cost money for strong ones.** Planning on/off ablation (Fan et al. 2026): Nemotron-3 30B 13.6% to 25.2% on SWE-Bench Verified (significant); the two strongest models lose 0.4 to 2.0 points and save about 30% cost. Repository context files raised cost over 20% with no general success gain (Gloaguen et al.).
9. **No controlled evidence found** for: pre-mortem prompts, EARS or Gherkin acceptance criteria written first, LLM requirements interviews improving downstream code, question fatigue in coding-agent users. Spec-driven development evidence is practitioner or self-reported (grade D).

---

## 1. Verification notes and blocked sources

- Blocked (HTTP 403): the ACM Digital Library page for ClarifyGPT's journal version (DOI 10.1145/3660810; venue FSE 2024 is inferred from the DOI and search listing; every number below comes from the arXiv PDF); the ACM pages for a five-day proactive-AI field study and a "verification load and fatigue" CHI paper (not used); OpenAI's SWE-bench Verified pages (so the "38.3% underspecified" figure I recalled is **not verified and not used**); OpenAI's February 2026 post on retiring SWE-bench Verified (only a search snippet says it cites contamination).
- Anthropic's original 2025 "Claude Code: Best practices for agentic coding" post now redirects to the docs; the current docs page no longer carries the old "explore, plan, code, commit" text I could fetch. I could not retrieve the archived original, so I do **not** quote it.
- Pre-mortem human-factors figure (reported as roughly 30% better at identifying reasons for a future outcome; Mitchell, Russo, Pennington 1989): only secondary sources (book highlights) seen. Not verified.
- Wharton chain-of-thought report: the arXiv abstract is qualitative; the per-model percentages come from a search snippet of the authors' page.
- Evidence of question fatigue in real developers (interruption cost studies): only search-result summaries, not opened. Excluded from findings.

---

## 2. Area 1: clarifying questions for code generation

### 2.1 Summary table

| Source | Setting and answerer | Key result | Grade |
|---|---|---|---|
| ClarifyGPT (Mu et al., arXiv 2310.10996; FSE 2024 per ACM DOI) | Function-level, GPT-4 and ChatGPT; humans (10) answered 140 flagged MBPP-sanitized problems; simulator seeded with ground-truth tests for the other runs | GPT-4 Pass@1 70.96 to 80.80 (MBPP-sanitized), 51.52 to 60.19 (MBPP-ET); simulated: GPT-4 avg 68.02 to 75.75, ChatGPT 58.55 to 67.22 | B |
| TiCoder (Lahiri et al., arXiv 2208.05950; user study Fakhoury et al., IEEE TSE 2024) | Codex; user answers yes/no on generated tests; oracle = reference implementation | pass@1 absolute +22.49 (1 query) to +37.71 (5) on MBPP; +24.79 to +53.98 on HumanEval. Four LLMs: +45.97 avg within 5 queries. 15-programmer study: better judgement of AI code, less cognitive load | B (C for the study) |
| CodeClarQA (Li et al., ACL 2023) | Synthetic Q&A on API usage | Clarifications: +17.52 BLEU, +12.72 CodeBLEU, +7.7% exact match | B |
| HumanEvalComm (Wu and Fard, TOSEM 2025) | 164 modified HumanEval tasks; LLM answers questions | Code LLMs drop 35 to 52% relative Pass@1 on flawed requirements; more than 60% of responses still code; Okanagan agent lifts communication 14.21% to 72.73% and Pass@1 31.34% to 39.62% but falls to 27.45% on original tasks | B |
| ClarifyCoder (Wu et al., arXiv 2504.16331) | DeepSeek Coder 7B fine-tuned | communication rate 24.12% to 63.61%; HumanEval Pass@1 73.62 to 74.85; on ambiguous tasks second-round Pass@1 fell 48.05 to 23.71; false-positive asks not measured | B |
| Ambig-SWE (Vijayvargiya et al., ICLR 2026, arXiv 2502.13069) | 500 SWE-bench Verified issues summarized by GPT-4o; GPT-4o simulated user holds the full issue; 6 models | up to 74% gain over non-interactive; Sonnet 4 recovers 89% of full-spec, Sonnet 3.5 and Haiku up to 80%, DeepSeek-v2 59%, Llama 3.1 54% | A (oracle) |
| Ask or Assume (Edwards and Schuster, Findings of EMNLP 2026, arXiv 2603.26233) | Same 500-task variant; OpenHands; GPT-5.1 simulated user | Full 70.8, Hidden 54.8, forced-ask baseline 70.4, UA-Single 61.2, UA-Multi 69.4 | A (oracle) |
| Asking What Matters / CLARITI (Vijayvargiya, Viswanathan, Neubig, ICML 2026, arXiv 2604.14624) | OpenHands + Seed-OSS 36B; GPT-5 simulated user; 250 downstream instances | No clarification 22.4%, GPT-5 Nano 29.6%, GPT-5 35.6% (5.1 questions), CLARITI 8B 36.8% (3.0 questions), full issue 41.6% | A/B (oracle) |
| Dialogue SWE-Bench (King and Flanigan, arXiv 2606.13995) `[abstract-level via alphaXiv]` | 500 tasks with brief persona-driven user queries; open-weights user simulator | schema-guided agent 46.9% average resolve vs 32.9% for OpenHands; positive correlation between clarifying questions and success (no coefficient given) | B |
| SWE-RPG (Zhou et al. with D. Lo, arXiv 2608.09072) | 163 tasks, 3 agents x 6 backends, **no user** | mean resolve 31.5%; requirement-stage failure 24.5% to 46.0%; planning failure 5.5% to 17.8%; code-generation failure 7.4% to 37.4% | C |
| ClarifyCodeBench (Fang et al., arXiv 2607.00711) | LiveCodeBench v6 tasks with deleted information (419 tasks); GPT-4o judge matches questions to key questions | all six models lose 7.8 to 19.8 pass@1 points under ambiguity; most ask fewer questions than needed; ambiguity count 3 gives near-zero key-question hit rate | B |
| ClarEval (Li, Wu, Chang, arXiv 2603.00187) | 2,250 instances, 11 agents; rule-based user | GPT-4o 89.02% (oracle-clarified) vs 8.94% (ambiguous); no measure of whether agent-initiated asking raised pass rate | C |
| Orchid / "Clarity Is Not Assumed" (Yang et al., arXiv 2604.21505) | 1,304 function-level tasks, 6 models | average Pass@1 drop 7.22 points (16.25% relative), max 32.35; advanced models hurt most (GPT-4 about 28 to 31 points on Orchid-BCB); self-detection recall high, precision about 50% | B |

### 2.2 Notes on the central sources

**ClarifyGPT** (arXiv 2310.10996). Setup: a code-consistency check (sample solutions, run them on generated inputs, treat disagreement as ambiguity) decides whether to ask; then reasoning-based question generation; then code from the refined requirement. In the human run, 140 problems were judged ambiguous out of MBPP-sanitized, average 2.85 questions per problem, three annotators per problem, answers were given with the unit tests visible. Baselines: default 70.96, CoT 72.68, GPT-Engineer (asks up to five questions on every task) 73.77, ClarifyGPT 80.80. The authors say that asking about every requirement creates needless interaction on unambiguous ones and can hurt accuracy when the questions are off-topic. The zero-shot version of its own prompt gave only +2.1% (ChatGPT) and +0.8% (GPT-4) average relative gain; three demonstrations gave +15.1% and +11.5%. Simulated answers come from an LLM that sees the ground-truth tests, and the human run scored slightly higher than the simulated run. Relevance: the consistency check is a script-friendly ambiguity trigger that needs no human; the answer side is the oracle the harness lacks.

**TiCoder.** The "question" is a candidate test shown to the user for approval; the answerer is cheap yes/no. Codex code-davinci-002; MBPP 427 problems, HumanEval 164. Average queries until a user-consistent test appears: 1.7 (MBPP) and 1.5 (HumanEval); found on the first query in 61.12% and 73.17% of cases; found within ten queries in 87.12% and 95.73%. Ablation: random test ranking drops to 63.23 (MBPP) and 48.44 (HumanEval), the biggest single loss. Paper states a limitation that the oracle assumes users can always answer. Relevance: turning an intent question into a concrete, executable behavior check is both cheap for a human and checkable against reality for a harness.

**HumanEvalComm.** ChatGPT's Pass@1 on the original tasks is 65.58% and falls to 31.34% on flawed versions; Okanagan (ChatGPT base) scores 27.45% on the original tasks because it asks needless questions, and 39.62% on the flawed ones. The LLM that answers questions had a "false recovery" rate of 30 to 40% for several models (an answer that looks fine but is wrong), and the authors note its good-question labels are more lenient than humans'. Random removal of description text: ChatGPT asked questions on 54% of tasks only at 90% removal. Relevance: models under-ask by default, and an always-ask agent pays heavily on clear tasks.

**Ambig-SWE.** Detection of underspecification (Table 2, accuracy): Sonnet 4 reaches 0.89 with the strongest prompt, but Llama 3.1 and Qwen 3 Coder sit near 0.5; Qwen never asks without a forced prompt. Average questions per interaction: Qwen 3 Coder 6.02, DeepSeek-v2 4.57, Sonnet 4 4.03, Sonnet 3.5 3.80, Haiku 3.5 3.49, Llama 3.1 2.61. Qwen asks the most and gets the highest information gain (0.179) but no resolve-rate benefit; Sonnet 4 reaches similar gain (0.171) with about half the questions. Interaction improved effectiveness, not efficiency: Sonnet 4 steps rose from 65 to 75. Authors' caveats: simulated user may be more cooperative than humans; the underspecified issues are synthetic (information removed from real issues); Hidden-setting numbers may be inflated by memorization; Sonnet 4's Hidden run covers only 100 of 500 instances. Observation relevant to self-research: in the Hidden setting Sonnet 4 explores the codebase extensively and tries several solutions, and the authors suggest that stronger coders can extract more from a stack trace by reproducing the error themselves.

**Ask or Assume** (Findings of EMNLP 2026). Costs per task (Anthropic API): Full $1.63, Hidden $1.80, forced-ask baseline $1.40, UA-Single $2.03, UA-Multi $3.50. Questions per task: forced-ask 1.02 (97.6% of them in the early stage of the trajectory), UA-Single 1.84 (skewed late, 43.9%), UA-Multi 3.06 (spread early 41.8% and mid 43.4%). Conditional on asking, UA-Multi resolved 65.99% against 44.48% for Hidden on the same 344 tasks; on the 156 tasks it did not ask about, 76.92% against 77.56%, i.e. no loss from not asking. Ask rate rises with difficulty (62.4% under 15 min, 71.7% 15 min to 1 h, 78.6% 1 to 4 h, 100% over 4 h). v3 adds Kimi K2.6: forced-ask baseline 47.20%, UA-Single 61.60%, UA-Multi 69.40%, Full 72.80%; after an augmented prompt the agent still flagged the vast majority of tasks as underspecified (ask rates 82.99% to 100%). The paper reports no ablation that separates exploring from asking. Authors' caveats: simulated user may be unnaturally cooperative; the best result relies on prompting a second agent; single frontier model.

**CLARITI / Asking What Matters.** Information-need categories in 112 highly underspecified Verified issues (Table 1): error information 65%, implementation details 37%, expected behavior 33%, external references 15%, reproduction steps 12%, version/environment 3% (the text and table disagree on which category is 65%). Success fell from 43.8% (full issue) to 23.7% (underspecified) in their RQ1 setup. Even the best model's questions were answerable from the full issue only at score 0.373, and the success curve plateaus as question count rises while the answerable fraction falls. Ablation of the training reward: SFT alone 24.2%; without the answerability stage 24.4%; without the task-relevance stage 32.0%; full 36.8%. Relevance: question value comes from relevance to the task and answerability, not from volume.

**SWE-RPG.** Agents run autonomously. Ground truth averages 4.53 implicit requirement points per task. Lowest coverage clusters in interfaces, repository conventions and data invariants (Claude Code's lowest category, code structure, 54.2%; Codex 42.0% and 41.9% on code structure and data-structure semantics). Planning coverage did not track outcome: OpenCode had the lowest planning coverage (target location 43.8% vs Claude Code 79.7%) and the highest average resolve rate (33.0% vs 32.8%). The denominator of the 24.5% to 46.0% range is not stated clearly in the text. Relevance: for a harness without a user, the unmet need is exactly implicit requirements in conventions, interfaces and invariants, which are repository-checkable.

### 2.3 What fraction of the gain comes from asking versus self-research?

There is **no study that isolates the two** (grade E). What the data supports:

- Exploration alone leaves a large gap on underspecified tasks: Ask or Assume's Hidden condition (agent can read and run everything but cannot ask) reaches 54.8% against 70.8% for the full issue, a 16.0-point gap that asking closes almost entirely (69.4% to 70.4%) for Sonnet 4.5 with an oracle user.
- Which facts are worth asking for depends on the model. Ambig-SWE Table 1, resolve rate without versus with navigational information (file paths), share of issues where it was acquired: Sonnet 4 60.82% to 67.24% (12.24%); Sonnet 3.5 37.94% to 59.52% (8.96%); Haiku 3.5 24.78% to 36.94% (24.67%); DeepSeek-v2 4.62% to 13.19% (30.70%); Llama 3.1 4.28% to 6.34% (30.28%); Qwen 3 Coder 55.43% to 52.38% (18.58%). Stronger models gain less because they find locations themselves; weak models are helped by being told.
- Information that is not in the repository (expected behavior, the nature of the error) is where asking is irreplaceable; CLARITI's ranking by Shapley value puts error information first, implementation details second, expected behavior third (confidence intervals overlap, so the order is indicative).

### 2.4 What happens when no human answers

Evidence, in order of directness:

1. **LLM-only ambiguity repair, function level.** SpecFix (Jia et al., arXiv 2505.07270): samples 20 programs, clusters them by output behavior, scores semantic entropy and example consistency, rewrites the requirement with a contrastive prompt; up to three iterations; no human, no outside information. Average Pass@1 +4.3% and +3.4% problems solved by majority vote over three models on HumanEval+ and MBPP+ (GPT-4o on HumanEval+ 82.02 to 87.62; DeepSeek-V3 on HumanEval+ 87.80 to 91.99). Requirements repaired by one model raised another model's Pass@1 by 9.6% on average. It beat "ClarifyGPT-auto", an automated ClarifyGPT variant the authors built that answers from the requirement's own embedded examples instead of hidden tests, in every setting, and its rewrites were far shorter (for GPT-4o on MBPP+, requirement text grew 66% to 237% under SpecFix against about 577% for ClarifyGPT-auto). Caveats from the authors: small subsets, benchmark near saturation, three models.
2. **LLM self-QA with model-judged verification.** REA-Coder (Li et al., arXiv 2604.16198): the model builds a question checklist with reference answers over core requirement dimensions, answers it, compares its answers to the references, revises the requirement, then verifies by masking requirement spans and asking the model to recover them from its own code. No human; public tests serve only as a stopping criterion and hidden tests only for final scoring. Pass@1 relative gains 7.93%, 30.25%, 26.75%, 8.59%, 8.64% over five competitive-programming benchmarks (APPS, CodeContests, xCodeEval, LiveCodeBench-Lite), four LLMs. Ablation: dropping the QA alignment stage costs 5.82% on average; dropping the masking verification stage costs 9.99%. Cost: for DeepSeek-v3.2, 2.78 hours and 9.74 million tokens versus 0.32 hours and 0.37 million for zero-shot. Caveat from the paper: the same model writes the reference answers and judges the responses, so there is no external check; gains are strongest on weaker models.
3. **Models cannot reliably self-clarify.** Orchid: detection recall high, precision about 50%; localization at most 23%. ClarifyCodeBench: enabling thinking left clarification quality essentially unchanged (Claude Sonnet 4.5 key-question rate 0.12 either way) and lowered ambiguous-task pass@1 from 38.2 to 34.3 while raising complete-requirement pass@1 from 48.8 to 50.0. CLAMBER (ACL 2024): chain-of-thought and few-shot gave only marginal gains in identifying ambiguity and may cause overconfidence.
4. **Defaults are fragile.** "What Prompts Don't Say" (Yang et al., arXiv 2505.13360): LLMs infer unspecified requirements by default in 41.1% of cases; underspecified prompts are 2 times as likely to regress across model or prompt changes, with drops over 20%; listing every requirement did not reliably help; requirements-aware prompt optimization improved performance 4.8% on average.
5. **Early wrong assumptions persist.** "LLMs Get Lost in Multi-Turn Conversation" (Laban et al., arXiv 2505.06120): average 39% performance drop when instructions are revealed over turns, across six generation tasks and over 200,000 simulated conversations; mostly unreliability rather than lost ability; models make assumptions early, attempt final solutions prematurely, and do not recover.
6. **Recording assumptions and proceeding**: recommended by OpenAI's GPT-5 prompting guide (when uncertain, pick the most reasonable assumption, proceed, and document it for the user afterward; set the ask threshold by risk, low for payments or deletion, high for search) and by the Claude Code docs for unattended runs (a scheduled task cannot ask, so state what success looks like up front; an unwatched run can spend a whole night building on a wrong assumption). Both are grade D. **I found no study measuring the effect of recording assumptions on outcomes** (grade E).
7. **A stronger model as answerer.** Socratic Students (Ambati et al., arXiv 2512.13102): a student model asks a stronger teacher within a turn budget; question policy learned from task outcomes (SFT then DPO); Pass@5 gains over interactive baselines up to +22.9 points absolute on coding (HumanEval, OpenCoder) and +54.7 on math, matching baseline performance in three fewer turns. Grade B (function level). The answerer is a model, not a user, which is closest to a harness consulting an advisor model.
8. **Human expert Socratic steering** (SoHF, EMNLP Findings 2024): experts using Socratic-style feedback guided GPT-4, Gemini Ultra and Claude 3.5 Sonnet to solve 74% of problems the models had failed alone; 30 transcripts analyzed. Grade C, human in the loop.

Reading across these: autonomous question loops yield modest, benchmark-dependent gains (single digits to a few tens of percent relative on weaker models at a large token cost), versus 10 to 20 absolute points when an oracle answers. The part of intent that lives only in the requester's head is not recoverable by thinking harder.

### 2.5 Other results touching this area

- **SpecRover** (Ruan, Zhang, Roychoudhury, ICSE 2025, arXiv 2408.02232): iterative specification inference plus a reviewer agent and reproducer test; 31.00% on SWE-bench Lite and 19.31% on full SWE-bench (AutoCodeRover 19.00% on Lite); about $0.65 per issue. Of 207 unresolved Lite tasks, 51.7% were labelled ambiguous issue descriptions (SWE-bench Verified labels), 29.5% wrong fix location, 18.8% wrong modification. No ablation of the specification step is reported. Grade C.
- **CollabLLM** (Wu et al., ICML 2025 Outstanding Paper, arXiv 2502.00640): multiturn-aware rewards; +18.5% average task performance and +46.3% interactivity by LLM judges; in a 201-judge user study +17.6% satisfaction and 10.4% less time. Document-creation tasks; code not mentioned. Grade B.
- **Ask-before-Plan** (EMNLP Findings 2024, arXiv 2406.12639) and **IN3 / Mistral-Interact** (arXiv 2402.09205): clarification before planning for general agents; abstracts report no numbers. `[abstract-only]`
- **Curiosity by Design** (Darji and Lutellier, arXiv 2507.21285): a classifier for unclear coding prompts plus a fine-tuned question generator; user study found its questions better than the baseline's; no numbers in the abstract. `[abstract-only]`

---

## 3. Area 2: question decomposition, self-questioning and planning

### 3.1 General reasoning results (older, little software content)

| Source | Result | Relevance |
|---|---|---|
| Self-Ask (Press et al., arXiv 2210.03350, Findings of EMNLP 2023) | Defines the compositionality gap (model answers all sub-questions but fails the composite); the gap does not shrink with scale; asking and answering follow-up questions narrows it; structured follow-ups allow a search engine as the answerer. `[abstract-only]` | Origin of "question, then answer by tool". |
| Least-to-Most (Zhou et al., ICLR 2023, arXiv 2205.10625) | SCAN: at least 99% with 14 exemplars versus 16% for chain of thought. `[abstract-only]` | Decomposition helps when problems exceed exemplar difficulty. |
| Plan-and-Solve (Wang et al., ACL 2023, arXiv 2305.04091) | Beats zero-shot CoT on ten datasets, GPT-3; target errors: calculation, missing step, semantic misunderstanding. `[abstract-only]` | "Devise a plan first" prompting. |
| Step-Back (Zheng et al., ICLR 2024, arXiv 2310.06117) | PaLM-2L: MMLU Physics +7%, Chemistry +11%, TimeQA +27%, MuSiQue +7% | Asking for the governing principles before solving. |
| Rephrase and Respond (Deng et al., arXiv 2311.04205) | Model rephrases and expands the question before answering; improves across tasks; abstract gives no numbers. `[abstract-only]` | Cheap restatement of the request. |
| Chain-of-Verification (Dhuliawala et al., arXiv 2309.11495) | Draft, plan verification questions, answer them independently, revise; reduces hallucination on list questions, MultiSpanQA, long-form text. `[abstract-only]` | Independent answering avoids anchoring on the draft. |

### 3.2 Code-specific

| Source | Setup | Result | Grade |
|---|---|---|---|
| Self-planning Code Generation (Jiang et al., TOSEM, arXiv 2303.06689) | LLM outlines steps from the intent, then implements step by step | up to 25.4% relative Pass@1 over direct generation and 11.9% over CoT | B |
| Structured CoT for code (Li et al., arXiv 2305.06599) | Reason with sequence, branch, loop structures; ChatGPT and Codex on HumanEval, MBPP, MBCPP | up to 13.79% over CoT (relative or absolute not stated in abstract); humans preferred SCoT programs | B `[abstract-only]` |
| PlanSearch (Wang et al., arXiv 2409.03733) | Search over natural-language plans built from observations about the problem, not over code | LiveCodeBench, Claude 3.5 Sonnet: pass@200 77.0% versus 60.6% repeated sampling; best no-search pass@1 41.4%; gains predicted by diversity of ideas | B |
| AlphaCodium (Ridnik et al., arXiv 2401.08500) | Test-based flow: problem reflection in bullets (goal, inputs, outputs, rules), public-test reasoning, 2 to 3 candidate solutions ranked, AI-generated tests, run-fix iterations with "test anchors" | CodeContests GPT-4 pass@5: validation 19% to 44%, test 12% to 29%; DeepSeek-33B validation 7% to 20%, test 12% to 24%; GPT-3.5 validation 15% to 25%, test 8% to 17%; about 15 to 20 LLM calls per solution (about 100 per pass@5 submission). No per-stage ablation table. | B |
| REA-Coder | see 2.4 | 7.93% to 30.25% relative | B |
| Anthropic "think" tool (Mar 2025; updated Dec 2025 recommending the built-in feature instead) | Scratch-pad tool for stopping to check policy and tool results | tau-bench airline pass^1 0.370 to 0.570 (+54% relative) with optimized prompt; retail 0.783 to 0.812; SWE-bench +1.6% average (30 samples vs 144, p < .001); not useful for non-sequential or simple tool use | B |

### 3.3 Modern caveats

- **Reasoning models.** Wharton Prompting Science Report 2 (Meincke et al., arXiv 2506.07142): for reasoning models chain-of-thought prompting gives at most marginal accuracy gains and costs far more time and tokens. Snippet figures for GPQA Diamond: o3-mini +2.9%, o4-mini +3.1%, Gemini Flash 2.5 −3.3%, 20% to 80% more time `[snippet]`. Not software, but it tells you explicit "think about key questions first" prompts have decreasing value on current models.
- **Planning inside a coding harness (grade A).** Fan et al., "An Empirical Study of Harness Design for Coding Agents" (arXiv 2609.20804, Sept 2026): a todo-style `update_plan` tool plus prompt reminders on versus off, execution loop otherwise fixed, McNemar tests. SWE-Bench Verified, with plan / without plan: Nemotron-3 30B 25.20% / 13.60% (significant; runs ending with no edit: 27.8% with plan vs 68.6% without); 120B 44.00 / 46.60; 550B 65.80 / 67.80 ($2.33 vs $3.31 per task); Mistral-Medium-3.5-128B 68.60 / 69.00 ($3.14 vs $4.65). Their conclusion: planning works as an accuracy scaffold for the weakest model and as a cost saver for stronger ones. Terminal-Bench has only 89 tasks, so most contrasts there are not significant.
- **Plan completeness is not a proxy for success** (SWE-RPG): OpenCode, with the thinnest plans, resolved the most.
- **Software-specific evidence for Socratic prompting** is indirect: human-led (SoHF) and teacher-student (Socratic Students) settings show gains; a self-questioning framework (MIND) is a registered report for MSR 2026 with no results yet `[snippet]`. No evidence of a self-Socratic pass@1 gain on code (grade E).

---

## 4. Area 3: requirements elicitation with LLMs and structured specifications

### 4.1 LLM-conducted elicitation

| Source | Result | Downstream code effect measured? |
|---|---|---|
| Shen, Singhal, Breaux, "Requirements Elicitation Follow-Up Question Generation" (RE 2025, arXiv 2507.02858) | GPT-4o follow-up questions rated no worse than human-written on clarity, relevancy, informativeness; better when guided by common interviewer mistake types; abstract reports no numbers. `[abstract-only]` | No |
| LLMREI (Korn, Gorsch, Vogelsang, arXiv 2507.02564, RE 2025) | Interview chatbot, 33 simulated interviews; error count similar to human interviewers; extracts a large share of requirements; no numbers in abstract. `[abstract-only]` | No |
| Elicitron (Ataei et al., arXiv 2404.16045) | LLM-simulated users surface more latent needs than conventional human interviews (qualitative in abstract). `[abstract-only]` | No |
| MARE (Jin et al., arXiv 2405.03256) | Five agents, nine actions across elicitation, modeling, verification, specification; reported as 15.4% better than state-of-the-art approaches on requirements-model metrics. `[abstract-only]` | No |
| Lubos et al., LLM quality assurance of requirements (RE 2024, arXiv 2408.10886) | Evaluates requirements against ISO 29148, explains and rewrites; abstract gives no precision/recall. `[abstract-only]` | No |

None of these measure whether better elicited requirements produce better code. Grade E for the causal chain "elicit with LLM, then code better". A search summary reported LLM requirement-defect detection as high recall and low precision, and GPT-4o ambiguity-detection accuracy near 52% to 55% in one 2026 preprint (ClarifySTL); neither opened `[snippet]`. Orchid's own measurement agrees on the precision side (about 50%).

### 4.2 Does requirement quality change code quality?

- Orchid (Section 2.1): ambiguity costs 7.22 points on average (16.25% relative); intra-model output conflict for GPT-4 on Orchid-HEval rises from 14.09% to 28.29%; authors recommend treating divergence across samples as a trigger for clarification and prompting models to restate requirements and explain assumptions (not evaluated).
- Requirement smells (Villamizar et al., PROFES 2026, arXiv 2609.29208): adding semantic, syntactic and lexical smells to four applications' requirements lowered test-suite correctness with density, but clear requirements still produced faulty code. `[abstract-only]`
- HumanEvalComm (Section 2.1): 35% to 52% relative Pass@1 drops.
- Real SWE-bench Lite issues: Agentless' manual classification of all 300 found 4.3% with the exact patch in the description, 10.0% missing critical information, 5.0% with misleading solutions.

### 4.3 Structured or "spec-driven" development

All grade D unless noted:

- **Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl"** (martinfowler.com, 15 Oct 2025): qualitative, September 2025 trials. Kiro produced four user stories and 16 acceptance criteria for a small bug fix; spec-kit generated many repetitive markdown files that were harder to review than code, and a medium feature felt like overkill; agents did not reliably follow specs (ignored notes and duplicated existing classes, or followed an overly literal rule). Conclusion in her words: "Are we making something worse in the attempt of making it better?" The author notes the assessment was not systematic.
- **Piskala, "Spec-Driven Development: From Code to Contract"** (arXiv 2602.00180, Jan 2026): conceptual practitioner guide with three rigor levels (spec-first, spec-anchored, spec-as-source). A claim that circulates of up to 50% error reduction from refined specs does **not** appear in the abstract and I could not trace it (grade E).
- **Agarwal et al., "Spec-Driven Development as Prescribed and as Practiced"** (arXiv 2608.25202, last revised Oct 2026): Reddit analysis, 21 practitioner interviews (8 tool makers), 266 popular repositories from a corpus of 470,795 spec files. Practitioners report more reliable agent behavior with greater planning and review costs; spec drift; checks mostly at completion. Perceptions, not measured outcomes.
- **de Macedo, "From Prompt to Process"** (arXiv 2606.04967): taxonomy over six frameworks (Spec Kit, OpenSpec, BMAD, GSD, Spec Kitty, Reversa); finds convergence on persistent artifacts, contracts, traceability, human review; states there is a lack of benchmarks for the full process.
- **Kiro docs** (kiro.dev/docs/specs): requirements, design, tasks as three markdown files; the page does not mention EARS and gives no outcome numbers.
- **MetaGPT** (Hong et al., arXiv 2308.00352; role ablation Table 3, two tasks, human-rated executability 1 to 4): Engineer only 1.0 executability and 10 human revisions; plus Product Manager 2.0 and 6.5; plus Architect 2.5 and 4.0; all four roles 4.0 and 2.5; expense $0.915 to $1.385. Executable feedback added +4.2% and +5.4% Pass@1 on HumanEval and MBPP. Small, confounded (grade B/C): suggests structured intermediate artifacts help a simple generator.
- **Tufano et al., "Grounding AI Agents in Contracts: Spec-Driven Test Generation"** (SpecOps 2026, arXiv 2608.17177): Google production bugs; an agent that first documents preconditions, postconditions and undefined behaviors before writing tests found +9.8 percentage points more bugs (p = 0.0352) and +2.5 points branch coverage (p = 0.0034) than a conventional test-generation agent; LLM judge preferred its suites in 77.8% of comparisons. `[abstract-only]` This is the closest thing to a controlled "answer the key questions first" result in an industrial setting, but for test generation, not feature code. Grade B.
- **EARS**: no controlled study found that compares EARS-structured against free-text requirements for generated-code correctness (grade E).
- **Gherkin or acceptance criteria first**: studies found concern LLMs writing scenarios (expert-rated quality), not scenarios improving generated code (grade E). A blog repeats a claim of up to 50% fewer errors without a traceable source.

---

## 5. Area 4: pre-mortem, assumption surfacing, "what would make this plan fail"

- **Direct evidence for pre-mortem prompting of LLM plans against a plain "what could go wrong" baseline: none found** (grade E). Searches returned practitioner "premortem" skills only.
- Human foundation: prospective hindsight (Mitchell, Russo, Pennington, "Back to the future", J. Behavioral Decision Making 1989); the widely repeated figure of roughly 30% better at identifying reasons is from secondary sources I could not verify.
- **PreFlect** (Wang et al., arXiv 2602.07187, Feb 2026): "prospective reflection" that criticizes and refines a plan before execution, using planning errors distilled from past trajectories, plus dynamic re-planning; abstract claims it beats reflection-based baselines but gives no numbers. `[abstract-only]`
- **SIMMER** (Lu et al., COLM 2026, arXiv 2606.14574): household planning with a symbolic world model; frontier models produce at most 17% error-free plans and up to 56% of plans contain latent failures; explicit state reasoning via counterfactual foresight simulation reduced latent failures by up to 72% and irreversible failures by up to 75%. Non-software, grade B for the foresight idea.
- **Self-critique without an external check is unreliable.** Huang et al., "LLMs Cannot Self-Correct Reasoning Yet" (ICLR 2024): intrinsic self-correction often fails and can degrade performance. Stechly, Valmeekam, Kambhampati (ICLR 2025): GPT-4 self-critique caused a "significant performance collapse" on Game of 24, graph coloring and STRIPS planning, while a sound external verifier gave significant gains, and plain re-prompting with a verifier kept most of the benefit. A pre-mortem produced by the planning model and judged by the same model inherits this weakness unless failure hypotheses are checked by execution or by a different grounding source.
- **Assumption surfacing** has evidence only indirectly: "What Prompts Don't Say" (Section 2.4) shows 41.1% default inference and a 4.8% gain from requirements-aware optimization; Orchid recommends having the model restate requirements and explain assumptions but does not test it; REA-Coder's question checklist is a form of assumption check with a measured 5.82% contribution.

---

## 6. Area 5: research or spike before committing to a plan

| Source | Finding | Grade |
|---|---|---|
| Agentless (Xia et al., arXiv 2407.01489) | Localization, then repair, then validation. SWE-bench Lite 32.00% (96/300) at $0.70 with GPT-4o. Patch-selection ablation: majority vote 77 (25.67%); plus regression tests 81 (27.00%); plus generated reproduction tests 96 (32.00%), +$0.25 per issue. Reproduction tests are used only if they reproduce the issue on the original repo. The number of plausible reproduction tests plateaus as more are sampled, which the authors attribute to ambiguity in issue descriptions limiting reproduction and verification. | A- (single configuration) |
| SWE-agent (Yang et al., NeurIPS 2024, arXiv 2405.15793) | The agent prompt tells it to begin by reproducing the bug. Unresolved GPT-4 Turbo trajectories: 52.0% incorrect or over-specific implementation; 23.4% failed edit recovery; the remaining categories total under 25% (failed to reproduce, wrong file, wrong location, out of budget, gave up). Edit success 90.5% eventually, but 57.2% after one failed edit. | C |
| Ambig-SWE (Section 2.2) | Strong models explore and reproduce the error to recover missing information; weak ones benefit from asking. | C |
| SWE-Next (arXiv 2603.20691) | Successful trajectories: at least one test command 97.6%, reproduction script 90.3%; failed runs: 86.0% and 67.2%. Descriptive: both successful and failed runs explore, so presence of exploration does not discriminate. `[snippet]` | C |
| Fan et al. 2026 (Section 3.3) | Planning prompts help weak models, save cost on strong ones. | A |
| Gloaguen et al., "Evaluating AGENTS.md" (arXiv 2602.11988, v3 Sept 2026) | Repository-level context files do not generally improve task success and increase inference cost by over 20% on average; agents follow them and explore more; repository overviews are not helpful; useful for non-standard practices. Tested on SWE-bench tasks with LLM-generated files and on issues from repositories with developer-written files. | A |
| CodeAct (Wang et al., ICML 2024, arXiv 2402.01030) | Executable Python actions give up to 20% higher success than JSON or text actions across 17 LLMs. `[abstract-only]` | B |
| Self-Debugging (Chen et al., arXiv 2304.05128) | Execution results plus self-explanation: +2% to 3% on Spider (+9% hardest), up to +12% on TransCoder and MBPP with tests; matches baselines that generate over 10 times more candidates. `[abstract-only]` | B |
| Anthropic multi-agent research system (13 Jun 2025) | Lead Opus 4 with Sonnet 4 subagents beat single-agent Opus 4 by 90.2% on Anthropic's internal research eval; agents use about 4 times and multi-agent about 15 times the tokens of chat; token usage explains about 80% of variance on BrowseComp; effort-scaling rules embedded in prompts because agents misjudge needed effort (simple lookups 3 to 10 tool calls, comparisons 2 to 4 subagents, complex research over 10). Research tasks, not code. | D/B |
| Anthropic, "Measuring AI agent autonomy in practice" (18 Feb 2026, 500k interactive sessions) | Claude Code asks for clarification more often as task complexity rises. Reasons Claude stops itself: 35% presenting a choice between approaches, 21% gathering diagnostic information or test results, 13% clarifying vague or incomplete requests, 12% missing credentials or access, 11% approval. Humans interrupt mostly to add missing technical context or corrections (32%). Average human interventions per session fell from 5.4 to 3.3 while internal success on hardest tasks doubled. | C |
| OpenAI GPT-5 prompting guide | Recommends explicit context-gathering budgets: start broad, parallelize, stop when the exact content to change can be named or about 70% of top hits converge on one area, allow one refined batch if signals conflict, then act; tight budgets should carry an escape hatch to proceed under uncertainty. The 70% is a sample parameter, not a measured result. | D |
| Claude Code docs (fetched 2026-10-30) | The best-practices page has a brainstorm-first recipe (have Claude interview you until it can write SPEC.md, then build in a fresh session); plan mode for changes you want to review; delegating research to subagents; a test for what belongs in CLAUDE.md (only facts Claude would not find by looking at the repo); and giving Claude a pass/fail check to run. Its "what you can stop doing" table retires describing architecture and file layout in CLAUDE.md (Claude reads the repo itself), delegating to a subagent merely for a better answer (a fresh independent reviewer helps because it has not seen your reasoning), and "think hard" phrasing (effort setting is the control). No measurements. | D |
| Cursor, "Best practices for coding with agents" (Lee Robinson, 9 Jan 2026) | Plan Mode researches the codebase, asks clarifying questions, drafts an editable plan; planning is optional for quick or familiar changes; revert and re-plan instead of patching. No numbers. | D |
| Anthropic, "Effective harnesses for long-running agents" (26 Nov 2025) | Initializer produced a 200+ feature list (JSON with a `passes` field, because models alter JSON less than markdown); failure modes: trying to one-shot the app, declaring victory early, marking features done without end-to-end testing; mitigation: one feature per session, browser automation. Qualitative only. | D |

Overall: reproducing the issue and validating with an executed reproduction are the best-supported "experiment before commitment" steps (Agentless +5.0 points). Evidence for a generic research phase raising resolve rate is mostly descriptive or vendor guidance, and the one controlled study of added context (AGENTS.md) found cost without success gain.

---

## 7. Area 6: test-first and acceptance-criteria-first planning

| Source | Setup | Result | Grade |
|---|---|---|---|
| TGen, "Test-Driven Development for Code Generation" (Mathews and Nagappan, ASE 2024, arXiv 2402.13521) | Tests added to the prompt; GPT-4 Turbo main, Llama 3 70B; EvalPlus MBPP (399) and HumanEval (164), CodeChef (1,100) | GPT-4, public tests: +12.0% of MBPP problems and +8.5% of HumanEval; remediation loop +2.8% and +3.0% more. Private-test totals: tests lift MBPP 69.67 to 82.45 and HumanEval 78.66 to 87.81 (remediation to 87.71 and 93.30). Llama 3 70B: MBPP 46.37 to 75.94 to 84.96, HumanEval 62.20 to 75.61 to 84.15. More tests sometimes broke previously correct solutions ("lost in the middle"); MBPP gains decline after about three tests. | B |
| TiCoder (Section 2.1) | tests as intent clarification | see above | B |
| Agentless | generated reproduction tests as patch filter | +5.0 points | A- |
| SWT-Bench (Mündler et al., arXiv 2406.12952) | issue-to-test generation | code-repair agents beat dedicated test generators; per the abstract, using generated tests as a patch filter doubles SWE-Agent's precision `[abstract-only]` | B |
| Otter (Ahmed et al., ICML 2025, arXiv 2502.05368) | TDD-Bench-Verified | outperforms prior issue-to-test systems; abstract gives no numbers `[abstract-only]` | B |
| TDFlow (Han et al., EACL 2026, arXiv 2510.23761) | human-written tests supplied | 88.8% on SWE-Bench Lite and 94.3% on Verified; 7 test-hacking cases in 800 manually inspected runs; the remaining obstacle is writing valid reproduction tests | B |
| Rethinking the Value of Agent-Generated Tests (Chen et al., arXiv 2602.07900) | mini-SWE-agent on SWE-bench Verified, six models; prompts that encourage or discourage writing tests | Resolved counts: GPT-5.2 encourage 359 vs 359; Gemini 3 Pro encourage 371 to 366; Kimi K2 Thinking discourage 317 to 304 (−2.6 points); DeepSeek v3.2 discourage 300 to 291 (−1.8). No McNemar test significant (p from 0.228 to 1.000). Suppressing tests cut input tokens 33% to 49% and API calls 25% to 35%. Agent tests were mostly print statements (roughly 75% to 86% of prints plus assertions, a share computed from the paper's count tables), i.e. observation channels, not oracles. | A |
| SWE-Doctor (Guo et al., arXiv 2607.00990) | bug reproduction tests as patch guidance | preliminary study: generated tests can hurt (fail-to-fail tests mislead; fail-to-pass tests cover one manifestation and yield partial patches); multi-faceted tests plus runtime diagnosis reach 75.7% (Verified) and 59.4% (Pro) averaged over five backends `[abstract-only]` | B |
| Building to the Test (Ma et al., arXiv 2606.28430) | claude-opus-4.7 and gpt-5.5 re-implement a component under a hidden 222-test oracle, 18 runs | with the oracle in the loop scores approach perfect but the library is dead or absent and the demo hard-codes the tested behavior; without the oracle the library exists but is incomplete | C `[abstract-only]` |
| Cursor and Claude docs | TDD loop: write tests, confirm they fail, commit, then implement without modifying tests | No numbers | D |

Reading: tests supplied from outside the generating model (humans, specs, existing suites) help clearly (TGen, TDFlow). Tests the same agent writes help mostly as a patch filter when they are verified to fail first (Agentless, SWT-Bench), and not as a general driver of success (Chen et al.). The hazard is optimizing for the check rather than the request (Building to the Test; TDFlow's test-hacking cases).

---

## 8. Area 7: risks, cost, and choosing which questions to ask

### 8.1 Over-asking and under-asking

- Models under-ask by default: HumanEvalComm (more than 60% still produce code); ClarifyCodeBench (most ask fewer questions than the annotated count; differences −0.10 to −1.41 per task, Gemini-2.5-Flash +0.57 but missing key ambiguities); Ambig-SWE (without a forced prompt, models default to non-interactive; Qwen never interacts).
- They also over-ask when pushed: Okanagan on clear problems (27.45% against 65.58%); Ambig-SWE false-positive rates up to 0.93 to 0.95 for Llama 3.1 at moderate to strong prompts and Sonnet 3.5 at 0.24 to 0.36; Orchid precision about 50%; Ask or Assume's Kimi K2.6 flags nearly everything as underspecified (82.99% to 100%).
- Detection quality is model-specific and prompt-sensitive (Ambig-SWE Table 2: Sonnet 4 accuracy 0.74 with neutral prompting and 0.89 with strong; DeepSeek-v2 falls from 0.69 to 0.51 as encouragement increases).
- Picking the right question is hard: QuestBench (Li, Kim, Wang, NeurIPS 2025 Datasets and Benchmarks, arXiv 2503.22674): models do well on grade-school math variants but only about 40% to 50% on logic and planning problems that need exactly one clarifying question, and solving the full problem does not guarantee asking the right question. CLAMBER (ACL 2024): CoT and few-shot give marginal gains and may cause overconfidence.

### 8.2 How many questions

| Source | Questions | Outcome |
|---|---|---|
| ClarifyGPT | 2.85 average, asked only on the 140 MBPP-sanitized problems the consistency check flagged as ambiguous | +13.9% relative |
| TiCoder | 1.5 to 1.7 queries to find a consistent test; gains measured at 1 to 5 | +22 to +54 points |
| Ask or Assume (Sonnet 4.5) | 1.02 forced up front vs 3.06 (UA-Multi) | 70.4% vs 69.4% |
| Ask or Assume (Kimi K2.6) | forced up front | 47.2% (full 72.8%) |
| CLARITI | 3.0 vs GPT-5's 5.1 | 36.8% vs 35.6% |
| Ambig-SWE | 2.6 to 6.0 | highest-asking model (Qwen, 6.02) shows no resolve-rate gain |
| Zhang and Choi (arXiv 2311.09469) | allowed on only 10% of examples chosen by uncertainty | doubles the gain of choosing the 10% at random |

CLARITI's analysis agrees: success plateaus as question count rises while the answerable share falls.

### 8.3 Value-of-information and uncertainty-based selection

- **Uncertainty of Thoughts** (Hu et al., NeurIPS 2024, arXiv 2402.03271): simulate futures, reward by information gain, choose the question with the best expected reward; +38.1% average task success over direct prompting on medical diagnosis, troubleshooting and 20 Questions, fewer questions needed. `[abstract-only]`
- **Active Task Disambiguation** (Kobalczyk et al., arXiv 2502.04485): Bayesian experimental design; choosing questions by information gain beats reasoning only in the space of questions; abstract gives no numbers. `[abstract-only]`
- **Clarify When Necessary** (Zhang and Choi): "intent-sim" entropy over user intents decides whether to ask. `[abstract-only]`
- **Modeling Future Conversation Turns** (Zhang, Knox, Choi, ICLR 2025, arXiv 2410.13788): preference labels from simulated future turns; +5% F1 and +3% accuracy on whether to ask. `[abstract-only]`
- **ClarifyGPT / SpecFix / Orchid**: disagreement among sampled solutions (execution consistency, semantic entropy, conflict rate) as the ambiguity trigger. These need no user and are cheap to script.
- **Information categories as a schema**: CLARITI's six categories of missing information (Section 2.2); SWE-RPG's six practitioner-derived categories of implicit requirement, running from C1 functional intent and scope to C5 code structure and C6 data-structure semantics (middle categories not retrieved); Dialogue SWE-Bench's "schema-guided" agent beat OpenHands by about 14 points (46.9% vs 32.9%), but I did not verify what its schema contains, so I do not claim it is a question-category schema.

### 8.4 Cost of ceremony (measured)

| Item | Cost or effect |
|---|---|
| UA-Multi (separate intent agent) | $3.50 per task vs $1.63 full-spec, 2.1 times; UA-Single $2.03 |
| REA-Coder | 9.74M tokens and 2.78 h vs 0.37M tokens and 0.32 h zero-shot (about 26 times tokens) |
| AlphaCodium | 15 to 20 LLM calls per solution |
| Anthropic multi-agent research | about 15 times chat tokens |
| AGENTS.md context files | +20% cost on average, no general success gain |
| Planning, strong models | up to 32% cheaper with planning, small accuracy loss; weak model gains accuracy |
| Test writing | suppressing agent tests cuts 33% to 49% of tokens with at most 2.6 points change |
| Spec-driven tooling | qualitative: 4 user stories and 16 acceptance criteria for a small bug fix; reviewing specs can be harder than reviewing code (Böckeler) |
| Ambig-SWE | interaction raised steps from 65 to 75 for Sonnet 4: effectiveness, not efficiency |

### 8.5 Humans in the loop

- TiCoder user study (15 programmers): significantly better at judging AI code and less cognitive load when intent was formalized as tests (grade C).
- CollabLLM: 201 judges, +17.6% satisfaction, 10.4% less time (grade B).
- Question fatigue and interruption cost in coding-agent users: **no verified primary evidence**. Anthropic's autonomy post is descriptive of how often Claude Code stops and why, not of fatigue (grade C). Search summaries of proactive-assistant field studies were not verified.

### 8.6 Validity of the evidence base

- Simulated users are optimistic or unstable: Lost in Simulation (Seshadri et al., arXiv 2601.17087, ACL 2026): success rates moved by up to 9 percentage points depending on which LLM played the user; simulators mis-calibrate difficulty and differ from human failure patterns. HumanEvalComm: 30 to 40% false-recovery rates in LLM answers. Ambig-SWE and Ask or Assume both warn that simulators may be more cooperative than real users.
- Synthetic underspecification: removing information from a well-specified issue guarantees the missing information exists and is known to the simulator. Real requests contain preferences not yet formed and unknown unknowns; the Claude docs' "interview me" flow targets that case, with no measurement.
- Benchmark contamination: Ambig-SWE notes possible memorization inflating Hidden-setting results; OpenAI reportedly retired SWE-bench Verified evaluation in 2026 over contamination `[blocked / snippet]`.
- LLM judges produce several headline metrics (good-question rate, key-question hit, coverage); human agreement was checked only on small samples.

---

## 9. What this means for an unattended, script-driven harness

The evidence supports a narrower claim than "ask key questions first". It supports: **find out where the request is uncertain, resolve what can be resolved by evidence, and be explicit about what cannot.**

1. **Triage every key question by who can answer it.**
   - Repository-derivable (conventions, interfaces, data invariants, file locations, existing behavior): inspect. SWE-RPG shows these are the weak spots of autonomous agents; Ambig-SWE shows strong models already recover them, weak models need help.
   - Execution-derivable (does the bug reproduce, what does this function return): run a probe. Best supported: reproduction tests (Agentless +5.0 points), TiCoder-style behavior checks, self-debugging.
   - External-knowledge (library behavior, standards): research. Only vendor guidance and the multi-agent research results (not code) support this.
   - Another model as answerer (advisor): Socratic Students shows gains on function-level coding when a student trained with a learned question policy asks a stronger teacher. No repository-level evidence.
   - Only the requester knows (intent, preference, acceptance): no amount of reasoning recovers it (Orchid, ClarifyCodeBench). Record as an assumption with a default and a testable acceptance check; carry it through every context clear because early wrong assumptions persist (Lost in Conversation). Treat the assumption log as an input to review, not as ground truth.

2. **Gate the stage with a script, not with the coding agent.** The separate-intent-agent result (61.2% to 69.4%) and the finding that a coding agent asks late or too often argue for a dedicated, mechanical decision point. Triggers with support: disagreement among cheap samples (ClarifyGPT, SpecFix, Orchid), and task difficulty (Ask or Assume: the well-calibrated scaffold asked more as annotated difficulty rose). Skipping the stage for clear small changes has vendor guidance (Cursor and Claude docs, grade D) and indirect measured support (the planning ablation; Okanagan's cost on clear tasks), but no direct test of a size-based gate.

3. **Rank questions by expected change to the plan and stop when the best remaining question is worth little.** Do not use a fixed question count: the plateau is model-dependent (forced single round works for Sonnet 4.5, fails for Kimi K2.6; Qwen's 6 questions bought nothing). Task relevance and answerability were the reward terms that mattered in CLARITI. A fixed list of information needs is a reasonable scaffold; the list below is my synthesis from CLARITI's categories and SWE-RPG's weak areas, not a tested schema: expected behavior, error and reproduction information, implementation constraints, interfaces, data invariants, external references, environment. For orientation only: CLARITI put 26.4% of its questions on error information against 10.2% for GPT-5, whose questions clustered around one or two categories, and it matched or slightly exceeded GPT-5 (36.8% vs 35.6%) with 41% fewer questions; the difference is small and I saw no significance test, so this is suggestive, not established.

4. **Make answers executable and keep verification independent of the author.** Self-critique collapses without an external check (Huang; Stechly); REA-Coder's code-to-requirement verification stage contributed more (9.99%) than its question-and-answer stage (5.82%), although that verification is judged by the model, not executed; generated tests help as filters when shown to fail first but are not oracles (Chen et al.; SWE-Doctor; Building to the Test). Prefer failing-before, passing-after probes against the real system, keep held-out checks the generating agent cannot see, and have a different model or script judge the answers.

5. **Scale ceremony to measured gain on your own evidence.** Costs in the literature range from 2 to 26 times tokens; gains concentrate on underspecified tasks and on weaker models. Each question stage should log whether its answer changed the plan, a test, or a default; questions whose answers never change anything should be dropped. A cheap internal experiment would mirror Ambig-SWE or Ask or Assume: the same request set with the question stage on or off, crossed with the answer source (none, repository only, repository plus execution, repository plus execution plus oracle), reporting resolve rate, cost, and plan-change rate.

---

## 10. Evidence gaps (stated plainly)

- No study separates the gain from asking from the gain from self-research, or measures hallucinated self-answers.
- No controlled evidence that recording assumptions improves final outcomes, or that unattended agents proceeding on recorded defaults do better than stopping.
- No controlled study of pre-mortem or failure-hypothesis prompts on coding plans.
- No controlled comparison of EARS, Gherkin or user-story forms against free text for generated-code correctness; spec-driven development evidence is perceptions and qualitative review.
- No study connecting LLM-conducted requirements elicitation to downstream code quality.
- No verified evidence on question fatigue for coding-agent users.
- Most SWE-level evidence uses synthetic underspecification, an LLM user holding the answer, a single scaffold, one or two model families and a possibly contaminated benchmark.

---

## 11. Source index

Core clarification and ambiguity (code)
- ClarifyGPT, arXiv 2310.10996: https://arxiv.org/abs/2310.10996 (journal version DOI 10.1145/3660810, blocked)
- TiCoder, arXiv 2208.05950: https://arxiv.org/abs/2208.05950 ; user study arXiv 2404.10100: https://arxiv.org/abs/2404.10100
- CodeClarQA, ACL 2023: https://arxiv.org/abs/2212.09885
- HumanEvalComm, TOSEM 2025: https://arxiv.org/abs/2406.00215
- ClarifyCoder: https://arxiv.org/abs/2504.16331
- Ambig-SWE, ICLR 2026: https://arxiv.org/abs/2502.13069
- Ask or Assume, Findings of EMNLP 2026: https://arxiv.org/abs/2603.26233 , https://aclanthology.org/2026.findings-emnlp.15/
- Asking What Matters (CLARITI), ICML 2026: https://arxiv.org/abs/2604.14624 , https://proceedings.mlr.press/v306/vijayvargiya26a.html
- Dialogue SWE-Bench: https://arxiv.org/abs/2606.13995
- SWE-RPG: https://arxiv.org/abs/2608.09072
- ClarifyCodeBench: https://arxiv.org/abs/2607.00711
- ClarEval: https://arxiv.org/abs/2603.00187
- Orchid, "Clarity Is Not Assumed": https://arxiv.org/abs/2604.21505
- SpecFix: https://arxiv.org/abs/2505.07270
- REA-Coder: https://arxiv.org/abs/2604.16198
- SpecRover, ICSE 2025: https://arxiv.org/abs/2408.02232
- Socratic Students: https://arxiv.org/abs/2512.13102
- SoHF, EMNLP Findings 2024: https://www.amazon.science/publications/socratic-human-feedback-sohf-expert-steering-strategies-for-llm-code-generation
- CollabLLM, ICML 2025: https://arxiv.org/abs/2502.00640
- Ask-before-Plan: https://arxiv.org/abs/2406.12639 ; IN3: https://arxiv.org/abs/2402.09205 ; Curiosity by Design: https://arxiv.org/abs/2507.21285
- What Prompts Don't Say: https://arxiv.org/abs/2505.13360
- LLMs Get Lost in Multi-Turn Conversation: https://arxiv.org/abs/2505.06120
- Lost in Simulation, ACL 2026: https://arxiv.org/abs/2601.17087

Question selection and risks
- Uncertainty of Thoughts, NeurIPS 2024: https://arxiv.org/abs/2402.03271
- Active Task Disambiguation: https://arxiv.org/abs/2502.04485
- QuestBench, NeurIPS 2025: https://arxiv.org/abs/2503.22674
- CLAMBER, ACL 2024: https://arxiv.org/abs/2405.12063
- Clarify When Necessary: https://arxiv.org/abs/2311.09469
- Modeling Future Conversation Turns, ICLR 2025: https://arxiv.org/abs/2410.13788

Decomposition and planning
- Self-Ask: https://arxiv.org/abs/2210.03350 ; Least-to-Most: https://arxiv.org/abs/2205.10625 ; Plan-and-Solve: https://arxiv.org/abs/2305.04091 ; Step-Back: https://arxiv.org/abs/2310.06117 ; RaR: https://arxiv.org/abs/2311.04205 ; CoVe: https://arxiv.org/abs/2309.11495
- Self-planning: https://arxiv.org/abs/2303.06689 ; SCoT: https://arxiv.org/abs/2305.06599 ; PlanSearch: https://arxiv.org/abs/2409.03733 ; AlphaCodium: https://arxiv.org/abs/2401.08500
- Wharton CoT report: https://arxiv.org/abs/2506.07142
- Harness design study: https://arxiv.org/abs/2609.20804
- Anthropic think tool: https://www.anthropic.com/engineering/claude-think-tool

Requirements and specs
- Follow-up question generation: https://arxiv.org/abs/2507.02858 ; LLMREI: https://arxiv.org/abs/2507.02564 ; Elicitron: https://arxiv.org/abs/2404.16045 ; MARE: https://arxiv.org/abs/2405.03256 ; requirements QA: https://arxiv.org/abs/2408.10886
- Requirement smells: https://arxiv.org/abs/2609.29208
- Böckeler: https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- Piskala: https://arxiv.org/abs/2602.00180 ; Agarwal et al.: https://arxiv.org/abs/2608.25202 ; de Macedo: https://arxiv.org/abs/2606.04967 ; Tufano et al.: https://arxiv.org/abs/2608.17177 ; Kiro docs: https://kiro.dev/docs/specs/
- MetaGPT: https://arxiv.org/abs/2308.00352

Foresight and self-critique
- PreFlect: https://arxiv.org/abs/2602.07187 ; SIMMER: https://arxiv.org/abs/2606.14574 ; Huang et al.: https://arxiv.org/abs/2310.01798 ; Stechly et al.: https://arxiv.org/abs/2402.08115

Agents, exploration, tests
- Agentless: https://arxiv.org/abs/2407.01489 ; SWE-agent: https://arxiv.org/abs/2405.15793 ; AGENTS.md study: https://arxiv.org/abs/2602.11988 ; CodeAct: https://arxiv.org/abs/2402.01030 ; Self-Debug: https://arxiv.org/abs/2304.05128 ; SWE-Next (snippet): https://arxiv.org/abs/2603.20691
- TGen: https://arxiv.org/abs/2402.13521 ; SWT-Bench: https://arxiv.org/abs/2406.12952 ; Otter: https://arxiv.org/abs/2502.05368 ; TDFlow: https://arxiv.org/abs/2510.23761 ; SWE-Doctor: https://arxiv.org/abs/2607.00990 ; Rethinking agent tests: https://arxiv.org/abs/2602.07900 ; Building to the Test: https://arxiv.org/abs/2606.28430

Vendor and engineering write-ups
- Claude Code best practices: https://code.claude.com/docs/en/best-practices ; common workflows: https://code.claude.com/docs/en/common-workflows
- Anthropic multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic effective harnesses: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic agent autonomy: https://www.anthropic.com/research/measuring-agent-autonomy
- Cursor agent best practices: https://cursor.com/blog/agent-best-practices
- OpenAI GPT-5 prompting guide: https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide

Local scratch copies of fetched PDFs (text-extracted) are under /private/tmp/claude-501/-Users-dadleet-src-skill-craft/09ce7a42-fa70-4884-8d71-fe8a0ac1238f/scratchpad/research/src/ (AlphaCodium, Agentless, SWE-agent, SpecRover, Ambig-SWE, ClarifyGPT, MetaGPT).
