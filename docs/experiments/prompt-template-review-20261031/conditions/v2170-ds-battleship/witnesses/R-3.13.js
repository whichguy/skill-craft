'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    async function pattern() {
      const g = (await L.getJson(p, '/api/new')).json.game;
      const seq = [];
      for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const x = await L.fire(p, g, r, c); if (x.status === 200) seq.push(x.json.result[0]); }
      return seq.join('');
    }
    const pats = new Set();
    for (let i = 0; i < 3; i++) pats.add(await pattern());
    check(pats.size > 1, 'three games in one process had the same fleet');
  } finally { await s.kill(); }
});
