## Use cases

### U-1: An operator starts the HTTP server to make the game available
Flow: Run `node server.js` with Node.js available. With `PORT` set to an available TCP port number, reach the game on that port. With `PORT` unset, the server uses port 3000. No npm installation is needed.
Source: request

### U-2: A player opens the game to find and sink the computer's fleet
Flow: Open `GET /` in a browser to see the page titled "Battleship". Fire at squares on the 10×10 grid, use the shot feedback to continue playing, then see that the game is complete when the last ship sinks.
Source: request

### U-3: An API caller starts a round to submit shots against it
Flow: Send `GET /api/new` and read the game id from the JSON response. For each shot, send `POST /api/fire` with JSON `{"game": id, "row": r, "col": c}`, using that id and a square's coordinates. Read `"result"` as `"miss"`, `"hit"` or `"sunk"`. The response for the final sink has `"gameOver": true`.
Source: request

### U-4: A maintainer runs the game-rule tests to verify gameplay
Flow: From the repository root, run `node --test` to run the `node:test` tests under `test/` covering the rules in the module the server uses.
Source: request

## Clauses

### C-1: The HTTP game runs in Node.js without npm dependencies
Observable: With Node.js available in a checkout without installed npm packages, run `node server.js` and reach the game over HTTP.
Source: request

### C-2: server.js starts the HTTP server on the port specified by PORT
Observable: Set `PORT` to an available TCP port number and run `node server.js`. `GET /` is reachable on that port.
Source: request

### C-3: server.js defaults to port 3000 when PORT is unset
Observable: Start `node server.js` with `PORT` absent from the environment. With port 3000 available, the game is reachable on that port.
Source: request

### C-4: GET / serves the game page as HTML
Observable: Request `GET /` and open the response in a browser to see the game page.
Source: request

### C-5: The game page is titled "Battleship"
Observable: Open `/` in a browser and read "Battleship" as the page title.
Source: request

### C-6: The player targets a grid of 10 rows by 10 columns
Observable: Open the game page and count 10 rows and 10 columns of target squares.
Source: request

### C-7: The player fires at a chosen square from the game page
Observable: Open the game page, use its controls to aim at a square and fire, then observe the outcome for that square.
Source: request

### C-8: The computer places the fleet for each new game
Observable: Start a game and fire without choosing any ship positions. The fleet can be sunk using shots on the 10×10 board.
Source: request
Open: The requester decides fleet composition and placement rules, including ship counts, ship lengths, spacing and how placement varies between games.

### C-9: The game page keeps unhit ship positions hidden during play
Observable: Open the page before firing and play a series of shots. Unhit ship squares are not revealed by the page while the game is in progress.
Source: implied: U-2 asks the player to find a computer-placed fleet by firing at its grid

### C-10: The game page gives the player visible shot feedback
Observable: Fire at water and at a ship square. The page lets the player tell a miss from a shot that hit a ship.
Source: implied: U-2 requires feedback the player can use to find and sink the fleet

### C-11: The game page shows when the fleet has been sunk
Observable: Fire the shot that sinks the last afloat ship and see that the game is complete.
Source: implied: U-2 ends when all ships are sunk

### C-12: GET /api/new starts a fresh game
Observable: After firing in one game, issue `GET /api/new`. The game it starts has no prior shots recorded.
Source: request

### C-13: GET /api/new returns a game id as JSON
Observable: Parse the response to `GET /api/new` as JSON and use the id it provides as the `"game"` value in a shot request for the new game.
Source: request
Open: The requester decides the JSON representation of the id, including its value type and whether it appears in a named response field.

### C-14: POST /api/fire targets the game identified by the JSON game value
Observable: With a playable game id, send a shot using that id as `"game"`. If another game is playable, its shot state is unaffected. An unrecognized or retired id cannot apply the shot to a different game.
Source: implied: U-3 passes the id returned by the game creation request to identify the target game
Open: The requester decides when a game id ceases to be playable, including whether a new game retires an earlier one, and what response callers see when an id has no playable game.

### C-15: POST /api/fire uses the JSON row and col values to target one square on the 10×10 board
Observable: Send `{"game": id, "row": r, "col": c}` with coordinates addressing a board square. The shot applies to that square, including squares in the first and last rows and columns. A row or column that addresses no square cannot change the game's shot state.
Source: request
Open: The requester decides the API coordinate convention, including the numeric values for the first and last row or column, and the response for coordinates outside the board.

### C-16: A first shot at an empty square returns a miss
Observable: Fire at an untried square that contains no ship. The response is JSON with `"result": "miss"`.
Source: request

### C-17: A first shot at a ship square returns a hit when the ship still has unhit squares
Observable: Fire at an unhit ship square while at least one other square of that ship remains unhit. The response is JSON with `"result": "hit"`.
Source: request

### C-18: A first shot at the final unhit square of a ship returns sunk
Observable: Fire at a ship's only remaining unhit square. The response is JSON with `"result": "sunk"`.
Source: request

### C-19: A hit counts toward sinking its ship on later turns of the same game
Observable: Hit the squares of a ship across separate requests using the same game id. Hitting its last unhit square sinks the ship without requiring another shot at any of its previously hit squares.
Source: implied: U-3 reports whether each new shot hits or sinks a ship based on the game's earlier shots

### C-20: Repeating a shot at the same square adds no damage
Observable: Compare the effect of one shot at a square with the effect of multiple requests for that square in the same game, including overlapping requests. The repeats do not create extra hits or cause another ship to sink.
Source: implied: C-18 depends on which squares of the ship have been hit
Open: The requester decides how the API reports a repeated shot, including whether it returns a shot result or refuses the repeat.

### C-21: A shot result reports whether all ships are sunk
Observable: Read `"gameOver": false` in the JSON response while at least one ship remains afloat. Read `"gameOver": true` in the response when a shot sinks the last ship, or in any shot result after that.
Source: request
Open: The requester decides whether the API accepts further shots after game over and what callers see if the game refuses them.

### C-22: The HTTP server uses a game-rules module to resolve play
Observable: Inspect the server's source and trace game creation and shot resolution to the module that supplies the game rules.
Source: request

### C-23: The game rules have node:test coverage under test/
Observable: Inspect the tests under `test/` and see that they use `node:test` to exercise the game rules.
Source: request

### C-24: node --test runs the game-rule tests
Observable: Run `node --test` from the repository root and see the tests under `test/` run and pass.
Source: request
