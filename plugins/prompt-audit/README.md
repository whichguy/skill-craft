# Prompt Audit

Audit an agent or skill prompt file for internal inconsistencies (phase numbering, behavioral contracts, terminology, stale references). Produces a Q&A with info-gain scores, a learnings section, and a remediation list. Use before any prompt migration.

## Install

Install the `prompt-audit` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$prompt-audit` for a matching request. Read [SKILL.md](skills/prompt-audit/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/prompt-audit/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/prompt-audit/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
