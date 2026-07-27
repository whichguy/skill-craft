---
name: question-bench
description: |
  Benchmark review-plan question effectiveness via experiment-based ablation.
  Applies different question subsets to a plan (or directory of plans) in parallel
  experiments, evaluates each against fixed plan-quality questions (Q-PQ1..Q-PQ8),
  and compares quality spreads to identify which questions drive real improvement.

  Core question: can a smaller set of questions achieve equivalent plan quality?
  Finds the minimal effective question set and recommends keep/merge/drop dispositions.

  Two modes: improve-only (no reference — did questions materially improve?) and
  A/B comparison (reference provided — how does question-derived planB compare?).
  Supports --dry-run for quick per-question verdict scan.

  AUTOMATICALLY INVOKE when user mentions:
  - "benchmark questions", "question effectiveness", "which questions matter"
  - "test review questions", "question impact", "question overlap"
  - "question bench", "bench questions", "ablation"

  NOT for: reviewing a plan (use /review-plan), comparing prompts (use /compare-prompts)

argument-hint: "<plan-file|plans-dir> [--reference <known-good>] [--questions <selector>] [--experiments N|\"subset1 | subset2\"] [--dry-run]"
allowed-tools: Agent, Bash, Read, Glob, Write, Edit
---

# question-bench Skill

Experiment-based ablation for review-plan question effectiveness. Measures whether
review-plan questions improve plans by applying different question subsets in parallel
experiments and comparing quality spreads using fixed evaluation questions.

**Key principle:** Review-plan questions are the *treatment*. Q-PQ evaluation questions
are the *measurement instrument*. These are never conflated.

**Architecture:** Evaluate-then-Edit. All questions are evaluated once against the original
plan (Step 2a), producing stable, authoritative verdicts. Then per experiment, only that
subset's findings are applied to produce planB (Step 2b). This eliminates cross-experiment
context contamination where the same question could get different verdicts in different experiments.

**Core question:** Can fewer questions achieve the same plan quality? The skill finds the
*minimal effective set* — the smallest question subset whose quality spread is within
0.05 of the best — and classifies every question as KEEP, MERGE, CONDITIONAL, or DROP.

**Scope:** Single-pass question application, not the full review-plan convergence loop.
Results indicate individual question signal strength.

## Question ID Registry

### Layer 1 — General Quality (18 active questions, 4 inactive)

**Gate 1 (blocking):** Q-G1, Q-G26, Q-G11
**Gate 2 (important):** Q-G4, Q-G5, Q-G10, Q-G12, Q-G13, Q-G14, Q-G18, Q-G21, Q-G22, Q-G23, Q-G24, Q-G25
**Gate 3 (advisory):** Q-G6, Q-G7, Q-G16, Q-G19
**Epilogue (post-convergence):** Q-E1
**Inactive:** Q-G2 (0% hit rate), Q-G8 (0% hit rate, all N/A), Q-G17 (0% hit rate), Q-G20 (0% hit rate)

### Layer 2 — Code Change Quality (38 questions in 6 clusters)

**Cluster: impact** — Q-C3, Q-C8, Q-C12, Q-C14, Q-C26, Q-C27, Q-C32, Q-C35, Q-C37, Q-C38, Q-C39, Q-C40
**Cluster: testing** — Q-C4, Q-C5, Q-C11, Q-C29 (Q-C9, Q-C10 inactive)
**Cluster: state** — Q-C13, Q-C18, Q-C19, Q-C24, Q-C36
**Cluster: security** — Q-C15, Q-C16, Q-C22, Q-C30, Q-C31, Q-C33, Q-C34
**Cluster: operations** — Q-C6, Q-C7, Q-C20, Q-C23, Q-C28 (Q-C21 inactive)
**Cluster: client** — Q-C17, Q-C25

### Layer 3 — UI Specialization (9 questions)

Q-U1, Q-U2, Q-U3, Q-U4, Q-U5, Q-U6, Q-U7, Q-C17, Q-C25

### Selector → Q-ID Resolution

```
"all"              → L1 + L2 + L3 + Epilogue (61 active + Q-E1)
"L1"               → Gate 1 + Gate 2 + Gate 3 (18 active questions)
"L2"               → all 6 clusters (35 active questions)
"L3"               → Q-U1..Q-U7 + Q-C17 + Q-C25 (9 questions)
"gate:1"           → Q-G1, Q-G26, Q-G11 (3 questions)
"gate:2"           → all Gate 2 questions (12 questions)
"gate:3"           → all Gate 3 questions (4 questions)
"cluster:impact"   → Q-C3, Q-C8, Q-C12, Q-C14, Q-C26, Q-C27, Q-C32, Q-C35, Q-C37, Q-C38, Q-C39, Q-C40
"cluster:testing"  → Q-C4, Q-C5, Q-C11, Q-C29 (Q-C9, Q-C10 inactive)
"cluster:state"    → Q-C13, Q-C18, Q-C19, Q-C24, Q-C36
"cluster:security" → Q-C15, Q-C16, Q-C22, Q-C30, Q-C31, Q-C33, Q-C34
"cluster:operations" → Q-C6, Q-C7, Q-C20, Q-C23, Q-C28 (Q-C21 inactive)
"cluster:client"   → Q-C17, Q-C25
"Q-G1,Q-G26,..."   → parse comma-separated IDs, validate each exists
```

