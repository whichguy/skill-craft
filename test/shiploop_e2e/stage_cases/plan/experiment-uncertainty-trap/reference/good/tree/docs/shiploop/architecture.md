# Architecture

## Stack
- Node.js CommonJS, zero dependencies.

## Decisions

### AD-1
Keep zero external npm dependencies and preserve CommonJS module structure.

### AD-2
Invoke `tools/export-engine.js` with `--format ndjson --escape-newlines` in batches of at most 25 records per invocation, based on isolated probe evidence in `RUN/experiments/exp-export-engine/`.
