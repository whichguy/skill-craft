# Environment

Seeded by the E2E harness; discovery did not run.

## Commands

```sh
node scripts/deploy.js && node --test
```

## Harnesses and suites

node:test, run against the deployed target (test/deployed.js loads modules from it). Risk noted during strategy: the
deployed target keeps state between commands, because a deploy copies files over what is there and removes nothing, so
code an earlier step deployed is still on the target when a later command runs.
