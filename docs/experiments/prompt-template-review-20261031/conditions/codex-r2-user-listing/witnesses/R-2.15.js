'use strict';
// Witness for R-2.15 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?name=hopper&size=1'); eq(r.json, { page: 1, size: 1, total: 1, pages: 1, items: [U[1]] });
  r = await get('?name=r&size=1&page=2'); eq(r.json, { page: 2, size: 1, total: 2, pages: 2, items: [U[2]] });
});
