# Evidence Gates

Optional offline evidence gates (freeze/prove/stop with guard digests) for machine-checkable red→green contracts without the autonomous engine. Use when the user says evidence-gates, offline evidence gates, freeze prove stop, or host-native verify gates. NOT the autonomous engine product.

## Install

Install the `evidence-gates` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$evidence-gates` for a matching request. Read [SKILL.md](skills/evidence-gates/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/evidence-gates/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/evidence-gates/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
