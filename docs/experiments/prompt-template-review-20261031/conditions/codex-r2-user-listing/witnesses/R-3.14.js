'use strict';
// Witness for R-3.14 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?page=1');
  equal(r.status, 200); equal(r.json.page, 1);
  r = await get('?page=1&size=2');
  equal(r.status, 200); eq(r.json.items, [U[0], U[1]]);
});
