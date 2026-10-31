'use strict';
// Witness for R-2.9 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?page=2&size=1'); eq(r.json.items, [U[1]]);
  r = await get('?page=1&size=2'); eq(r.json.items, [U[0], U[1]]);
  r = await get('?page=3&size=1'); eq(r.json.items, [U[2]]);
  r = await get('?page=1&size=1'); eq(r.json.items, [U[0]]);
});
