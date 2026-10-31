'use strict';
// Witness for R-3.19 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['?size=abc', '?size=101', '?size=', '?size=0&page=1']) {
    const r = await get(q);
    equal(r.status, 400, `${q} status`);
    ok(r.json && /size/i.test(String(r.json.error)), `${q} error must name size: ${r.text}`);
  }
});
