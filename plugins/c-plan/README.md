# C Plan

Resolve ambiguous user prompts by choosing whether to answer now, answer with assumptions, ask 1–2 high-value clarification questions, replan, or stop. Use when the best response depends on hidden intent, audience, scope, constraints, risk, output format, or desired depth.

## Install

Install the `c-plan` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$c-plan:c-plan`; in Claude, invoke `/c-plan:c-plan`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/c-plan/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/c-plan/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/c-plan/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
