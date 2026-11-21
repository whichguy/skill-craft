## On the starting project

- Existing clauses whose tests fail: none. The specification has no clauses sourced from existing behavior.
- Other clauses whose tests pass: none. All 28 mapped commands printed their item IDs and exited 1. C-1 through C-22 and U-1 through U-3 reported the missing HTTP game. C-23 reported missing game-rule coverage. C-24 and U-4 reported zero discovered cases under `test/`.

## Assumed

- The browser driver uses the macOS host's WebKit and Clang. It locates the plan's board controls by their rendered positions and recognizes common completion cues in visible text.
- The rules module probes recognize public creation results that expose a board as a square array, flat array, or map using common empty-cell and ship identifiers. Other layouts use HTTP sweeps, which give less precise evidence about individual ships.
- The adapter tries the plan's zero-based API coordinates first and also recognizes conventional one-based integer coordinates. It probes the planned JSON id field, other named fields, and a bare JSON id.

## Discoveries

- An incomplete shot request leaves the round unchanged even if the bytes received so far form valid JSON | Observable: Send a valid shot body with a larger Content-Length, disconnect, and then verify that the targeted square still needs a shot. | Why: A server can parse a complete JSON value before the HTTP request has finished.
