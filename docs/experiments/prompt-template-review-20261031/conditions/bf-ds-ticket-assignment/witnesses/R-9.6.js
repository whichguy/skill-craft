'use strict';
// Witness R-9.6: status, priority and assignee combine.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const a = await L.ticket(s.api, { title: 'A', priority: 'urgent' });
  const b = await L.ticket(s.api, { title: 'B', priority: 'low' });
  const c = await L.ticket(s.api, { title: 'C', priority: 'urgent' });
  const d = await L.ticket(s.api, { title: 'D', priority: 'urgent' });
  await L.assign(s.api, a.id, 'dana');
  await L.assign(s.api, b.id, 'dana');
  await L.assign(s.api, c.id, 'dana');
  await L.assign(s.api, d.id, 'erin');
  await L.advance(s.api, c.id, 'in_progress');
  const r = await s.api.get('/tickets?status=open&priority=urgent&assignee=dana');
  eq(r.body.items.map((i) => i.id), [a.id], 'only the ticket matching all three');
});
