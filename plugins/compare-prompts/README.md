# Compare Prompts

Compare two prompt versions (A vs B) by running both against a directory of test input files, then evaluating results on three dimensions in priority order: quality > tokens > time.

## Install

Install the `compare-prompts` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$compare-prompts:compare-prompts`; in Claude, invoke `/compare-prompts:compare-prompts`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/compare-prompts/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/compare-prompts/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/compare-prompts/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
