'use strict';
// Witness for R-3.13 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  const r = await get('?size=1');
  equal(r.status, 200);
  eq([r.json.size, r.json.pages, r.json.items], [1, 3, [U[0]]]);
});
