---
name: architect
description: |
  Design system architecture and make technology decisions. Uses a structured inline
  design or an available independent reviewer for comprehensive work.

  AUTOMATICALLY INVOKE when:
  - "design architecture", "what tech stack", "system design"
  - "how should I structure", "architecture for", "design system"
  - "technology recommendation", "compare frameworks"

  NOT for: Direct implementation or a routine task breakdown.
version: 0.1.2
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

# /architect — Architecture & Technology Decisions

Design system architecture, evaluate technology options, and make informed
stack decisions. Quick comparisons stay inline; comprehensive designs use an
available independent review capability when it adds material value.

## Step 0 — Parse Arguments

From the invocation args, extract:
- **question**: The architecture question or design request
- **scope**: "compare" (A vs B), "design" (full architecture), or "evaluate" (tech research)
- **context**: Project constraints, existing stack, team preferences

## Step 1 — Triage

**Fast path** (inline comparison):
- Quick "X or Y?" technology comparison
- Single architecture question with clear constraints
- Proceed to Step 2a

**Agent path** (full design):
- Comprehensive system design request
- Multi-component architecture
- Technology evaluation requiring deep research
- Proceed to Step 2b

## Step 2a — Inline Comparison

1. Scan the existing codebase for current patterns:
   - Package.json / requirements.txt for dependencies
   - Existing frameworks and conventions
   - Project structure and module organization
2. Present a structured comparison:

```
## [Option A] vs [Option B]

| Criterion        | Option A | Option B |
|-----------------|----------|----------|
| Fits existing stack | ... | ... |
| Learning curve   | ... | ... |
| Performance      | ... | ... |
| Maintenance      | ... | ... |

**Recommendation**: [choice] because [reason tied to project context]
```

After the table, state the recommendation and its decisive trade-off. If a user choice is
needed, ask it in ordinary conversation with the same concise option labels; do not require
a host-specific question UI.

## Step 2b — Capability-Assisted Design

If the host exposes an **available independent architecture reviewer** and a second
analysis would materially improve the decision, give it this bounded task:

```text
Design architecture for: [question].
Existing codebase context: [patterns found].
Constraints: [context].
Return an implementation blueprint with specific files, components, data flows,
alternatives, and unresolved assumptions.
```

Otherwise perform that same structured analysis inline and label it `single-pass analysis`.
Do not invent an agent name, model, or tool that the current host has not advertised.

## Step 3 — Post-Processing

After design completes:
- Summarize key decisions and rationale
- List files that would be created/modified
- Suggest the next user-approved planning or implementation step
