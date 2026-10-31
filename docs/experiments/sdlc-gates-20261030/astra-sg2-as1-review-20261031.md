# Astra review of "SG2-K1..K4 and AS1 at 8 samples per arm instead of 4", 2026-10-31

Asked by the owner ("Ask Astra about whether this plan is valuable") through the `ask` skill: `ask.sh astra ask --json --effort max --cwd <repo>`. Served model `gpt-6-astra`, persona `codex-astra`, effort `max`, no fallback. The brief below is exactly what it was sent, with no verdict of mine in it; the answer is its `text`, unedited. Astra ran no live slices. I checked what it cited before relying on it (see "Pooled reading" in README.md): its power figures (85% at 16 per arm, 84% at 24 per arm for 20% to 60%, 3% for four independent wins at 42%, 85% for the blocked test) all reproduce, as do its readings of `sg2_recall.py`, `experiment.judge`'s `contradicts` branch and the AS1 guide's shared-folder limitation. I did not check its two outside references (NIST on randomized block designs; Johari et al. on always-valid inference).

## The brief

I need an honest judgement on whether a proposed plan is worth doing. Please judge it on its merits, argue against it where you can, and say what you would do instead. Your working directory is the repository (skill-craft); you may read it to check a claim, but everything you need is below.

## The plan under review

Run five declared-but-not-yet-run A/B experiments (SG2-K1..K4 and AS1) at **8 samples per arm instead of 4**. Each sample is a full model-driven stage slice, run on a Codex GPT-6.1 "Terra" host at xhigh effort, so a sample costs real model time and money.

## Background

ShipLoop is a delivery harness for coding agents: scripts own the workflow stages and the model does one step at a time. Its E2E harness runs controlled A/B experiments. Each experiment compares arm A (control) with arm B on a binary or numeric metric, with a fixed number of samples per arm, and a script (`decide`) reads the result as `supports`, `contradicts` or `inconclusive`.

**The decision rule changed on 2026-10-31.** It used to call a gain real if it exceeded the "A/A spread" (the difference between two control samples against two others). It now uses an exact one-sided permutation test, supports when p < 0.05. Re-reading the earlier results under the new rule reversed two earlier "supports" verdicts to "inconclusive" (p 0.071 and p 0.50). The five experiments above were declared before the change, are binary, and are set to 4 samples per arm.

**What 4 samples per arm can detect (computed with the real test).** With 4 binary samples per arm, the only split that reaches p < 0.05 is B = 4 successes against A = 0. With 8 per arm: A=0 needs B>=4, A=1 needs B>=6, A=2 needs B>=7, A=3 or 4 needs B=8. Probability the rule returns `supports`, if the true per-sample success rates are:

| true A | true B | power at 4 per arm | power at 8 per arm |
|---|---|---|---|
| 0.00 | 1.00 | 1.00 | 1.00 |
| 0.25 | 1.00 | 0.32 | 0.97 |
| 0.25 | 0.75 | 0.10 | 0.42 |
| 0.50 | 1.00 | 0.06 | 0.64 |
| 0.10 | 0.70 | 0.16 | 0.66 |
| 0.20 | 0.60 | 0.05 | 0.28 |
| 0.50 | 0.90 | 0.04 | 0.33 |

## The experiments

**SG2-K1..K4 (four cases, one experiment each).** Question: does a step review run in a fresh context (arm B, `delegation: ask-agent`, a fresh worker) remove a *seeded* defect from the final tree more often than the inline review that shares the producer's context (arm A)? Both arms use the same build (a 1.23.2 release commit); they differ only in delegation. Each case has a planted defect that the case's own checks miss, so the review is the last line of defence. Metric: 1 if the defect is absent from the final tree. Four cases means four separate experiments, each decided on its own samples: 4 cases x 2 arms x 4 samples = 32 slices today, 64 at 8 per arm. If B wins (supports and minutes per sample not above 1.5x control), the follow-up decision is to make the fresh review the default for step reviews. That would reverse a 2026-09-24 decision that dropped fresh reviews as the default because they cost 7 to 17 minutes and 40 to 100 tool calls per run.

Caveats the docs already record: delegation also moves the `implement` stage to a fresh worker, so the comparison is "everything in one context" against "fresh workers", not the review alone. A fix-commit count is recorded beside the metric so a review's catch can be told from a defect never written. The skill has since moved on two releases, and both arms stay on the older build, so a result says nothing about the current build. A seeded slice gives the inline reviewer the stage's records rather than a long producer conversation, so it likely understates the self-review problem and understates inline's disadvantage. Outside research the plan cites says LLM self-review is lenient, but it was measured on agents without ShipLoop's guards.

**AS1 (one experiment).** Question: does a new section in the Apps Script reference card (arm B, a later build) make the `test-strategy` stage record a deployment as a target that keeps state, more often than the build without it (arm A)? The case is an Apps Script project whose code runs from a deployment, and nothing in it says the deployment keeps state. Metric: 1 if the accepted test-strategy result has a targets row for the deployment with keeps_state yes. 2 arms x 4 samples = 8 slices today, 16 at 8 per arm. It is a short slice that stops after `test-strategy`.

## Total cost

Today 40 slices (32 + 8); with the plan 80 slices. Per-slice minutes are not yet measured for this build: a 2-case smoke is planned first to measure them. The Ollama route is at its monthly limit, so the Codex Terra host is the one available.

## What I want from you

