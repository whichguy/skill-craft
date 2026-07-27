---
name: architect
description: |
  Design system architecture and make technology decisions. Dispatches to system-architect
  agent for comprehensive design work.

  AUTOMATICALLY INVOKE when:
  - "design architecture", "what tech stack", "system design"
  - "how should I structure", "architecture for", "design system"
  - "technology recommendation", "compare frameworks"

  NOT for: Implementation (use superpowers:executing-plans), task breakdown (use superpowers:writing-plans)
allowed-tools: all
---

# /architect — Architecture & Technology Decisions

Design system architecture, evaluate technology options, and make informed
stack decisions. Quick comparisons inline; full designs via agent.

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

After building the comparison table, present the recommendation using AskUserQuestion
with markdown previews so the user can visually compare options:

```
AskUserQuestion({
  questions: [{
    question: "Which option fits your project best?",
    header: "Architecture",
    options: [
      {
        label: "[Option A] (Recommended)",
        description: "[1-line rationale tied to project context]",
        markdown: "[Full comparison table for Option A:\n| Criterion | Rating |\n|---|---|\n| Fits stack | ... |\n| Performance | ... |]"
      },
      {
        label: "[Option B]",
        description: "[1-line rationale]",
        markdown: "[Full comparison table for Option B]"
      }
    ],
    multiSelect: false
  }]
})
```

This enables side-by-side comparison in the Claude Code UI when the user focuses each option.

## Step 2b — Agent Dispatch

```
Use the Agent tool:
  subagent_type: "system-architect"
  prompt: "Design architecture for: [question].
           Existing codebase context: [patterns found].
           Constraints: [context].
           Provide implementation blueprint with specific files, components, and data flows."
```

The system-architect agent may internally spawn recommend-tech for technology evaluation.

## Step 3 — Post-Processing

After design completes:
- Summarize key decisions and rationale
- List files that would be created/modified
- Suggest next step: superpowers:writing-plans to break down, then superpowers:executing-plans to implement
