# Prompt Refine

Full prompt-improvement workflow — runs prompt-audit to find inconsistencies, presents a remediation plan, then runs prompt-migrate to apply fixes and prompt-align to verify harness consistency. Use for any agent or skill prompt that needs structural repair.

## Install

Install the `prompt-refine` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$prompt-refine:prompt-refine`; in Claude, invoke `/prompt-refine:prompt-refine`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/prompt-refine/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/prompt-refine/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/prompt-refine/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
