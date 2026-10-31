'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const p = await L.freePort();
  const r = await L.listenReport(String(p));
  check(r.kind === 'listening' && r.ports.includes(p), 'PORT=' + p + ' should be listened on, got ' + JSON.stringify({ kind: r.kind, ports: r.ports, out: r.out.slice(0, 100) }));
});
