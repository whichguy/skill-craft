# Question Bench

Benchmark review-plan question effectiveness via experiment-based ablation. Applies different question subsets to a plan (or directory of plans) in parallel experiments, evaluates each against fixed plan-quality questions (Q-PQ1..Q-PQ8), and compares quality spreads to identify which questions drive real improvement.

## Install

Install the `question-bench` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$question-bench` for a matching request. Read [SKILL.md](skills/question-bench/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/question-bench/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/question-bench/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
