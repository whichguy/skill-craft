'use strict';
// Witness for R-2.10 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  let r = await get('?size=3'); eq(r.json.items.map((u) => u.id), [1, 2, 3]);
  r = await get('?size=100&name=r'); eq(r.json.items.map((u) => u.id), [2, 3]);
  r = await get('?size=2'); eq(r.json.items.map((u) => u.id), [1, 2]);
});
