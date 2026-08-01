---
name: prompt-refine
description: Full prompt-improvement workflow — runs prompt-audit to find inconsistencies, presents a remediation plan, then runs prompt-migrate to apply fixes and prompt-align to verify harness consistency. Use for any agent or skill prompt that needs structural repair.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

> **skill-craft port** of the claude-craft planning-suite skill. Host-neutral: use repo-root search instead of Claude plugin paths. SoT: this package under whichguy/skill-craft.


# /prompt-refine

End-to-end prompt improvement: audit → plan → migrate → align.

## Invocation

```
/prompt-refine <path-to-prompt-file>
```

## Step 1 — Audit

Invoke `/prompt-audit <path-to-prompt-file>`. Read its full output (Q&A, learnings, remediation list).

## Step 2 — Confirm scope with user

Present the CRITICAL and HIGH remediation items. Ask:
> "These are the changes I'll apply. Anything to add, remove, or defer?"

Wait for confirmation before proceeding. If the user defers any items, note them as OUT-OF-SCOPE for this run.

## Step 3 — Migrate

Invoke `/prompt-migrate <path-to-prompt-file> --remediation <audit-output>` using only the confirmed items.

## Step 4 — Align

Invoke `/prompt-align <path-to-prompt-file>`. If any `✗ conflict` rows remain after migration, fix them inline (they were missed by the migrate step) and commit:

```bash
git -C "<repo-root>/.." add <files>
git -C "<repo-root>/.." commit -m "fix(<scope>): align harness after prompt migration"
```

## Step 5 — Final verification

```bash
cd "<repo-root>/.." && npm test && ./tools/lint-marketplace.sh
```

Expected: All green.

## Step 6 — Summary

Emit:
```
## Prompt-refine summary
Target: <file>
Audit findings: <N CRITICAL, M HIGH, K MEDIUM, J LOW>
Applied: <N CRITICAL, M HIGH> (<K MEDIUM if any>)
Deferred: <items>
Test result: PASS
Harness alignment: clean | <N conflicts fixed>
```
