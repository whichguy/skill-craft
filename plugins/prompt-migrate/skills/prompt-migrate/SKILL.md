---
name: prompt-migrate
description: TDD-based prompt migration — given a target agent/skill prompt and a remediation list from prompt-audit, writes failing tests first, then updates the prompt to make them pass, and commits both in a single atomic commit.
---

> **skill-craft port** of the claude-craft planning-suite skill. Host-neutral: use repo-root search instead of Claude plugin paths. SoT: this package under whichguy/skill-craft.


# /prompt-migrate

Migrate a prompt file using TDD. Never commits failing tests without the corresponding prompt fix in the same commit.

## Invocation

```
/prompt-migrate <path-to-prompt-file> [--remediation <audit-output-file>]
```

If `--remediation` is omitted, run `/prompt-audit <path-to-prompt-file>` first and use its output.

## Step 1 — Load remediation list

Read the remediation list. For each CRITICAL or HIGH item, classify it:
- **Test-verifiable** — the change produces a string or structure that a `includes()` or regex check can validate (e.g. new phase row, new section header, new entry count)
- **Prose-only** — the change is wording/terminology with no structural footprint a test can assert

## Step 2 — Read existing tests

```bash
find "<repo-root>/test" -name "*.test.js" | xargs grep -l "<prompt-file-basename>"
```

Read each test file in full.

## Step 3 — Write failing test assertions (test-verifiable items only)

For each test-verifiable CRITICAL/HIGH item, add a new `it(...)` assertion to the appropriate test file. Verify tests fail before proceeding:

```bash
cd "<repo-root>/.." && npm test -- --grep "<suite name>"
```

Expected: ≥1 failure per test-verifiable item. **Do not commit.**

## Step 4 — Apply prompt changes

For each CRITICAL and HIGH remediation item (both test-verifiable and prose-only), make the corresponding edit to the prompt file. Apply MEDIUM and LOW items if straightforward; skip if risk of unintended side-effects.

## Step 5 — Run tests — confirm green

```bash
cd "<repo-root>/.." && npm test -- --grep "<suite name>"
```

Expected: All green (including the assertions added in Step 3).

If any test still fails, diagnose and fix before proceeding.

## Step 6 — Commit test changes and prompt changes together

```bash
git -C "<repo-root>/.." add <test-file(s)> <prompt-file>
git -C "<repo-root>/.." commit -m "<type>(<scope>): <summary of migration>"
```

Never split test changes and prompt changes into separate commits.
