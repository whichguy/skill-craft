'use strict';
// Witness for R-2.5 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?size=2'); equal(r.json.size, 2);
  r = await get('?page=1'); equal(r.json.size, 10);
  r = await get('?size=7'); equal(r.json.size, 7);
});
