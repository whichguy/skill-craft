# ShipLoop

Markdown-authoritative delivery harness. Start or resume once, follow the script's current action packet, and submit its exact completion call until the script reports completion with an HTML achievement report. Use when the user says shiploop, ship the project, or requests a durable delivery loop.

## Install

Install the `shiploop` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$shiploop` for a matching request. Read [SKILL.md](skills/shiploop/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/shiploop/scripts/...`), never from the consumer project's current directory.

## Documentation

This package preserves its authored guide at [skills/shiploop/README.md](skills/shiploop/README.md).

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
