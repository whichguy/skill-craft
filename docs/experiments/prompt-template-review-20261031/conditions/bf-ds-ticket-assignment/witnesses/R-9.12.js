'use strict';
// Witness R-9.12: A 64-character assignee filter is accepted.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const name = 'n'.repeat(64);
  await L.assign(s.api, t.id, name);
  const r = await s.api.get('/tickets?assignee=' + name);
  check(r.status === 200, '64-character filter answers 200, got ' + r.status);
  eq(r.body.items.map((i) => i.id), [t.id], 'finds the ticket');
});
