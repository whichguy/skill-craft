---
name: compare-prompts
description: |
  Compare two prompt versions (A vs B) by running both against a directory of test input
  files, then evaluating results on three dimensions in priority order: quality > tokens > time.

  **AUTOMATICALLY INVOKE** when user mentions:
  - "compare prompts", "which prompt is better", "prompt efficiency"
  - "A/B test prompts", "evaluate prompts", "test these prompts"
  - Multiple prompt variations to choose between

  **STRONGLY RECOMMENDED** for:
  - Optimizing prompt quality
  - Reducing token usage
  - Comparing alternative approaches
  - Before finalizing agent/skill prompts

  Position bias mitigated via randomized ordering per test case — judge sees A/B in random
  order, results remapped before aggregation.

argument-hint: "<prompt-file> [inputs-dir | inline text] [prompt-b] [free-form options]"
allowed-tools: Agent, Task, TaskCreate, TaskGet, TaskList, TaskUpdate, TaskStop, TaskOutput, Bash, Read, Glob, Write
---

# compare-prompts Skill

Run two prompt versions against a directory of test inputs, then compare outputs on:
**quality** (pairwise judge) → **tokens** (char/4 estimate) → **time** (wall-clock).

## Argument Reference

The arguments after `/compare-prompts` are **free-form text**. The LLM interprets them
to extract the following values:

| Parameter | Required? | What to look for | Default |
|-----------|-----------|-------------------|---------|
| `prompt_a_path` | **yes** | A file path — the first/only `.md` path, or one labeled "A", "baseline", "current", "before" | — |
| `inputs_dir` | no | A directory path for test inputs. Associated with "inputs", "test", "dir" | — |
| `input_text` | no | Inline text to use as a single test input. Any remaining free-form text that is not a file path, directory, label, or model name. Look for quoted strings, or text after "with input", "using text", "test with" | — |
| `prompt_b_path` | no | A second file path labeled "B", "candidate", "new", "after", or simply the second path | HEAD~1 of prompt A |
| `label_a` | no | A short label for prompt A. Look for "label-a", "baseline label" | "A" |
| `label_b` | no | A short label for prompt B. Look for "label-b", "candidate label" | "B" |
| `run_model` | no | A model name (claude-*) for running prompts | claude-sonnet-4-6 |
| `judge_model` | no | A model name for the quality judge | claude-opus-4-6 |

