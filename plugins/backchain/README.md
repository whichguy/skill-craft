# Backchain

Use when an implementation task needs a dependency-aware plan before coding: backward planner / backchain / precondition-first planning, dependency DAGs, elaborating incomplete plans, or scheduler-ready step graphs. Turns a natural-language coding request into a forward draft then backward-chaining enriched DAG with explicit unresolved risks, then directly calls the selected Until Loop to repeat dependency review until two consecutive trivial/no-change reviews.

## Install

Install the `backchain` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$backchain:backchain`; in Claude, invoke `/backchain:backchain`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/backchain/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/backchain/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/backchain/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
