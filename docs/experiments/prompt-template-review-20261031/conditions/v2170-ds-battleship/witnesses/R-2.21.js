'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    await C.win(page, fleet);
    const st = await page.eval(`(() => { const b = [...document.querySelectorAll('button')].find((x) => /New game/.test(x.textContent)); return { present: !!b, disabled: b && b.disabled, aria: b && b.getAttribute('aria-disabled') }; })()`);
    check(st.present && !st.disabled && st.aria !== 'true', 'New game after the win: ' + JSON.stringify(st));
    const n = page.news().length; await C.clickNewGame(page); await L.sleep(400);
    check(page.news().length === n + 1, 'clicking New game after the win started no game');
  });
});
