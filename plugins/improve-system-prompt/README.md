# Improve System Prompt

Benchmark and compare system prompt variants (V2/V2a/V2b/V2c) for Sheets Chat by running test scenarios through the real GAS-side ClaudeConversation pipeline. Tests both system-placement and user-placement, then evaluates with heuristic scoring (ABTestHarness) and LLM-as-judge. Product-specific: requires an authorized Sheets Chat/GAS execution integration.

## Install

Install the `improve-system-prompt` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Ask the host to use `$improve-system-prompt` for a matching request. Read [SKILL.md](skills/improve-system-prompt/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `prompt-only` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/improve-system-prompt/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/improve-system-prompt/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
