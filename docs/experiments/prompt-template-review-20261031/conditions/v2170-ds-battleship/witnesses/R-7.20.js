'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const errs = [];
    errs.push(await L.rawFire(s.port, '{bad'));
    errs.push(await L.rawFire(s.port, JSON.stringify({ game: 'zzz', row: 0, col: 0 })));
    errs.push(await L.req(s.port, 'GET', '/api/fire'));
    errs.push(await L.req(s.port, 'POST', '/api/new', { body: '{}' }));
    errs.push(await L.req(s.port, 'POST', '/', { body: '{}' }));
    errs.push(await L.getJson(s.port, '/nope'));
    await L.fire(s.port, g, 1, 1); errs.push(await L.fire(s.port, g, 1, 1));
    const body = JSON.stringify({ game: g, row: 0, col: 0 });
    errs.push(await L.rawFire(s.port, body + ' '.repeat(1024 * 1024 + 1 - body.length)));
    check(errs.map((e) => e.status).join() === '400,404,405,405,405,404,409,413', 'statuses ' + errs.map((e) => e.status));
for (const e of errs) {
      check(e.json && typeof e.json === 'object' && !Array.isArray(e.json), 'status ' + e.status + ' body is not a JSON object: ' + e.text.slice(0, 80));
      check(Object.keys(e.json).join() === 'error' && typeof e.json.error === 'string' && e.json.error.length > 0, 'status ' + e.status + ' body keys ' + Object.keys(e.json));
    }
  } finally { await s.close(); }
});
