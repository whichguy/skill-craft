# Architecture

How the Battleship contract in `docs/shiploop/spec.md` is built. Seeded by the E2E harness for a run that starts at the release stages: the stages before release-plan were recorded without doing them. The product is committed in the run's worktree and has not been deployed.

## Stack

Apex and one Lightning web component on a Salesforce Developer Edition org, API 68.0. The org compiles them when they are deployed. There is no Node package, no local Apex compiler and no third-party library. `sfdx-project.json` at the repository root sets `sourceApiVersion` 68.0 and the package directory `force-app`.

## Structure

One unpackaged Salesforce DX tree under `force-app/main/default`:

- `classes/SLBattleEngine.cls` owns the rules: placement, shots, the game state and `InvalidShotException`. Public, static methods only.
- `classes/SLBattleController.cls` owns the `@AuraEnabled` entry points. It calls the engine and returns the same JSON string.
- `classes/SLBattleEngineTest.cls` (8 test methods) and `classes/SLBattleGameTest.cls` (2) own the org tests. They are not in the permission set.
- `lwc/slBattleBoard/` owns the grid: one component, no child component.
- `tabs/SLBattle_Board.tab-meta.xml`, `applications/SLBattle.app-meta.xml` and `permissionsets/SLBattle_Access.permissionset-meta.xml` own the visibility for the logged-in user.

## Conventions

Apex classes start with `SLBattle`; the component directory is `slBattleBoard`; test classes match `SLBattle...Test`. Rejected shots are `SLBattleEngine.InvalidShotException`; the controller turns one into an `AuraHandledException`. Every metadata file carries `apiVersion` / `sourceApiVersion` 68.0.

## Interfaces and boundaries

The board and any grader call `SLBattleController.newGame(Integer)` and `fire(String, Integer, Integer)`; both return the game JSON as a `String`. `SLBattleEngine.fire` is called directly for an invalid shot. The engine never calls the controller; the component never calls the engine.

## Real-boundary checks

The Apex tests exist in the org only after a deploy, so they are checked there: each test class is run with `sf apex run test --target-org de --class-names <TestClass> --synchronous --result-format human --code-coverage`, after `sf project deploy start --target-org de`. Owner: system-test and release-verify.

The rendered board (a click shows a miss, a hit, a sunk ship, the counts and the game over line, and New game clears the grid) needs a Lightning session; no Apex test proves it. Owner: a person, at release-verify or handoff.

## Decisions

### AD-1 Stateless game JSON

The game is a JSON string the caller keeps; every method parses the string it is given and returns a new one, so nothing is static state. Why: the same seed gives the same fleet in any transaction, and the controller needs no stored record. Alternatives: a custom object (forbidden by R-2), static variables (lost between transactions). Status: accepted.

### AD-2 Rules in Apex, view in the browser

The rules live in `SLBattleEngine`; the component renders what the controller returns. Why: the rules are tested in the org without a browser. Status: accepted.

### AD-3 A small seeded generator

Apex has no seeded random number generator, so placement uses a Park-Miller generator (multiplier 48271, modulus 2^31 - 1) seeded from the request's seed. Why: the same seed must always give the same fleet. Alternatives: `Crypto.getRandomInteger` (not seedable). Status: accepted.

### AD-4 A permission set grants the board

The app, the tab and the two classes are granted by the permission set `SLBattle_Access`, assigned to the logged-in user after the deploy. Why: a new tab is hidden from every user until a permission set or profile grants it, and profiles and other permission sets stay untouched (R-2). Status: accepted.

## Superseded

None.
