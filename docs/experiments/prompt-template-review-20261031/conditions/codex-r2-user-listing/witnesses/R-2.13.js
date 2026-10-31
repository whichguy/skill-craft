'use strict';
// Witness for R-2.13 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const [q, page, pages, total] of [['?page=2&size=3', 2, 1, 3], ['?page=99&size=2', 99, 2, 3], ['?page=2&name=zzz', 2, 0, 0]]) {
    const r = await get(q);
    equal(r.status, 200, `${q} status`);
    eq(r.json, { page, size: q.includes('size=3') ? 3 : q.includes('size=2') ? 2 : 10, total, pages, items: [] }, q);
  }
});
