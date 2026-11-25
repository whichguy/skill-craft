# Judge Prompts & Report Templates

Reference templates for [compare-prompts](../SKILL.md). Substitute placeholders before spawning judges or emitting the final report.

## Diff-Based Judge Prompt (`IS_LARGE_PROMPT == true`)

Run in a fresh independent session (use `judge_model` only when verified host-valid; otherwise `host-default model`):

```
You are comparing two versions of a prompt or skill.
Version B (candidate) differs from version A (baseline) as shown in the diff below.

IMPORTANT: You cannot run these prompts — evaluate which version's INSTRUCTIONS
are better for the given input. Judge on: precision, completeness, unambiguity,
and correctness of the instructions. Reason through what each version would DO
differently for this specific input, based on the diff.

<diff_a_to_b>
{contents of $COMPARE_TMPDIR/diff.txt}
{IF swapped[i]: "(diff direction reversed — lines starting with - are candidate B, + are baseline A)"}
</diff_a_to_b>

<input>
{input_file_i_contents}
</input>

Evaluate the following 7 criteria. For each, determine which version's instructions
better address the criterion for this specific input:
- task_adherence: Which version's instructions would better adhere to the task requirements?
- factual_accuracy: Which version's instructions are more accurate and free of errors?
- completeness: Which version's instructions are more complete for this input type?
- instruction_following: Which version's instructions are clearer and easier to follow?
- structural_clarity: Which version has better structural clarity and organization?
- precision: Which version's instructions are more precise and unambiguous?
- conciseness: Which version is more concise without losing necessary detail?

Output only valid JSON on a single line — no preamble, no markdown fences:
{"scores":{"task_adherence":"?","factual_accuracy":"?","completeness":"?","instruction_following":"?","structural_clarity":"?","precision":"?","conciseness":"?"},"winner":"?","reasoning":"<1-2 sentences>"}
Where each score value is "A" (baseline better), "B" (candidate better), or "~" (equivalent).
```

## Standard Pairwise Judge Prompt (`IS_LARGE_PROMPT == false`)

Run in a fresh independent session (use `judge_model` only when verified host-valid; otherwise `host-default model`):

```
<PROMPT_A>
{judge_prompt_a}
</PROMPT_A>

<PROMPT_B>
{judge_prompt_b}
</PROMPT_B>

<INPUT>
{input_file_i_contents}
</INPUT>

<OUTPUT_A>
{judge_output_a}
</OUTPUT_A>

<OUTPUT_B>
{judge_output_b}
</OUTPUT_B>

Output only valid JSON on a single line — no preamble, no markdown fences:
{"scores":{"task_adherence":"?","factual_accuracy":"?","completeness":"?","instruction_following":"?","structural_clarity":"?","precision":"?","conciseness":"?"},"winner":"?","reasoning":"<1-2 sentences>"}
```

## Pre-Report Helpers

**Bar chart helper** (`bar(value, max_val, width=20)`):
```
filled = round(value / max(max_val, 1) * width)
return "█".repeat(filled) + "░".repeat(width - filled)
```

**Criterion leader** per row:
- `a > b` → `"🔵 A"`
- `b > a` → `"🟢 B"`
- `a == b` → `"⚖️  ~"`

**Criteria where A leads / B leads:**
- `n_criteria_a = count(criterion_tallies[key].a > criterion_tallies[key].b for each key)`
- `n_criteria_b = count(criterion_tallies[key].b > criterion_tallies[key].a for each key)`

**Delta label** (token and latency):
- `delta > 0` → `"+{delta}% · A {leaner|faster}"` (B costs/takes more)
- `delta < 0` → `"{delta}% · B {leaner|faster}"` (B costs/takes less)
- `delta == 0` → `"0% · equal"`

**Verdict emoji:** `IMPROVED → "✅"`, `REGRESSED → "❌"`, `NEUTRAL → "➖"`

**Recommendation sentence** (one sentence, appended after verdict line):
- `IMPROVED  + quality` → `"Ship the candidate — B leads {n_criteria_b}/7 criteria and wins {win_rate_b_pct}% of test cases."`
- `IMPROVED  + tokens`  → `"Ship the candidate — quality tied; B is {|token_delta_pct|}% leaner."`
- `IMPROVED  + time`    → `"Ship the candidate — quality and tokens tied; B is {|latency_delta_pct|}% faster."`
- `REGRESSED + quality` → `"Keep the baseline — A leads {n_criteria_a}/7 criteria and wins {win_rate_a_pct}% of test cases."`
- `REGRESSED + tokens`  → `"Keep the baseline — quality tied; A is {|token_delta_pct|}% leaner."`
- `REGRESSED + time`    → `"Keep the baseline — quality and tokens tied; A is {|latency_delta_pct|}% faster."`
- `NEUTRAL`             → `"No meaningful difference across all three dimensions."`

## Final Report Output Template

Render the following report as markdown (outside any outer code fence; inner `[render as fenced code block]` sections use code fences):

