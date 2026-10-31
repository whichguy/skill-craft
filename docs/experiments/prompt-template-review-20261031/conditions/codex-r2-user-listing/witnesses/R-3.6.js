'use strict';
// Witness for R-3.6 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  { const r = await get('?size=2.5'); equal(r.status, 400, 'size=2.5 status'); }
  { const r = await get('?size=0.5'); equal(r.status, 400, 'size=0.5 status'); }
  { const r = await get('?size=10.75'); equal(r.status, 400, 'size=10.75 status'); }
});
