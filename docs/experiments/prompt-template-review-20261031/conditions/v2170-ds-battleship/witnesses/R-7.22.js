'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    const g = (await L.getJson(p, '/api/new')).json.game;
    const x = await L.rawFire(p, '{not json'); check(x.status === 400, 'malformed body answered ' + x.status);
    await L.sleep(400);
    const alive = await L.getJson(p, '/api/new').catch(() => null);
    check(s.exited === null && alive && alive.status === 200, 'the server is gone or not serving afterwards: ' + JSON.stringify(s.exited) + ' ' + s.stderr.slice(0, 120));
  } finally { await s.kill(); }
});
