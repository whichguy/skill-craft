# Ask Agent

A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main conversation, and incorporate their results when they return. Use for "ask an agent", named agent roles, parallel delegation, or launch-and-notify work.

## Install

Install the `ask-agent` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$ask-agent` for a matching request. Read [SKILL.md](skills/ask-agent/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/ask-agent/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/ask-agent/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
