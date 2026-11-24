# Environment

## Targets and runtimes
- Local Node.js (`>=20`, CommonJS, zero npm dependencies).

## Commands
- `node --test` (passes baseline suite: 4 test files).
- `node tools/export-engine.js --help` (legacy export CLI present in repo; exact runtime limits and newline behaviour not yet probed).

## Harnesses and suites
- Unit and integration tests use `node --test`.
