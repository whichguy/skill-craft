'use strict';
// Witness for R-1.9 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?name=a'); eq(r.json.map((u) => u.id), [1, 2, 3]);
  r = await get('?name=r'); eq(r.json.map((u) => u.id), [2, 3]);
});
