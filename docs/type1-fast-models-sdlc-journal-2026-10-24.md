# Type 1 (fast, low-deliberation) models in the SDLC, and what ShipLoop does with them

Journal opened 2026-10-24. Consumer: the owner, deciding whether ShipLoop should get a per-step model or effort
lever; read at that decision. Status words: **firm** (primary source or measured here), **interim** (secondary or
single run), **exploratory** (anecdote or vendor claim). Nothing here changes behaviour; no skill file was edited.

## 1. Question and reading

"Type 1 models" is read as Type 1 / System 1 in the dual-process sense: fast, low-deliberation inference, as opposed to
slow reasoning models. Two axes are easy to confuse and the evidence separates them:

- **Speed and size** (small or specialised model, fast hardware): Cursor Fast Apply, SWE-grep, Codex-Spark.
- **Deliberation depth** (thinking tokens, reasoning effort): the same model run low or high.

Claude Code "fast mode" is a third thing (Opus with faster output) and is not Type 1.

## 2. External findings

| # | Where in the SDLC | Who | What was shown | Status |
|---|---|---|---|---|
| E1 | Edit apply | Cursor Fast Apply | A frontier model plans, a fine-tuned Llama-3-70b applies the edit at about 1,000 tokens/s, 13x vanilla, 9x the earlier GPT-4 deployment; about 450 full-file edits, graded by Claude-3 Opus (self-preference caveat in the post). Diff format was less reliable than full-file rewrite. [Cursor](https://cursor.com/blog/instant-apply) | firm (2024, vendor) |
| E2 | Context retrieval | Cognition SWE-grep and SWE-grep-mini in Windsurf Fast Context | RL-trained retrieval subagent, up to 8 parallel tool calls for at most 4 turns; over 650 and over 2,800 tokens/s against Haiku 4.5 at 140; "matching or outperforming" frontier models on weighted F1; on hard SWE-bench Verified tasks with Sonnet 4.5 as main model, "significantly lower end-to-end time" with no figures in the text, and the authors call the comparison "not meant to be an extremely rigorous benchmark". [Cognition](https://cognition.com/blog/swe-grep) | interim (vendor, charts only) |
| E3 | Reasoning vs formatting split | Aider architect/editor | o1-preview solo 79.7%; with o1-mini or DeepSeek as editor 85.0%; Sonnet 3.5 77.4% to 80.5%; o1-mini 61.1% to 71.4% with DeepSeek. The editor is not a small fast tier; the gain came from separating the two jobs. [Aider](https://aider.chat/2024/09/26/architect.html) | firm (2024) |
| E4 | Planner plus fast workers | Anthropic Haiku 4.5 | "similar levels of coding performance but at one-third the cost and more than twice the speed" against Sonnet 4; Sonnet 4.5 can "orchestrate a team of multiple Haiku 4.5s". [Anthropic](https://www.anthropic.com/news/claude-haiku-4-5) | firm as a claim, vendor |
| E5 | Subagent model choice | Claude Code docs | Current docs: Explore and Plan follow the main conversation's model; only `claude-code-guide` runs on Haiku; a user-defined `Explore` with `model: haiku` is the documented route to cheap exploration. An October 2025 quote said Haiku 4.5 powered Explore, so the default has moved. [Docs](https://code.claude.com/docs/en/sub-agents) | firm (page read to character 100,000 of 116,349) |
| E6 | Routing by difficulty | Gemini CLI auto routing; Amp rush and oracle | Gemini CLI classifies a prompt and sends simple ones to Flash, complex ones to Pro. Amp's rush mode is for small, well-defined tasks and is "weaker on complex work"; its advice is rush builds, the oracle plans and reviews. [Gemini CLI](https://www.mintlify.com/google-gemini/gemini-cli/concepts/models), [Amp](https://ampcode.com/news/rush-2.0) | interim (secondary summaries) |
| E7 | Real-time coding | OpenAI GPT-5.3-Codex-Spark on Cerebras | Over 1,000 tokens/s, minimal targeted edits, does not run tests unless asked; Heise reports lower Terminal-Bench 2.0 accuracy. [OpenAI](https://openai.com/index/introducing-gpt-5-3-codex-spark/), [Heise](https://heise.de/-11175885) | interim |
| E8 | Effort as a dial | Anthropic Opus 4.5 `effort` | At medium effort Opus 4.5 matches Sonnet 4.5's best SWE-bench Verified score with 76% fewer output tokens; at the highest effort it exceeds Sonnet 4.5 by 4.3 points with 48% fewer tokens. Default effort is high. [Anthropic](https://www.anthropic.com/news/claude-opus-4-5) | firm (vendor) |
| E9 | Overthinking | Apple, "Illusion of Thinking"; "Danger of Overthinking" | Low-complexity puzzles: non-thinking models match or beat thinking ones with fewer tokens, thinking wins in the middle, both collapse at the top (critics dispute the framing). On SWE-bench Verified, 4,018 trajectories, higher overthinking scores correlate with lower performance; picking the lower-overthinking solution improved performance "by almost 30%" and cut compute 43%. [Apple](https://arxiv.org/pdf/2506.06941), [Overthinking](https://arxiv.org/abs/2502.08235) | firm as papers; transfer to SDLC steps is inference |
| E10 | Fixed pipeline, narrow LLM steps | Agentless | Localise, repair, validate with no agent loop: SWE-bench Lite 32.67% at $0.68 per issue in the FSE 2025 version (27.33% at $0.34 in v1). 2024 numbers, now low in absolute terms. [Agentless](https://arxiv.org/abs/2407.01489v2) | firm, dated |
| E11 | Two-tier CI review | One engineer's blog | Free local model on every push, frontier model when the merge request opens; the no-thinking Qwen variant found real bugs, the reasoning variant talked itself out of them. [Post](https://snowgoons.ro/posts/2026-08-29-putting-a-local-llm-in-the-code-review-loop/) | exploratory (one author, not opened by me, search summary only) |
| E12 | Router research | RouteLLM | Over 85% cost cut on MT Bench, 45% on MMLU, 35% on GSM8K at about 95% of GPT-4 quality; a glossary source says coding assistants gain less. [LMSYS](https://lmsys.org/blog/2024-07-01-routellm/) | firm for chat tasks; not measured on coding agents |

### Counter-evidence that deliberation pays

- **C1.** One app, 90 runs, observational: raising effort from High to xHigh lifted first-try perfect runs from 28% to 89%
  at a 9 to 29% cost increase; the authors say to "match the fix to the failure", since most first-run failures were weak
  reasoning. [arXiv 2607.02436](https://arxiv.org/abs/2607.02436) (interim).
- **C2.** SlopCodeBench, October 2026, each setting run once: Opus 5.5 medium 28/196 strict passes at about $193, xhigh
  25/196 at about $817 (4.22x); GPT-6 Astra went 29 to 32 at 2.91x. The author says xhigh "was not a reliable way to buy
  more strict passes" and that noise could explain a three-checkpoint swing.
  [Write-up](https://www.developersdigest.tech/blog/slopcodebench-october-2026-effort-xhigh-medium-opus-5-5) (exploratory).
- **C3.** Amp and Codex-Spark both concede lower reliability on complex work (E6, E7).

### What nobody has shown (searched, not found)

- Independent, end-to-end, measured integration of fast models across SDLC **phases** (requirements, design, test
  authoring, review, release). Every working example is a tool-level or step-level integration: edit apply, search,
  autocomplete, difficulty routing, parallel workers.
- Production numbers for cheap-model cascades in review or test generation. The cascade and ladder projects found are
  blogs and personal configs.
- A coding-specific measurement of router savings.

## 3. ShipLoop facts (this checkout, main at 6ed81762, 0 behind origin/main)

- **Model-neutral by rule.** `skills/shiploop/SKILL.md` ("The skill and its navigator commands launch no Grok, Claude,
  Codex, or other model process"); the optional outer driver `scripts/shiploop-drive` starts and resumes host sessions.
- **One model and effort per run, chosen by the host.** `test/shiploop_e2e/hosts.py` `HOSTS`: Grok `grok-4.7` medium,
  Claude `claude-sonnet-5-5` with no effort flag, Codex `gpt-6-luna` xhigh. No stage carries an effort or model hint.
- **Agent cards inherit.** `agents/backchain.md`, `in-parallel.md`, `skill-interop.md` carry `model: inherit`.
  `skills/ask-agent/SKILL.md` forbids adding "model downgrades" unless the user or invoking skill asks.
- **Owner rule:** never Haiku, for anything (memory `experiments-use-sonnet`, 2026-09-24).
- **Script-owned decisions already do the Type 0 work.** Navigation, successors, lint, receipts, and since Step 6.4 of
  `docs/shiploop-efficiency-plan-2026-10-16.md` the Improve stop rule (trivial and satisfied, checks passed, content tree
  equal to the previous pass's tree) are decided by scripts, not by a model.

### Internal measurements relevant to Type 1 (all single-run, interim)

- **Uniform deliberation on mechanical steps (Luna max, battleship, 1.16.1).** Generating tokens was 99.5% of wall time at
  about 55 tokens/s; 2,276 short or message-only responses were 52.3% of output tokens, about 376 minutes (32.5% of wall
  time) of thinking before a short command. Input context was 3.3% of latency. Source: `docs/shiploop-fast-planning-plan-2026-10-04.md`
  ("Diagnosis"), `test/shiploop_e2e/LEARNINGS.md` ("Fast planning").
- **Same request on Sonnet 5.5.** Planned in 4.8 minutes and 83 turns; plan 0.8 KB against 32.1 KB; 24 Improve passes in
  5.6 minutes against 41 in 305 to 360; no Backchain loop started. Whole run 19 minutes against 19.3 hours.
  **Not established:** whether the loops or the larger plans bought quality ("No comparison exists ... the models
  differ", LEARNINGS). The Luna run ended blocked at system-test on two browser cases that need a person, so it is not a
  quality baseline either.
- **Luna xhigh with one-pass Backchain (v1210).** Planning window 375.9 minutes against 647.5 at max, about 42% less, n=1
  (memory `fast-planning-2026-10-04`).
- **Improve value.** Of 12 first-pass changes in the 1.18.0 and 1.19.0 hello runs, 9 fixed a real defect and passes 2
  and 3 changed nothing in any of the 12 (LEARNINGS, "Most first-pass findings were real"). In chess run 2, 21 Improve
  passes over five stages were 8 material and 10 no-change, and Improve was 49% of time and output.
- **Effort levels tried so far** were chosen for speed, not compared for quality: max to xhigh was a run-length fix.

## 4. Comparison

- ShipLoop already has the preconditions under which the outside evidence says fast steps work: narrow single-step
  packets, mechanical checks after each step, retry on refusal, state held by scripts. It differs from the outside
  examples in having no model tier at all.
- The outside wins come from three things ShipLoop cannot copy directly: specialised models with no API (Fast Apply,
  SWE-grep, Windsurf SWE-1.5), host-level auto routing (Gemini CLI), and product modes (Amp). The remaining portable idea
  is the effort or model choice per step.
- ShipLoop's own data show the cost of uniform deliberation (E9 pattern, 32.5% of Luna wall time) but not its benefit
  or absence of benefit, because no run varied effort at fixed model and case.

## 5. Recommendation (interim)

1. **Do not add a Type 1 model tier to ShipLoop.** The skill must stay model-neutral, the owner rules out Haiku, the
   specialised fast models are not available, and the Type 0 route (script-owned decisions) already beat a cheap-model
   guess on the clearest candidate (Improve confirmation passes).
2. **There is an effective use to test: lower effort on mechanical packets, not smaller models.** Candidates: callback,
   copy and file-write steps, test running, and Improve passes 2 and later. Not candidates: spec, test-strategy, plan, and
   the first Improve pass. **Narrowed 2026-10-24 (section 7):** callback, copy and write steps are calls inside
   deliberative stages, which a per-session effort cannot reach; the mechanical packets are the seven outer stages
   (12.7% of stage seconds on Claude), so the Improve arm is the larger one.
3. **Test it in the harness first, with no skill change.** One blocked pair on the same case and host: control at current
   defaults against a by-stage effort arm; the lever lives in `shiploop-drive` or the harness because stage boundaries are
   already session boundaries under the context-clear tenet. Decide by eval-decision-priority: material quality
   difference first (blind rubric-eval, SPEC clauses, seeded-defect catch), then tokens, then minutes. Escalation is
   script-owned: a refusal or a changed tree at a low-effort pass reruns at default effort.
4. **Only after a win** add a script-derived `effort_class` line to the packet as a record-only field.

Open: no measurement yet of Luna or Grok at fixed case with effort varied; C1 and C2 disagree, so the answer is
task-dependent and must be measured on ShipLoop's own stages.

## 6. Limits of this survey

Web results were search summaries for E6, E7, E11, E12; E1, E2, E3, E4, E5, E8, E9 (Overthinking), C1 and C2 were opened
and read. The Claude Code docs page was read to character 100,000 of 116,349. Vendor numbers are vendor numbers. The
Heise Terminal-Bench claim and Augment's "90% of Sonnet 4.5" were not verified.

## 7. Experiment plan written (2026-10-24, same day)

The owner asked for the by-stage effort experiment plan: one blocked pair, control against low effort on mechanical
packets and Improve passes 2 and later, judged by eval-decision-priority. Plan:
`docs/shiploop-effort-by-stage-experiment-plan-2026-10-24.md` (Execute: ask; nothing built or run).

Findings made while grounding it (status: measured from `baselines.jsonl` and the stage table, interim):

- **F7.1 No inner-loop stage is mechanical.** In `shiploop_stage_spec.py` every inner stage authors a plan, test, code or
  document, or reviews the diff; `validate-existing` is script-first and usually issues no packet.
- **F7.2 The mechanical stages are outer.** `prepare`, `system-test`, `product-acceptance`, `release-check`, `release`,
  `release-verify` and `operations` are 12.7% of stage seconds on Claude Sonnet 5.5 (28 full runs; 22 of them `hello`,
  `battleship`, `checkers`) and 16.8% on Grok 4.7 medium (1 run). That bounds the mechanical arm.
- **F7.3 The Luna "thinking before a short command" waste is per call.** It sits inside deliberative stages and is not
  reachable by a per-session effort; the plan excludes it.
- **F7.4 The `rubric-eval` rule needs eight scenarios** for a win (SPEC section 8); a harm can block with fewer. The plan
  therefore uses eight non-platform full-run cases, 16 runs, and offers a four-scenario start that can stop the idea but
  not approve it.
- **F7.5 `arms.py` decides on bytes ingested**, which an effort change does not move; the plan uses it for its hard
  gates only and decides with `rubric-eval analyze`.
- **F7.6 Claude baselines record `effort: null`**, so the default Claude effort is unknown; only explicit-level arms are
  comparable.

Superseded: recommendation 2 in section 5 as first worded (see the marked edit there).

## 8. R0 of the effort experiment done (2026-10-24, same day)

Plan: `docs/shiploop-effort-by-stage-experiment-plan-2026-10-24.md` section 9. Evidence:
`docs/experiments/shiploop-effort-by-stage-20261024/`. All statuses below are interim (single runs, small n).

- **F8.1 (firm, measured) Grok 4.7 accepts `low`, and a resumed session honours a changed effort.** Four runs per cell on two
  prompts: low used about 30% fewer reasoning and output tokens than medium on means (ranges overlap); resumed low was 0.63 to
  0.79 of resumed medium. `probes/summary.json`.
- **F8.2 (firm) Claude ignores an invalid `--effort` with a warning and runs at its default.** The harness now validates
  levels per host (`effort.check_levels`). Claude reports thinking tokens separately (`output_tokens_details.thinking_tokens`),
  noisy at low effort.
- **F8.3 (interim) Improve pass >= 2 has mass and events at stake on Grok.** 134 of 226 passes; 23 of the 100 with a recorded
  tree change did change it. Claude children mostly stop at one pass. `cost/c-improve-mass.json`.
- **F8.4 (interim) The `shiploop-run` judge suite is accepted:** Opus 5.5 medium, kappa 0.914, noise 1.67 points, 30 artifacts
  graded twice (first attempt 0.727 and 6.67 points, revised once to require exact record quotes). Improve reviews sit at the
  ceiling (all 100), so Q2 may not separate a weaker low-effort review. `judge/acceptance.json`, `references/judges.json`.
- **F8.5 (interim, corrects F7.2) The Grok mechanical share is 16.8%, 10.0% and 1.2% over three rows,** one of them complete.
- **F8.6 (interim) Grok per-run time is uncertain by about 3x** (5,599 s finished on 1.22.0; at least 14,229 s unfinished on
  2.6.0, 115.5M prompt tokens in 912 calls). The cost table is an estimate; six of the ten cases have no current Claude timing.
- **F8.7 (process) My harness edit broke an anchor line in the shared fake Grok** that the environment suite checks; found by the
  targeted suite run, fixed, rerun. 18 targeted suites, all exit 0 after the fix; `rubric-eval` 30 tests; `seeded_defects verify`.

Manifest: `manifest.json`, sha256 in `manifest.sha256` (value recorded below). Superseded: none.

Frozen manifest sha256: `2b4120c17fb092ba5d0e7f3424dffe245dae0ed54f86290134f7dc7c8bd52026` (2026-10-24, before any decision-round run; `freeze_manifest.py --check` compares).

## 9. Second search: how teams use fast or tiered models across the SDLC (2026-10-24, same day)

The owner asked for another search for how others use Type 1 models with the SDLC. Primary sources were opened for the rows
marked (P); the rest are search summaries (S). Statuses: firm = primary source read; interim = secondary or company-reported;
exploratory = a blog or one author.

| Phase | Who | What the fast or lighter tier does | Status |
| --- | --- | --- | --- |
| Review | Cloudflare (P) | Seven specialist reviewers per merge request: a top-tier model (Opus 4.7, GPT-5.4) only as coordinator; standard tier (Sonnet 4.6, GPT-5.3 Codex) for code quality, security, performance; Kimi K2.5 on Workers AI for documentation, release and AGENTS.md reviewers. 131,246 reviews in a month, median 3m39s, average $1.19 (trivial $0.20, lite $0.67, full $1.68). Quote: "we don't need to use a super expensive, highly capable model for every task." No quality comparison of tiers; false-positive rate not reported. https://blog.cloudflare.com/ai-code-review/ | firm for the design and numbers; interim for quality |
| Review | Uber uReview (P) | Four stages (generate, filter, validate, dedupe); best benchmarked setup was Claude-4-Sonnet generating with o4-mini-high as grader. No cheaper model mentioned; the grader is a reasoning model. 75% of comments useful; about 65% addressed. https://www.uber.com/blog/ureview/ | firm; counter-example |
| Review | Cursor Bugbot (S) | Parallel bug-finding passes with randomised diff order and majority vote, then rebuilt agentic; Cursor staff confirm findings sometimes surface across later passes | exploratory |
| Commit messages, history summaries | Aider (P) | `--weak-model`: "commit messages and chat history summarization" | firm |
| Edit, completion | GitHub Copilot (S) | Custom low-latency models for completions and next edit suggestions; "frontier models didn't meet quality and latency, smaller ones were fast but low quality", so a task-trained model; Sept 2026 single "3-in-1" inline model. Completions: +12% acceptance, 3x throughput, -35% latency (company-reported) | interim |
| Completion | JetBrains Mellum (S) | 4B completion model; latency to one third; about 40% acceptance (company-reported); 100M local models | interim |
| Commit messages | CommitLLM, 2026 (S) | Fine-tuned 7B with constrained decoding: 98% format compliance; earlier studies found GPT-3.5 best on quality | interim |
| Subagent work | Anthropic Haiku 5.5 (P) | "designed for high-volume, cost-sensitive tasks": summaries, compactions, classification; "pairs well with Opus 5.5 and Sonnet 5.5 as a subagent on coding work"; "Sonnet 5.5 and Opus 5.5 remain better choices for complex agentic coding tasks" (Terminal-Bench 4.0: Haiku 39.2%, Sonnet 70.6%). About 75% cheaper than Haiku 4.5; first Haiku with effort levels. https://www.anthropic.com/news/claude-haiku-5-5 | firm (vendor) |
| Plan then execute | Claude Code (P) | `opusplan`: Opus in plan mode, Sonnet in execution; skill and subagent frontmatter can set `effort`, overriding the session level while that skill or subagent is active; Sonnet 5.5, Opus 5.5 and Haiku 5.5 default to `medium` effort. https://code.claude.com/docs/en/model-config | firm |
| Routing, research | SWE-Router, June 2026 (P: abstract) | A cheap model runs a few exploratory turns, then a router reads the partial trajectory and keeps going cheaply or escalates; "greatly improves cost efficiency" keeping "the majority" of the strong model's performance; the abstract gives no numbers. https://arxiv.org/abs/2607.00053 | interim |
| Routing, research | Bouchard, cascades (P: abstract) | Two-model cascades beat single-model selection by 2.1 to 8.2 points; more than two models added nothing in 118 of 135 comparisons. Not coding-specific in the abstract. https://arxiv.org/abs/2605.06350 | firm as a paper |
| CI review, triage | dev.to posts (S) | Small local model as first pass, strong model only for risky diffs; "escalate on an external deterministic check, not model confidence"; self-reported numbers with no method | exploratory |
| Fast generation | Mercury Coder, diffusion (S) | Over 1,000 tokens/s on H100; second on Copilot Arena for the Mini; no workflow study | interim (vendor) |

**Not found.** A software-engineering paper applying dual-process (System 1 / System 2) to coding agents; a rigorous study of small
against frontier models on test generation, log triage or incident response; any measured quality comparison between the tiers in
Cloudflare's design.

**What changes.**
- F9.1 (firm) The best phase-level example is role-based tiering inside review, not a non-deliberative model: the strong model judges and merges,
  specialists run on a standard tier, and text-heavy chores (documentation, release notes) run on the lightest tier.
- F9.2 (firm) Lighter-tier candidates by that example are text-heavy stages, not run-and-report stages. ShipLoop's analogues are `document`,
  `carry-forward` and `handoff`, which the frozen experiment keeps in class D. A candidate for a second pair, not a change to the manifest.
- F9.3 (interim) Escalating on an objective check rather than on model confidence matches ShipLoop's script-owned gates; the escalation arm
  deferred from E-EFF1 has outside support.
- F9.4 (firm) Cursor's Bugbot and ShipLoop's own Grok data both show later review passes finding things; do not downgrade later passes on faith.
- F9.5 (firm) Claude's default effort for Sonnet 5.5 is `medium` per the current model-config page (resolves U8 for current builds; older
  baselines may differ). Skill frontmatter `effort` is a Claude-host way to set effort per skill with no session restart.
- F9.6 (owner decision) Haiku 5.5 (about 2026-10-07) postdates the 2026-09-24 "I don't trust Haiku" rule, which concerned Haiku 4.5. Whether the
  rule covers Haiku 5.5 is the owner's call; nothing was run on it.

## 10. R1 done: one `hello` pair on Grok 4.7, control and treatment, two at a time (2026-10-24, same day)

Runs: `/Users/dadleet/e2e-runs/effort-eeff1-r1/{control,treatment}-hello` (marketplace skill-craft 2.8.0 / ShipLoop 1.8.0, started
together, load 7.6 to 10 on 18 CPUs). Compact evidence: `docs/experiments/shiploop-effort-by-stage-20261024/r1/` (`report.json`,
`by-class.json`, each arm's `effort.json` and `sessions.jsonl`, `tokens-*.json`). Reader: `r1_report.py`. Statuses: interim, n=1 pair.

| | Control (medium everywhere) | Treatment (low on M and I2) |
| --- | --- | --- |
| Session seconds | 4,339.8 | 4,503.9 |
| Model calls | 363 | 374 |
| Prompt + output tokens | 47.64M (output 219.1k, reasoning 102.2k) | 47.87M (output 250.5k, reasoning 124.0k) |
| CLI-reported cost | $1.73 (lower bound) | $2.35 (lower bound) |
| Sessions (restarts / natural) | 13 (10 / 3) | 13 (8 / 5) |
| Improve | 9 children, 11 passes, 2 reached pass 2 | 10 children, 11 passes, 1 reached pass 2 (tree changed) |
| Verdicts | `committed` FAIL, rest PASS | all PASS |

- **F10.1 (firm) The schedule fires on real packets, both classes.** Every restart into I2 matched a child that really reached pass 2 (control 2 of 2,
  treatment 1 of 1); no spurious I2 restart, no missed pass 2. Restarts into and out of M fell at the same stages in both arms (prepare, system-test,
  release-check; then step-plan, release-plan, handoff). Treatment's sessions ran at `low` for exactly the M and I2 sessions. U7 is resolved on a live run.
- **F10.2 (interim) Low effort acted where it was applied, and the whole-run total cannot show it.** By class (`by-class.json`), M sessions: reasoning per
  call 151 at low against 252 at medium (-40%), output per call 495 against 610 (-19%), 41 calls against 55, 420 s against 751 s. Class D, medium in both
  arms, differed more: reasoning per call 354 against 285 (+24%), 3,989 s against 3,372 s. Run-to-run variance in the unchanged class is several times the
  M effect at n=1, so run totals alone cannot detect it; stage-matched measures would.
- **F10.3 (interim) The shares are bigger than the baseline-table 12.7%:** in control, M was 17.3% of session seconds and 15.3% of output tokens, I2 5.0% and
  5.3%, D 77.7% and 79.4%. Treatment's I2 sample is one pass of 7 calls (reasoning per call 337 against 315): no I2 effect can be read from it.
- **F10.4 (firm) The restart itself causes refusals, two per Improve pass-2 cycle.** The first session after D to I2 tried `improve-pass` before the pass's
  review existed ("Write this pass's review"), and the first after I2 to D re-ran it on a loop that had ended ("already ended"). 3 cycles, 3 pairs (control 4
  refusal lines-groups, treatment 2). A Grok run with no restarts (`2026-10-18/battleship-1`, 17 children) had none of the first and one of the second. The
  refusal count is a quality gate in the plan, and it scales with the number of cycles, which differs by arm.
- **F10.5 (interim) `committed` differed between two runs of one case.** Control returned its delivery to the working tree uncommitted (HEAD with 0 files, 7
  untracked product paths), treatment committed it (8 files in HEAD). LEARNINGS (the route follows untracked product files at return) records the pattern; the
  difference was not shown to be effort-related and may be run variance.
- **F10.6 (interim) Grok timing for the smallest case is 1.7x the plan's estimate:** 4,340 s and 4,504 s at two at a time, against 2,558 s. If the factor held for all
  eight scenarios, 16 runs would take about 15 h at two at a time (30 h serial); one case, so a signal and not an estimate.
- **F10.7 (firm) The import pipeline runs on real output:** `collect` found 6 artifacts in control (4 mechanical reports, 2 Improve reviews) and 5 in
  treatment; totals and `place` worked; no judge call was made, so the judged half of R1's exit is not exercised. Treatment lacked control's spec pass-2 review, so
  arm pairing drops it (limit already recorded).

**R1 verdict on the plan:** machinery works; three things need a decision before R2 as frozen: (a) attribute or avoid restart-induced refusals, (b) add
stage-matched per-class measures beside run totals, (c) restate the R2 time estimate. Nothing was changed in the frozen manifest.

## 11. Plan and manifest revised after R1 (2026-10-24, same day)

The owner asked for the plan and manifest to be revised for the three R1 findings and re-frozen; R2 not started. Plan section 10;
manifest revision 2 (`supersedes_sha256` 2b4120c1…). Statuses: interim.

- **F11.1 (avoid) The I2 class is held while the Improve loop closes,** so the I2 to D boundary falls after the model's `complete` call
  (`effort.running_pass`: a complete or stopped packet under a bound child is indeterminate). The session after a boundary is told
  nothing was undone (`effort.RESTART_NOTE`). Not tested live.
- **F11.2 (attribute) `run_totals.py refusals` sets apart the two `improve-pass` refusals a boundary caused** (R1: control 4 of 10,
  treatment 2 of 5) and the refusal gate excludes them in both arms.
- **F11.3 (measures) M-class and I2-class tokens and seconds per scenario are analysed beside the run totals,** which still decide.
  Expect the totals to be inconclusive at 8 scenarios (M is about 15% of tokens; the unchanged class moved +24% reasoning per call
  between two runs).
- **F11.4 (estimate) 16 Grok runs: 9.4 / 15.4 / 28.9 hours at two at a time (low / central / high),** from one measured case.
- Tests: `EffortScheduleTests` 14, `EffortMeasureTests` 4, `EffortSliceTests` 1 in `test/shiploop-e2e-slice.test.py`; `EffortScheduleThroughMainTest` 4.

Frozen manifest revision 2 sha256: `fb47d9d736d2bcb3ec50fc735b43324cfac1d9062c5f8c0141e86c6185a67962` (supersedes `2b4120c17fb092ba5d0e7f3424dffe245dae0ed54f86290134f7dc7c8bd52026`; before any decision-round run).

## 12. Python upgraded under the experiment (2026-10-24, 18:33)

The plan-sizing session reported that Homebrew replaced Python 3.14.7 with 3.14.9 and moved `python3` to 3.15.1 at 18:33; processes
started earlier failed on lazily imported stdlib modules (`_strptime`). Checked here: `python3` is 3.15.1 (`/opt/homebrew/opt/python@3.15/bin/python3.15`).
R1 ran on 3.14.7 (before the upgrade); the next runs (the second hello pair, then R2) will use 3.15.1 for the harness and for the
ShipLoop CLI the model types as `python3`. Both touched suites pass on 3.15.1 (`shiploop-e2e-slice` 77 tests, `shiploop-e2e` 433). The manifest
now records the interpreter (revision 3). The interpreter differs between R1 and the second pair, so their timings are not strictly
comparable; within a pair both arms share it.

Frozen manifest revision 3 sha256: `177a6a334f4f9b450e6049fd303ddf3fd2a891ec9a63d6771a46380fff754390` (supersedes revisions 1 and 2; before any decision-round run).

## 13. Second hello pair: control killed by a boundary before Grok had a session id (2026-10-24, evening)

Pair 2 started 19:51 on this checkout's 2.8.0 code (`--source checkout`; the marketplace had moved to 2.9.0 and its source is gated on
local HEAD == origin/main). Statuses: firm for the defect, interim for the rest.

- **F13.1 (firm) A boundary before Grok's first turn ended could not be continued.** Grok reports `sessionId` only in the `end` event of a
  turn. The control run's first boundary (D to I2 at spec, 8 minutes into the first turn) killed the host (rc -9) with no id, the resume loop
  found none ("no host session id to resume") and the run ended `active at spec`. R1 escaped by luck: its first boundary came after three
  natural turn ends. The run is kept as evidence in `effort-eeff1-r1b/control-hello-failed-no-session-id` (its effort record shows no
  restart, because the boundary was recorded only after the id check).
- **F13.2 (fix) `Planner` takes `can_resume`:** no session is ended until the host has an id to resume from; the boundary is then applied at
  the next natural turn end, when the next launch reads the class again (`run.py` and `slice.py` pass it; a fresh-session host needs none).
  Tests: a pure one (`EffortScheduleTests`, 15) and one through `run.main` with a fake Grok whose turn ends after the class changes.
  Effect on the design: a boundary in the first turn is applied late, in both arms; the restart count can differ from R1's.
- **F13.3 (correction to section 12) In Grok's isolated environment `python3` is `/usr/bin/python3`, Apple's Python 3.9.6, not Homebrew's 3.15.1.**
  ShipLoop's printed `done` command for the Until Loop named it. So the Homebrew upgrade affects the harness (3.15.1) but not the CLI the Grok
  model runs; R1 and pair 2 ran that CLI on 3.9.6.
- **F13.4 The manifest hash no longer matches** (run.py, slice.py, effort.py changed after revision 3); it is re-frozen when the pair ends, together with
  the plugin pin decision (the marketplace now serves 2.9.0; the manifest still says 2.8.0).
- Control was relaunched at 20:0x with the fixed harness in the same folder name; the treatment run continues on the old code (it already has a session id).

## 14. Second hello pair finished; session-id fix (2026-10-24, night)

Both pair-2 runs ended `done` (exit 0, every verdict PASS). Evidence: `docs/experiments/shiploop-effort-by-stage-20261024/r1b/`
(`report.json`, `refusals.jsonl`, `classes.jsonl`, each arm's `effort.json` and `sessions.jsonl`); the failed first control run is
kept at `effort-eeff1-r1b/control-hello-failed-no-session-id`. Statuses: interim (n=1 pair).

- **F14.1 (firm) The hold removes one restart refusal; the restart note does not remove the other.** Treatment, 9 restarts, 2 pass-2 cycles: "loop already ended" 0
  (R1 3 of 3), "write this pass's review" 2 of 2 (R1 3 of 3). Control, no restarts, 2 pass-2 cycles: 0 of that kind. Plan section 10.5.
- **F14.2 (firm) Choosing the Grok session id up front makes every session resumable.** `--session-id <uuid>` on the first launch, `--resume <uuid>`
  after a kill mid-turn: context restored (probe). Implemented in `run.py` and `slice.py` (`planned_session_id`); the `can_resume` guard
  of F13.2 stays for hosts without the flag. Tests: 15 pure, 5 through `run.main` including one where the class changes before the first turn ends.
- **F14.3 (firm) The F13.2 guard alone broke the blocked design:** control's first turn ran 9,665 event lines before any id, so no boundary fired until
  handoff (1 restart against 9). Lesson: a fix that waits for a condition can change what is measured.
- **F14.4 (interim) Totals again do not separate the arms** (seconds 3,986 against 4,063; reasoning 103.7k against 99.6k); class D moved -10% in
  reasoning per call here and +24% in R1.
- **F14.5 (interim) hello on Grok over four runs: 3,986 to 4,504 s,** mean 4,223 s (factor 1.65); 16 runs: 9.4 / 14.7 / 28.8 hours at two at a time.
- **F14.6 (open, owner) The plugin pin.** The marketplace serves skill-craft 2.9.0 / ShipLoop 1.9.0 (Improve route changes); the manifest named 2.8.0.

Frozen manifest revision 4 sha256: `815996c5b51f77b76520dc9ca402f7ef023f607dd0dafd151ec0cf576ffd379a` (supersedes revisions 1 to 3; before any decision-round run).

## 15. R2 build chosen: marketplace 2.9.0; what the sync takes (2026-10-25, after midnight)

The owner chose "run R2 on the marketplace 2.9.0 build", asked what synchronising the local checkout to origin/main takes without touching their
uncommitted work, and for the manifest to be updated and re-frozen; R2 not started. Plan section 10.6. Statuses: firm (read from code and
reproduced), interim where noted.

- **F15.1 (firm, correction) The marketplace gate does not require HEAD == origin/main.** `version_gate` refuses unpublished local commits, version mismatches,
  unreleased change notes on origin/main and a failed CI; "behind origin/main is fine" (`released_versions`). I told the owner on 2026-10-24 that the gate
  required a match, from an out-of-date comment in run.py's header; pair 2 could have run on the marketplace build. The reason to sync is different.
- **F15.2 (firm) The harness imports ShipLoop's modules from its own checkout,** so a 2.8.0 checkout would read 2.9.0 runs with 2.8.0 code; the Improve-pass
  detection depends on names that 2.9.0 left unchanged, so it was safe, but the check is the reason to pin the harness to the plugin under test.
- **F15.3 (firm) A fast-forward is refused on one file.** Upstream's 26 commits (then) touched 254 paths; one overlaps an uncommitted edit
  (`test/shiploop-e2e.test.py`). All seven edited files apply cleanly with `git apply --3way` on origin/main and on 31933a73. No untracked path overlaps.
- **F15.4 (firm, not by me) The canonical checkout was rebased onto origin/main by another session** (reflog: rebase start/finish at about 22:5x; autostash).
  Verified after: seven modified files and all untracked files intact, stash list empty, patch size unchanged. The E2E review session says it was not that
  session and will not touch the canonical checkout; 13 more harness commits (run.py, cases.json) are due on origin/main.
- **F15.5 (firm) The marketplace REFUSES today:** origin/main e707b794 has 3 unreleased change notes; CI success; the marketplace serves 2.9.0 / 1.9.0. A
  release moves the marketplace past 2.9.0, so a marketplace R2 means whatever it serves at launch, and a release mid-batch would split the arms across
  engines. Manifest guard: preflight must name 2.9.0 / 1.9.0 before every launch; fallback `--source checkout` from the pinned worktree (owner's OK).
- **F15.6 (firm) The pinned harness works:** worktree `.claude/worktrees/eeff1-r2-ac0ac8` at 31933a73, changes uncommitted, built by
  `sync/make_r2_harness.sh` from copies in `sync/`; effort tests 20 and 5, `shiploop-e2e-slice` 78, `shiploop-e2e` 442 pass; the same overlay on the origin/main
  tip also passes. The first throwaway worktree (at the tip) was removed.
- Grok window: the plan-sizing session's E6 R2 batch (32 slices, 4 lanes) started about 22:50 and runs 2.5 to 3 hours; it will message when it ends.

Frozen manifest revision 5 sha256: `23dabea9c5564c8dd20a75343b9ddcb6399a4ad04323c53ec00376988dd336d9` (supersedes revisions 1 to 4; before any decision-round run; harness: the pinned worktree).

## 16. R2 build decided: `--source checkout`, the 2.9.0 payload from the pinned worktree (2026-10-25)

The owner chose the checkout fallback; manifest revision 6; R2 not started. Plan section 10.7.

- **F16.1 (firm) `--plugin-dir` at the worktree's committed `plugins/skill-craft` is the 2.9.0 marketplace payload.** That directory is identical between
  31933a73 and origin/main (e707b794), and the harness itself describes the marketplace as "origin/main's plugins/skill-craft, byte for byte". Versions
  skill-craft 2.9.0 / ShipLoop 1.9.0; tree digest `86b138e1652e`.
- **F16.2 (firm) The default checkout build differs from that payload in exactly three paths,** all the experiment's rubric-eval overlay (`judges.json`,
  `rubric_eval.py`, the `shiploop-run` suite; digest `4dd13076c669`), so `--plugin-dir` is used to keep the plugin under test byte-identical to what
  was published. The ShipLoop side is the same in both. `sync/plugin-build-comparison.json`.
- **F16.3 The launch guard is now local and checkable:** harness worktree HEAD 31933a73, `freeze_manifest.py --check` clean (it now also compares the
  payload digest and the worktree HEAD), and each run's `versions.plugin_sha256` equal to the payload digest. No marketplace preflight is needed; a release
  on main no longer matters to R2.
- Still needed before R2: a Grok window (the plan-sizing E6 batch and another session's chess-salesforce run share the account) and the owner's go.

Frozen manifest revision 6 sha256: `abc0896c1000c12a3f07f1f9d644554bca1d68356e2b03799d29095c801615aa` (supersedes revisions 1 to 5; before any decision-round run; harness and plugin: the pinned worktree at 31933a73).

## 17. R2 started (2026-10-25, 11:35) and the canonical checkout flapping

- **R2 pair 1/8 (hello) launched 11:35:36** from the pinned worktree through `r2_queue.py` (guard OK, manifest abc0896c). Treatment and control run at the same
  time; both restart the Grok session at every class change (control at the same medium effort, so only the flag differs).
- **F17.1 (firm) Another session's stash/rebase/apply cycles on the canonical checkout removed the experiment folder from the working tree for a few seconds at a time,
  at least three times (about 12:00 to 12:03).** The runs themselves live outside the repo (`/Users/dadleet/e2e-runs/effort-eeff1/`) and run from the pinned worktree, so
  they were not touched; the exposed paths are the queue runner's own scripts, the schedule files passed on argv, and the baseline append at the end of a run.
  `freeze_manifest.py --check` failed once with "No such file" during a wipe; the folder returned byte-identical to the off-repo backup
  (`/Users/dadleet/e2e-runs/effort-eeff1-backup-20261025`).
- **Mitigations without a manifest change:** the queue's guard now retries up to four times, 20 s apart (`R2_GUARD_TRIES`, `R2_GUARD_WAIT`), so a wipe window is not read as a
  failed guard; the off-repo backup restores any file. A relocation of the runtime state out of the repo would be revision 7 and is not done.
- Stashes `stash@{0}` and `stash@{1}` in the canonical repo belong to the other session; they were not touched.

## 18. R2 pair 1 (hello) finished (2026-10-25, 13:13)

Evidence: `/Users/dadleet/e2e-runs/effort-eeff1/{treatment,control}-hello/result.json`, `docs/experiments/shiploop-effort-by-stage-20261024/r2-queue-events.log`.

| arm | outcome | seconds | restarts | tokens (prompt + output) |
|---|---|---|---|---|
| treatment-hello | PASS, committed | 4,030.8 | 11 | 41,659,602 |
| control-hello | FAILED (committed verdict) | 5,836.8 | 14 | 65,540,870 |

- **F18.1 (interim, n = 1 pair) control-hello ended `engine=done` with both content checks passing (hello.py prints the line; `unittest` OK) but the delivery was not committed:**
  `.gitignore`, `docs/shiploop/{architecture,environment,spec}.md`, `hello.py` and `test_hello.py` were left uncommitted and HEAD held no files, so the run's own verdict is FAILED.
- **F18.2 (exploratory) The same `committed` failure hit control-hello in R1 (7 uncommitted files); R1b control passed; treatment passed all three hello runs.** Control: 1 of 3 valid hello runs delivered a
  commit; treatment: 3 of 3. The failure is in the arm that did not change effort, so low effort did not cause it; the cause is not yet known (candidate: how a restart at a class boundary interacts with the commit step).
  To check at analysis: the engine ledger for control-hello around the stage that should commit (`release`/`operations` sessions) and each session's reason in `sessions.jsonl`.
- The totals above are run totals; per-class measures and refusal attribution come from the analysis after all 16 runs. The judge scores quality first (eval-decision-priority); the cost gap of this pair is not a result.

## 19. Redirect: the full-run test cannot see the lever; slice test drafted (2026-10-25, afternoon)

Owner asked what the big picture is and whether the test was the right one; owner approved the redirect ("go with this").

- **F19.1 (firm, n = 1 pair) Mechanical stages (M) plus Improve pass >= 2 (I2) are 22% of run seconds in both hello arms and 24 to 26% of tokens;** class D (all else, same medium effort in both arms) is the other 78% and differed by 31% in seconds
  (3,132 s against 4,536 s) and in model calls (258 against 391) between the arms. The pair-1 total gap (31% fewer seconds, 36% fewer tokens for treatment) is therefore mostly noise in the part the lever does not touch;
  the part it touches differs by 402 s of 5,837 s (7%), with 3 against 5 I2 sessions. Source: `run_totals.py classes` on the two result folders. The pair-1 table in section 18 stands as a run total only.
- **F19.2 (firm) Output plus reasoning tokens are about 0.5% of all tokens in both runs (204,921 of 41.66 M; 313,585 of 65.54 M);** the rest is context re-read per model call, so effort cannot move the token total much; call count can.
- **F19.3 (correction) My statement on 2026-10-25 that I should have warned about the low ceiling "before launching R2" was partly wrong:** the plan, section 0, already gave the ceiling (mechanical stages 12.7% of stage seconds on Claude; Improve pass >= 2 the larger arm).
  What I did not carry into the chat was the run-to-run noise, which pair 1 first measured.
- **F19.4 (firm) A Grok 4.7 medium slice is far shorter than a full run:** 80 slices of the plan-sizing batch took 442 to 2,132 s (median per case set 610 to 1,267 s), and 55 of 80 had an Improve child that reached pass 2 or later.
- **Decision:** let R2 pair 2 finish; start no pair 3 (the queue runs one pair per invocation and was not restarted); hand Grok to the E2E session after pair 2; draft E-EFF2,
  `docs/shiploop-effort-slice-experiment-plan-2026-10-25.md` (rung S0: seven control slices to measure the I2 share; rung S1: the blocked pair, only on the owner's go). Nothing launched.

## 20. R2 pair 2 (seat-reservations) finished (2026-10-25, 15:51)

Evidence: `/Users/dadleet/e2e-runs/effort-eeff1/{treatment,control}-seat-reservations/result.json`, `run_totals.py classes`, `docs/experiments/shiploop-effort-by-stage-20261024/r2-queue-events.log`. No pair 3 was started.

| arm | outcome | seconds | restarts | tokens |
|---|---|---|---|---|
| treatment-seat-reservations | FAILED (`unit`: `test_R_1B_stdlib`), committed | 8,536.4 | 17 | 71,574,646 |
| control-seat-reservations | FAILED (`unit`: `test_stdlib`), committed | 9,214.9 | 18 | 75,925,838 |

| class | treatment seconds (share) | control seconds (share) | treatment tokens | control tokens |
|---|---|---|---|---|
| D | 7,262.6 (85.1%), 444 calls | 5,800.5 (62.9%), 351 calls | 54.71 M | 49.04 M |
| I2 | 739.8 (8.7%), 58 calls, 6 sessions | 2,809.4 (30.5%), 164 calls, 9 sessions | 9.07 M | 18.11 M |
| M | 534.0 (6.3%) | 604.9 (6.6%) | 7.80 M | 8.78 M |

- **F20.1 (firm, n = 1 pair) On a real app the Improve pass >= 2 arm is large: 30.5% of control's seconds and 23.9% of its tokens (hello: about 10% of seconds).** With M (6.6%) the lever's ceiling in control is 37% of seconds, 35% of tokens. This is the ceiling measurement that rung S0 of E-EFF2 was meant to give; it supports running E-EFF2.
- **F20.2 (interim) The I2 class fell by 2,070 s (74%) in treatment, but class D rose by 1,462 s (+25%, 444 against 351 calls) so the total moved only 678 s (-7.4%; tokens -5.7%).** D has the same setting in both arms, so this is run-to-run variation or an effect of the I2 change on later work; one pair cannot tell which (the same open question as F19.1, now with the sign reversed against treatment). I2 sessions also differ (6 against 9), so the arms did not do the same number of Improve passes.
- **F20.3 (exploratory) Both arms failed the same `unit` check on this case, on a stdlib-requirement test; contract, restart and concurrency checks passed in both.** Quality did not separate the arms on the script verdicts; the case itself is hard for Grok 4.7 medium.
- Run totals are not a decision; the judge needs all 8 scenarios (2 exist).

## 21. S0 held (2026-10-25, 16:07)

- S0 was approved by the owner in this session ("Approve S0 … once pair 2 has ended and the E2E session has had its Grok window"). The E2E session released its window at about 16:05 (its trio stopped on a CI failure) and told me to go ahead; `s0_queue.py` started 16:03:19.
- The first queue process died with exit 144 before launching a slice. I restarted it at 16:06:47. The E2E session then reported that, relaying "Stop the type 1 models" from the owner, it had ended my S0 runner's process group and asked me not to relaunch S0 or any Grok slice until the owner says so.
- **I have no message from the owner in this session saying to stop**, so the claim is unverified here. I stopped my restarted runner (nothing had launched; `/Users/dadleet/e2e-runs/effort-eeff2` is empty) and its watch, and asked the owner to confirm. E-EFF2 plan, runner and R2 data are kept as they are. Nothing is deleted.
