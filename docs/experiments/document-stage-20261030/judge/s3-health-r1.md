# Scenario s3-health

## Request
S1 In this Node.js project, add a health route to the HTTP server in src/server.js: GET /health answers 200 with the JSON body {"ok":true} and a content-type of application/json. The existing routes must not change. npm test must pass.

## The step's state before the document stage
Implement and test were done; the uncommitted change before documentation was:  M src/server.js,  M test/server.test.js
Earlier results (implement summary, not-covered behaviour, test summary):
# ShipLoop navigator result

```shiploop-state
{
  "outcome": "done",
  "summary": "Added the GET /health branch before the users routes in createServer. Observed with `PORT=4123 npm start` and `curl -si http://127.0.0.1:4123/health`: 200, content-type application/json, body {\"ok\":true}. A HEAD /health request answers 404 because only GET is routed; POST /health also answers 404, not 405.",
  "not_covered": [
    "HEAD /health answers 404 (only GET is routed)"
  ]
}
```

# ShipLoop navigator result

```shiploop-state
{
  "outcome": "done",
  "summary": "TC-1 passes; the existing server test still passes.",
  "commands": [
    {
      "kind": "focused",
      "command": "node --test test/server.test.js",
      "ids": [
        "TC-1"
      ]
    },
    {
      "kind": "full",
      "command": "npm test",
      "ids": []
    }
  ]
}
```

## Reference checklist (what a strong document stage should catch; not exhaustive)
{
 "readme_missing": "README does not say how to start the server, its PORT, or its routes (health included)",
 "caveat": "HEAD /health answers 404 (load balancers often probe with HEAD)",
 "stale_docstring": "createServer's docstring says 'for the user store' only",
 "environment_durable": [
  "npm start",
  "PORT",
  "/health"
 ]
}
## Arm X: diff against the base commit (code, tests and docs)
```diff
diff --git a/README.md b/README.md
index 68ec0ac..b4f3cd3 100644
--- a/README.md
+++ b/README.md
@@ -5,6 +5,27 @@ A small Node.js project with no dependencies.
 - `src/strings.js`: text helpers
 - `src/paginate.js`: split a list into pages
 - `src/users.js`: an in-memory user store
