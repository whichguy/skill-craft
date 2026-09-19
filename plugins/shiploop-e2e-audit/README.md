# Shiploop E2e Audit

Run the ShipLoop test harness and audit its retained graph, review, test, product and incremental-change evidence. Use for ShipLoop mock checks, live one-shot E2E smoke/full campaigns, or review of existing trial output. Full Google Apps Script and Salesforce game cases require an authorized test deployment and hosted behavior evidence. Includes its harness for source and marketplace installs; tests a separately selected ShipLoop.

## Install

Install the `shiploop-e2e-audit` package from a configured Skill Craft marketplace, then start a fresh host session so it loads the packaged skill.

## Use

Use the installed plugin skill: in Codex, ask for `$shiploop-e2e-audit:shiploop-e2e-audit`; in Claude, invoke `/shiploop-e2e-audit:shiploop-e2e-audit`; in other hosts, select the installed plugin skill. Read [SKILL.md](skills/shiploop-e2e-audit/SKILL.md) before execution; it defines the workflow and any task-specific limits.

## Runtime and prerequisites

This is a `script-backed` skill for linux, macos. Consult the packaged card for its required tools, credentials, filesystem writes, network behavior, and recovery steps. When it invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/shiploop-e2e-audit/scripts/...`), never from the consumer project's current directory.

## Documentation

The packaged [skill instructions](skills/shiploop-e2e-audit/SKILL.md) are the authoritative guide.

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
