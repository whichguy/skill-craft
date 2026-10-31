'use strict';
// Witness for R-3.22 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?name=lovelace&name=zzz'); eq(r.json, [U[0]]);
  r = await get('?name=zzz&name=lovelace'); eq(r.json, []);
});
