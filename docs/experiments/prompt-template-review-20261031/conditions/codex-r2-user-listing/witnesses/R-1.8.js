'use strict';
// Witness for R-1.8 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?foo=bar'); equal(r.status, 200); eq(r.json, U);
  r = await get('?name=ada&foo=bar'); equal(r.status, 200); eq(r.json, [U[0]]);
  r = await get('?x=1&y=2&name=grace'); equal(r.status, 200); eq(r.json, [U[1]]);
});