Compound selectors: `L1,cluster:security` → union of both sets.

### Experiment Assignment

**Numeric mode** (`--experiments N`):

```
E=1: Exp-1 = all selected questions
E=2: Exp-1 = gate:1; Exp-2 = all selected
E=3: Exp-1 = gate:1; Exp-2 = gate:1 ∪ gate:2; Exp-3 = all selected
E=4: Exp-1 = gate:1; Exp-2 = gate:1 ∪ gate:2; Exp-3 = L1; Exp-4 = all selected
```

If selected questions are a subset (e.g. `--questions L1`), experiments that would exceed the selected pool are capped at the pool. Example: `--questions L1 --experiments 3` → Exp-1 = gate:1, Exp-2 = gate:1+2, Exp-3 = L1 (all).

**Rationale for default E=3 split:** Gate 1 (3 Qs) → Gate 1+2 (17 Qs) → all selected isolates whether the 14 Gate 2 questions add value beyond the blocking Gate 1 set. This is the most actionable split for determining the minimal effective question set within L1.

**Custom mode** (`--experiments "subset1 | subset2 | ..."`):
Each segment uses selector syntax. `--questions` is ignored in custom mode.

---

## Step 0 — Parse & Preflight

Parse the free-form arguments after `/question-bench`:

| Parameter | Required? | Default | Identification |
|-----------|-----------|---------|----------------|
| PLAN_INPUT | yes | — | First file/directory path |
| REFERENCE_PATH | no | — | After `--reference`, `--planA`, `--gold`, `--known-good` |
| QUESTION_SELECTOR | no | `all` | After `--questions` |
| EXPERIMENTS | no | `3` | After `--experiments`; number 1-4 or quoted string with `\|` |
| DRY_RUN | no | false | `--dry-run` flag present |
| JUDGE_MODEL | no | `claude-opus-4-6` | After `--judge-model` |

**Plan resolution:**
```
IF PLAN_INPUT is a file:
    plans = [PLAN_INPUT]
    is_multi_plan = false
ELIF PLAN_INPUT is a directory:
    plans = glob(PLAN_INPUT/*.md), skip >50KB, sort alphabetically
    is_multi_plan = true
    IF len(plans) == 0: ABORT "No .md files found in PLAN_INPUT"
```

**Mode determination:**
```
IF REFERENCE_PATH provided AND file exists:
    MODE = "ab_comparison"
ELSE:
    MODE = "improve_only"
```

**Experiment parsing:**
```
IF EXPERIMENTS contains "|":
    experiment_mode = "custom"
    segments = split EXPERIMENTS on "|", trim each
    experiment_subsets = [resolve_selector(seg) for seg in segments]
    E = len(experiment_subsets)
    IF E > 4: ABORT "Maximum 4 experiments"
ELSE:
    experiment_mode = "numeric"
    E = int(EXPERIMENTS), clamp to [1, 4]
    selected_questions = resolve_selector(QUESTION_SELECTOR)
    experiment_subsets = compute per assignment table above
```

**Validation:**
- All resolved Q-IDs must exist in the registry
- Each experiment subset must have >= 1 question
- PLAN_INPUT must exist

**Derive paths:**
```
QUESTIONS_PATH = find review-plan/QUESTIONS.md (search ~/.claude/skills/review-plan/ then ../claude-craft/skills/review-plan/)
QUESTIONS_L3_PATH = same directory + QUESTIONS-L3.md
CROSSREF_PATH = find shared/question-cross-reference.md
```

**State output:** Store as BENCH_CONFIG:
- PLANS[] — list of plan file paths
- BATCHES[][] — PLANS chunked into groups of BATCH_SIZE (4)
- REFERENCE_PATH — known-good reference path (null if improve_only)
- MODE — "improve_only" or "ab_comparison"
- EXPERIMENT_SUBSETS[][] — per experiment: list of Q-IDs
- E — experiment count
- JUDGE_MODEL
- IS_MULTI_PLAN — boolean
- QUESTIONS_PATH, QUESTIONS_L3_PATH, CROSSREF_PATH
Consumed by: Steps 2a-5.

