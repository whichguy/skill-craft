'use strict';
// Witness for R-3.8 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  { const r = await get('?page=-1'); equal(r.status, 400, 'page=-1 status'); }
  { const r = await get('?page=-5'); equal(r.status, 400, 'page=-5 status'); }
});
