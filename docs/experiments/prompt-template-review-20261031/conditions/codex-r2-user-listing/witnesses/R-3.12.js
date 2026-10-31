'use strict';
// Witness for R-3.12 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  const r = await get('?size=100');
  equal(r.status, 200);
  eq([r.json.size, r.json.page, r.json.items], [100, 1, U]);
});
