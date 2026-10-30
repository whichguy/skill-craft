# document W1/S1 notes

Changed public behaviour: GET /health (200, {"ok":true}, application/json). Observed with `PORT=4123 node src/server.js`
and curl: exact GET /health and /health?x=1 answer 200; /health/, POST /health and HEAD /health answer 404
{"error":"not found"} (404 with content-type application/json, not 405). /users, /users/1, /users/42 and an unknown
path answer as before. Without PORT the server printed `listening on 3000` and /health answered 200 on port 3000.

Documents changed and reread after the last edit: README.md (new "Running the server" section, route table, example,
caveats; the file list line for src/server.js), src/server.js (one-line JSDoc on createServer now names GET /health),
docs/shiploop/spec.md (R-1, R-2 lines), docs/shiploop/environment.md (commands). The README example was run again after
the edit: the same 200 / content-type / body. The route table rows were each run again.

docs/shiploop/architecture.md: unchanged. The health route is a branch in the existing createServer handler using node:http
only, so it follows AD-1 and the Structure/Conventions already recorded; no service choice and no departure.

Gap noticed, not fixed (outside this item, and no later work item exists to carry it): test/server.test.js has no HTTP test
for GET /users (only /users/:id and, new, /health), though R-2 names it. R-2's check is `npm test` exit 0, which passes.

Tooling fact: `pkill -f 'node src/server.js'` was refused by the host permission classifier; a server started by this run
was stopped by its own PID (`kill $!`, or the PID `lsof -ti tcp:<port> -sTCP:LISTEN` names).
Scratch logs: RUN/scratch/*.log.