```
## compare-prompts Results

**Baseline (A):** {label_a} — `{prompt_a_path}`
**Candidate (B):** {label_b} — `{prompt_b_path}`
**Inputs:** {inputs_line} · {N} test cases

---

### 🔍 Quality  _(7-criterion pairwise judge)_

| Criterion             |  A  |  B  |  ~  | Leader |
|-----------------------|:---:|:---:|:---:|--------|
| Task Adherence        | {criterion_tallies.task_adherence.a} | {criterion_tallies.task_adherence.b} | {criterion_tallies.task_adherence.tie} | {leader} |
| Factual Accuracy      | {criterion_tallies.factual_accuracy.a} | {criterion_tallies.factual_accuracy.b} | {criterion_tallies.factual_accuracy.tie} | {leader} |
| Completeness          | {criterion_tallies.completeness.a} | {criterion_tallies.completeness.b} | {criterion_tallies.completeness.tie} | {leader} |
| Instruction Following | {criterion_tallies.instruction_following.a} | {criterion_tallies.instruction_following.b} | {criterion_tallies.instruction_following.tie} | {leader} |
| Structural Clarity    | {criterion_tallies.structural_clarity.a} | {criterion_tallies.structural_clarity.b} | {criterion_tallies.structural_clarity.tie} | {leader} |
| Precision             | {criterion_tallies.precision.a} | {criterion_tallies.precision.b} | {criterion_tallies.precision.tie} | {leader} |
| Conciseness           | {criterion_tallies.conciseness.a} | {criterion_tallies.conciseness.b} | {criterion_tallies.conciseness.tie} | {leader} |
| **Total**             | **{Σ_a}** | **{Σ_b}** | **{Σ_tie}** | |

**Win rate by test case:**
[render as fenced code block]
A  {bar(count_a, N)}   {win_rate_a_pct}%   ({count_a} of {N})
B  {bar(count_b, N)}   {win_rate_b_pct}%   ({count_b} of {N})
~  {bar(count_tie, N)} {win_rate_tie_pct}% ({count_tie} of {N})
[end code block]

---

### 🪙 Token Count  _(estimated · char/4 approx)_

Compute: `bar_tokens_a = bar(avg_tokens_a, max(avg_tokens_a, avg_tokens_b))`
         `bar_tokens_b = bar(avg_tokens_b, max(avg_tokens_a, avg_tokens_b))`
Pad `label_a` and `label_b` to equal column width (right-pad shorter with spaces).

[render as fenced code block]
{label_a_padded}  {bar_tokens_a}  ~{avg_tokens_a} est.
{label_b_padded}  {bar_tokens_b}  ~{avg_tokens_b} est.
   Δ {token_delta_label}
[end code block]

---

### ⏱ Time  _(wall-clock · indicative)_

Compute: `bar_latency_a = bar(avg_latency_a, max(avg_latency_a, avg_latency_b))`
         `bar_latency_b = bar(avg_latency_b, max(avg_latency_a, avg_latency_b))`

[render as fenced code block]
{label_a_padded}  {bar_latency_a}  {avg_latency_a} ms
{label_b_padded}  {bar_latency_b}  {avg_latency_b} ms
   Δ {latency_delta_label}
[end code block]

---

### 📋 Per-Test Breakdown

| | File | Reasoning |
|-|------|-----------|
| {winner_emoji} | {file} | "{reasoning}" |
... (one row per test case; winner_emoji: 🟢=B wins, 🔵=A wins, ⚖️=TIE)

---

[render as fenced code block — all lines exactly 64 chars wide]
╔══════════════════════════════════════════════════════════════╗
║  {verdict_emoji}  {verdict}  —  decided by {decided_by}      ║
╠══════════════════════════════════════════════════════════════╣
║  {quality_metric_row}                                        ║
║  {token_metric_row}                                          ║
║  {latency_metric_row}                                        ║
╠══════════════════════════════════════════════════════════════╣
║  {recommendation_sentence_line1}                             ║
[║  {recommendation_sentence_line2}  — only if sentence wraps  ║]
╚══════════════════════════════════════════════════════════════╝
[end code block]

Metric row rules (each row right-padded to fill column 62, then `║`):

**Quality row:**
- decided_by == "quality" AND winner == B → `Quality:  {label_b} leads {n_criteria_b}/7 criteria  ·  {win_rate_b_pct:.0f}% test wins  ←`
- decided_by == "quality" AND winner == A → `Quality:  {label_a} leads {n_criteria_a}/7 criteria  ·  {win_rate_a_pct:.0f}% test wins  ←`
- otherwise → `Quality:  tied (spread within 15% threshold)`

**Token row:**
- decided_by contains "tokens" → `Tokens:   {token_delta_label}  ←`
- NEUTRAL AND |token_delta_pct| < 10 → `Tokens:   {token_delta_label}  (within noise)`
- otherwise → `Tokens:   {token_delta_label}`

**Latency row:**
- decided_by contains "time" → `Latency:  {latency_delta_label}  ←`
- NEUTRAL AND |latency_delta_pct| < 15 → `Latency:  {latency_delta_label}  (within noise)`
- otherwise → `Latency:  {latency_delta_label}`

**Recommendation wrapping:** if recommendation_sentence > 60 chars, split at last space before char 60 and emit the remainder as a second `║` row at the same 2-space indent.
```

**Formatting rules:**
- Round all percentages to 1 decimal place.
- Token delta: `+X%` if B > A (A leaner), `-X%` if B < A (B leaner); label `· A leaner` or `· B leaner`.
- Latency delta: `+X%` if B > A (A faster), `-X%` if B < A (B faster); label `· A faster` or `· B faster`.
- Pad bar chart rows so columns align (counts right-aligned in their field).
- Token/time bar charts: normalize to `max(a, b)` so the larger value fills the full bar. Pad labels to equal width so bar columns align.
- Verdict box: 3 sections separated by `╠═══╣` dividers — (1) verdict header, (2) quality/token/latency metric rows with `←` on the deciding dimension, (3) recommendation. Wrap recommendation at last space before char 60 if > 60 chars; emit remainder as second `║` row.
- Winner emoji column in per-test table: use `⚖️` for TIE (note: emoji width varies — use a single space after for alignment).
