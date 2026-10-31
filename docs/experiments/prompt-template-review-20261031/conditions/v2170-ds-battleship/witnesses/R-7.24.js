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
    const raw = await new Promise((resolve) => {
      const sock = L.net.connect(p, '127.0.0.1');
      let data = '';
      sock.on('connect', () => sock.write('GET http://[ HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'));
      sock.on('data', (d) => { data += d; });
      sock.on('close', () => resolve(data));
      sock.on('error', () => resolve(data));
      setTimeout(() => { sock.destroy(); resolve(data); }, 3000);
    });
    check(/^HTTP\/1\.1 400/.test(raw), 'GET http://[ answered ' + JSON.stringify(raw.slice(0, 60)));
    await L.sleep(400);
    const alive = await L.getJson(p, '/api/new').catch(() => null);
    check(s.exited === null && alive && alive.status === 200, 'the server is gone or not serving afterwards: ' + JSON.stringify(s.exited) + ' ' + s.stderr.slice(0, 120));
  } finally { await s.kill(); }
});