-- `src/server.js`: an HTTP server (`node:http`) that serves the users
+- `src/server.js`: an HTTP server (`node:http`) that serves the users and a health check (see [Server](#server))
 
 Run the tests with `npm test`, which runs `node --test`.
+
+## Server
+
+Start it with `npm start`, which prints `listening on <port>`. It listens on `PORT` (default 3000).
+
+| Route | Answer |
+| --- | --- |
+| `GET /health` | 200, `{"ok":true}` |
+| `GET /users` | 200, every user |
+| `GET /users/:id` | 200 and the user, or 404 `{"error":"not found"}` |
+
+Every answer is `application/json`. Check that it is up:
+
+```sh
+curl -i http://127.0.0.1:3000/health   # HTTP/1.1 200 OK, content-type: application/json, {"ok":true}
+```
+
+Known limit: only `GET` is routed, so `HEAD` and `POST` on any path, `/health` included, answer 404, not 405,
+and a `HEAD /health` probe reads as down.
+
+The requirements are in [docs/shiploop/spec.md](docs/shiploop/spec.md).
diff --git a/docs/shiploop/environment.md b/docs/shiploop/environment.md
index 8b88e1d..01022d4 100644
--- a/docs/shiploop/environment.md
+++ b/docs/shiploop/environment.md
@@ -2,6 +2,9 @@
 
 ## Commands
 - `npm test`: runs `node --test`, every test/*.test.js; exit 0 is a pass.
+- `node --test test/server.test.js`: the server tests alone (TC-1 included); exit 0 is a pass.
+- `PORT=<port> npm start`: runs `node src/server.js`, which prints `listening on <port>` (port 3000 when PORT is unset); stop it by killing the process.
+- `curl -si http://127.0.0.1:<port>/health`: the health check; a healthy server answers `HTTP/1.1 200 OK`, `content-type: application/json` and `{"ok":true}`. Only GET is routed, so `curl -I` (HEAD) answers 404.
 
 ## Harnesses and suites
 - node:test through `node --test`; no other harness.
diff --git a/docs/shiploop/spec.md b/docs/shiploop/spec.md
index 5ce67bc..f56d209 100644
--- a/docs/shiploop/spec.md
+++ b/docs/shiploop/spec.md
@@ -2,6 +2,7 @@
 
 ## R-1 Health route
 GET /health answers 200 with the JSON body {"ok":true} and content-type application/json.
+Met by the `/health` branch of `createServer` in `src/server.js` and TC-1 in `test/server.test.js`. (W1/S1)
 
 ## R-2 Existing routes unchanged
 GET /users and GET /users/:id answer as before; `npm test` passes.
diff --git a/src/server.js b/src/server.js
index bcf2fad..6b4abcd 100644
--- a/src/server.js
+++ b/src/server.js
@@ -8,10 +8,11 @@ function send(res, status, body) {
   res.end(JSON.stringify(body));
 }
 
-/** An HTTP server for the user store; not listening until the caller calls listen(). */
+/** Returns an HTTP server, not yet listening, that serves GET /health, /users and /users/:id as JSON and answers any other method or path 404 {"error":"not found"}. */
 function createServer() {
   return http.createServer((req, res) => {
     const url = new URL(req.url, 'http://localhost');
+    if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { ok: true });
     if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());
     const match = /^\/users\/(\d+)$/.exec(url.pathname);
     if (req.method === 'GET' && match) {
diff --git a/test/server.test.js b/test/server.test.js
index 38f9c89..146daf7 100644
--- a/test/server.test.js
+++ b/test/server.test.js
@@ -22,3 +22,12 @@ test('GET /users/:id returns the user or 404', async () => {
     assert.equal((await fetch(`${base}/users/42`)).status, 404);
   });
 });
+
+test('TC-1 GET /health answers 200 with {"ok":true} as application/json', async () => {
+  await withServer(async (base) => {
+    const res = await fetch(`${base}/health`);
+    assert.equal(res.status, 200);
+    assert.match(res.headers.get('content-type'), /^application\/json/);
+    assert.deepEqual(await res.json(), { ok: true });
+  });
+});

```
## Arm X: result and notes
# ShipLoop navigator result

```shiploop-state
{
  "assumptions": [
    {
      "text": "GET /users has no test: test/server.test.js covers only GET /users/:id, so criterion C2 (existing routes unchanged, proof npm test) cannot fail on a change to GET /users. Observed by hand during document: GET /users answers 200 with three users.",
      "settle": "carry-forward or a later work item adds a GET /users case to test/server.test.js; the /health change itself is one branch placed before the users routes",
      "due_stage": "carry-forward"
    }
  ],
  "headline": "Documented GET /health: createServer contract, README Server section with the health check and the GET-only limit, spec met-by line and environment commands.",
  "knowledge": {
    "architecture": "No change: the health route is one more branch in the existing flat handler; no structure, dependency, interface or convention moved, so no AD-<n>.",
    "environment": "Added three commands under ## Commands: the focused `node --test test/server.test.js`, `PORT=<port> npm start` (default 3000, prints `listening on <port>`) and the health-check curl with its expected answer; all three were run here.",
    "spec": "Added one line inside R-1 naming the files and test that meet it (the /health branch of createServer, TC-1 in test/server.test.js), ending with the mark (W1/S1). R-2 unchanged: still true, and no step line is owed."
  },
  "outcome": "done",
  "summary": "Files changed: src/server.js (createServer docstring only, no code change), README.md (Server section, src/server.js line), docs/shiploop/spec.md, docs/shiploop/environment.md. Decisions: the docstring stays one line per the architecture convention and now lists the three GET routes and the 404 for every other method or path. HEAD and POST answer 404 (not 405) on every route, observed on /health, /users and /users/1; this is documented in the README as a known limit and kept out of the spec because no requirement asks for it. Observed: GET /health, /users, /users/1, /users/42, HEAD and POST variants, `npm start` on the default port, `node --test test/server.test.js` (2 pass) and `npm test` (8 pass, exit 0). Open item: GET /users is untested (see assumptions). Notes: RUN/notes/document.md."
}
```

----- RUN/notes/document.md -----
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

## Arm Y: diff against the base commit (code, tests and docs)
```diff
diff --git a/README.md b/README.md
index 68ec0ac..4562360 100644
--- a/README.md
+++ b/README.md
@@ -5,6 +5,31 @@ A small Node.js project with no dependencies.
 - `src/strings.js`: text helpers
 - `src/paginate.js`: split a list into pages
 - `src/users.js`: an in-memory user store
-- `src/server.js`: an HTTP server (`node:http`) that serves the users
+- `src/server.js`: an HTTP server (`node:http`) that serves the users and `GET /health` (see below)
 
 Run the tests with `npm test`, which runs `node --test`.
+
+## Running the server
+
+`npm start` runs `src/server.js`. It listens on `PORT` (default 3000) and prints `listening on <port>`.
+Every answer is JSON (`content-type: application/json`):
+
+| Request | Answer |
+| --- | --- |
+| `GET /health` | `200` with `{"ok":true}`, for a liveness check |
+| `GET /users` | `200` with the list of users |
+| `GET /users/:id` | `200` with the user, or `404` with `{"error":"not found"}` |
+| any other path or method | `404` with `{"error":"not found"}` |
+
+```sh
+PORT=4123 npm start
+curl -si http://127.0.0.1:4123/health
+# HTTP/1.1 200 OK
+# content-type: application/json
+#
+# {"ok":true}
+```
+
+Only an exact `GET /health` is routed. A query string is ignored, but `/health/`, `HEAD /health` and
+`POST /health` answer `404` (not `405`). The requirement is R-1 in [docs/shiploop/spec.md](docs/shiploop/spec.md);
+its test is `TC-1` in `test/server.test.js`.
diff --git a/docs/shiploop/environment.md b/docs/shiploop/environment.md
index 8b88e1d..85c5866 100644
--- a/docs/shiploop/environment.md
+++ b/docs/shiploop/environment.md
@@ -2,6 +2,8 @@
 
 ## Commands
 - `npm test`: runs `node --test`, every test/*.test.js; exit 0 is a pass.
+- `node --test test/server.test.js`: the focused run; 2 tests, including TC-1 (W1/S1). `npm test` ran 8 tests, all passing (W1/S1).
+- `PORT=4123 npm start`: runs src/server.js in the foreground on that port (default 3000) and prints `listening on 4123`; then `curl -si http://127.0.0.1:4123/health` answers 200 `{"ok":true}` and `curl -sI` shows HEAD answers 404. Stop it by the PID that `lsof -ti tcp:4123 -sTCP:LISTEN` names: a `pkill -f` pattern kill was refused by this run's host permission classifier (W1/S1).
 
 ## Harnesses and suites
 - node:test through `node --test`; no other harness.
diff --git a/docs/shiploop/spec.md b/docs/shiploop/spec.md
index 5ce67bc..bf21575 100644
--- a/docs/shiploop/spec.md
+++ b/docs/shiploop/spec.md
@@ -2,6 +2,8 @@
 
 ## R-1 Health route
 GET /health answers 200 with the JSON body {"ok":true} and content-type application/json.
+Only an exact GET /health is routed and a query string is ignored; /health/, HEAD /health and POST /health answer 404 {"error":"not found"}. Met by src/server.js and TC-1 in test/server.test.js (W1/S1)
 
 ## R-2 Existing routes unchanged
 GET /users and GET /users/:id answer as before; `npm test` passes.
+Observed unchanged: GET /users 200 with the user list, GET /users/:id 200 or 404 {"error":"not found"}, any other path 404 {"error":"not found"}; test/server.test.js asserts only /users/:id, so the GET /users route has no HTTP test (W1/S1)
diff --git a/src/server.js b/src/server.js
index bcf2fad..b528cb8 100644
--- a/src/server.js
+++ b/src/server.js
@@ -8,10 +8,11 @@ function send(res, status, body) {
   res.end(JSON.stringify(body));
 }
 
-/** An HTTP server for the user store; not listening until the caller calls listen(). */
+/** An HTTP server for the user store and `GET /health`; not listening until the caller calls listen(). */
 function createServer() {
   return http.createServer((req, res) => {
     const url = new URL(req.url, 'http://localhost');
+    if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { ok: true });
     if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());
     const match = /^\/users\/(\d+)$/.exec(url.pathname);
     if (req.method === 'GET' && match) {
diff --git a/test/server.test.js b/test/server.test.js
index 38f9c89..146daf7 100644
--- a/test/server.test.js
+++ b/test/server.test.js
@@ -22,3 +22,12 @@ test('GET /users/:id returns the user or 404', async () => {
     assert.equal((await fetch(`${base}/users/42`)).status, 404);
   });
 });
+
+test('TC-1 GET /health answers 200 with {"ok":true} as application/json', async () => {
+  await withServer(async (base) => {
+    const res = await fetch(`${base}/health`);
+    assert.equal(res.status, 200);
+    assert.match(res.headers.get('content-type'), /^application\/json/);
+    assert.deepEqual(await res.json(), { ok: true });
+  });
+});

```
## Arm Y: result and notes
# ShipLoop navigator result

```shiploop-state
{
  "assumptions": [],
  "headline": "GET /health is documented in the README (route table, runnable example, 404 caveats) and recorded in the spec and environment notes; focused and full tests pass.",
  "knowledge": {
    "architecture": "No change: the health route is a branch in the existing createServer handler using node:http only, so it follows AD-1 and the recorded Structure and Conventions; no new decision and no departure.",
    "environment": "Added two commands under ## Commands (W1/S1): the focused `node --test test/server.test.js` (2 tests, TC-1 included; `npm test` ran 8, all passing) and `PORT=4123 npm start` with `curl -si http://127.0.0.1:4123/health`, plus how to stop a started server (by its PID; a pkill -f pattern kill was refused by this host's classifier).",
    "spec": "R-1: one line stating that only an exact GET /health is routed, the query string is ignored and /health/, HEAD and POST answer 404 {\"error\":\"not found\"}, met by src/server.js and TC-1 (W1/S1). R-2: one line recording the observed unchanged routes and that GET /users has no HTTP test (W1/S1)."
  },
  "outcome": "done",
  "summary": "Documented from observation: README.md gains a Running the server section (PORT default 3000, route table, curl example, exact-match and 404-not-405 caveats, link to R-1 and TC-1); createServer's JSDoc now names GET /health (comment only, tests rerun green: focused 2/2, npm test 8/8). Default: HEAD and POST /health answering 404 is documented as observed behaviour, not changed (the request did not ask for 405 or HEAD support). Open question, no owner item exists because W1 is the only work item: test/server.test.js has no HTTP test for GET /users, which R-2 names; R-2 is met by npm test exit 0 only. Not run: nothing; every README command and table row was executed."
}
```

----- RUN/notes/document.md -----
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
