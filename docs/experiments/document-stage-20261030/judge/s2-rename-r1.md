# Scenario s2-rename

## Request
S1 In this Node.js project, rename getUser to findUser everywhere: its definition and export in src/users.js, its use in src/server.js, and the tests. Behaviour must not change and no getUser alias may remain. npm test must pass.

## The step's state before the document stage
Implement and test were done; the uncommitted change before documentation was:  M src/server.js,  M src/users.js,  M test/users.test.js
Earlier results (implement summary, not-covered behaviour, test summary):
# ShipLoop navigator result

```shiploop-state
{
  "outcome": "done",
  "summary": "Renamed getUser to findUser in src/users.js (definition and export) and src/server.js; no alias kept. `! grep -rn getUser src test` exits 0.",
  "not_covered": []
}
```

# ShipLoop navigator result

```shiploop-state
{
  "outcome": "done",
  "summary": "TC-1 renamed the users test to findUser; all suites pass.",
  "commands": [
    {
      "kind": "focused",
      "command": "node --test test/users.test.js",
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
 "stale_mentions": [
  "README.md: getUser(id)",
  "docs/api.md: getUser(id)"
 ],
 "no_bloat": "a rename needs no new prose: the two stale mentions are the whole doc change",
 "architecture": "no AD warranted"
}
## Arm X: diff against the base commit (code, tests and docs)
```diff
diff --git a/README.md b/README.md
index b201620..781b534 100644
--- a/README.md
+++ b/README.md
@@ -4,7 +4,7 @@ A small Node.js project with no dependencies.
 
 - `src/strings.js`: text helpers
 - `src/paginate.js`: split a list into pages
-- `src/users.js`: an in-memory user store; `getUser(id)` returns the user or null, `listUsers()` every user
+- `src/users.js`: an in-memory user store; `findUser(id)` returns the user or null, `listUsers()` every user
 - `src/server.js`: an HTTP server (`node:http`) that serves the users (see [docs/api.md](docs/api.md))
 
 Run the tests with `npm test`, which runs `node --test`.
diff --git a/docs/api.md b/docs/api.md
index 4046d90..be7dd6a 100644
--- a/docs/api.md
+++ b/docs/api.md
@@ -3,6 +3,6 @@
 | Route | Answer |
 |---|---|
 | `GET /users` | 200, every user as a JSON array (`listUsers()`) |
-| `GET /users/:id` | 200 with the user found by `getUser(id)`, or 404 `{"error":"not found"}` |
+| `GET /users/:id` | 200 with the user found by `findUser(id)`, or 404 `{"error":"not found"}` |
 
 Any other route answers 404 `{"error":"not found"}`.
diff --git a/src/server.js b/src/server.js
index bcf2fad..2b737f6 100644
--- a/src/server.js
+++ b/src/server.js
@@ -1,7 +1,7 @@
 'use strict';
 
 const http = require('node:http');
