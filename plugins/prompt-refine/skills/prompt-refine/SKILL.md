---
name: prompt-refine
description: Full prompt-improvement workflow — runs prompt-audit to find inconsistencies, presents a remediation plan, then runs prompt-migrate to apply fixes and prompt-align to verify harness consistency. Use for any agent or skill prompt that needs structural repair.
version: 0.1.2
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

Resolve an installed `prompt-audit` skill through current-host discovery. If it is available,
use it and read its full output (Q&A, learnings, remediation list). If it is unavailable,
perform its documented audit procedure inline and label the result `inline audit`; do not
assume a personal suite or a sibling filesystem layout.

## Step 2 — Confirm scope with user

Present the CRITICAL and HIGH remediation items. Ask:
> "These are the changes I'll apply. Anything to add, remove, or defer?"

Wait for confirmation before proceeding. If the user defers any items, note them as OUT-OF-SCOPE for this run.

## Step 3 — Migrate

Resolve an installed `prompt-migrate` skill through current-host discovery and use it only for
the confirmed items. If it is unavailable, follow its documented TDD procedure inline and
label that route. In either route, detect the target repository's actual test command before
running tests.

## Step 4 — Align

Resolve an installed `prompt-align` skill through current-host discovery. If any `✗ conflict`
rows remain after migration, fix them inline and rerun alignment. If the sibling is unavailable,
follow its documented comparison procedure inline and label that route.

## Step 5 — Final verification

Run the target repository's actual test command discovered from its documentation, build files,
package scripts, and nearby tests. Run an additional lint or marketplace check only when that
repository documents it. Report a missing test command as a prerequisite rather than inventing
one.

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

Stage or commit the result **only when the user explicitly requests a commit**. A successful
refinement run does not authorize a version-control mutation by itself.
