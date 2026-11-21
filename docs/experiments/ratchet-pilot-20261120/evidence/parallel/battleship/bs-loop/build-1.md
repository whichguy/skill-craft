## Done

- C-1–C-3, C-22. Added a dependency-free Node HTTP server that uses `game.js` for fleet placement and shot resolution. It listens on the configured `PORT` or defaults to `3000`.
- C-4–C-7, C-9–C-11. Served the Battleship page with 100 labeled target squares, hidden ship locations, visible shot feedback, and a persistent victory message.
- C-8, C-12–C-15. Generated a fleet for each new round. The creation endpoint returns a game id, and the shot endpoint resolves the supplied coordinates against that round.
- C-16–C-21. Implemented misses, accumulated hits, sinking, repeat handling, and completion on the last sink.
- C-23–C-24. Added six direct rules tests under `test/` and verified them with `node --test`.
- Added `README.md` with startup, gameplay, API, and test instructions.

Verified the unset `PORT` branch with a listener stub and ran full HTTP rounds on OS-assigned ports. The HTTP checks covered invalid input, an interrupted request body, overlapping shots at a known ship square, round isolation, and the body-size boundary. A WebKit run verified the grid, shot feedback, and recovery of the victory message after a simulated lost winning response.

## Not done

none

## Discoveries

- C-8 build choice. Each round independently draws legal horizontal or vertical placements for ships of lengths 5, 4, 3, 3, and 2. Ships may touch and cannot overlap. | Observable: Sweep a new board and count 17 occupied squares and five sinks. The rules tests inspect generated placements. | Why: Enumerating legal placements keeps generation bounded and gives each ship its own damage count even when ships touch.
- C-13 build choice. Creation returns an object with an opaque UUID string in `game`. | Observable: Pass the `game` value from `GET /api/new` directly to `POST /api/fire`. | Why: The same named field carries the round id in both calls.
- C-14 build choice. Round ids stay valid for the process lifetime. An unknown string id receives JSON `404`. | Observable: Create a second round while the first is active and keep playing either. After restart, an old id returns `404`. | Why: Tabs and API callers can play independently, with one in-memory record retained for every created round.
- C-15 build choice. The shot API accepts integer rows and columns from `0` through `9` and returns JSON `400` for invalid coordinates on a known game. | Observable: Fire at `(0, 0)` and `(9, 9)`. Coordinates of `10`, fractional values, and numeric strings are rejected. | Why: The browser and rules share the same board indices.
- C-20 build choice. Repeats return the square's original result with the current `gameOver` value. | Observable: Revisit a square that first returned `hit` after its ship has sunk. The replay returns `hit` and adds no damage. | Why: A client can recover a lost shot response, including after the round ends.
- C-21 build choice. Completed rounds replay tried squares and return JSON `409` for untried squares. | Observable: Replay the winning square for `sunk` and `gameOver: true`, then try an unused square. | Why: The winning response stays recoverable and the finished board stays fixed.
- Shot request bodies are limited to 8 KiB. Oversized bodies receive JSON `413`. | Observable: Send an otherwise valid shot padded with whitespace to 8,193 bytes. | Why: The server bounds how much shot input it buffers.
- The browser asks the player to retry the same square when a shot response is unavailable. | Observable: Drop a shot response and see the attempted square highlighted until it is retried. | Why: The server may already have applied the shot, including the final sink.
- `PORT=0` asks the OS for a free port, and startup prints the bound port. Invalid port values exit with an error. | Observable: Start with `PORT=0` and read the listening message, or start with `PORT=65536` and see a validation error. | Why: Operators can select a free development port and identify configuration mistakes at startup.
