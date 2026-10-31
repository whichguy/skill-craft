import sys; sys.path.insert(0, '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship')
from mk_common import write

def bw(wid, body, seed=21, rule='C.ALLOW'):
    write(wid, f"""L.run(async () => {{
  const SEED = {seed};
  await C.withPage(SEED, async (page, base, srv) => {{
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, {rule});
    {body}
  }});
}});""")

bw('R-2.10', """await page.eval('window.__m = 1');
    const n0 = page.navigations;
    await page.clickCell(3, 4); await L.sleep(500);
    const f = page.fires();
    check(f.length === 1, 'one click sent ' + f.length + ' POST /api/fire requests');
    const b = JSON.parse(f[0].postData);
    check(b.row === 3 && b.col === 4, 'the shot carried ' + f[0].postData);
    check(await page.eval('window.__m') === 1 && page.navigations === n0, 'the document navigated or reloaded');""")
bw('R-2.11', """const w = C.waterCell(fleet), d = fleet[4].cells;
    await C.shoot(page, w.row, w.col); const miss = await C.info(page, w.row, w.col);
    await C.shoot(page, d[0].row, d[0].col); const hit = await C.info(page, d[0].row, d[0].col);
    await C.shoot(page, d[1].row, d[1].col); const sunk = await C.info(page, d[1].row, d[1].col);
    for (const [word, i] of [['miss', miss], ['hit', hit], ['sunk', sunk]]) check(new RegExp(word, 'i').test(i.label) || i.result === word, 'the ' + word + ' cell shows ' + JSON.stringify([i.text, i.label, i.result]));
    check(new Set([miss.text, hit.text, sunk.text]).size === 3, 'miss, hit and sunk are not shown differently: ' + JSON.stringify([miss.text, hit.text, sunk.text]));""")
bw('R-2.12', """const t = await C.text(page); check(/Ships remaining:?\\s*5\\b/i.test(t), 'the page does not display 5 ships remaining; visible text: ' + JSON.stringify(t.slice(0, 120)));""")
bw('R-2.13', """const d = fleet[4].cells;
    await C.shoot(page, d[0].row, d[0].col); await C.shoot(page, d[1].row, d[1].col);
    const t = await C.text(page); check(/Ships remaining:?\\s*4\\b/i.test(t), 'after a sink the count shown is not 4; visible text: ' + JSON.stringify(t.slice(0, 120)));""")
bw('R-2.14', """const w = C.waterCell(fleet), d = fleet[4].cells; const out = {};
    await C.shoot(page, w.row, w.col); out.miss = await C.statusOf(page);
    await C.shoot(page, d[0].row, d[0].col); out.hit = await C.statusOf(page);
    await C.shoot(page, d[1].row, d[1].col); out.sunk = await C.statusOf(page);
    for (const k of ['miss', 'hit', 'sunk']) check(new RegExp(k, 'i').test(out[k]), 'after a ' + k + ' the status region says ' + JSON.stringify(out[k]));""")
bw('R-2.15', """const w = C.waterCell(fleet);
    check(await C.shoot(page, w.row, w.col), 'first shot not sent');
    const n = page.fires().length;
    await C.shoot(page, w.row, w.col); await L.sleep(300);
    check(page.fires().length === n, 'a click on an already-fired cell sent another request');""")
bw('R-2.16', """const a = fleet[0].cells[0], b = fleet[1].cells[0];
    await page.clickCell(a.row, a.col); await L.sleep(300);
    await page.clickCell(b.row, b.col); await L.sleep(150);
    await page.clickCell(a.row, a.col); await L.sleep(300);
    check(page.fires().length === 1, 'while a shot was in flight the page sent ' + page.fires().length + ' requests');""", rule="(rq) => (rq.method === 'POST' && /api\\/fire/.test(rq.url) ? { action: 'hold' } : { action: 'continue' })")
bw('R-2.17', """await C.win(page, fleet);
    check(/win|sunk/i.test(await C.statusOf(page)), 'game did not end: ' + await C.statusOf(page));
    const n = page.fires().length, w = C.waterCell(fleet);
    await C.shoot(page, w.row, w.col); await L.sleep(300);
    check(page.fires().length === n, 'after the game ended a click sent another request');""")
bw('R-2.18', """await page.clickCell(4, 4); await L.sleep(400);
    const t = await C.statusOf(page);
    check(/not reach|fail|error|could not|unable|network/i.test(t), 'status region after a failed request: ' + JSON.stringify(t));""",
   rule="(rq) => (rq.method === 'POST' && /api\\/fire/.test(rq.url) ? { action: 'fail' } : { action: 'continue' })")
