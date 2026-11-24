# Environment

## Targets and runtimes
- Local Node.js (`>=20`, CommonJS, zero npm dependencies).

## Commands
- `node --test` (baseline suite).
- `node tools/export-v1.js --help` and `node tools/export-v2-stream.js --help` (present; actual runtime caps/modes not yet probed).

## Harnesses and suites
- Unit and integration tests use `node --test`.
