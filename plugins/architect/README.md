# Architect

Design system architecture and make technology decisions. Uses a structured inline design or an available independent reviewer for comprehensive work.

## Install

Install the `architect` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$architect` for a matching request. Read [SKILL.md](skills/architect/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/architect/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/architect/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
