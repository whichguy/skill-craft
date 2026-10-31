'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    await L.sleep(100);
    const out = s.stdout + s.stderr;
    check(new RegExp('https?://[^\\s]*:' + p + '\\b').test(out), 'startup output does not name an http URL with port ' + p + ': ' + JSON.stringify(out.slice(0, 200)));
  } finally { await s.kill(); }
});
