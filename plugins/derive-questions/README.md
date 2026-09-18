# Derive Questions

Iteratively researches real software project failures and wins, extracts key planning questions via 5-whys analysis, validates them against synthetic test plans, judges their effectiveness via a parallel judge agent, refines them, and persists to a growing questions library. Builds a curated, language/system-agnostic question library that prevents known failure modes when applied during software planning.

## Install

Install the `derive-questions` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$derive-questions:derive-questions`; in Claude, invoke `/derive-questions:derive-questions`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/derive-questions/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/derive-questions/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/derive-questions/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
