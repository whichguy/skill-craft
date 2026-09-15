# Review Coverage

Add a post-ship improve-to-exhaustion directive to a plan, or run that directive after implementation. Invoke like any skill: /review-coverage, "review-coverage on this plan", residual×2 after ship, or ensure the plan has a /goal-ready ## Review Coverage section. Not for pre-exit plan quality (use review-plan) or raw residual×2 engine mechanics alone (use review-converge under /goal).

## Install

Install the `review-coverage` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$review-coverage` for a matching request. Read [SKILL.md](skills/review-coverage/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/review-coverage/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/review-coverage/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
