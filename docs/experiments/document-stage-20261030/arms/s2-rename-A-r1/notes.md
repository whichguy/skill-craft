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
