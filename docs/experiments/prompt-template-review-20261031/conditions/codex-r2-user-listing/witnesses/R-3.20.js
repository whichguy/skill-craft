'use strict';
// Witness for R-3.20 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?page=2&page=abc&size=1'); equal(r.status, 200); eq([r.json.page, r.json.items], [2, [U[1]]]);
  r = await get('?size=1&page=2&page=3'); equal(r.status, 200); equal(r.json.page, 2);
});