1. **Verdict:** is running these five at 8 per arm valuable, marginal or not worth it? Give the one or two reasons that drive your verdict.
2. **Argue against it:** the strongest case that this is wasted effort, and the strongest case that even 8 per arm is still too few.
3. **Alternatives:** if you would do something different (pool the four SG2 cases as blocks, sequential stopping, a different sample count, running a smoke first and deciding from measured cost, dropping AS1 or SG2, or anything else), say exactly what and why.
4. **Before spending:** what, if anything, should be checked or measured first so the money is not wasted.
5. **Unknowns:** what you could not judge from this brief.

Be direct and concise. Do not hedge to be agreeable.

## The answer

**Verdict: marginal as proposed. I would not run all 80 slices as declared.** Eight per arm substantially improves detection—I verified your thresholds against the actual permutation function—but SG2’s treatment does not isolate the change you want to adopt. More replication makes that mismatch more precisely measured. AS1 is cleaner and shorter, but its value depends on whether the result would change an actual decision.

1. **The strongest arguments against it**

   **Wasted effort:** SG2 could produce a significant improvement because fresh *implementation* prevents the defect, without showing that fresh *review* helps. The final-tree score and accompanying fix-commit count do not establish which review removed the particular defect; that needs before/after defect evidence. Historical-build results remain informative, but cannot alone justify a current-build default change. [SG2 scorer — final-tree outcome and commit count](/Users/dadleet/src/skill-craft/test/shiploop_e2e/evaluators/sg2_recall.py:22)

   **Still too few:** Even a large improvement from 25% to 75% has only 42% power at eight per arm. My exact enumeration gives about **85% at 16 per arm**; a 20%→60% improvement needs **24 per arm for about 84%**. These assume independent samples and no multiplicity adjustment. Eight is a useful screening budget, not a generally adequate confirmation budget.

   Repeating four artificial defects also does little to establish performance across real defects. Statistical precision and representative coverage are different problems.

2. **What I would do instead**

   **First, run the cost and validity smoke.** Exercise both arms on two SG2 cases, measuring total elapsed time and tokens—including workers, retries and failures—and review time separately. Treat this as a feasibility check, not an efficacy verdict.

   **Then make SG2 one experiment with four case blocks.** Predeclare the primary statistic as the equally weighted mean of the four case-specific catch-rate differences. Use an exact permutation test that exchanges arm labels **within each case**, and retain each case’s results as diagnostics. Blocking accounts for known differences between cases. [NIST — randomized block designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm)

   Start with **four independent samples per arm per case: 32 slices total**. For illustration, if every case truly has A=25% and B=75%, I calculate approximately **85% power** for that blocked test, versus 42% for each separate eight-per-arm test. Those answer different questions: the blocked result concerns the average across these four cases, not improvement on every case or on unseen defects.

   Before that run, make the treatment match the decision: keep implementation identical between routes and vary review context alone, on the intended production build. Establish defect presence before assigning the review route, and preserve producer context for inline review. If using matched snapshots, use an analysis respecting those pairs. Record this as a superseding declaration. **If that isolation is impractical, label the existing experiment a combined delegation comparison and do not use it alone to change the review default.**

   **AS1: defer unless an outcome would trigger a specific action.** The repository records that its text already shipped, and arm B omits later corrections. If the decision is whether to retain or revise today’s text, test today’s text against its removal. Eight per arm is defensible for that cheap, narrow test after the smoke; it provides no evidence that deployment testing actually works. [AS1 guide — arm versions and release decision](/Users/dadleet/src/skill-craft/docs/experiments/apps-script-deployed-target-20261031/README.md:29)

3. **Use stopping rules carefully**

   Predeclare a maximum sample count and allow stopping for excessive cost or futility. A simple valid futility rule is to stop when **no possible completion of the remaining samples could support the candidate**; report no promotion, without claiming equivalence.

   Do not test at four, continue unsuccessful comparisons to eight, and apply ordinary p<0.05 at both looks. Early efficacy decisions require a sequentially valid procedure. For this small campaign, fixed sample counts plus futility stopping are simpler. [Johari et al. — Always Valid Inference](https://arxiv.org/abs/1512.04922)

4. **Before spending, resolve these concrete issues**

   - **AS1 isolation:** its guide documents a shared default deployment folder. Concurrent samples can overwrite or clean one another’s target; serial samples can inherit leftovers. Give every sample an isolated target before running the advertised parallel queue. [AS1 guide — shared target limitation](/Users/dadleet/src/skill-craft/docs/experiments/apps-script-deployed-target-20261031/README.md:59)
   - **Treatment and scoring:** verify actual worker/context separation, card exposure, and defect presence immediately before review. Inspect the specific repair rather than inferring it from a commit count.
   - **Promotion rule:** decide whether SG2 requires one winning case, all four, or the blocked result. “Any wins” introduces multiplicity; requiring all four is extremely demanding—at 42% power each, four independent wins occur only about **3%** of the time.
   - **Economics:** specify a minimum worthwhile catch-rate gain alongside the 1.5× cost limit. Seeded-defect recall does not reveal how often real defects occur or how much avoided damage is worth. Measure SG2 and AS1 costs separately.
   - **Failure handling:** freeze scorer/build identities and define treatment of timeouts, missing results and retries before observing outcomes. Also interpret `contradicts` cautiously: the current code assigns it whenever B’s observed mean is no higher, without a significant harm test. [experiment.py — verdict logic](/Users/dadleet/src/skill-craft/test/shiploop_e2e/experiment.py:373)

5. **What remains unknown**

   Actual slice cost and variability; baseline catch rates; natural defect frequency and severity; whether the four cases represent consequential failures; whether the inline context reproduces the real self-review problem; and what AS1 result would change your behavior. I ran no live model slices. These uncertainties determine the spending decision more than choosing eight instead of four.
