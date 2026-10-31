'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'the server to answer');
    await L.sleep(6000);
    check(s.exited === null, 'the process exited ' + JSON.stringify(s.exited) + ' within 6 s of starting');
    const r = await L.getJson(p, '/api/new');
    check(r.status === 200, 'GET /api/new after 6 s idle answered ' + r.status);
    const page = await L.getJson(p, '/');
    check(page.status === 200, 'GET / after 6 s idle answered ' + page.status);
  } finally { await s.kill(); }
});
