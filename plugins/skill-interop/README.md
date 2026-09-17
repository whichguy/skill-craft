# Skill Interop

Use when authoring or reviewing a portable multi-host agent skill (Grok, Claude Code, Codex, Hermes): scaffold a prompt-only skill, make a skill host-agnostic, create skill layout, review skill for interop, or install across hosts. Covers prompt-first design, host matrix, anti-patterns (divergent copies, silent mode fallback, abs symlinks), and script-backed CLI contracts.

## Install

Install the `skill-interop` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$skill-interop` for a matching request. Read [SKILL.md](skills/skill-interop/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/skill-interop/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/skill-interop/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
