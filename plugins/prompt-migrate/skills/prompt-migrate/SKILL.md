---
name: prompt-migrate
description: TDD-based prompt migration — given a target agent/skill prompt and a remediation list, writes failing tests first, then updates the prompt to make them pass. Commits remain user-controlled.
version: 0.1.1
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

> **skill-craft port** of the claude-craft planning-suite skill. Host-neutral: use repo-root search instead of Claude plugin paths. SoT: this package under whichguy/skill-craft.


# /prompt-migrate

Migrate a prompt file using TDD. Never leave failing test assertions behind after a completed
migration. Version-control actions remain outside this skill unless the user asks for them.

## Invocation

```
/prompt-migrate <path-to-prompt-file> [--remediation <audit-output-file>]
```

If `--remediation` is omitted, resolve an installed `prompt-audit` skill through the current
host's skill discovery and use its output. If it is unavailable, perform the documented audit
steps inline, label the result `inline audit`, and do not pretend a sibling skill ran.

## Step 1 — Load remediation list

Read the remediation list. For each CRITICAL or HIGH item, classify it:
- **Test-verifiable** — the change produces a string or structure that a `includes()` or regex check can validate (e.g. new phase row, new section header, new entry count)
- **Prose-only** — the change is wording/terminology with no structural footprint a test can assert

## Step 2 — Read existing tests

Search the target repository's test and fixture directories using the host's available scoped
search. Include every matching test format actually present; do not restrict the search to one
language or assume a sibling checkout.

Read each test file in full.

## Step 3 — Write failing test assertions (test-verifiable items only)

For each test-verifiable CRITICAL/HIGH item, add a focused assertion using the target
repository's existing test style. Before proceeding, detect the target repository's actual test
command from contributor documentation, build configuration, package scripts, and nearby tests;
run the narrowest relevant command and verify the new assertion fails.

Expected: ≥1 failure per test-verifiable item. **Do not commit.**

## Step 4 — Apply prompt changes

For each CRITICAL and HIGH remediation item (both test-verifiable and prose-only), make the corresponding edit to the prompt file. Apply MEDIUM and LOW items if straightforward; skip if risk of unintended side-effects.

## Step 5 — Run tests — confirm green

Run the same discovered target-repository command and confirm the relevant tests are green.

Expected: All green (including the assertions added in Step 3).

If any test still fails, diagnose and fix before proceeding.

## Step 6 — Handoff or optional commit

Report changed files, the detected test command, and its result. Stage or commit changes **only
when the user explicitly requests a commit**. If requested, include the prompt and its related
tests in the same reviewable change, but never create a commit merely because this skill ran.