**Banner:**
```
╔═══════════════════════════════════════════════════════════╗
║  question-bench                                           ║
║                                                           ║
║  Mode:        MODE                                        ║
║  Plans:       N plan(s) in B batch(es) (PLAN_BASENAMES)   ║
║  Reference:   REFERENCE_PATH or "n/a"                     ║
║  Questions:   N selected (SELECTOR_LABEL)                 ║
║  Experiments: E (ASSIGNMENT_SUMMARY)                      ║
╚═══════════════════════════════════════════════════════════╝
```

*Substitution rules:*
- MODE → BENCH_CONFIG.MODE
- N → len(PLANS)
- PLAN_BASENAMES → comma-separated basenames of first 3 plans + "..." if >3
- SELECTOR_LABEL → QUESTION_SELECTOR or "custom" if custom mode
- ASSIGNMENT_SUMMARY → e.g. "gate:1, gate:1+2, all" or "custom: 3 subsets"

---

## Batch Processing

When more than 4 plans are present, process them in sequential batches to stay within
concurrent agent limits. Each batch completes Steps 2a through 4 before the next batch starts.
Step 5 (Report) runs once after all batches complete, aggregating across all plans.

```
BATCH_SIZE = 4
batches = chunk(PLANS, BATCH_SIZE)   # e.g. 12 plans → 3 batches of 4

For each batch B (1..len(batches)):
    current_plans = batches[B]
    
    # Emit progress
    print "━━━ Batch B/len(batches): PLAN_BASENAMES ━━━"
    
    # Run Steps 2a → 2b → 3 → 4 for current_plans only
    # All agent spawns within a step are parallel (up to BATCH_SIZE concurrent)
    # Steps are sequential: 2a completes before 2b starts, etc.
    
    # Accumulate results into global arrays:
    #   EVAL_VERDICTS[plan_index], EXPERIMENT_RESULTS[plan_index],
    #   SCOPE_RESULTS[plan_index], EVAL_RESULTS per-experiment scores

# After all batches complete:
# Step 5 aggregates across ALL plans (all batches)
```

When 4 or fewer plans are present, there is a single batch and behavior is identical
to the non-batched flow.

---

## Step 2a — Evaluate (once per plan)

**Uses:** BENCH_CONFIG from Step 0.

For each plan P in the current batch, spawn a single evaluation Task. Evaluates ALL selected
questions (union of all experiment subsets, deduplicated) against the original plan. No edits applied.

This step produces **authoritative, stable verdicts** — the same verdict for each question
regardless of which experiment it appears in. This eliminates the cross-experiment context
contamination where the same question could get different verdicts in different experiments.

`--dry-run` stops after this step (skip Steps 2b-5, emit verdicts report).

**Evaluation Task prompt:**

```
You are evaluating an implementation plan against review-plan questions.
For each question, determine: PASS, NEEDS_UPDATE, or N/A.
Do NOT edit the plan — only evaluate and describe findings.

Read the plan:
PLAN_PATH

Read the question definitions:
QUESTIONS_PATH
QUESTIONS_L3_PATH (if L3 questions selected)

Evaluate these questions IN ORDER:
ALL_SELECTED_QUESTION_IDS

For each question:
1. Read its full definition (criteria, N/A conditions)
2. Evaluate whether the plan satisfies the criterion
3. If NEEDS_UPDATE: describe what specific issue was found and what edit would fix it
4. If PASS or N/A: brief reason

Output ONLY this format:
<verdicts>
{"per_question": [
  {"q_id": "Q-G1", "verdict": "NEEDS_UPDATE", "finding": "No alternative approaches considered", "proposed_edit": "Add 'Alternatives Considered' section after Approach with at least 2 rejected alternatives and reasoning", "change_category": "structural"},
  {"q_id": "Q-G2", "verdict": "PASS", "finding": "Follows CLAUDE.md directives", "proposed_edit": null, "change_category": "none"}
]}
</verdicts>

Rules:
- change_category: "structural" | "content" | "cosmetic" | "none"
- proposed_edit: specific enough for a separate editor to apply (section name, what to add/change/remove)
- Do not invent issues — PASS if the plan genuinely satisfies the criterion
- Evaluate each question independently against the ORIGINAL plan (no cumulative edits)
```

*Substitution rules:*
- PLAN_PATH → current plan file path
- QUESTIONS_PATH → BENCH_CONFIG.QUESTIONS_PATH
- QUESTIONS_L3_PATH → BENCH_CONFIG.QUESTIONS_L3_PATH (include only if selected questions contain L3 Q-IDs)
- ALL_SELECTED_QUESTION_IDS → union of all experiment subsets (deduplicated), comma-separated

**Parse results:** Extract JSON from `<verdicts>` tags.

