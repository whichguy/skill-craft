'use strict';
// Witness for R-2.4 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?page=2&size=2'); equal(r.json.page, 2);
  r = await get('?size=2'); equal(r.json.page, 1);
  r = await get('?page=3&size=1'); equal(r.json.page, 3);
});