write('R-2.19', """L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    let failing = true;
    await C.ready(page, base, (rq) => (failing && rq.method === 'POST' && /api\\/fire/.test(rq.url) ? { action: 'fail' } : { action: 'continue' }));
    await page.clickCell(4, 4); await L.sleep(400);
    const i = await C.info(page, 4, 4);
    check(!C.marked(i), 'a failed shot left the cell marked: ' + JSON.stringify([i.text, i.label, i.result]));
    failing = false;
    const sent = await C.shoot(page, 4, 4);
    check(sent, 'after the failure a retry click on the same cell sent nothing (grid stayed locked)');
    const j = await C.info(page, 4, 4);
    check(C.marked(j), 'the retry was not rendered: ' + JSON.stringify([j.text, j.label, j.result]));
  });
});""")
bw('R-2.20', """await C.win(page, fleet);
    const t = await C.statusOf(page);
    check(/five/i.test(t) && /sunk/i.test(t), 'win announcement does not say all five ships are sunk: ' + JSON.stringify(t));""")
bw('R-2.21', """await C.win(page, fleet);
    const st = await page.eval(`(() => { const b = [...document.querySelectorAll('button')].find((x) => /New game/.test(x.textContent)); return { present: !!b, disabled: b && b.disabled, aria: b && b.getAttribute('aria-disabled') }; })()`);
    check(st.present && !st.disabled && st.aria !== 'true', 'New game after the win: ' + JSON.stringify(st));
    const n = page.news().length; await C.clickNewGame(page); await L.sleep(400);
    check(page.news().length === n + 1, 'clicking New game after the win started no game');""")
bw('R-2.22', """await C.win(page, fleet);
    const n = page.news().length; await C.clickNewGame(page); await L.sleep(500);
    check(page.news().length === n + 1, 'New game started no game');
    const bad = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const i = await C.info(page, r, c); if (C.marked(i)) bad.push(r + ',' + c); }
    check(bad.length === 0, 'cells still show previous results after New game: ' + bad.slice(0, 5));""")
bw('R-2.23', """await C.win(page, fleet);
    const first = JSON.parse(page.fires()[0].postData).game;
    await C.clickNewGame(page); await L.sleep(500);
    const t = await C.text(page);
    check(/Ships remaining:?\\s*5\\b/i.test(t), 'after New game the count shown is not 5: ' + JSON.stringify(t.slice(0, 100)));
    await C.shoot(page, 0, 0);
    const second = JSON.parse(page.fires()[page.fires().length - 1].postData).game;
    check(second && second !== first, 'New game did not switch to a new game id');""")
bw('R-2.24', """let ok = false;
    for (let i = 0; i < 6 && !ok; i++) { await page.tab(); ok = await page.eval(`document.activeElement.classList.contains('cell')`); }
    check(ok, 'Tab never reached a cell');
    const at = await page.eval(`({ r: Number(document.activeElement.dataset.row), c: Number(document.activeElement.dataset.col) })`);
    await page.enter(); await L.sleep(500);
    check(page.fires().length === 1, 'Enter on a focused cell sent ' + page.fires().length + ' shots');
    const b = JSON.parse(page.fires()[0].postData); check(b.row === at.r && b.col === at.c, 'Enter fired ' + page.fires()[0].postData + ' instead of the focused cell ' + JSON.stringify(at));""")
bw('R-2.25', """let ok = false;
    for (let i = 0; i < 6 && !ok; i++) { await page.tab(); ok = await page.eval(`document.activeElement.classList.contains('cell')`); }
    check(ok, 'Tab never reached a cell');
    const cs = await page.eval(`(() => { const s = getComputedStyle(document.activeElement); return { os: s.outlineStyle, ow: parseFloat(s.outlineWidth), bs: s.boxShadow }; })()`);
    check((cs.os !== 'none' && cs.ow > 0) || (cs.bs && cs.bs !== 'none'), 'a focused cell shows no focus indicator: ' + JSON.stringify(cs));""")
bw('R-2.26', """const w = C.waterCell(fleet), h = fleet[0].cells[0];
    await C.shoot(page, w.row, w.col); await C.shoot(page, h.row, h.col);
    for (const [word, p] of [['miss', w], ['hit', h]]) {
      const i = await C.info(page, p.row, p.col);
      check(i.text.length > 0 || new RegExp(word, 'i').test(i.label), 'the ' + word + ' cell conveys its outcome by colour only: ' + JSON.stringify([i.text, i.label]));
    }""")
bw('R-2.27', """let ok = false;
    for (let i = 0; i < 6 && !ok; i++) { await page.tab(); ok = await page.eval(`document.activeElement.classList.contains('cell')`); }
    check(ok, 'Tab never reached a cell');
    const at = await page.eval(`document.activeElement.dataset.row + ',' + document.activeElement.dataset.col`);
    await page.enter(); await L.sleep(500);
    check(page.fires().length === 1, 'Enter did not fire');
    const now = await page.eval(`document.activeElement.classList.contains('cell') ? document.activeElement.dataset.row + ',' + document.activeElement.dataset.col : document.activeElement.tagName`);
    check(now === at, 'focus moved from cell ' + at + ' to ' + now);""")
