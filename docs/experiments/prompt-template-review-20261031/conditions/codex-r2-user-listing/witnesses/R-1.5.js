'use strict';
// Witness for R-1.5 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['%2E*', 'a.a', '%5Ea', 'a%24', '%28', '%5B', '*']) {
    const r = await get(`?name=${q}`);
    equal(r.status, 200, `name=${q} status`);
    eq(r.json, [], `name=${q} body`);
  }
});
