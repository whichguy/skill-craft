'use strict';
// Witness for R-3.9 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  { const r = await get('?size=0'); equal(r.status, 400, 'size=0 status'); }
});
