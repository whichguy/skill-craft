# Probes of the shipped Sonnet product (v2180-sonnet-battleship-36036c, HEAD f02ef66)

Run on a `git archive` copy, never the run's worktree. The three defect classes are the ones the per-step baseline
01b9b3 fixed and 491d9a shipped (docs/experiments/e2e-v2170-validation-20261027/probes.md).

## 1. A request target the WHATWG URL parser refuses: fixed by the item review

```
GET '//'         -> HTTP/1.1 404 Not Found; server alive: True
GET 'http://['   -> HTTP/1.1 404 Not Found; server alive: True
GET '/'          -> HTTP/1.1 200 OK; server alive: True
```
`server.js` takes the path with a non-throwing `pathOf` (54d88a3, the implement item review's pass 1, which also
added the `//` case to environment.md's TC-5).

## 2. Unchecked options: absent by design, with one residue

```
createStore({cap: 0}) -> RangeError: cap must be an integer >= 1
createStore({cap: -1}) -> RangeError: cap must be an integer >= 1
createStore({cap: 1.5}) -> RangeError: cap must be an integer >= 1
createStore({cap: "x"}) -> RangeError: cap must be an integer >= 1
createStore({cap: null}) -> RangeError: cap must be an integer >= 1
createStore(5) -> accepted (add,get,size)
createGame({rng: 5}) -> TypeError: opts.rng must be a function returning a number in [0, 1)
createGame(null) -> TypeError: opts must be an object
cap 1 after two adds: first kept? false second kept? true
store.add(42) -> accepted undefined
```
- `createStore` checked `cap` from S1 on (41ace8a, `git blame` lines 122-124), and `createServer()` takes no options. So
  491d9a's `maxGames: 0 / -1` defect has no counterpart.
- Residue: the exported `store.add` takes any value (`add(42)` accepted), and `createStore(5)` is taken as no options.
  01b9b3's S1 review fixed both shapes ("add() rejects a non-game").

## 3. A stale fire reply lands on the new game: shipped

Found by reading `public/index.html`, as in 491d9a:
- `newGame()` does not check `busy`, and New game stays clickable while a shot is in flight.
- `newGame()` resets `shots`, rebuilds the grid and fetches a new game.
- The old `fireAt` reply then still runs `shots += 1` and posts the old game's status text. On `gameOver` it runs
  `setCellsDisabled(true)` on the new board's cells.
- Its final `.then` clears `busy` while the new game's fetch may still be pending.

The item review's pass 2 says it re-read "page behaviour" and found no other defect. 01b9b3's S2 review fixed this
class (b46f76b: fire() remembers its game id and ignores a reply for another game).
