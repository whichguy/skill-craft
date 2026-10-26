# Environment

## Targets and runtimes

Local only: Node.js 20 or later (CommonJS), no network and no deployment target. Fact: `node --version` prints v20 or later.

## Commands

```sh
npm test                                              # node --test: the whole suite
node --test --test-reporter=spec test/chess.test.js   # one file
```

## Harnesses and suites

- Harness: Node's built-in `node:test` with `node:assert/strict`; no test dependency.
- Focused suite: `node --test --test-reporter=spec test/chess.test.js`.
- Regression suite: `node --test`.
- NFR-1 timing runs inside a test with `process.hrtime.bigint()`.

## ID convention

Requirements R-<n> and NFR-<n>; test cases TC-<n>.
