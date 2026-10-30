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
