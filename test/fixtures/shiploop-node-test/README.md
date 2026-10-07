Real `node --test` output (Node v25.9.0, piped, paths rewritten to `/work`), one file per reporter and outcome.
Tests in `test/shiploop-test-counts.test.py` read them. The source files were `test/a.test.js` (TC-1 pass, TC-2 pass with
"pending" in its title, TC-3 skipped, TC-4 todo, TC-5 group holding TC-6 pass and TC-7 failing), `test/b.test.js` (TC-8
pass) and `test/c.test.js` (requires a missing module). `pass-*` ran four tests, `fail-*` ran a.test.js and b.test.js,
`load-*` ran c.test.js. The `dot` reporter prints only dots, so it has no countable summary.
