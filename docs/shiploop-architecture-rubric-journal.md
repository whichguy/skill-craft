# ShipLoop architecture rubric: experiment journal

A living record of every round, every change to the evaluation harness and its test cases, and every finding,
each with the evidence behind it. Edit entries when later evidence changes them: mark the old claim
**superseded** with the date and the reason, and keep the old text beside it. Do not delete it.

- Method and rules: [skills/rubric-eval/SPEC.md](../skills/rubric-eval/SPEC.md)
- Narrative results: [shiploop-architecture-rubric-results-2026-09-26.md](shiploop-architecture-rubric-results-2026-09-26.md)
- Evidence bundles: `docs/experiments/shiploop-architecture-rubric/round<N>/`, written by `rubric-eval export`. Each
  holds:
  - `manifest.json`: suite, frame, arms with source and hash, and the run condition (model spec, tools, workspace);
  - every `analysis*.json`;
  - `verdicts.jsonl.gz`: every grading pass, with grades, quotes, overbuilt items and platform errors;
  - `audits.jsonl.gz`: the value and diff audits;
  - `usage.json`: tokens and seconds per output;
  - for decision rounds, `outputs.jsonl.gz`.

## How to read the evidence

- A plan's score is the percentage of available rubric points it earns: met 2, partial 1, missed or overbuilt 0.
  "+3.8" means 3.8 points out of 100 against the named baseline.
- Arm comparisons are paired by scenario:
  - a 95% bootstrap interval that resamples whole scenarios;
  - the Wilcoxon signed-rank test over scenario means;
  - scenarios won and lost.
- **Decision rule** (SPEC section 8): a material quality difference decides first. Only near-identical quality moves
  on to tokens, then time. A difference is material only when the interval and the Wilcoxon test agree in
  direction.
- **Model specs** are `host:model@effort`. The aliases are:
  - `grok` = grok:grok-4.7@medium
  - `opus` = claude:claude-opus-5-5@medium
  - `sonnet` = claude:sonnet
  - `luna` = codex:gpt-5.6-luna@xhigh

## Round ledger

| Round | Question | Suite / frame | Arms (words, sha) | Subject | Judge (passes) | Tools / workspace | Cells | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1–3 | Interaction-design wording (plan pass); round 3 adds review-pass detail safeguards | architecture (31 criteria) / plan, review | see the results doc | Sonnet | Sonnet (1; judge v1, then v2 from round 3) | none | 19 scenarios | `round2/`, `round3/` |
| 4 | Review-pass wording | architecture / review-bare | current, design v2, prune3 (353); baseline: unreviewed round-2 v5 plans (input) | Sonnet | Sonnet (1); re-graded by Opus (1); quote check applied | Read, empty folder | 19 scenarios, 104 plans per arm | `round4/` |
| 5 | Design-thinking steps on the plan pass (expand, prune, outcome, negative intents) | architecture-v2 (+ threat T1, load L1, integration X1) / plan | base, expand, expprune, outcome, negative | Sonnet | Sonnet (1) | none | 13 cells × 3 trials | `round5/` |
| 6 | Review wording with reference files open | architecture-v3 (36 criteria, + grounding G1, unknowns Q1) / review-ref | prune3 (353, e3563f01), v3 (422, b72bade3), ground (409, c80578a2); baseline: unreviewed Grok plans (input) | **grok:grok-4.7@medium** | Opus: 1 pass (v3 rubric), 1 pass (v4 rubric), **3 fresh passes (v4 rubric, clean setup)** | Grok read_file, list_dir, grep; all 33 ShipLoop references; audited | 23 scenarios (first runtime), 16–17 per arm (Grok credits ran out at 49 of 69) | `round6/plans/`, `round6/reviews/` |
| 7 | Review wording **inside the real plan-stage packet** | architecture-v4 / review-packet (made from ShipLoop source a99ba114577c) | current (200, d9bc1f86), v4 (451, aeeccca3), v4card (469, fa1ff003); baseline: the same unreviewed Grok plans | **codex:gpt-5.6-luna@xhigh** | Opus, 3 passes | Codex read-only shell; all references as the packet points; audited | 23 scenarios | `round7/` (in progress) |

The round-6 base plans were written by grok:grok-4.7@medium with the shipped v5 INTERACTION_DESIGN (467 words, dd2c8013),
using the plan frame from suite v3 with its written-exercise line. That was 56 cells; 23 were used as inputs.

## Test cases and suites

