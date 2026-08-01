---
name: prompt-align
description: Compare an agent or skill prompt against its test harness skill for phase-model, skip-condition, and wiring consistency. Reports mismatches and identifies which file is authoritative.
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


# /prompt-align

Compare an agent/skill prompt against its test harness. Emit a mismatch report.

## Invocation

```
/prompt-align <path-to-agent-or-skill> [--harness <path-to-harness-skill>]
```

If `--harness` is omitted, search for the harness automatically:

```bash
find "<repo-root>" -name "SKILL.md" | xargs grep -l "test.*<agent-basename>\|<agent-basename>.*test" 2>/dev/null
```

## Step 1 — Read both files

Read the agent/skill file and the harness file in full.

## Step 2 — Extract comparable structures

| Structure | Agent location | Harness location |
|-----------|---------------|-----------------|
| Phase table (IDs + skip conditions) | L0 phase table | Step 4.3 skip table |
| Standard wiring | L1 wiring list | Standard wiring list |
| Phase names | Phase table Subject column | Phase Backlog row labels |

## Step 3 — Compare and emit mismatch report

For each structure, diff the two versions:

```
### Phase table mismatches
| Phase ID | Agent says | Harness says | Verdict |
|----------|-----------|--------------|---------|
| P1 | Research (skip: self-contained) | Research (skip: ## What to do self-contained...) | ✓ equivalent |
| P6 | Tests + fix (skip: docs-only) | Tests + fix (skip: docs-only) | ✓ match |
| ...

### Wiring mismatches
(same table format)

### Phase name mismatches
(same table format)
```

Verdict values: `✓ match`, `✓ equivalent` (same semantics, different wording), `⚠ minor` (semantically close but worth aligning), `✗ conflict` (different behavior implied).

## Step 4 — Authoritative source determination

State which file is authoritative for each conflict and why (usually the agent is authoritative; the harness is the consumer).

## Step 5 — Emit fix list

For each `⚠ minor` or `✗ conflict` row, emit a one-line fix recommendation:
- Which file to change
- The exact string to replace or add
