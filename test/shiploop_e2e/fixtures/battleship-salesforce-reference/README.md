# battleship-salesforce-reference

The known-good answer to the `battleship-salesforce` E2E case (`test/shiploop_e2e/cases.json`): an Apex Battleship engine, its
`@AuraEnabled` controller, Apex tests, a Lightning web component board, a Lightning tab, a Lightning app and the permission set that
grants them, all carrying the case prefix (`SLBattle` / `slBattle`).

**Nothing in this folder is ever shown to a model.** It is the harness's own fixture: the case prompt is all a model sees, and a model's
working directory never contains this folder. Do not copy it into a case workspace, a prompt or a packet.
Known limit: a host with file access could still read it from the checkout; grep the run's commands for
`battleship-salesforce-reference` to see whether one did.

## What it is for

- It is the first thing the real checks (`project`, `deployed`, `tests`, `access`, `rules`) run against, so a wrong oracle, a grader
  script the real Apex compiler refuses, or a permission-set query on a field the org does not have shows up here instead of as a failed
  90-minute model run (`battleship_salesforce.py selftest --reference`; real org: main session only).
- Deployed to the real Developer Edition org and with `SLBattle_Access` assigned (the selftest assigns it), it is a playable board: the
  tab opens at `/lightning/n/SLBattle_Board` and the app is `SL Battleship` in the App Launcher. `--keep` leaves it there.

## Status of the Apex

There is no Apex runtime in this repository, so Salesforce has not compiled or run this Apex. The hermetic suite
(`test/shiploop-e2e-battleship-salesforce.test.py`) holds a Python copy of the engine (the same generator, placement and shot rules,
line for line) and checks, against that copy: the fleet of 200 seeds (names, sizes, straight, inside, no shared cell), that seeds 1 and
2 and the grader's two seeds give different fleets (the reference test asserts the first pair), and that the grader's own anonymous
Apex, translated by the suite's Apex subset, scores the copy 19 of 19. That proves the logic. It does not prove that Apex compiles:
the first real deploy is the proof. If the compiler objects, look first at the places below.

## If the first deploy fails, look first at

1. `SLBattleEngine.cls`: `Long start = seed;` (an Integer widened to a Long), `Math.abs(Long)`, `Math.mod(Long, Long)`,
   `Long.intValue()`, the `do { } while` loop, `List<Object>.contains(Integer)` on a list that `JSON.deserializeUntyped` made, and the
   private inner class `Generator` with public members.
2. `SLBattleController.cls`: `AuraHandledException.setMessage` (the message shows in a test only after it is called).
3. The permission set: element order (alphabetical, as a retrieve writes it), `<hasActivationRequired>`, and whether the org accepts
   `<classAccesses>` for both classes; then the `access` check's three queries (PermissionSet, PermissionSetTabSetting with its
   `Visibility` values, PermissionSetAssignment), which no one has run against a real org yet.
4. The metadata shared with the chess reference: the tab's `<motif>Custom57: Grid</motif>`, the app XML, `apiVersion` /
   `sourceApiVersion` 68.0.
5. A deploy of Apex to a production-type org can require tests and 75% coverage; the ten tests should clear that for both classes.

## Files

```
sfdx-project.json                                         sourceApiVersion 68.0, package directory force-app
force-app/main/default/
  classes/SLBattleEngine.cls                              the rules (public, static methods, InvalidShotException inside)
  classes/SLBattleController.cls                          public with sharing; newGame, fire (@AuraEnabled)
  classes/SLBattleEngineTest.cls                          8 tests: fleet, straightness, seeds, miss, hit and sink, game over, both refusals
  classes/SLBattleGameTest.cls                            2 tests: a whole game through the controller, the AuraHandledException
  classes/*.cls-meta.xml                                  apiVersion 68.0, Active
  lwc/slBattleBoard/slBattleBoard.{html,js,css}           the board: click a cell to fire; hits, misses, sunk ships, counts, New game
  lwc/slBattleBoard/slBattleBoard.js-meta.xml             exposed; target lightning__Tab
  tabs/SLBattle_Board.tab-meta.xml                        Lightning component tab showing slBattleBoard
  applications/SLBattle.app-meta.xml                      Lightning app (Standard nav) holding the tab
  permissionsets/SLBattle_Access.permissionset-meta.xml   the app visible, the tab Visible, both classes enabled
```

No other metadata type exists here, and none may: the case's guard (`sf_guard.py --permission-sets`) and its cleanup allow exactly
ApexClass, LightningComponentBundle, CustomTab, CustomApplication, FlexiPage and PermissionSet, each with the prefix (the request rules
out an app page, so `project` refuses one).

## How the engine works

- A game is the JSON of a map: the five ships (name, size, cells as `row * 10 + col`, hits so far), the cells fired at, `shots`,
  `shipsLeft`, `gameOver` and `lastShot`. Every method parses the string it is given and returns a new one; nothing is static state, so
  the same seed gives the same fleet in any transaction and after any number of earlier games.
- The fleet comes from a Park-Miller generator (multiplier 48271, modulus 2^31 - 1) seeded with `|seed| mod (2^31 - 2) + 1`; each ship in
  fleet order draws across-or-down, then a start cell that keeps it inside the grid, and draws again while it would share a cell.
- `fire` refuses a row or column outside 0 to 9 (or null) and a cell already fired at with `InvalidShotException`, then records the shot:
  `sunk` when it hits the last unhit cell of a ship (with that ship's name and size), `hit` for any other ship cell, `miss` otherwise.
  `gameOver` is true once no ship is afloat, and a later shot at water is a plain `miss`.
