---
bump: minor
---
- **The script-owned lint pass applies more fixes itself, instead of leaving them for the model or for Improve to
  redo by hand:** prettier, black and gofmt now apply their fix exactly like ruff already does — journal-first,
  only on lines the work item changed, sha256-checked before writing — rather than only reporting what they would
  rewrite. A path more than one fixable tool matches (for example a `.py` file both ruff and black touch) gets
  each tool's fix applied in the catalog's listed order, one tool to completion before the next starts, and the
  pending journal still records exactly one entry per path.
- **The catalog gains five more languages:** clang-format (C/C++/Obj-C) and `terraform fmt` apply fixes the same
  way; ktlint (Kotlin), phpcs (PHP) and rubocop (Ruby) report findings, since this round found no confirmed way to
  apply their fix safely without mutating a file directly. Rust, Dockerfile, C#/.NET, Java and SQL are
  deliberately left out, each for a specific, checked reason recorded in `lint-catalog.md`.
