# Environment

Seeded by the E2E harness for a run that starts at the release stages: discovery did not run, so this file holds what the request and the repository say. Revalidate the org alias before the first deploy.

## Targets and runtimes

- Delivery target: the Salesforce Developer Edition org with Salesforce CLI alias `de`. Nothing from this product is deployed to it by the stages already recorded.
- Runtime: Apex and Lightning Web Components on that org. No local Node package and no local Apex compiler; the org compiles a deploy.
- The product is committed in this run's worktree. The original checkout does not hold it until the workspace return, which is a separate step from the deploy.
- API version: 68.0 (`sfdx-project.json`).

## Commands

- CLI: `sf version`.
- Org identity, without a token: `sf org list`. Never `sf org display`.
- Deploy, from the repository root: `sf project deploy start --target-org de`.
- Dry run of the same deploy: `sf project deploy validate --target-org de --source-dir force-app` (the CLI refuses the command without one of `--manifest`, `--metadata`, `--metadata-dir` or `--source-dir`).
- Permission grant, after the deploy: `sf org assign permset --name SLBattle_Access --target-org de`. A repeat reports a duplicate assignment, which is acceptable when the grant is already in place.
- Apex tests, one class per invocation (a synchronous run takes one class):

```sh
sf apex run test --target-org de --class-names SLBattleEngineTest --synchronous --result-format human --code-coverage
```

```sh
sf apex run test --target-org de --class-names SLBattleGameTest --synchronous --result-format human --code-coverage
```

- Read-only org query: `sf data query --target-org de --query "SELECT Name FROM ApexClass WHERE Name LIKE 'SLBattle%'" --use-tooling-api`.

## Skills

none. The repository has no skill directory.

## Harnesses and suites

Org-resident Apex tests, run with the Salesforce CLI (`sf apex run test`) against org `de`. The classes exist in the org only after the deploy; before it the commands above fail because the class is absent, which says nothing about the product.

- `SLBattleEngineTest`, 8 methods: the fleet, straightness, the seeds, a miss, a hit and a sink, the end of the game and both refusals.
- `SLBattleGameTest`, 2 methods: a whole game of 100 shots through the controller, and the controller's `AuraHandledException`.

System catalog:

| Case ID | Phase | Requirement | Expected outcome | Where | Owner |
| --- | --- | --- | --- | --- | --- |
| SYS-ORG-SUITE | after the deploy | R-3 to R-7, R-9, R-10 | both test classes pass, 10 methods in all | org `de` | release-verify |
| SYS-ACCESS | after the deploy and the assignment | R-2 | the permission set `SLBattle_Access` is assigned to the logged-in user | org `de` | release-verify |
| SYS-BOARD | after the assignment | R-8 | a person sees the rendered board | a Lightning session | a person, at handoff |

## ID convention

A test ID is an Apex test method name. The IDs already taken: `grep -h "static void" force-app/main/default/classes/SLBattle*Test.cls`.

## Access and accounts

The CLI is already logged in; credentials are never asked for, printed or stored. The request grants, for alias `de` only: deploying this project's metadata (`sf project deploy start`, `sf project deploy validate`), assigning `SLBattle_Access` to the logged-in user (`sf org assign permset`), reading the org (`sf org list`, `sf data query`) and running the Apex tests. Not granted: deleting or unassigning anything, `sf org open`, `sf org display`, changing a profile or another permission set, any other org.

## Platform facts

- The permission set must be assigned for the tab to be visible to the logged-in user.
- A synchronous test run takes one class; `--class-names` and `--tests` cannot be combined.
