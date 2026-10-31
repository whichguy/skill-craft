'use strict';
// Witness for R-2.8 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['?name=zzz&size=3', '?name=zzz&page=1', '?name=zzz&size=1&page=1']) {
    const r = await get(q);
    equal(r.status, 200, q);
    eq([r.json.total, r.json.pages, r.json.items], [0, 0, []], q);
  }
});
