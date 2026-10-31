'use strict';
// Witness for R-3.18 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['?page=abc', '?page=0', '?page=', '?page=1.5&size=2']) {
    const r = await get(q);
    equal(r.status, 400, `${q} status`);
    ok(r.json && /page/i.test(String(r.json.error)), `${q} error must name page: ${r.text}`);
  }
});
