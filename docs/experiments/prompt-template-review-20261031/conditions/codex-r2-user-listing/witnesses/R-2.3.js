'use strict';
// Witness for R-2.3 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['', '?name=a', '?name=zzz', '?foo=1']) {
    const r = await get(q);
    equal(r.status, 200, `${q} status`);
    ok(Array.isArray(r.json), `${q} should be a bare array`);
  }
});
