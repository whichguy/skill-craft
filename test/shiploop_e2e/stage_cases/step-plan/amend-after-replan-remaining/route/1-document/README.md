# node-base

A small Node.js project with no dependencies.

- `src/strings.js`: text helpers
- `src/paginate.js`: split a list into pages (uses `Math.ceil` for trailing partial pages and validates integer bounds)
- `src/users.js`: an in-memory user store
- `src/server.js`: an HTTP server (`node:http`) that serves the users

Run the tests with `npm test`, which runs `node --test`.