bw('R-2.28', """await page.clickCell(4, 4); await L.sleep(300);
    const n = page.news().length;
    await C.clickNewGame(page); await L.sleep(400);
    check(page.news().length === n, 'New game started a new game while a shot was in flight');""",
   rule="(rq) => (rq.method === 'POST' && /api\\/fire/.test(rq.url) ? { action: 'hold' } : { action: 'continue' })")
write('R-2.29', """L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    const fleet = L.fleetOf(SEED);
    let failNew = false;
    await C.ready(page, base, (rq) => (failNew && /api\\/new/.test(rq.url) ? { action: 'fulfill', status: 500, body: '{"error":"boom"}' } : { action: 'continue' }));
    await C.win(page, fleet);
    failNew = true;
    await C.clickNewGame(page); await L.sleep(500);
    check((await C.statusOf(page)).length > 0, 'no status after the refused New game');
    const n = page.fires().length, w = C.waterCell(fleet);
    await C.shoot(page, w.row, w.col); await L.sleep(300);
    check(page.fires().length === n, 'after a refused New game the finished board accepted a shot');
    const h = fleet[0].cells[0]; const i = await C.info(page, h.row, h.col);
    check(C.marked(i), 'the finished board lost its marks after a refused New game: ' + JSON.stringify([i.text, i.label]));
  });
});""")
write('R-2.30', """L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    let bad = false;
    await C.ready(page, base, (rq) => (bad && rq.method === 'POST' && /api\\/fire/.test(rq.url) ? { action: 'fulfill', status: 200, body: '{"result":"banana","gameOver":false,"shipsRemaining":3}' } : { action: 'continue' }));
    bad = true;
    const before = await C.info(page, 6, 6), tb = await C.text(page);
    await page.clickCell(6, 6); await L.sleep(500);
    const after = await C.info(page, 6, 6), ta = await C.text(page);
    check(!C.marked(after) && after.html === before.html, 'an off-contract answer marked the cell: ' + after.html);
    check(/Ships remaining:?\\s*5\\b/i.test(ta), 'an off-contract answer changed the count: ' + ta.slice(0, 80));
    const st = await C.statusOf(page);
    check(st.length > 0 && !/Firing/i.test(st), 'the off-contract answer was not reported: ' + JSON.stringify(st));
  });
});""")

# ---------------- R-10 browser ----------------
bw('R-10.1', """check(page.news().length === 1, 'the page requested ' + page.news().length + ' games on load');
    await C.shoot(page, 0, 0);
    const b = JSON.parse(page.fires()[0].postData);
    check(typeof b.game === 'string' && /^[0-9a-f-]{36}$/.test(b.game), 'the first shot carried game ' + JSON.stringify(b.game));""")
write('R-10.2', """L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base);
    const d = fleet[4].cells;
    await C.shoot(page, d[0].row, d[0].col); await C.shoot(page, d[1].row, d[1].col);
    check(/Ships remaining:?\\s*4\\b/i.test(await C.text(page)), 'precondition: count 4');
    await page.reload(); await L.waitFor(() => page.news().length >= 2, 5000, 'second game request'); await L.sleep(300);
    const t = await C.text(page);
    check(/Ships remaining:?\\s*5\\b/i.test(t), 'after a reload the count shown is not 5: ' + JSON.stringify(t.slice(0, 100)));
    const bad = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const i = await C.info(page, r, c); if (C.marked(i)) bad.push(r + ',' + c); }
    check(bad.length === 0, 'after a reload cells still show results: ' + bad.slice(0, 5));
  });
});""")
write('R-10.3', """L.run(async () => {
  await C.withPage(21, async (page, base) => {
    await C.ready(page, base);
    await C.shoot(page, 0, 0);
    const id1 = JSON.parse(page.fires()[0].postData).game;
    await page.reload(); await L.sleep(800);
    await C.shoot(page, 0, 0);
    const id2 = JSON.parse(page.fires()[page.fires().length - 1].postData).game;
    check(page.news().length === 2, 'the reloaded page did not start a game of its own (' + page.news().length + ' /api/new requests)');
    check(id1 && id2 && id1 !== id2, 'the reloaded page kept using the earlier game id');
  });
});""")
bw('R-10.4', """await page.clickCell(4, 4); await L.sleep(500);
    const bad = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const i = await C.info(page, r, c); if (C.marked(i)) bad.push(r + ',' + c); }
    check(bad.length === 0, 'a failed shot left cells marked: ' + bad);
    check(/Ships remaining:?\\s*5\\b/i.test(await C.text(page)), 'the count changed after a failed shot');""",
   rule="(rq) => (rq.method === 'POST' && /api\\/fire/.test(rq.url) ? { action: 'fail' } : { action: 'continue' })")
write('R-10.6', """L.run(async () => {
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
      check(/Ships remaining:?\\s*5\\b/i.test(await C.text(page)), 'the count changed after the restart error');
    } finally { s2.closeAllConnections?.(); await new Promise((r) => s2.close(r)); }
  });
});""")
write('R-10.7', """L.run(async () => {
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
});""")
print('ok')
