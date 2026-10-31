'use strict';
// Witness for R-2.2 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  const r = await get('?size=2');
  equal(r.status, 200);
  ok(r.json && !Array.isArray(r.json) && typeof r.json === 'object', 'object expected');
});
