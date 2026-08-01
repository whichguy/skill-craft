---
name: plan-test
description: |
  Generate comprehensive tests for code. Dispatches to qa-analyst agent for complex
  components requiring test architecture decisions.

  AUTOMATICALLY INVOKE when:
  - "write tests", "test this", "generate tests", "add test coverage"
  - "test plan", "what should I test"
  - After feature implementation is complete

  NOT for: Running existing tests (use `npm test`)
argument-hint: "[file-path or function-name]"
allowed-tools: all
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

> **skill-craft port** of a claude-craft suite skill. Host-neutral: use repo-root search instead of Claude plugin paths. SoT: whichguy/skill-craft `skills/plan-test/`.


# /test — Test Generation

Generate tests for specified code. Detects the project's test framework automatically
and matches existing test patterns.

## Step 0 — Parse Arguments

From the invocation args, extract:
- **target**: File path, function name, or component to test
- **--framework**: Override test framework detection (mocha, jest, vitest, pytest)
- **--unit-only**: Skip integration test generation

If no target specified, use recently modified files:
```bash
git diff --name-only HEAD~1
```

## Step 1 — Detect Test Infrastructure

Scan the project for existing test setup:
1. Check package.json for test scripts and dependencies (mocha, jest, vitest, chai)
2. Find existing test files: `Glob("**/*.test.*")` and `Glob("**/*.spec.*")`
3. Read 1-2 existing test files to match style (imports, describe/it patterns, assertion style)
4. Identify test directory convention (test/, __tests__/, co-located)

## Step 2 — Triage

**Fast path** (inline generation):
- Single function or small file (< 100 lines)
- Clear inputs/outputs, no complex dependencies
- Proceed to Step 3a

**Agent path** (dispatch):
- Complex component with multiple methods
- Requires mocking strategy decisions
- Integration tests needed across modules
- Proceed to Step 3b

## Step 3a — Inline Test Generation

1. Read the target file completely
2. Identify testable units: exported functions, public methods, API endpoints
3. Generate tests matching the project's existing style:
   - Happy path for each function
   - Edge cases: empty input, null, boundary values
   - Error cases: invalid input, missing dependencies
4. Write the test file to the conventional location

## Step 3b — Agent Dispatch

```
Use the Agent tool:
  subagent_type: "qa-analyst"
  prompt: "Create a comprehensive test plan and generate tests for: [target].
           Existing test framework: [detected framework].
           Existing test patterns: [patterns found in Step 1].
           Match the project's test style."
```

## Step 4 — Verify

After tests are written:
1. Run the new tests to verify they pass
2. Report coverage if possible
3. List any functions/paths not covered with rationale