**Short-circuit:** If 0 NEEDS_UPDATE verdicts across all questions → all experiments get STATUS = "no_changes", skip Steps 2b-4, emit NEUTRAL across the board.

**State output:** Store as EVAL_VERDICTS[plan_index]:
- PER_QUESTION[] — array of {q_id, verdict, finding, proposed_edit, change_category}
- NEEDS_UPDATE_IDS[] — list of Q-IDs with verdict == "NEEDS_UPDATE"
- HIT_RATE — needs_update_count / total_questions
Consumed by: Steps 2b, 5.

**If DRY_RUN == true:**

Output per plan:
```
━━━ PLAN_BASENAME ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Q-ID  | Verdict      | Finding                              |
|-------|-------------|--------------------------------------|
| Q-G1  | NEEDS_UPDATE | No alternative approaches considered  |
| Q-G2  | PASS         | Follows CLAUDE.md directives          |
| Q-G11 | NEEDS_UPDATE | References "the module" without paths |
...

Summary: N NEEDS_UPDATE, M PASS, K N/A out of TOTAL.
```

After all plans, print aggregate:
```
━━━ Aggregate (N plans) ━━━━━━━━━━━━━━━━━━━━━━

| Q-ID  | NEEDS_UPDATE | PASS | N/A | Hit Rate |
|-------|-------------|------|-----|----------|
| Q-G1  | 8           | 2    | 1   | 73%      |
| Q-G2  | 3           | 8    | 0   | 27%      |
...

Questions by hit rate (most triggered first):
├─ Q-G11 (82%) — Existing code examined
├─ Q-G1  (73%) — Approach soundness
└─ Q-G6  (9%)  — Naming consistency
```

Skip to Step 6 (emit dry-run summary line). Exit.

---

## Step 2b — Edit (per experiment, parallel)

**Uses:** BENCH_CONFIG from Step 0, EVAL_VERDICTS from Step 2a.

For each plan P in the current batch, for each experiment k (1..E), filter EVAL_VERDICTS to
only include Q-IDs in the experiment's subset that have verdict == "NEEDS_UPDATE". This is
the FINDINGS_JSON for that experiment.

**Short-circuit per experiment:** If no Q-IDs in the experiment subset have NEEDS_UPDATE →
STATUS = "no_changes", skip scope gate + judge for this experiment, emit NEUTRAL.

For experiments with findings, spawn an editor Task. Issue all tasks in parallel
(single message, multiple Agent calls), up to BATCH_SIZE × E concurrent.

**Editor Task prompt:**

```
You are applying specific findings to an implementation plan to produce an improved version.

Read the original plan:
PLAN_PATH_P

Read the question definitions (for context on each finding):
QUESTIONS_PATH
QUESTIONS_L3_PATH (if needed)

Apply these findings to the plan. Each finding was identified by the listed
review-plan question — the question definition provides context for the edit.

Findings to apply:
FINDINGS_JSON

For each finding:
1. Read the question definition for context on what the criterion requires
2. Apply the proposed_edit to the plan text
3. Apply edits cumulatively — each edit builds on prior edits

Output ONLY:
<planB>
[The full improved plan text after all edits applied]
</planB>

Rules:
- Apply ONLY the listed findings — do not evaluate additional questions
- Do not invent new issues beyond what the findings describe
- The planB must be the complete plan, not a diff
- If a proposed_edit conflicts with a prior edit, prefer the one with higher change_category
  (structural > content > cosmetic)
```

*Substitution rules:*
- PLAN_PATH_P → path to plan P
- QUESTIONS_PATH → BENCH_CONFIG.QUESTIONS_PATH
- QUESTIONS_L3_PATH → BENCH_CONFIG.QUESTIONS_L3_PATH (include only if experiment contains L3 Q-IDs)
- FINDINGS_JSON → filtered array from EVAL_VERDICTS, example:
  ```
  [
    {"q_id": "Q-G10", "finding": "Slug collision risk...", "proposed_edit": "Add host-prefix to slug derivation in Phase 3 Step 2", "change_category": "structural"},
    {"q_id": "Q-G22", "finding": "Cross-phase deps implicit...", "proposed_edit": "Add Outputs/Pre-check annotations to each phase", "change_category": "structural"}
  ]
  ```

**Parse results:** For each completed Task:
1. Extract plan text between `<planB>` and `</planB>` tags
2. On parse failure: mark experiment as failed, exclude from Steps 3-4

**State output:** Store as EXPERIMENT_RESULTS[plan_index][exp_index]:
- PLANB_TEXT — improved plan text
- STATUS — "success", "no_changes", or "failed"
- APPLIED_FINDINGS[] — list of Q-IDs whose edits were applied
Consumed by: Steps 3, 4, 5.

---

## Step 3 — Scope Gate (regression check)

