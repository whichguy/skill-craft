'use strict';
// Witness for R-3.16 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  { const r = await get('?size=0x2'); equal(r.status, 400, 'size=0x2 status'); }
  { const r = await get('?size=1e1'); equal(r.status, 400, 'size=1e1 status'); }
});