| Change | When / commit | What | Why | Effect on results |
| --- | --- | --- | --- | --- |
| architecture | rounds 1–4 | 31 criteria, 19 scenarios, 7 runtimes; frames plan, review, review-bare | Baseline suite | none |
| architecture-v2 | round 5 | Adds threat T1, load L1, integration X1; cross-runtime scenarios S20–S23; runtimes SF+GAS, CF+SF | Test interaction and threat modelling | Round 5 only |
| architecture-v3 | 6ffdbe8c | Adds grounding G1 and unknowns Q1 to every scenario (36 criteria); plan and review frames get a written-exercise line | Measure grounding; stop Grok hunting for a packet that was not there | Round 6 |
| v3 frames review-ref, plan-ref | e83a232f, then 72732860 | The reviewer reads references in its own folder; later narrowed to the platform cards | Realistic reviews; then cost | review-ref (all references) used in round 6 |
| architecture-v4 | abb0d238 | P3 scope and the overbuilt anchor no longer penalise an addition that makes a stated requirement work or that correctness, security, data integrity or failure visibility demand; scenario overbuild notes unchanged | The value audit found 13 of 16 round-4 overbuilt flags were such additions | Round 6 re-graded; round 7 |
| v4 runtime_cards and `{card}` | bb08a81f | Each runtime maps to its platform card | The v4card arm | Round 7 |
| v4 review-packet frame | bb08a81f | Generated by `make_packet_frame.py` from the plan-stage Improve packet: 29 reference locators, the arm, the plan-stage Improve prompt verbatim (1,758 words), and a line saying run mechanics do not apply | Test the wording as ShipLoop runs it | Round 7 |

## Harness change log (`skills/rubric-eval`, `skills/adversarial-review`)

Each entry: commit, then what changed, why, and its effect on earlier results.

**Skills and judge rules**
- **d8c159e9:** rubric-eval and adversarial-review created, with SPEC, suites and CLI. They turn the ad-hoc scripts into composable skills.
- **1792957a:** every verdict records `judge_model`, and `analyze` refuses mixed judges. A changed default had let a Grok judge grade a Sonnet round; 41 verdicts were deleted and re-graded.
- **00646bb5:** `diffcheck` skips input arms. It had compared the unreviewed plan with itself.

**Scoring and decision rule**
- **de621ab0, 7ff46b2c:** a standard scale (percentage of rubric points), Wilcoxon agreement, equivalence bounded by the judge's measured noise, and quality before tokens before time. It replaces hand-picked margins, per your direction. Round 4's decisions were unchanged.
- **7af1c809, c7f78d95:**
  - A quote check lowers grades whose quote is not in the plan.
  - The Grok adversarial review of the scoring led to these fixes:
    - near-identical quality is checked first;
    - wins need both tests;
    - rates are compared paired;
    - missing usage is recorded as unknown.
  - The first quote matcher cut prune3's round-4 lead to +2.7. That was a punctuation artifact, and it is back to +4.1.
- **abb0d238:** suite v4 correction, a value-audit proportionality clause, and a block on removing valuable items against a reviewed baseline. Round 6 was re-graded.
- **c46c1ba9, de086bca:** grading in 3 passes, with noise measured on the round's own outputs. One re-grade of round 6 moved a plan's score by 4.1 points on average and erased the +5.8 v3 effect.

**Isolation and tool access**
- **6ffdbe8c:** Grok calls name a tool allowlist. `--tools ""` had given Grok every tool, including the shell. No decision result had used Grok before.
- **e83a232f, a50c5cac:** workspace runs with read-only tools and a per-call read audit from the Grok session log. Grok's kernel sandbox cannot start here: `/var/run/docker.sock` is a symlink.
- **9e933451:** Claude calls use `--setting-sources ""`, and Codex calls get a minimal environment. Luna's Phase-0 review F2 showed your global CLAUDE.md loading into every Claude call. All Opus grades before this include it; it was the same for every arm.
- **082d7b12:** Codex runs with an isolated `CODEX_HOME` and an empty `HOME`. A Luna pilot read one of your personal skills (`~/.codex/skills/…`): `--ignore-user-config` still loaded your AGENTS.md and `~/.agents/skills`. The audit discarded that review.
- **a9ec2861:** `model_call.py` puts every host (Grok, Claude, Codex) behind one interface and one record, with pinned specs. Adversarial review now defaults to luna.

**Turn and timeout limits**
- **daa27bb1:** read-mode Grok calls get 40 turns. At 12, reviews ran out of turns before writing.
- **973e7784:** tool-mode calls get 1,800 seconds. At 600, reviews were cut off and retried.

**Tooling for arms and evidence**
- **ab660526:** `build --input-arm` writes the unreviewed baseline, which had been made by hand in round 4.
- **a7b883cc, e0c54fba:** the value audit weighs every added and removed item, following your direction to question value.
- **arm_arg:** arms can join source constants the way the navigator does (`FILE::A+B`), so an arm is the exact text ShipLoop would send.
- **this entry:** `export` writes evidence bundles.

## ShipLoop change under test

- **e45ef761** (branch): `DESIGN_REVIEW_CHECKS` is attached to the plan and step-plan reviews only (v2 wording).
- **abb0d238, 72732860:** it becomes the v4 candidate. That is v3's checks with deduplicated wording, plus: "removing is a change too; never remove or weaken a safeguard unless it contradicts the request or spec; an unsourced number stays, marked as an assumption". Change note: `changes/shiploop/design-review-checks.md`. Unreleased, awaiting round 7.

## Findings register

Status: **firm** (decision-grade evidence), **interim**, **exploratory** (Sonnet rounds), or **superseded**.