**Uses:** EXPERIMENT_RESULTS from Step 2b.

For each experiment in the current batch where STATUS == "success" (skip "no_changes" and "failed"), spawn a general-purpose agent Task (all in parallel):

```
You are checking whether an improved plan has regressed compared to its original.

<original>
ORIGINAL_PLAN_TEXT
</original>

<improved>
PLANB_TEXT
</improved>

Answer these 4 scope-preservation questions. For each: PASS, WARN, or FAIL with a one-sentence reason.

Q-SG1: Does the improved plan preserve all implementation steps from the original? (FAIL if steps were removed without replacement)
Q-SG2: Does the improved plan preserve the original's verification/test strategy? (FAIL if test coverage was removed or weakened)
Q-SG3: Did the improvements introduce contradictions not present in the original? (FAIL if new internal inconsistencies exist)
Q-SG4: Did the improvements add unnecessary scope beyond what the original problem requires? (WARN if mild scope creep, FAIL if significant over-engineering added)

Output ONLY this format:
<scope>
Q-SG1|PASS|All implementation steps preserved
Q-SG2|WARN|Test section expanded but original tests still present
Q-SG3|PASS|No contradictions introduced
Q-SG4|WARN|Added rollback section not in original — minor scope expansion
</scope>
```

*Substitution rules:*
- ORIGINAL_PLAN_TEXT → contents of the original plan file
- PLANB_TEXT → EXPERIMENT_RESULTS[p][k].PLANB_TEXT

**Parse results:** Split `<scope>` content on `|`.

**Verdict per experiment:**
```
IF any Q-SG == FAIL:
    gate_verdict = "FAIL" → excluded from Step 4
ELIF any Q-SG == WARN:
    gate_verdict = "WARN" → proceed with annotation
ELSE:
    gate_verdict = "PASS"
```

**State output:** Store as SCOPE_RESULTS[plan_index][exp_index]:
- GATE_VERDICT — "PASS", "WARN", or "FAIL"
- PER_SG[] — array of {sg_id, verdict, reason}
Consumed by: Steps 4, 5.

---

## Step 4 — Evaluate Experiments (comparative judge)

**Uses:** EXPERIMENT_RESULTS from Step 2b, SCOPE_RESULTS from Step 3.

For each surviving experiment in the current batch (GATE_VERDICT != "FAIL" AND STATUS != "no_changes"), spawn a question-bench-judge agent Task comparing original vs planB.

Experiments with STATUS == "no_changes" receive automatic NEUTRAL verdict with quality_spread = 0.0 and all Q-PQ dimensions = TIE. This avoids wasting compute comparing identical plans.

**Judge runs per comparison:**
```
IF IS_MULTI_PLAN AND len(PLANS) > 3:
    JUDGE_RUNS = 1   # cross-plan averaging provides statistical power
ELSE:
    JUDGE_RUNS = 3   # multiple runs reduce single-plan variance
```

For each plan P, each surviving experiment k, each judge run r (1..JUDGE_RUNS):

**Position randomization:**
```
coin_flip = (random value) < 0.5
IF coin_flip:
    version_x = PLANB_TEXT
    version_y = ORIGINAL_PLAN_TEXT
    swapped = true
ELSE:
    version_x = ORIGINAL_PLAN_TEXT
    version_y = PLANB_TEXT
    swapped = false
```

**Spawn judge agent** (subagent_type: question-bench-judge):

```
<plan_x>
VERSION_X_TEXT
</plan_x>

<plan_y>
VERSION_Y_TEXT
</plan_y>
```

*Substitution rules:*
- VERSION_X_TEXT → version_x (per randomization above)
- VERSION_Y_TEXT → version_y (per randomization above)

**Position remapping** after parsing judge JSON:
```
IF swapped:
    for each question q in result.questions:
        if q.winner == "X": q.winner = "planB"
        elif q.winner == "Y": q.winner = "original"
ELSE:
    for each question q in result.questions:
        if q.winner == "X": q.winner = "original"
        elif q.winner == "Y": q.winner = "planB"
# "TIE" unchanged in both cases
```

**If MODE == "ab_comparison":** Also run judge comparing REFERENCE vs original (same pattern, same JUDGE_RUNS). Reference is treated as another "planB" for scoring purposes.

**Aggregation** (per experiment k):

```
strength_weight = {"strong": 1.0, "moderate": 0.67, "slight": 0.33}
MAX_SCORE = 8.0   # 8 questions x 1.0 max weight

For each plan P, experiment k, judge run r:
  score_original = sum(strength_weight[q.strength] for q in results if q.winner == "original")
  score_planB = sum(strength_weight[q.strength] for q in results if q.winner == "planB")

# Average across judge runs AND across plans:
quality_original_k = mean(score_original / MAX_SCORE)   # across all (P, r) pairs
quality_planB_k = mean(score_planB / MAX_SCORE)
quality_spread_k = quality_planB_k - quality_original_k  # positive = planB better
```

