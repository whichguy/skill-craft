# Improve Agent

Use when Improve should run in a fresh native agent instead of this conversation: start one agent that runs /improve in its own context, keep useful parent work going, then verify and relay its result. For Improve in this conversation, use improve.

## Install

Install the `improve-agent` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$improve-agent:improve-agent`; in Claude, invoke `/improve-agent:improve-agent`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/improve-agent/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/improve-agent/scripts/...`), never from the consumer project's current directory.

## Documentation

This package preserves its authored guide at [skills/improve-agent/README.md](skills/improve-agent/README.md).

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
