'use strict';
// Witness R-9.5: ?assignee=dana&status=open combines with AND.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const a = await L.ticket(s.api, { title: 'dana open' });
  const b = await L.ticket(s.api, { title: 'dana wip' });
  const c = await L.ticket(s.api, { title: 'erin open' });
  const d = await L.ticket(s.api, { title: 'none open' });
  await L.assign(s.api, a.id, 'dana');
  await L.assign(s.api, b.id, 'dana');
  await L.assign(s.api, c.id, 'erin');
  await L.advance(s.api, b.id, 'in_progress');
  const r = await s.api.get('/tickets?assignee=dana&status=open');
  eq(r.body.items.map((i) => i.id), [a.id], 'only dana\'s open ticket');
});
