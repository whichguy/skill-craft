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
      const n = page.news().length, nav = page.navigations;
      await C.clickNewGame(page); await L.sleep(600);
      check(page.news().length === n + 1, 'New game after the restart error started no game');
      const sent = await C.shoot(page, 0, 0);
      check(sent, 'after New game the board did not accept a shot');
      const i = await C.info(page, 0, 0);
      check(C.marked(i) && page.navigations === nav, 'the new game did not play without a reload');
    } finally { s2.closeAllConnections?.(); await new Promise((r) => s2.close(r)); }
  });
});
