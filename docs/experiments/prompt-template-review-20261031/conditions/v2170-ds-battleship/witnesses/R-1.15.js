'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const nets = Object.values(L.os.networkInterfaces()).flat().filter((a) => a && a.family === 'IPv4' && !a.internal);
  if (nets.length === 0) { console.log('no non-internal IPv4 address on this host'); process.exit(3); }
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    const refused = await new Promise((resolve) => {
      const c = L.net.connect({ host: nets[0].address, port: p, timeout: 2000 });
      c.on('connect', () => { c.destroy(); resolve(false); });
      c.on('error', () => resolve(true));
      c.on('timeout', () => { c.destroy(); resolve(true); });
    });
    check(refused, 'a connection to ' + nets[0].address + ':' + p + ' was accepted (the service is not loopback-only)');
  } finally { await s.kill(); }
});
