## Failing now
- C-20: `test/assignment.test.js` (the only new test file) covers the endpoint and the filter but nothing in it exercises the command-line listing (no `bin/tickets.js`, `main()` or table/format use), so the clause "tests covering the assignment endpoint, the filter and the command-line listing" is not met. `npm test` itself passes.

All other clauses (C-1 to C-19, C-21 to C-25) and use cases U-1 to U-6 pass on the product as it stands.

## Discoveries
- `node --test` with no arguments finds every `*.test.js` under the folder, so acceptance files must not use that suffix (they are `*.spec.js`), or `npm test` would run them and C-20's own `npm test` call would recurse | Observable: `npm test` output lists only test/ files | Why: the acceptance folder sits inside the product folder.
- C-20 can only be checked by reading the test files for the three topics, since "covering" is not otherwise observable | Observable: grep of test/ for the endpoint path, the filter and the command line | Why: the check is a heuristic (a file mentioning `assignee`, `/assignee`, a filter use and `tickets.js|format|table|main(`).
- The service's whole data-file refusal at start exits non-zero and writes the field name to stderr; the spec says "the data-file error naming the field" without fixing the exit code | Observable: `PORT=.. DATA_FILE=bad.json node src/server.js` exits 2 | Why: C-24 tests only "non-zero, stderr names `assignee`".
- Validation-vs-state precedence (C-5 Open) is untested by design; the build answered 400 first.
