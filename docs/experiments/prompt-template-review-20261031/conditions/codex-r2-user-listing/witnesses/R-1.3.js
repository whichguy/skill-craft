'use strict';
// Witness for R-1.3 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?name=OVELACE');
  equal(r.status, 200); eq(r.json, [U[0]]);
  r = await get('?name=RACE');
  equal(r.status, 200); eq(r.json, [U[1]]);
});
