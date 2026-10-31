'use strict';
// Witness R-9.1: ?assignee=dana lists only dana's tickets.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const a = await L.ticket(s.api, { title: 'A' });
  const b = await L.ticket(s.api, { title: 'B' });
  const c = await L.ticket(s.api, { title: 'C' });
  await L.assign(s.api, a.id, 'dana');
  await L.assign(s.api, b.id, 'erin');
  const r = await s.api.get('/tickets?assignee=dana');
  check(r.status === 200, 'answers 200');
  eq(r.body.items.map((i) => i.id), [a.id], 'only dana\'s ticket');
});