**Firm**
- **F1: the grounding self-check makes a review help.**
  - v3 against the unreviewed plan: **+3.8** [+0.4, +7.1], p = 0.044, 12 won / 4 lost; safeguards +4.4; grounding +17.7; proportion +0.7.
  - Evidence: `round6/reviews/analysis_judge_p1+judge_p2+judge_p3_scenario.json` (grok@medium subject, 3 Opus passes).
  - The earlier +5.8 from a single pass (`analysis_scenario.json`) was **superseded**: grading noise.
- **F2: v3's closing paragraph is what drives the gain.**
  - v3 against prune3 on the same plans: +7.1 [+4.5, +9.5], p = 0.002, 15 won / 1 lost.
  - Evidence: the same bundle, analysed against prune3.
- **F3: without a self-check, a lean checklist hurts once reviewers read references.**
  - prune3 against the unreviewed plan: −3.3 [−7.4, +0.1], and it fails the proportion guardrail (round 6, 3 passes).
  - In round 4 (no files to read) it had won, +4.1 under Opus (`round4/analysis_judge_opus_a_qc_scenario.json`).
- **F4: reviews that read platform cards cut factual errors about the runtime.**
  - Platform errors in unreviewed plans: 17 (single pass) and 13 (v4 re-grade).
  - Reviewed: 5–7 and 2–7.
  - Evidence: `round6/reviews/analysis_scenario.json` and `analysis_judge_v4_scenario.json`, field `platform_errors`.
- **F5: every review arm removes about 2 valuable items per review.**
  - prune3 2.50, ground 2.41, v3 2.06. The losses include:
    - rate limits (S05, S10, S11);
    - an access check (S09);
    - a 24-month retention guarantee (S17);
    - failure routes (S06, S12).
  - Evidence: `round6/reviews/audits.jsonl.gz` (audit `value`, verdict `loss`).
  - The value audit is 89% consistent on re-audit (`round4/value_b_summary.json`).
- **F6: in round 4 the rubric over-penalised gap-fixing additions.**
  - 13 of 16 judge overbuilt flags matched additions the audit rated valuable.
  - Evidence: `round4/value_summary.json`, `judge_overbuilt_but_valuable`.
  - Some were proportionality calls: S01's anti-cheat server for a single-player game is still overbuilt.

**Cost and measurement**
- **F7: a review costs 10 to 50 times the plan that it reviews, mostly by re-reading references.**
  - Grok reviews: about 220k tokens. Luna@xhigh in-context pilot: 0.57M–1.17M. A Grok plan: about 23k.
  - Round-6 reviewers read on average 11.4 files per review, mostly general guides: behavioral-requirements (4,875 words), improve-context and execution-planning.
  - Evidence: `round6/reviews/usage.json`, `round6/plans/usage.json`, and the Grok session logs (read counts recorded in this journal, 2026-09-27).
- **F8: real plan-stage packets point reviewers at the general guides and never at a platform card.**
  - Evidence: `suites/architecture-v4/frames/review-packet.txt`: its 29 locators include no card.
- **F9: effort drives cost more than the model.**
  - The same review: luna@xhigh 690k tokens and 12.4 min; luna@medium 88k and 2.0 min; sol@low 71k and 2.4 min (a 3,101-word plan).
  - A single sample; per-token prices are not known here.
- **F10: grading noise depends on output length.**
  - Opus test-retest was 2.07 points on round-4 outputs (`references/judges.json`) and 2.71 per pass on round 6's long reviews (3-pass analysis, `measured_pass_noise_points`).
  - Opus against Sonnet: kappa 0.443.
- **F11: every host leaked something into "isolated" calls until fixed.**
  - Grok had all its tools, Claude loaded CLAUDE.md, and Codex loaded AGENTS.md and personal skills.
  - Commits: 6ffdbe8c, 9e933451, 082d7b12.
  - Evidence: the isolation logs in `round6/reviews/isolation.log` and the round-7 pilot.

**Exploratory (Sonnet rounds)**
- **E1:** wording moves big decisions, not details (rounds 1–3).
- **E2:** threat and interaction modelling raised threat (+0.24 to +0.35 on the old scale) and load scores, but cost safeguards (negative-intents arm −0.096, 4 won / 15 lost).
  - Evidence: `round5/analysis_scenario.json`.

**Superseded**
- **S1:** "prune3 leads by only +2.7 under the quote check."
  - A matching artifact; with full normalisation it is +4.1 (c7f78d95).
- **S2:** "v3 +5.8 against the unreviewed plan."
  - A single grading pass; the 3-pass result is +3.8 (F1).
- **S3:** the round-3 "61/15" figure I stated.
  - The committed data support 60/15 [+0.018, +0.047]; the results doc keeps 60/15.

## Open questions (round 7 and after)

- **Q1:** Do the narrow checks (v4) still add value inside the real packet's global guidance?
- **Q2:** Does naming the runtime's platform card (v4card) improve plans or reduce tokens?
- **Q3:** Does v4 beat what ShipLoop ships today, without removing more valuable items? The valuable-removal block applies against `current`.
- **Q4 (round 8):** plans produced by the real plan-stage producer packet.
- **Q5:** whether xhigh effort buys review quality over medium (effort-only arms).
