---
version: 0.1.0
---
Expose one callable coordinator entry point shared with the CLI and a public
delivery request validator. Reject malformed arguments before reserving work;
preserve caller-owned inputs, structured diagnostics, and existing recovery
rules. Document the composable APIs and add concise comments around evidence,
locking and cleanup boundaries.
