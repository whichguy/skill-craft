'use strict';
// Witness for R-3.17 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const q of ['?page=abc', '?size=abc', '?page=0', '?size=101']) {
    const r = await get(q);
    equal(r.status, 400, `${q} status`);
    ok(/application\/json/i.test(r.type), `${q} content-type was "${r.type}"`);
    ok(r.json && typeof r.json.error === 'string' && r.json.error.length > 0, `${q} body must be JSON with an error string: ${r.text}`);
  }
});
