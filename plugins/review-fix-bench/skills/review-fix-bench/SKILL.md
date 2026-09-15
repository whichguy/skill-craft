---
name: review-fix-bench
description: >-
  Compare two code-review prompt versions against supplied fixture ground truth
  using an explicitly configured external benchmark runner. Reports an F1-based
  verdict only when the runner completes both evaluations and comparison.
argument-hint: "--target <prompt> --runner <executable> --fixtures <dir> --judge <prompt> [--candidate <prompt>] [--runs N] [--repo <dir>]"
version: 0.1.1
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

# review-fix-bench

Benchmark a review-prompt candidate against ground-truth fixtures. This package
contains the orchestration contract only. **No installed runner is bundled**:
the target, fixtures, judge rubric, and benchmark runner are explicit inputs so
the skill never reaches into a sibling plugin, a personal checkout, or a host cache.

## Invocation

```text
/review-fix-bench \
  --target /absolute/path/to/current-reviewer.md \
  --runner /absolute/path/to/review-fix-bench.sh \
  --fixtures /absolute/path/to/fixtures \
  --judge /absolute/path/to/judge-rubric.md \
  [--candidate /absolute/path/to/candidate-reviewer.md] \
  [--repo /absolute/path/to/target-repository] [--runs 1..3]
```

`--target`, `--runner`, `--fixtures`, and `--judge` are required. The runner is a
**separately installed** and licensed dependency chosen by the operator; this
marketplace package neither declares an imaginary plugin dependency nor downloads
one. `--candidate` is preferred. Without it, derive the candidate from `HEAD~1`
only after the supplied `--repo` is confirmed to contain `--target`; otherwise
stop and ask for `--candidate`.

## Step 1 — Resolve and preflight

1. Canonicalize each supplied path. Do not infer any path from the current working
   directory, an installed skill directory, an environment variable, or a host cache.
2. Confirm `--target`, `--judge`, and every fixture file exist and are readable.
   Require at least one `*.ground-truth.json` fixture.
3. Confirm `--runner` is executable and is the intended separately installed runner.
   Read its documented interface or call its non-mutating help command. It must support
   `--run`, `--compare`, `--agent-file`, `--judge-file`, `--fixtures`, and `--runs`.
   If it does not, stop with `ERROR: configured runner lacks the required bench interface`.
4. If deriving `HEAD~1`, confirm the supplied repository is a Git worktree and compute the
   target's repository-relative path. On missing history, stop with `ERROR: provide --candidate`.
5. State the resolved absolute inputs and selected candidate source before any evaluation.

Do not report a benchmark result after only these checks. A missing runner, fixture, judge,
or history is a blocked prerequisite, not a neutral or passing result.

## Step 2 — Run isolated A/B evaluations

Run the configured runner twice with identical fixtures, judge, run count, and isolation
settings; vary only the agent prompt and label:

```sh
"$RUNNER" --run --label current --fixtures "$FIXTURES" --runs "$RUNS" \
  --agent-file "$TARGET" --judge-file "$JUDGE"
"$RUNNER" --run --label candidate --fixtures "$FIXTURES" --runs "$RUNS" \
  --agent-file "$CANDIDATE" --judge-file "$JUDGE"
```

If the runner evaluates prompts through an agent host, each evaluation must use a fresh
independent session. Do not reuse the current result as context for the candidate. Parallel
execution is permitted only when the runner guarantees that the two runs do not share state.
Capture stdout, stderr, exit code, and the reported result path for both runs.

## Step 3 — Compare only completed result files

Proceed only when both evaluations exited zero and each emitted an existing result file.
Run:

```sh
"$RUNNER" --compare "$RESULT_CURRENT" "$RESULT_CANDIDATE"
```

Treat malformed output, missing F1 metrics, or a non-zero comparison as a benchmark failure.
Do not infer an IMPROVED, REGRESSED, or NEUTRAL verdict from partial output.

## Step 4 — Report

Report the target/candidate paths, source revision when used, runner path and version,
fixture digest or inventory, judge path, run count, result paths, exit codes, and the raw
comparison verdict. Label the result as an evaluation by the configured runner; this skill
does not itself validate reviewer behavior. Keep temporary candidate files only until the
comparison completes, then remove only those files created for this invocation.

## Not for

Installing a benchmark runner, discovering arbitrary sibling plugins, or claiming a model
evaluation from static package checks. Supply a compatible runner and fixtures first.
