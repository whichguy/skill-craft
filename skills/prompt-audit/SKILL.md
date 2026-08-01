---
name: prompt-audit
description: Audit an agent or skill prompt file for internal inconsistencies (phase numbering, behavioral contracts, terminology, stale references). Produces a Q&A with info-gain scores, a learnings section, and a remediation list. Use before any prompt migration.
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


# /prompt-audit

Audit a prompt file for internal inconsistencies. Every finding cites `file:line`.

## Invocation

```
/prompt-audit <path-to-prompt-file>
```

`<path-to-prompt-file>` is a repo-relative path to any `agents/*.md` or `skills/*/SKILL.md`.

## Step 1 — Read target file

Read the full content of `<path-to-prompt-file>` using the Read tool.

## Step 2 — Identify ecosystem files

Search for files that reference the target prompt:

```bash
grep -rn "<prompt-file-basename>" <repo-root>/ --include="*.md" --include="*.js" -l
```

Read each related file (envelope template, test harness skill, test fixtures, test JS file).

## Step 3 — Audit pass

For each dimension below, enumerate findings. Every finding must cite `file:line`.

| Dimension | What to check |
|-----------|--------------|
| Phase model | Phase table ↔ specialist catalog ↔ test harness all use the same phase IDs and numbering |
| Behavioral contracts | Every contract stated in one file (e.g. envelope) is consistent with the agent body |
| Terminology | Terms like "Orchestrator", "cascade", "DISPATCHED" used consistently across the file |
| Stale references | Date literals, commit SHAs, removed section names, deprecated field names |
| Skip conditions | Skip rules in the phase table match skip rules in the test harness |
| Standard wiring | Dependency graph stated in the agent matches the graph in the harness |
| Specialist catalog coverage | Every non-trivial non-inline phase has a catalog entry |

## Step 4 — Q&A with info-gain

For each inconsistency that requires a design decision (not just a mechanical fix), emit:

```
### Q<N> — <short question>

**Info-gain: <0.0–1.0>** — <one sentence explaining what uncertainty this resolves>

**Evidence:**
- <file:line>: <what it says>
- <file:line>: <what it says (contradicting or context)>

**Answer:** <your reasoned answer, citing evidence>
```

Sort questions highest-info-gain first. Pure mechanical fixes (typos, stale dates) go in Step 5 directly without a Q entry.

## Step 5 — Learnings

List non-obvious discoveries that a future prompt author should know:

```
## Learnings
1. <finding> — <why it matters>
```

## Step 6 — Remediation list

Emit a prioritized list of changes needed:

```
## Remediation
| Priority | File | Change |
|----------|------|--------|
| CRITICAL | <file> | <what to fix> |
| HIGH     | <file> | <what to fix> |
| MEDIUM   | <file> | <what to fix> |
| LOW      | <file> | <what to fix> |
```
