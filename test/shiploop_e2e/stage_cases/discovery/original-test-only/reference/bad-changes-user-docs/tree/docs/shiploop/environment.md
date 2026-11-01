# Environment
## Targets and runtimes
Local Node >=22, no dependencies (README.md, package.json); observed v26.12.1. Tests run locally in isolated worktree; deliver new test files to original source checkout. No hosted deployment requested or needed; CI/source return automation unknown, owner maintainer. No platform guide applicable.
## Commands
npm test (node --test), package.json. No documented lint or type checker.
## Platform facts
CommonJS, strict mode, standard library only; HTTP tests use port 0, worker disabled and test/helpers.js (CONTRIBUTING.md, test/helpers.js). Error envelope and actor conventions: docs/api.md; decisions 5–8 govern pagination, outbox, audit and persistence. Product scope is new test files/helpers only.
## Skills
No repository-local skill links found in README.md or CONTRIBUTING.md. ShipLoop selected by user; test design follows node:test examples.
## Access and accounts
Local test process identity; no remote target or credentials required. Consumer is repository maintainer.
