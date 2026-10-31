'use strict';
// Witness for R-1.6 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  const r = await get('?name=');
  equal(r.status, 200);
  eq(r.json, U);
});
