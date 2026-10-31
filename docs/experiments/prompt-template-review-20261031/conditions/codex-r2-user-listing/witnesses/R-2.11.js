'use strict';
// Witness for R-2.11 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  const r = await get('?size=2');
  eq([r.json.page, r.json.items], [1, [U[0], U[1]]]);
});
