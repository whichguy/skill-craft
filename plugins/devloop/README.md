# DevLoop

DevLoop (default): invoke the autonomous engine for a machine-verifiable build or debug goal. Use when the user says devloop, DevLoop, /devloop, or wants an isolated fail-closed build with executable tests. Thin shim: resolve a preinstalled engine, then exec scripts/devloop-run. Runtime hosts: Grok and Hermes. Claude/Codex/Cursor require an explicit external transport. NOT the demoted offline skill evidence-gates. NOT host-agent DEFINE/PROVE/BUILD.

## Install

Install the `devloop` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$devloop:devloop`; in Claude, invoke `/devloop:devloop`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/devloop/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/devloop/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/devloop/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
