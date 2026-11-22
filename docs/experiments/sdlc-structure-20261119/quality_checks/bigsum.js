'use strict';
// shared-expenses: what happens when a member's running total passes the largest safe integer.
const fs = require('node:fs'); const os = require('node:os'); const path = require('node:path'); const http = require('node:http');
const { start, req } = require('./lib');
const raw = (port, p) => new Promise((resolve) => http.get({ host: '127.0.0.1', port, path: p }, (res) => { let t = ''; res.on('data', (d) => { t += d; }); res.on('end', () => resolve(`${res.statusCode} ${t}`)); }));
(async () => {
  const dir = process.argv[2]; const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qb-'));
  const s = await start(dir, 'server.js', { DATA_FILE: path.join(tmp, 'data.json') });
  if (!s.started) { console.log(JSON.stringify({ error: 'did not start', out: s.out().slice(0, 200) })); return; }
  const out = {};
  await req(s.port, 'POST', '/groups', { id: 'other', members: ['Ada', 'Bo'] });
  out.first = (await req(s.port, 'POST', '/groups/other/expenses', { payer: 'Ada', cents: 9007199254740991, split: 'exact', shares: { Bo: 9007199254740991 } })).status;
  out.second = (await req(s.port, 'POST', '/groups/other/expenses', { payer: 'Ada', cents: 2, split: 'exact', shares: { Bo: 2 } })).status;
  out.balances = await raw(s.port, '/groups/other/balances');
  out.settlements = await raw(s.port, '/groups/other/settlements');
  await s.stop(); console.log(JSON.stringify(out));
})();
