---
name: sample-skill
description: >-
  Use when exercising install --from / portable skill fixture paths in tests.
  Minimal frozen sample for multi-host symlink install coverage.
version: 0.1.0
author: backchain test fixture
license: MIT
platforms:
  - linux
  - macos
---

# sample-skill

Minimal frozen skill fixture for install and interop tests.

## Triggers

- When tests need a portable skill package outside `skills/`
- When verifying `--from DIR` multi-host install

## Procedure

1. Load `prompts/main.prompt.md` and fill `{{INPUT}}`.
2. Run the filled prompt on the current host.
3. Label outputs honestly; never silent empty success.

Host matrix: `references/host-matrix.md`.

## Not for

Production operator workflows — this is a test fixture only.
