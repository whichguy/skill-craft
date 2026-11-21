## Failing now
none — all 24 clauses and 5 use cases pass on the product as built (each command run, each prints its item id).

## Discoveries
- Acceptance test files must not match `node --test`'s discovery patterns (`*.test.js`, under `test/`), or `npm test` would run them too | Observable: `npm test` test count | Why: they are named `acceptance/*.accept.js`; C-23/C-24 and U-5 spawn `node --test` with `NODE_TEST_CONTEXT` removed, since an inherited value makes the nested run report nothing and pass vacuously.
- `list --raw` in the build appends `assignee` as a fifth column | Observable: `node bin/tickets.js list --raw` | Why: C-20's Open allows it; tests check columns 1 to 4 and the weekly report counts only.
- Unstated: a body that is not a JSON object (`[]`, `5`, `null`, bad JSON) on the assignee endpoint is 400 `invalid` | Observable: PUT with such a body | Why: C-4 covers it through the existing docs; tested there.
