# node-base (fixture, digest in cases.json): facts a baseline scoped to the user-listing request must hold

Hand-compiled from the code on 2026-10-28; never shown to a subject.

| ID | Fact | Evidence | Why it matters to the request |
|---|---|---|---|
| E1 | `GET /users` answers 200 with a JSON array of every user (id, name, email) in id order; query parameters are ignored (the route matches the path only). The HTTP route has no test; the store's `listUsers` has one. | `src/server.js` `createServer`; `src/users.js` `listUsers`; `test/users.test.js` "listUsers returns every user" | pass-to-pass: the request keeps this answer when `page` and `size` are absent |
| E2 | `GET /users/<digits>` answers 200 with the user object, or 404 `{"error": "not found"}`; a non-digit id is 404. | `src/server.js` `createServer`; `test/server.test.js` "GET /users/:id returns the user or 404" | pass-to-pass |
| E3 | Every other method or path answers 404 `{"error": "not found"}`; every response is JSON with `content-type: application/json`. | `src/server.js` `send` | the new 400 errors should follow the `{error}` shape |
| E4 | `npm start` listens on `PORT` (default 3000) only when run directly; `createServer` is exported without listening. | `src/server.js`; `package.json` scripts | tests start the server on port 0 |
| E5 | `paginate(items, page, size)` is 1-based and validates its arguments, but counts `pages = floor(length / size)`: a partial last page is not counted and its items are not returned. Its one test covers an evenly divided list only. This contradicts the README's "split a list into pages". | `src/paginate.js` `paginate`; `test/paginate.test.js`; `README.md:6` | the request needs a partial last page; reusing the helper as it is ships the `floor-pages` defect |
| E6 | Decisions: no npm dependencies; CommonJS with `'use strict'`; tests with `node:test` run by `npm test`; users in an in-memory array; errors as JSON `{error}`. | `package.json`; `src/*.js`; `README.md` | the change must follow them |