-const { getUser, listUsers } = require('./users');
+const { findUser, listUsers } = require('./users');
 
 function send(res, status, body) {
   res.writeHead(status, { 'content-type': 'application/json' });
@@ -15,7 +15,7 @@ function createServer() {
     if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());
     const match = /^\/users\/(\d+)$/.exec(url.pathname);
     if (req.method === 'GET' && match) {
-      const user = getUser(Number(match[1]));
+      const user = findUser(Number(match[1]));
       return user ? send(res, 200, user) : send(res, 404, { error: 'not found' });
     }
     return send(res, 404, { error: 'not found' });
diff --git a/src/users.js b/src/users.js
index 28fa02d..758cd4b 100644
--- a/src/users.js
+++ b/src/users.js
@@ -6,8 +6,8 @@ const USERS = [
   { id: 3, name: 'Alan Turing', email: 'alan@example.com' },
 ];
 
-/** The user with `id`, or null. */
-function getUser(id) {
+/** The user whose numeric `id` is `id`, or null; a non-number never matches and nothing throws. */
+function findUser(id) {
   return USERS.find((user) => user.id === id) || null;
 }
 
@@ -16,4 +16,4 @@ function listUsers() {
   return USERS.slice();
 }
 
-module.exports = { getUser, listUsers };
+module.exports = { findUser, listUsers };
diff --git a/test/users.test.js b/test/users.test.js
index 5403e12..0ee498c 100644
--- a/test/users.test.js
+++ b/test/users.test.js
@@ -2,11 +2,11 @@
 
 const test = require('node:test');
 const assert = require('node:assert/strict');
-const { getUser, listUsers } = require('../src/users');
+const { findUser, listUsers } = require('../src/users');
 
-test('getUser finds a user by id and returns null otherwise', () => {
-  assert.equal(getUser(2).name, 'Grace Hopper');
-  assert.equal(getUser(99), null);
+test('findUser finds a user by id and returns null otherwise', () => {
+  assert.equal(findUser(2).name, 'Grace Hopper');
+  assert.equal(findUser(99), null);
 });
 
 test('listUsers returns every user', () => {

```
## Arm X: result and notes
# ShipLoop navigator result

```shiploop-state
{
  "assumptions": [],
  "headline": "The rename's two stale doc mentions (README.md, docs/api.md) now say findUser, and findUser's JSDoc states its argument contract.",
  "knowledge": {"architecture": "No AD-<n>: the rename follows AD-1 and the ## Conventions (one-line JSDoc on each exported function) and sets no new structure, dependency, interface rule or convention.", "environment": "No change: `npm test` is already recorded, the focused `node --test test/users.test.js` is derivable from it, and `npm start` with PORT is in package.json; this step proved `npm test` (7 pass) and the focused run (2 pass).", "spec": "No line added: R-1 (findUser exported from src/users.js, used by src/server.js and the tests), R-2 (no getUser name) and R-3 (findUser returns the user or null; GET /users/:id answers 200 or 404; npm test passes) were already precise and the code shows which files meet them; the new JSDoc detail (a non-number never matches) is a docstring fact no requirement concerns."},
  "outcome": "done",
  "summary": "Edited README.md:7 and docs/api.md:6 (getUser to findUser) and the findUser JSDoc in src/users.js (strict numeric match, nothing throws; observed with node -e and a live server on PORT 34567). Left src/server.js, test/users.test.js, the three knowledge files and spec.md R-2's deliberate getUser mention unchanged; no tombstone, because it would reintroduce the forbidden name. After the last edit npm test (7 pass), node --test test/users.test.js (2 pass) and `! grep -rn getUser src test` (exit 0) all passed. Reasons are in RUN/notes/document.md."
}
```

----- RUN/notes/document.md -----
# W1/S1 document notes

Listed: `findUser` (renamed from `getUser`; src/users.js definition and export, src/server.js use, test/users.test.js).

- src/users.js `findUser`: JSDoc now states the argument contract the signature hides (strict numeric match; a
  non-number such as '2', null or {} finds nothing and nothing throws). Observed with node -e. One line, per
  architecture.md ## Conventions.
- src/server.js `createServer`: docstring unchanged, still true; the step only renamed the call. Routes are
  documented once in docs/api.md.
- test/users.test.js: test title renamed in the step; no comment to reconcile.
- README.md line 7 and docs/api.md line 6 (the two stale mentions) now name `findUser`. Routes observed on a
  server started with `PORT=34567 node src/server.js`: GET /users 200 array, /users/2 200 user, /users/99 404,
  /users/abc 404, /nope 404; matches docs/api.md.
- No README start/usage section added: the step changed no start behaviour; `npm start` and PORT live in package.json
  and src/server.js, so adding them would be unrequested scope.
- No tombstone: R-2 (no getUser alias) and test C2 (`! grep -rn getUser src test`) already guard the removed name;
  a source comment naming it would itself leave a getUser mention that R-2 forbids.
- docs/shiploop/spec.md R-2 names `getUser` as the forbidden name: a requirement, not a stale mention.
- Knowledge home: no edit to spec, architecture or environment (reasons in the result's `knowledge`).
- Rerun after the last edit: `npm test` 7/7 pass, `node --test test/users.test.js` 2/2 pass, `! grep -rn getUser src test` exit 0.

## Arm Y: diff against the base commit (code, tests and docs)
```diff
diff --git a/README.md b/README.md
index b201620..781b534 100644
--- a/README.md
+++ b/README.md
@@ -4,7 +4,7 @@ A small Node.js project with no dependencies.
 
 - `src/strings.js`: text helpers
 - `src/paginate.js`: split a list into pages
-- `src/users.js`: an in-memory user store; `getUser(id)` returns the user or null, `listUsers()` every user
+- `src/users.js`: an in-memory user store; `findUser(id)` returns the user or null, `listUsers()` every user
 - `src/server.js`: an HTTP server (`node:http`) that serves the users (see [docs/api.md](docs/api.md))
 
 Run the tests with `npm test`, which runs `node --test`.
diff --git a/docs/api.md b/docs/api.md
index 4046d90..be7dd6a 100644
--- a/docs/api.md
+++ b/docs/api.md
@@ -3,6 +3,6 @@
 | Route | Answer |
 |---|---|
 | `GET /users` | 200, every user as a JSON array (`listUsers()`) |
-| `GET /users/:id` | 200 with the user found by `getUser(id)`, or 404 `{"error":"not found"}` |
+| `GET /users/:id` | 200 with the user found by `findUser(id)`, or 404 `{"error":"not found"}` |
 
 Any other route answers 404 `{"error":"not found"}`.
diff --git a/docs/shiploop/environment.md b/docs/shiploop/environment.md
index 8b88e1d..39571d4 100644
--- a/docs/shiploop/environment.md
+++ b/docs/shiploop/environment.md
@@ -2,6 +2,9 @@
 
 ## Commands
 - `npm test`: runs `node --test`, every test/*.test.js; exit 0 is a pass.
+- `node --test test/users.test.js`: one test file (focused run); exit 0 is a pass. (W1/S1)
+- `! grep -rn <name> src test`: exit 0 means the name appears in no source or test file (a rename check). (W1/S1)
+- Route check without a harness: `createServer().listen(0)` from src/server.js, then `fetch` of `/users`, `/users/2` (200) and `/users/99` (404). (W1/S1)
 
 ## Harnesses and suites
 - node:test through `node --test`; no other harness.
diff --git a/docs/shiploop/spec.md b/docs/shiploop/spec.md
index 266abc6..1ebec70 100644
--- a/docs/shiploop/spec.md
+++ b/docs/shiploop/spec.md
@@ -2,9 +2,12 @@
 
 ## R-1 Rename
 The user lookup is exported as `findUser(id)` from src/users.js and used by src/server.js and the tests.
+Met by src/users.js (definition and export), src/server.js (GET /users/:id) and test/users.test.js; README.md and docs/api.md name `findUser(id)` too. (W1/S1)
 
 ## R-2 No alias
 No `getUser` name or alias remains.
+Met: src/users.js exports only `findUser` and `listUsers`, and the old name is absent from src, test, README.md and docs/api.md; this requirement is the one place that still names it. (W1/S1)
 
 ## R-3 Behaviour unchanged
 `findUser(id)` returns the user with `id`, or null; GET /users/:id answers 200 with the user or 404; `npm test` passes.
+Observed: `findUser(2)` returns Grace Hopper and `findUser(99)` null; GET /users/2 answers 200 with that user and GET /users/99 answers 404 `{"error":"not found"}`; `npm test` passes 7 tests (test/users.test.js, test/server.test.js). (W1/S1)
diff --git a/src/server.js b/src/server.js
index bcf2fad..2b737f6 100644
--- a/src/server.js
+++ b/src/server.js
@@ -1,7 +1,7 @@
 'use strict';
 
 const http = require('node:http');
-const { getUser, listUsers } = require('./users');
+const { findUser, listUsers } = require('./users');
 
 function send(res, status, body) {
   res.writeHead(status, { 'content-type': 'application/json' });
@@ -15,7 +15,7 @@ function createServer() {
     if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());
     const match = /^\/users\/(\d+)$/.exec(url.pathname);
     if (req.method === 'GET' && match) {
-      const user = getUser(Number(match[1]));
+      const user = findUser(Number(match[1]));
       return user ? send(res, 200, user) : send(res, 404, { error: 'not found' });
     }
     return send(res, 404, { error: 'not found' });
diff --git a/src/users.js b/src/users.js
index 28fa02d..4f50bb5 100644
--- a/src/users.js
+++ b/src/users.js
@@ -7,7 +7,7 @@ const USERS = [
 ];
 
 /** The user with `id`, or null. */
-function getUser(id) {
+function findUser(id) {
   return USERS.find((user) => user.id === id) || null;
 }
 
@@ -16,4 +16,4 @@ function listUsers() {
   return USERS.slice();
 }
 
-module.exports = { getUser, listUsers };
+module.exports = { findUser, listUsers };
diff --git a/test/users.test.js b/test/users.test.js
index 5403e12..0ee498c 100644
--- a/test/users.test.js
+++ b/test/users.test.js
@@ -2,11 +2,11 @@
 
 const test = require('node:test');
 const assert = require('node:assert/strict');
-const { getUser, listUsers } = require('../src/users');
+const { findUser, listUsers } = require('../src/users');
 
-test('getUser finds a user by id and returns null otherwise', () => {
-  assert.equal(getUser(2).name, 'Grace Hopper');
-  assert.equal(getUser(99), null);
+test('findUser finds a user by id and returns null otherwise', () => {
+  assert.equal(findUser(2).name, 'Grace Hopper');
+  assert.equal(findUser(99), null);
 });
 
 test('listUsers returns every user', () => {

```
## Arm Y: result and notes
# ShipLoop navigator result

```shiploop-state
{
  "assumptions": [],
  "headline": "README.md and docs/api.md now name findUser(id); behaviour is unchanged and the old name survives only in spec requirement R-2.",
  "knowledge": {
    "architecture": "No change: a pure rename under the existing named-export convention; no new decision and no AD-<n> departed from.",
    "environment": "Added under Commands the focused run `node --test test/users.test.js`, the rename check `! grep -rn <name> src test`, and the harness-free route check (createServer().listen(0) then fetch /users, /users/2, /users/99); each was run and worked.",
    "spec": "Added one line each, marked (W1/S1), inside R-1 (files that meet it), R-2 (export list and where the old name is absent; this requirement is the only mention) and R-3 (observed findUser results, 200/404 route answers, npm test 7 pass)."
  },
  "outcome": "done",
  "summary": "Docs fixed: README.md users.js bullet and docs/api.md GET /users/:id row (getUser -> findUser). Reread after edit; npm test (7 pass) and node --test test/users.test.js (2 pass) rerun green; `! grep -rn getUser src test` exits 0. The committed R-2 line still names getUser because it forbids it and a committed line is not editable; no open items, no send-back."
}
```

----- RUN/notes/document.md -----
# document W1/S1 notes

Changed public behaviour: the user-lookup export is renamed getUser -> findUser (no alias); HTTP behaviour unchanged.

Observed (from WORKTREE): findUser(2) -> Grace Hopper, findUser(99) -> null, the module exports only findUser and listUsers;
GET /users 200, GET /users/2 200, GET /users/99 404 {"error":"not found"}; npm test 7 pass 0 fail; node --test test/users.test.js 2 pass;
`! grep -rn getUser src test` exits 0.

Docs changed: README.md (users.js bullet) and docs/api.md (GET /users/:id row) named the old function; both now say findUser(id).
Reread both after the edit; no old name left outside docs/shiploop/spec.md.

No-change reasons:
- docs/shiploop/spec.md R-2 still contains the old name: it is the committed requirement text that forbids it (a committed line, not editable); R-2's new line says so.
- docs/shiploop/architecture.md: no design or service decision; the rename follows the existing "one CommonJS module per concept, named exports" convention, and the JSDoc on findUser is unchanged and still correct.
- No example in README/api.md is a runnable command; the route table was checked by calling the server routes above.
