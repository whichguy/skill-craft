# Environment

Seeded by the E2E harness; discovery did not run.

## Targets and runtimes

- Development: this checkout, Node.js with node:test. Delivery: the Apps Script deployment the project is pushed to
  (appsscript.json, V8). Platform guide: GUIDES/platforms/apps-script.md

## Commands

```sh
node scripts/deploy.js && node --test
```

## Harnesses and suites

node:test, run against the deployed copy: test/deployed.js loads the server files from the deployment.
