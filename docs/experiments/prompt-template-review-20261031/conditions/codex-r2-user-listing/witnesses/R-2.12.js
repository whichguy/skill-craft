'use strict';
// Witness for R-2.12 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  const r = await get('?page=1');
  eq([r.json.size, r.json.items], [10, U]);
});