**Input sources** (at least one recommended, but both optional):
- `inputs_dir` — directory of test files (each file = one test case)
- `input_text` — inline text string (becomes a single test case named "inline-input")
- If both provided: directory files + inline text are all used as test cases
- If neither provided: prompts are run once with no input (empty input — useful for prompts that don't need external input)

**Example invocations:**
```
/compare-prompts agents/code-reviewer.md inputs/
/compare-prompts agents/code-reviewer.md with inputs from inputs/
/compare-prompts compare agents/code-reviewer.md against agents/code-reviewer-v2.md using inputs/
/compare-prompts baseline agents/old.md vs candidate agents/new.md, test with inputs/, use haiku as judge
/compare-prompts agents/summarizer.md "The quick brown fox jumped over the lazy dog"
/compare-prompts agents/translator.md with text "Hello world, how are you?"
/compare-prompts agents/code-reviewer.md   (no input — runs prompt with empty input)
/compare-prompts --prompt agents/code-reviewer.md --inputs inputs/  (legacy flag style also works)
```

---

## Step 0 — Parse & Preflight

**Interpret arguments from `<prompt-arguments>` as free-form text.**

Extract these values by understanding the user's intent — they may use flags, positional
paths, natural language, or any combination:

| Variable | How to identify |
|----------|----------------|
| `prompt_a_path` | The primary prompt file. Look for the first file path containing `/` or `.md`. If `--prompt` or `--prompt-a` flag is present, use its value. Words like "baseline", "current", "before", "A" help disambiguate when two paths are present. |
| `prompt_b_path` | The comparison prompt file. Look for a second file path, or one associated with "B", "candidate", "new", "after", "compare against", "vs". If `--prompt-b` flag is present, use its value. |
| `inputs_dir` | A directory path for test inputs. Look for paths associated with "inputs", "test", "dir". If `--inputs` flag is present, use its value. Optional — may be absent. |
| `input_text` | Inline text to use as test input. Look for quoted strings, or text after "with input", "using text", "test with". Also: any substantial free-form text that is clearly meant as input content (not a path, label, or model). If `--input` or `--text` flag is present, use its value. Optional — may be absent. |
| `label_a` | Display label for prompt A. Look for "label-a", "baseline label", or `--label-a`. |
| `label_b` | Display label for prompt B. Look for "label-b", "candidate label", or `--label-b`. |
| `run_model` | A model identifier (claude-*). Look for "model", "use", "with", or `--model`. |
| `judge_model` | A model for judging. Look for "judge", "judge-model", or `--judge-model`. |

**Defaults** (apply when not found in arguments):
- `prompt_b_path` = derived from git HEAD~1 of prompt_a_path (existing resolution logic)
- `inputs_dir` = none (no directory inputs)
- `input_text` = none (no inline input)
- `label_a` = "A"
- `label_b` = "B"
- `run_model` = claude-sonnet-4-6
- `judge_model` = claude-opus-4-6

**Resolve prompt_b_path** (if not explicitly provided):
1. Determine REPO_ROOT: `git -C "$(dirname <prompt_a_path>)" rev-parse --show-toplevel`
2. Compute RELATIVE_PATH: relative path of prompt_a_path from REPO_ROOT
3. Run preflight: `git -C "$REPO_ROOT" show HEAD~1:"$RELATIVE_PATH" > /dev/null 2>&1`
   - If this fails → abort with:
     `"Cannot extract HEAD~1 of <file>: no prior commit history. Provide --prompt-b explicitly."`
4. Extract: `git -C "$REPO_ROOT" show HEAD~1:"$RELATIVE_PATH" > "$COMPARE_TMPDIR/prompt-b-head1.md"`
5. Set prompt_b_path = `$COMPARE_TMPDIR/prompt-b-head1.md`

Create temp working dir: `COMPARE_TMPDIR=$(mktemp -d /tmp/compare-prompts.XXXXXX)`
— NOTE: use `COMPARE_TMPDIR`, not `$TMPDIR` (macOS system env var, do not overwrite)

**Requirement validation — abort immediately if any required value is missing:**

After interpreting the arguments, check:

1. **Prompt A**: `prompt_a_path` must be identified.
   If not found → abort:
   "ERROR: Could not identify a prompt file in the arguments.
   Provide a file path to compare.
   Example: /compare-prompts path/to/prompt.md path/to/inputs/"

2. **Value validation**:
   - prompt_a_path must exist on disk
   - prompt_b_path must exist on disk (after git HEAD~1 resolution if not explicit)
   - If `inputs_dir` was identified: it must exist on disk
   - run_model and judge_model must match `claude-*`

After all validations pass, emit the start banner as a fenced code block:

[render as fenced code block — all lines exactly 64 chars wide]
╔══════════════════════════════════════════════════════════════╗
║  ⚖️  compare-prompts                                         ║
║                                                              ║
║  Baseline  ({label_a}):  {prompt_a_path}                     ║
║  Candidate ({label_b}):  {prompt_b_path}                     ║
║  Inputs:        {inputs_line}                                ║
║  Model:         {model_line}                                 ║
╚══════════════════════════════════════════════════════════════╝
[end code block]

Inputs line: if `inputs_dir` → `"{inputs_dir}"` · if `input_text` only → `"inline text ({len} chars)"` · if both → `"{inputs_dir} + inline text"` · if neither → `"(no input — empty run)"`

Truncation rule: usable inner width = 60 chars (after 2-space left margin). If a path/dir
field exceeds its usable width, truncate from the left: `"..." + path[-(usable - 3):]`.
Model line: if run_model == judge_model → `"{run_model}  (runs + judge)"`
           if different → `"{run_model}  ·  Judge: {judge_model}"`
Each row right-padded with spaces to fill column 62, then `║`.

[1/6] ⚙️  preflight ── `{prompt_a_path}` vs `{prompt_b_path}`

---

## Step 1 — Load Inputs

Build the list of test cases from available input sources:

**From `inputs_dir`** (if provided):
- Glob `*.md` and `*.txt` from inputs_dir
- Cap at 10 files. If more found → warn: `"Warning: found <N> input files; using first 10 only."`
- For each file: check size. If > 50KB → skip with: `"Skipping <file>: exceeds 50KB limit"`
- Read surviving files' contents into memory

**From `input_text`** (if provided):
- If `input_text` is an empty string → skip and warn: `"Warning: input_text was empty — ignored."`
- Otherwise: create a single test case named `"inline-input"` with contents = the `input_text` string

**No input sources** (neither `inputs_dir` nor `input_text`):
- Create a single test case named `"empty-input"` with contents = `""` (empty string)
- Warn: `"Warning: no inputs provided — running prompts with empty input."`

**Combine**: all test cases from directory files + inline text (if both provided).

**Validation**:
- If `inputs_dir` was provided but zero files survived (all exceeded 50KB or none matched *.md/*.txt) AND no `input_text` → abort: `"No valid input files in <dir> (all exceeded 50KB or none matched *.md/*.txt)"`
- If N < 3 → warn: `"Warning: N=<N> test case(s) — quality win rates have low statistical confidence. Use 3+ inputs for meaningful comparison."`

[2/6] 📂 inputs ── {N} test cases{source_detail}
Where `source_detail`:
- directory only: `" from \`{inputs_dir}\`"`
- inline only: `" (inline text)"`
- both: `" from \`{inputs_dir}\` + inline text"`
- neither: `" (empty input)"`
(If files were skipped: [2/6] 📂 inputs ── {N} of {N_found} test cases ({N_skipped} skipped))

---

## Step 2 — Spawn All Runs in Parallel (2×N Tasks)

Read prompt_a contents and prompt_b contents.

**Large-prompt detection:**
```
LARGE_PROMPT_THRESHOLD = 25000
IS_LARGE_PROMPT = max(len(prompt_a_contents), len(prompt_b_contents)) > LARGE_PROMPT_THRESHOLD
IF IS_LARGE_PROMPT:
    max_len = max(len(prompt_a_contents), len(prompt_b_contents))
    Print: "⚠️  Large prompt ({max_len} chars) — using diff-based evaluation"
    Bash: diff "{prompt_a_path}" "{prompt_b_path}" > "$COMPARE_TMPDIR/diff.txt" || true
```

IF IS_LARGE_PROMPT:
    # Skip run agents — proceed directly to diff-based judges in Step 4
    Print: "[3/6] 🚀 runs ── skipped (diff-based mode)"
    # All run outputs set to N/A; latency/tokens N/A
    avg_latency_a = 0; avg_latency_b = 0
    avg_tokens_a = 0; avg_tokens_b = 0
ELSE:
    **Prompt injection** — build task_prompt per run:
    ```
    IF prompt_contents contains "{{INPUT}}":
        task_prompt = prompt_contents.replace("{{INPUT}}", input_file_contents)
    ELSE:
        task_prompt = prompt_contents + "\n\n<INPUT>\n" + input_file_contents + "\n</INPUT>\n\nExecute the above instructions on the provided input. Output your response directly."
    ```

    Record `start_time_ms = Date.now()` per task before spawning.

    **Spawn all 2×N Tasks in a single parallel message** with `run_in_background: true`.
    Each task:
    - `subagent_type`: general-purpose
    - `model`: run_model (default claude-sonnet-4-6)
    - `prompt`: constructed task_prompt (above)
    - `run_in_background`: true

    Name tasks for tracking: `run-A-<filename>`, `run-B-<filename>`.

[3/6] 🚀 runs ── {2*N} tasks launched  _(or "skipped (diff-based mode)" if IS_LARGE_PROMPT)_

---

## Step 3 — Collect Results, File-Artifact Resolution & Timing

IF IS_LARGE_PROMPT:
    Print: "[4/6] ✅ runs complete ── (skipped — diff-based mode)"
    Skip remaining steps in this section — no run tasks were spawned. Proceed directly to Step 4.

Poll all 2×N tasks until complete. Use TaskGet or await completion notifications. Wrap each TaskGet call in try/catch — if a poll throws, treat that task as failed and proceed to error handling below.

For each completed task, collect the raw output text then apply **file-artifact resolution**:

```
raw_output = task result text

// Pattern 1: file-output-executor format — "COMPLETE: /path/to/file BYTES SECONDS"
IF raw_output matches /^COMPLETE:\s+(\/\S+)/m:
    file_path = captured group 1
    TRY: output = Read(file_path)   // full file contents
    CATCH: log "file-artifact read failed: <file_path>" — output = raw_output

// Pattern 2: agent wrote file and said so — "Output written to /path/to/file" (or "output written to:")
ELIF raw_output matches /[Oo]utput written to[:\s]+(\/\S+)/m:
    file_path = captured group 1
    TRY: output = Read(file_path)
    CATCH: output = raw_output

// Pattern 3: bare file path — entire output (trimmed) is a single path starting with /
ELIF strip(raw_output) matches /^\/\S+$/:
    file_path = strip(raw_output)
    TRY: output = Read(file_path)
    CATCH: output = raw_output   // might be a path-like string, not an actual file

// No artifact detected
ELSE:
    output = raw_output
```

After resolution, record per task:
- **output**: resolved content (file contents if artifact detected, else raw output)
- **latency_ms**: `end_time_ms - start_time_ms` (wall-clock from spawn to completion detection)
- **input_tokens_est**: `Math.floor((prompt_len + input_len) / 4)` (char/4 approximation — labeled "est." in report)
- **output_tokens_est**: `Math.floor(len(output) / 4)` (re-computed after resolution)
- **total_tokens_est**: `input_tokens_est + output_tokens_est`

**NOTE on timing**: latency_ms reflects polling-detected wall-clock time. For short tasks, polling interval overhead may exceed model compute time — treat as indicative, not precise.

**Error handling**: If a task completed in error state → mark as failed. Skip it in aggregation (tokens, time) AND skip the quality judge for that input file — do not spawn a judge task when either A or B run for that file failed. Note in Per-Test Breakdown: `"task error — skipped (no judge)"`. Use try/catch around result collection.

**Context management**: After collecting each task's output, store only compact summaries
(winner/latency/tokens/output text for judge). Do not retain full raw outputs longer than needed —
with 10 inputs, 20 raw outputs could bloat the context significantly.

[4/6] ✅ runs complete ── {label_a} {avg_latency_a/1000:.1f}s · {label_b} {avg_latency_b/1000:.1f}s

---

## Step 4 — Spawn Judge Tasks in Parallel (N Tasks)

IF IS_LARGE_PROMPT:
    # DIFF-BASED JUDGING — judge receives diff + input context (no run outputs)

    **Spawn all N judge tasks in a single parallel message** with `run_in_background: true`.

    For each input file i:

    **Position randomization** (mitigates first-position bias):
    ```
    coin_flip = Math.random() < 0.5
    swapped[i] = coin_flip
    # if swapped: diff direction is noted as reversed in prompt
    ```

    Diff-based judge task prompt (use judge_model):
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

    [5/6] ⚖️  judging ── {N} tasks launched  _(diff-based mode)_

ELSE:
    # STANDARD JUDGING — judge receives both prompt texts + run outputs

    **Spawn all N judge tasks in a single parallel message** with `run_in_background: true`.

    For each input file i:

    **Position randomization** (mitigates first-position bias):
    ```
    coin_flip = Math.random() < 0.5
    IF coin_flip:
        // Swap: B appears as "A" to the judge
        judge_prompt_a = prompt_b_contents
        judge_prompt_b = prompt_a_contents
        judge_output_a = task_b_output_for_file_i
        judge_output_b = task_a_output_for_file_i
        swapped[i] = true
    ELSE:
        // Normal ordering
        judge_prompt_a = prompt_a_contents
        judge_prompt_b = prompt_b_contents
        judge_output_a = task_a_output_for_file_i
        judge_output_b = task_b_output_for_file_i
        swapped[i] = false
    ```

    Spawn agent `compare-prompts-judge` with prompt:
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

    Use `judge_model` (default claude-opus-4-6) as model parameter.

    [5/6] ⚖️  judging ── {N} tasks launched

**Judge output**: JSON with 3 keys: `scores` (7-key object — each criterion evaluated relative to its own prompt's instructions), `winner` ("A"|"B"|"TIE"), `reasoning` (1-2 sentences).

**Position remapping** (after parsing each judge result, before aggregation):
```
IF swapped[i]:
    for key in result.scores:
        if scores[key] == "A": scores[key] = "B"
        elif scores[key] == "B": scores[key] = "A"
        // "TIE" unchanged
    if result.winner == "A": result.winner = "B"
    elif result.winner == "B": result.winner = "A"
    // "TIE" unchanged
```

**Error handling**: If a judge task fails or returns malformed JSON:
- TRY to parse `result.scores` (7 keys) and `result.winner`
- If `scores` key is missing but `winner` is present → use `winner` only, skip criterion tallies for this case (count as TIE per criterion)
- If both missing → count overall winner as TIE
- Note in Per-Test Breakdown: `"judge error — counted as TIE"`. Use try/catch on JSON.parse().

[6/6] ✅ judging complete ── {label_a} {count_a}/{N} · {label_b} {count_b}/{N} · {count_tie} tied

---

## Step 5 — Aggregate & Verdict

Compute per dimension:

**Quality — per-test winners:**
```
count_a = count(winner == "A")
count_b = count(winner == "B")
count_tie = count(winner == "TIE")
win_rate_a = count_a / N
win_rate_b = count_b / N
win_rate_tie = count_tie / N
```

**Quality — per-criterion tallies** (across all N test cases):
```
criterion_keys = ["task_adherence","factual_accuracy","completeness","instruction_following","structural_clarity","precision","conciseness"]

criterion_tallies = {}
FOR key IN criterion_keys:
    criterion_tallies[key] = {a: 0, b: 0, tie: 0}

FOR each judge result WITH valid scores object:
    FOR key IN criterion_keys:
        score = result.scores[key]   // "A", "B", or "TIE"
        IF score == "A": criterion_tallies[key].a += 1
        ELIF score == "B": criterion_tallies[key].b += 1
        ELSE: criterion_tallies[key].tie += 1
```

**Tokens** (averages across successful runs only):
```
avg_tokens_a = mean(total_tokens_est for all A runs)
avg_tokens_b = mean(total_tokens_est for all B runs)
```

**Time:**
```
avg_latency_a = mean(latency_ms for all A runs)
avg_latency_b = mean(latency_ms for all B runs)
```

Compute delta values for the report:
```
token_delta_pct = round(((avg_tokens_b - avg_tokens_a) / max(avg_tokens_a, avg_tokens_b, 1)) * 100, 1)
latency_delta_pct = round(((avg_latency_b - avg_latency_a) / max(avg_latency_a, avg_latency_b, 1)) * 100, 1)
# Positive = B is larger (A wins efficiency), negative = B is smaller (B wins efficiency)
# NOTE: denominators use max(a,b,1) to match the tiebreaker condition denominators and keep
# the reported percentage consistent with the decision threshold.
```

**Tiebreaker chain — priority: quality → tokens → time:**
```
# Threshold values chosen to filter noise:
# quality: >15% spread = meaningful difference
# tokens: >10% spread = meaningful efficiency gain
# time: >15% spread = meaningful speed difference

IF |win_rate_a - win_rate_b| > 0.15:
    overall_winner = (win_rate_a > win_rate_b) ? "A" : "B"
    decided_by = "quality"
ELIF max(avg_tokens_a, avg_tokens_b) > 0 AND |avg_tokens_a - avg_tokens_b| / max(avg_tokens_a, avg_tokens_b) > 0.10:
    overall_winner = (avg_tokens_a < avg_tokens_b) ? "A" : "B"
    decided_by = "tokens (quality tied)"
ELIF max(avg_latency_a, avg_latency_b) > 0 AND |avg_latency_a - avg_latency_b| / max(avg_latency_a, avg_latency_b) > 0.15:
    overall_winner = (avg_latency_a < avg_latency_b) ? "A" : "B"
    decided_by = "time (quality+tokens tied)"
ELSE:
    overall_winner = "NEUTRAL"
    decided_by = "all dimensions within noise thresholds"
```

**Verdict label mapping:**
```
overall_winner == "A"       → verdict = "REGRESSED"
overall_winner == "B"       → verdict = "IMPROVED"
overall_winner == "NEUTRAL" → verdict = "NEUTRAL"
```

After computing overall_winner, decided_by, verdict, and all metric values, emit the early verdict flash wrapped in thin rules (plain markdown, not fenced):

```
Print: "──────────────────────────────────────────────────────"
```
- If decided_by == "quality":
  {verdict_emoji} {verdict} ── quality: {quality_flash} · tokens: {token_flash} · latency: {latency_flash}
- Otherwise (decided by tokens, time, or NEUTRAL):
  {verdict_emoji} {verdict} ── quality: tied · tokens: {token_flash} · latency: {latency_flash}
```
Print: "──────────────────────────────────────────────────────"
```

Where:
- `quality_flash`: `"{winning_label} leads {n_criteria_winner}/7 criteria ({win_rate_winner_pct:.0f}% wins)"` where `n_criteria_winner` = `n_criteria_b` if `overall_winner == "B"` else `n_criteria_a`; `win_rate_winner_pct` = `win_rate_b * 100` if `overall_winner == "B"` else `win_rate_a * 100`
- `token_flash`: if `|token_delta_pct| >= 10` → `"{sign}{|val|}% ({leaner_label} leaner)"` · else → `"{token_delta_pct:+.1f}% (within noise)"`
- `latency_flash`: if `|latency_delta_pct| >= 15` → `"{sign}{|val|}% ({faster_label} faster)"` · else → `"{latency_delta_pct:+.1f}% (within noise)"`
- Use − (U+2212) for negative values, + for positive.

---

## Step 6 — Report

### Pre-report computations

**Bar chart helper** (`bar(value, max_val, width=20)`):
```
filled = round(value / max(max_val, 1) * width)
return "█".repeat(filled) + "░".repeat(width - filled)
```

**Criterion leader** per row:
```
a > b  → "🔵 A"
b > a  → "🟢 B"
a == b → "⚖️  ~"
```

**Criteria where A leads / B leads:**
```
n_criteria_a = count(criterion_tallies[key].a > criterion_tallies[key].b for each key)
n_criteria_b = count(criterion_tallies[key].b > criterion_tallies[key].a for each key)
```

**Delta label** (token and latency):
```
delta > 0  → "+{delta}% · A {leaner|faster}"   // B costs/takes more
delta < 0  → "{delta}% · B {leaner|faster}"     // B costs/takes less
delta == 0 → "0% · equal"
```

**Verdict emoji:**
```
IMPROVED  → "✅"
REGRESSED → "❌"
NEUTRAL   → "➖"
```

**Recommendation sentence** (one sentence, appended after verdict line):
```
IMPROVED  + decided by quality → "Ship the candidate — B leads {n_criteria_b}/7 criteria and wins {win_rate_b_pct}% of test cases."
IMPROVED  + decided by tokens  → "Ship the candidate — quality tied; B is {|token_delta_pct|}% leaner."
IMPROVED  + decided by time    → "Ship the candidate — quality and tokens tied; B is {|latency_delta_pct|}% faster."
REGRESSED + decided by quality → "Keep the baseline — A leads {n_criteria_a}/7 criteria and wins {win_rate_a_pct}% of test cases."
REGRESSED + decided by tokens  → "Keep the baseline — quality tied; A is {|token_delta_pct|}% leaner."
REGRESSED + decided by time    → "Keep the baseline — quality and tokens tied; A is {|latency_delta_pct|}% faster."
NEUTRAL                        → "No meaningful difference across all three dimensions."
```

---

### Output

Output the following report (outside any code fence — render as markdown):

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

---

## Step 7 — Cleanup

```bash
rm -rf "$COMPARE_TMPDIR"
```
