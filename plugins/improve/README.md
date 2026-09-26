# Improve

Use when a repository candidate needs a deliberate review-and-improvement loop: use recent Git history, make warranted changes, run meaningful checks, and repeat until two consecutive passes make no changes, or the first pass completes with no change. Supports a read-only interpretation preview; not a one-off code review.

## Install

Install the `improve` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$improve:improve`; in Claude, invoke `/improve:improve`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/improve/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/improve/scripts/...`), never from the consumer project's current directory.

## Documentation

This package preserves its authored guide at [skills/improve/README.md](skills/improve/README.md).

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