**Per-dimension scores** (for ablation analysis):
```
For each Q-PQ dimension d, each experiment k:
  # Across all plans and judge runs, count planB wins on dimension d
  dimension_wins_k[d] = count(q.winner == "planB" for q in all_results where q.id == d)
  dimension_losses_k[d] = count(q.winner == "original" for q in all_results where q.id == d)
  dimension_score_k[d] = (dimension_wins_k[d] - dimension_losses_k[d]) / total_judgments_k
```

**Per-question impact** (ablation between adjacent experiments):
```
For adjacent experiment pairs (k-1, k):
  added_questions = EXPERIMENT_SUBSETS[k] - EXPERIMENT_SUBSETS[k-1]
  
  For each Q-PQ dimension d:
    delta_d = dimension_score_k[d] - dimension_score_{k-1}[d]
  
  # Attribution: delta_d is attributed to added_questions for dimension d
  # Store as IMPACT_DELTAS[k] = {added_questions, per_dimension_deltas}
```

**Verdict per experiment:**
```
IF quality_spread_k > 0.15:   verdict = "IMPROVED"
ELIF quality_spread_k < -0.15: verdict = "REGRESSED"
ELSE:                          verdict = "NEUTRAL"
```

**State output:** Store as EVAL_RESULTS:
- PER_EXPERIMENT[k] — quality_spread, verdict, dimension_scores, per_judge_results
- IMPACT_DELTAS[k] — added_questions, per_dimension_deltas (for k >= 2)
- REFERENCE_SPREAD — quality_spread for reference (null if improve_only)
Consumed by: Step 5.

---

## Step 5 — Report

**Uses:** BENCH_CONFIG, EVAL_VERDICTS (from Step 2a), EXPERIMENT_RESULTS (from Step 2b), SCOPE_RESULTS, EVAL_RESULTS.

### Overlap detection

Overlap measures whether two questions flag the same issue in the same plan.
With the evaluate-then-edit architecture, verdicts are authoritative (from Step 2a),
so overlap is detected across all NEEDS_UPDATE pairs per plan — not within any specific experiment.

```
# Use EVAL_VERDICTS (authoritative, from Step 2a) for overlap detection
For each plan P:
  needs_update_pairs = all pairs (q_a, q_b) from EVAL_VERDICTS[P] where both verdict == "NEEDS_UPDATE"
  For each pair (q_a, q_b):
    # Check if proposed_edits target the same plan section (nearest ## header)
    section_a = extract target section from q_a.proposed_edit
    section_b = extract target section from q_b.proposed_edit
    IF section_a == section_b:
      overlap_candidates.append({q_a, q_b, section: section_a, plan: P})

# Cross-reference validation
Read CROSSREF_PATH
For each overlap candidate:
  IF (q_a, q_b) appears in cross-reference overlap map:
    classify as "known (confirmed)"
  ELSE:
    classify as "new (investigate)"
```

### "Never fired" tracking

```
# Use EVAL_VERDICTS (authoritative, from Step 2a) — one verdict per Q-ID per plan
all_question_ids = union of all EXPERIMENT_SUBSETS
never_fired = []
For each q_id in all_question_ids:
  fired_count = count of plans P where EVAL_VERDICTS[P].q_id.verdict == "NEEDS_UPDATE"
  total_plans = len(PLANS)
  IF fired_count == 0:
    never_fired.append(q_id)
  hit_rate[q_id] = fired_count / total_plans
```

### Compute best experiment

```
non_regressed = [k for k where verdict != "REGRESSED"]
IF len(non_regressed) > 0:
  best_k = argmax(quality_spread_k for k in non_regressed)
ELSE:
  best_k = argmin(abs(quality_spread_k) for all k)  # least-bad experiment
best_spread = quality_spread_{best_k}
```

### Equivalence analysis (the key insight)

The core question: **can a smaller set of questions achieve equivalent quality?**

```
EQUIVALENCE_THRESHOLD = 0.05  # spreads within 0.05 are considered equivalent

For each pair of experiments (smaller, larger) where |smaller| < |larger|:
  spread_diff = quality_spread_larger - quality_spread_smaller
  
  IF abs(spread_diff) <= EQUIVALENCE_THRESHOLD:
    equivalence = "EQUIVALENT"
    # The smaller set achieves the same quality — the extra questions are unnecessary
  ELIF spread_diff < -EQUIVALENCE_THRESHOLD:
    equivalence = "SMALLER_WINS"
    # The smaller set is actually better — extra questions hurt (over-improvement)
  ELSE:
    equivalence = "LARGER_WINS"
    # The extra questions provide measurable value

# Minimal effective set: smallest experiment whose spread is within EQUIVALENCE_THRESHOLD
# of the best experiment's spread
minimal_effective_k = min(k for k where abs(quality_spread_k - best_spread) <= EQUIVALENCE_THRESHOLD)
minimal_effective_count = len(EXPERIMENT_SUBSETS[minimal_effective_k])
total_question_count = len(union of all EXPERIMENT_SUBSETS)
efficiency_ratio = minimal_effective_count / total_question_count
```

