'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const x = await L.getJson(s.port, '/nope'); check(x.status === 404, 'GET /nope answered ' + x.status); check(x.json && typeof x.json.error === 'string', 'body is not JSON error: ' + x.text.slice(0, 80)); check(!/<html/i.test(x.text), 'the page was served');
  } finally { await s.close(); }
});
