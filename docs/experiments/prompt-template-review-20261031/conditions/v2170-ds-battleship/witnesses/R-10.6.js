'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    await C.ready(page, base);
    await srv.close();
    const s2 = L.serverModule().createServer({ random: L.seeded(99) });
    await new Promise((r) => s2.listen(srv.port, '127.0.0.1', r));
    try {
      await page.clickCell(4, 4); await L.sleep(600);
      const st = await C.statusOf(page);
      check(/no game|choose new game|not found|error|could not|unable|404/i.test(st), 'after the restart the status region says ' + JSON.stringify(st));
      const i = await C.info(page, 4, 4);
      check(!C.marked(i), 'the cell was marked after the restart error: ' + JSON.stringify([i.text, i.label]));
      check(/Ships remaining:?\s*5\b/i.test(await C.text(page)), 'the count changed after the restart error');
    } finally { s2.closeAllConnections?.(); await new Promise((r) => s2.close(r)); }
  });
});
