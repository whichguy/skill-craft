'use strict';
// Witness for R-1.7 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['?name=zzzz', '?name=Lovelace%20Turing']) {
    const r = await get(q);
    equal(r.status, 200, `${q} status`);
    eq(r.json, [], `${q} body`);
  }
});
