'use strict';
// Runs the judges' functional checks for the shared-expenses case against one product tree.
const fs = require('node:fs'); const os = require('node:os'); const path = require('node:path');
const { start, req } = require('./lib');
(async () => {
  const dir = process.argv[2]; const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qx-')); const out = {};
  let s = await start(dir, 'server.js', { DATA_FILE: path.join(tmp, 'data.json') });
  if (!s.started) { console.log(JSON.stringify({ dir, error: 'did not start', out: s.out().slice(0, 300) })); return; }
  const p = s.port;
  out.whitespace_name = (await req(p, 'POST', '/groups', { id: 'ws', members: ['ann', '  '] })).status;
  out.bad_percent = (await req(p, 'GET', '/groups/%E0%A4%A/balances')).status;
  out.bad_percent_2 = (await req(p, 'GET', '/groups/%E0/balances')).status;
  const p1 = await req(p, 'POST', '/groups', { id: '__proto__', members: ['a', 'b'] });
  const p2 = await req(p, 'GET', '/groups/__proto__/balances');
  const p3 = await req(p, 'POST', '/groups', { id: '__proto__', members: ['a', 'b'] });
  out.proto_group = [p1.status, p2.status, p3.status];
  await req(p, 'POST', '/groups', { id: 't1', members: ['x', '2', 'd'] });
  await req(p, 'POST', '/groups/t1/expenses', { payer: 'x', cents: 50, split: 'exact', shares: { d: 50 } });
  await req(p, 'POST', '/groups/t1/expenses', { payer: '2', cents: 50, split: 'exact', shares: { d: 50 } });
  out.tie_owed = (await req(p, 'GET', '/groups/t1/settlements')).body;
  await req(p, 'POST', '/groups', { id: 't2', members: ['zed', '7', 'amy'] });
  await req(p, 'POST', '/groups/t2/expenses', { payer: 'amy', cents: 100, split: 'exact', shares: { zed: 50, 7: 50 } });
  out.tie_owes = (await req(p, 'GET', '/groups/t2/settlements')).body;
  const m1 = await req(p, 'POST', '/groups', { id: 'pm', members: ['__proto__', 'bob'] });
  const m2 = await req(p, 'POST', '/groups/pm/expenses', { payer: 'bob', cents: 100, split: 'equal' });
  out.proto_member = [m1.status, m2.status, (await req(p, 'GET', '/groups/pm/balances')).body];
  await s.stop();
  const empty = path.join(tmp, 'empty.json'); fs.writeFileSync(empty, '');
  s = await start(dir, 'server.js', { DATA_FILE: empty });
  out.empty_data_file = s.started ? 'started' : `did not start: ${JSON.stringify(s.exited)}`;
  await s.stop();
  s = await start(dir, 'server.js', {});
  out.no_data_file = s.started ? 'started' : `did not start: ${JSON.stringify(s.exited)}`;
  await s.stop();
  console.log(JSON.stringify(out));
})();
