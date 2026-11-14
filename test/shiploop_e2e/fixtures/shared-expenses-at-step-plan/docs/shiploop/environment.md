# Environment

## Targets and runtimes
Node v26.12.1 observed via node --version. Local HTTP service and JSON file configured by environment; source checkout receives the final guarded return. Empty repository has no CI or deployment configuration; return triggers no known automation. No remote target requested.

## Commands
node --test is the requested verification. No baseline suite exists in the empty checkout.

## Platform facts
Empty starting repository: no code, conventions, dependencies, docs, or existing consumers to preserve. Use Node built-ins.

## Skills
No repository-local skills or instructions exist.

## Access and accounts
Local process and filesystem only; no remote identity or account required.

## Harnesses and suites
Planned: Node built-in node:test with isolated temporary directories and child processes; setup starts server on an ephemeral port, teardown stops it and removes fixture. R-1 restart and concurrency, R-2 valid and invalid groups, R-3 equal and exact with invalid cases, R-4 balances and ordered settlements, R-5 missing routes, R-6 suite discovery all use HTTP component tests due implementation and test stages. Base is empty and tests must fail before implementation. No remote test target.

## ID convention
TC_1 runtime persistence and concurrency
TC_2 groups
TC_3 expenses
TC_4 balances and settlements
TC_5 missing groups

## Full suite command
Planned, local Node, isolated fixtures; all TC cases, seconds.
```sh
node --test
```

Runner readiness: node --test --help exited 0; no installation needed. Tests and fixture are to be authored in W1. Return has no known automation trigger; local checkout is consumer target.
