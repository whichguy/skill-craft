'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); check(r.text.includes('<title>Battleship</title>'), 'the body has no exact <title>Battleship</title>'); } finally { await s.close(); }
});
