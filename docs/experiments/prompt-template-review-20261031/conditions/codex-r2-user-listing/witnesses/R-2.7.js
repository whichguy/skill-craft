'use strict';
// Witness for R-2.7 (codex-r2-user-listing): independent HTTP check; exit 0 when the condition holds.
// WORK=<product dir> selects the copy under test.
const { run, U, eq, ok, equal } = require('./_lib');

run(async ({ get }) => {
  for (const [size, pages] of [[1, 3], [2, 2], [3, 1], [100, 1]]) {
    const r = await get(`?size=${size}`);
    equal(r.json.pages, pages, `size=${size} pages`);
  }
});