### Incremental value computation

```
For k = 2..E:
  incremental_value[k] = quality_spread_k - quality_spread_{k-1}
  added_count = len(EXPERIMENT_SUBSETS[k] - EXPERIMENT_SUBSETS[k-1])
  
  IF incremental_value[k] < 0.02:
    label = "redundant"
  ELIF incremental_value[k] < 0.08:
    label = "low"
  ELIF incremental_value[k] < 0.15:
    label = "moderate"
  ELSE:
    label = "high"
```

### Emit report

```
╔═══════════════════════════════════════════════════════════╗
║  question-bench Results                                   ║
║  Mode: MODE  ·  Plans: N                                  ║
╚═══════════════════════════════════════════════════════════╝

━━━ 1. Ablation Summary ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Experiment | Questions | Avg Spread | Verdict |
|-----------|-----------|------------|---------|
```

For each experiment k: emit row with subset label, question count, quality_spread_k, verdict.
If MODE == "ab_comparison": emit reference row.

```
  Incremental value:
```

For k = 2..E: emit `├─` or `└─` line with incremental_value[k] and label.

```
━━━ 2. Per-Dimension Impact ━━━━━━━━━━━━━━━━━━━━━━━━
```

For each adjacent experiment pair, emit which Q-PQ dimensions improved/regressed and which
added review-plan questions are attributed. Format:

```
  What SUBSET_LABEL improved (Exp-K vs Exp-K_MINUS_1):
  ├─ Q-PQ_ID dimension_name: +strength
  └─ Q-PQ_ID dimension_name: +strength
```

If IMPACT_DELTAS show a dimension regressed, note it:
```
  └─ Q-PQ5 proportionality: -slight (added questions introduced mild bloat)
```

```
━━━ 3. Per-Question Change Log ━━━━━━━━━━━━━━━━━━━━━

| Q-ID | Verdict      | Finding                    | Applied In    | Category   |
|------|-------------|----------------------------|---------------|------------|
```

One row per Q-ID from EVAL_VERDICTS (authoritative — one verdict per question, stable across experiments).
- Verdict: NEEDS_UPDATE / PASS / N/A (from Step 2a)
- Finding: brief finding text (from Step 2a)
- Applied In: comma-separated experiment labels where this Q-ID was in the subset (e.g. "Exp-2, Exp-3")
- Category: change_category (from Step 2a)

```
━━━ 4. Overlap Detection ━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If overlap candidates found:
```
  Known (confirmed via cross-reference):
  ├─ Q_A ↔ Q_B: both modify "SECTION" section
  ...

  New (not in cross-reference):
  └─ Q_A ↔ Q_B: both modify "SECTION" section
```

If none: `  No overlaps detected.`

```
━━━ 5. Equivalence Analysis ━━━━━━━━━━━━━━━━━━━━━━━━
```

The central question: can fewer questions produce equivalent results?

```
  Minimal effective set: Exp-MINIMAL_K (N questions, SUBSET_LABEL)
  ├─ Spread: +X.XX (vs best Exp-BEST_K: +Y.YY)
  ├─ Efficiency: EFFICIENCY_RATIO% of questions, SPREAD_RATIO% of quality
  └─ Verdict: "N questions are sufficient" / "all N questions needed"

  Pairwise equivalence:
  ├─ Exp-1 (3 Qs) vs Exp-2 (17 Qs): EQUIVALENCE — extra 14 Qs are LABEL
  ├─ Exp-2 (17 Qs) vs Exp-3 (69 Qs): EQUIVALENCE — extra 52 Qs are LABEL
  └─ Exp-1 (3 Qs) vs Exp-3 (69 Qs): EQUIVALENCE — extra 66 Qs are LABEL
```

*Substitution rules:*
- EQUIVALENCE → "EQUIVALENT", "SMALLER_WINS", or "LARGER_WINS"
- LABEL → "unnecessary" (equivalent/smaller_wins), "valuable" (larger_wins)
- SPREAD_RATIO = `quality_spread_minimal / best_spread * 100` (if best_spread == 0: 100%)
- EFFICIENCY_RATIO = `minimal_effective_count / total_question_count * 100`

```
━━━ 6. Never-Fired Questions ━━━━━━━━━━━━━━━━━━━━━━━
```

```
  Questions that never triggered NEEDS_UPDATE across any plan:
  ├─ Q-ID (evaluated across M plans, 0 hits)
  └─ Q-ID (evaluated across M plans, 0 hits)

  IF len(never_fired) > 0:
    These questions may be: (a) well-covered by existing plan conventions,
    (b) too narrowly scoped for these plan types, or (c) candidates for removal.
    Run against more diverse plan types before dropping.
