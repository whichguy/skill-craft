'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const p = await L.freePort();
  let s = L.spawnServer({ port: p });
  let id;
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    id = (await L.getJson(p, '/api/new')).json.game;
    check((await L.fire(p, id, 0, 0)).status === 200, 'a shot in the first process');
  } finally { await s.kill(); }
  await L.sleep(300);
  s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'restart');
    const x = await L.fire(p, id, 0, 0);
    check(x.status === 404, 'an id issued before the restart answered ' + x.status + ' after it');
  } finally { await s.kill(); }
});
