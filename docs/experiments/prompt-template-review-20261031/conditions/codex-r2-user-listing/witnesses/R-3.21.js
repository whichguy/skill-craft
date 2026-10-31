'use strict';
// Witness for R-3.21 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?size=2&size=500'); equal(r.status, 200); equal(r.json.size, 2);
  r = await get('?size=1&size=2'); equal(r.status, 200); equal(r.json.size, 1);
});