```

If no never-fired questions: `  All questions fired at least once.`

```
━━━ 7. Quality Verdict ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╔═══════════════════════════════════════════════════════════╗
║  VERDICT  ·  best: Exp-K (SUBSET, avg spread +X.XX)       ║
╠═══════════════════════════════════════════════════════════╣
```

For each Q-PQ dimension: emit `║  Q-PQ_ID name:  winner > loser (strength)  ║`

```
╠═══════════════════════════════════════════════════════════╣
║  SUMMARY_SENTENCE_1                                       ║
║  SUMMARY_SENTENCE_2                                       ║
║  SUMMARY_SENTENCE_3                                       ║
╚═══════════════════════════════════════════════════════════╝
```

Summary sentences: derived from equivalence analysis — minimal effective set, which layers are unnecessary, efficiency ratio.

```
━━━ 8. Recommendations ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Actionable question disposition:** Group every tested question into one of four buckets:

```
  Question Disposition:
  
  ✓ KEEP (essential — in minimal effective set, high hit rate):
  ├─ Q-G1 (hit: 73%, improves: approach, specificity)
  ├─ Q-G11 (hit: 82%, improves: actionability)
  └─ Q-G10 (hit: 64%, improves: verification)

  ~ MERGE (overlapping — combine with another question):
  ├─ Q-C15 → merge into Q-G4 (both target security, same section)
  └─ Q-C12 → merge into Q-G12 (duplication check overlap)

  ▸ CONDITIONAL (value depends on plan type):
  ├─ Q-C3 — only fires on deployment plans (0% hit on lib plans)
  └─ L3 questions — only for UI plans

  ✗ DROP candidates (never fired, or fired but no quality impact):
  ├─ Q-G8 (fired 45% but Q-PQ5 regressed — adds bloat)
  └─ Q-C28 (never fired across 11 plans)
```

Disposition logic:
```
For each Q-ID:
  IF in minimal effective set AND hit_rate > 0.3:
    disposition = "KEEP"
  ELIF in overlap_candidates (Section 4):
    disposition = "MERGE" — suggest merge target (the overlapping Q with higher hit rate)
  ELIF in never_fired:
    disposition = "DROP candidate"
  ELIF hit_rate > 0 AND associated dimension_delta <= 0:
    disposition = "DROP candidate" — fires but doesn't improve quality
  ELIF hit_rate > 0 AND fires only on specific plan types:
    disposition = "CONDITIONAL"
  ELSE:
    disposition = "KEEP" (default to keeping if insufficient data)
```

**Cross-plan patterns** (multi-plan mode only):

```
  Cross-Plan Patterns:
  ├─ Questions that consistently improve across all plan types:
  │   Q-G1, Q-G11, Q-G10 (fired 70%+ on all plan types)
  ├─ Questions that only fire on specific plan types:
  │   Q-C3, Q-C8 — deployment/infra plans only
  │   Q-U1..Q-U7 — UI plans only
  └─ Plan types where questions add least value:
      trivial plans (avg spread +0.03) — consider skipping review-plan
```

**Efficiency summary:**
```
  Efficiency: MINIMAL_COUNT / TOTAL_COUNT questions (EFFICIENCY_RATIO%)
  achieve SPREAD_RATIO% of maximum quality improvement.
  
  Recommended question set for these plan types:
    MINIMAL_EFFECTIVE_Q_IDS
```

If custom experiments were used, emit per-question isolation findings.

If IS_MULTI_PLAN == false:
```
  Note: Single-plan results are directional. Run against a plan directory
  for statistically meaningful results.
```

If custom experiments available, suggest follow-up:
```
  To isolate individual questions, re-run with custom experiments:
    /question-bench PLAN_INPUT --experiments "Q-G1 | Q-G1,Q-G10 | Q-G1,Q-G10,Q-G22"
  
  To find the minimal set for your plan types:
    /question-bench plans/ --experiments "gate:1 | gate:1,gate:2 | L1 | all"
```

---

## Step 6 — Cleanup

Remove any temporary files created during the run.

Print summary one-liner:
```
question-bench complete: E experiments × N plans, hit rate: X% (N/M fired), best=Exp-K (SUBSET, spread +X.XX), verdict: VERDICT, minimal set: N Qs (EFFICIENCY%)
```
