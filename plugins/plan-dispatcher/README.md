# Plan Dispatcher

Use when executing or resuming an agreed dependency graph with one main dispatcher and parallel native workers: claim ready steps, preserve launch state, collect result evidence, verify outcomes, and identify successors. Planning belongs to Backchain or the caller; this skill executes the plan.

## Install

Install the `plan-dispatcher` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$plan-dispatcher:plan-dispatcher`; in Claude, invoke `/plan-dispatcher:plan-dispatcher`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/plan-dispatcher/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/plan-dispatcher/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/plan-dispatcher/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
