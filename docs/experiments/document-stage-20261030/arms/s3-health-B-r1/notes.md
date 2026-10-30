# document W1/S1 notes

Listed: `createServer` in src/server.js (changed), route GET /health (new). `send` is unexported and unchanged: no contract added.
Stale mentions: none listed by the packet. Found by reading: the `createServer` docstring described only the user store, and the README line for src/server.js said it serves the users. Both now name the health route.

Observed (curl against `node src/server.js`, port 4871/4872, and `npm start` on the default port 3000):
- GET /health -> 200, content-type application/json, {"ok":true}
- GET /users -> 200 with three users; GET /users/1 -> 200; GET /users/42 -> 404 {"error":"not found"}
- HEAD and POST on /health, /users and /users/1 -> 404 (POST body {"error":"not found"}; a HEAD answer has no body), never 405; GET /health/ and GET /nope -> 404
- `npm start` with PORT unset prints `listening on 3000`
- `node --test test/server.test.js`: 2 pass; `npm test`: 8 pass, exit 0

Reread after the last edit: README.md (Server section; the curl example ran as written), the `createServer` docstring against the code, docs/shiploop/spec.md, docs/shiploop/environment.md.

No tombstone: the step removed no approach.
Baseline: not applicable, the step adds behaviour and recovers none.
architecture.md unchanged: the route is one more branch in the existing flat handler; no structure, dependency, interface or convention moved, so no AD.
spec.md: one line added inside R-1 (met-by files and TC-1, mark W1/S1). R-1's intent did not move. The HEAD/POST 404 is recorded in the README as a known limit, not in the spec: no requirement asks for it, so a later step may add HEAD without contradicting the spec.
R-2 unchanged: its text is still true and no step line is owed.
