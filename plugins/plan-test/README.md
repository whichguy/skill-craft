# Plan Test

Generate comprehensive tests for code. Uses an inline strategy or an available independent test specialist for complex components.

## Install

Install the `plan-test` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$plan-test` for a matching request. Read [SKILL.md](skills/plan-test/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/plan-test/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/plan-test/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
