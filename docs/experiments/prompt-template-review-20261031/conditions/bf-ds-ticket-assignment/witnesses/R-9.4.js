'use strict';
// Witness R-9.4: ?status=open&priority=urgent lists only tickets that are both.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const a = await L.ticket(s.api, { title: 'open urgent', priority: 'urgent' });
  const b = await L.ticket(s.api, { title: 'open low', priority: 'low' });
  const c = await L.ticket(s.api, { title: 'wip urgent', priority: 'urgent' });
  await L.advance(s.api, c.id, 'in_progress');
  const r = await s.api.get('/tickets?status=open&priority=urgent');
  eq(r.body.items.map((i) => i.id), [a.id], 'only the open urgent ticket');
});
