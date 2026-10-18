# Living spec

Seeded by the E2E harness for a run that starts at the release stages (fixture `battleship-salesforce-home`): the stages before release-plan were recorded without doing them, so this file stands for what the spec stage would have left. Source: the request. The product these requirements describe is built and committed in the run's worktree; it has not been deployed to any org.

## Requirements

### R-1 Project root and names

The Salesforce DX project root is this repository: `sfdx-project.json` and `force-app/`, `sourceApiVersion` 68.0. Every Apex class is named `SLBattle...`; the board component is `slBattleBoard`. `SLBattleEngine` is a public class with static methods only.

Acceptance: the project deploys from the repository root and the names are as stated.

### R-2 Metadata the person can open, and nothing else

Besides the Apex classes and the component the project holds only: the Lightning component tab `SLBattle_Board` (it shows `slBattleBoard`), the Lightning app `SLBattle` (standard navigation, containing that tab) and the permission set `SLBattle_Access`, which makes the app visible, the tab Visible and enables the `SLBattleEngine` and `SLBattleController` classes. No custom objects, fields, other permission sets, static resources, triggers, profiles, labels, flows or app pages, and no change to a profile or to another permission set. A new tab is hidden from every user until a permission set grants it, so after the deploy the permission set is assigned to the logged-in user.

Acceptance: the deploy lists only those metadata types; after the assignment the logged-in user opens app `SLBattle` and tab `SLBattle_Board`.

### R-3 The fleet

A game places the standard fleet on a 10x10 grid (rows and columns 0 to 9): `carrier` 5 cells, `battleship` 4, `cruiser` 3, `submarine` 3, `destroyer` 2. Every ship lies straight along one row or one column, entirely inside the grid, and no two ships share a cell.

Acceptance: for any seed the fleet has those names and sizes, is straight, inside the grid and disjoint.

### R-4 Seeded placement

`SLBattleEngine.newGame(Integer seed)` places the fleet at random from the seed. The same seed always gives the same fleet, in any transaction and however many games came before; two different seeds give different fleets.

Acceptance: the same seed twice gives one fleet, two seeds give two.

### R-5 Shots and the game state

`SLBattleEngine.fire(String game, Integer row, Integer col)` returns the game after one shot. A game is a JSON string with at least `shots`, `shipsLeft`, `gameOver` and `lastShot` (`null` in a new game; after a shot `{"row", "col", "result": "miss" | "hit" | "sunk", "ship", "size"}`, where `ship` and `size` are set only on the shot that sinks a ship, and that shot's result is `sunk`, not `hit`). `gameOver` is false until the shot that sinks the last ship.

Acceptance: a miss, a hit, a sink and the game over are reported as stated.

### R-6 Invalid shots and shots after the game

A shot at a cell already fired at, or with a row or a column outside 0 to 9, throws `SLBattleEngine.InvalidShotException`. After the game is over a shot at a cell not yet fired at is a `miss` and `gameOver` stays true.

Acceptance: both kinds of invalid shot throw; the shot after the end is a miss.

### R-7 The controller

`SLBattleController` has `@AuraEnabled public static` methods `newGame(Integer seed)` and `fire(String game, Integer row, Integer col)` returning the game JSON as a `String`; an invalid shot reaches the caller as an `AuraHandledException`.

Acceptance: a whole game of 100 shots played through the controller ends with `gameOver` true.

### R-8 The board

The component `slBattleBoard` renders the 10x10 grid, fires at a cell when a person clicks it, shows hits, misses and sunk ships, the number of shots fired and of ships left, says when the game is over and has a New game button. It calls `SLBattleController`. It never shows a ship cell before it is hit.

Acceptance: a person sees these in the org (a rendered check, not an Apex test).

### R-9 Tests in the org

Apex tests in classes named `SLBattle...Test`, at least 8 test methods in all: the fleet, a miss, a hit, a sink, game over, a shot after game over and both kinds of invalid shot. They run in the org, one test class at a time, with `sf apex run test --target-org de --class-names <TestClass> --synchronous`.

Acceptance: every test class passes in the org.

### R-10 Efficiency

A whole game of 100 shots played through `SLBattleController` (`newGame`, then `fire` at every cell) runs inside one transaction.

Acceptance: the whole-game test passes in the org.

### R-11 The org and credentials

The target is the Salesforce Developer Edition org with alias `de`; `--target-org de` is on every `sf` command that talks to the org. The CLI is already logged in: credentials are never asked for, printed or stored, and `sf org display` is never run.

Acceptance: no command names another org or prints a credential.

### R-12 Delivery

The work is delivered by `sf project deploy start --target-org de`, then the permission set is assigned to the logged-in user with `sf org assign permset --name SLBattle_Access --target-org de`, and the tests pass in the org.

Acceptance: the deploy succeeds with only the allowed metadata types, the assignment exists, the tests pass.

## Non-functional requirements

None beyond R-10. No availability target, no stored data, no schema.

## Retired

None.
